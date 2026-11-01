"""Flash Datos · video 08 · ¿Sobrevivirías a un apocalipsis zombi en tu ciudad? (esferas trazadas y sprites 3D).

Uso:
  python3 escena.py test 1.0 5.0 ...        -> PNG de prueba en frames_test/
  python3 escena.py chunk <ini> <fin> <out> -> MP4 de los cuadros [ini, fin)
  python3 escena.py info
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
W, H, FPS = 1080, 1920, 30
TY = math.tan(math.radians(20)); TX = TY * W / H
PIX = 2 * TY / H

xs = ((np.arange(W) + 0.5) / W * 2 - 1) * TX
ys = (1 - (np.arange(H) + 0.5) / H * 2) * TY
DX, DY = np.meshgrid(xs, ys)
NRM = np.sqrt(DX * DX + DY * DY + 1)
DIRS = np.stack([DX / NRM, DY / NRM, -1 / NRM], axis=-1)

LIGHT0 = np.array([-0.55, 0.55, 0.62]); LIGHT0 /= np.linalg.norm(LIGHT0)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
EARTH = lin(np.clip(T("earth"), 0, 1)); CLOUDS = T("earth_clouds"); LAND = T("earth_land")
GOLD = lin([1.0, 0.78, 0.34]); ICE = lin([0.62, 0.90, 1.0])


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


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def make_background():
    rng = np.random.default_rng(66)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1500
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.025 + 0.42 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 40
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 40.0
    neb = fbm(gx, gy, np.full_like(gx, 0.3), 5, seed=6)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.004, 0.020, 0.010], np.float32)  # niebla verdosa muy tenue
    return bg


BG = make_background()


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


def shade(body, n, V, t, L):
    ndl = (n * L).sum(-1)
    mu = np.clip((n * V).sum(-1), 0, 1)
    diff = np.clip(ndl, 0, 1)
    kind = body["kind"]
    if kind in ("gold", "ice"):
        base = GOLD if kind == "gold" else ICE
        R = 2 * (n * V).sum(-1)[..., None] * n - V
        up = smooth(-0.2, 0.8, R[..., 1])
        env = (np.array([0.05, 0.035, 0.015]) + up[..., None] * np.array([0.30, 0.22, 0.10])) if kind == "gold" else \
              (np.array([0.03, 0.06, 0.09]) + up[..., None] * np.array([0.25, 0.42, 0.55]))
        Hh = L + V; Hh = Hh / np.linalg.norm(Hh, axis=-1, keepdims=True)
        spec = np.clip((n * Hh).sum(-1), 0, 1) ** 70 * 7.0
        fres = (1 - mu) ** 3
        col = base * (0.06 + 1.25 * diff)[..., None] + env * base * 1.6 + spec[..., None] * np.array([1.0, 0.95, 0.85])
        col = col + fres[..., None] * base * 0.6
        return col * body.get("gain", 1.0)
    # Tierra
    loc = rot_y(rot_x(n, math.radians(body.get("tilt", 16))), body.get("spin", -1.72))
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.85) + 0.80 * cl * 0.85
    R = 2 * ndl[..., None] * n - L
    spec = np.clip((R * V).sum(-1), 0, 1) ** 45 * (1 - land) * (1 - cl[..., 0]) * 0.9
    light = (0.03 + 2.0 * diff + smooth(-0.15, 0.35, ndl) * 0.10)[..., None]
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85])
    fres = (1 - mu) ** 2.5
    col = col + np.array([0.25, 0.55, 1.0]) * (fres * 0.9 * np.clip(ndl + 0.3, 0, 1))[..., None]
    return col * body.get("gain", 1.0)


def draw_sphere(img, O, body, t):
    C = np.array(body["c"], float); r = body["r"]
    if r <= 1e-4:
        return
    rel = C - O
    dist_c = float(np.linalg.norm(rel))
    if dist_c <= r * 1.0001 or rel[2] >= 0:
        return
    depth = -rel[2]
    cxp = (rel[0] / depth / TX + 1) / 2 * W
    cyp = (1 - rel[1] / depth / TY) / 2 * H
    rpx = math.tan(math.asin(r / dist_c)) / PIX
    ext = rpx * 1.12 + 6
    ext *= 1.0 + 0.6 * min(1.0, rpx / H)
    x0 = int(max(0, cxp - ext)); x1 = int(min(W, cxp + ext + 1))
    y0 = int(max(0, cyp - ext)); y1 = int(min(H, cyp + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return
    d = DIRS[y0:y1, x0:x1]
    oc = O - C
    b = d @ oc
    occ = float(oc @ oc)
    perp2 = np.maximum(occ - b * b, 0)
    dist = np.sqrt(perp2)
    pixw = np.maximum(-b, 1e-9) * PIX
    alpha = np.clip((r - dist) / pixw + 0.5, 0, 1) * (b < 0) * body.get("op", 1.0)
    region = img[y0:y1, x0:x1]
    if body["kind"] == "earth":
        hz = (dist > r * 0.995) & (dist < r * 1.06) & (b < 0)
        if hz.any():
            dd = (dist[hz] - r) / (0.018 * r)
            P = O + (-b[hz])[:, None] * d[hz]
            nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
            lit = np.clip(nn @ LIGHT0 + 0.35, 0, 1)
            gl = np.exp(-np.maximum(dd, 0)) * lit * 0.35 * body.get("gain", 1.0)
            region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([0.30, 0.60, 1.0])
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]; bs = b[sel]
    disc = np.maximum(r * r - perp2[sel], 0)
    tt = -bs - np.sqrt(disc)
    P = O + tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    V = -ds
    col = shade(body, n, V, t, np.broadcast_to(LIGHT0, P.shape))
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


def bloom(img):
    small = img[::4, ::4]
    br = np.clip(small - 0.9, 0, None)
    g = gaussian_filter(br, (5, 5, 0)) * 0.55 + gaussian_filter(br, (22, 22, 0)) * 0.85 + gaussian_filter(br, (60, 60, 0)) * 0.5
    return img + ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)



# ---------------- sprites 3D (esferas sombreadas instanciadas) para multitudes ----------------
L_SPR = np.array([-0.5, 0.65, 0.58]); L_SPR /= np.linalg.norm(L_SPR)
SPR_COL = {
    "human": (lin([0.78, 0.82, 0.90]), 0.0),
    "you": (lin([1.0, 0.95, 0.85]), 0.35),
    "zombie": (lin([0.35, 1.0, 0.30]), 0.55),
    "dead": (lin([0.16, 0.18, 0.17]), 0.0),
    "post": (lin([1.0, 0.18, 0.12]), 0.25),
    "hill": (lin([0.035, 0.045, 0.06]), 0.0),
    "warm": (lin([1.0, 0.45, 0.12]), 1.4),
    "moon": (lin([0.92, 0.95, 1.0]), 0.9),
}
_SPR = {}


def sprite(kind, r):
    r = max(1, int(round(r)))
    key = (kind, r)
    if key in _SPR:
        return _SPR[key]
    n = 2 * r + 3
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    dx = (xx - (n - 1) / 2) / r; dy = -(yy - (n - 1) / 2) / r
    rr = dx * dx + dy * dy
    a = np.clip((1.0 - np.sqrt(rr)) * r + 0.5, 0, 1)
    dz = np.sqrt(np.clip(1 - rr, 0, 1))
    N = np.stack([dx, dy, dz], -1)
    ndl = np.clip(N @ L_SPR, 0, 1)
    Hh = L_SPR + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    spec = np.clip(N @ Hh, 0, 1) ** 40 * 0.9
    rim = (1 - dz) ** 3
    base, emit = SPR_COL[kind]
    col = base * (0.06 + 1.35 * ndl)[..., None] + spec[..., None] * 0.6 + rim[..., None] * base * 0.5 + base * emit
    _SPR[key] = (col.astype(np.float32), a.astype(np.float32))
    return _SPR[key]


def blit(img, kind, x, y, r, op=1.0):
    if r < 0.6:
        if 0 <= int(x) < W and 0 <= int(y) < H:
            base, emit = SPR_COL[kind]
            img[int(y), int(x)] += (base * (0.6 + emit)) * op
        return
    col, a = sprite(kind, r)
    n = col.shape[0]
    x0 = int(round(x - (n - 1) / 2)); y0 = int(round(y - (n - 1) / 2))
    xa, ya = max(x0, 0), max(y0, 0); xb, yb = min(x0 + n, W), min(y0 + n, H)
    if xa >= xb or ya >= yb:
        return
    c = col[ya - y0:yb - y0, xa - x0:xb - x0]; al = a[ya - y0:yb - y0, xa - x0:xb - x0, None] * op
    reg = img[ya:yb, xa:xb]
    reg[:] = reg * (1 - al) + c * al


class Cam:
    def __init__(self, pos, pitch_deg):
        self.p = np.asarray(pos, float)
        pa = math.radians(pitch_deg)
        self.f = np.array([0.0, -math.sin(pa), -math.cos(pa)])
        self.u = np.array([0.0, math.cos(pa), -math.sin(pa)])

    def proj(self, P):
        P = np.atleast_2d(np.asarray(P, float)) - self.p
        x = P[:, 0]; y = P @ self.u; z = P @ self.f
        z = np.maximum(z, 1e-3)
        return (x / z / TX + 1) / 2 * W, (1 - y / z / TY) / 2 * H, z


def draw_crowd(img, cam, items):
    """items: lista de (kind, pos(3), radio, op)."""
    if not items:
        return
    P = np.array([it[1] for it in items])
    sx, sy, z = cam.proj(P)
    order = np.argsort(-z)
    for i in order:
        if z[i] < 0.3:
            continue
        kind, _, r, op = items[i]
        blit(img, kind, sx[i], sy[i], r / z[i] / PIX, op)


def ground_layer(cam, t, spacing=2.4, extent=40, glow=None):
    """Calles de la ciudad: retícula en perspectiva sobre el suelo."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    z_near = cam.p[2] - 0.5
    for k in np.arange(-extent, extent + 0.01, spacing):
        for a, b in (((k, 0, z_near), (k, 0, -extent * 2)), ((-extent, 0, z_near - (k + extent)), (extent, 0, z_near - (k + extent)))):
            pts = np.linspace(np.array(a), np.array(b), 24)
            sx, sy, z = cam.proj(pts)
            ok = z > 0.4
            seg = [(float(x), float(y)) for x, y, o in zip(sx, sy, ok) if o]
            if len(seg) > 1:
                d.line(seg, fill=(60, 90, 80, 70), width=2)
    return lay


