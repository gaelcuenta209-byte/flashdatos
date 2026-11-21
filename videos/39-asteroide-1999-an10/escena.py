"""Flash Datos · video 39: el asteroide (137108) 1999 AN10 pasará a ~390,000 km de la Tierra el 7 ago 2027.

Escena nueva: asteroide irregular trazado por pasos sobre un mapa de alturas con cráteres; comparación con
una cordillera y regla 800 m – 1.8 km; calendario 7 AGO 2027; diagrama con la Tierra, la órbita de la Luna
y la trayectoria del asteroide con contador de distancia; barras Luna vs 1999 AN10; margen de ±160 km;
vista por binoculares; cierre con la Tierra (América de frente) y el asteroide pasando.

Uso:
  python3 escena.py test 1 5 12 ...
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

def draw_earth(img, cam, C, r, t, atm=0.03, glow=0.55, expo=1.0):
    C = np.asarray(C, float)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    cx, cy, _ = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
    if dist < r * 1.6 or rel @ cam.f <= 0:
        x0, x1, y0, y1 = 0, W, 0, H
    else:
        rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
        ext = rpx * (1.0 + 5 * atm) + 4
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
    alpha = np.clip((r - dd) / pixw + 0.5, 0, 1) * (b < 0)
    region = img[y0:y1, x0:x1]
    hz = (dd > r * 0.995) & (dd < r * (1.0 + 4 * atm)) & (b < 0)
    if hz.any():
        P = cam.O + (-b[hz])[:, None] * d[hz]
        nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
        lit = np.clip(nn @ LIGHT + 0.4, 0, 1)
        gl = np.exp(-np.maximum((dd[hz] - r) / (atm * r), 0)) * lit * glow
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
    col = col * expo
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


# ---------------- partículas (eyección, estela) ----------------

def splat(img, cam, P, col, size=1.0):
    """Suma puntos luminosos HDR (P: Nx3, col: Nx3) con un núcleo pequeño + halo a 1/4 de resolución."""
    if len(P) == 0:
        return
    x, y, z = cam.proj(P)
    ok = (z > 1e-4) & (x > -20) & (x < W + 20) & (y > -20) & (y < H + 20)
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



def bloom(img):
    small = img[::4, ::4]
    br = np.clip(small - 0.85, 0, None)
    g = gaussian_filter(br, (5, 5, 0)) * 0.55 + gaussian_filter(br, (22, 22, 0)) * 0.8 + gaussian_filter(br, (60, 60, 0)) * 0.45
    return img + ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)


TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
SPLIT = lambda k, f: S0[k] + (S1[k] - S0[k]) * f
CARD = S1["cierre"] + 0.25
RE_KM = 6371.0
FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); RED = (255, 90, 70); ORANGE = (255, 160, 70)
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
    txt(d, (W / 2, 1185), "del espacio y la tecnología", 52, CYAN, A, "Inter-ExtraBold.otf", 6)


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
def glow(layer, x, y, r, col, A):
    """Halo suave (a 1/4 de resolución) sobre la capa de textos/naves."""
    if A <= 0 or r < 2:
        return
    q = 4
    sz = int(r * 2.6 / q) + 4
    g = Image.new("RGBA", (sz * 2, sz * 2), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([sz - r / q, sz - r / q, sz + r / q, sz + r / q], fill=col + (int(A),))
    from PIL import ImageFilter
    g = g.filter(ImageFilter.GaussianBlur(r / q * 0.55)).resize((sz * 2 * q, sz * 2 * q), Image.BILINEAR)
    layer.alpha_composite(g, (int(x - sz * q), int(y - sz * q))) if 0 <= x - sz * q and 0 <= y - sz * q and x + sz * q < W and y + sz * q < H else _paste(layer, g, int(x - sz * q), int(y - sz * q))


def _paste(layer, g, x0, y0):
    big = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    big.paste(g, (x0, y0))
    layer.alpha_composite(big)






# =====================================================================
#  VIDEO 39 · asteroide (137108) 1999 AN10 · escena nueva
# =====================================================================

# ---------------- asteroide: mapa de alturas sobre la esfera, trazado por pasos ----------------
def _sphere_grid(h, w):
    la = (0.5 - (np.arange(h) + 0.5) / h) * np.pi
    lo = ((np.arange(w) + 0.5) / w) * 2 * np.pi - np.pi
    LO, LA = np.meshgrid(lo, la)
    return np.stack([np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO)], -1)


def make_asteroid():
    cache = os.path.join(BASE, "tex", "an10.npz")
    if os.path.exists(cache):
        z = np.load(cache)
        return z["hm"], z["alb"]
    hh, ww = 256, 512
    v = _sphere_grid(hh, ww)
    a, b, c = 1.22, 0.84, 0.95                     # forma alargada, como una papa
    re = 1.0 / np.sqrt((v[..., 0] / a) ** 2 + (v[..., 1] / b) ** 2 + (v[..., 2] / c) ** 2)
    n1 = fbm(v[..., 0] * 1.4 + 3, v[..., 1] * 1.4, v[..., 2] * 1.4, 4, seed=5)
    n2 = fbm(v[..., 0] * 5 + 1, v[..., 1] * 5, v[..., 2] * 5, 4, seed=9)
    hm = re * (1 + 0.30 * (n1 - 0.5) + 0.06 * (n2 - 0.5))
    rng = np.random.default_rng(39)
    crat = np.zeros((hh, ww))
    for i in range(46):
        cdir = rng.normal(size=3); cdir /= np.linalg.norm(cdir)
        rad = 0.07 + 0.30 * rng.random() ** 2.4
        ang = np.arccos(np.clip(v @ cdir, -1, 1)) / rad
        bowl = np.where(ang < 1, -(1 - ang ** 2), 0) * 0.9
        rim = np.exp(-((ang - 1.05) / 0.16) ** 2) * 0.35
        crat += (bowl + rim) * rad * 0.22
    hm = hm * (1 + crat)
    alb = 0.55 + 0.35 * (n2 - 0.5) + 0.25 * (fbm(v[..., 0] * 9, v[..., 1] * 9, v[..., 2] * 9, 3, seed=2) - 0.5)
    alb = alb - np.clip(-crat * 2.0, 0, 0.25)
    np.savez(cache, hm=hm.astype(np.float32), alb=alb.astype(np.float32))
    return hm.astype(np.float32), alb.astype(np.float32)


HM, ALB = make_asteroid()
HMAX = float(HM.max())
ROCK = lin((0.50, 0.45, 0.40))


def rotm(yaw, pitch=0.0, roll=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def draw_asteroid(img, cam, C, R, M, light=None, q=2, tint=1.0):
    """Asteroide irregular trazado por pasos sobre un mapa de alturas. M: rotación local->mundo."""
    L = LIGHT if light is None else light
    C = np.asarray(C, float)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    Rb = R * HMAX * 1.02
    if rel @ cam.f <= Rb:
        return None
    cx, cy, _ = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
    rpx = math.tan(math.asin(min(Rb / dist, 0.999))) / PIX
    if rpx < 5:
        splat(img, cam, C[None], (np.array([1.0, 0.92, 0.8]) * 0.5 * max(rpx, 1.2) ** 2 / 4)[None], 1.0)
        return (cx, cy, rpx)
    ext = rpx * 1.08 + 6
    x0 = int(max(0, cx - ext)); x1 = int(min(W, cx + ext + 1))
    y0 = int(max(0, cy - ext)); y1 = int(min(H, cy + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return (cx, cy, rpx)
    d = cam.dirs(y0, y1, x0, x1)[::q, ::q]
    sh = d.shape[:2]
    d = d.reshape(-1, 3)
    oc = cam.O - C
    b = d @ oc
    disc = b * b - (oc @ oc - Rb * Rb)
    ok = disc > 0
    tn = np.where(ok, -b - np.sqrt(np.maximum(disc, 0)), 0)
    tf = np.where(ok, -b + np.sqrt(np.maximum(disc, 0)), 0)
    tt = tn.copy()
    hit = np.zeros(len(d), bool)
    act = np.where(ok)[0]
    Mi = M  # p_local = p_world_rel @ M   (M ortonormal: local->mundo)
    for it in range(48):
        if len(act) == 0:
            break
        p = oc + tt[act, None] * d[act]
        pl = p @ Mi
        rr = np.linalg.norm(pl, axis=-1)
        u = pl / rr[:, None]
        la, lo = latlon(u)
        h = R * sample(HM, la, lo)
        f = rr - h
        done = f < R * 0.0025
        hit[act[done]] = True
        tt[act] += np.where(done, 0, f * 0.55)
        gone = tt[act] > tf[act]
        act = act[~done & ~gone]
    P = oc + tt[:, None] * d
    P = P.reshape(sh + (3,)); hitg = hit.reshape(sh)
    dPx = np.gradient(P, axis=1); dPy = np.gradient(P, axis=0)
    n = np.cross(dPx, dPy)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
    Vd = d.reshape(sh + (3,))
    flip = (n * Vd).sum(-1) > 0
    n[flip] *= -1
    radial = P / (np.linalg.norm(P, axis=-1, keepdims=True) + 1e-12)
    # en los bordes el gradiente mezcla fondo: usar la normal radial
    edge = ~(np.roll(hitg, 1, 0) & np.roll(hitg, -1, 0) & np.roll(hitg, 1, 1) & np.roll(hitg, -1, 1))
    n[edge] = radial[edge] * 0.6 + n[edge] * 0.4
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
    pl = P.reshape(-1, 3) @ Mi
    u = pl / (np.linalg.norm(pl, axis=-1, keepdims=True) + 1e-12)
    la, lo = latlon(u)
    alb = sample(ALB, la, lo).reshape(sh)
    ndl = (n * L).sum(-1)
    diff = np.clip(ndl, 0, 1) ** 0.9
    mu = np.clip(-(n * Vd).sum(-1), 0, 1)
    shade_ = (0.012 + 2.3 * diff + 0.05 * (1 - mu) ** 3)
    col = ROCK[None, None, :] * (alb * shade_)[..., None] * tint
    a = gaussian_filter(hitg.astype(np.float32), 0.55)
    if q > 1:
        col = ndzoom(col, (q, q, 1), order=1)
        a = ndzoom(a, (q, q), order=1)
    hh, ww = y1 - y0, x1 - x0
    col = col[:hh, :ww]; a = np.clip(a[:hh, :ww], 0, 1)
    if col.shape[0] < hh or col.shape[1] < ww:
        pc = np.zeros((hh, ww, 3), np.float32); pa = np.zeros((hh, ww), np.float32)
        pc[:col.shape[0], :col.shape[1]] = col; pa[:a.shape[0], :a.shape[1]] = a
        col, a = pc, pa
    region = img[y0:y1, x0:x1]
    region[:] = region * (1 - a[..., None]) + col * a[..., None]
    return (cx, cy, rpx)


# ---------------- Luna ----------------
def make_moon():
    v = _sphere_grid(256, 512)
    m = fbm(v[..., 0] * 2 + 7, v[..., 1] * 2, v[..., 2] * 2, 5, seed=13)
    maria = smooth(0.52, 0.60, m) * 0.45
    fine = fbm(v[..., 0] * 12, v[..., 1] * 12, v[..., 2] * 12, 3, seed=3)
    return (0.70 - maria + 0.18 * (fine - 0.5)).astype(np.float32)


MOONT = make_moon()


def draw_moon(img, cam, C, r):
    C = np.asarray(C, float)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    if rel @ cam.f <= r:
        return
    cx, cy, _ = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
    rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
    if rpx < 1.5:
        splat(img, cam, C[None], np.array([[0.5, 0.5, 0.5]]) * max(rpx, 0.6) ** 2, 1.0)
        return
    ext = rpx + 4
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
    alpha = np.clip((r - dd) / pixw + 0.5, 0, 1) * (b < 0)
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]; bs = b[sel]
    tt = -bs - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = cam.O + tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    la, lo = latlon(n)
    alb = sample(MOONT, la, lo)
    col = (alb * (0.01 + 2.0 * np.clip(n @ LIGHT, 0, 1)))[:, None] * lin((0.80, 0.79, 0.76))
    region = img[y0:y1, x0:x1]
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


# ---------------- montañas (silueta 2D en el HDR) ----------------
def ridge(seed, n, base, amp, rough):
    rng = np.random.default_rng(seed)
    xs_ = np.linspace(-80, W + 80, n)
    ys_ = np.zeros(n)
    k = 1.0
    for o in range(6):
        ph = rng.random() * 10
        ys_ += amp * k * np.sin(xs_ / W * (2 + o * 2.3) * math.pi + ph) * (rough ** o)
        k *= 0.6
    return xs_, base - np.abs(ys_)


RIDGES = [ridge(1, 240, 1600, 230, 0.55), ridge(2, 240, 1720, 170, 0.6), ridge(3, 240, 1840, 120, 0.6)]


def draw_mountains(img, rise):
    lay = Image.new("RGB", (W, H), (0, 0, 0))
    msk = Image.new("L", (W, H), 0)
    cols = [(0.012, 0.018, 0.040), (0.007, 0.011, 0.026), (0.003, 0.005, 0.012)]
    for (xs_, ys_), c in zip(RIDGES, cols):
        pts = [(float(x), float(y + rise)) for x, y in zip(xs_, ys_)] + [(W + 80, H + 10), (-80, H + 10)]
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon(pts, fill=255)
        ma = np.asarray(m, np.float32)[..., None] / 255
        img[:] = img * (1 - ma) + np.array(c, np.float32) * ma
        # borde iluminado
        e = Image.new("L", (W, H), 0)
        ImageDraw.Draw(e).line([(float(x), float(y + rise)) for x, y in zip(xs_, ys_)], fill=255, width=3)
        ea = gaussian_filter(np.asarray(e, np.float32) / 255, 1.2)[..., None]
        img += ea * np.array([0.10, 0.16, 0.30], np.float32) * 0.45


# ---------------- mundo del diagrama: Tierra en el centro, órbita lunar y trayectoria ----------------
RE_V = 7.0          # radio de la Tierra en el diagrama (no está a escala)
R_MOON = 60.0       # 384,400 km
R_AN10 = R_MOON * 389866 / 384400   # ≈ 1.014 distancias lunares medias
RMOON_V = 2.4
DIR_IN = np.array([1.0, 0.0, -0.18]); DIR_IN /= np.linalg.norm(DIR_IN)
PERP = np.array([0.18, 0.0, 1.0]); PERP /= np.linalg.norm(PERP)
CA = PERP * R_AN10                  # punto de máximo acercamiento
MOON_ANG = math.radians(240)        # la Luna esa noche estaba lejos del asteroide (~763,000 km)
MOON_P = np.array([math.cos(MOON_ANG), 0.0, math.sin(MOON_ANG)]) * R_MOON


def path_pt(s):
    """s en [-1, 1]: posición a lo largo de la trayectoria (s=0: máximo acercamiento)."""
    return CA + DIR_IN * s * 140.0


def circle3d(R, n=200, y=0.0):
    a = np.linspace(0, 2 * np.pi, n)
    return np.stack([np.cos(a) * R, np.full(n, y), np.sin(a) * R], -1)


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def poly3d(d, cam, pts, col, A, width=6, behind=None, dash=0):
    x, y, z = cam.proj(pts)
    vis = z > 0.1
    if behind is not None:
        C, r = behind
        rel = pts - cam.O
        dist = np.linalg.norm(rel, axis=-1)
        dirn = rel / dist[:, None]
        oc = cam.O - C
        b = dirn @ oc
        disc = b * b - (oc @ oc - r * r)
        tnear = -b - np.sqrt(np.maximum(disc, 0))
        vis &= ~((disc > 0) & (tnear < dist) & (tnear > 0))
    seg = []
    for i in range(len(pts) - 1):
        if dash and (i // dash) % 2 == 1:
            continue
        if vis[i] and vis[i + 1]:
            d.line([(x[i], y[i]), (x[i + 1], y[i + 1])], fill=col + (A,), width=width)


def cam_orbit(dist, elev, azim, target=(0, 0, 0)):
    tg = np.asarray(target, float)
    e, a = math.radians(elev), math.radians(azim)
    pos = tg + dist * np.array([math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)])
    return Cam(pos, tg)


def an10_spin(t):
    return rotm(0.55 * t, 0.35 + 0.12 * t, 0.2)


# ---------------- tomas ----------------
FIRST = ["gancho", "nombre", "fecha", "luna", "seguro", "binoculares", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.22) for i, k in enumerate(FIRST)]
FL = [b for _, b in SHOTS[1:]] + [CARD - 0.05]


def scene(t):
    name = SHOTS[0][0]
    for k, a in SHOTS:
        if t >= a:
            name = k
    return name


def span(name):
    a0 = dict(SHOTS)[name]
    nxt = [b for k, b in SHOTS if b > a0]
    return a0, (nxt[0] if nxt else END + 1)


def sh_gancho(img, t):
    a0, a1 = span("gancho")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.3 - 0.6 * s, 0.2 + 0.2 * s, 7.6 - 1.2 * ease_out(s)), (0.05, -0.55, 0))
    draw_earth(img, cam, (-9, -30, -70), 9.0, t)
    draw_moon(img, cam, (14, -22, -60), 1.6)
    info = draw_asteroid(img, cam, (0, 0, 0), 1.0, an10_spin(t), q=2)
    return cam, dict(rock=info)


def sh_nombre(img, t):
    a0, a1 = span("nombre")
    s = (t - a0) / (a1 - a0)
    draw_mountains(img, 60 * (1 - ease_out(s * 2)))
    cam = Cam((0, 0, 8.4 - 0.5 * s), (0, 0.55, 0))
    info = draw_asteroid(img, cam, (0, 0.06 * math.sin(t * 1.3), 0), 1.0, an10_spin(t), q=2)
    return cam, dict(rock=info, s=s)


def plane_cam(t):
    """Cámara del diagrama: recorre fecha -> luna -> seguro."""
    f0, l0, g0, b0 = dict(SHOTS)["fecha"], dict(SHOTS)["luna"], dict(SHOTS)["seguro"], dict(SHOTS)["binoculares"]
    if t < l0:
        s = ease((t - f0) / (l0 - f0))
        return cam_orbit(250 - 30 * s, 26 + 6 * s, 20 - 25 * s), s
    if t < g0:
        s = ease((t - l0) / 1.6)
        return cam_orbit(220 + 40 * s, 32 + 40 * s, -5 - 10 * s), s
    s = ease((t - g0) / 2.2)
    tg = path_pt(an10_s(t)) * s
    return cam_orbit(260 - 215 * s, 72 - 52 * s, -15 + 75 * s, tg), s


def an10_s(t):
    f0, b0 = dict(SHOTS)["fecha"], dict(SHOTS)["binoculares"]
    g0 = dict(SHOTS)["seguro"]
    # entra, llega al máximo acercamiento al empezar "luna" y avanza muy despacio después
    l0 = dict(SHOTS)["luna"] + 0.6
    if t < l0:
        return -1.0 + ease_out((t - f0) / (l0 - f0))
    return 0.0 + 0.0025 * (t - l0)


def sh_plano(img, t):
    cam, s = plane_cam(t)
    draw_earth(img, cam, (0, 0, 0), RE_V, t * 0.6, atm=0.05, glow=0.7)
    draw_moon(img, cam, MOON_P, RMOON_V)
    P = path_pt(an10_s(t))
    name = scene(t)
    R = 1.3 if name != "seguro" else 1.3 + 2.2 * ease((t - dict(SHOTS)["seguro"]) / 2.4)
    info = draw_asteroid(img, cam, P, R, an10_spin(t), q=2)
    return cam, dict(P=P, rock=info)


def sh_binoculares(img, t):
    a0, a1 = span("binoculares")
    s = (t - a0) / (a1 - a0)
    # campo de estrellas más denso, desplazándose despacio
    sh = int(40 * s)
    img[:] = np.roll(BG, sh, axis=1) * 1.8 + np.array([0.006, 0.010, 0.022], np.float32)
    rng = np.random.default_rng(77)
    n = 900
    P = np.stack([rng.uniform(-1, 1, n) * 1.0, rng.uniform(-1, 1, n) * 1.8], -1)
    xs_ = ((P[:, 0] + 1) / 2 * W + sh) % W; ys_ = (P[:, 1] + 1.8) / 3.6 * H
    br = 0.03 + 0.5 * rng.random(n) ** 6
    np.add.at(img, (ys_.astype(int).clip(0, H - 1), xs_.astype(int).clip(0, W - 1)), (br[:, None] * np.array([0.9, 0.95, 1.0])))
    # el asteroide: un punto que cruza el campo, como una estrella que se mueve
    x = W * (0.82 - 0.62 * s); y = H * (0.30 + 0.16 * s)
    k = 3.2 * smooth(0.0, 0.25, s)
    small = np.zeros((H // 2, W // 2, 3), np.float32)
    small[int(y / 2), int(x / 2)] = np.array([1.0, 0.93, 0.80]) * 60 * k
    img += ndzoom(gaussian_filter(small, (1.0, 1.0, 0)) + gaussian_filter(small, (5, 5, 0)) * 0.4, (2, 2, 1), order=1)[:H, :W]
    return None, dict(x=x, y=y, s=s)


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    s = (t - a0) / (END - a0)
    cam = Cam((0, 1.5, 9.0), (0, -1.2, 0))
    # Tierra grande abajo, con América de frente
    draw_earth(img, cam, (1.5, -27, -58), 12.5, t * 0.5, atm=0.03, glow=0.6, expo=0.85)
    draw_moon(img, cam, (-16, 14, -85), 2.6)
    P = np.array([3.6 - 7.0 * s, -0.7 - 0.4 * s, -2.0 + 1.5 * math.sin(s * 2.4)])
    info = draw_asteroid(img, cam, P, 1.25, an10_spin(t), q=2)
    return cam, dict(rock=info, s=s)


SCENES = dict(gancho=sh_gancho, nombre=sh_nombre, fecha=sh_plano, luna=sh_plano, seguro=sh_plano,
              binoculares=sh_binoculares, cierre=sh_cierre)


# ---------------- textos y gráficos de cada toma ----------------
def calendar(layer, t, a, b, y0=560):
    al = fade(t, a, b, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    k = ease_out((t - a) / 0.45)
    w_, h_ = 330 * (0.8 + 0.2 * k), 330 * (0.8 + 0.2 * k)
    d = ImageDraw.Draw(layer)
    x0, y1 = W / 2 - w_ / 2, y0 - h_ / 2
    d.rounded_rectangle([x0, y1, x0 + w_, y1 + h_], 28, fill=(245, 247, 252, A))
    d.rounded_rectangle([x0, y1, x0 + w_, y1 + h_ * 0.28], 28, fill=(230, 60, 60, A))
    d.rectangle([x0, y1 + h_ * 0.16, x0 + w_, y1 + h_ * 0.28], fill=(230, 60, 60, A))
    d.text((W / 2, y1 + h_ * 0.14), "AGOSTO 2027", font=font("Inter-Black.otf", int(44 * w_ / 330)), fill=(255, 255, 255, A), anchor="mm")
    d.text((W / 2, y1 + h_ * 0.64), "7", font=font("Inter-Black.otf", int(190 * w_ / 330)), fill=(20, 24, 36, A), anchor="mm")


def bars(layer, t, a, b):
    al = fade(t, a, b, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k1 = ease_out((t - a) / 0.8); k2 = ease_out((t - a - 0.5) / 0.8)
    L = 820
    x0 = W / 2 - L / 2
    y = 470
    txt(d, (x0, y - 46), "LUNA (promedio)", 44, CYAN, A, "Inter-ExtraBold.otf", 6, "lm")
    d.rounded_rectangle([x0, y - 16, x0 + max(L * k1, 2), y + 16], 12, fill=CYAN + (A,))
    txt(d, (x0 + L, y - 46), "384,400 km", 44, WHITE, int(A * min(1, k1 * 2)), "Inter-ExtraBold.otf", 6, "rm")
    y = 590
    txt(d, (x0, y - 46), "1999 AN10", 44, YELLOW, A, "Inter-ExtraBold.otf", 6, "lm")
    d.rounded_rectangle([x0, y - 16, x0 + max(L * 389866 / 384400 * k2, 2), y + 16], 12, fill=YELLOW + (A,))
    txt(d, (x0 + L * 1.014, y - 46), "389,900 km", 44, WHITE, int(A * min(1, k2 * 2)), "Inter-ExtraBold.otf", 6, "rm")


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    if name == "gancho":
        draw_label(layer, t, -1, 2.7, "¿UNA MONTAÑA?", ["pasando junto a la Tierra"], YELLOW, 120)
        calendar(layer, t, 2.75, a1 + 0.1, 560)
        cx, cy, r = ex["rock"]
    elif name == "nombre":
        draw_label(layer, t, a0 + 0.1, a1, "1999 AN10", ["asteroide cercano a la Tierra"], YELLOW, 130)
        cx, cy, r = ex["rock"]
        A = int(255 * fade(t, S0["nombre"] + 2.6, a1))
        if A > 0:
            k = ease_out((t - S0["nombre"] - 2.6) / 0.6)
            yy = cy + r * 0.62 + 30
            hw = r * 0.62 * k
            d.line([(cx - hw, yy), (cx + hw, yy)], fill=YELLOW + (A,), width=6)
            for sx in (-1, 1):
                d.line([(cx + sx * hw, yy - 22), (cx + sx * hw, yy + 22)], fill=YELLOW + (A,), width=6)
            txt(d, (cx, yy + 62), "800 m – 1.8 km", 64, WHITE, A, "Inter-Black.otf", 8)
    elif name in ("fecha", "luna", "seguro"):
        behind = (np.zeros(3), RE_V)
        f0 = dict(SHOTS)["fecha"]
        # órbita de la Luna
        Am = int(255 * min(1.0, (t - f0) / 0.6))
        poly3d(d, cam, circle3d(R_MOON, 240), CYAN, int(Am * 0.75), 4, behind)
        # trayectoria del asteroide (lo recorrido y lo que falta, punteado)
        s_now = an10_s(t)
        ss = np.linspace(-1, s_now, 120)
        poly3d(d, cam, np.array([path_pt(v) for v in ss]), YELLOW, 235, 6, behind)
        ss2 = np.linspace(s_now, 1, 120)
        poly3d(d, cam, np.array([path_pt(v) for v in ss2]), YELLOW, 120, 4, behind, dash=3)
        xm, ym, zm = pt(cam, MOON_P)
        xe, ye, _ = pt(cam, np.zeros(3))
        if name == "fecha":
            calendar(layer, t, a0 + 0.15, a1, 520)
            A = int(255 * fade(t, S0["fecha"] + 2.5, a1))
            if A > 0:
                xc, yc, _ = pt(cam, path_pt(min(s_now, 0.0)))
                k = ease_out((t - S0["fecha"] - 2.5) / 1.6)
                d.line([(xe, ye), (xe + (xc - xe) * k, ye + (yc - ye) * k)], fill=WHITE + (A,), width=4)
                km = int(round(390000 * k / 1000.0)) * 1000
                txt(d, (W / 2, 1110), f"{km:,} KM", 92, YELLOW, A)
            if zm > 0:
                marker(d, xm, ym, t, CYAN, int(255 * fade(t, a0 + 0.6, a1)), 22, "LUNA", -1 if xm > W / 2 else 1, 42)
        elif name == "luna":
            bars(layer, t, a0 + 0.2, a1)
            txt(d, (W / 2, 700), "≈ 1.02 DISTANCIAS LUNARES", 60, WHITE, int(255 * fade(t, a0 + 1.2, a1)), "Inter-Black.otf", 8)
            if zm > 0 and ym > 780:
                marker(d, xm, ym, t, CYAN, int(255 * fade(t, a0 + 0.3, a1)), 22, "LUNA", -1 if xm > W / 2 else 1, 42)
            xa, ya, _ = pt(cam, ex["P"])
            marker(d, xa, ya, t, YELLOW, int(255 * fade(t, a0 + 0.3, a1)), 26, "1999 AN10", -1 if xa > W / 2 else 1, 42)
            txt(d, (xe, ye + 54), "TIERRA", 40, WHITE, int(220 * fade(t, a0 + 0.3, a1)), "Inter-ExtraBold.otf", 6)
        else:
            A = int(255 * fade(t, S0["seguro"] + 1.4, a1))
            if A > 0:
                # corredor de incertidumbre (±160 km) dibujado a lo largo de la trayectoria
                xa, ya, _ = pt(cam, ex["P"])
                ss = np.linspace(-0.25, 0.25, 80)
                for off in (-1, 1):
                    pts_ = np.array([path_pt(v) + PERP * off * 0.9 for v in ss])
                    poly3d(d, cam, pts_, CYAN, int(A * 0.9), 4, behind, dash=2)
                draw_label(layer, t, S0["seguro"] + 1.4, S0["seguro"] + 4.0, "± 160 KM", ["de margen en su trayectoria"], CYAN, 124, 380)
            A2 = int(255 * fade(t, S0["seguro"] + 4.0, a1))
            if A2 > 0:
                k = ease_out((t - S0["seguro"] - 4.0) / 0.35)
                cxk, cyk, rk = W / 2, 400, 70 * (0.7 + 0.3 * k)
                d.ellipse([cxk - rk, cyk - rk, cxk + rk, cyk + rk], fill=(40, 200, 110, A2), outline=(255, 255, 255, A2), width=6)
                d.line([(cxk - rk * 0.45, cyk + 2), (cxk - rk * 0.1, cyk + rk * 0.38), (cxk + rk * 0.5, cyk - rk * 0.35)], fill=(255, 255, 255, A2), width=16, joint="curve")
                txt(d, (W / 2, 545), "NO VA A CHOCAR", 84, WHITE, A2)
    elif name == "binoculares":
        # máscara de binoculares
        m = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(m)
        R = 400; cyb = 800
        md.ellipse([W / 2 - 330 - R, cyb - R, W / 2 - 330 + R, cyb + R], fill=255)
        md.ellipse([W / 2 + 330 - R, cyb - R, W / 2 + 330 + R, cyb + R], fill=255)
        from PIL import ImageFilter
        m = m.filter(ImageFilter.GaussianBlur(18))
        dark = Image.new("RGBA", (W, H), (3, 4, 9, 255))
        dark.putalpha(Image.eval(m, lambda v: 255 - v))
        layer.alpha_composite(dark)
        d = ImageDraw.Draw(layer)
        for sx in (-1, 1):
            d.ellipse([W / 2 + sx * 330 - R, cyb - R, W / 2 + sx * 330 + R, cyb + R], outline=(60, 80, 120, 140), width=4)
        A = int(255 * fade(t, a0 + 0.5, a1))
        if A > 0:
            x, y = ex["x"], ex["y"]
            d.ellipse([x - 34, y - 34, x + 34, y + 34], outline=YELLOW + (A,), width=5)
            txt(d, (x, y - 70), "1999 AN10", 46, YELLOW, A, "Inter-Black.otf", 7)
        draw_label(layer, t, a0 + 0.15, a1, "CON BINOCULARES", ["brillo: magnitud ≈ 7.3"], YELLOW, 104, 380)
        A3 = int(255 * fade(t, S0["binoculares"] + 2.6, a1))
        if A3 > 0:
            txt(d, (W / 2, 1150), "mejor desde AMÉRICA", 56, CYAN, A3, "Inter-ExtraBold.otf", 7)
    elif name == "cierre":
        draw_label(layer, t, a0 + 0.2, CARD, "7 · AGO · 2027", ["a ~390,000 km de la Tierra"], YELLOW, 116)
        draw_endcard(layer, t)
    draw_caption(layer, t)
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
    cam, ex = SCENES[name](img, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, name, cam, ex)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        import time
        for ts in sys.argv[2:]:
            t = float(ts); t0 = time.time()
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, scene(t), round(time.time() - t0, 2), "s", flush=True)
    elif mode == "chunk":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(render(f / FPS).tobytes())
            if f % 30 == 0:
                print(f"{out}: {f}/{b}", flush=True)
        p.stdin.close(); p.wait()
        print("listo", out, flush=True)
    elif mode == "info":
        print("frames", NFRAMES, "shots", [(a, round(b, 2)) for a, b in SHOTS], "card", round(CARD, 2))
