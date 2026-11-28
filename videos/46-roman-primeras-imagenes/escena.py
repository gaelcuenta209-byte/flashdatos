"""Flash Datos · video 46: el telescopio Roman de la NASA enseña sus primeras imágenes (7 dic 2026).

Escena nueva: el telescopio Roman (tubo plateado con la tapa abierta, cuerpo hexagonal dorado y paneles
solares que hacen de parasol) flotando con la Tierra pequeña al fondo; campo de galaxias donde el recuadro
del Hubble crece 10 veces por lado (100 veces el área) hasta el de Roman; zoom hasta un solo píxel
«adoptado»; mapa Tierra–Luna–L2 con el viaje y la regla de 1.5 millones de km; vista dentro del tubo al
espejo de 2.4 m; plano focal de 18 detectores; 1 foto de Roman = 100 recuadros del Hubble; universo que se
expande cada vez más rápido (energía oscura); certificado ilustrativo del píxel; cierre con el campo de
galaxias que vuelve al píxel amarillo.

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
JUP = T("jupiter")
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
    tw = d.textlength(title, font=font("Inter-Black.otf", title_size))
    if tw > W - 90:
        title_size = int(title_size * (W - 90) / tw)
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
EARTH = T("earth"); CLOUDS = T("earth_clouds"); LAND = T("earth_land")


def draw_body(img, cam, C, r, t, tex, spin=0.0, tilt=0.3, expo=1.0, light=LIGHT, tint=(1.0, 0.93, 0.85), amb=0.02):
    """Cuerpo iluminado (asteroide, Luna) con textura en lat/lon."""
    C = np.asarray(C, float)
    rel = C - cam.O
    dist = float(np.linalg.norm(rel))
    if rel @ cam.f <= r:
        return None
    cx, cy, _ = cam.proj(C); cx, cy = float(cx[0]), float(cy[0])
    rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
    ext = rpx + 4
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
    sel = alpha > 0
    if not sel.any():
        return (cx, cy, rpx)
    region = img[y0:y1, x0:x1]
    ds = d[sel]; bs = b[sel]
    tt = -bs - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = cam.O + tt[:, None] * ds
    n = (P - C) / r
    ndl = n @ light
    la, lo = latlon(rot_y(rot_x(n, tilt), spin))
    col = sample(tex, la, lo)
    if col.ndim == 1:
        col = col[:, None] * np.array(tint)
    diff = np.clip(ndl, 0, 1)
    col = col * (amb + 1.9 * diff)[:, None] * expo
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a
    return (cx, cy, rpx)


def _rock_tex(seed=3, crat=9):
    th, tw = 256, 512
    la = (0.5 - (np.arange(th) + 0.5) / th) * np.pi
    lo = (np.arange(tw) + 0.5) / tw * 2 * np.pi - np.pi
    LO, LA = np.meshgrid(lo, la)
    x, y, z = np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO)
    n1 = fbm(x * 3 + 5, y * 3, z * 3, 5, seed=seed)
    n2 = fbm(x * crat, y * crat + 2, z * crat, 3, seed=seed + 5)
    cr = np.clip(1 - np.abs(n2 - 0.5) * 9, 0, 1) ** 2
    g = 0.22 + 0.35 * n1 - 0.12 * cr
    return np.clip(g, 0.05, 0.7).astype(np.float32)


ROCK = _rock_tex()
MOONT = np.clip(_rock_tex(17, 6) * 1.25 + 0.12, 0, 1).astype(np.float32)
def _box(x0, x1, y0, y1, z0, z1):
    v = lambda a, b, c: np.array([a, b, c], float)
    return [
        [v(x0, y0, z1), v(x1, y0, z1), v(x1, y1, z1), v(x0, y1, z1)],
        [v(x1, y0, z0), v(x0, y0, z0), v(x0, y1, z0), v(x1, y1, z0)],
        [v(x1, y0, z1), v(x1, y0, z0), v(x1, y1, z0), v(x1, y1, z1)],
        [v(x0, y0, z0), v(x0, y0, z1), v(x0, y1, z1), v(x0, y1, z0)],
        [v(x0, y1, z1), v(x1, y1, z1), v(x1, y1, z0), v(x0, y1, z0)],
        [v(x0, y0, z0), v(x1, y0, z0), v(x1, y0, z1), v(x0, y0, z1)],
    ]


# =====================================================================
#  VIDEO 46 · El telescopio Roman enseña sus primeras imágenes (7 dic 2026)
# =====================================================================

def unit3(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# ---------------- geometría del telescopio (polígonos 3D) ----------------
def prism(n, r, z0, z1, inward=False, phase=0.0, a_from=0.0, a_to=2 * math.pi):
    out = []
    angs = np.linspace(a_from, a_to, n + 1) + phase
    for a, b in zip(angs[:-1], angs[1:]):
        q = [np.array([r * math.cos(a), r * math.sin(a), z0]), np.array([r * math.cos(b), r * math.sin(b), z0]),
             np.array([r * math.cos(b), r * math.sin(b), z1]), np.array([r * math.cos(a), r * math.sin(a), z1])]
        out.append(q[::-1] if inward else q)
    return out


def disc(n, r, z, up=True, phase=0.0, cx=0.0, cy=0.0):
    q = [np.array([cx + r * math.cos(a), cy + r * math.sin(a), z]) for a in np.linspace(0, 2 * math.pi, n, endpoint=False) + phase]
    return q if up else q[::-1]


def _roman_parts():
    P = []
    silver = (0.78, 0.80, 0.85); dark = (0.045, 0.05, 0.065); gold = (0.86, 0.63, 0.30)
    blue = (0.10, 0.17, 0.52); white = (0.92, 0.92, 0.95); mirror = (0.80, 0.85, 0.95); grey = (0.30, 0.31, 0.34)
    # tubo (barril) con su interior oscuro
    for q in prism(22, 1.25, 0.0, 4.2):
        P.append((q, silver, "solid"))
    for q in prism(22, 1.21, 0.35, 4.2, inward=True):
        P.append((q, dark, "solid"))
    # espejo primario de 2.4 m (radio 1.2 en unidades del modelo)
    P.append((disc(28, 1.17, 0.40), mirror, "mirror"))
    P.append((disc(10, 0.20, 0.405), dark, "solid"))           # agujero central
    # espejo secundario y sus soportes
    P.append((disc(12, 0.30, 3.50, up=False), silver, "solid"))
    P.append((disc(12, 0.30, 3.62), dark, "solid"))
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.5
        c, s = math.cos(a), math.sin(a)
        q = [np.array([0.30 * c, 0.30 * s, 3.53]), np.array([1.21 * c, 1.21 * s, 3.53]), np.array([1.21 * c, 1.21 * s, 3.60]), np.array([0.30 * c, 0.30 * s, 3.60])]
        P.append((q, grey, "panel"))
    # tapa de la apertura, abierta hacia el lado del Sol (+y)
    P.append(([np.array([-1.15, 1.25, 4.2]), np.array([1.15, 1.25, 4.2]), np.array([1.15, 2.05, 6.0]), np.array([-1.15, 2.05, 6.0])], silver, "panel"))
    # cuerpo de la nave (hexágono dorado)
    for q in prism(6, 1.95, -1.5, 0.0, phase=math.pi / 6):
        P.append((q, gold, "solid"))
    P.append((disc(6, 1.95, -1.5, up=False, phase=math.pi / 6), gold, "solid"))
    P.append((disc(6, 1.95, 0.0, phase=math.pi / 6), (0.70, 0.52, 0.26), "solid"))
    # paneles solares que también hacen de parasol, del lado del Sol (+y)
    for z0, z1 in ((-1.5, 1.15), (1.25, 3.9)):
        for c in range(3):
            a0 = math.radians(38 + c * 35)
            for q in prism(1, 2.25, z0, z1, a_from=a0, a_to=a0 + math.radians(34)):
                P.append((q, blue, "panel"))
    # antena de alta ganancia (lado contrario al Sol)
    P.append(([np.array([-0.06, -1.95, -0.8]), np.array([0.06, -1.95, -0.8]), np.array([0.06, -2.9, -0.8]), np.array([-0.06, -2.9, -0.8])], grey, "panel"))
    ring = [np.array([0.65 * math.cos(a), -2.95, -0.8 + 0.65 * math.sin(a)]) for a in np.linspace(0, 2 * np.pi, 18, endpoint=False)]
    P.append((ring, white, "dish"))
    return P


ROMAN = _roman_parts()


def _detector_parts():
    """Plano focal de la cámara de campo amplio: 18 detectores en 3 filas de 6, en arco."""
    P = []
    for q in _box(-3.9, 3.9, -2.3, 2.6, -0.25, 0.0):
        P.append((q, (0.80, 0.60, 0.28), "solid"))
    for row in range(3):
        for col in range(6):
            x = (col - 2.5) * 1.18
            y = (row - 1) * 1.18 + 0.045 * x * x
            z = 0.02
            q = [np.array([x - 0.52, y - 0.52, z]), np.array([x + 0.52, y - 0.52, z]), np.array([x + 0.52, y + 0.52, z]), np.array([x - 0.52, y + 0.52, z])]
            P.append((q, (0.16, 0.12, 0.36), "chip"))
    return P


DETECT = _detector_parts()


def frame_of(fwd, up):
    f = unit3(fwd)
    u = np.asarray(up, float) - (np.asarray(up, float) @ f) * f
    u = unit3(u)
    r = np.cross(u, f)
    return np.stack([r, u, f], 1)          # columnas: x local→r, y→u, z→f


def draw_poly(img, cam, parts, P, Rm, scale, light=LIGHT, expo=1.0):
    """Dibuja un modelo de polígonos (pintor) en una capa 2x y lo mezcla en la imagen HDR."""
    P = np.asarray(P, float)
    cx, cy, cz = pt(cam, P)
    if cz <= 0.05:
        return None
    polys = []
    for q, col, kind in parts:
        V = np.array([P + Rm @ (v * scale) for v in q])
        x, y, z = cam.proj(V)
        if np.any(z <= 0.01):
            continue
        n = np.cross(V[1] - V[0], V[2] - V[0])
        if np.linalg.norm(n) < 1e-12:
            continue
        n = unit3(n)
        view = unit3(cam.O - V.mean(0))
        facing = n @ view
        if kind in ("solid", "mirror", "chip") and facing <= 0:
            continue
        nn = n if facing > 0 else -n
        lam = max(float(nn @ light), 0.0)
        refl = max(float((2 * (nn @ light) * nn - light) @ view), 0)
        c = np.array(col)
        if kind == "panel":
            if facing <= 0 and col[2] > 0.4:
                c = np.array([0.35, 0.36, 0.40])
            shade = 0.18 + 0.9 * lam + 0.6 * refl ** 30
        elif kind == "dish":
            shade = 0.25 + 0.85 * lam
        elif kind == "mirror":
            shade = 0.30 + 0.45 * lam + 1.2 * refl ** 6
        elif kind == "chip":
            shade = 0.35 + 0.5 * lam + 2.2 * refl ** 12
        else:
            shade = 0.12 + 1.0 * lam
        rgb = np.clip(c * shade * expo, 0, 1)
        polys.append((float(z.mean()) - (1e4 if kind == "chip" else 0.0), list(zip(x * 2, y * 2)), tuple(int(255 * v) for v in rgb), kind))
    if not polys:
        return None
    xs_ = [p[0] for pp in polys for p in pp[1]]; ys_ = [p[1] for pp in polys for p in pp[1]]
    x0 = int(max(0, min(xs_) - 8)); x1 = int(min(2 * W, max(xs_) + 8))
    y0 = int(max(0, min(ys_) - 8)); y1 = int(min(2 * H, max(ys_) + 8))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return (cx, cy)
    x0 -= x0 % 2; y0 -= y0 % 2; x1 += x1 % 2; y1 += y1 % 2
    layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    polys.sort(key=lambda p: -p[0])
    for z, pts2, rgb, kind in polys:
        pts2 = [(a - x0, b - y0) for a, b in pts2]
        d.polygon(pts2, fill=rgb + (255,))
        if kind in ("panel", "chip") and rgb[2] > rgb[0] + 20 and len(pts2) == 4:
            nl = 4 if kind == "panel" else 6
            lc = (20, 30, 60, 255) if kind == "panel" else (10, 8, 26, 255)
            for k in range(1, nl):
                f = k / nl
                for (pa, pb, pc, pd) in ((0, 1, 3, 2), (0, 3, 1, 2)):
                    a = (pts2[pa][0] + (pts2[pb][0] - pts2[pa][0]) * f, pts2[pa][1] + (pts2[pb][1] - pts2[pa][1]) * f)
                    b = (pts2[pc][0] + (pts2[pd][0] - pts2[pc][0]) * f, pts2[pc][1] + (pts2[pd][1] - pts2[pc][1]) * f)
                    d.line([a, b], fill=lc, width=1)
                    if kind == "panel":
                        break
    small = layer.resize(((x1 - x0) // 2, (y1 - y0) // 2), Image.LANCZOS)
    arr = np.asarray(small).astype(np.float32) / 255.0
    a = arr[..., 3:4]
    rgb = (arr[..., :3] ** 2.2) * 1.6
    X0, Y0 = x0 // 2, y0 // 2
    h, w = arr.shape[:2]
    h = min(h, H - Y0); w = min(w, W - X0)
    reg = img[Y0:Y0 + h, X0:X0 + w]
    reg[:] = reg * (1 - a[:h, :w]) + rgb[:h, :w] * a[:h, :w]
    return (cx, cy)


def model_pt(P, Rm, scale, v):
    return np.asarray(P, float) + Rm @ (np.asarray(v, float) * scale)


# ---------------- campo de galaxias (la «foto» del universo) ----------------
GW, GH = 2304, 4096
GC = (GW / 2, GH / 2)


def _galfield(seed=46):
    path = os.path.join(BASE, "tex", "galfield46.npy")
    if os.path.exists(path):
        return np.load(path)
    rng = np.random.default_rng(seed)
    img = np.zeros((GH, GW, 3), np.float32)
    gy, gx = np.mgrid[0:128, 0:72] / 30.0
    neb = fbm(gx, gy, np.full_like(gx, 4.1), 5, seed=146)
    neb = ndzoom(neb, (GH / 128, GW / 72), order=1)
    img += (np.clip((neb - 0.42) * 2.0, 0, 1) ** 1.5)[..., None] * np.array([0.010, 0.012, 0.030], np.float32)
    n = 3400
    for i in range(n):
        size = 0.7 + 11.0 * rng.random() ** 5
        x = rng.uniform(0, GW); y = rng.uniform(0, GH)
        q = rng.uniform(0.3, 1.0); ang = rng.uniform(0, np.pi)
        R = int(size * 4.5) + 3
        x0, x1 = int(max(0, x - R)), int(min(GW, x + R + 1)); y0, y1 = int(max(0, y - R)), int(min(GH, y + R + 1))
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx = xx + 0.5 - x; dy = yy + 0.5 - y
        c, s = math.cos(ang), math.sin(ang)
        u = dx * c + dy * s; v = (-dx * s + dy * c) / q
        r = np.sqrt(u * u + v * v)
        prof = np.exp(-r / (0.45 * size)) + 1.6 * np.exp(-(r / (0.35 * size)) ** 2)
        if size > 5.5 and rng.random() < 0.7:
            phi = np.arctan2(v, u)
            arms = 0.55 + 0.45 * np.cos(2 * (phi - 1.6 * np.log(r / size + 0.15)))
            prof = prof * (0.35 + 0.65 * arms)
        k = rng.random()
        if k < 0.45:
            col = np.array([1.0, 0.82, 0.58])
        elif k < 0.8:
            col = np.array([0.62, 0.74, 1.0])
        else:
            col = np.array([1.0, 0.55, 0.42])
        b = (0.10 + 1.3 * rng.random() ** 3) * (1.0 if size > 2 else 0.8)
        img[y0:y1, x0:x1] += prof[..., None] * col * b * 0.35
    # estrellas de la Vía Láctea en primer plano
    for i in range(170):
        x = rng.integers(2, GW - 2); y = rng.integers(2, GH - 2)
        img[y, x] += np.array([1.0, 0.95, 0.9]) * (0.8 + 4 * rng.random() ** 3)
    img = gaussian_filter(img, (0.7, 0.7, 0))
    np.save(path, img.astype(np.float32))
    return img.astype(np.float32)


GAL = _galfield()
GAL2 = GAL.reshape(GH // 2, 2, GW // 2, 2, 3).mean((1, 3))
PIX0 = (1216, 2057)
GAIN = 7.0          # el «píxel adoptado» (columna, fila) del campo


def field_view(cx, cy, s, gain=1.0):
    """Vista del campo: centro (cx, cy) en píxeles del campo, s = píxeles del campo por píxel de pantalla."""
    src, k = (GAL2, 2.0) if s >= 1.5 else (GAL, 1.0)
    sh, sw = src.shape[:2]
    xs_ = (cx + (np.arange(W) + 0.5 - W / 2) * s) / k - 0.5
    ys_ = (cy + (np.arange(H) + 0.5 - H / 2) * s) / k - 0.5
    if s < 0.6:
        ix = np.clip(np.floor(xs_ + 0.5).astype(int), 0, sw - 1)
        iy = np.clip(np.floor(ys_ + 0.5).astype(int), 0, sh - 1)
        out = src[iy][:, ix]
    else:
        x0 = np.floor(xs_).astype(int); fx = (xs_ - x0).astype(np.float32)[None, :, None]
        y0 = np.floor(ys_).astype(int); fy = (ys_ - y0).astype(np.float32)[:, None, None]
        xa = np.clip(x0, 0, sw - 1); xb = np.clip(x0 + 1, 0, sw - 1)
        ya = np.clip(y0, 0, sh - 1); yb = np.clip(y0 + 1, 0, sh - 1)
        ra = src[ya]; rb = src[yb]
        out = (ra[:, xa] * (1 - fx) + ra[:, xb] * fx) * (1 - fy) + (rb[:, xa] * (1 - fx) + rb[:, xb] * fx) * fy
    return out * (gain * GAIN)


def field_to_screen(fx, fy, cx, cy, s):
    return (fx - cx) / s + W / 2, (fy - cy) / s + H / 2


# ---------------- universo en expansión ----------------
RU = np.random.default_rng(461)
NU = 2600
UP = np.stack([RU.uniform(-22, 22, NU), RU.uniform(-30, 30, NU), RU.uniform(-60, -2, NU)], -1)
UC = np.where(RU.random(NU)[:, None] < 0.5, np.array([[1.0, 0.82, 0.6]]), np.array([[0.65, 0.78, 1.0]])) * (0.25 + 1.6 * RU.random(NU)[:, None] ** 3)


# ---------------- tiempos y planos ----------------
O3 = np.zeros(3)
FIRST = ["gancho", "roman", "camara", "mision", "pixel", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.22) for i, k in enumerate(FIRST)]
SUB = {"gancho_b": SPLIT("gancho", 0.47), "gancho_c": SPLIT("gancho", 0.76),
       "camara_b": SPLIT("camara", 0.38), "camara_c": SPLIT("camara", 0.63),
       "pixel_b": SPLIT("pixel", 0.50), "cierre_b": SPLIT("cierre", 0.40)}
FL = [b for _, b in SHOTS[1:]] + [SUB["gancho_b"], SUB["camara_b"], SUB["cierre_b"], CARD - 0.05]
SUNL = unit3([0.55, 0.55, 0.62])


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


def telescope_shot(img, t, s, variant=0):
    """Roman flotando cerca de L2, con la Tierra pequeña al fondo."""
    if variant == 0:
        ang = 0.55 - 0.45 * s
        D = 25.0 - 4.0 * ease(s)
        pos = (D * math.sin(ang), 4.5 + 1.5 * s, D * math.cos(ang))
        tgt = (0.0, 2.6, 0.0)
        ep = np.array([-0.55, -0.45, -1.0]) * 140
    else:
        ang = -0.35 + 0.30 * s
        D = 23.0 - 2.5 * ease(s)
        pos = (D * math.sin(ang), 5.0 - 0.6 * s, D * math.cos(ang))
        tgt = (0.0, 2.4, 0.0)
        ep = np.array([0.6, -0.5, -1.0]) * 140
    cam = Cam(pos, tgt, roll=0.04)
    draw_earth(img, cam, ep, 4.5, t, atm=0.04, glow=0.7, expo=1.0, lon=-1.9)
    Rm = frame_of((0.18, 1.0, 0.25), (0.9, 0.0, -0.35))
    info = draw_poly(img, cam, ROMAN, O3, Rm, 1.0, light=SUNL)
    return cam, dict(info=info, Rm=Rm, ep=ep)


def sh_gancho(img, t):
    a0, a1 = span("gancho")
    if t < SUB["gancho_b"]:
        s = (t - a0) / (SUB["gancho_b"] - a0)
        cam, ex = telescope_shot(img, t, s, 0)
        ex["mode"] = "tel"
        return cam, ex
    if t < SUB["gancho_c"]:
        s = (t - SUB["gancho_b"]) / (SUB["gancho_c"] - SUB["gancho_b"])
        sc = 2.0 * (1 - 0.05 * s)
        img += field_view(GC[0], GC[1], sc)
        return None, dict(mode="cmp", s=s, sc=sc)
    s = (t - SUB["gancho_c"]) / (a1 - SUB["gancho_c"])
    sc = math.exp(math.log(1.9) + (math.log(0.022) - math.log(1.9)) * ease(min(1.0, s * 1.15)))
    cx = PIX0[0] + 0.5; cy = PIX0[1] + 0.5
    img += field_view(cx, cy, sc)
    return None, dict(mode="pix", s=s, sc=sc, cx=cx, cy=cy)


# mapa Tierra-Luna-L2 (no está a escala: Tierra agrandada)
R_MOON = 1.0
X_L2 = 3.9                       # 1.5 millones de km ≈ 3.9 veces la distancia a la Luna


def sh_roman(img, t):
    a0, a1 = span("roman")
    s = (t - a0) / (a1 - a0)
    cx = 1.75
    cam = Cam((cx, 13.0 - 0.6 * s, 3.6), (cx, 0.0, 0.25), roll=0.0)
    draw_earth(img, cam, O3, 0.24, t, atm=0.07, glow=1.0, expo=1.2, lon=-1.72 + 0.4 * t)
    ma = 2.2 + 0.25 * s
    Pm = np.array([R_MOON * math.cos(ma), 0.0, -R_MOON * math.sin(ma)])
    minfo = draw_body(img, cam, Pm, 0.07, t, MOONT, spin=0.1, tilt=0.2, light=unit3([-1, 0.6, 0]), expo=1.5)
    # viaje: sale de la Tierra, llega a L2 y empieza a dar vueltas alrededor de L2 (órbita de halo)
    u = smooth(0.05, 0.62, s)
    if s < 0.62:
        Pt = np.array([0.3 + (X_L2 - 0.3 - 0.35) * u, 0.0, -0.45 * math.sin(math.pi * u)])
    else:
        w = (s - 0.62) * 5.0
        Pt = np.array([X_L2 - 0.35 * math.cos(w), 0.0, -0.35 * math.sin(w)])
    splat(img, cam, Pt[None, :], np.array([[3.0, 2.6, 1.4]], np.float32), 1.0)
    return cam, dict(Pm=Pm, Pt=Pt, s=s, u=u)


def sh_camara(img, t):
    a0, a1 = span("camara")
    if t < SUB["camara_b"]:
        s = (t - a0) / (SUB["camara_b"] - a0)
        # mirada dentro del tubo: el espejo primario
        ang = 0.25 - 0.5 * s
        cam = Cam((3.4 * math.sin(ang), 15.0 - 2.0 * ease(s), 3.4 * math.cos(ang)), (0.0, 0.4, -0.3), roll=0.0)
        Rm = frame_of((0, 1, 0), (1, 0, 0))
        info = draw_poly(img, cam, ROMAN, O3, Rm, 1.0, light=unit3([0.2, 1.0, 0.45]))
        return cam, dict(mode="espejo", Rm=Rm, s=s, info=info)
    if t < SUB["camara_c"]:
        s = (t - SUB["camara_b"]) / (SUB["camara_c"] - SUB["camara_b"])
        ang = -0.45 + 0.6 * ease(s)
        cam = Cam((24.0 * math.sin(ang), -2.0 + 3.5 * s, 24.0 * math.cos(ang)), (0.0, 0.35, 0.0), roll=0.06 - 0.1 * s)
        Rm = np.eye(3)
        lt = unit3([0.6 - 1.4 * s, 0.4, 0.75])
        info = draw_poly(img, cam, DETECT, O3, Rm, 1.0, light=lt)
        return cam, dict(mode="detector", s=s, info=info)
    s = (t - SUB["camara_c"]) / (a1 - SUB["camara_c"])
    img += field_view(GC[0], GC[1], 2.0, 0.9)
    return None, dict(mode="tiles", s=s)


def sh_mision(img, t):
    a0, a1 = span("mision")
    s = (t - a0) / (a1 - a0)
    a = math.exp(0.25 * s + 1.15 * s * s)
    cam = Cam((0.0, 0.0, 6.0 - 1.5 * s), (0.0, 0.0, -10.0), roll=0.12 * s)
    P = UP * np.array([a, a, 1.0]) + np.array([0, 0, 0])
    P[:, 2] = UP[:, 2] * (0.8 + 0.2 * a)
    dist = np.linalg.norm(P - cam.O, axis=1)
    col = UC * np.clip(3000.0 / (dist ** 2), 0.15, 8.0)[:, None]
    splat(img, cam, P, col.astype(np.float32), 1.0)
    return cam, dict(s=s, a=a)


def sh_pixel(img, t):
    a0, a1 = span("pixel")
    cx = PIX0[0] + 0.5; cy = PIX0[1] + 0.5
    if t < SUB["pixel_b"]:
        s = (t - a0) / (SUB["pixel_b"] - a0)
        sc = math.exp(math.log(0.30) + (math.log(0.0105) - math.log(0.30)) * ease(min(1, s * 1.3)))
        img += field_view(cx, cy, sc)
        return None, dict(mode="zoom", s=s, sc=sc, cx=cx, cy=cy)
    s = (t - SUB["pixel_b"]) / (a1 - SUB["pixel_b"])
    sc = 0.0105 * (1 + 0.25 * s)
    img += field_view(cx, cy, sc, 0.35)
    return None, dict(mode="cert", s=s, sc=sc, cx=cx, cy=cy)


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    if t < SUB["cierre_b"]:
        s = (t - a0) / (SUB["cierre_b"] - a0)
        cx = PIX0[0] + 0.5; cy = PIX0[1] + 0.5
        sc = math.exp(math.log(2.0) + (math.log(0.9) - math.log(2.0)) * ease(s))
        cxx = GC[0] + (cx - GC[0]) * ease(s); cyy = GC[1] + (cy - GC[1]) * ease(s)
        img += field_view(cxx, cyy, sc)
        return None, dict(mode="foto", s=s, sc=sc, cx=cxx, cy=cyy)
    s = (t - SUB["cierre_b"]) / (END - SUB["cierre_b"])
    sc = math.exp(math.log(0.9) + (math.log(0.016) - math.log(0.9)) * ease(min(1.0, s * 1.35)))
    cx = PIX0[0] + 0.5; cy = PIX0[1] + 0.5
    img += field_view(cx, cy, sc)
    return None, dict(mode="tuyo", s=s, sc=sc, cx=cx, cy=cy)


SCENES = dict(gancho=sh_gancho, roman=sh_roman, camara=sh_camara, mision=sh_mision, pixel=sh_pixel, cierre=sh_cierre)


# ---------------- textos y gráficos ----------------
def poly3(d, cam, pts, col, A, width=3, dash=False):
    P = [pt(cam, p) for p in pts]
    for i in range(len(P) - 1):
        if dash and i % 2 == 1:
            continue
        if P[i][2] > 0.05 and P[i + 1][2] > 0.05:
            d.line([P[i][:2], P[i + 1][:2]], fill=col + (int(A),), width=width)


def circle_at(d, cam, C, R, col, A, width=2, dash=True, n=160):
    pts = [np.asarray(C, float) + np.array([R * math.cos(a), 0.0, R * math.sin(a)]) for a in np.linspace(0, 2 * np.pi, n)]
    poly3(d, cam, pts, col, A, width, dash)


def box2(d, x, y, w, h, col, A, width=5):
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], outline=col + (int(A),), width=width)


def pixel_grid(d, cx, cy, sc, A, hl=True, t=0.0):
    """Cuadrícula de píxeles del campo cuando el zoom es grande, con el píxel adoptado en amarillo."""
    if sc < 0.09 and A > 0:
        ga = int(A * min(1.0, (0.09 - sc) / 0.05) * 0.55)
        fx0 = math.floor(cx - W / 2 * sc); fx1 = math.ceil(cx + W / 2 * sc)
        fy0 = math.floor(cy - H / 2 * sc); fy1 = math.ceil(cy + H / 2 * sc)
        for fx in range(fx0, fx1 + 1):
            x, _ = field_to_screen(fx, 0, cx, cy, sc)
            d.line([(x, 0), (x, H)], fill=(10, 14, 28, ga), width=2)
        for fy in range(fy0, fy1 + 1):
            _, y = field_to_screen(0, fy, cx, cy, sc)
            d.line([(0, y), (W, y)], fill=(10, 14, 28, ga), width=2)
    if hl and A > 0:
        x0, y0 = field_to_screen(PIX0[0], PIX0[1], cx, cy, sc)
        x1, y1 = field_to_screen(PIX0[0] + 1, PIX0[1] + 1, cx, cy, sc)
        side = x1 - x0
        if side < 26:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            rr = 26 + 4 * math.sin(t * 7)
            d.ellipse([mx - rr, my - rr, mx + rr, my + rr], outline=YELLOW + (int(A),), width=6)
            return (mx, my, rr)
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        d.rectangle([x0, y0, x1, y1], fill=YELLOW + (int(A * (0.18 + 0.12 * pulse)),), outline=YELLOW + (int(A),), width=max(4, int(side * 0.04)))
        return ((x0 + x1) / 2, (y0 + y1) / 2, side / 2)
    return None


def tag(d, x, y, label, col, A, size=46, side=1, r=30):
    lx = x + side * (r + 70)
    d.line([(x + side * r, y - side * 0), (lx, y - 50)], fill=col + (int(A),), width=5)
    txt(d, (lx + side * 10, y - 50), label, size, WHITE, int(A), "Inter-Black.otf", 7, "lm" if side > 0 else "rm")


def certificate(layer, t, s):
    """Tarjeta ilustrativa del certificado (diseño propio, sin logotipos)."""
    k = ease_out(s / 0.25)
    A = int(255 * min(1.0, s / 0.15))
    if A <= 0:
        return
    w, h = 820, 560
    x0 = W / 2 - w / 2; y0 = 560 + (1 - k) * 160
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 34, fill=(10, 16, 36, int(A * 0.94)), outline=YELLOW + (A,), width=6)
    txt(d, (W / 2, y0 + 70), "CERTIFICADO", 64, YELLOW, A)
    txt(d, (W / 2, y0 + 135), "Adopta un píxel · telescopio Roman", 38, CYAN, A, "Inter-ExtraBold.otf", 5)
    sq = 150
    sx, sy = W / 2 - sq / 2, y0 + 190
    c = GAL[PIX0[1], PIX0[0]]
    c = tuple(int(255 * v) for v in np.clip(tonemap(c * GAIN * 1.6), 0, 1))
    d.rectangle([sx, sy, sx + sq, sy + sq], fill=c + (A,), outline=YELLOW + (A,), width=6)
    txt(d, (W / 2, y0 + 400), "Tu píxel n.º  ??????", 50, WHITE, A, "Inter-Black.otf", 6)
    txt(d, (W / 2, y0 + 472), "llega cuando salgan las imágenes", 38, CYAN, A, "Inter-ExtraBold.otf", 5)
    layer.alpha_composite(card)


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    if name == "gancho":
        if ex["mode"] == "tel":
            draw_label(layer, t, -1, SUB["gancho_b"] + 0.1, "7 DE DICIEMBRE", ["primeras fotos del telescopio Roman"], YELLOW, 120)
            if ex["info"]:
                x, y = ex["info"]
                A = int(255 * fade(t, 1.2, SUB["gancho_b"]))
                tag(d, x + 150, y - 330, "ROMAN", CYAN, A, 50, 1)
        elif ex["mode"] == "cmp":
            s = ex["s"]; sc = ex["sc"]
            hx, hy = field_to_screen(GC[0], GC[1], GC[0], GC[1], sc)
            side_h = 84
            Ah = int(255 * min(1, s / 0.12))
            box2(d, hx, hy, side_h, side_h, CYAN, Ah, 5)
            txt(d, (hx, hy + side_h / 2 + 40), "HUBBLE", 40, CYAN, Ah, "Inter-Black.otf", 6)
            k = ease(smooth(0.25, 0.75, s))
            side_r = side_h * (1 + 9 * k)
            if k > 0:
                box2(d, hx, hy, side_r, side_r, YELLOW, int(255 * min(1, k * 4)), 7)
                txt(d, (hx - side_r / 2 + 22, hy - side_r / 2 + 42), "ROMAN", 52, YELLOW, int(255 * min(1, k * 4)) if side_r > 300 else 0, "Inter-Black.otf", 7, "lm")
            draw_label(layer, t, SUB["gancho_b"], a1 + 0.2, "100 VECES", ["más cielo que el Hubble"], YELLOW, 130, 300)
        else:
            A = int(255 * fade(t, SUB["gancho_c"], a1 + 0.3))
            info = pixel_grid(d, ex["cx"], ex["cy"], ex["sc"], A, True, t)
            if info and ex["s"] > 0.35:
                Al = int(255 * min(1, (ex["s"] - 0.35) / 0.15))
                x, y, r = info
                txt(d, (x, y - r - 70), "¡TUYO!", 84, YELLOW, Al, "Inter-Black.otf", 9)
    elif name == "roman":
        s = ex["s"]
        cut = SPLIT("roman", 0.45)
        draw_label(layer, t, a0 + 0.1, cut, "ROMAN", ["despegó en agosto · Falcon Heavy"], YELLOW, 140)
        draw_label(layer, t, cut, a1, "1.5 MILLONES DE KM", ["cerca del punto L2"], WHITE, 96)
        A = int(255 * fade(t, a0 + 0.1, a1))
        circle_at(d, cam, O3, R_MOON, (200, 200, 210), A * 0.45, 2)
        L2 = np.array([X_L2, 0, 0])
        poly3(d, cam, [O3 + np.array([0.3, 0, 0]), L2], WHITE, A * 0.25, 3, dash=True)
        if s > 0.55:
            circle_at(d, cam, L2, 0.35, CYAN, A * 0.5 * min(1, (s - 0.55) / 0.1), 3)
        e = pt(cam, O3); m = pt(cam, ex["Pm"]); l2 = pt(cam, L2); tp = pt(cam, ex["Pt"])
        txt(d, (e[0], e[1] + 95), "TIERRA", 40, CYAN, int(A * 0.9), "Inter-Black.otf", 6)
        txt(d, (m[0] + 10, m[1] - 52), "LUNA", 36, WHITE, int(A * 0.8), "Inter-Black.otf", 6)
        d.line([(l2[0] - 14, l2[1] - 14), (l2[0] + 14, l2[1] + 14)], fill=WHITE + (int(A * 0.8),), width=4)
        d.line([(l2[0] - 14, l2[1] + 14), (l2[0] + 14, l2[1] - 14)], fill=WHITE + (int(A * 0.8),), width=4)
        txt(d, (l2[0], l2[1] + 120), "L2", 48, WHITE, int(A * 0.9), "Inter-Black.otf", 6)
        # el Sol queda del otro lado
        arrow(d, (230, 610), (70, 610), (255, 200, 90), int(A * 0.8), 8, 28)
        txt(d, (250, 610), "SOL", 40, (255, 200, 90), int(A * 0.8), "Inter-Black.otf", 6, "lm")
        Ar = int(255 * fade(t, cut, a1))
        if Ar > 0:
            yb = e[1] + 185
            d.line([(e[0], yb), (l2[0], yb)], fill=YELLOW + (Ar,), width=6)
            for x in (e[0], l2[0]):
                d.line([(x, yb - 20), (x, yb + 20)], fill=YELLOW + (Ar,), width=6)
            k = ease_out((t - cut) / 1.0)
            txt(d, ((e[0] + l2[0]) / 2, yb + 48), f"{1.5 * k:.1f} millones de km", 46, YELLOW, Ar, "Inter-Black.otf", 7)
        marker(d, tp[0], tp[1], t, CYAN, int(A * 0.9), 26)
    elif name == "camara":
        if ex["mode"] == "espejo":
            draw_label(layer, t, a0 + 0.1, SUB["camara_b"], "ESPEJO DE 2.4 M", ["igual que el del Hubble"], YELLOW, 116)
            A = int(255 * fade(t, a0 + 0.6, SUB["camara_b"]))
            if A > 0:
                Rm = ex["Rm"]
                p0 = pt(cam, model_pt(O3, Rm, 1.0, (0, -1.17, 0.41))); p1 = pt(cam, model_pt(O3, Rm, 1.0, (0, 1.17, 0.41)))
                d.line([p0[:2], p1[:2]], fill=YELLOW + (A,), width=6)
                for p in (p0, p1):
                    d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], fill=YELLOW + (A,))
                txt(d, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + 52), "2.4 m", 54, YELLOW, A, "Inter-Black.otf", 8)
        elif ex["mode"] == "detector":
            draw_label(layer, t, SUB["camara_b"], SUB["camara_c"] + 0.1, "300 MEGAPÍXELES", ["la cámara de campo amplio"], YELLOW, 112)
        else:
            s = ex["s"]
            draw_label(layer, t, SUB["camara_c"], a1 + 0.2, "1 FOTO = 100", ["fotos del Hubble"], YELLOW, 132, 300)
            side = 920
            A = int(255 * min(1, s / 0.1))
            box2(d, W / 2, H / 2, side, side, YELLOW, A, 8)
            n = int(min(100, ease_out(min(1.0, s / 0.7)) * 100 + 0.5))
            cs = side / 10
            for i in range(n):
                r_, c_ = divmod(i, 10)
                x = W / 2 - side / 2 + (c_ + 0.5) * cs; y = H / 2 - side / 2 + (r_ + 0.5) * cs
                box2(d, x, y, cs - 6, cs - 6, CYAN, int(A * 0.75), 3)
            txt(d, (W / 2 + side / 2 - 10, H / 2 + side / 2 + 50), f"{n} × HUBBLE", 50, CYAN, A, "Inter-Black.otf", 7, "rm")
    elif name == "mision":
        draw_label(layer, t, a0 + 0.1, a1, "ENERGÍA OSCURA", ["acelera la expansión del universo"], (190, 150, 255), 118)
        A = int(255 * fade(t, a0 + 0.3, a1))
        k = ex["a"]
        for ang in np.linspace(0, 2 * np.pi, 8, endpoint=False) + 0.39:
            r0 = 90 * k; r1 = r0 + 60 + 40 * k
            p0 = (W / 2 + r0 * math.cos(ang), 860 + r0 * math.sin(ang)); p1 = (W / 2 + r1 * math.cos(ang), 860 + r1 * math.sin(ang))
            arrow(d, p0, p1, (190, 150, 255), int(A * 0.55), 6, 22)
    elif name == "pixel":
        if ex["mode"] == "zoom":
            draw_label(layer, t, a0 + 0.1, SUB["pixel_b"] + 0.1, "ADOPTA UN PÍXEL", ["te registras en la página de la NASA"], YELLOW, 116)
            A = int(255 * fade(t, a0, SUB["pixel_b"] + 0.3))
            pixel_grid(d, ex["cx"], ex["cy"], ex["sc"], A, True, t)
        else:
            A = int(255 * fade(t, SUB["pixel_b"] - 0.1, a1 + 0.3))
            pixel_grid(d, ex["cx"], ex["cy"], ex["sc"], int(A * 0.4), True, t)
            draw_label(layer, t, SUB["pixel_b"], a1 + 0.2, "TU CERTIFICADO", ["con el número de tu píxel"], WHITE, 112, 330)
            certificate(layer, t, ex["s"])
    elif name == "cierre":
        if ex["mode"] == "foto":
            draw_label(layer, t, a0 + 0.1, SUB["cierre_b"], "7 DE DICIEMBRE", ["el universo en esa foto"], YELLOW, 120)
            A = int(255 * fade(t, a0 + 0.5, SUB["cierre_b"] + 0.2))
            pixel_grid(d, ex["cx"], ex["cy"], ex["sc"], A, True, t)
        else:
            draw_label(layer, t, SUB["cierre_b"], CARD, "UN PEDACITO", ["será tuyo"], YELLOW, 132)
            A = int(255 * fade(t, SUB["cierre_b"], CARD + 0.3))
            pixel_grid(d, ex["cx"], ex["cy"], ex["sc"], A, True, t)
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


def arrow(d, p0, p1, col, A, width=10, head=34):
    d.line([p0, p1], fill=col + (A,), width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    a1 = (p1[0] - head * math.cos(ang - 0.45), p1[1] - head * math.sin(ang - 0.45))
    a2 = (p1[0] - head * math.cos(ang + 0.45), p1[1] - head * math.sin(ang + 0.45))
    d.polygon([p1, a1, a2], fill=col + (A,))


def render(t):
    name = scene(t)
    img = BG.copy()
    if name in ("gancho", "camara", "pixel", "cierre"):
        pass
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
