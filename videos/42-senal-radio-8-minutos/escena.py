"""Flash Datos · video 42: la señal de radio que se repite casi cada 8 minutos (GPM J071507−114153).

Escena nueva: enana blanca que gira como faro con un solo haz de radio (pulso en cada vuelta) y un
osciloscopio que marca cada pulso; ondas de radio que cruzan el espacio hasta la Tierra (Australia);
la pareja con la estrella parecida al Sol; la docena de señales conocidas con una enana roja; la
prominencia y la llamarada iluminadas por el haz; cierre con la pareja completa.

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
BET = T("betelgeuse")
EARTH = T("earth"); CLOUDS = T("earth_clouds"); LAND = T("earth_land")
SUNT = T("sun")


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

def draw_earth(img, cam, C, r, t, atm=0.03, glow=0.55, expo=1.0, lon=-1.72):
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
    loc = rot_y(rot_x(n, math.radians(-20)), lon + 0.03 * t)
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
#  VIDEO 42 · La señal de radio de cada 8 minutos · escena nueva
# =====================================================================

def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


BET_N = np.clip((BET - 0.34) / 0.56, 0, 1).astype(np.float32)
SUN_N = np.clip((SUNT - 0.63) / 0.38, 0, 1).astype(np.float32)
SOL_HOT = np.array([3.0, 2.3, 1.05]); SOL_COOL = np.array([1.9, 1.0, 0.32])
WD_HOT = np.array([1.5, 1.8, 2.4]); WD_COOL = np.array([1.0, 1.25, 1.8])
RD_HOT = np.array([1.9, 0.5, 0.16]); RD_COOL = np.array([0.9, 0.15, 0.04])


def draw_star(img, cam, C, r, t, hot, cool, expo=1.0, spin=0.0, halo=1.0, halo_col=None, tex=None, tex_scale=1.0):
    """Estrella emisiva con granulación, oscurecimiento al limbo y halo. tex=None → superficie lisa."""
    C = np.asarray(C, float)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    if rel @ cam.f <= r * 1.05:
        return None
    cx, cy, _ = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
    rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
    HX = 1.2 * max(halo, 0.3)
    ext = rpx * (1.0 + HX) + 6
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
    region = img[y0:y1, x0:x1]
    hc = np.asarray(halo_col if halo_col is not None else hot * 0.45, np.float32)
    if halo > 0:
        x = np.maximum(dd - r, 0) / r
        g = (np.exp(-x / 0.08) * 0.45 + np.exp(-x / 0.35) * 0.18) * np.clip(1 - x / HX, 0, 1) ** 2 * halo * expo
        region += ((1 - alpha) * g)[..., None] * hc
    sel = alpha > 0
    if sel.any():
        ds = d[sel]; bs = b[sel]
        tt = -bs - np.sqrt(np.maximum(r * r - perp2[sel], 0))
        P = cam.O + tt[:, None] * ds
        n = (P - C) / r
        mu = np.clip((n * -ds).sum(-1), 0, 1)
        if tex is None:
            g = np.full(len(mu), 0.6, np.float32)
        else:
            la, lo = latlon(rot_y(n, spin))
            g = sample(tex, np.clip(la * tex_scale, -1.57, 1.57), lo * tex_scale)
            g = 0.5 + (g - 0.5) * (0.85 + 0.15 * math.sin(t * 1.3))
        col = cool[None, :] * (1 - g[:, None]) + hot[None, :] * g[:, None]
        limb = (0.3 + 0.7 * mu ** 0.5)[:, None]
        col = col * limb * expo
        a = alpha[sel][:, None]
        region[sel] = region[sel] * (1 - a) + col * a
    return (cx, cy, rpx)


# ---------------- el faro: un haz de radio que gira ----------------
PV = 2.0          # segundos de video por vuelta (en la realidad, casi 8 minutos)
T_OFF = 0.55      # primer pulso
ALPHA = math.radians(80)


def theta(t):
    return 2 * math.pi * (t - T_OFF) / PV


def pulse(t):
    th = (theta(t) + math.pi) % (2 * math.pi) - math.pi
    return math.exp(-th * th / 0.035)


def pulse_times(a, b):
    k0 = math.ceil((a - T_OFF) / PV)
    out = []
    k = k0
    while T_OFF + k * PV <= b:
        out.append(T_OFF + k * PV); k += 1
    return out


RB = np.random.default_rng(42)
NB = 7000
B_S = RB.random(NB); B_J = RB.standard_normal((NB, 2)); B_TW = RB.random(NB)


def beam_axis(cam, C, t, tilt=0.28):
    S = unit(cam.u * math.cos(tilt) + cam.r * math.sin(tilt))
    dc = unit(cam.O - C)
    e1 = unit(dc - (dc @ S) * S)
    e2 = np.cross(S, e1)
    th = theta(t)
    M = math.cos(ALPHA) * S + math.sin(ALPHA) * (math.cos(th) * e1 + math.sin(th) * e2)
    return M, S


def draw_beam(img, cam, C, R, L, t, amp=1.0):
    """Haz de radio (visualizado en cian) que sale del polo magnético de la enana blanca."""
    M, S = beam_axis(cam, C, t)
    a = unit(np.cross(M, S)); b = np.cross(M, a)
    r = R + B_S * L
    w = R * 0.32 + (r - R) * 0.05
    P = C[None, :] + M[None, :] * r[:, None] + (B_J[:, 0:1] * a[None, :] + B_J[:, 1:2] * b[None, :]) * w[:, None] * 0.6
    fall = np.exp(-(r - R) / (L * 0.55)) * (0.75 + 0.25 * np.sin(B_TW * 40 + t * 9))
    col = np.array([0.5, 0.95, 1.7], np.float32)[None, :] * (0.42 * amp * fall)[:, None]
    splat(img, cam, P, col.astype(np.float32))
    # contrahaz débil (el otro polo)
    P2 = C[None, :] - M[None, :] * r[:, None] + (B_J[:, 1:2] * a[None, :] - B_J[:, 0:1] * b[None, :]) * w[:, None] * 0.6
    splat(img, cam, P2[::3], (col[::3] * 0.35).astype(np.float32))
    return M


def pulse_flash(img, cam, C, R, t, amp=1.0):
    p = pulse(t) * amp
    if p < 0.01:
        return p
    x, y, z = pt(cam, C)
    yy, xx = np.mgrid[0:H:4, 0:W:4]
    dd = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
    g = (np.exp(-dd / 50) * 1.2 + np.exp(-dd / 240) * 0.25) * p
    img += ndzoom(g[..., None].astype(np.float32) * np.array([0.55, 0.9, 1.4], np.float32), (4, 4, 1), order=1)[:H, :W]
    return p


def draw_wd(img, cam, C, R, t, L, amp=1.0, beam=True):
    if beam:
        draw_beam(img, cam, C, R, L, t, amp)
    info = draw_star(img, cam, C, R, t, WD_HOT, WD_COOL, 1.0 + 0.8 * pulse(t) * amp, halo=0.8, halo_col=np.array([0.35, 0.6, 1.0]))
    p = pulse_flash(img, cam, C, R, t, amp) if beam else 0.0
    return info, p


# ---------------- la pareja ----------------
U1 = np.array([1.0, 0.0, 0.0])
U2 = unit([0.0, 0.22, -1.0])
A_ORB = 2.9
R_SOL, R_WD = 1.0, 0.11


def wd_pos(t):
    ph = 2.35 + 0.045 * t
    return A_ORB * (math.cos(ph) * U1 + math.sin(ph) * U2)


def draw_pair(img, cam, t, L=2.4, amp=1.0, sol_expo=1.0):
    W_ = wd_pos(t)
    zs = (np.zeros(3) - cam.O) @ cam.f; zw = (W_ - cam.O) @ cam.f
    infos = {}
    items = [("sol", zs), ("wd", zw)]
    items.sort(key=lambda q: -q[1])
    for k, _ in items:
        if k == "sol":
            infos["sol"] = draw_star(img, cam, np.zeros(3), R_SOL, t, SOL_HOT, SOL_COOL, sol_expo, spin=0.04 * t, halo=1.2, tex=SUN_N, tex_scale=2.0)
        else:
            infos["wd"], infos["p"] = draw_wd(img, cam, W_, R_WD, t, L, amp)
    infos["W"] = W_
    return infos


def orbit_ring(d, cam, a, col, A, width=3):
    ph = np.linspace(0, 2 * math.pi, 240)
    P = a * (np.cos(ph)[:, None] * U1 + np.sin(ph)[:, None] * U2)
    x, y, z = cam.proj(P)
    for j in range(len(ph) - 1):
        if j % 3 == 2 or z[j] <= 0 or z[j + 1] <= 0:
            continue
        # tramo detrás de la estrella: no se dibuja
        mid = (P[j] + P[j + 1]) / 2
        if (mid - cam.O) @ cam.f > (-cam.O) @ cam.f:
            dvec = mid - cam.O; dd = unit(dvec)
            if np.linalg.norm(np.cross(dd, -cam.O)) < R_SOL * 1.02:
                continue
        d.line([(x[j], y[j]), (x[j + 1], y[j + 1])], fill=col + (A,), width=width)


# ---------------- ondas de radio hacia la Tierra ----------------
SRC = np.array([2.2, 4.9, -20.0])


# ---------------- prominencia y llamarada ----------------
RP = np.random.default_rng(7)
NP_ = 2600
P_U = RP.random(NP_); P_J = RP.standard_normal((NP_, 3)); P_B = 0.5 + RP.random(NP_)
CD_L = unit([-0.29, 0.39, 0.88])
_er = unit(np.cross([0, 1, 0], CD_L)); _er = -_er if _er[0] > 0 else _er
_eu = np.cross(CD_L, _er)
_eu = _eu if _eu[1] > 0 else -_eu
def _limb(a):
    return unit(math.cos(a) * _er + math.sin(a) * _eu + 0.18 * CD_L)
PR_A = _limb(math.radians(25)); PR_B = _limb(math.radians(55))
LIMB_T = _limb(math.radians(40))


def slerp(a, b, u):
    om = math.acos(float(np.clip(a @ b, -1, 1)))
    so = math.sin(om)
    return (np.sin((1 - u) * om)[:, None] * a + np.sin(u * om)[:, None] * b) / so


def prominence(img, cam, t, flare):
    u = P_U
    base = slerp(PR_A, PR_B, u)
    h = 0.42 * np.sin(np.pi * u) * (1 + 0.04 * math.sin(t * 2.0))
    P = base * (R_SOL + h)[:, None] + P_J * 0.025
    col = np.stack([P_B * 2.6, P_B * 0.9, P_B * 0.3], -1) * 0.022 * (1 + 5.0 * flare)
    splat(img, cam, P, col.astype(np.float32))
    if flare > 0.01:
        top = slerp(PR_A, PR_B, np.array([0.5]))[0] * (R_SOL + 0.05)
        Q = top[None, :] + P_J * 0.12 * (1 + 2 * (1 - flare))
        splat(img, cam, Q[:900], (np.tile([3.0, 2.6, 2.0], (900, 1)) * 0.06 * flare).astype(np.float32))


# ---------------- planos ----------------
FIRST = ["gancho", "distancia", "enana", "pareja", "docena", "llamaradas", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.22) for i, k in enumerate(FIRST)]
FL = [b for _, b in SHOTS[1:]] + [CARD - 0.05]
FLARE_T = SPLIT("llamaradas", 0.62)


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
    ang = 0.5 - 0.7 * s
    R = 4.6 - 0.9 * ease_out(s)
    cam = Cam((R * math.sin(ang), 0.9 - 0.5 * s, R * math.cos(ang)), (0, 0.12, 0), roll=0.12 - 0.1 * s)
    info, p = draw_wd(img, cam, np.zeros(3), 0.22, t, 7.0, 1.0)
    return cam, dict(info=info, p=p)


def sh_distancia(img, t):
    a0, a1 = span("distancia")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.3 - 0.3 * s, 0.0, 7.6 - 0.5 * s), (0.0, 0.15, 0.0))
    # la fuente: un puntito azul lejano que parpadea con cada pulso
    p = pulse(t)
    splat(img, cam, SRC[None, :], (np.array([[1.4, 2.2, 3.4]], np.float32) * (1.0 + 4 * p)))
    draw_earth(img, cam, np.zeros(3), 1.0, t, lon=2.05)
    return cam, dict(p=p)


def sh_enana(img, t):
    a0, a1 = span("enana")
    s = (t - a0) / (a1 - a0)
    ang = -0.9 + 0.8 * s
    R = 3.4 + 0.5 * s
    cam = Cam((R * math.sin(ang), -0.4 + 0.6 * s, R * math.cos(ang)), (0, 0.16, 0), roll=-0.08)
    info, p = draw_wd(img, cam, np.zeros(3), 0.22, t, 6.5, 1.0)
    return cam, dict(info=info, p=p)


def sh_pareja(img, t):
    a0, a1 = span("pareja")
    s = (t - a0) / (a1 - a0)
    W_ = wd_pos(t)
    e = ease(min(1.0, s * 1.5))
    tgt = lerp(W_, W_ * 0.5, e)
    dv = unit([-0.55 + 0.25 * s, 0.38, 1.0])
    R = 2.6 + 10.0 * e
    cam = Cam(tgt + dv * R, tgt, roll=0.05)
    info = draw_pair(img, cam, t, L=2.6)
    return cam, dict(info=info)


RD_A = 1.25


def sh_docena(img, t):
    a0, a1 = span("docena")
    s = (t - a0) / (a1 - a0)
    cam = Cam((-0.5 + 1.2 * s, 1.5, 6.6 - 0.6 * s), (0.2, 0.15, 0), roll=-0.06)
    ph = 0.6 + 0.35 * (t - a0)
    Wp = RD_A * (math.cos(ph) * U1 + math.sin(ph) * U2)
    Rp = -0.55 * Wp / RD_A
    items = sorted([("rd", (Rp - cam.O) @ cam.f), ("wd", (Wp - cam.O) @ cam.f)], key=lambda q: -q[1])
    info = {}
    for k, _ in items:
        if k == "rd":
            info["rd"] = draw_star(img, cam, Rp, 0.42, t, RD_HOT, RD_COOL, 1.0, spin=0.1 * t, halo=1.1, tex=BET_N, tex_scale=1.5)
        else:
            info["wd"], info["p"] = draw_wd(img, cam, Wp, 0.1, t, 2.0, 0.8)
    return cam, dict(info=info)


def sh_llamaradas(img, t):
    a0, a1 = span("llamaradas")
    s = (t - a0) / (a1 - a0)
    cam = Cam(CD_L * (7.0 + 0.8 * s) + np.array([0.3 * s, 0, 0]), LIMB_T * 1.25, roll=0.05)
    te = t - FLARE_T
    flare = 0.0 if te < 0 else (1 - math.exp(-te / 0.12)) * math.exp(-te / 1.6)
    W_ = LIMB_T * 2.9 - CD_L * 1.2
    draw_wd(img, cam, W_, 0.1, t, 3.0, 1.0)
    info = draw_star(img, cam, np.zeros(3), R_SOL, t, SOL_HOT, SOL_COOL, 0.8 + 0.4 * flare, spin=0.04 * t, halo=1.0, tex=SUN_N, tex_scale=2.0)
    prominence(img, cam, t, flare)
    if flare > 0.01:
        img += np.float32(0.04 * flare) * np.array([1.0, 0.8, 0.5], np.float32)
    return cam, dict(info=info, flare=flare)


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    s = (t - a0) / (END - a0)
    W_ = wd_pos(t)
    tgt = W_ * 0.5 + np.array([0.0, -0.2, 0.0])
    ang = 0.75 - 0.35 * s
    dv = unit([math.sin(ang), 0.55, math.cos(ang)])
    R = 12.5 - 1.5 * ease_out(s)
    cam = Cam(tgt + dv * R, tgt, roll=-0.04)
    info = draw_pair(img, cam, t, L=2.8)
    return cam, dict(info=info)


SCENES = dict(gancho=sh_gancho, distancia=sh_distancia, enana=sh_enana, pareja=sh_pareja,
              docena=sh_docena, llamaradas=sh_llamaradas, cierre=sh_cierre)


# ---------------- textos y gráficos ----------------
def scope(layer, t, A, y=690, wdt=820, hgt=150):
    """Osciloscopio: la señal de radio de los últimos segundos, con un pico en cada pulso."""
    if A <= 0:
        return
    d = ImageDraw.Draw(layer)
    x0 = W / 2 - wdt / 2
    d.rounded_rectangle([x0, y - hgt / 2, x0 + wdt, y + hgt / 2], 24, fill=(6, 14, 30, int(A * 0.72)), outline=CYAN + (int(A * 0.6),), width=3)
    for gx in range(1, 8):
        xx = x0 + wdt * gx / 8
        d.line([(xx, y - hgt / 2 + 10), (xx, y + hgt / 2 - 10)], fill=(79, 216, 255, int(A * 0.12)), width=2)
    N = 260; span_s = 4.0
    pts = []
    for i in range(N):
        tt = t - span_s + span_s * i / (N - 1)
        nz = 0.06 * math.sin(tt * 61.0) + 0.05 * math.sin(tt * 97.3 + 1.1) + 0.04 * math.sin(tt * 173.1)
        v = pulse(tt) + nz
        pts.append((x0 + 20 + (wdt - 40) * i / (N - 1), y + hgt / 2 - 22 - v * (hgt - 50)))
    d.line(pts, fill=CYAN + (A,), width=5, joint="curve")
    x, yy = pts[-1]
    d.ellipse([x - 9, yy - 9, x + 9, yy + 9], fill=YELLOW + (A,))
    txt(d, (x0 + 24, y - hgt / 2 + 26), "RADIO", 30, CYAN, A, "Inter-ExtraBold.otf", 4, "lm")


def clock(layer, t, A, cx, cy, r=70):
    if A <= 0:
        return
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(245, 247, 252, A), outline=(8, 10, 20, A), width=6)
    for k in range(12):
        a = k * math.pi / 6
        d.line([(cx + math.sin(a) * r * 0.78, cy - math.cos(a) * r * 0.78), (cx + math.sin(a) * r * 0.9, cy - math.cos(a) * r * 0.9)], fill=(20, 24, 36, A), width=4)
    a = 2 * math.pi * ((t - T_OFF) / PV % 1)
    d.line([(cx, cy), (cx + math.sin(a) * r * 0.75, cy - math.cos(a) * r * 0.75)], fill=(220, 80, 50, A), width=7)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(20, 24, 36, A))


def waves(d, t, cx, cy, A, toward, n=4):
    """Frentes de onda (arcos) que salen de la fuente hacia la Tierra."""
    for k in pulse_times(t - 2.6 * PV, t):
        age = t - k
        r = 30 + age * 260
        a = max(0.0, 1 - age / (2.2 * PV))
        if a <= 0:
            continue
        ang = math.degrees(math.atan2(toward[1] - cy, toward[0] - cx))
        box = [cx - r, cy - r * 0.8, cx + r, cy + r * 0.8]
        for j, dr in enumerate((0, 26, 52)):
            bx = [box[0] - dr, box[1] - dr * 0.8, box[2] + dr, box[3] + dr * 0.8]
            d.arc(bx, ang - 30, ang + 30, fill=CYAN + (int(A * a * (1 - 0.3 * j)),), width=7 - 2 * j)


def dots12(layer, t, a, A):
    d = ImageDraw.Draw(layer)
    for i in range(12):
        ti = a + 0.12 * i
        if t < ti:
            continue
        k = ease_out((t - ti) / 0.25)
        x = W / 2 + ((i % 6) - 2.5) * 120; y = 640 + (i // 6) * 110
        rr = 34 * k
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(79, 216, 255, int(A * 0.9)), outline=(8, 10, 20, A), width=4)
        d.polygon(bolt(x, y, 46 * k), fill=(8, 10, 20, A))


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    if name == "gancho":
        cut = SPLIT("gancho", 0.62)
        draw_label(layer, t, -1, cut, "SEÑAL DE RADIO", ["se repite casi cada 8 minutos"], YELLOW, 112)
        draw_label(layer, t, cut, a1 + 0.3, "¿DE DÓNDE VIENE?", ["por fin hay respuesta"], CYAN, 100)
        As = int(255 * fade(t, 0.15, a1 + 0.3))
        scope(layer, t, As)
        clock(layer, t, int(255 * fade(t, 0.4, cut)), W - 150, 880, 62)
        if int(255 * fade(t, 0.4, cut)) > 0:
            txt(d, (W - 150, 985), "≈ 8 MIN", 44, WHITE, int(255 * fade(t, 0.4, cut)), "Inter-Black.otf", 6)
    elif name == "distancia":
        draw_label(layer, t, a0 + 0.1, a1, "+5,000 AÑOS LUZ", ["de viaje hasta la Tierra"], YELLOW, 104)
        sx, sy, _ = pt(cam, SRC)
        ex_, ey_, _ = pt(cam, np.array([0.0, 0.9, 0.0]))
        A = int(255 * fade(t, a0 + 0.1, a1))
        waves(d, t, sx, sy, A, (ex_, ey_))
        marker(d, sx, sy, t, CYAN, int(A * 0.9), 26, "LA FUENTE", -1, 44)
        Am = int(255 * fade(t, SPLIT("distancia", 0.45), a1))
        if Am > 0:
            ax, ay, _ = pt(cam, AUS)
            marker(d, ax, ay, t, YELLOW, Am, 34, "AUSTRALIA", -1, 50)
            txt(d, (ax - 75, ay + 56), "radiotelescopio", 38, CYAN, Am, "Inter-ExtraBold.otf", 6, "rm")
    elif name == "enana":
        cut = SPLIT("enana", 0.5)
        draw_label(layer, t, a0 + 0.1, cut, "ENANA BLANCA", ["el núcleo muerto de una estrella"], WHITE, 124)
        draw_label(layer, t, cut, a1, "1 VUELTA = 1 PULSO", ["gira como un faro"], YELLOW, 94)
        A = int(255 * fade(t, cut, a1))
        scope(layer, t, A)
    elif name == "pareja":
        info = ex["info"]
        cut = SPLIT("pareja", 0.5)
        draw_label(layer, t, a0 + 0.1, cut, "NO ESTÁ SOLA", ["a su lado, una estrella como el Sol"], WHITE, 118)
        draw_label(layer, t, cut, a1, "PRIMERA VEZ", ["que una señal así sale de esta pareja"], YELLOW, 130)
        A = int(255 * fade(t, a0 + 1.2, a1))
        orbit_ring(d, cam, A_ORB, CYAN, int(A * 0.35), 3)
        if info.get("sol"):
            x, y, r = info["sol"]
            if r > 30:
                txt(d, (x, max(600, y - r - 50)), "TIPO SOL", 54, YELLOW, int(A * fade(t, a0 + 1.6, a1)), "Inter-Black.otf", 7)
        if info.get("wd"):
            x, y, r = info["wd"]
            Aw = int(A * fade(t, a0 + 1.6, a1))
            marker(d, x, y, t, CYAN, Aw, 26, "ENANA BLANCA", 1 if x < W * 0.55 else -1, 42)
    elif name == "docena":
        cut = SPLIT("docena", 0.48)
        draw_label(layer, t, a0 + 0.1, cut, "≈ 12 SEÑALES", ["así se conocen en todo el cielo"], CYAN, 124)
        dots12(layer, t, a0 + 0.35, int(255 * fade(t, a0 + 0.3, cut)))
        draw_label(layer, t, cut, a1, "ANTES:", ["parejas con enanas rojas"], WHITE, 110)
        info = ex["info"]
        Ar = int(255 * fade(t, cut + 0.2, a1))
        if info.get("rd") and Ar > 0:
            x, y, r = info["rd"]
            txt(d, (x, max(600, y - r - 50)), "ENANA ROJA", 56, RED, Ar, "Inter-Black.otf", 7)
    elif name == "llamaradas":
        draw_label(layer, t, a0 + 0.1, FLARE_T - 0.1, "LOS PULSOS", ["funcionan como linterna"], CYAN, 122)
        draw_label(layer, t, FLARE_T - 0.1, a1, "¡LLAMARADA!", ["en la estrella vecina"], ORANGE, 130)
    elif name == "cierre":
        cut = SPLIT("cierre", 0.5)
        Aa = int(255 * fade(t, a0 + 0.1, cut))
        if Aa > 0:
            draw_label(layer, t, a0 + 0.1, cut, "NO SON ALIENS", ["es pura física estelar"], WHITE, 118)
            k = ease_out((t - a0 - 0.8) / 0.4)
            if k > 0:
                d.line([(W / 2 - 430, 380), (W / 2 - 430 + 860 * k, 340)], fill=RED + (Aa,), width=14)
        draw_label(layer, t, cut, CARD, "ESTRELLA MUERTA", ["girando junto a un Sol"], YELLOW, 100)
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


# Australia en el globo (coordenadas locales de la textura → se calcula una vez por cuadro)
AUS_LAT, AUS_LON = math.radians(-25.0), math.radians(146.0)
AUS = np.zeros(3)


def aus_point(t, lon_rot=2.05):
    """Punto 3D de Australia, invirtiendo la rotación usada en draw_earth."""
    v = np.array([math.cos(AUS_LAT) * math.sin(AUS_LON), math.sin(AUS_LAT), math.cos(AUS_LAT) * math.cos(AUS_LON)])
    v = rot_y(v, -(lon_rot + 0.03 * t))
    v = rot_x(v, -math.radians(-20))
    return v * 1.0


def render(t):
    global AUS
    name = scene(t)
    AUS = aus_point(t)
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