def skyline_layer(cam, t, flicker=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hx, hy, _ = cam.proj([(0.0, 0.0, -400.0)])
    hy = float(hy[0])
    if hy < -50:
        return lay, hy
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(31)
    x = -20
    while x < W + 20:
        w = rng.integers(40, 110); h = rng.integers(60, 260)
        d.rectangle([x, hy - h, x + w, hy + 2], fill=(7, 9, 14, 255))
        for wy in range(int(hy - h + 14), int(hy - 10), 22):
            for wx in range(int(x + 8), int(x + w - 8), 18):
                ph = rng.random()
                on = ph < 0.18 and (math.sin(t * (1 + 3 * ph) + wx) > -0.2 or flicker < 0.6)
                if on:
                    d.rectangle([wx, wy, wx + 7, wy + 10], fill=(255, 200, 120, int(150 * flicker)))
        x += w + rng.integers(0, 14)
    return lay, hy


def comp_layer(img, lay):
    a = np.asarray(lay, np.float32) / 255.0
    img[:] = img * (1 - a[..., 3:4]) + lin(a[..., :3]) * a[..., 3:4]


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
P = lambda sid, k: SEG[sid]["parts"][k]
H1 = SEG["hook1"]; H2 = SEG["hook2"]
COR0 = SEG["cornell"]["t0"]; CIU0 = SEG["ciudades"]["t0"]; CIU_P2 = P("ciudades", 1)[0]
MX0 = SEG["cdmx"]["t0"]; HUI0 = SEG["huir"]["t0"]; OTT0 = SEG["ottawa"]["t0"]
HON0 = SEG["hongo"]["t0"]; CIE0 = SEG["cierre"]["t0"]; CIE_P2 = P("cierre", 1)[0]
FL = [COR0 - 0.2, CIU_P2 - 0.15, MX0 - 0.2, HUI0 - 0.2, OTT0 - 0.2, HON0 - 0.2, CIE0 - 0.2, CIE_P2 - 0.15]


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


# ---------------- la ciudad y el brote ----------------
RC = np.random.default_rng(8)
CROWD = []
for gx in np.arange(-7.0, 7.01, 0.62):
    for gz in np.arange(1.5, -34, -0.62):
        if (abs(gx) % 2.4) < 0.5 or (abs(gz) % 2.4) < 0.5:  # la gente camina por las calles
            CROWD.append((gx + RC.uniform(-0.16, 0.16), gz + RC.uniform(-0.16, 0.16)))
CROWD = np.array(CROWD)
Z0 = np.array([0.15, -9.0])  # paciente cero
_d = np.linalg.norm(CROWD - Z0, axis=1)
T_INF = H2["t0"] + 0.2 + _d / 2.4 + RC.uniform(0, 0.8, len(CROWD))   # frente de contagio
T_INF[np.argmin(_d)] = H2["t0"] + 0.1
T_DEAD = T_INF + 4.0 + RC.uniform(0, 8, len(CROWD))
T_DEAD[RC.random(len(CROWD)) < 0.7] = 1e9                      # pocos zombis caen
WALK = RC.uniform(0, 2 * math.pi, len(CROWD))
R_P = 0.2


def city_items(t, calm=False):
    out = []
    for i, (x, z) in enumerate(CROWD):
        bob = 0.03 * abs(math.sin(t * 4 + WALK[i]))
        k = "human"
        if not calm and t >= T_INF[i]:
            k = "dead" if t >= T_DEAD[i] else "zombie"
        sh = 0.0
        if k == "zombie":
            sh = 0.05 * math.sin(t * 9 + i)
        out.append((k, (x + sh, R_P + bob, z), R_P, 1.0))
    return out


# densa contra dispersa
RD = np.random.default_rng(12)
DENSE = np.array([(x + RD.uniform(-0.05, 0.05), z + RD.uniform(-0.05, 0.05)) for x in np.arange(-3.6, -0.6, 0.36) for z in np.arange(-3.5, -9.5, -0.36)])
SPARSE = np.array([(x + RD.uniform(-0.3, 0.3), z + RD.uniform(-0.3, 0.3)) for x in np.arange(0.9, 3.9, 1.0) for z in np.arange(-3.5, -9.5, -1.0)])
dD = np.linalg.norm(DENSE - DENSE.mean(0), axis=1); dS = np.linalg.norm(SPARSE - SPARSE.mean(0), axis=1)
TD = CIU_P2 + 0.2 + dD / 1.7 + RD.uniform(0, 0.3, len(DENSE)); TD[np.argmin(dD)] = CIU_P2
TS = CIU_P2 + 0.2 + dS / 0.45 + RD.uniform(0, 1.2, len(SPARSE)); TS[np.argmin(dS)] = CIU_P2
TS[RD.random(len(SPARSE)) < 0.35] = 1e9


def split_items(t):
    out = []
    for (x, z), ti in zip(DENSE, TD):
        out.append(("zombie" if t >= ti else "human", (x, 0.16, z), 0.16, 1.0))
    for (x, z), ti in zip(SPARSE, TS):
        out.append(("zombie" if t >= ti else "human", (x, 0.16, z), 0.16, 1.0))
    return out


# huida
HORDE = np.array([(RC.uniform(-4, 4), RC.uniform(0, 7)) for _ in range(90)])


def run_items(t):
    s = t - HUI0
    you_z = -2.0 - 1.1 * s
    out = [("you", (0.25 * math.sin(s * 9), 0.24 + 0.08 * abs(math.sin(s * 9)), you_z), 0.24, 1.0)]
    for i, (x, dz) in enumerate(HORDE):
        z = you_z + 1.6 + dz * 0.7 - 0.15 * s
        out.append(("zombie", (x + 0.1 * math.sin(t * 5 + i), 0.24 + 0.04 * abs(math.sin(t * 6 + i)), z), 0.24, 1.0))
    return out


# cuarentena (Ottawa)
NQ = 46
QPOS = np.array([(math.cos(a) * 2.6, math.sin(a) * 2.6) for a in np.linspace(0, 2 * math.pi, NQ, endpoint=False)])
INQ = np.array([(r * math.cos(a), r * math.sin(a)) for r, a in zip(np.sqrt(RC.random(110)) * 2.2, RC.uniform(0, 2 * math.pi, 110))])
BREAK = OTT0 + 2.2
GAP = [k for k in range(NQ) if abs(((k / NQ) * 360 - 300 + 180) % 360 - 180) < 34]
ESC_DIR = np.array([math.cos(math.radians(300)), math.sin(math.radians(300))])


def quar_items(t):
    out = []
    for k, (x, z) in enumerate(QPOS):
        if k in GAP and t > BREAK:
            dt = t - BREAK
            x = x + ESC_DIR[0] * dt * 2.0; z = z + ESC_DIR[1] * dt * 2.0
            out.append(("post", (x, max(0.12, 0.2 - dt * 0.1), z - 6), 0.17, max(0.0, 1 - dt / 1.2)))
        else:
            out.append(("post", (x, 0.2, z - 6), 0.17, 1.0))
    for i, (x, z) in enumerate(INQ):
        px, pz = x, z
        if t > BREAK + 0.2:
            dt = t - BREAK - 0.2
            toward = ESC_DIR * (dt * (1.2 + 0.9 * ((i * 37) % 10) / 10))
            if (np.array([x, z]) @ ESC_DIR) > -0.6 + 0.15 * (i % 5):
                px, pz = x + toward[0] * 1.6, z + toward[1] * 1.6
        out.append(("zombie", (px + 0.06 * math.sin(t * 7 + i), 0.15, pz - 6), 0.15, 1.0))
    return out


# el hongo y la hormiga
ANT = dict(c=(0.0, -0.3, 0.0))
SPORES = np.array([(RC.uniform(-1.6, 1.6), RC.uniform(0, 1), RC.uniform(0.6, 1.4), RC.uniform(0, 6)) for _ in range(140)])


def scene(t):
    if t < FL[0] or (t >= FL[7]):
        calm = t >= FL[7]
        tt = t if not calm else t - FL[7]
        cam = Cam((0.0, 3.0 + (1.2 * ease(tt / 5) if calm else 0.0), 7.5 - (0.6 * ease_out(t / 6) if not calm else 0.0)), 13 if not calm else lerp(13, 6, ease(tt / 2.5)))
        return "hook" if not calm else "calma", cam, city_items(t, calm=calm)
    if t < FL[1]:
        s = (t - FL[0]) / (FL[1] - FL[0])
        cam = Cam((0.0, lerp(3.0, 9.0, ease(s)), lerp(6.9, 4.0, ease(s))), lerp(13, 38, ease(s)))
        return "cornell", cam, city_items(t)
    if t < FL[2]:
        return "split", Cam((0.0, 18.0, 2.2), 62), split_items(t)
    if t < FL[3]:
        return "cdmx", None, None
    if t < FL[4]:
        s = t - HUI0
        you_z = -2.0 - 1.1 * s
        return "huir", Cam((0.0, 3.2, you_z + 9.5), 11), run_items(t)
    if t < FL[5]:
        return "ottawa", Cam((0.0, 14.0, 1.6), 60), quar_items(t)
    if t < FL[6]:
        return "hongo", None, None
    return "calor", None, None


HL_WORDS = {"silencio…", "silencio", "apocalipsis", "zombi?", "sobrevivirías", "cornell", "millones", "ciudades", "primero.", "rápido",
            "cdmx", "huir:", "semanas", "meses", "montañas.", "ottawa", "cuarentena", "zombis", "hongo", "hormigas", "calor",
            "destruye", "dormir", "tranquilo."}

# ---------------- subtítulos y textos ----------------
def groups_for_part(t0, t1, text):
    words = text.split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w[-1] in ".,:…?" or len(" ".join(cur)) > 17:
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
    for t0, t1, txt in s["parts"]:
        CAPS += groups_for_part(t0, t1, txt)
for i in range(len(CAPS) - 1):
    if CAPS[i + 1][0] - CAPS[i][1] < 0.7:
        CAPS[i][1] = CAPS[i + 1][0]

FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); INK = (8, 10, 20); RED = (255, 84, 84)


