"""Flash Datos · video 11: las estrellas fugaces no se queman, se derriten y revientan.

Escena nueva: roca espacial con relieve propio (esfera deformada con ruido y cráteres, trazada con
raymarching), capa de choque de aire incandescente, estela, gotas de roca fundida que se desprenden,
fragmentación en pedazos con destellos (el último, rojo), vuelo oscuro de los meteoritos con costra
de fusión, y cielos nocturnos con lluvias de meteoros saliendo de su radiante (Táuridas y Leónidas).

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



# ---------------- cielo nocturno con horizonte ----------------
def make_sky(seed, top, horizon, ground_y=1560, stars=1.0):
    rng = np.random.default_rng(seed)
    yy = np.linspace(0, 1, H)[:, None, None]
    sky = lin(top) * (1 - yy ** 1.6) + lin(horizon) * yy ** 1.6
    sky = np.broadcast_to(sky, (H, W, 3)).astype(np.float32).copy()
    sky += BG * stars * np.clip(1.2 - np.linspace(0, 1, H)[:, None, None] * 1.1, 0, 1)
    # montañas en silueta (perfil 1D de ruido)
    xs_ = np.arange(W) / W * 6.0
    prof = fbm(xs_, np.full_like(xs_, 1.7), np.full_like(xs_, seed * 0.37), 5, seed=seed)
    prof = (prof - prof.min()) / (prof.max() - prof.min() + 1e-9)
    gy = ground_y - prof * 230
    rows = np.arange(H)[:, None]
    m = np.clip(rows - gy[None, :] + 0.5, 0, 1)[..., None]
    sky = sky * (1 - m) + lin((0.015, 0.018, 0.03)) * m
    return sky


SKY_N = make_sky(21, (0.02, 0.03, 0.09), (0.10, 0.08, 0.20))
SKY_T = make_sky(33, (0.015, 0.025, 0.08), (0.16, 0.07, 0.12))
SKY_L = make_sky(44, (0.01, 0.02, 0.07), (0.05, 0.10, 0.18))
yy_ = np.linspace(0, 1, H)[:, None, None]
SKY_DAY = (lin((0.16, 0.30, 0.58)) * (1 - yy_) + lin((0.62, 0.72, 0.85)) * yy_).astype(np.float32) * np.ones((1, W, 3), np.float32)
SKY_HI = (lin((0.004, 0.006, 0.02)) * (1 - yy_ ** 1.3) + lin((0.05, 0.07, 0.20)) * yy_ ** 1.3).astype(np.float32) + BG * 0.6


def streak(img, x0, y0, x1, y1, head, tail, col, width=2.5, bright=1.0):
    """Meteoro: cabeza en la fracción 'head' del trayecto, cola de longitud 'tail' (fracción)."""
    hx, hy = x0 + (x1 - x0) * head, y0 + (y1 - y0) * head
    t0 = max(0.0, head - tail)
    tx, ty = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
    L = math.hypot(hx - tx, hy - ty)
    n = max(2, int(L / (width * 1.2)))
    for i in range(n):
        q = i / (n - 1)
        glow(img, tx + (hx - tx) * q, ty + (hy - ty) * q, col, width * (0.5 + 0.6 * q), bright * q ** 1.5 * 0.6)
    glow(img, hx, hy, col, width * 2.2, bright * 0.9)


class Meteor:
    def __init__(self, rng, t0, rad, dur, length, col, width, bright, d0=(80, 520)):
        for _ in range(30):
            ang = rng.uniform(0, 2 * np.pi)
            dist = rng.uniform(*d0)
            ex = rad[0] + math.cos(ang) * (dist + length * 0.7); ey = rad[1] + math.sin(ang) * (dist + length * 0.7)
            if 60 < ex < W - 60 and 300 < ey < 1500:
                break
        self.t0, self.dur = t0, dur
        self.x0 = rad[0] + math.cos(ang) * dist; self.y0 = rad[1] + math.sin(ang) * dist
        self.x1 = self.x0 + math.cos(ang) * length; self.y1 = self.y0 + math.sin(ang) * length
        self.col, self.width, self.bright = col, width, bright

    def draw(self, img, t):
        u = (t - self.t0) / self.dur
        if u < 0 or u > 1.25:
            return
        fade_ = 1.0 if u <= 1 else max(0.0, 1 - (u - 1) / 0.25)
        flare = 1 + 1.6 * math.exp(-((u - 0.82) / 0.07) ** 2)
        streak(img, self.x0, self.y0, self.x1, self.y1, min(u, 1.0), 0.45, self.col, self.width, self.bright * fade_ * flare * min(1, u * 5))


def meteor_list(seed, t_a, t_b, rate, rad, dur, length, col, width, bright, d0=(80, 520)):
    rng = np.random.default_rng(seed)
    out = []; t = t_a + rng.uniform(0, 1 / rate)
    while t < t_b:
        out.append(Meteor(rng, t, rad, rng.uniform(*dur), rng.uniform(*length), col, rng.uniform(*width), rng.uniform(*bright), d0))
        t += rng.exponential(1 / rate)
    return out


# ---------------- roca: esfera deformada con raymarching ----------------
def make_rock_tex(seed, th=128, tw=256):
    lat = (0.5 - (np.arange(th) + 0.5) / th) * np.pi
    lon = ((np.arange(tw) + 0.5) / tw * 2 - 1) * np.pi
    LO, LA = np.meshgrid(lon, lat)
    x = np.cos(LA) * np.sin(LO); y = np.sin(LA); z = np.cos(LA) * np.cos(LO)
    h = fbm(x * 1.4 + 5, y * 1.4, z * 1.4, 6, seed=seed)
    h = (h - h.min()) / (h.max() - h.min())
    # cráteres suaves
    rng = np.random.default_rng(seed)
    for _ in range(7):
        c = rng.normal(size=3); c /= np.linalg.norm(c)
        dd = np.arccos(np.clip(x * c[0] + y * c[1] + z * c[2], -1, 1))
        rr = rng.uniform(0.18, 0.4)
        h -= 0.25 * np.exp(-(dd / rr) ** 2) - 0.1 * np.exp(-((dd - rr) / (rr * 0.3)) ** 2)
    h = (h - h.min()) / (h.max() - h.min())
    det = fbm(x * 9 + 2, y * 9, z * 9, 3, seed=seed + 9)
    det = (det - det.min()) / (det.max() - det.min())
    return h.astype(np.float32), det.astype(np.float32)


ROCK_TEX = [make_rock_tex(s) for s in (3, 8, 13, 21)]
ELL = np.array([1.0, 0.80, 0.90])
ROCK_COL = lin((0.40, 0.36, 0.31))
CRUST = lin((0.07, 0.06, 0.055))
FIRE = lin((1.0, 0.42, 0.10))
HOT = lin((1.0, 0.86, 0.60))


def rock_sdf(q, r, tex, amp):
    n = np.linalg.norm(q, axis=-1)
    u = q / np.maximum(n, 1e-9)[..., None]
    la, lo = latlon(u)
    h = sample(tex[0], la, lo)
    e = 1.0 / np.sqrt(((u / ELL) ** 2).sum(-1))
    return n - r * e * (1 + amp * (h * 2 - 1)), h, la, lo


def draw_rock(img, cam, C, r, R, tex, heat=0.0, crust=0.0, mdir=None, amp=0.18, iters=30):
    C = np.asarray(C, float)
    cx, cy, cz = cam.proj(C)
    if cz[0] <= 0:
        return None
    cx, cy = float(cx[0]), float(cy[0])
    dist = float(np.linalg.norm(C - cam.O))
    rb = r * (1 + amp) * 1.02
    rpx = math.tan(math.asin(min(rb / dist, 0.999))) / PIX
    ext = rpx + 3
    x0 = int(max(0, cx - ext)); x1 = int(min(W, cx + ext + 1))
    y0 = int(max(0, cy - ext)); y1 = int(min(H, cy + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return None
    d = cam.dirs(y0, y1, x0, x1).reshape(-1, 3)
    oc = cam.O - C
    b = d @ oc
    disc = b * b - (oc @ oc - rb * rb)
    idx = np.nonzero(disc > 0)[0]
    if len(idx) == 0:
        return None
    sq = np.sqrt(disc[idx])
    t = np.maximum(-b[idx] - sq, 0.0); tmax = -b[idx] + sq
    dd = d[idx]
    O_l = oc @ R           # origen en coordenadas locales de la roca
    dl = dd @ R
    fmin = np.full(len(idx), 1e9)
    act = np.arange(len(idx))
    hit = np.zeros(len(idx), bool)
    for _ in range(iters):
        if len(act) == 0:
            break
        q = O_l + t[act, None] * dl[act]
        f, _, _, _ = rock_sdf(q, r, tex, amp)
        fmin[act] = np.minimum(fmin[act], f / np.maximum(t[act], 1e-3))
        done = f < 0.002 * r
        hit[act[done]] = True
        t[act] += np.maximum(f, 0.002 * r) * 0.75
        keep = (~done) & (t[act] < tmax[act])
        act = act[keep]
    pixang = PIX
    alpha = np.where(hit, 1.0, np.clip(1 - fmin / (pixang * 1.2), 0, 1))
    alpha[t > tmax + 1e-6] *= (fmin[t > tmax + 1e-6] < pixang * 1.2)
    sel = alpha > 0
    if not sel.any():
        return (cx, cy, rpx)
    q = O_l + t[sel, None] * dl[sel]
    f0, h, la, lo = rock_sdf(q, r, tex, amp)
    eps = 0.006 * r
    nl = np.stack([rock_sdf(q + np.array(e_) * eps, r, tex, amp)[0] - f0 for e_ in ((1, 0, 0), (0, 1, 0), (0, 0, 1))], -1)
    nl /= np.linalg.norm(nl, axis=-1, keepdims=True) + 1e-12
    n = nl @ R.T           # normal en mundo
    V = -dd[sel]
    det = sample(tex[1], la, lo)
    alb = ROCK_COL * (0.55 + 0.7 * h[:, None]) * (0.75 + 0.5 * det[:, None])
    alb = alb * (1 - crust) + CRUST * (0.8 + 0.4 * det[:, None]) * crust
    ndl = np.clip(n @ LIGHT, 0, 1)
    amb = 0.04 + 0.05 * np.clip(n[:, 1], 0, 1)
    col = alb * (2.2 * ndl + amb)[:, None]
    Rr = 2 * (n @ LIGHT)[:, None] * n - LIGHT
    col += (np.clip((Rr * V).sum(-1), 0, 1) ** (12 + 30 * crust) * (0.05 + 0.35 * crust))[:, None] * np.array([1.0, 0.97, 0.9])
    if heat > 0 and mdir is not None:
        front = np.clip(n @ mdir, 0, 1)
        lava = np.clip((det - 0.35) * 2.2, 0, 1)
        em = heat * (front ** 1.6 * 1.1 + 0.05 * heat) * (0.4 + 1.0 * lava)
        col = col * (1 - 0.6 * heat) + FIRE * em[:, None] + HOT * (heat ** 2 * front ** 6 * 1.2)[:, None]
        # borde incandescente (capa de material fundido)
        mu = np.clip((n * V).sum(-1), 0, 1)
        col += FIRE * ((1 - mu) ** 3 * heat * 0.9 * (0.3 + front))[:, None]
    region = img[y0:y1, x0:x1].reshape(-1, 3)
    a = alpha[sel][:, None]
    ii = idx[sel]
    region[ii] = region[ii] * (1 - a) + col * a
    img[y0:y1, x0:x1] = region.reshape(y1 - y0, x1 - x0, 3)
    return (cx, cy, rpx)


def basis(m):
    m = np.asarray(m, float); m /= np.linalg.norm(m)
    a = np.cross(m, [0, 1, 0]); a /= np.linalg.norm(a)
    b = np.cross(m, a)
    return m, a, b


def shock(img, cam, C, r, mdir, inten, t):
    """Capa de choque: aire comprimido que brilla delante de la roca."""
    if inten <= 0:
        return
    m, a, b = basis(mdir)
    C = np.asarray(C, float)
    sc = cam.proj(C)
    dist = float(np.linalg.norm(C - cam.O))
    px = r / dist / PIX     # radio de la roca en píxeles (aprox.)
    for s in np.linspace(0, 1.7, 12):
        nang = 6 + int(s * 22)
        for k in range(nang):
            ang = 2 * np.pi * k / nang + s * 1.3 + t * 0.7
            P = C + m * r * (1.28 - 0.42 * s * s) + (math.cos(ang) * a + math.sin(ang) * b) * r * 1.22 * s
            x, y, z = cam.proj(P)
            if z[0] <= 0:
                continue
            fl = 0.85 + 0.15 * math.sin(t * 31 + k * 2.1 + s * 7)
            w = math.exp(-s * 1.4) * inten * fl
            glow(img, float(x[0]), float(y[0]), (1.6, 0.85, 0.35), max(4.0, px * 0.22), w * 0.022)
    x, y, _ = cam.proj(C + m * r * 1.1)
    glow(img, float(x[0]), float(y[0]), (1.4, 1.0, 0.7), px * 0.6, inten * 0.12)


def wake(img, cam, C, r, mdir, inten, t, length=9.0):
    if inten <= 0:
        return
    m, a, b = basis(mdir)
    dist = float(np.linalg.norm(np.asarray(C) - cam.O))
    px = r / dist / PIX
    n = 46
    for i in range(n):
        q = (i + 1) / n
        jit = 0.25 * r * q * math.sin(t * 17 + i * 1.7)
        P = np.asarray(C) - m * (r * 0.6 + length * r * q ** 1.25) + a * jit + b * jit * 0.6
        x, y, z = cam.proj(P)
        if z[0] <= 0:
            continue
        col = (1.5, 0.7, 0.25) if q < 0.5 else (0.9, 0.45, 0.35)
        glow(img, float(x[0]), float(y[0]), col, px * (0.35 + 0.9 * q), inten * (1 - q) ** 1.6 * 0.22)


DROP_RNG = np.random.default_rng(77)
DROPS = DROP_RNG.uniform(0, 1, (260, 4))


def droplets(img, cam, C, r, mdir, inten, t, t0):
    if inten <= 0:
        return
    m, a, b = basis(mdir)
    C = np.asarray(C, float)
    for i, (u1, u2, u3, u4) in enumerate(DROPS):
        tb = t0 + u1 * 4.0
        age = (t - tb) % 0.9
        if t < tb:
            continue
        ang = u2 * 2 * np.pi
        side = (math.cos(ang) * a + math.sin(ang) * b) * r * (0.75 + 0.25 * u3)
        P = C + side * (1 + age * 0.8) - m * (age * (3 + 4 * u4) * r) + m * 0.2 * r
        x, y, z = cam.proj(P)
        if z[0] <= 0:
            continue
        life = 1 - age / 0.9
        glow(img, float(x[0]), float(y[0]), (1.8, 0.75, 0.25) if u3 > 0.3 else (1.8, 1.3, 0.8), 2.2 + 2.5 * u4, inten * life * 0.55)


AIR = np.random.default_rng(91).uniform(-1, 1, (180, 3)) * np.array([14, 9, 6])


def air_lines(img, cam, mdir, t, speed=26.0, inten=1.0):
    """Aire que pasa rapidísimo junto a la roca (líneas de velocidad)."""
    m = np.asarray(mdir, float) / np.linalg.norm(mdir)
    lay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lay)
    for i, p in enumerate(AIR):
        s = ((p @ m) - speed * t) % 28 - 14
        P = p - m * (p @ m) + m * s
        P2 = P + m * 1.6
        x0_, y0_, z0 = cam.proj(P); x1_, y1_, z1 = cam.proj(P2)
        if z0[0] <= 0.5 or z1[0] <= 0.5:
            continue
        d.line([float(x0_[0]), float(y0_[0]), float(x1_[0]), float(y1_[0])], fill=int(70 + 60 * (i % 3)), width=2)
    arr = gaussian_filter(np.asarray(lay, np.float32) / 255.0, 1.2)
    img += arr[..., None] * np.array([0.10, 0.14, 0.30], np.float32) * inten

# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
HK0, HK1 = SEG["hook1"]["t0"], SEG["hook1"]["t1"]
ES0, ES1 = SEG["estudio"]["t0"], SEG["estudio"]["t1"]
CH0, CH1 = SEG["choque"]["t0"], SEG["choque"]["t1"]
DE0, DE1 = SEG["derrite"]["t0"], SEG["derrite"]["t1"]
RO0, RO1 = SEG["rompe"]["t0"], SEG["rompe"]["t1"]
CA0, CA1 = SEG["caida"]["t0"], SEG["caida"]["t1"]
TA0, TA1 = SEG["tauridas"]["t0"], SEG["tauridas"]["t1"]
LE0, LE1 = SEG["leonidas"]["t0"], SEG["leonidas"]["t1"]
CI0, CI1 = SEG["cierre"]["t0"], SEG["cierre"]["t1"]
CARD = CI1 + 0.15
FL = [ES0 - 0.2, CH0 - 0.2, CA0 - 0.2, TA0 - 0.2, LE0 - 0.2, CI0 - 0.2]
HK_BURST = HK1 - 0.7                       # "…y revientan"
CI_BURST = CI1 - 0.6                       # "…y estallando"
RO_S1 = RO0 + 0.9                          # "se rompe en pedazos"
RO_S2 = RO0 + 1.9                          # "con destellos"
RO_RED = RO0 + 0.80 * (RO1 - RO0)          # "el último suele ser rojo"
TAU_RAD = (780, 600)
LEO_RAD = (300, 640)
MET_SKY = (meteor_list(1, FL[0] - 0.3, FL[1] + 0.2, 2.6, (700, 420), (0.5, 0.9), (300, 520), (1.4, 1.4, 1.3), (2.8, 4.0), (1.4, 2.2))
           + meteor_list(2, FL[0] - 0.3, FL[1] + 0.2, 1.4, (250, 900), (0.6, 1.1), (300, 500), (1.6, 1.1, 0.8), (3.0, 4.2), (1.4, 2.2)))
MET_TAU = meteor_list(3, FL[3] - 0.6, FL[4] + 0.2, 0.75, TAU_RAD, (1.5, 2.3), (520, 820), (1.7, 0.95, 0.45), (4.5, 6.5), (1.3, 1.9), (60, 300))
MET_LEO = meteor_list(4, FL[4] - 0.3, FL[5] + 0.2, 4.0, LEO_RAD, (0.45, 0.7), (380, 680), (1.2, 1.55, 1.3), (2.0, 3.0), (1.0, 1.5), (60, 360))


def scene(t):
    names = ["hook", "cielo", "roca", "caida", "tauridas", "leonidas", "cierre"]
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



def mass_bar(d, frac, A, x=W / 2, y=560, w=560):
    h = 34
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], 17, outline=(255, 255, 255, int(A * 0.6)), width=4)
    fw = (w - 12) * frac
    d.rounded_rectangle([x - w / 2 + 6, y - h / 2 + 6, x - w / 2 + 6 + fw, y + h / 2 - 6], 11, fill=YELLOW + (A,))
    txt(d, (x - w / 2, y - 50), "MASA", 42, WHITE, A, "Inter-Black.otf", 6, "lm")
    txt(d, (x + w / 2, y - 50), f"{int(round(frac * 100))} %", 42, YELLOW, A, "Inter-Black.otf", 6, "rm")


# ---------------- escenas ----------------
MDIR = np.array([-1.0, -0.32, 0.22]); MDIR /= np.linalg.norm(MDIR)


def limb_cam(t, k):
    return Cam((0.0, 0.55 - 0.03 * k, 2.9), (0.0, 0.92, 0.0), roll=0.08)


def fireball_over_earth(img, layer, t, t0, t1, burst_at):
    """Bola de fuego que cruza la atmósfera sobre el borde de la Tierra y revienta."""
    cam = limb_cam(t, (t - t0) / max(t1 - t0, 1e-3))
    draw_earth(img, cam, (0, 0, 0), 1.0, t)
    x0, y0, x1, y1 = 980, 520, 300, 980
    u = ease_out((t - t0) / max(burst_at - t0, 1e-3))
    if t < burst_at:
        streak(img, x0, y0, x1, y1, u, 0.55, (1.6, 0.75, 0.3), 5.0, 1.4)
        streak(img, x0, y0, x1, y1, u, 0.2, (1.4, 1.3, 1.1), 2.5, 0.8)
        hx, hy = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        glow(img, hx, hy, (1.6, 1.2, 0.8), 26, 0.5)
    else:
        dt = t - burst_at
        hx, hy = x1, y1
        glow(img, hx, hy, (2.2, 1.6, 1.0), 40 + 120 * dt, 2.2 * math.exp(-dt / 0.25))
        rng = np.random.default_rng(5)
        for k in range(26):
            ang = rng.uniform(0, 2 * np.pi); sp = rng.uniform(60, 330)
            dx, dy = math.cos(ang) * sp * (1 - math.exp(-dt / 0.35)), math.sin(ang) * sp * (1 - math.exp(-dt / 0.35)) + 60 * dt * dt
            dx += -180 * dt; dy += 120 * dt
            glow(img, hx + dx, hy + dy, (1.7, 0.8, 0.3), 3.5, 0.9 * math.exp(-dt / 0.9))
        # restos de la estela que se desvanecen
        streak(img, x0, y0, x1, y1, 1.0, 0.55, (1.0, 0.5, 0.25), 5.0, 1.0 * math.exp(-dt / 0.5))
    return cam, dict(hx=x1, hy=y1)


def sc_hook(img, layer, t):
    return fireball_over_earth(img, layer, t, 0.15, FL[0], HK_BURST)


def sc_cielo(img, layer, t):
    img[:] = SKY_N
    for m in MET_SKY:
        m.draw(img, t)
    return None, {}


def rock_state(t):
    """Estado continuo de la roca entre el choque y la ruptura."""
    heat = 0.15 + 0.55 * smooth(CH0 - 0.3, CH1, t) + 0.3 * smooth(DE0, DE0 + 2.0, t)
    shockI = 0.3 + 0.9 * smooth(CH0 - 0.3, CH0 + 1.6, t)
    melt = smooth(DE0 + 0.3, DE1, t)        # 0 → 1
    r = 1.0 * (1 - 0.157 * melt)            # 40 % menos volumen ≈ 16 % menos radio
    return heat, shockI, melt, r


def roca_cam(t):
    u = t - FL[1]
    a = 0.35 - 0.95 * smooth(CH0, DE1, t)
    dist = 8.0 + 3.5 * smooth(RO0 - 0.2, RO0 + 1.6, t)
    pos = np.array([math.sin(a) * dist, 1.1 + 0.2 * math.sin(u * 0.3), math.cos(a) * dist])
    return Cam(pos, (-0.35, -0.25, 0.0), roll=0.04 * math.sin(u * 0.4))


FRAGS1 = [(np.array([0.1, 1.0, 0.3]), 0.56, 0), (np.array([0.2, -0.8, 0.6]), 0.50, 1), (np.array([-0.1, -0.2, -1.0]), 0.44, 2)]


def fragments(t):
    """Lista de (centro, radio, R, tex) de los pedazos según el tiempo."""
    out = []
    if t < RO_S1:
        return None
    for i, (dvec, rr, ti) in enumerate(FRAGS1):
        dv = dvec / np.linalg.norm(dvec)
        s1 = 1.6 * (1 - math.exp(-(t - RO_S1) / 0.55))
        c = dv * s1 * 0.8 - MDIR * 0.25 * (t - RO_S1) * (0.6 + 0.3 * i)
        R = rotm(0.9 * i + 1.8 * (t - RO_S1) * (1 + 0.3 * i), 0.5 * i + 0.7 * (t - RO_S1), 0.3 * i)
        if t < RO_S2 or i == 2:
            out.append((c, rr, R, ROCK_TEX[ti + 1], 0.24))
        else:
            for sgn in (-1, 1):
                perp = np.cross(dv, MDIR); perp /= np.linalg.norm(perp)
                s2 = 0.9 * (1 - math.exp(-(t - RO_S2) / 0.5))
                cc = c + perp * sgn * s2 - MDIR * 0.12 * (t - RO_S2)
                R2 = R @ rotm(sgn * 1.2 * (t - RO_S2), 0.4, 0)
                out.append((cc, rr * 0.74, R2, ROCK_TEX[(ti + 2 + (sgn > 0)) % 4], 0.28))
    return out


def sc_roca(img, layer, t):
    img[:] = SKY_HI
    cam = roca_cam(t)
    heat, shockI, melt, r = rock_state(t)
    air_lines(img, cam, MDIR, t, 26.0, 0.6 + 0.8 * smooth(CH0, CH0 + 1.5, t))
    frs = fragments(t)
    if frs is None:
        wake(img, cam, (0, 0, 0), r, MDIR, 0.6 + 0.8 * heat, t)
        R = rotm(0.6 + 0.18 * t, 0.35 + 0.05 * t, 0.1)
        info = draw_rock(img, cam, (0, 0, 0), r, R, ROCK_TEX[0], heat, 0.0, MDIR, 0.18)
        shock(img, cam, (0, 0, 0), r, MDIR, shockI, t)
        droplets(img, cam, (0, 0, 0), r, MDIR, smooth(DE0 + 0.2, DE0 + 1.2, t) * (1.0 if t < RO_S1 else 0), t, DE0)
    else:
        hf = max(0.0, 1.0 - 0.15 * (t - RO_S1))
        order = sorted(frs, key=lambda f: -float(np.linalg.norm(f[0] - cam.O)))
        for (c, rr, R, tx, am) in order:
            wake(img, cam, c, rr, MDIR, 0.9 * hf, t, 7.0)
        for (c, rr, R, tx, am) in order:
            draw_rock(img, cam, c, rr, R, tx, 0.95 * hf, 0.0, MDIR, am, 26)
            shock(img, cam, c, rr, MDIR, 0.55 * hf, t)
        # destellos de la ruptura (el último, rojo)
        for (tf, col, sz) in ((RO_S1, (2.4, 2.0, 1.5), 1.0), (RO_S2, (2.2, 1.6, 0.9), 0.9), (RO_RED, (2.6, 0.45, 0.25), 1.25)):
            dt = t - tf
            if -0.02 < dt < 1.2:
                x, y, _ = cam.proj(-MDIR * 0.6 * max(dt, 0) if tf != RO_RED else -MDIR * 1.4)
                glow(img, float(x[0]), float(y[0]), col, 45 * sz + 110 * max(dt, 0), 1.5 * sz * math.exp(-max(dt, 0) / 0.2))
    return cam, {}


CA_ROCKS = [((-1.1, 1.2, 0.0), 0.55, 1), ((1.0, 1.7, -1.0), 0.46, 2), ((1.2, 0.3, 0.8), 0.38, 3), ((-0.6, -0.2, 1.4), 0.32, 0)]


def sc_caida(img, layer, t):
    img[:] = SKY_DAY
    u = t - FL[2]
    cam = Cam((0.0, 0.3, 9.0), (0.0, 0.1, 0.0))
    heat = 0.6 * (1 - smooth(0.0, 1.4, u))
    crust = smooth(0.2, 1.8, u)
    items = []
    for i, (c0, rr, ti) in enumerate(CA_ROCKS):
        c = np.array(c0) + np.array([0.08 * u * (i - 1.5), -0.45 * u - 0.05 * u * u, 0])
        R = rotm(0.7 * i + 0.9 * u * (1 + 0.25 * i), 0.4 + 0.5 * u, 0.2 * i)
        items.append((c, rr, R, ROCK_TEX[ti]))
    items.sort(key=lambda f: -float(np.linalg.norm(f[0] - cam.O)))
    for (c, rr, R, tx) in items:
        draw_rock(img, cam, c, rr, R, tx, heat, crust, np.array([0.0, -1.0, 0.0]), 0.22, 26)
    return cam, {}


def sky_with_radiant(img, t, sky, mets):
    img[:] = sky
    for m in mets:
        m.draw(img, t)


def sc_tauridas(img, layer, t):
    sky_with_radiant(img, t, SKY_T, MET_TAU)
    return None, dict(rx=TAU_RAD[0], ry=TAU_RAD[1])


def sc_leonidas(img, layer, t):
    sky_with_radiant(img, t, SKY_L, MET_LEO)
    return None, dict(rx=LEO_RAD[0], ry=LEO_RAD[1])


def sc_cierre(img, layer, t):
    return fireball_over_earth(img, layer, t, FL[5], CARD, CI_BURST)


SCENES = {"hook": sc_hook, "cielo": sc_cielo, "roca": sc_roca, "caida": sc_caida, "tauridas": sc_tauridas, "leonidas": sc_leonidas, "cierre": sc_cierre}


def overlays(frame_u8, layer, t, name, cam, extra):
    im = Image.fromarray(frame_u8).convert("RGBA")
    im.alpha_composite(layer)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if name == "hook":
        draw_label(layer, t, 0.4, FL[0], "NO SE QUEMAN", ["se derriten y revientan"], YELLOW, 124)
    elif name == "cielo":
        draw_label(layer, t, ES0, FL[1], "75 CAÍDAS", ["grabadas en video", "Instituto SETI · NASA Ames"], YELLOW, 130)
    elif name == "roca":
        draw_label(layer, t, CH0 - 0.05, DE0 - 0.1, "CHOQUE CON EL AIRE", ["la roca y el gas brillan"], WHITE, 92)
        if t < RO0 - 0.1:
            al = fade(t, DE0 - 0.05, RO0 - 0.15)
            if al > 0:
                A = int(255 * al)
                draw_label(layer, t, DE0 - 0.05, RO0 - 0.15, "SE DERRITE", [], (255, 150, 60), 112)
                _, _, melt, _ = rock_state(t)
                mass_bar(d, 1 - 0.40 * melt, A)
        draw_label(layer, t, RO0 + 0.1, FL[2], "SE ROMPE", ["destellos… y el último, rojo"], WHITE, 120)
    elif name == "caida":
        draw_label(layer, t, CA0 - 0.05, FL[3], "METEORITOS", ["se apagan y caen"], YELLOW, 124)
    elif name == "tauridas":
        draw_label(layer, t, TA0, FL[4], "TÁURIDAS DEL SUR", ["noche del 4 al 5 de noviembre", "bolas de fuego lentas"], YELLOW, 96)
        al = fade(t, TA0 + 0.5, FL[4], 0.3)
        if al > 0:
            marker(d, extra["rx"], extra["ry"], t, YELLOW, int(255 * al), 30, "TAURO", 1, 44)
    elif name == "leonidas":
        draw_label(layer, t, LE0, FL[5], "LEÓNIDAS", ["noche del 17 al 18 de noviembre", "hasta 15 por hora"], CYAN, 124)
        al = fade(t, LE0 + 0.4, FL[5], 0.3)
        if al > 0:
            marker(d, extra["rx"], extra["ry"], t, CYAN, int(255 * al), 30, "LEO", -1, 44)
    elif name == "cierre":
        draw_label(layer, t, CI0 + 0.1, CARD, "MÍRALO TÚ", ["4–5 NOV · Táuridas", "17–18 NOV · Leónidas"], YELLOW, 120)
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
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL], "card", round(CARD, 2), "ruptura", round(RO_S1, 2), round(RO_S2, 2), round(RO_RED, 2))
