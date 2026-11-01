"""Flash Datos · video 09: Hera llega al asteroide que la NASA golpeó (DART).

Escena nueva: asteroides elipsoidales con relieve (cráteres y rocas por mapa de alturas),
naves DART y Hera hechas de cajas 3D, partículas de eyección, órbita que se encoge,
y la Tierra con una trayectoria desviada al final.

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

LIGHT = np.array([-0.55, 0.45, 0.70]); LIGHT /= np.linalg.norm(LIGHT)


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


# ---------------- texturas de roca (mapa de alturas con cráteres) ----------------
def rock_texture(seed, n_craters, boulders):
    path = os.path.join(BASE, "tex", f"rock{seed}.npz")
    if os.path.exists(path):
        z = np.load(path); return z["h"], z["alb"]
    th, tw = 320, 640
    lat = (0.5 - (np.arange(th) + 0.5) / th) * np.pi
    lon = ((np.arange(tw) + 0.5) / tw * 2 - 1) * np.pi
    LO, LA = np.meshgrid(lon, lat)
    P = np.stack([np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO)], -1)
    h = fbm(P[..., 0] * 2.2, P[..., 1] * 2.2, P[..., 2] * 2.2, 6, seed=seed) - 0.5
    h += 0.35 * (fbm(P[..., 0] * 9, P[..., 1] * 9, P[..., 2] * 9, 4, seed=seed + 3) - 0.5)
    rng = np.random.default_rng(seed)
    for _ in range(n_craters):
        c = rng.normal(size=3); c /= np.linalg.norm(c)
        r = 0.06 + 0.22 * rng.random() ** 2.5
        d = np.arccos(np.clip(P @ c, -1, 1)) / r
        bowl = np.where(d < 1, (d ** 2 - 1) * 0.55, 0) + 0.22 * np.exp(-((d - 1.0) / 0.18) ** 2)
        h += bowl * r * 1.6
    if boulders:
        for _ in range(boulders):
            c = rng.normal(size=3); c /= np.linalg.norm(c)
            r = 0.015 + 0.03 * rng.random()
            d = np.arccos(np.clip(P @ c, -1, 1)) / r
            h += np.exp(-d ** 2 * 1.6) * r * 1.8
    alb = 0.17 + 0.07 * (fbm(P[..., 0] * 5, P[..., 1] * 5, P[..., 2] * 5, 4, seed=seed + 9) - 0.5) - 0.12 * np.clip(-h, 0, 0.3)
    os.makedirs(os.path.join(BASE, "tex"), exist_ok=True)
    np.savez(path, h=h.astype(np.float32), alb=alb.astype(np.float32))
    return h.astype(np.float32), alb.astype(np.float32)


H_DIM, A_DIM = rock_texture(41, 34, 70)
H_DID, A_DID = rock_texture(57, 40, 30)


def grads(h):
    th, tw = h.shape
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * 2 * np.pi / tw)
    gy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) / (2 * np.pi / th)
    gy[0] = gy[1]; gy[-1] = gy[-2]
    return np.stack([gx, gy], -1).astype(np.float32)


G_DIM = grads(H_DIM); G_DID = grads(H_DID)

T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
EARTH = lin(np.clip(T("earth"), 0, 1)); CLOUDS = T("earth_clouds"); LAND = T("earth_land")


# ---------------- fondo ----------------
def make_background():
    rng = np.random.default_rng(9)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1700
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.02 + 0.45 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 40
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    gy, gx = np.mgrid[0:120, 0:68] / 40.0
    neb = fbm(gx, gy, np.full_like(gx, 2.3), 5, seed=21)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.012, 0.016, 0.045], np.float32)
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
        cz = np.where(np.abs(cz) < 1e-6, 1e-6, cz)
        return (cx / cz / TX + 1) / 2 * W, (1 - cy / cz / TY) / 2 * H, cz


# ---------------- cuerpos ----------------
def draw_ellipsoid(img, cam, body, t):
    C = np.asarray(body["c"], float); S = np.asarray(body["s"], float)
    ang = body.get("spin", 0.0) * t + body.get("a0", 0.0)
    rmax = float(S.max())
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    depth = float(rel @ cam.f)
    if depth <= rmax * 0.2:
        return
    cx, cy, _ = cam.proj(C)
    cx, cy = float(cx[0]), float(cy[0])
    rpx = math.tan(math.asin(min(rmax / dist, 0.999))) / PIX
    if rpx < 0.7:
        return
    ext = rpx * 1.25 + 4
    x0 = int(max(0, cx - ext)); x1 = int(min(W, cx + ext + 1))
    y0 = int(max(0, cy - ext)); y1 = int(min(H, cy + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return
    d = cam.dirs(y0, y1, x0, x1)
    o = rot_y(cam.O - C, -ang) / S
    dl = rot_y(d, -ang) / S
    A = (dl * dl).sum(-1); B = (dl * o).sum(-1); Cc = float(o @ o) - 1
    disc = B * B - A * Cc
    perp = np.sqrt(np.maximum(float(o @ o) - B * B / A, 0))
    pixw = dist * PIX / float(S.min()) * 1.2
    alpha = np.clip((1 - perp) / pixw + 0.5, 0, 1)
    sel = alpha > 0
    if not sel.any():
        return
    tt = (-B[sel] - np.sqrt(np.maximum(disc[sel], 0))) / A[sel]
    u = o + tt[:, None] * dl[sel]
    u /= np.linalg.norm(u, axis=-1, keepdims=True)
    la, lo = latlon(u)
    nl = u / S; nl /= np.linalg.norm(nl, axis=-1, keepdims=True)
    g = sample(body["g"], la, lo)
    cl = np.maximum(np.cos(la), 0.15)
    east = np.stack([np.cos(lo), np.zeros_like(lo), -np.sin(lo)], -1)
    north = np.stack([-np.sin(la) * np.sin(lo), np.cos(la), -np.sin(la) * np.cos(lo)], -1)
    k = body.get("bump", 2.2)
    nl = nl - k * ((g[:, 0] / cl)[:, None] * east + g[:, 1:2] * north)
    nl /= np.linalg.norm(nl, axis=-1, keepdims=True)
    n = rot_y(nl, ang)
    alb = sample(body["alb"], la, lo)
    hh = sample(body["h"], la, lo)
    ndl = n @ LIGHT
    diff = np.clip(ndl, 0, 1) ** 0.9
    amb = 0.022 + 0.03 * np.clip(hh + 0.3, 0, 1)
    tint = np.array(body.get("tint", (1.0, 0.93, 0.84)), np.float32)
    col = (alb * (amb + 2.4 * diff))[:, None] * tint
    # cráter del impacto (zona oscura y fresca) en Dimorphos
    if body.get("crater") is not None and t >= body["crater"][1]:
        cdir = np.asarray(body["crater"][0], float)
        dd = np.arccos(np.clip(u @ cdir, -1, 1))
        grow = ease_out((t - body["crater"][1]) / 0.6)
        rim = np.exp(-((dd - 0.30 * grow) / 0.05) ** 2) * 0.6
        dark = smooth(0.30 * grow, 0.12 * grow, dd)
        col = col * (1 - 0.65 * dark)[:, None] + (rim * diff)[:, None] * np.array([0.55, 0.5, 0.45])
    region = img[y0:y1, x0:x1]
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


def draw_earth(img, cam, C, r, t):
    C = np.asarray(C, float)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    cx, cy, _ = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
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
    loc = rot_y(rot_x(n, math.radians(16)), -1.72 + 0.03 * t)
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


# ---------------- partículas (eyección, estela) ----------------
def splat(img, cam, P, col, size=1.0):
    """Suma puntos luminosos HDR (P: Nx3, col: Nx3) con un núcleo pequeño + halo a 1/4 de resolución."""
    if len(P) == 0:
        return
    x, y, z = cam.proj(P)
    ok = (z > 0.5) & (x > -20) & (x < W + 20) & (y > -20) & (y < H + 20)
    x, y, z, c = x[ok], y[ok], z[ok], col[ok]
    if len(x) == 0:
        return
    small = np.zeros((H // 4, W // 4, 3), np.float32)
    xi = np.clip((x / 4).astype(int), 0, W // 4 - 1); yi = np.clip((y / 4).astype(int), 0, H // 4 - 1)
    np.add.at(small, (yi, xi), c * size)
    small = gaussian_filter(small, (1.4, 1.4, 0))
    img += ndzoom(small, (4, 4, 1), order=1)[:H, :W]
    xf = np.clip(x.astype(int), 0, W - 1); yf = np.clip(y.astype(int), 0, H - 1)
    np.add.at(img, (yf, xf), c * 0.35)


def ejecta(rng_seed, n, origin, normal, t_since, spread=0.55, vmax=1.0, scale=60.0):
    if t_since <= 0:
        return np.zeros((0, 3)), np.zeros((0, 3))
    rng = np.random.default_rng(rng_seed)
    normal = np.asarray(normal, float); normal /= np.linalg.norm(normal)
    a = np.cross(normal, [0, 1, 0]);
    if np.linalg.norm(a) < 1e-3:
        a = np.cross(normal, [1, 0, 0])
    a /= np.linalg.norm(a); b = np.cross(normal, a)
    th = rng.random(n) * 2 * np.pi
    cone = spread * np.sqrt(rng.random(n))
    dirs = (np.cos(cone)[:, None] * normal + np.sin(cone)[:, None] * (np.cos(th)[:, None] * a + np.sin(th)[:, None] * b))
    v = vmax * (0.15 + rng.random(n) ** 2.2)
    tt = t_since
    dist = scale * v * (1 - np.exp(-tt / 1.6)) * 1.6
    P = np.asarray(origin) + dirs * dist[:, None]
    fade_ = np.exp(-tt / 3.5) * (0.6 + 0.4 * rng.random(n))
    hot = np.exp(-tt / 0.35)
    col = (np.array([0.55, 0.50, 0.44]) * (1 - hot)[..., None] + np.array([3.0, 2.2, 1.2]) * hot) * fade_[:, None] * 0.55
    return P, np.broadcast_to(col, (n, 3)) if col.ndim == 1 else col


def bloom(img):
    small = img[::4, ::4]
    br = np.clip(small - 0.85, 0, None)
    g = gaussian_filter(br, (5, 5, 0)) * 0.55 + gaussian_filter(br, (22, 22, 0)) * 0.8 + gaussian_filter(br, (60, 60, 0)) * 0.45
    return img + ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)


# ---------------- naves (cajas 3D dibujadas como polígonos) ----------------
def box_faces(center, half, R):
    hx, hy, hz = half
    V = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    V = V @ R.T + center
    F = [((0, 1, 3, 2), (-1, 0, 0)), ((4, 6, 7, 5), (1, 0, 0)), ((0, 4, 5, 1), (0, -1, 0)),
         ((2, 3, 7, 6), (0, 1, 0)), ((0, 2, 6, 4), (0, 0, -1)), ((1, 5, 7, 3), (0, 0, 1))]
    return V, [(idx, R @ np.array(nr, float)) for idx, nr in F]


def rotm(yaw, pitch=0.0, roll=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch); cr, sr = math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def draw_boxes(layer, cam, boxes, alpha=1.0):
    """boxes: lista de (centro, medias, R, color_rgb). Ordena caras por profundidad."""
    polys = []
    for c, half, R, col in boxes:
        V, F = box_faces(np.asarray(c, float), half, R)
        x, y, z = cam.proj(V)
        if (z <= 0.05).any():
            continue
        for idx, nr in F:
            ctr = V[list(idx)].mean(0)
            if (ctr - cam.O) @ nr >= 0:
                continue
            lam = 0.25 + 0.95 * max(0.0, float(nr @ LIGHT))
            shade = tuple(int(min(255, ch * lam)) for ch in col)
            polys.append((float(np.linalg.norm(ctr - cam.O)), [(float(x[i]), float(y[i])) for i in idx], shade))
    polys.sort(key=lambda p: -p[0])
    d = ImageDraw.Draw(layer)
    A = int(255 * alpha)
    for _, pts, shade in polys:
        d.polygon(pts, fill=shade + (A,), outline=(20, 24, 34, A))


def dart_boxes(pos, R, s):
    gold = (214, 170, 72); panel = (40, 70, 140); grey = (190, 190, 200)
    out = [(pos, (0.6 * s, 0.6 * s, 0.6 * s), R, gold)]
    for side in (-1, 1):
        off = R @ np.array([side * 2.4 * s, 0, 0])
        out.append((pos + off, (1.6 * s, 0.05 * s, 0.55 * s), R, panel))
    out.append((pos + R @ np.array([0, 0.75 * s, 0]), (0.25 * s, 0.15 * s, 0.25 * s), R, grey))
    return out


def hera_boxes(pos, R, s):
    body = (225, 228, 235); panel = (36, 64, 130); gold = (214, 170, 72)
    out = [(pos, (0.8 * s, 0.75 * s, 0.75 * s), R, body),
           (pos + R @ np.array([0, 0, 0.8 * s]), (0.6 * s, 0.55 * s, 0.06 * s), R, gold)]
    for side in (-1, 1):
        for k in (1, 2):
            off = R @ np.array([side * (0.8 + 0.95 * k - 0.4) * s, 0, 0])
            out.append((pos + off, (0.45 * s, 0.04 * s, 0.6 * s), R, panel))
    out.append((pos + R @ np.array([0, 1.0 * s, 0]), (0.45 * s, 0.2 * s, 0.45 * s), R, (200, 200, 210)))
    return out


def cubesat_boxes(pos, R, s, col):
    return [(pos, (0.25 * s, 0.18 * s, 0.35 * s), R, col),
            (pos + R @ np.array([0.55 * s, 0, 0]), (0.3 * s, 0.02 * s, 0.3 * s), R, (36, 64, 130)),
            (pos + R @ np.array([-0.55 * s, 0, 0]), (0.3 * s, 0.02 * s, 0.3 * s), R, (36, 64, 130))]


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
P_ = lambda sid, k: SEG[sid]["parts"][k]
H1 = SEG["hook1"]; H2 = SEG["hook2"]
DA0 = SEG["dart"]["t0"]; DA1 = SEG["dart"]["t1"]
OR0 = SEG["orbita"]["t0"]; GO0 = SEG["golpe"]["t0"]; GO_P2 = P_("golpe", 1)[0]
HE0 = SEG["hera"]["t0"]; MI0 = SEG["mision"]["t0"]; MI1 = SEG["mision"]["t1"]
CI0 = SEG["cierre"]["t0"]; CI_P2 = P_("cierre", 1)[0]; CI1 = SEG["cierre"]["t1"]
TI = H1["t0"] + (H1["t1"] - H1["t0"]) * 0.80        # choque del gancho (en "a propósito")
TI2 = DA1 - 0.35                                      # choque de la repetición
CARD = CI1 + 0.15
FL = [DA0 - 0.2, OR0 - 0.2, HE0 - 0.2, MI0 - 0.2, CI0 - 0.2]

# Dimorphos (radio ~80 m) y Didymos (radio ~390 m), unidades: metros
DIM_S = (88.0, 62.0, 76.0)
DID_S = (395.0, 300.0, 395.0)
CRATER_DIR = np.array([0.15, 0.10, 1.0]); CRATER_DIR /= np.linalg.norm(CRATER_DIR)


def dimorphos(c, t, crater_t=None, spin=0.05, a0=0.0):
    return dict(c=c, s=DIM_S, g=G_DIM, h=H_DIM, alb=A_DIM, spin=spin, a0=a0, bump=0.30,
                crater=(CRATER_DIR, crater_t) if crater_t is not None else None)


def didymos(c, spin=0.12):
    return dict(c=c, s=DID_S, g=G_DID, h=H_DID, alb=A_DID, spin=spin, a0=0.4, bump=0.22, tint=(1.0, 0.95, 0.88))


def scene(t):
    if t < FL[0]:
        return "impacto"
    if t < FL[1]:
        return "dart"
    if t < FL[2]:
        return "orbita"
    if t < FL[3]:
        return "hera"
    if t < FL[4]:
        return "mision"
    return "tierra"


# ---------------- subtítulos y textos ----------------
FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); RED = (255, 90, 70); ORANGE = (255, 160, 70)
HL_WORDS = {"nasa", "estrelló", "asteroide", "propósito", "ver", "dart", "dimorphos", "km/h", "didymos", "h", "min",
            "media", "hora", "vez", "movemos", "hera", "europea", "maleta", "cráter", "pesarán", "interior",
            "empujar", "tierra", "humanidad", "defender", "más"}


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
    core = w.strip(".,:…?¿!¡()").lower()
    return any(ch.isdigit() for ch in core) or core in HL_WORDS or (core.isupper() and len(core) > 2) or w.strip(".,:…?¿!¡()").isupper()


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


def marker(d, x, y, t, col, A, r0=40, label=None, side=1, lsize=50):
    rr = r0 + 5 * math.sin(t * 7)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (A,), width=6)
    if label:
        lx = x + side * (rr + 30)
        d.line([x + side * rr, y, lx, y], fill=col + (A,), width=5)
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


# ---------------- escenas ----------------
def impact_flash(img, cam, P, t_since, k=1.0):
    if t_since < 0 or t_since > 2.5:
        return
    x, y, z = cam.proj(P)
    if z[0] <= 0:
        return
    s = math.exp(-t_since / 0.25) * 7 * k + math.exp(-t_since / 1.0) * 0.6 * k
    small = np.zeros((H // 4, W // 4, 3), np.float32)
    xi, yi = int(x[0] / 4), int(y[0] / 4)
    if 0 <= xi < W // 4 and 0 <= yi < H // 4:
        small[yi, xi] = np.array([1.0, 0.85, 0.6]) * s * 900
        g = gaussian_filter(small, (3, 3, 0)) + gaussian_filter(small, (14, 14, 0)) * 0.6
        img += ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def sc_impacto(img, layer, t):
    """Gancho: vamos detrás de DART hasta el choque; después, la nube de eyección."""
    C = np.zeros(3)
    surf = CRATER_DIR * np.array(DIM_S) * 0.97
    s = min(t / TI, 1.0)
    # DART llega desde +z (por donde mira la cámara)
    dpos = surf + CRATER_DIR * (2600 * (1 - s) ** 1.6)
    if t < TI:
        cpos = dpos + np.array([8, 5, 0]) + CRATER_DIR * (70 + 380 * (1 - s))
        cam = Cam(cpos, C + np.array([0, 0, 0]))
    else:
        k = ease_out((t - TI) / 3.0)
        cpos = surf + CRATER_DIR * 70 + np.array([8, 5, 0]) + lerp([0, 0, 0], [380, 160, 520], k)
        cam = Cam(cpos, C)
    draw_ellipsoid(img, cam, dimorphos(C, t, TI, 0.05, -0.05 * TI), t)
    if t >= TI:
        P, col = ejecta(5, 2600, surf, CRATER_DIR + np.array([0.1, 0.25, 0]), t - TI, 0.75, 1.0, 70.0)
        splat(img, cam, P, col, 1.6)
        impact_flash(img, cam, surf + CRATER_DIR * 3, t - TI, 1.2)
    return cam, (dpos if t < TI else None)


def sc_dart(img, layer, t):
    """Repetición de lado: DART entra por la derecha a velocidad constante y choca."""
    C = np.zeros(3)
    k = (t - (DA0 - 0.2)) / (FL[1] - DA0 + 0.2)
    cam = Cam(np.array([-1150.0, 160.0, 140.0]) + np.array([0, 0, 40.0]) * k, np.array([0.0, -40.0, 115.0]))
    draw_ellipsoid(img, cam, dimorphos(C, t, TI2, 0.05, -0.05 * TI2), t)
    surf = CRATER_DIR * np.array(DIM_S) * 0.97
    s = (t - (DA0 - 0.2)) / (TI2 - (DA0 - 0.2))
    dpos = None
    if t < TI2:
        dist = 1000 * (1 - s) + 2
        dpos = surf + CRATER_DIR * dist
        trail = dpos[None, :] + np.linspace(0, 1, 160)[:, None] * CRATER_DIR * 220
        col = np.linspace(1, 0, 160)[:, None] ** 2 * np.array([0.9, 1.0, 1.4]) * 0.3
        splat(img, cam, trail, col, 2.0)
    else:
        P, col = ejecta(8, 2400, surf, CRATER_DIR + np.array([0.15, 0.2, 0]), t - TI2, 0.75, 1.0, 70.0)
        splat(img, cam, P, col, 1.6)
        impact_flash(img, cam, surf + CRATER_DIR * 3, t - TI2, 1.0)
    return cam, dpos


ORB_R0 = 1190.0
ORB_R1 = 1190.0 * 0.86        # exagerado para que se vea


def orbit_radius(t):
    return ORB_R0 + (ORB_R1 - ORB_R0) * ease((t - GO0 - 0.1) / 1.6)


def orbit_angle(t):
    return 0.9 + 0.55 * (t - OR0) + 0.25 * max(0.0, t - GO0)


def sc_orbita(img, layer, t):
    k = (t - (OR0 - 0.2)) / (HE0 - OR0)
    az = 0.35 + 0.25 * k
    cpos = np.array([math.sin(az) * 3600, 2300 - 300 * k, math.cos(az) * 3600])
    cam = Cam(cpos, np.array([0, -150.0, 0]))
    r = orbit_radius(t); a = orbit_angle(t)
    pd = np.array([math.cos(a) * r, 0, -math.sin(a) * r])
    bodies = [(didymos(np.zeros(3)), 0), (dimorphos(pd, t, 0.0, 0.0, -a), 1)]
    bodies.sort(key=lambda b: -np.linalg.norm(np.asarray(b[0]["c"]) - cam.O))
    for b, _ in bodies:
        draw_ellipsoid(img, cam, b, t)
    return cam, pd


def hera_pos(t):
    k = ease_out((t - (HE0 - 0.2)) / (MI0 - HE0 + 0.4))
    return np.array([-2600.0, 700.0, 3600.0]) * (1 - k) + np.array([-1300.0, 500.0, 2900.0]) * k


def sc_hera(img, layer, t):
    hp = hera_pos(t)
    k = (t - (HE0 - 0.2)) / (MI0 - HE0)
    back = hp / np.linalg.norm(hp)
    side = np.cross([0.0, 1.0, 0.0], back); side /= np.linalg.norm(side)
    cpos = hp + back * (190 + 40 * k) + np.array([0.0, 35.0, 0.0])
    cam = Cam(cpos, cpos - back * 1000 + np.array([0.0, -105.0, 0.0]))
    a = orbit_angle(t)
    pd = np.array([math.cos(a) * ORB_R1, 0, -math.sin(a) * ORB_R1])
    bodies = [didymos(np.zeros(3)), dimorphos(pd, t, 0.0, 0.0, -a)]
    bodies.sort(key=lambda b: -np.linalg.norm(np.asarray(b["c"]) - cam.O))
    for b in bodies:
        draw_ellipsoid(img, cam, b, t)
    return cam, hp


def sc_mision(img, layer, t):
    C = np.zeros(3)
    k = (t - (MI0 - 0.2)) / (CI0 - MI0)
    az = -0.25 + 0.5 * k
    cpos = np.array([math.sin(az) * 420, 90.0, math.cos(az) * 420])
    cam = Cam(cpos, np.array([0.0, -10.0, 0.0]))
    draw_ellipsoid(img, cam, dimorphos(C, t, 0.0, 0.0, 0.0), t)
    return cam, None


EARTH_R = 6371.0


def asteroid_path(s, deflect):
    """Trayectoria del asteroide hacia la Tierra (s de 0 a 1); deflect de 0 a 1 la curva hacia afuera."""
    p0 = np.array([26000.0, 15000.0, -9000.0]); p1 = np.array([0.0, 0.0, 0.0])
    base = p0 * (1 - s) + p1 * s
    side = np.array([-0.3, 1.0, 0.25]); side /= np.linalg.norm(side)
    return base + side * deflect * EARTH_R * 2.6 * max(0.0, s - 0.35) ** 1.5 / 0.65 ** 1.5


def sc_tierra(img, layer, t):
    k = (t - (CI0 - 0.2)) / (END - CI0)
    cpos = np.array([0.0, 2500.0, 55500.0]) * (1 + 0.08 * ease(k))
    cam = Cam(cpos, np.array([0.0, 2500.0, 0.0]) * (1 + 0.08 * ease(k)) + np.array([0.0, 11400.0, 0.0]))
    draw_earth(img, cam, np.zeros(3), EARTH_R, t)
    return cam, None


SCENES = {"impacto": sc_impacto, "dart": sc_dart, "orbita": sc_orbita, "hera": sc_hera, "mision": sc_mision, "tierra": sc_tierra}

KICK = None  # tiempo del empujón (se calcula con la palabra "empujar")


def push_time():
    p = P_("cierre", 0)
    return p[0] + (p[1] - p[0]) * 0.45


def deflect_amount(t):
    return ease((t - push_time()) / 1.4)


def ast_s(t):
    return min(0.82, 0.22 + 0.62 * (t - (CI0 - 0.2)) / (CI_P2 - CI0 + 0.2))


# ---------------- overlays por escena ----------------
def overlays(frame_u8, t, name, cam, extra):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if name == "impacto":
        if extra is not None:
            R = rotm(math.atan2(CRATER_DIR[0], CRATER_DIR[2]) + math.pi, 0.0, 0.3 + 0.2 * t)
            draw_boxes(layer, cam, dart_boxes(extra, R, 2.2))
        draw_label(layer, t, -1, TI - 0.05, "26 SEP 2022", ["NASA · misión DART"], YELLOW, 120)
        draw_label(layer, t, H2["t0"] - 0.1, FL[0] + 0.05, "¿QUÉ LE HIZO?", ["Hera lo verá este mes"], WHITE, 112)
    elif name == "dart":
        if extra is not None:
            R = rotm(math.atan2(CRATER_DIR[0], CRATER_DIR[2]) + math.pi, 0.05, 0.4)
            draw_boxes(layer, cam, dart_boxes(extra, R, 4.0))
            x, y, z = cam.proj(extra)
            if 0 < x[0] < W and z[0] > 0:
                marker(d, float(x[0]), float(y[0]), t, YELLOW, int(255 * fade(t, DA0, TI2 - 0.05, 0.2)), 46, "DART", -1 if x[0] > W / 2 else 1)
        al = fade(t, DA0 + 0.2, FL[1] + 0.05)
        if al > 0:
            A = int(255 * al)
            txt(d, (W / 2, 380), "+20,000 KM/H", 118, YELLOW, A)
            txt(d, (W / 2, 470), "≈ 6 km por segundo", 54, CYAN, A, "Inter-ExtraBold.otf", 7)
        al = fade(t, DA0 + 1.6, FL[1] + 0.05)
        if al > 0:
            x, y, z = cam.proj(np.zeros(3))
            A = int(255 * al)
            xl, _, _ = cam.proj(-cam.r * 80); xr, _, _ = cam.proj(cam.r * 80)
            yy = float(y[0]) + (float(xr[0]) - float(xl[0])) * 0.62
            rx = (float(xr[0]) - float(xl[0])) / 2
            W2 = float(x[0])
            d.line([W2 - rx, yy, W2 + rx, yy], fill=CYAN + (A,), width=6)
            d.line([W2 - rx, yy - 16, W2 - rx, yy + 16], fill=CYAN + (A,), width=6)
            d.line([W2 + rx, yy - 16, W2 + rx, yy + 16], fill=CYAN + (A,), width=6)
            txt(d, (max(W2, 260), yy + 52), "DIMORPHOS · 160 m", 50, WHITE, A, "Inter-Black.otf", 7)
    elif name == "orbita":
        # anillos de órbita
        for rr, col, al in ((ORB_R0, CYAN, 1.0 if t < GO0 else 0.45), (orbit_radius(t), YELLOW, fade(t, GO0, 99, 0.3))):
            if al <= 0:
                continue
            ang = np.linspace(0, 2 * np.pi, 220)
            P = np.stack([np.cos(ang) * rr, np.zeros_like(ang), -np.sin(ang) * rr], -1)
            x, y, z = cam.proj(P)
            pts = list(zip(x.tolist(), y.tolist()))
            A = int(235 * al)
            if col == CYAN and t >= GO0:
                for i in range(0, len(pts) - 1, 6):
                    d.line(pts[i:i + 4], fill=col + (A,), width=5)
            else:
                d.line(pts + [pts[0]], fill=col + (A,), width=6)
        x, y, _ = cam.proj(np.zeros(3))
        al = fade(t, OR0 + 0.3, GO0 + 0.4)
        if al > 0:
            marker(d, float(x[0]), float(y[0]), t, CYAN, int(255 * al), 70, "DIDYMOS", -1, 46)
        xd, yd, _ = cam.proj(extra)
        al = fade(t, OR0 + 0.3, GO_P2)
        if al > 0:
            marker(d, float(xd[0]), float(yd[0]), t, YELLOW, int(255 * al), 34, "DIMORPHOS", 1 if xd[0] < W * 0.6 else -1, 42)
        # reloj de la vuelta
        al = fade(t, OR0 + 0.5, GO_P2 - 0.05)
        if al > 0:
            A = int(255 * al)
            after = ease((t - GO0 - 0.3) / 0.8)
            if after < 0.5:
                txt(d, (W / 2, 380), "11 h 55 min", 120, WHITE, int(A * (1 - 2 * after)))
                txt(d, (W / 2, 475), "por cada vuelta", 54, CYAN, int(A * (1 - 2 * after)), "Inter-ExtraBold.otf", 7)
            else:
                A2 = int(A * (2 * after - 1))
                txt(d, (W / 2, 380), "11 h 23 min", 120, YELLOW, A2)
                txt(d, (W / 2, 475), "−32 minutos tras el choque", 54, CYAN, A2, "Inter-ExtraBold.otf", 7)
        al = fade(t, GO0 + 0.4, FL[2] + 0.05)
        if al > 0:
            txt(d, (W / 2, 1720), "órbita exagerada para que se vea", 34, (200, 210, 230), int(200 * al), "Inter-ExtraBold.otf", 5)
        draw_label(layer, t, GO_P2 - 0.05, FL[2] + 0.05, "1.ª VEZ", ["que la humanidad mueve", "un objeto del espacio"], YELLOW, 140)
    elif name == "hera":
        hp = extra
        R = rotm(0.55 + 0.05 * t, 0.15, 0.1)
        boxes = hera_boxes(hp, R, 9.0)
        sep = ease((t - (HE0 + 2.0)) / 1.4)
        offs = [(-cam.r * 26 + cam.u * 12 + cam.f * 30, "MILANI", (230, 180, 90)), (cam.r * 26 - cam.u * 4 + cam.f * 40, "JUVENTAS", (190, 220, 240))]
        if sep > 0:
            for i, (off, _, col) in enumerate(offs):
                boxes += cubesat_boxes(hp + off * sep, rotm(0.3 + (1 - 2 * i) * t, 0.4), 6.0, col)
        draw_boxes(layer, cam, boxes)
        draw_label(layer, t, HE0 - 0.05, FL[3] + 0.05, "HERA", ["Agencia Espacial Europea", "llega en noviembre de 2026"], CYAN, 140)
        if sep > 0.3:
            A = int(255 * fade(t, HE0 + 2.5, FL[3] + 0.05, 0.2))
            for off, name_, _ in offs:
                x, y, z = cam.proj(hp + off * sep)
                marker(d, float(x[0]), float(y[0]), t, YELLOW, A, 30, None)
                txt(d, (float(x[0]), float(y[0]) + 68), name_, 40, WHITE, A, "Inter-Black.otf", 6)
    elif name == "mision":
        # cráter, masa e interior (radar)
        cr = CRATER_DIR * np.array(DIM_S)
        x, y, z = cam.proj(cr)
        third = (MI1 - MI0) / 3
        A1 = int(255 * fade(t, MI0, FL[4] + 0.05, 0.2))
        if A1:
            marker(d, float(x[0]), float(y[0]), t, YELLOW, A1, 58, None)
        xc, yc, _ = cam.proj(np.zeros(3))
        rk = (t - (MI0 + 2 * third)) / 1.6
        if rk > 0:
            for i in range(4):
                ph = (rk * 1.4 + i * 0.25) % 1.0
                rr = 60 + 260 * ph
                A = int(200 * (1 - ph) * fade(t, MI0 + 2 * third, FL[4] + 0.05, 0.2))
                d.arc([xc[0] - rr, yc[0] - rr, xc[0] + rr, yc[0] + rr], 200, 340, fill=CYAN + (A,), width=6)
        chips = [("CRÁTER", MI0), ("MASA", MI0 + third), ("INTERIOR", MI0 + 2 * third)]
        for i, (lab, t0) in enumerate(chips):
            al = fade(t, t0, FL[4] + 0.05, 0.2)
            if al <= 0:
                continue
            A = int(255 * al)
            yy = 330 + i * 110
            pop = ease_out((t - t0) / 0.25)
            f = font("Inter-Black.otf", int(72 * (0.85 + 0.15 * pop)))
            tw = d.textlength(lab, font=f)
            d.rounded_rectangle([W / 2 - tw / 2 - 30, yy - 50, W / 2 + tw / 2 + 30, yy + 50], 24, fill=(8, 14, 30, int(200 * al)), outline=(YELLOW if i == 0 else CYAN) + (A,), width=5)
            d.text((W / 2, yy), lab, font=f, fill=WHITE + (A,), anchor="mm")
    elif name == "tierra":
        dfl = deflect_amount(t)
        ex, ey, _ = cam.proj(np.zeros(3)); ex, ey = float(ex[0]), float(ey[0])
        A0 = np.array([W + 60.0, 450.0]); E = np.array([ex, ey])
        dirv = (E - A0) / np.linalg.norm(E - A0)
        perp = np.array([dirv[1], -dirv[0]])
        if perp[1] > 0:
            perp = -perp
        Lp = np.linalg.norm(E - A0)
        def path(s, dv):
            return A0 + (E - A0) * s + perp * dv * Lp * 0.9 * max(0.0, s - 0.4) ** 1.5
        ss = np.linspace(0.0, 1.0, 120)
        Ared = int(230 * (1 - 0.6 * dfl))
        pts = [tuple(path(s, 0.0)) for s in ss]
        for i in range(0, len(pts) - 1, 5):
            d.line(pts[i:i + 3], fill=RED + (Ared,), width=6)
        if dfl > 0:
            s2 = np.linspace(0.0, 1.5, 180)
            n = int(len(s2) * min(1.0, dfl * 1.2))
            d.line([tuple(path(s, 1.0)) for s in s2][:max(n, 2)], fill=YELLOW + (int(255 * dfl),), width=7)
        s_now = 0.12 + 0.38 * (t - (CI0 - 0.2)) / (push_time() - CI0 + 0.2) if t < push_time() else 0.50 + 0.11 * (t - push_time())
        xa, ya = path(min(s_now, 1.6), dfl)
        rr0 = 24
        d.ellipse([xa - 46, ya - 46, xa + 46, ya + 46], fill=(255, 200, 120, 40))
        d.ellipse([xa - rr0, ya - rr0 * 0.8, xa + rr0, ya + rr0 * 0.8], fill=(170, 160, 150, 255), outline=(60, 55, 50, 255), width=3)
        tp = push_time()
        if tp - 0.4 < t < tp + 0.9:
            A = int(255 * fade(t, tp - 0.4, tp + 0.9, 0.15))
            rr = 26 + 50 * ease_out((t - tp + 0.4) / 1.0)
            d.ellipse([xa - rr, ya - rr, xa + rr, ya + rr], outline=YELLOW + (A,), width=5)
        al = fade(t, CI0 + 0.3, CI_P2 + 0.1)
        if al > 0:
            A = int(255 * al)
            txt(d, (W / 2, 380), "¿CUÁNTO EMPUJAR?", 92, WHITE, A)
            txt(d, (W / 2, 470), "para desviar un asteroide", 54, CYAN, A, "Inter-ExtraBold.otf", 7)
        draw_label(layer, t, CI_P2 - 0.05, CARD + 0.1, "DEFENSA", [], WHITE, 150)
        al = fade(t, CI_P2 - 0.05, CARD + 0.1)
        if al > 0:
            txt(d, (W / 2, 515), "PLANETARIA", 110, YELLOW, int(255 * al))
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
    cam, extra = SCENES[name](img, None, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, name, cam, extra)


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
        print("frames", NFRAMES, "TI", round(TI, 2), "TI2", round(TI2, 2), "flashes", [round(x, 2) for x in FL], "card", round(CARD, 2))