def is_hl(w):
    core = w.strip(".,:…?¿!").lower()
    return any(ch.isdigit() for ch in core) or core in HL_WORDS or w.strip(".,:…?¿!").isupper() and len(core) > 1


def draw_caption(layer, t, y=1250):
    for (t0, t1, g) in CAPS:
        if t0 <= t < t1:
            k = min(1.0, (t - t0) / 0.09)
            size = int(round(80 * (1.12 - 0.12 * k)))
            f = font("Inter-Black.otf", size)
            d = ImageDraw.Draw(layer)
            space = d.textlength(" ", font=f)
            widths = [d.textlength(w, font=f) for w in g]
            total = sum(widths) + space * (len(g) - 1)
            if total > W - 80:
                size = int(size * (W - 80) / total); f = font("Inter-Black.otf", size)
                space = d.textlength(" ", font=f); widths = [d.textlength(w, font=f) for w in g]
                total = sum(widths) + space * (len(g) - 1)
            x = W / 2 - total / 2
            for w, wd in zip(g, widths):
                col = YELLOW if is_hl(w) else WHITE
                d.text((x, y), w, font=f, fill=col + (255,), anchor="lm", stroke_width=9, stroke_fill=INK + (255,))
                x += wd + space
            return


def fade(t, a, b, f=0.25):
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / f, (b - t) / f)


