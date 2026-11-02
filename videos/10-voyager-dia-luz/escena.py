"""Flash Datos · video 10: Voyager 1 llega a un día luz de la Tierra.

Escena nueva: la nave Voyager 1 modelada en 3D (antena parabólica en malla, cuerpo decagonal,
RTG, brazo científico y magnetómetro), pulso de luz que viaja de la Tierra a la nave sobre un
mapa del sistema solar a escala real, estrellas en estela, ondas de radio que se apagan y vuelven,
y el disco de oro trazado por rayos con brillo anisotrópico de surcos.

Uso:
  python3 escena.py test 1 5 12 ...       -> PNG de prueba en frames_test/
  python3 escena.py chunk <ini> <fin> <out>
  python3 escena.py info
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from noise import fbm

W, H, FPS = 1080, 1920, 30
TY = math.tan(math.radians(20)); TX = TY * W / H
PIX = 2 * TY / H

xs = ((np.arange(W) + 0.5) / W * 2 - 1) * TX
ys = (1 - (np.arange(H) + 0.5) / H * 2) * TY
DX, DY = np.meshgrid(xs, ys)
NRM = np.sqrt(DX * DX + DY * DY + 1)
DIRS = np.stack([DX / NRM, DY / NRM, -1 / NRM], axis=-1).astype(np.float64)

LIGHT = np.array([-0.50, 0.40, 0.77]); LIGHT /= np.linalg.norm(LIGHT)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return np.asarray(a, float) * (1 - s) + np.asarray(b, float) * s


def sample(tex, lat, lon):
    th, tw = tex.shape[:2]
    u = (lon + np.pi) / (2 * np.pi) * tw - 0.5
    v = (0.5 - lat / np.pi) * th - 0.5
    u0 = np.floor(u).astype(np.int64); v0 = np.floor(v).astype(np.int64)
    fu = (u - u0).astype(np.float32); fv = (v - v0).astype(np.float32)
    ua = u0 % tw; ub = (u0 + 1) % tw
    va = np.clip(v0, 0, th - 1); vb = np.clip(v0 + 1, 0, th - 1)
    if tex.ndim == 3:
        fu = fu[..., None]; fv = fv[..., None]
    a, b, c, d = tex[va, ua], tex[va, ub], tex[vb, ua], tex[vb, ub]
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


def rot_y(v, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = v[..., 0], v[..., 1], v[..., 2]
    return np.stack([x * c + z * s, y, -x * s + z * c], -1)


def rot_x(v, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = v[..., 0], v[..., 1], v[..., 2]
    return np.stack([x, y * c + z * s, -y * s + z * c], -1)


def latlon(v):
    return np.arcsin(np.clip(v[..., 1], -1, 1)), np.arctan2(v[..., 0], v[..., 2])


def rotm(yaw, pitch=0.0, roll=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch); cr, sr = math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
EARTH = lin(np.clip(T("earth"), 0, 1)); CLOUDS = T("earth_clouds"); LAND = T("earth_land")


# ---------------- fondo: Vía Láctea tenue en diagonal ----------------
def make_background(seed=10, band=True):
    rng = np.random.default_rng(seed)
    bg = np.zeros((H, W, 3), np.float32)
    n = 2200
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.02 + 0.45 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 45
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    gy, gx = np.mgrid[0:120, 0:68] / 40.0
    neb = fbm(gx, gy, np.full_like(gx, 3.1), 5, seed=seed + 30)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.42) * 2.2, 0, 1) ** 1.5
    if band:
        yy, xx = np.mgrid[0:H, 0:W]
        dband = np.abs((yy - 0.55 * H) - 0.9 * (xx - 0.5 * W)) / H
        neb = neb * (0.35 + 1.3 * np.exp(-(dband / 0.16) ** 2))
    bg += neb[..., None] * np.array([0.020, 0.018, 0.042], np.float32)
    return bg


BG = make_background()


# ---------------- cámara ----------------
class Cam:
    def __init__(self, pos, target, roll=0.0):
        self.O = np.asarray(pos, float)
        f = np.asarray(target, float) - self.O; f /= np.linalg.norm(f)
        up0 = np.array([math.sin(roll), math.cos(roll), 0.0])
        r = np.cross(f, up0); r /= np.linalg.norm(r)
        u = np.cross(r, f)
        self.f, self.r, self.u = f, r, u

    def dirs(self, y0, y1, x0, x1):
        d = DIRS[y0:y1, x0:x1]
        return d[..., 0:1] * self.r + d[..., 1:2] * self.u + (-d[..., 2:3]) * self.f

    def proj(self, P):
        P = np.atleast_2d(np.asarray(P, float))
        rel = P - self.O
        cx = rel @ self.r; cy = rel @ self.u; cz = rel @ self.f
        czs = np.where(np.abs(cz) < 1e-6, 1e-6, cz)
        return (cx / czs / TX + 1) / 2 * W, (1 - cy / czs / TY) / 2 * H, cz


# ---------------- Tierra ----------------
def draw_earth(img, cam, C, r, t):
    C = np.asarray(C, float)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    cx, cy, cz = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
    if cz[0] <= 0:
        return
    rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
    ext = rpx * 1.18 + 4
    x0 = int(max(0, cx - ext)); x1 = int(min(W, cx + ext + 1))
    y0 = int(max(0, cy - ext)); y1 = int(min(H, cy + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return
    d = cam.dirs(y0, y1, x0, x1)
    oc = cam.O - C
    b = d @ oc
    perp2 = np.maximum(float(oc @ oc) - b * b, 0)
    dd = np.sqrt(perp2)
    pixw = np.maximum(-b, 1e-9) * PIX
    alpha = np.clip((r - dd) / pixw + 0.5, 0, 1)
    region = img[y0:y1, x0:x1]
    hz = (dd > r * 0.995) & (dd < r * 1.1)
    if hz.any():
        P = cam.O + (-b[hz])[:, None] * d[hz]
        nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
        lit = np.clip(nn @ LIGHT + 0.4, 0, 1)
        gl = np.exp(-np.maximum((dd[hz] - r) / (0.03 * r), 0)) * lit * 0.55
        region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([0.25, 0.52, 1.0])
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]; bs = b[sel]
    tt = -bs - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = cam.O + tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    V = -ds
    ndl = n @ LIGHT
    loc = rot_y(rot_x(n, math.radians(18)), -1.72 + 0.03 * t)
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.88) + 0.80 * cl * 0.88
    diff = np.clip(ndl, 0, 1)
    light = (0.018 + 2.1 * diff + smooth(-0.15, 0.35, ndl) * 0.10)[..., None]
    Rr = 2 * ndl[..., None] * n - LIGHT
    spec = np.clip((Rr * V).sum(-1), 0, 1) ** 45 * (1 - land) * (1 - cl[..., 0]) * 0.9
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85])
    mu = np.clip((n * V).sum(-1), 0, 1)
    col = col + np.array([0.22, 0.50, 1.0]) * ((1 - mu) ** 2.6 * 1.3 * np.clip(ndl + 0.35, 0, 1))[..., None]
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


# ---------------- luz: puntos HDR ----------------
def glow(img, x, y, col, sigma=6.0, core=1.0):
    """Mancha luminosa HDR gaussiana en (x, y) de pantalla."""
    R = int(sigma * 4) + 2
    ix, iy = int(round(x)), int(round(y))
    y0, y1 = max(iy - R, 0), min(iy + R + 1, H); x0, x1 = max(ix - R, 0), min(ix + R + 1, W)
    if y0 >= y1 or x0 >= x1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    r2 = (xx - x) ** 2 + (yy - y) ** 2
    g = np.exp(-r2 / (2 * sigma * sigma)) * core + np.exp(-r2 / (2 * (sigma * 0.25) ** 2)) * core * 2
    img[y0:y1, x0:x1] += g[..., None] * np.asarray(col, np.float32)


def bloom(img):
    small = img[::4, ::4]
    br = np.clip(small - 0.85, 0, None)
    g = gaussian_filter(br, (5, 5, 0)) * 0.55 + gaussian_filter(br, (22, 22, 0)) * 0.8 + gaussian_filter(br, (60, 60, 0)) * 0.45
    return img + ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)


# ---------------- Voyager 1 (malla 3D) ----------------
def prism(center, axis, radius, half, n, col, cap_col=None):
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    a = np.cross(axis, [0, 1, 0]) if abs(axis[1]) < 0.9 else np.cross(axis, [1, 0, 0])
    a /= np.linalg.norm(a); b = np.cross(axis, a)
    ang = np.arange(n) * 2 * np.pi / n
    ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    top = center + axis * half + radius * ring
    bot = center - axis * half + radius * ring
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((np.array([bot[i], bot[j], top[j], top[i]]), col, False))
    faces.append((top[::-1].copy(), cap_col or col, False))
    faces.append((bot.copy(), cap_col or col, False))
    return faces


def box(center, half, R, col):
    hx, hy, hz = half
    V = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) @ R.T + center
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [(V[list(q)], col, False) for q in idx]


def voyager_local():
    """Malla en coordenadas de la nave (metros). La antena mira a +z (hacia la Tierra)."""
    faces, lines = [], []
    I = np.eye(3)
    # antena parabólica de 3.7 m
    f = 1.25; nr, ns = 6, 30
    rr = np.linspace(0.12, 1.83, nr + 1)
    ang = np.arange(ns) * 2 * np.pi / ns
    def P(r, a):
        return np.array([r * math.cos(a), r * math.sin(a), r * r / (4 * f)])
    for i in range(nr):
        for j in range(ns):
            a0, a1 = ang[j], ang[(j + 1) % ns]
            q = np.array([P(rr[i], a0), P(rr[i], a1), P(rr[i + 1], a1), P(rr[i + 1], a0)])
            faces.append((q, (238, 238, 232), "dish"))
    # alimentador y soportes
    feed = np.array([0, 0, 1.05])
    faces += prism(feed, (0, 0, 1), 0.16, 0.12, 8, (210, 210, 215))
    for k in range(3):
        a = k * 2 * np.pi / 3 + 0.5
        lines.append((P(1.6, a), feed, 0.03, (200, 200, 205)))
    # cuerpo decagonal (bus) con mantas doradas
    faces += prism(np.array([0, 0, -0.42]), (0, 0, 1), 0.92, 0.24, 10, (92, 92, 104), (196, 156, 72))
    faces += prism(np.array([0, 0, -0.86]), (0, 0, 1), 0.38, 0.22, 8, (180, 140, 60))
    # brazo de los RTG (generadores de plutonio)
    a0 = np.array([-0.85, -0.10, -0.50]); a1 = np.array([-3.6, -0.45, -0.60])
    lines.append((a0, a1, 0.07, (150, 150, 160)))
    for s in (0.38, 0.62, 0.86):
        c = a0 + (a1 - a0) * s
        faces += prism(c, a1 - a0, 0.21, 0.25, 8, (70, 70, 78), (110, 110, 120))
        for k in range(4):
            fa = k * np.pi / 2 + 0.4
            fin = np.array([0, math.cos(fa), math.sin(fa)]) * 0.33
            lines.append((c + fin - (a1 - a0) / np.linalg.norm(a1 - a0) * 0.22, c + fin + (a1 - a0) / np.linalg.norm(a1 - a0) * 0.22, 0.05, (85, 85, 92)))
    # brazo científico con plataforma de cámaras
    b0 = np.array([0.85, -0.05, -0.55]); b1 = np.array([3.1, 0.25, -0.55])
    lines.append((b0, b1, 0.08, (170, 170, 178)))
    R = rotm(0.3, 0.2, 0.0)
    faces += box(b1 + np.array([0.1, 0, 0]), (0.38, 0.30, 0.30), R, (60, 60, 68))
    faces += box(b1 + np.array([0.15, 0.32, 0.25]), (0.16, 0.12, 0.28), R, (205, 205, 210))
    faces += box(b1 + np.array([0.55, -0.05, 0.15]), (0.12, 0.12, 0.22), R, (190, 160, 80))
    # magnetómetro: brazo largo y fino de 13 m
    lines.append((np.array([0.2, 0.75, -0.55]), np.array([-5.8, 11.4, -0.9]), 0.05, (175, 175, 182)))
    faces += box(np.array([-5.8, 11.4, -0.9]), (0.12, 0.12, 0.12), I, (190, 190, 196))
    # antenas de radio y plasma
    lines.append((np.array([-0.4, -0.7, -0.6]), np.array([-1.6, -6.5, -1.0]), 0.03, (160, 160, 170)))
    lines.append((np.array([0.4, -0.7, -0.6]), np.array([2.4, -6.2, -0.9]), 0.03, (160, 160, 170)))
    return faces, lines


V_FACES, V_LINES = voyager_local()


def draw_voyager(layer, cam, pos, R, scale=1.0, alpha=1.0, glow_dish=0.0):
    """Dibuja la nave en una capa RGBA (supermuestreo x2)."""
    pos = np.asarray(pos, float)
    items = []
    L = LIGHT
    for q, col, kind in V_FACES:
        Q = (q * scale) @ R.T + pos
        c = Q.mean(0)
        n = np.cross(Q[1] - Q[0], Q[2] - Q[0])
        if np.linalg.norm(n) < 1e-12:
            n = np.cross(Q[2] - Q[0], Q[3] - Q[0]) if len(Q) > 3 else np.array([0, 0, 1.0])
        n = n / (np.linalg.norm(n) + 1e-12)
        vdir = cam.O - c; vdir /= np.linalg.norm(vdir)
        if kind == "dish":
            back = n @ vdir < 0
            if back:
                n = -n
            base = (205, 205, 200) if not back else (150, 150, 152)
        else:
            if n @ vdir <= 0:
                continue
            base = col
        diff = max(0.0, float(n @ L))
        Rv = 2 * (n @ L) * n - L
        spec = max(0.0, float(Rv @ vdir)) ** 24 * 0.55
        lam = 0.16 + 0.95 * diff
        shade = [min(255, int(ch * lam + 255 * spec)) for ch in base]
        if kind == "dish" and glow_dish > 0:
            shade = [min(255, int(s * (1 - 0.4 * glow_dish) + g * glow_dish)) for s, g in zip(shade, (120, 230, 255))]
        x, y, z = cam.proj(Q)
        if (z <= 0.05).any():
            continue
        items.append((float(np.linalg.norm(c - cam.O)), "poly", [(float(a) * 2, float(b) * 2) for a, b in zip(x, y)], tuple(shade)))
    for p0, p1, wm, col in V_LINES:
        A0 = (p0 * scale) @ R.T + pos; A1 = (p1 * scale) @ R.T + pos
        x, y, z = cam.proj(np.array([A0, A1]))
        if (z <= 0.05).any():
            continue
        c = (A0 + A1) / 2
        dist = float(np.linalg.norm(c - cam.O))
        wpx = max(2.0, wm * scale / dist / PIX * 2)
        items.append((dist, "line", [(float(x[0]) * 2, float(y[0]) * 2), (float(x[1]) * 2, float(y[1]) * 2)], col, wpx))
    items.sort(key=lambda it: -it[0])
    big = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    A = int(255 * alpha)
    for it in items:
        if it[1] == "poly":
            d.polygon(it[2], fill=it[3] + (A,), outline=it[3] + (A,))
        else:
            d.line(it[2], fill=it[3] + (A,), width=int(round(it[4])))
    layer.alpha_composite(big.resize((W, H), Image.LANCZOS))


# ---------------- disco de oro (trazado por rayos) ----------------
GOLD = lin((1.0, 0.77, 0.34))


def draw_record(img, cam, C, nrm, e1, Rad, t):
    C = np.asarray(C, float); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm)
    e1 = np.asarray(e1, float); e1 = e1 - (e1 @ nrm) * nrm; e1 /= np.linalg.norm(e1); e2 = np.cross(nrm, e1)
    pts = np.array([C + Rad * (math.cos(a) * e1 + math.sin(a) * e2) for a in np.linspace(0, 2 * np.pi, 24)])
    x, y, z = cam.proj(pts)
    x0 = int(max(0, x.min() - 4)); x1 = int(min(W, x.max() + 5)); y0 = int(max(0, y.min() - 4)); y1 = int(min(H, y.max() + 5))
    if x0 >= x1 or y0 >= y1:
        return
    d = cam.dirs(y0, y1, x0, x1)
    denom = d @ nrm
    denom = np.where(np.abs(denom) < 1e-6, 1e-6, denom)
    tt = ((C - cam.O) @ nrm) / denom
    P = cam.O + tt[..., None] * d
    L = P - C
    u = L @ e1; v = L @ e2
    r = np.sqrt(u * u + v * v) / Rad
    pixw = np.maximum(tt, 1e-6) * PIX / Rad / max(abs(float(cam.f @ nrm)), 0.25)
    alpha = np.clip((1 - r) / pixw + 0.5, 0, 1) * (tt > 0)
    sel = alpha > 0
    if not sel.any():
        return
    rs = r[sel]; us = u[sel]; vs = v[sel]; ds = d[sel]
    n = nrm if (cam.O - C) @ nrm > 0 else -nrm
    V = -ds
    Hh = LIGHT[None, :] + V; Hh /= np.linalg.norm(Hh, axis=-1, keepdims=True)
    tang = (-vs[:, None] * e1 + us[:, None] * e2) / np.maximum(rs * Rad, 1e-6)[:, None]
    th = (tang * Hh).sum(-1)
    nh = np.clip(Hh @ n, 0, 1)
    groove = 0.88 + 0.12 * np.sin(rs * 170) * smooth(0.30, 0.34, rs)
    tracks = 1 - 0.35 * np.exp(-((rs - 0.52) / 0.006) ** 2) - 0.35 * np.exp(-((rs - 0.71) / 0.006) ** 2) - 0.35 * np.exp(-((rs - 0.86) / 0.006) ** 2)
    aniso = np.exp(-(th ** 2) / 0.0035) * nh ** 3 * 1.1 * smooth(0.30, 0.35, rs)
    diff = max(0.0, float(n @ LIGHT))
    base = GOLD[None, :] * (0.05 + 0.32 * diff) * (groove * tracks)[:, None]
    lab = rs < 0.31
    base[lab] = GOLD * 0.40 * (0.10 + 0.5 * diff)
    spec_lab = np.exp(-((nh - 1) ** 2) / 0.0008) * 0.35
    col = base + aniso[:, None] * np.array([1.0, 0.82, 0.45]) + (spec_lab * lab)[:, None] * np.array([1.0, 0.85, 0.5])
    rim = smooth(0.965, 0.99, rs)
    col = col * (1 - rim[:, None] * 0.5) + rim[:, None] * GOLD * 0.9 * (0.3 + diff)
    hole = rs < 0.025
    col[hole] = 0.0
    a = alpha[sel][:, None]
    region = img[y0:y1, x0:x1]
    region[sel] = region[sel] * (1 - a) + col * a


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
P_ = lambda sid, k: SEG[sid]["parts"][k]
HK0, HK1 = SEG["hook1"]["t0"], SEG["hook1"]["t1"]
VO0 = SEG["voyager"]["t0"]; VO_P2 = P_("voyager", 1)[0]
VE0 = SEG["velocidad"]["t0"]; VE1 = SEG["velocidad"]["t1"]
DL0 = SEG["dialuz"]["t0"]; DL1 = SEG["dialuz"]["t1"]
LU0 = SEG["luz"]["t0"]; LU1 = SEG["luz"]["t1"]
RE0 = SEG["respuesta"]["t0"]; RE1 = SEG["respuesta"]["t1"]
SI0 = SEG["silencio"]["t0"]; SI1 = SEG["silencio"]["t1"]
SI_BACK = SI0 + (SI1 - SI0) * 0.60          # "…hasta que volvió a hablar"
DI0 = SEG["disco"]["t0"]; DI1 = SEG["disco"]["t1"]
CI0 = SEG["cierre"]["t0"]; CI1 = SEG["cierre"]["t1"]
CARD = CI1 + 0.15
FL = [VO0 - 0.2, VE0 - 0.2, DL0 - 0.2, SI0 - 0.2, DI0 - 0.2, CI0 - 0.2]


def scene(t):
    names = ["hook", "nave", "veloz", "mapa", "silencio", "disco", "adios"]
    for i, f in enumerate(FL):
        if t < f:
            return names[i]
    return names[-1]


# ---------------- textos ----------------
FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); RED = (255, 90, 70); GREEN = (120, 255, 160)
HL_WORDS = set()


def groups_for_part(t0, t1, text):
    words = text.split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w[-1] in ".,:…?!" or len(" ".join(cur)) > 17:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    weights = [sum(len(w) for w in g) + 2 for g in groups]
    tot = sum(weights); t = t0; out = []
    for g, wt in zip(groups, weights):
        dur = (t1 - t0) * wt / tot
        out.append([t, t + dur, g]); t += dur
    return out


CAPS = []
for s in TM["segments"]:
    for t0, t1, txt_ in s["parts"]:
        CAPS += groups_for_part(t0, t1, txt_)
for i in range(len(CAPS) - 1):
    if CAPS[i + 1][0] - CAPS[i][1] < 0.7:
        CAPS[i][1] = CAPS[i + 1][0]


def is_hl(w):
    core = w.strip(".,:…?¿!¡()≈").lower()
    raw = w.strip(".,:…?¿!¡()≈")
    return any(ch.isdigit() for ch in core) or core in HL_WORDS or (raw.isupper() and len(raw) > 1)


def draw_caption(layer, t):
    if t >= CARD:
        return
    for (t0, t1, g) in CAPS:
        if t0 <= t < t1:
            k = min(1.0, (t - t0) / 0.09)
            size = int(round(80 * (1.12 - 0.12 * k)))
            f = font("Inter-Black.otf", size)
            d = ImageDraw.Draw(layer)
            space = d.textlength(" ", font=f)
            widths = [d.textlength(w, font=f) for w in g]
            total = sum(widths) + space * (len(g) - 1)
            if total > W - 60:
                f = font("Inter-Black.otf", int(size * (W - 60) / total))
                widths = [d.textlength(w, font=f) for w in g]; space = d.textlength(" ", font=f)
                total = sum(widths) + space * (len(g) - 1)
            x = W / 2 - total / 2; y = 1300
            for w, wd in zip(g, widths):
                col = YELLOW if is_hl(w) else WHITE
                d.text((x, y), w, font=f, fill=col + (255,), anchor="lm", stroke_width=9, stroke_fill=(8, 10, 20, 255))
                x += wd + space
            return


def fade(t, a, b, f=0.25):
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / f, (b - t) / f)


def txt(d, xy, s, size, col, A, fn="Inter-Black.otf", sw=8, anchor="mm"):
    d.text(xy, s, font=font(fn, size), fill=col + (A,), anchor=anchor, stroke_width=sw, stroke_fill=(8, 10, 20, A))


def draw_label(layer, t, a, b, title, subs, title_col=WHITE, title_size=118, y0=360):
    al = fade(t, a, b)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - min(1.0, (t - a) / 0.3)) * 24
    y = y0 + rise
    txt(d, (W / 2, y), title, title_size, title_col, A)
    y += title_size * 0.5 + 44
    for s in subs:
        txt(d, (W / 2, y), s, 54, CYAN, A, "Inter-ExtraBold.otf", 7)
        y += 70


def bolt(cx, cy, s):
    pts = [(0.58, 0.0), (0.12, 0.56), (0.44, 0.56), (0.30, 1.0), (0.88, 0.38), (0.55, 0.38), (0.74, 0.0)]
    return [(cx + (px - 0.5) * s, cy + (py - 0.5) * s) for px, py in pts]


def draw_watermark(layer):
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 38)
    tw = d.textlength("FLASH DATOS", font=f)
    x = W / 2 - (tw + 40) / 2
    d.polygon(bolt(x + 14, 212, 40), fill=YELLOW + (230,))
    d.text((x + 40, 212), "FLASH DATOS", font=f, fill=(255, 255, 255, 215), anchor="lm", stroke_width=4, stroke_fill=(8, 10, 20, 160))


def marker(d, x, y, t, col, A, r0=34, label=None, side=1, lsize=46):
    rr = r0 + 5 * math.sin(t * 7)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (A,), width=5)
    if label:
        lx = x + side * (rr + 26)
        d.line([x + side * rr, y, lx, y], fill=col + (A,), width=4)
        txt(d, (lx + side * 10, y), label, lsize, WHITE, A, "Inter-Black.otf", 7, "lm" if side > 0 else "rm")


def draw_endcard(layer, t):
    al = fade(t, CARD, END + 1, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    layer.alpha_composite(Image.new("RGBA", (W, H), (4, 6, 12, int(175 * al))))
    d = ImageDraw.Draw(layer)
    k = ease_out((t - CARD) / 0.4)
    d.polygon(bolt(W / 2, 780, 230 + 40 * k), fill=YELLOW + (A,))
    txt(d, (W / 2, 1010), "FLASH DATOS", 104, WHITE, A)
    txt(d, (W / 2, 1120), "Síguenos para más datos", 52, CYAN, A, "Inter-ExtraBold.otf", 6)
    txt(d, (W / 2, 1185), "del espacio", 52, CYAN, A, "Inter-ExtraBold.otf", 6)


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


def clock_hud(d, cx, cy, rad, hours, A, col=YELLOW, total=24):
    """Reloj circular: arco lleno según las horas (una vuelta = 24 h)."""
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(255, 255, 255, int(A * 0.35)), width=6)
    turns = hours / 24.0
    full = int(turns)
    frac = turns - full
    if full >= 1:
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=col + (A,), width=12)
    if frac > 1e-3:
        r2 = rad if full == 0 else rad - 18
        d.arc([cx - r2, cy - r2, cx + r2, cy + r2], -90, -90 + 360 * frac, fill=(col if full == 0 else CYAN) + (A,), width=12)
    ang = -math.pi / 2 + 2 * math.pi * turns
    d.line([cx, cy, cx + math.cos(ang) * rad * 0.78, cy + math.sin(ang) * rad * 0.78], fill=WHITE + (A,), width=7)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=WHITE + (A,))


# ---------------- escenas ----------------
def sc_hook(img, layer, t):
    """La Tierra abajo; un pulso de luz sale hacia la Voyager, un punto lejano arriba."""
    k = t / FL[0]
    cam = Cam((0.25 - 0.2 * k, 0.0, 6.2 - 0.5 * k), (0.0, 1.85, 0.0))
    draw_earth(img, cam, (0, 0, 0), 1.0, t)
    vx, vy = W / 2 + 40, 700
    tw = 0.5 + 0.5 * math.sin(t * 5)
    glow(img, vx, vy, (0.9, 0.95, 1.0), 2.5, 0.8 + 0.4 * tw)
    # pulso que viaja
    sx, sy = W / 2 - 30, 1340
    s = ease((t - 0.4) / (HK1 - 0.7))
    if 0.4 < t:
        px = sx + (vx - sx) * s; py = sy + (vy - sy) * s
        n = 40
        for i in range(n):
            q = max(0.0, s - i * 0.012)
            glow(img, sx + (vx - sx) * q, sy + (vy - sy) * q, (0.3, 0.7, 1.4), 3.5, (1 - i / n) * 0.5)
        glow(img, px, py, (1.6, 2.2, 3.0), 9, 1.2)
    return cam, dict(vx=vx, vy=vy)


def sc_nave(img, layer, t):
    u = t - FL[0]
    p2 = max(0.0, t - VO_P2)
    yaw = 0.9 + 0.12 * u
    R = rotm(0.0, 0.0, 0.0)
    dist = 10.0 + 1.2 * u + 16 * ease(p2 / 4.0)
    cam_pos = np.array([math.sin(yaw) * dist, 3.2 + 0.25 * u, math.cos(yaw) * dist])
    target = np.array([0.0, 1.6 - 0.3 * ease(p2 / 4.0), 0.0])
    cam = Cam(cam_pos, target, roll=0.08)
    # el Sol, muy lejos, como una estrella brillante
    sx, sy, sz = cam.proj(cam.O + LIGHT * 1e6)
    if sz[0] > 0:
        glow(img, float(sx[0]), float(sy[0]), (3.0, 2.6, 1.9), 10, 1.0)
    draw_voyager(layer, cam, (0, 0, 0), R)
    return cam, {}


STREAK = np.random.default_rng(5).uniform([-60, -110, -400], [60, 110, 40], (900, 3))


def sc_veloz(img, layer, t):
    u = t - FL[1]
    R = rotm(0.25, 0.0, 0.0)
    # la nave avanza hacia -z; la cámara la sigue de lado, las estrellas pasan como estelas
    cam = Cam((9.5 + 0.6 * u, 3.0, 8.0 - 0.8 * u), (0.0, 0.6, -1.5), roll=-0.12)
    speed = 160.0
    P = STREAK.copy()
    P[:, 2] = (P[:, 2] + speed * u) % 440 - 400
    Q = P.copy(); Q[:, 2] -= 22.0
    x0, y0, z0 = cam.proj(P); x1, y1, z1 = cam.proj(Q)
    d = ImageDraw.Draw(layer)
    for i in range(len(P)):
        if z0[i] > 1 and z1[i] > 1:
            a = int(min(255, 9000 / z0[i]))
            if a > 10:
                d.line([(x0[i], y0[i]), (x1[i], y1[i])], fill=(210, 230, 255, a), width=3 if z0[i] > 40 else 5)
    draw_voyager(layer, cam, (0, 0, 0), R)
    return cam, {}


# Mapa del sistema solar (unidades: UA). Voyager 1 a 173 UA, unos 35° sobre el plano de los planetas.
ORBITS = [("Mercurio", 0.387, (200, 200, 200)), ("Venus", 0.723, (255, 209, 102)), ("Tierra", 1.0, (79, 216, 255)),
          ("Marte", 1.524, (255, 140, 110)), ("Júpiter", 5.20, (230, 190, 140)), ("Saturno", 9.58, (240, 215, 150)),
          ("Urano", 19.2, (150, 230, 240)), ("Neptuno", 30.1, (110, 150, 255))]
PH = {n: a for n, a in zip([o[0] for o in ORBITS], [2.6, 0.8, 1.9, 4.1, 2.2, 5.0, 3.4, 0.9])}
VPOS = 173.1 * np.array([0.10, math.sin(math.radians(35)), -math.cos(math.radians(35))])
TILT = math.radians(32)
UP_AX = np.array([0, math.sin(TILT), -math.cos(TILT)])


def earth_pos(t):
    a = PH["Tierra"] + 0.0 * t
    return np.array([math.cos(a), 0, math.sin(a)])


def map_cam(t):
    D0, D1 = 6.0, 500.0
    s = ease((t - (DL0 - 0.3)) / 3.6)
    D = math.exp(math.log(D0) + (math.log(D1) - math.log(D0)) * s)
    w = (D - D0) / (D1 - D0)
    tgt = lerp((0, 0, 0), VPOS * 0.5 + UP_AX * 38, w)
    drift = 0.02 * (t - DL0)
    off = np.array([math.sin(drift) * math.sin(TILT), math.cos(TILT), math.cos(drift) * math.sin(TILT)])
    return Cam(tgt + off * D, tgt, roll=0.0), D


def pulse_pos(t):
    """Posición (fracción 0→1 del camino Tierra→Voyager) y si es el regreso."""
    if LU0 - 0.1 <= t < RE0 - 0.15:
        return min(1.0, (t - (LU0 - 0.1)) / (LU1 - LU0 - 0.2)), False, 24 * min(1.0, (t - (LU0 - 0.1)) / (LU1 - LU0 - 0.2))
    if t >= RE0 - 0.15:
        span = (RE1 - RE0) - 0.2
        s = (t - (RE0 - 0.15)) / span
        hrs = 48 * min(1.0, s)
        if s < 0.5:
            return s * 2, False, hrs
        return max(0.0, 2 - s * 2), True, hrs
    return None, False, 0.0


def sc_mapa(img, layer, t):
    cam, D = map_cam(t)
    d = ImageDraw.Draw(layer)
    sx, sy, _ = cam.proj([0, 0, 0])
    glow(img, float(sx[0]), float(sy[0]), (3.0, 2.4, 1.5), 4 + 30 / (1 + D / 8), 1.2)
    big = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    db = ImageDraw.Draw(big)
    ang = np.linspace(0, 2 * np.pi, 241)
    labels = []
    for name, a, col in ORBITS:
        P = np.stack([a * np.cos(ang), np.zeros_like(ang), a * np.sin(ang)], -1)
        x, y, z = cam.proj(P)
        rpx = a / D / PIX
        if rpx < 6:
            continue
        al = min(1.0, (rpx - 6) / 20) * (0.85 if name not in ("Tierra", "Neptuno") else 1.0)
        pts = [(float(a_) * 2, float(b_) * 2) for a_, b_ in zip(x, y)]
        db.line(pts, fill=col + (int(200 * al),), width=4 if name not in ("Tierra", "Neptuno") else 6)
        pp = np.array([a * math.cos(PH[name]), 0, a * math.sin(PH[name])])
        px, py, _ = cam.proj(pp)
        rr = 9 if name != "Tierra" else 12
        db.ellipse([px[0] * 2 - rr, py[0] * 2 - rr, px[0] * 2 + rr, py[0] * 2 + rr], fill=col + (int(255 * al),))
        if name in ("Tierra", "Neptuno") or (name == "Júpiter" and 60 < rpx < 400):
            labels.append((name, float(px[0]), float(py[0]), al, col))
    layer.alpha_composite(big.resize((W, H), Image.LANCZOS))
    # Voyager y la línea de 1 día luz
    vx, vy, vz = cam.proj(VPOS)
    vx, vy = float(vx[0]), float(vy[0])
    ex, ey, _ = cam.proj(earth_pos(t)); ex, ey = float(ex[0]), float(ey[0])
    show = smooth(DL0 + 3.1, DL0 + 3.6, t)
    if show > 0 and vz[0] > 0:
        A = int(255 * show)
        n = 40
        for i in range(n):
            if i % 2 == 0:
                a0, a1 = i / n, (i + 1) / n
                d.line([(ex + (vx - ex) * a0, ey + (vy - ey) * a0), (ex + (vx - ex) * a1, ey + (vy - ey) * a1)], fill=(255, 255, 255, int(A * 0.55)), width=4)
        glow(img, vx, vy, (1.4, 1.6, 2.0), 4, show)
        marker(d, vx, vy, t, YELLOW, A, 30, "VOYAGER 1", -1 if vx > W / 2 else 1, 44)
        # 1 día luz a mitad de la línea
        mx, my = (ex + vx) / 2, (ey + vy) / 2
        lab = fade(t, DL0 + 3.6, LU0 - 0.1, 0.3)
        if lab > 0:
            txt(d, (mx + 150, my), "1 día luz", 48, YELLOW, int(255 * lab), "Inter-Black.otf", 7)
    for name, px, py, al, col in labels:
        A = int(255 * al * (1 - smooth(DL0 + 2.0, DL0 + 2.6, t) * (name == "Tierra")))
        if A > 0:
            off = -48 if name != "Neptuno" else 52
            txt(d, (px, py + off), name, 40 if name != "Tierra" else 48, col, A, "Inter-Black.otf", 6)
    # pulso de luz (ida y vuelta)
    s, back, hrs = pulse_pos(t)
    if s is not None:
        px, py = ex + (vx - ex) * s, ey + (vy - ey) * s
        col = (1.6, 2.2, 3.0) if not back else (2.6, 2.2, 1.0)
        for i in range(30):
            q = s - i * 0.012 * (-1 if back else 1)
            if 0 <= q <= 1:
                glow(img, ex + (vx - ex) * q, ey + (vy - ey) * q, tuple(c * 0.25 for c in col), 4, (1 - i / 30))
        glow(img, px, py, col, 10, 1.3)
    return cam, dict(hrs=hrs, ex=ex, ey=ey, vx=vx, vy=vy)


def sc_silencio(img, layer, t):
    u = t - FL[3]
    R = rotm(0.0, 0.0, 0.0)
    yaw = 0.55 + 0.05 * u
    cam = Cam((math.sin(yaw) * 18.0, 3.0, math.cos(yaw) * 18.0), (-3.2, -1.3, 0.0), roll=0.06)
    draw_voyager(layer, cam, (0, 0, 0), R)
    # ondas de radio desde la antena hacia la Tierra (abajo a la izquierda)
    d = ImageDraw.Draw(layer)
    on = t >= SI_BACK
    cx, cy, _ = cam.proj(R @ np.array([0, 0, 0.9]))
    cx, cy = float(cx[0]), float(cy[0])
    for k in range(5):
        if on:
            ph = (t - SI_BACK) * 0.9 + k / 5
            ph = ph % 1.0 if ph >= 0 else 0
            fadeout = smooth(SI_BACK, SI_BACK + 0.25, t)
        else:
            ph = ((SI0 - 0.3) * 0.9 + k / 5) % 1.0
            fadeout = 1 - smooth(FL[3] + 0.1, SI0 + 0.4, t)
        rad = 170 + ph * 560
        A = int(255 * (1 - ph) ** 0.8 * fadeout)
        if A <= 3:
            continue
        col = CYAN if on else (190, 190, 200)
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad], 105, 165, fill=col + (A,), width=12)
    return cam, dict(on=on)


def sc_disco(img, layer, t):
    u = t - FL[4]
    cam = Cam((0.0, 0.2, 5.6 - 0.35 * u), (0.0, -0.25, 0.0))
    a = -0.55 + 0.22 * u
    nrm = np.array([math.sin(a), 0.42, math.cos(a)]); nrm /= np.linalg.norm(nrm)
    e1 = np.array([math.cos(0.4 * u), math.sin(0.4 * u), 0.0])
    draw_record(img, cam, (0, 0.05, 0), nrm, e1, 1.0, t)
    return cam, {}


def sc_adios(img, layer, t):
    u = t - FL[5]
    R = rotm(math.pi, 0.0, 0.0)  # la antena mira a la cámara (hacia la Tierra)
    pos = np.array([0.0, 0.0, -8.0 - 9.0 * u ** 1.25])
    cam = Cam((1.2, 1.0, 9.0), (0.0, 0.4, -20.0), roll=0.03)
    # el Sol pequeño detrás de la cámara ilumina la antena
    draw_voyager(layer, cam, pos, R, alpha=1.0)
    vx, vy, _ = cam.proj(pos)
    glow(img, float(vx[0]), float(vy[0]), (0.8, 0.9, 1.1), 18, 0.25)
    return cam, dict(vx=float(vx[0]), vy=float(vy[0]))


SCENES = {"hook": sc_hook, "nave": sc_nave, "veloz": sc_veloz, "mapa": sc_mapa, "silencio": sc_silencio, "disco": sc_disco, "adios": sc_adios}


def overlays(frame_u8, layer, t, name, cam, extra):
    im = Image.fromarray(frame_u8).convert("RGBA")
    im.alpha_composite(layer)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if name == "hook":
        draw_label(layer, t, -1, FL[0], "24 HORAS", ["para que le llegue un mensaje"], YELLOW, 130)
        al = fade(t, 1.0, FL[0], 0.3)
        if al > 0:
            marker(d, extra["vx"], extra["vy"], t, YELLOW, int(255 * al), 30, "VOYAGER 1", 1, 44)
            txt(d, (W / 2 - 30, 1420), "", 10, WHITE, 0)
    elif name == "nave":
        draw_label(layer, t, VO0 + 0.1, VO_P2 - 0.05, "VOYAGER 1", ["NASA · lanzada en 1977"], WHITE, 120)
        draw_label(layer, t, VO_P2 + 0.1, FL[1], "49 AÑOS", ["alejándose sin parar"], YELLOW, 130)
    elif name == "veloz":
        draw_label(layer, t, VE0 - 0.05, FL[2], "61,000 KM/H", ["unos 17 km cada segundo"], YELLOW, 120)
    elif name == "mapa":
        draw_label(layer, t, DL0 + 0.3, LU0 - 0.2, "1 DÍA LUZ", ["25,900 millones de km", "173 veces la distancia Tierra–Sol"], YELLOW, 130)
        hrs = extra["hrs"]
        if t >= LU0 - 0.2:
            al = fade(t, LU0 - 0.2, FL[3] + 0.1, 0.2)
            A = int(255 * al)
            cx, cy = W / 2 - 170, 430
            clock_hud(d, cx, cy, 82, hrs, A)
            txt(d, (cx + 120, cy - 22), f"{int(hrs)} h", 110, YELLOW, A, "Inter-Black.otf", 8, "lm")
            sub = "la luz viaja…" if t < RE0 - 0.15 else ("ida y vuelta" if hrs < 47.9 else "¡2 días!")
            txt(d, (cx + 125, cy + 62), sub, 48, CYAN, A, "Inter-ExtraBold.otf", 6, "lm")
            if t >= RE0 - 0.15:
                txt(d, (extra["ex"], extra["ey"] + 70), "HOY", 46, WHITE, int(255 * fade(t, RE0, FL[3] + 0.1, 0.2)), "Inter-Black.otf", 7)
    elif name == "silencio":
        if not extra["on"]:
            draw_label(layer, t, SI0 - 0.1, SI_BACK, "SIN SEÑAL", ["18 y 19 de octubre"], RED, 120)
        else:
            draw_label(layer, t, SI_BACK, FL[4], "¡VOLVIÓ!", ["20 de octubre de 2026"], GREEN, 130)
    elif name == "disco":
        draw_label(layer, t, DI0 - 0.05, FL[5], "DISCO DE ORO", ["imágenes, sonidos y saludos"], YELLOW, 112)
    elif name == "adios":
        draw_label(layer, t, CI0 + 0.2, CARD, "18 NOV 2026", ["Voyager 1 a un día luz"], WHITE, 100)
    draw_caption(layer, t)
    draw_endcard(layer, t)
    draw_watermark(layer)
    im.alpha_composite(layer)
    fa = flash_alpha(t)
    if fa > 0:
        im.alpha_composite(Image.new("RGBA", (W, H), (225, 248, 255, int(235 * fa))))
        if fa > 0.35:
            b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(b).polygon(bolt(W / 2, H / 2, 420), fill=YELLOW + (int(255 * min(1, (fa - 0.35) / 0.4)),))
            im.alpha_composite(b)
    return np.asarray(im.convert("RGB"))


def render(t):
    name = scene(t)
    img = BG.copy()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cam, extra = SCENES[name](img, layer, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, layer, t, name, cam, extra)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        for ts in sys.argv[2:]:
            t = float(ts)
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, scene(t), flush=True)
    elif mode == "chunk":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(render(f / FPS).tobytes())
            if f % 30 == 0:
                print(f"{out}: {f}/{b}", flush=True)
        p.stdin.close(); p.wait()
        print("listo", out, flush=True)
    elif mode == "info":
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL], "card", round(CARD, 2), "si_back", round(SI_BACK, 2))
