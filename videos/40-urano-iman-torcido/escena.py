"""Flash Datos · video 40: Urano en oposición (25 nov 2026) y su campo magnético torcido.

Escena nueva: Urano acostado con anillos y bandas, líneas de campo de un dipolo inclinado 59° y descentrado;
diagrama de la oposición Sol–Tierra–Urano; comparación Tierra (11°) y Neptuno (47°); corte del interior con
agua iónica brillando más hacia adentro e iones en movimiento; la Voyager 2 cruzando el campo; cielo de Tauro.


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
#  VIDEO 40 · Urano: oposición del 25 nov y su imán torcido · escena nueva
# =====================================================================

def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(ax):
    ax = unit(ax)
    ref = np.array([0.0, 0.0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = unit(np.cross(ref, ax)); e2 = np.cross(ax, e1)
    return ax, e1, e2


def tilt_axis(tilt_deg, lean_deg=0.0):
    """Eje inclinado `tilt_deg` respecto a la vertical (en el plano de la pantalla) y `lean_deg` hacia la cámara."""
    a, l = math.radians(tilt_deg), math.radians(lean_deg)
    return unit([math.sin(a) * math.cos(l), math.cos(a) * math.cos(l), math.sin(l)])


def rotate_about(v, k, ang):
    v = np.asarray(v, float); k = unit(k)
    c, s = math.cos(ang), math.sin(ang)
    return v * c + np.cross(k, v) * s + k * (k @ v) * (1 - c)


URANUS_B = lin((0.50, 0.80, 0.86))
NEPTUNE_B = lin((0.18, 0.36, 0.86))


def uranus_col(la, lo, t):
    b = 0.035 * np.sin(la * 9 + 0.6) + 0.02 * np.sin(la * 23 + 1.3) + 0.012 * np.sin(la * 41)
    cap = smooth(0.55, 1.2, la) * 0.16
    return URANUS_B[None, :] * (1 + b + cap)[:, None]


def neptune_col(la, lo, t):
    b = 0.06 * np.sin(la * 11) + 0.03 * np.sin(la * 27 + 2)
    dl = (lo - 0.5 + np.pi) % (2 * np.pi) - np.pi
    spot = np.exp(-((la + 0.38) / 0.10) ** 2 - (dl / 0.22) ** 2) * 0.55
    streak = np.exp(-((la + 0.22) / 0.03) ** 2) * 0.35 * (0.5 + 0.5 * np.sin(lo * 3))
    c = NEPTUNE_B[None, :] * (1 + b - spot)[:, None]
    return c + streak[:, None] * lin((0.85, 0.9, 1.0))[None, :] * 0.6


def draw_planet(img, cam, C, r, ax, colfn, t, spin=0.0, rings=False, atm=(0.30, 0.75, 0.85), expo=1.0):
    """Planeta gaseoso con bandas según el eje `ax` y anillos (opcionales) en el plano ecuatorial."""
    C = np.asarray(C, float)
    ax, e1, e2 = frame(ax)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    if rel @ cam.f <= r:
        return None
    cx, cy, _ = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
    rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
    ext = rpx * (2.15 if rings else 1.25) + 4
    x0 = int(max(0, cx - ext)); x1 = int(min(W, cx + ext + 1))
    y0 = int(max(0, cy - ext)); y1 = int(min(H, cy + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return (cx, cy, rpx)
    d = cam.dirs(y0, y1, x0, x1)
    oc = cam.O - C
    b = d @ oc
    perp2 = np.maximum(float(oc @ oc) - b * b, 0)
    dd = np.sqrt(perp2)
    pixw = np.maximum(-b, 1e-9) * PIX
    alpha = np.clip((r - dd) / pixw + 0.5, 0, 1) * (b < 0)
    tsph = np.where(alpha > 0, -b - np.sqrt(np.maximum(r * r - perp2, 0)), np.inf)
    region = img[y0:y1, x0:x1]
    # halo de atmósfera
    hz = (dd > r * 0.99) & (dd < r * 1.2) & (b < 0)
    if hz.any():
        P = cam.O + (-b[hz])[:, None] * d[hz]
        nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
        lit = np.clip(nn @ LIGHT + 0.45, 0, 1)
        gl = np.exp(-np.maximum((dd[hz] - r) / (0.05 * r), 0)) * lit * 0.45
        region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array(atm)
    ring_a = None
    if rings:
        den = d @ ax
        den = np.where(np.abs(den) < 1e-6, 1e-6, den)
        tr = -(oc @ ax) / den
        P = oc + tr[..., None] * d
        rr = np.linalg.norm(P, axis=-1) / r
        ra = np.zeros_like(rr)
        for rad, wdt, amp in ((1.64, 0.008, 0.35), (1.68, 0.008, 0.35), (1.72, 0.010, 0.4), (1.80, 0.010, 0.35), (2.00, 0.020, 0.9)):
            ra += amp * np.exp(-((rr - rad) / wdt) ** 2)
        # suavizado mínimo para que no parpadee cuando el anillo se ve de canto
        ra = np.clip(ra, 0, 0.9) * (tr > 0)
        # sombra del planeta sobre los anillos
        Pw = P
        bl = Pw @ LIGHT
        sh = (np.sum(Pw * Pw, -1) - bl * bl < r * r) & (bl < 0)
        rcol = lin((0.75, 0.80, 0.85)) * 0.55
        rc = rcol[None, None, :] * np.where(sh, 0.08, 1.0)[..., None]
        back = ra * (tr >= tsph)
        front = ra * (tr < tsph)
        region[:] = region * (1 - back[..., None]) + rc * back[..., None]
        ring_a = (front, rc)
    sel = alpha > 0
    if sel.any():
        ds = d[sel]
        P = cam.O + tsph[sel][:, None] * ds
        n = (P - C) / r
        V = -ds
        ndl = n @ LIGHT
        la = np.arcsin(np.clip(n @ ax, -1, 1))
        lo = np.arctan2(n @ e2, n @ e1) + spin
        alb = colfn(la, lo, t)
        mu = np.clip((n * V).sum(-1), 0, 1)
        diff = np.clip(ndl, 0, 1)
        light = (0.010 + 1.05 * diff * (0.45 + 0.55 * mu ** 0.5))[:, None]
        col = alb * light + np.array(atm) * ((1 - mu) ** 3 * 0.55 * np.clip(ndl + 0.3, 0, 1))[:, None]
        col = col * expo
        a = alpha[sel][:, None]
        region[sel] = region[sel] * (1 - a) + col * a
    if ring_a is not None:
        front, rc = ring_a
        region[:] = region * (1 - front[..., None]) + rc * front[..., None]
    return (cx, cy, rpx)


def draw_sun(img, cam, C, r):
    x, y, z = cam.proj(np.asarray(C, float))
    if z[0] <= 0:
        return None
    x, y = float(x[0]), float(y[0])
    rpx = r / float(z[0]) / PIX
    yy, xx = np.mgrid[0:H:4, 0:W:4]
    dd = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
    core = np.clip((rpx - dd) / 3 + 0.5, 0, 1)
    halo = np.exp(-dd / (rpx * 1.0)) * 0.7 + np.exp(-dd / (rpx * 3)) * 0.08
    small = core[..., None] * np.array([6.0, 4.6, 2.4]) + halo[..., None] * np.array([1.0, 0.65, 0.25])
    img += ndzoom(small.astype(np.float32), (4, 4, 1), order=1)[:H, :W]
    return (x, y, rpx)


# ---------------- líneas de campo magnético (dipolo) ----------------
def dipole_lines(Corig, r, max_, Ls=(1.5, 2.1, 2.9, 4.0), naz=6, n=80, phase=0.0):
    ax, e1, e2 = frame(max_)
    out = []
    for L in Ls:
        th0 = math.asin(min(1.0, math.sqrt(0.82 / L)))
        th = np.linspace(th0, math.pi - th0, n)
        rho = L * np.sin(th) ** 2 * r
        for k in range(naz):
            ph = phase + 2 * math.pi * k / naz
            dirr = np.cos(ph) * e1 + np.sin(ph) * e2
            P = Corig[None, :] + rho[:, None] * (np.cos(th)[:, None] * ax[None, :] + np.sin(th)[:, None] * dirr[None, :])
            out.append((L, P))
    return out


def vis_mask(cam, pts, C, r):
    x, y, z = cam.proj(pts)
    vis = z > 0.1
    rel = pts - cam.O
    dist = np.linalg.norm(rel, axis=-1)
    dirn = rel / dist[:, None]
    oc = cam.O - np.asarray(C, float)
    b = dirn @ oc
    disc = b * b - (oc @ oc - r * r)
    tnear = -b - np.sqrt(np.maximum(disc, 0))
    vis &= ~((disc > 0) & (tnear < dist) & (tnear > 0))
    return x, y, vis


def draw_field(layer, cam, C, r, Corig, max_, t, col, A, Ls=(1.5, 2.1, 2.9, 4.0), naz=6, grow=1.0, width=4):
    """Dibuja las líneas con brillo y pulsos que viajan a lo largo de ellas."""
    if A <= 0:
        return
    from PIL import ImageFilter
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, (L, P) in enumerate(dipole_lines(np.asarray(Corig, float), r, max_, Ls, naz, phase=0.25 * t)):
        x, y, vis = vis_mask(cam, P, C, r * 0.995)
        m = max(2, int(len(P) * grow))
        for j in range(m - 1):
            if vis[j] and vis[j + 1]:
                d.line([(x[j], y[j]), (x[j + 1], y[j + 1])], fill=col + (int(A * 0.75),), width=width)
        # pulso
        k = int(((t * 0.55 + i * 0.137) % 1.0) * (m - 1))
        if vis[k]:
            d.ellipse([x[k] - 9, y[k] - 9, x[k] + 9, y[k] + 9], fill=(255, 255, 255, A))
    gl = lay.filter(ImageFilter.GaussianBlur(9))
    layer.alpha_composite(gl)
    layer.alpha_composite(gl)
    layer.alpha_composite(lay)


def axis_line(d, cam, C, r, ax, col, A, length=1.75, width=7, behind=None, dash=0, label=None, lsize=44):
    ax = unit(ax)
    s = np.linspace(-length, length, 120)
    P = np.asarray(C, float)[None, :] + s[:, None] * r * ax[None, :]
    x, y, vis = vis_mask(cam, P, behind[0], behind[1]) if behind is not None else (*cam.proj(P)[:2], np.ones(len(P), bool))
    for j in range(len(P) - 1):
        if dash and (j // dash) % 2 == 1:
            continue
        if vis[j] and vis[j + 1]:
            d.line([(x[j], y[j]), (x[j + 1], y[j + 1])], fill=col + (A,), width=width)
    if label:
        txt(d, (x[-1] + 0, y[-1] - 40), label, lsize, col, A, "Inter-Black.otf", 7)
    return (x[0], y[0]), (x[-1], y[-1])


def angle_arc(d, cxy, a_from, a_to, R, col, A, label, lsize=88, width=8, k=1.0, loff=1.0):
    """Arco 2D en pantalla entre dos direcciones (ángulos en grados, sentido de pantalla) y etiqueta."""
    cx, cy = cxy
    a1 = a_from + (a_to - a_from) * k
    lo_, hi_ = sorted((a_from, a1))
    d.arc([cx - R, cy - R, cx + R, cy + R], lo_, hi_, fill=col + (A,), width=width)
    am = math.radians((a_from + a1) / 2)
    txt(d, (cx + math.cos(am) * (R + 80 * loff), cy + math.sin(am) * (R + 80 * loff)), label, lsize, col, int(A * min(1, k * 1.5)))


def screen_angle(p0, p1):
    return math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))


# ---------------- montañas (silueta para el cielo final) ----------------
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


RIDGES = [ridge(4, 240, 1640, 150, 0.55), ridge(5, 240, 1760, 110, 0.6), ridge(6, 240, 1870, 80, 0.6)]


def draw_mountains(img, rise):
    cols = [(0.010, 0.015, 0.032), (0.006, 0.009, 0.020), (0.003, 0.004, 0.010)]
    for (xs_, ys_), c in zip(RIDGES, cols):
        pts = [(float(x), float(y + rise)) for x, y in zip(xs_, ys_)] + [(W + 80, H + 10), (-80, H + 10)]
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon(pts, fill=255)
        ma = np.asarray(m, np.float32)[..., None] / 255
        img[:] = img * (1 - ma) + np.array(c, np.float32) * ma
        e = Image.new("L", (W, H), 0)
        ImageDraw.Draw(e).line([(float(x), float(y + rise)) for x, y in zip(xs_, ys_)], fill=255, width=3)
        ea = gaussian_filter(np.asarray(e, np.float32) / 255, 1.2)[..., None]
        img += ea * np.array([0.10, 0.16, 0.30], np.float32) * 0.4


# ---------------- ejes de cada planeta ----------------
U_SPIN = tilt_axis(97, 14)                        # Urano: acostado (~97°)
U_MAG = rotate_about(U_SPIN, [0.0, 0.0, 1.0], math.radians(59))   # campo desviado 59° del eje
U_OFF = 0.32                                       # centro del dipolo desplazado ~1/3 del radio
E_SPIN = tilt_axis(23.4, 8)
E_MAG = rotate_about(E_SPIN, [0.0, 0.0, 1.0], math.radians(-11))
N_SPIN = tilt_axis(28, 8)
N_MAG = rotate_about(N_SPIN, [0.0, 0.0, 1.0], math.radians(47))
N_OFF = 0.5                                        # Neptuno: a la mitad entre el centro y las nubes


def u_offset_vec():
    ax, e1, e2 = frame(U_MAG)
    return unit(np.cross([0.0, 0.0, 1.0], U_MAG)) * -1


# ---------------- tomas ----------------
FIRST = ["gancho", "oposicion", "acostado", "iman", "tierra", "agua", "resultado", "cierre"]
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
    cam = Cam((1.2 - 1.6 * s, 0.6 - 0.3 * s, 9.5 - 2.2 * ease_out(s)), (0, -0.25, 0))
    info = draw_planet(img, cam, (0, 0, 0), 1.0, U_SPIN, uranus_col, t, spin=0.6 * t, rings=True)
    return cam, dict(p=info, C=np.zeros(3))


# diagrama de la oposición (sin escala): Sol arriba, Tierra en medio, Urano abajo
R_E_ORB, R_U_ORB = 22.0, 46.0
SUN_P = np.array([0.0, 0.0, -30.0])


def opo_state(t):
    a0, a1 = span("oposicion")
    k = ease((t - a0) / 3.2)
    ae = math.radians(-38) * (1 - k)               # la Tierra llega a la línea Sol–Urano
    au = math.radians(-4) * (1 - k)
    E = SUN_P + R_E_ORB * np.array([math.sin(ae), 0, math.cos(ae)])
    U = SUN_P + R_U_ORB * np.array([math.sin(au), 0, math.cos(au)])
    return E, U, k


def sh_oposicion(img, t):
    a0, a1 = span("oposicion")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.0 + 6 * s, 62 - 6 * s, 52 - 4 * s), (0, 0, -6))
    E, U, k = opo_state(t)
    sinfo = draw_sun(img, cam, SUN_P, 3.2)
    draw_earth(img, cam, E, 1.6, t, atm=0.06, glow=0.7)
    uinfo = draw_planet(img, cam, U, 2.6, U_SPIN, uranus_col, t, spin=0.6 * t, rings=True)
    return cam, dict(E=E, U=U, k=k, s=sinfo, u=uinfo)


def sh_acostado(img, t):
    a0, a1 = span("acostado")
    s = (t - a0) / (a1 - a0)
    cam = Cam((-0.6 + 1.2 * s, 0.1, 6.4 - 0.5 * s), (0, 0.05, 0))
    info = draw_planet(img, cam, (0, 0, 0), 1.0, U_SPIN, uranus_col, t, spin=1.4 * t, rings=True)
    return cam, dict(p=info)


def sh_iman(img, t):
    a0, a1 = span("iman")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.8 - 1.0 * s, 0.4, 9.6 - 0.6 * s), (0, 0.2, 0))
    info = draw_planet(img, cam, (0, 0, 0), 1.0, U_SPIN, uranus_col, t, spin=0.6 * t, rings=True, expo=0.8)
    return cam, dict(p=info)


EARTH_C = np.array([-1.75, 0.55, 0.0])
NEP_C = np.array([1.75, 0.55, 0.0])


def sh_tierra(img, t):
    cam = Cam((0, 0.2, 17.0), (0, 0.15, 0))
    draw_earth(img, cam, EARTH_C, 1.0, t, atm=0.04, glow=0.6)
    info = draw_planet(img, cam, NEP_C, 1.0, N_SPIN, neptune_col, t, spin=0.8 * t, atm=(0.2, 0.4, 1.0))
    return cam, dict(n=info)


RNG_IONS = np.random.default_rng(40)
ION_R = np.sqrt(RNG_IONS.uniform(0.30 ** 2, 0.74 ** 2, 260))
ION_A = RNG_IONS.uniform(0, 1, 260)
ION_PH = RNG_IONS.uniform(0, 2 * math.pi, 260)
ION_SIGN = RNG_IONS.random(260) < 0.5


def cut_angles(t):
    a0, a1 = span("agua")
    k = ease((t - a0 - 0.2) / 1.2)
    return -95.0, -95.0 + 105.0 * k, k


def sh_agua(img, t):
    a0, a1 = span("agua")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0, 0.0, 6.6 - 0.4 * s), (0, -0.25, 0))
    info = draw_planet(img, cam, (0, 0, 0), 1.0, tilt_axis(97, 4), uranus_col, t, spin=0.4 * t, rings=False)
    cx, cy, rp = info
    ang0, ang1, k = cut_angles(t)
    if k > 0.001:
        yy, xx = np.mgrid[0:H, 0:W]
        x0 = int(max(0, cx - rp - 2)); x1 = int(min(W, cx + rp + 2)); y0 = int(max(0, cy - rp - 2)); y1 = int(min(H, cy + rp + 2))
        X = xx[y0:y1, x0:x1] - cx; Y = yy[y0:y1, x0:x1] - cy
        R = np.sqrt(X * X + Y * Y) / rp
        A = np.degrees(np.arctan2(Y, X))
        inw = ((A - ang0) % 360) <= (ang1 - ang0)
        m = (R < 1.0) & inw
        if m.any():
            col = np.zeros(R.shape + (3,), np.float32)
            atmc = lin((0.42, 0.70, 0.78)) * 0.55
            wat = lin((0.10, 0.55, 1.0))
            core = lin((0.45, 0.36, 0.30)) * 0.65
            depth = np.clip((0.75 - R) / 0.45, 0, 1)
            # agua iónica: más brillante (más conductora) hacia adentro
            pulse = 0.85 + 0.15 * np.sin(t * 4 - R * 12)
            wcol = wat[None, None, :] * (0.25 + 1.6 * depth ** 1.3)[..., None] * pulse[..., None]
            col[:] = atmc
            col = np.where((R < 0.75)[..., None], wcol, col)
            col = np.where((R < 0.28)[..., None], core * (0.8 + 0.4 * (1 - R / 0.28))[..., None], col)
            edge = (np.abs(R - 0.75) < 0.008) | (np.abs(R - 0.28) < 0.008)
            col[edge] = col[edge] * 0.4 + 0.35
            reg = img[y0:y1, x0:x1]
            reg[m] = col[m]
        # iones que se mueven dentro del corte
        aa = np.radians(ang0 + (ang1 - ang0) * ION_A)
        rr = ION_R * rp + 6 * np.sin(t * 3 + ION_PH)
        px = cx + np.cos(aa + 0.03 * np.sin(t * 2 + ION_PH)) * rr
        py = cy + np.sin(aa + 0.03 * np.sin(t * 2 + ION_PH)) * rr
        small = np.zeros((H // 2, W // 2, 3), np.float32)
        cols = np.where(ION_SIGN[:, None], np.array([1.0, 0.85, 0.3]), np.array([0.5, 0.95, 1.0])) * 2.5 * k
        np.add.at(small, (np.clip((py / 2).astype(int), 0, H // 2 - 1), np.clip((px / 2).astype(int), 0, W // 2 - 1)), cols)
        img += ndzoom(gaussian_filter(small, (1.0, 1.0, 0)) * 1.0 + gaussian_filter(small, (3, 3, 0)) * 0.8, (2, 2, 1), order=1)[:H, :W]
    return cam, dict(p=info)


def voyager_pos(t):
    a0, a1 = span("resultado")
    s = (t - a0) / (a1 - a0)
    return np.array([2.6 - 4.6 * s, 1.75 - 0.5 * s, 1.2])


def sh_resultado(img, t):
    a0, a1 = span("resultado")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.4 - 0.8 * s, -0.5, 10.5 - 0.8 * s), (0, 0.35, 0))
    info = draw_planet(img, cam, (0, 0, 0), 1.0, U_SPIN, uranus_col, t, spin=0.6 * t, rings=True, expo=0.85)
    return cam, dict(p=info, V=voyager_pos(t))


# cielo de Tauro (coordenadas de pantalla aproximadas, sin escala exacta)
TAURUS = {
    "ALDEBARÁN": (430, 980, 3.2, (1.0, 0.62, 0.35)),
    "h1": (520, 900, 1.2, (0.95, 0.9, 0.8)), "h2": (560, 930, 1.1, (0.95, 0.9, 0.8)),
    "h3": (600, 880, 1.0, (0.95, 0.9, 0.8)), "h4": (500, 860, 0.9, (0.95, 0.9, 0.8)),
    "e1": (250, 760, 1.3, (0.9, 0.92, 1.0)), "e2": (180, 1120, 1.4, (0.9, 0.92, 1.0)),
}
PLEIADES = [(780, 470), (812, 452), (834, 486), (800, 505), (850, 440), (770, 500), (826, 520)]
URANUS_SKY = (700, 690)


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    s = (t - a0) / (END - a0)
    z = 1.0 + 0.10 * s
    img[:] = img * 1.4 + np.array([0.004, 0.007, 0.016], np.float32)
    small = np.zeros((H // 2, W // 2, 3), np.float32)

    def put(x, y, inten, col):
        x = W / 2 + (x - W / 2) * z; y = 700 + (y - 700) * z
        if 0 <= x < W and 0 <= y < H:
            small[int(y / 2), int(x / 2)] += np.array(col) * inten

    for k, (x, y, m, c) in TAURUS.items():
        put(x, y, 34 * m, c)
    for (x, y) in PLEIADES:
        put(x, y, 22, (0.8, 0.88, 1.0))
    tw = 0.85 + 0.15 * math.sin(t * 5)
    put(*URANUS_SKY, 26 * tw, (0.45, 1.0, 0.85))
    img += ndzoom(gaussian_filter(small, (0.9, 0.9, 0)) * 1.2 + gaussian_filter(small, (4, 4, 0)) * 0.35, (2, 2, 1), order=1)[:H, :W]
    draw_mountains(img, 40 * (1 - ease_out(s * 2)))
    sky = lambda p: (W / 2 + (p[0] - W / 2) * z, 700 + (p[1] - 700) * z)
    return None, dict(sky=sky, s=s)


SCENES = dict(gancho=sh_gancho, oposicion=sh_oposicion, acostado=sh_acostado, iman=sh_iman,
              tierra=sh_tierra, agua=sh_agua, resultado=sh_resultado, cierre=sh_cierre)


# ---------------- textos y gráficos ----------------
def calendar(layer, t, a, b, xy=(W / 2, 560), size=300):
    al = fade(t, a, b, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    k = ease_out((t - a) / 0.45)
    w_ = h_ = size * (0.8 + 0.2 * k)
    d = ImageDraw.Draw(layer)
    x0, y1 = xy[0] - w_ / 2, xy[1] - h_ / 2
    d.rounded_rectangle([x0, y1, x0 + w_, y1 + h_], 28, fill=(245, 247, 252, A))
    d.rounded_rectangle([x0, y1, x0 + w_, y1 + h_ * 0.28], 28, fill=(40, 170, 190, A))
    d.rectangle([x0, y1 + h_ * 0.16, x0 + w_, y1 + h_ * 0.28], fill=(40, 170, 190, A))
    d.text((xy[0], y1 + h_ * 0.14), "NOVIEMBRE", font=font("Inter-Black.otf", int(40 * w_ / 300)), fill=(255, 255, 255, A), anchor="mm")
    d.text((xy[0], y1 + h_ * 0.64), "25", font=font("Inter-Black.otf", int(170 * w_ / 300)), fill=(20, 24, 36, A), anchor="mm")


def voyager(d, x, y, sc, A):
    """Silueta sencilla de la Voyager: antena parabólica, cuerpo, mástil del magnetómetro y RTG."""
    col = (235, 238, 245, A)
    d.line([(x, y), (x - 150 * sc, y + 70 * sc)], fill=(200, 205, 215, A), width=max(2, int(4 * sc)))   # magnetómetro
    d.line([(x, y), (x + 95 * sc, y + 40 * sc)], fill=(200, 205, 215, A), width=max(2, int(5 * sc)))    # brazo RTG
    d.rectangle([x + 88 * sc, y + 30 * sc, x + 110 * sc, y + 54 * sc], fill=(150, 150, 160, A))
    d.rectangle([x - 18 * sc, y - 4 * sc, x + 18 * sc, y + 22 * sc], fill=(190, 160, 90, A))
    d.ellipse([x - 62 * sc, y - 40 * sc, x + 62 * sc, y - 4 * sc], fill=col, outline=(150, 160, 175, A), width=3)
    d.line([(x, y - 22 * sc), (x, y - 52 * sc)], fill=col, width=max(2, int(4 * sc)))


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    Z = np.zeros(3)
    if name == "gancho":
        draw_label(layer, t, -1, 2.6, "URANO", ["en su mejor punto del año"], CYAN, 140)
        # al decir "imán torcido": aparecen las líneas del campo
        tm = S0["gancho"] + 3.0
        Af = int(255 * min(1.0, max(0.0, (t - tm) / 0.5)))
        if Af > 0:
            Corig = -u_offset_vec() * U_OFF
            draw_field(layer, cam, Z, 1.0, Corig, U_MAG, t, YELLOW, Af, grow=min(1.0, (t - tm) / 0.9))
            d = ImageDraw.Draw(layer)
            draw_label(layer, t, tm, a1 + 0.2, "IMÁN TORCIDO", [], YELLOW, 120)
    elif name == "oposicion":
        E, U, k = ex["E"], ex["U"], ex["k"]
        Ao = int(255 * min(1.0, (t - a0) / 0.5))
        for R_, c in ((R_E_ORB, CYAN), (R_U_ORB, (130, 220, 230))):
            pts = SUN_P[None, :] + np.stack([np.sin(np.linspace(0, 2 * np.pi, 240)) * R_, np.zeros(240), np.cos(np.linspace(0, 2 * np.pi, 240)) * R_], -1)
            poly3d(d, cam, pts, c, int(Ao * 0.55), 3)
        xs_, ys_, _ = pt(cam, SUN_P); xe, ye, _ = pt(cam, E); xu, yu, _ = pt(cam, U)
        if k > 0.98:
            Al = int(255 * min(1.0, (t - (a0 + 3.2)) / 0.4))
            for j in range(0, 30, 2):
                f0, f1 = j / 30, (j + 1) / 30
                d.line([(xs_ + (xu - xs_) * f0, ys_ + (yu - ys_) * f0), (xs_ + (xu - xs_) * f1, ys_ + (yu - ys_) * f1)], fill=YELLOW + (Al,), width=5)
            draw_label(layer, t, a0 + 3.2, a1, "OPOSICIÓN", ["Sol · Tierra · Urano en línea"], YELLOW, 116, 330)
        else:
            calendar(layer, t, a0 + 0.1, a0 + 3.1, (W / 2, 420), 280)
        Am = int(235 * fade(t, a0 + 0.3, a1))
        txt(d, (xs_ + 120, ys_), "SOL", 46, WHITE, Am, "Inter-Black.otf", 7, "lm")
        txt(d, (xe + 50, ye), "TIERRA", 46, WHITE, Am, "Inter-Black.otf", 7, "lm")
        if ex["u"]:
            txt(d, (xu + ex["u"][2] * 2.2 + 20, yu), "URANO", 46, CYAN, Am, "Inter-Black.otf", 7, "lm")
    elif name == "acostado":
        k = ease_out((t - a0 - 0.4) / 1.0)
        A = int(255 * fade(t, a0 + 0.2, a1))
        p0, p1 = axis_line(d, cam, Z, 1.0, [0, 1, 0], (200, 210, 230), int(A * 0.8), 1.7, 5, (Z, 1.0), dash=4)
        q0, q1 = axis_line(d, cam, Z, 1.0, U_SPIN, WHITE, A, 1.75, 7, (Z, 1.0))
        cxy = pt(cam, Z)[:2]
        a_up = screen_angle(cxy, p1); a_ax = screen_angle(cxy, q1)
        angle_arc(d, cxy, a_up, a_ax, 300, YELLOW, A, "97°", 100, 9, k)
        draw_label(layer, t, a0 + 0.1, a1, "GIRA ACOSTADO", ["su eje está casi de lado"], WHITE, 112)
    elif name == "iman":
        A = int(255 * fade(t, a0 + 0.1, a1))
        Corig = -u_offset_vec() * U_OFF
        draw_field(layer, cam, Z, 1.0, Corig, U_MAG, t, YELLOW, int(A * 0.9))
        d = ImageDraw.Draw(layer)
        q0, q1 = axis_line(d, cam, Z, 1.0, U_SPIN, WHITE, A, 1.75, 6, (Z, 1.0), dash=4)
        m0, m1 = axis_line(d, cam, Corig, 1.0, U_MAG, YELLOW, A, 1.85, 8, (Z, 1.0))
        cxy = pt(cam, Corig)[:2]
        k = ease_out((t - a0 - 0.8) / 1.0)
        angle_arc(d, cxy, screen_angle(cxy, q1), screen_angle(cxy, m1), 250, YELLOW, A, "59°", 100, 9, k)
        draw_label(layer, t, a0 + 0.1, a1, "CAMPO MAGNÉTICO", ["desviado 59° de su eje"], YELLOW, 90)
        # descentrado
        Ac = int(255 * fade(t, S0["iman"] + 3.4, a1))
        if Ac > 0:
            x0, y0 = pt(cam, Z)[:2]; x1, y1 = cxy
            d.ellipse([x0 - 12, y0 - 12, x0 + 12, y0 + 12], fill=WHITE + (Ac,))
            d.ellipse([x1 - 16, y1 - 16, x1 + 16, y1 + 16], fill=RED + (Ac,), outline=WHITE + (Ac,), width=3)
            txt(d, (W / 2, 1120), "¡NI SIQUIERA ESTÁ CENTRADO!", 62, RED, Ac, "Inter-Black.otf", 8)
    elif name == "tierra":
        Ae = int(255 * fade(t, a0 + 0.1, a1))
        An = int(255 * fade(t, S0["tierra"] + 1.6, a1))
        Ce = EARTH_C; Cn = NEP_C
        draw_field(layer, cam, Ce, 1.0, Ce, E_MAG, t, CYAN, int(Ae * 0.8), Ls=(1.5, 2.2, 3.0), naz=4, width=3)
        if An > 0:
            Co = Cn - unit(np.cross([0.0, 0.0, 1.0], N_MAG)) * N_OFF
            draw_field(layer, cam, Cn, 1.0, Co, N_MAG, t, YELLOW, int(An * 0.8), Ls=(1.5, 2.2, 3.0), naz=4, width=3)
        d = ImageDraw.Draw(layer)
        e0, e1 = axis_line(d, cam, Ce, 1.0, E_SPIN, WHITE, Ae, 1.6, 5, (Ce, 1.0), dash=4)
        f0, f1 = axis_line(d, cam, Ce, 1.0, E_MAG, CYAN, Ae, 1.7, 7, (Ce, 1.0))
        xe, ye, _ = pt(cam, Ce)
        txt(d, (xe, ye + 185), "TIERRA", 58, WHITE, Ae)
        txt(d, (xe, ye - 300), "11°", 120, CYAN, Ae)
        if An > 0:
            Co = Cn - unit(np.cross([0.0, 0.0, 1.0], N_MAG)) * N_OFF
            n0, n1 = axis_line(d, cam, Cn, 1.0, N_SPIN, WHITE, An, 1.6, 5, (Cn, 1.0), dash=4)
            g0, g1 = axis_line(d, cam, Co, 1.0, N_MAG, YELLOW, An, 1.7, 7, (Cn, 1.0))
            xn, yn, _ = pt(cam, Cn)
            txt(d, (xn, yn + 185), "NEPTUNO", 58, WHITE, An)
            txt(d, (xn, yn - 300), "47°", 120, YELLOW, An)
        Au = int(255 * fade(t, a0 + 0.4, a1))
        txt(d, (W / 2, 1175), "Y URANO: 59°", 76, YELLOW, Au, "Inter-Black.otf", 8)
    elif name == "agua":
        cx, cy, rp = ex["p"]
        ang0, ang1, k = cut_angles(t)
        A = int(255 * fade(t, a0 + 0.8, a1) * k)
        if A > 0:
            for frac, lab, col in ((0.87, "HIDRÓGENO Y HELIO", WHITE), (0.52, "AGUA IÓNICA", CYAN), (0.14, "ROCA", (230, 200, 170))):
                am = math.radians(ang0 + (ang1 - ang0) * 0.55)
                x = cx + math.cos(am) * rp * frac; y = cy + math.sin(am) * rp * frac
                if frac > 0.5:
                    d.line([(x, y), (x - 170, y - 60)], fill=col + (A,), width=4)
                    txt(d, (x - 180, y - 60), lab, 44, col, A, "Inter-Black.otf", 7, "rm")
                elif frac > 0.3:
                    d.line([(x, y), (x - 200, y + 40)], fill=col + (A,), width=4)
                    txt(d, (x - 210, y + 40), lab, 52, col, A, "Inter-Black.otf", 8, "rm")
                else:
                    d.line([(x, y), (x - 160, y + 120)], fill=col + (A,), width=4)
                    txt(d, (x - 170, y + 120), lab, 44, col, A, "Inter-Black.otf", 7, "rm")
        draw_label(layer, t, a0 + 0.1, S0["agua"] + 3.4, "UNIVERSIDAD DE TEXAS", ["simulaciones por computadora"], WHITE, 78)
        Ai = int(255 * fade(t, S0["agua"] + 3.4, a1))
        if Ai > 0:
            draw_label(layer, t, S0["agua"] + 3.4, a1, "H₂O → H⁺ + OH⁻", ["el agua se rompe en iones"], YELLOW, 104)
            kk = ease_out((t - S0["agua"] - 5.2) / 1.0)
            if kk > 0:
                xa = 120
                d.line([(xa, 760), (xa, 760 + 300 * kk)], fill=YELLOW + (Ai,), width=10)
                if kk > 0.95:
                    d.polygon([(xa - 26, 1060), (xa + 26, 1060), (xa, 1100)], fill=YELLOW + (Ai,))
                txt(d, (xa - 50, 1150), "más profundo =", 46, WHITE, int(Ai * min(1, kk * 2)), "Inter-ExtraBold.otf", 7, "lm")
                txt(d, (xa - 50, 1205), "más eléctrico", 46, YELLOW, int(Ai * min(1, kk * 2)), "Inter-ExtraBold.otf", 7, "lm")
    elif name == "resultado":
        A = int(255 * fade(t, a0 + 0.1, a1))
        Corig = -u_offset_vec() * U_OFF
        draw_field(layer, cam, Z, 1.0, Corig, U_MAG, t, YELLOW, int(A * 0.9))
        d = ImageDraw.Draw(layer)
        xv, yv, zv = pt(cam, ex["V"])
        voyager(d, xv, yv, 1.15, A)
        txt(d, (xv, yv + 110), "VOYAGER 2 · 1986", 46, CYAN, A, "Inter-Black.otf", 7)
        draw_label(layer, t, a0 + 0.1, a1, "¡COINCIDE!", ["la simulación reproduce lo medido"], YELLOW, 120)
    elif name == "cierre":
        sky = ex["sky"]
        A = int(255 * fade(t, a0 + 0.3, CARD))
        if A > 0:
            pts = [sky(TAURUS[k][:2]) for k in ("e1", "h4", "ALDEBARÁN", "h2", "h3", "h1", "h4")]
            for j in range(len(pts) - 1):
                d.line([pts[j], pts[j + 1]], fill=(120, 170, 230, int(A * 0.45)), width=3)
            d.line([sky(TAURUS["ALDEBARÁN"][:2]), sky(TAURUS["e2"][:2])], fill=(120, 170, 230, int(A * 0.45)), width=3)
            xa, ya = sky(TAURUS["ALDEBARÁN"][:2])
            txt(d, (xa - 30, ya + 50), "Aldebarán", 38, (255, 190, 140), int(A * 0.9), "Inter-ExtraBold.otf", 6, "rm")
            xp, yp = sky((810, 480))
            txt(d, (xp, yp - 80), "Pléyades", 38, (200, 220, 255), int(A * 0.9), "Inter-ExtraBold.otf", 6)
        Au = int(255 * fade(t, a0 + 1.2, CARD))
        if Au > 0:
            xu, yu = sky(URANUS_SKY)
            marker(d, xu, yu, t, YELLOW, Au, 34, "URANO", -1, 52)
        draw_label(layer, t, a0 + 0.1, CARD, "BUSCA EN TAURO", ["con binoculares y cielo oscuro"], YELLOW, 110, 300)
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


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def poly3d(d, cam, pts, col, A, width=6, behind=None, dash=0):
    x, y, z = cam.proj(pts)
    vis = z > 0.1
    for i in range(len(pts) - 1):
        if dash and (i // dash) % 2 == 1:
            continue
        if vis[i] and vis[i + 1]:
            d.line([(x[i], y[i]), (x[i + 1], y[i + 1])], fill=col + (A,), width=width)


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