def txt(d, xy, s, size, col, A, fname="Inter-Black.otf", anchor="mm", sw=7):
    d.text(xy, s, font=font(fname, size), fill=col + (A,), anchor=anchor, stroke_width=sw, stroke_fill=INK + (A,))


def draw_label(layer, t, a, b, title, subs, title_col=WHITE, title_size=118, y0=360, sub_col=CYAN):
    al = fade(t, a, b)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - min(1.0, (t - a) / 0.3)) * 24
    y = y0 + rise
    f = font("Inter-Black.otf", title_size)
    while d.textlength(title, font=f) > W - 90 and title_size > 40:
        title_size -= 4; f = font("Inter-Black.otf", title_size)
    d.text((W / 2, y), title, font=f, fill=title_col + (A,), anchor="mm", stroke_width=8, stroke_fill=INK + (A,))
    y += title_size * 0.5 + 44
    for s in subs:
        txt(d, (W / 2, y), s, 54, sub_col, A, "Inter-ExtraBold.otf")
        y += 70


def bolt(cx, cy, s):
    pts = [(0.58, 0.0), (0.12, 0.56), (0.44, 0.56), (0.30, 1.0), (0.88, 0.38), (0.55, 0.38), (0.74, 0.0)]
    return [(cx + (px - 0.5) * s, cy + (py - 0.5) * s) for px, py in pts]


def draw_watermark(layer):
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 38)
    s = "FLASH DATOS"
    tw = d.textlength(s, font=f)
    x = W / 2 - (tw + 40) / 2
    d.polygon(bolt(x + 14, 212, 40), fill=YELLOW + (230,))
    d.text((x + 40, 212), s, font=f, fill=(255, 255, 255, 215), anchor="lm", stroke_width=4, stroke_fill=INK + (160,))


def project(O, p):
    rel = np.asarray(p, float) - O
    depth = -rel[2]
    return (rel[0] / depth / TX + 1) / 2 * W, (1 - rel[1] / depth / TY) / 2 * H


def box(layer, xy, fill, outline, width=5, radius=34):
    b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(b).rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    layer.alpha_composite(b)


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a



GREEN = (120, 255, 110)


def ring_marker(d, x, y, t, col, A, big=110):
    for k in range(3):
        ph = ((t * 1.2) + k / 3) % 1.0
        rr = 22 + big * ph
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (int(A * (1 - ph)),), width=6)


def draw_clock(layer, t, a, b):
    al = fade(t, a, b, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    blink = (int(t * 2) % 2 == 0)
    cx, cy = W / 2, 1560
    box(layer, [cx - 230, cy - 78, cx + 230, cy + 78], (8, 10, 14, int(220 * al)), RED + (A,), 5)
    d = ImageDraw.Draw(layer)
    txt(d, (cx - 40, cy), "02" + (":" if blink else " ") + "00", 96, RED, A, sw=6)
    txt(d, (cx + 150, cy + 10), "AM", 52, RED, A, "Inter-ExtraBold.otf", sw=5)


def draw_endcard(layer, t, t0):
    al = fade(t, t0, END - 0.3, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    layer.alpha_composite(Image.new("RGBA", (W, H), (4, 6, 10, int(170 * al))))
    d = ImageDraw.Draw(layer)
    k = ease_out((t - t0) / 0.4)
    d.polygon(bolt(W / 2, 780, 230 + 40 * k), fill=YELLOW + (A,))
    txt(d, (W / 2, 1010), "FLASH DATOS", 104, WHITE, A, sw=8)
    txt(d, (W / 2, 1120), "Síguenos para más datos", 52, CYAN, A, "Inter-ExtraBold.otf", sw=6)
    txt(d, (W / 2, 1185), "que dan miedo", 52, CYAN, A, "Inter-ExtraBold.otf", sw=6)


def draw_city_labels(layer, t, name, cam):
    d = ImageDraw.Draw(layer)
    if name == "hook":
        draw_label(layer, t, -1, H2["t0"] - 0.05, "2:00 AM", ["tu ciudad está en silencio…"], WHITE, 150, y0=420)
        draw_clock(layer, t, -1, H2["t0"] - 0.05)
        al = fade(t, H2["t0"] - 0.05, FL[0] + 0.05, 0.12)
        if al > 0:
            A = int(255 * al)
            k = ease_out((t - H2["t0"] + 0.05) / 0.25)
            txt(d, (W / 2, 400), "¿SOBREVIVIRÍAS?", int(104 + 16 * k), GREEN, A, sw=9)
            x, y, _ = cam.proj([(Z0[0], R_P, Z0[1])])
            ring_marker(d, float(x[0]), float(y[0]), t, GREEN, A, 90)
    elif name == "cornell":
        draw_label(layer, t, FL[0] + 0.1, CIU0 - 0.05, "CORNELL", ["simuló un brote con", "300 MILLONES de personas"], WHITE, 130)
        draw_label(layer, t, CIU0 - 0.05, FL[1] + 0.05, "LAS CIUDADES", ["caen PRIMERO"], RED, 130)
        n = sum(1 for ti in T_INF if ti <= t)
        A = int(255 * fade(t, FL[0] + 0.3, FL[1] + 0.05))
        if A > 0:
            cx, cy = W / 2, 1560
            box(layer, [cx - 270, cy - 70, cx + 270, cy + 70], (8, 10, 14, int(210 * A / 255)), GREEN + (A,), 4)
            d = ImageDraw.Draw(layer)
            txt(d, (cx, cy), f"{100 * n / len(CROWD):.0f}% INFECTADOS", 60, GREEN, A, sw=5)
    elif name == "split":
        A = int(255 * fade(t, FL[1] + 0.05, FL[2] + 0.05))
        nd = np.mean(TD <= t); ns = np.mean(TS <= t)
        for xx, nm, v in ((W * 0.27, "CIUDAD", nd), (W * 0.73, "CAMPO", ns)):
            txt(d, (xx, 1480), nm, 62, WHITE, A, sw=6)
            txt(d, (xx, 1570), f"{100 * v:.0f}%", 84, GREEN, A, sw=7)
        draw_label(layer, t, FL[1] + 0.1, FL[2], "MÁS GENTE JUNTA", ["= contagio más RÁPIDO"], RED, 112)
    elif name == "huir":
        draw_label(layer, t, FL[3] + 0.1, HUI0 + 3.6, "¡HUYE!", ["SEMANAS para llegar al campo"], YELLOW, 150)
        draw_label(layer, t, HUI0 + 3.6, FL[4] + 0.05, "MESES", ["para llegar a las montañas"], YELLOW, 150)
        x, y, _ = cam.proj([(0.0, 0.7, -2.0 - 1.1 * (t - HUI0))])
        A = int(255 * fade(t, FL[3] + 0.3, FL[4]))
        txt(d, (float(x[0]), float(y[0]) - 40), "TÚ", 54, WHITE, A, sw=6)
    elif name == "ottawa":
        draw_label(layer, t, FL[4] + 0.1, BREAK + 0.1, "MODELO DE OTTAWA", ["(2009)"], WHITE, 104)
        draw_label(layer, t, BREAK + 0.1, FL[5] + 0.05, "LA CUARENTENA", ["NO BASTA: actúa rápido"], RED, 120)
    elif name == "calma":
        p2 = P("cierre", 1)
        draw_label(layer, t, FL[7] + 0.1, p2[1] + 0.25, "DUERME", ["TRANQUILO"], WHITE, 160, y0=420)
        draw_endcard(layer, t, p2[1] + 0.15)


def draw_cdmx(layer, t, O):
    d = ImageDraw.Draw(layer)
    x, y = project(O, (0.0, 0.35, 2.2))
    al = fade(t, FL[2] + 1.6, FL[3] + 0.05, 0.3)
    if al > 0:
        A = int(255 * al)
        ring_marker(d, x, y, t, GREEN, A, 120)
        d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=GREEN + (A,), outline=INK + (A,), width=4)
        bx = x + 36
        box(layer, [bx, y - 140, bx + 260, y - 52], (8, 10, 14, int(215 * al)), GREEN + (A,), 4, 28)
        d = ImageDraw.Draw(layer)
        txt(d, (bx + 130, y - 96), "CDMX", 50, WHITE, A, sw=4)
    draw_label(layer, t, FL[2] + 0.1, FL[3], "+9 MILLONES", ["viven en la CDMX"], GREEN, 140)


def draw_hongo(layer, t, O):
    d = ImageDraw.Draw(layer)
    s = t - HON0
    # patas de la hormiga
    for k, (ax, ay) in enumerate([(-0.25, -0.55), (0.0, -0.6), (0.25, -0.55)]):
        for sx in (-1, 1):
            p0 = project(O, (sx * 0.15 + ax * 0.2, -0.32, 0.25 * ax))
            p1 = project(O, (sx * 0.55 + ax, -0.45, 0.4 * ax))
            p2 = project(O, (sx * 0.75 + ax * 1.3, -0.9 + 0.03 * math.sin(t * 3 + k), 0.5 * ax))
            d.line([p0, p1, p2], fill=(25, 18, 14, 255), width=9, joint="curve")
    # ramita
    d.line([project(O, (-3, -1.0, 0)), project(O, (3, -0.85, 0))], fill=(70, 50, 30, 255), width=26)
    # esporas
    if s > 2.2:
        for i, (sx_, sy_, sp, ph) in enumerate(SPORES):
            u = ((s - 2.2) * 0.35 * sp + ph / 6) % 1.0
            px, py = project(O, (sx_ * (0.4 + u), 2.0 - 3.5 * u, 0.3))
            A = int(220 * (1 - u) * min(1.0, (s - 2.2) / 0.5))
            r = 4 + 3 * (i % 3)
            d.ellipse([px - r, py - r, px + r, py + r], fill=(200, 255, 160, A))
    draw_label(layer, t, FL[5] + 0.1, HON0 + 2.6, "LOS ZOMBIS", ["YA EXISTEN"], GREEN, 140)
    draw_label(layer, t, HON0 + 2.6, FL[6] + 0.05, "OPHIOCORDYCEPS", ["el hongo que controla", "a las hormigas"], GREEN, 100)


def draw_calor(layer, t, O):
    d = ImageDraw.Draw(layer)
    s = t - CIE0
    cx, cy = project(O, (0, 0, 0))
    for i in range(36):
        a = i * 2.4 + 0.3
        u = ((s * 0.55 + i / 36) % 1.0)
        rr = lerp(560, 230, u)
        px, py = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        if u < 0.92:
            A = int(230 * min(1.0, u * 4))
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(140, 255, 120, A))
        else:
            for k in range(4):
                b = a + k * 1.57
                d.line([px, py, px + 22 * math.cos(b), py + 22 * math.sin(b)], fill=(255, 190, 90, 220), width=4)
    draw_label(layer, t, FL[6] + 0.1, FL[7] + 0.05, "37 °C", ["el calor de tu cuerpo", "lo DESTRUYE"], YELLOW, 170)


def grade(u8, t, name):
    f = u8.astype(np.float32) / 255.0
    lum = f @ np.array([0.3, 0.59, 0.11], np.float32)
    tint = np.array([0.80, 1.02, 0.92], np.float32) if name not in ("calor",) else np.array([1.05, 0.95, 0.85], np.float32)
    f = (f * 0.7 + lum[..., None] * 0.3) * tint
    f *= VIG
    fl = 1.0
    if name in ("hook",) and 1.2 < t < 3.2:
        fl = 0.75 + 0.25 * (math.sin(t * 37) > -0.6)
    f *= fl
    f += GRAIN[int(t * 30) % len(GRAIN)]
    return (np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8)


_gy, _gx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.55 * np.clip((((_gx - W / 2) / (W * 0.62)) ** 2 + ((_gy - H * 0.5) / (H * 0.58)) ** 2), 0, 1) ** 1.4)[..., None].astype(np.float32)
_rg = np.random.default_rng(3)
GRAIN = [(_rg.standard_normal((H, W, 1)) * 0.022).astype(np.float32) for _ in range(6)]
del _gy, _gx


def overlays(frame_u8, t, name, O, cam):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if name == "cdmx":
        draw_cdmx(layer, t, O)
    elif name == "hongo":
        pass
    elif name == "calor":
        draw_calor(layer, t, O)
    else:
        draw_city_labels(layer, t, name, cam)
    if name == "hongo":
        hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_hongo(hl, t, O)
        layer.alpha_composite(hl)
    draw_caption(layer, t)
    draw_watermark(layer)
    im.alpha_composite(layer)
    fa = flash_alpha(t)
    if fa > 0:
        fl = Image.new("RGBA", (W, H), (255, 246, 225, int(235 * fa)))
        im.alpha_composite(fl)
        if fa > 0.35:
            b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(b).polygon(bolt(W / 2, H / 2, 420), fill=YELLOW + (int(255 * min(1, (fa - 0.35) / 0.4)),))
            im.alpha_composite(b)
    return np.asarray(im.convert("RGB"))


SKY = np.zeros((H, W, 3), np.float32)
_yy = np.arange(H, dtype=np.float32)[:, None]
SKY += (np.exp(-((_yy - 300) / 260.0) ** 2) * 0.05)[..., None] * np.array([0.6, 0.15, 0.08], np.float32)
del _yy


def render(t):
    name, cam, items = scene(t)
    O = np.array([0.0, 0.0, 9.0])
    img = BG.copy() * 0.6 + SKY
    if cam is not None:
        if name == "huir":
            _, _, _ = cam.proj([(0.0, 0.0, -400.0)])
            hy = float(cam.proj([(0.0, 0.0, -400.0)])[1][0])
            ml = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            pts = [(0, hy + 4)]
            for k, x in enumerate(np.linspace(0, W, 13)):
                pts.append((float(x), hy - (90 + 150 * abs(math.sin(k * 1.7 + 0.4))) * (0.6 + 0.4 * (k % 2))))
            pts.append((W, hy + 4))
            ImageDraw.Draw(ml).polygon(pts, fill=(10, 14, 20, 255))
            comp_layer(img, ml)
        if name in ("hook", "calma"):
            sk, hy = skyline_layer(cam, t, 0.5 if name == "hook" and 1.2 < t < 3.2 else 1.0)
            if True:
                blit(img, "moon", W * 0.78, max(80.0, hy - 330), 46, 1.0)
            comp_layer(img, sk)
        comp_layer(img, ground_layer(cam, t, spacing=2.4 if name != "huir" else 3.0))
        draw_crowd(img, cam, items)
        O = cam.p
    elif name == "cdmx":
        u = ease((t - FL[2]) / 2.0)
        spin = math.radians(lerp(-40, -99.13, u)); tilt = lerp(5, 19.43, u)
        O = np.array([0.0, 0.1, 9.6 - 0.9 * ease((t - FL[2]) / (FL[3] - FL[2]))])
        draw_sphere(img, O, dict(kind="earth", c=(0.0, 0.35, 0.0), r=2.2, tilt=tilt, spin=spin, gain=0.42), t)
    elif name == "hongo":
        s = t - HON0
        O = np.array([-0.1, 0.55, 8.4 - 0.7 * ease(s / 6)])
        bodies = [dict(kind="gold", c=(-0.95, -0.3, 0.0), r=0.62, gain=0.07), dict(kind="gold", c=(0.0, -0.32, 0.0), r=0.34, gain=0.07),
                  dict(kind="gold", c=(0.62, -0.18, 0.0), r=0.40, gain=0.07)]
        g = ease_out((s - 0.6) / 2.2)
        for k in range(12):
            h = k / 11
            if h > g:
                break
            bodies.append(dict(kind="ice", c=(0.66 + 0.06 * math.sin(h * 3), 0.2 + 2.0 * h, 0.0), r=0.11 + 0.02 * math.sin(k), gain=0.9))
        if g > 0.95:
            bodies.append(dict(kind="ice", c=(0.66 + 0.06 * math.sin(3), 2.25, 0.0), r=0.26 * ease_out((s - 2.6) / 0.6), gain=1.2))
        bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"], float) - O)))
        for b in bodies:
            draw_sphere(img, O, b, t)
    elif name == "calor":
        O = np.array([0.0, 0.0, 6.0])
        k = 1.0 + 0.06 * math.sin(t * 7.0)
        blit(img, "warm", W / 2, H / 2, 210 * k, 1.0)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    u8 = grade(u8, t, name)
    return overlays(u8, t, name, O, cam)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        for ts in sys.argv[2:]:
            t = float(ts)
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, scene(t)[0], flush=True)
    elif mode == "chunk":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(render(f / FPS).tobytes())
            if f % 30 == 0:
                print(f"{out}: {f}/{b}", flush=True)
        p.stdin.close(); p.wait()
        print("listo", out, flush=True)
    elif mode == "info":
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL])
