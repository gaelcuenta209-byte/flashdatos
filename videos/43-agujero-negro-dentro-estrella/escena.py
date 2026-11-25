"""Flash Datos · video 43: un agujero negro más pequeño que un átomo dentro de una estrella.

Escena nueva: estrella tipo Sol con corte transversal y un agujero negro diminuto (lente gravitacional
real sobre el fondo) en el núcleo; Big Bang con agujeros negros primordiales; comparación con un
asteroide; captura gracias a un planeta compañero; caída en espiral al centro; el núcleo devorado;
disco, dos chorros y la explosión con destello azul y de rayos X; campo de agujeros negros como
materia oscura; cierre igual al inicio.

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


# =====================================================================
#  VIDEO 43 · Un agujero negro más pequeño que un átomo dentro de una estrella
# =====================================================================

def draw_body(img, cam, C, r, t, tex, spin=0.0, tilt=0.3, expo=1.0, light=LIGHT):
    """Cuerpo iluminado (planeta o asteroide) con textura en lat/lon."""
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
        col = col[:, None] * np.array([1.0, 0.93, 0.85])
    diff = np.clip(ndl, 0, 1)
    col = col * (0.02 + 1.9 * diff)[:, None] * expo
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a
    return (cx, cy, rpx)


# textura de roca para el asteroide
def _rock_tex():
    th, tw = 256, 512
    la = (0.5 - (np.arange(th) + 0.5) / th) * np.pi
    lo = (np.arange(tw) + 0.5) / tw * 2 * np.pi - np.pi
    LO, LA = np.meshgrid(lo, la)
    x, y, z = np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO)
    n1 = fbm(x * 3 + 5, y * 3, z * 3, 5, seed=3)
    n2 = fbm(x * 9, y * 9 + 2, z * 9, 3, seed=8)
    cr = np.clip(1 - np.abs(n2 - 0.5) * 9, 0, 1) ** 2
    g = 0.22 + 0.35 * n1 - 0.12 * cr
    return np.clip(g, 0.05, 0.7).astype(np.float32)


ROCK = _rock_tex()

# celdas de convección para el corte de la estrella
_gy, _gx = np.mgrid[0:256, 0:256] / 22.0
CELLS = fbm(_gx, _gy, np.full_like(_gx, 1.7), 4, seed=5).astype(np.float32)


def cells(u, v, t):
    iu = ((u * 128 + 128 + t * 3) % 256).astype(int); iv = ((v * 128 + 128) % 256).astype(int)
    return CELLS[iv, iu]


def cutaway(img, info, t, wedge=100.0, core=0.25, rot=-35.0, heat=1.0):
    """Corte transversal en pantalla: una cuña y un disco central muestran el interior de la estrella."""
    if info is None or (wedge <= 0.5 and core <= 0.01):
        return
    cx, cy, rpx = info
    x0 = int(max(0, cx - rpx - 2)); x1 = int(min(W, cx + rpx + 3))
    y0 = int(max(0, cy - rpx - 2)); y1 = int(min(H, cy + rpx + 3))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    u = (xx + 0.5 - cx) / rpx; v = (cy - yy - 0.5) / rpx
    rho = np.sqrt(u * u + v * v)
    ang = np.degrees(np.arctan2(v, u))
    da = np.abs((ang - rot + 180) % 360 - 180)
    edge_w = 1.5 / rpx
    m_w = np.clip((wedge / 2 - da) / 2.0, 0, 1) * (wedge > 0.5)
    m_c = np.clip((core - rho) / edge_w, 0, 1)
    m = np.maximum(m_w, m_c) * np.clip((0.985 - rho) / edge_w, 0, 1)
    if not (m > 0).any():
        return
    c_core = np.array([1.5, 1.0, 0.45], np.float32)
    c_rad = np.array([1.15, 0.45, 0.13], np.float32)
    c_conv = np.array([0.62, 0.2, 0.05], np.float32)
    k1 = smooth(0.18, 0.42, rho)[..., None]
    k2 = smooth(0.66, 0.74, rho)[..., None]
    col = c_core * (1 - k1) + c_rad * k1
    col = col * (1 - k2) + c_conv * k2
    rip = 1 + 0.06 * np.sin(rho * 60 - t * 2.0)
    cv = 0.75 + 0.5 * cells(u, v, t)
    col = col * np.where(rho > 0.7, cv, rip)[..., None]
    col = col + c_core * (np.exp(-rho / 0.1) * 0.3 * heat)[..., None]
    # borde del corte un poco más oscuro (se ve el grosor de la cuña)
    rim = np.clip(1 - np.abs(da - wedge / 2) / 1.6, 0, 1) * (rho < 0.985) * (wedge > 0.5)
    col = col * (1 - 0.45 * rim)[..., None]
    region = img[y0:y1, x0:x1]
    region[:] = region * (1 - m[..., None]) + col * m[..., None]


BHS = []


def draw_bh(img, x, y, rs, lens, feed=0.0, t=0.0):
    """Agujero negro diminuto: lente gravitacional sobre lo que hay detrás, sombra y anillo de fotones."""
    R = int(max(lens * 3.2, rs * 4)) + 2
    x0 = int(max(0, x - R)); x1 = int(min(W, x + R + 1))
    y0 = int(max(0, y - R)); y1 = int(min(H, y + R + 1))
    if x0 >= x1 or y0 >= y1:
        return
    M = int(lens * lens / 2 + R) + 4
    sx0 = int(max(0, x - M)); sx1 = int(min(W, x + M + 1))
    sy0 = int(max(0, y - M)); sy1 = int(min(H, y + M + 1))
    src = img[sy0:sy1, sx0:sx1].copy()
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx = xx + 0.5 - x; dy = yy + 0.5 - y
    d = np.sqrt(dx * dx + dy * dy) + 1e-3
    beta = d - lens * lens / d
    qx = np.clip((x + dx / d * beta).astype(int) - sx0, 0, sx1 - sx0 - 1)
    qy = np.clip((y + dy / d * beta).astype(int) - sy0, 0, sy1 - sy0 - 1)
    new = src[qy, qx]
    bl = np.clip((R - d) / (R * 0.35), 0, 1)[..., None]
    region = img[y0:y1, x0:x1]
    out = region * (1 - bl) + new * bl
    ring = np.exp(-((d - rs * 1.4) / (rs * 0.22)) ** 2) * (0.9 + 2.2 * feed)
    out += ring[..., None] * np.array([1.6, 1.15, 0.7], np.float32)
    if feed > 0:
        g = np.exp(-np.maximum(d - rs, 0) / (rs * 1.6)) * feed * 0.9
        out += g[..., None] * np.array([2.2, 1.1, 0.35], np.float32)
    sh = np.clip(rs - d + 0.5, 0, 1)[..., None]
    region[:] = out * (1 - sh)
    BHS.append((x, y, rs))


RF = np.random.default_rng(3)
NF = 2600
F_U = RF.random(NF); F_P = RF.random(NF) * 2 * np.pi; F_B = 0.4 + RF.random(NF)


def feed_particles(img, cam, C, t, rad=0.5, amt=1.0, tilt=0.35):
    """Gas que cae en espiral hacia el agujero negro."""
    if amt <= 0.01:
        return
    e1 = cam.r; e2 = unit(cam.u * math.cos(tilt) - cam.f * math.sin(tilt))
    r = rad * (1 - (F_U + t * 0.22) % 1.0) ** 1.3 + 0.004
    ph = F_P + t * 0.9 / np.sqrt(r / rad + 0.02)
    P = C[None, :] + r[:, None] * (np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2)
    hot = np.clip(1 - r / rad, 0, 1)
    col = np.stack([2.4 + 1.5 * hot, 1.0 + 1.8 * hot, 0.3 + 1.6 * hot], -1) * (0.03 * amt * F_B)[:, None]
    splat(img, cam, P, col.astype(np.float32))


# ---------------- planos ----------------
FIRST = ["gancho", "origen", "captura", "caida", "come", "chorros", "materia", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.22) for i, k in enumerate(FIRST)]
FL = [b for _, b in SHOTS[1:]] + [CARD - 0.05]
O3 = np.zeros(3)


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


ST_HOT = np.array([1.6, 1.0, 0.32]); ST_COOL = np.array([1.05, 0.42, 0.08])


def star(img, cam, t, expo=1.0, spin=None):
    return draw_star(img, cam, O3, 1.0, t, ST_HOT, ST_COOL, expo, spin=0.05 * t if spin is None else spin,
                     halo=1.2, halo_col=np.array([0.9, 0.45, 0.12]), tex=SUN_N, tex_scale=1.0)


def sh_gancho(img, t):
    a0, a1 = span("gancho")
    s = (t - a0) / (a1 - a0)
    R = 9.6 - 1.6 * ease_out(s); ang = 0.35 - 0.3 * s
    cam = Cam((R * math.sin(ang), 0.8 - 0.4 * s, R * math.cos(ang)), (0, -0.33, 0), roll=0.05)
    info = star(img, cam, t)
    op = ease((t - 0.7) / 1.6)
    cutaway(img, info, t, 100 * op, 0.24 * op)
    feed_particles(img, cam, O3, t, 0.22, op)
    x, y, _ = pt(cam, O3)
    draw_bh(img, x, y, 11 + 3 * s, 34 + 8 * s, 0.4 * op, t)
    return cam, dict(info=info, bh=(x, y))


RB = np.random.default_rng(11)
NBB = 7000
BB_D = RB.standard_normal((NBB, 3)); BB_D /= np.linalg.norm(BB_D, axis=1, keepdims=True)
BB_V = 0.25 + 0.75 * RB.random(NBB) ** 0.6
BB_C = RB.random(NBB)
PBH_D = RB.standard_normal((9, 3)); PBH_D /= np.linalg.norm(PBH_D, axis=1, keepdims=True)
PBH_V = 0.45 + 0.4 * RB.random(9)
ORIG_CUT = None


def sh_origen(img, t):
    a0, a1 = span("origen")
    cut = SPLIT("origen", 0.72)
    if t < cut:
        s = (t - a0) / (cut - a0)
        ang = 0.2 * s
        cam = Cam((7.5 * math.sin(ang), 0.3, 7.5 * math.cos(ang)), (0, -0.55, 0))
        age = t - a0 + 0.05
        grow = 3.4 * (1 - math.exp(-age / 1.1)) + 0.2 * age
        r = BB_V * grow
        P = BB_D * r[:, None]
        hotc = np.array([2.2, 2.0, 1.8]); warm = np.array([2.2, 1.0, 0.35]); cool = np.array([0.6, 0.9, 2.0])
        mixc = np.where(BB_C[:, None] < 0.6, warm, cool)
        k = math.exp(-age / 0.9)
        col = (hotc * k + mixc * (1 - k)) * (0.14 + 0.5 * math.exp(-age / 0.8)) * (0.6 + 0.6 * BB_C[:, None])
        splat(img, cam, P, col.astype(np.float32))
        x, y, _ = pt(cam, O3)
        yy, xx = np.mgrid[0:H:4, 0:W:4]
        dd = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
        g = (np.exp(-dd / 40) * 4 + np.exp(-dd / 220) * 0.8) * math.exp(-age / 0.5)
        img += ndzoom(g[..., None].astype(np.float32) * np.array([1.0, 0.95, 0.85], np.float32), (4, 4, 1), order=1)[:H, :W]
        pts = []
        if age > 0.35:
            for D, v in zip(PBH_D, PBH_V):
                Pp = D * v * grow * 1.05
                px, py, pz = pt(cam, Pp)
                if pz > 0.5:
                    draw_bh(img, px, py, 4.5, 15, 0.0, t)
                    pts.append((px, py))
        return cam, dict(mode="bb", pts=pts)
    s = (t - cut) / (a1 - cut)
    cam = Cam((0.25 - 0.5 * s, 0.1, 8.6 - 0.4 * s), (0, -0.4, 0))
    RP = np.array([-1.0, 0.3, 0.0]); BP = np.array([0.98, 0.3, 0.0])
    ri = draw_body(img, cam, RP, 0.5, t, ROCK, spin=0.5 * t, tilt=0.4, light=unit([0.6, 0.5, 0.65]))
    bx, by, _ = pt(cam, BP)
    draw_bh(img, bx, by, 6, 20, 0.15, t)
    return cam, dict(mode="cmp", rock=ri, bh=(bx, by))


CAP_CUT = None
PL_A = 2.8


def planet_pos(t):
    ph = 0.3 + 0.45 * (t - S0["captura"])
    return PL_A * np.array([math.cos(ph), 0.0, math.sin(ph)])


def cap_params():
    cut = SPLIT("captura", 0.40)
    tc = SPLIT("captura", 0.78)
    Pc = planet_pos(tc)
    Q = Pc * (1 + 0.14 / PL_A * 2.2)
    ra = float(np.linalg.norm(Q)); rp = 0.55
    a = (ra + rp) / 2; e = (ra - rp) / (ra + rp); bmin = a * math.sqrt(1 - e * e)
    xh = -Q / ra
    yh = np.array([-xh[2], 0.0, xh[0]])
    return cut, tc, Q, a, e, bmin, xh, yh


def bh_cap(t):
    cut, tc, Q, a, e, bmin, xh, yh = cap_params()
    if t < cut:
        u = (t - S0["captura"] + 0.22) / (cut - S0["captura"] + 0.22)
        x = -7.0 + 14.0 * u
        z = 2.3 - 0.7 * math.exp(-(x / 1.6) ** 2)
        return np.array([x, 0.0, z])
    if t < tc:
        u = (t - cut) / (tc - cut)
        return Q + yh * 6.5 * (1 - u) ** 1.6 + xh * 0.8 * (1 - u) ** 2 * (-1)
    M = math.pi + 2 * math.pi / 2.4 * (t - tc)
    E = M
    for _ in range(8):
        E = E - (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    return xh * a * (math.cos(E) - e) + yh * bmin * math.sin(E)


def hidden(cam, P, R=1.0):
    """¿El punto está dentro de la estrella o detrás de ella?"""
    if np.linalg.norm(P) < R:
        return True
    dv = P - cam.O; L = float(np.linalg.norm(dv)); dv = dv / L
    tc = float(-cam.O @ dv)
    if tc <= 0 or tc > L:
        return False
    return float(np.linalg.norm(cam.O + dv * tc)) < R


def sh_captura(img, t):
    a0, a1 = span("captura")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.8 * s, 13.0 - 1.2 * s, 10.8 - 0.8 * s), (0, -1.7, 0), roll=0.03)
    info = star(img, cam, t)
    cut = SPLIT("captura", 0.40)
    pi_ = None
    if t >= cut - 0.3:
        Pp = planet_pos(t)
        pi_ = draw_body(img, cam, Pp, 0.26, t, JUP, spin=0.6 * t, tilt=0.2, light=unit(-Pp + np.array([0, 0.6, 0])))
    P = bh_cap(t)
    bx, by, _ = pt(cam, P)
    vis = not hidden(cam, P)
    if vis:
        draw_bh(img, bx, by, 7, 22, 0.1, t)
    return cam, dict(info=info, planet=pi_, bh=(bx, by), vis=vis)


SP_END = None


def bh_spiral(t):
    a0 = S0["caida"] - 0.22
    te = SPLIT("caida", 0.82)
    u = min(1.0, max(0.0, (t - a0) / (te - a0)))
    r = 2.3 * (1 - u) ** 0.9
    ph = 0.4 + 2 * math.pi * 2.6 * u ** 0.75
    return np.array([r * math.cos(ph), 0.0, r * math.sin(ph)]), u


def sh_caida(img, t):
    a0, a1 = span("caida")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.4 - 0.6 * s, 6.2 - 0.6 * s, 6.4 - 0.4 * s), (0, -0.85, 0), roll=-0.03)
    info = star(img, cam, t)
    cutaway(img, info, t, 130, 0.3, rot=-20)
    P, u = bh_spiral(t)
    bx, by, _ = pt(cam, P)
    draw_bh(img, bx, by, 9, 27, 0.2 + 0.4 * u, t)
    return cam, dict(info=info, bh=(bx, by), u=u)


def sh_come(img, t):
    a0, a1 = span("come")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.35 - 0.2 * s, 0.25, 3.9 - 0.4 * s), (0, -0.12, 0), roll=0.04 * s)
    info = star(img, cam, t)
    cutaway(img, info, t, 0, 1.2, heat=0.5)
    feed_particles(img, cam, O3, t, 0.42, 0.9)
    x, y, _ = pt(cam, O3)
    draw_bh(img, x, y, 22 + 12 * s, 60 + 24 * s, 0.5 + 0.3 * s, t)
    return cam, dict(info=info, bh=(x, y))


RJ = np.random.default_rng(21)
NJ = 5000
J_S = RJ.random(NJ); J_J = RJ.standard_normal((NJ, 2)); J_SIDE = np.where(RJ.random(NJ) < 0.5, 1.0, -1.0)
ND = 3000
D_R = 0.06 + 0.3 * RJ.random(ND) ** 1.5; D_P = RJ.random(ND) * 2 * np.pi; D_Z = RJ.standard_normal(ND) * 0.008
NS = 9000
S_D = RJ.standard_normal((NS, 3)); S_D /= np.linalg.norm(S_D, axis=1, keepdims=True)
S_V = 0.6 + 0.4 * RJ.random(NS); S_C = RJ.random(NS)
EXP_T = None


def sh_chorros(img, t):
    a0, a1 = span("chorros")
    s = (t - a0) / (a1 - a0)
    te = SPLIT("chorros", 0.55)
    ang = 0.25 - 0.35 * s
    R = 8.6 + (2.0 * ease_out((t - te) / 2.0) if t > te else 0)
    cam = Cam((R * math.sin(ang), 0.9, R * math.cos(ang)), (0, -0.3, 0), roll=0.02)
    info = None
    dk = smooth(SPLIT("chorros", 0.18), SPLIT("chorros", 0.34), t)
    jl = 3.2 * ease_out((t - SPLIT("chorros", 0.30)) / (te - SPLIT("chorros", 0.30)))
    if t < te + 0.12:
        info = star(img, cam, t, expo=1.0 + 0.5 * smooth(te - 0.6, te, t), spin=0.05 * t + 2.4 * max(0.0, t - a0))
        cutaway(img, info, t, 0, 0.32 * dk, heat=1.4)
        # disco de acreción en el ecuador
        if dk > 0.01:
            ph = D_P + (t - a0) * 3.0 / np.sqrt(D_R)
            P = np.stack([D_R * np.cos(ph), D_Z, D_R * np.sin(ph)], -1)
            hot = np.clip(1 - D_R / 0.36, 0, 1)
            col = np.stack([2.0 + 2 * hot, 1.2 + 2 * hot, 0.6 + 2.4 * hot], -1) * (0.05 * dk)
            splat(img, cam, P, col.astype(np.float32))
        x, y, _ = pt(cam, O3)
        draw_bh(img, x, y, 10, 28, 0.6 * dk, t)
    if jl > 0.01:
        L = jl if t < te else jl + 9.0 * (t - te)
        fadej = 1.0 if t < te else math.exp(-(t - te) / 1.3)
        r = J_S * L
        w = 0.03 + r * 0.06
        P = np.stack([J_J[:, 0] * w, J_SIDE * r, J_J[:, 1] * w], -1)
        col = np.array([0.8, 1.4, 2.6], np.float32)[None, :] * ((0.14 + 0.14 * (r > 1.0)) * fadej * (0.6 + 0.4 * np.sin(J_S * 50 - t * 20)))[:, None]
        splat(img, cam, P, col.astype(np.float32))
    if t >= te:
        age = t - te
        rr = S_V * (1.0 + 4.5 * (1 - math.exp(-age / 0.9)))
        P = S_D * rr[:, None]
        k = math.exp(-age / 1.0)
        base = np.where(S_C[:, None] < 0.55, np.array([0.7, 1.2, 2.6]), np.array([2.4, 1.3, 0.5]))
        col = base * (0.018 + 0.05 * k) * (0.5 + 0.8 * S_C[:, None])
        splat(img, cam, P, col.astype(np.float32))
        img += np.float32(0.9 * math.exp(-age / 0.18)) * np.array([0.55, 0.8, 1.6], np.float32)
        x, y, _ = pt(cam, O3)
        yy, xx = np.mgrid[0:H:4, 0:W:4]
        dd = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
        g = (np.exp(-dd / 60) * 1.6 + np.exp(-dd / 260) * 0.35) * (0.2 + 0.8 * math.exp(-age / 0.6))
        img += ndzoom(g[..., None].astype(np.float32) * np.array([0.6, 0.85, 1.6], np.float32), (4, 4, 1), order=1)[:H, :W]
    return cam, dict(info=info, te=te)


RG = np.random.default_rng(5)
NG = 14000
G_R = RG.random(NG) ** 0.7 * 3.2
G_ARM = RG.integers(0, 2, NG)
G_TH = G_R * 1.6 + G_ARM * math.pi + RG.standard_normal(NG) * 0.28
G_Y = RG.standard_normal(NG) * 0.05
G_B = 0.5 + RG.random(NG)
LENS = [(0.28, 0.33, 6, 22), (0.70, 0.41, 5, 18), (0.46, 0.55, 7, 26), (0.18, 0.62, 4, 15),
        (0.80, 0.60, 5, 19), (0.58, 0.28, 4, 14), (0.36, 0.73, 5, 17), (0.86, 0.25, 4, 14), (0.12, 0.40, 4, 14)]
_dy, _dx = np.mgrid[0:120, 0:68] / 22.0
DMH = fbm(_dx, _dy, np.full_like(_dx, 4.1), 5, seed=13)
DMH = ndzoom(np.clip((DMH - 0.38) * 2.4, 0, 1) ** 1.3, (H / 120, W / 68), order=1).astype(np.float32)


def sh_materia(img, t):
    a0, a1 = span("materia")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.0, 4.2 - 0.6 * s, 6.5), (0.0, -0.1, 0.0), roll=0.12 + 0.05 * s)
    th = G_TH + 0.05 * (t - a0)
    P = np.stack([G_R * np.cos(th), G_Y, G_R * np.sin(th)], -1) + np.array([0, -0.5, -2.0])
    core = np.exp(-G_R / 0.7)
    col = np.stack([0.9 + 1.2 * core, 0.85 + 0.8 * core, 1.4 - 0.5 * core], -1) * (0.035 * G_B)[:, None]
    splat(img, cam, P, col.astype(np.float32))
    hz = smooth(SPLIT("materia", 0.4), SPLIT("materia", 0.7), t)
    img += (DMH * (0.05 * hz))[..., None] * np.array([0.55, 0.25, 1.0], np.float32)
    pts = []
    for i, (fx, fy, rs, ln) in enumerate(LENS):
        x = fx * W + 25 * math.sin(0.4 * t + i); y = fy * H + 20 * math.cos(0.33 * t + 2 * i)
        draw_bh(img, x, y, rs, ln, 0.0, t)
        pts.append((x, y, ln))
    return cam, dict(pts=pts, hz=hz)


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    s = (t - a0) / (END - a0)
    R = 8.2 + 1.4 * ease_out(s); ang = -0.05 + 0.4 * s
    cam = Cam((R * math.sin(ang), 0.4 + 0.4 * s, R * math.cos(ang)), (0, -0.33, 0), roll=0.05)
    info = star(img, cam, t)
    cutaway(img, info, t, 100, 0.24)
    feed_particles(img, cam, O3, t, 0.22, 1.0)
    x, y, _ = pt(cam, O3)
    draw_bh(img, x, y, 14, 42, 0.5, t)
    return cam, dict(info=info, bh=(x, y))


SCENES = dict(gancho=sh_gancho, origen=sh_origen, captura=sh_captura, caida=sh_caida, come=sh_come,
              chorros=sh_chorros, materia=sh_materia, cierre=sh_cierre)


# ---------------- textos y gráficos ----------------
def trail(d, cam, f, ta, tb, col, A, n=60, width=6):
    if tb <= ta or A <= 0:
        return
    pts = []
    for i in range(n):
        tt = ta + (tb - ta) * i / (n - 1)
        x, y, z = pt(cam, f(tt))
        pts.append((x, y))
    for i in range(n - 1):
        a = int(A * (i / (n - 1)) ** 1.5)
        d.line([pts[i], pts[i + 1]], fill=col + (a,), width=width)


def years(k):
    v = int(10 ** (1 + 5.6 * k))
    return f"{v:,}"


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    if name == "gancho":
        cut = SPLIT("gancho", 0.6)
        draw_label(layer, t, -1, cut, "AGUJERO NEGRO", ["más pequeño que un átomo"], YELLOW, 118)
        draw_label(layer, t, cut, a1 + 0.3, "¡DESDE ADENTRO!", ["podría comerse una estrella"], WHITE, 112)
        x, y = ex["bh"]
        Am = int(255 * fade(t, 1.4, a1 + 0.3))
        marker(d, x, y, t, CYAN, Am, 50)
    elif name == "origen":
        if ex["mode"] == "bb":
            draw_label(layer, t, a0 + 0.1, SPLIT("origen", 0.72), "PRIMORDIALES", ["nacidos poco después del Big Bang"], YELLOW, 120)
            A = int(255 * fade(t, a0 + 0.9, SPLIT("origen", 0.72)) * 0.8)
            for (px, py) in ex["pts"][:5]:
                marker(d, px, py, t, CYAN, A, 26)
        else:
            cut = SPLIT("origen", 0.72)
            draw_label(layer, t, cut, a1, "MASA DE UN ASTEROIDE", ["en algo más chico que un átomo"], WHITE, 104)
            A = int(255 * fade(t, cut + 0.2, a1))
            if ex["rock"]:
                x, y, r = ex["rock"]
                txt(d, (x, y + r + 60), "ASTEROIDE", 50, WHITE, A, "Inter-Black.otf", 7)
            x, y = ex["bh"]
            marker(d, x, y, t, CYAN, A, 44)
            txt(d, (x, y + 100), "AGUJERO NEGRO", 40, YELLOW, A, "Inter-Black.otf", 7)
            txt(d, (W / 2, y - 6), "=", 120, YELLOW, A, "Inter-Black.otf", 8)
    elif name == "captura":
        cut = SPLIT("captura", 0.40)
        _, tc, *_ = cap_params()
        draw_label(layer, t, a0 + 0.1, cut, "SOLA, NO PUEDE", ["el agujero negro pasa de largo"], WHITE, 118)
        draw_label(layer, t, cut, tc, "CON UN PLANETA", ["o una estrella compañera"], CYAN, 116)
        draw_label(layer, t, tc, a1, "¡ATRAPADO!", ["queda en órbita"], YELLOW, 130)
        A = int(255 * fade(t, a0 + 0.1, a1))
        if t < cut:
            trail(d, cam, bh_cap, max(a0, t - 2.5), t, CYAN, int(A * 0.8))
            Ax = int(255 * fade(t, SPLIT("captura", 0.26), cut))
            if Ax > 0:
                x, y = ex["bh"]
                d.line([(x - 40, y - 40), (x + 40, y + 40)], fill=RED + (Ax,), width=12)
                d.line([(x - 40, y + 40), (x + 40, y - 40)], fill=RED + (Ax,), width=12)
        else:
            trail(d, cam, bh_cap, max(cut, t - 2.2), t, YELLOW if t > tc else CYAN, int(A * 0.85))
            if ex["planet"]:
                x, y, r = ex["planet"]
                txt(d, (x, y - r - 40), "PLANETA", 44, WHITE, int(255 * fade(t, cut, tc + 0.5)), "Inter-Black.otf", 6)
        if ex["vis"]:
            x, y = ex["bh"]
            marker(d, x, y, t, CYAN, int(A * 0.9), 30)
    elif name == "caida":
        te = SPLIT("caida", 0.78)
        draw_label(layer, t, a0 + 0.1, te, "FRENA EN CADA PASO", ["al atravesar la estrella"], WHITE, 108)
        draw_label(layer, t, te, a1, "¡AL CENTRO!", [], YELLOW, 140)
        A = int(255 * fade(t, a0 + 0.1, a1))
        trail(d, cam, lambda tt: bh_spiral(tt)[0], max(a0, t - 1.6), t, CYAN, int(A * 0.85), 80)
        x, y = ex["bh"]
        marker(d, x, y, t, CYAN, A, 30)
    elif name == "come":
        draw_label(layer, t, a0 + 0.1, a1, "SE LA COME", ["por dentro, poco a poco"], WHITE, 124)
        A = int(255 * fade(t, a0 + 0.3, a1))
        k = min(1.0, (t - a0 - 0.3) / (a1 - a0 - 1.1))
        if A > 0 and k >= 0:
            if k < 1.0:
                txt(d, (W / 2, 640), years(k), 96, YELLOW, A, "Inter-Black.otf", 9)
                txt(d, (W / 2, 720), "AÑOS", 54, CYAN, A, "Inter-ExtraBold.otf", 7)
            else:
                txt(d, (W / 2, 650), "MILLONES DE AÑOS", 84, YELLOW, A, "Inter-Black.otf", 9)
    elif name == "chorros":
        te = ex["te"]
        draw_label(layer, t, a0 + 0.1, SPLIT("chorros", 0.22), "SI GIRA RÁPIDO…", [], WHITE, 120)
        draw_label(layer, t, SPLIT("chorros", 0.22), te, "DISCO + 2 CHORROS", ["salen por los polos"], CYAN, 110)
        draw_label(layer, t, te, SPLIT("chorros", 0.68), "¡LA REVIENTA!", [], ORANGE, 136)
        draw_label(layer, t, SPLIT("chorros", 0.68), a1, "RAYOS X + LUZ AZUL", ["un destello visible"], CYAN, 108)
        if t > te:
            x, y, _ = pt(cam, O3)
            for j in range(3):
                age = t - te - 0.25 * j
                if age <= 0:
                    continue
                r = 60 + age * 520
                Ar = int(200 * max(0.0, 1 - age / 1.6))
                if Ar > 0:
                    d.ellipse([x - r, y - r, x + r, y + r], outline=CYAN + (Ar,), width=8)
    elif name == "materia":
        cut = SPLIT("materia", 0.45)
        draw_label(layer, t, a0 + 0.1, cut, "NADIE HA VISTO UNO", ["por ahora, es teoría"], WHITE, 108)
        draw_label(layer, t, cut, a1, "¿MATERIA OSCURA?", ["podrían ser parte de ella"], YELLOW, 116)
        A = int(255 * fade(t, a0 + 0.4, a1) * 0.85)
        for (x, y, ln) in ex["pts"][:5]:
            if 560 < y < 1220:
                txt(d, (x + ln + 26, y - ln - 10), "?", 54, CYAN, A, "Inter-Black.otf", 6)
    elif name == "cierre":
        cut = SPLIT("cierre", 0.5)
        draw_label(layer, t, a0 + 0.1, cut, "PUEDE MORIR", ["por culpa de un monstruo diminuto"], WHITE, 120)
        draw_label(layer, t, cut, CARD, "MÁS CHICO QUE UN ÁTOMO", [], YELLOW, 100)
        x, y = ex["bh"]
        marker(d, x, y, t, CYAN, int(255 * fade(t, a0 + 0.2, CARD)), 52)
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
    BHS.clear()
    cam, ex = SCENES[name](img, t)
    img = bloom(img)
    for (bx, by, rs) in BHS:
        x0 = int(max(0, bx - rs - 3)); x1 = int(min(W, bx + rs + 4)); y0 = int(max(0, by - rs - 3)); y1 = int(min(H, by + rs + 4))
        if x0 < x1 and y0 < y1:
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            dd = np.sqrt((xx + 0.5 - bx) ** 2 + (yy + 0.5 - by) ** 2)
            img[y0:y1, x0:x1] *= (1 - np.clip(rs * 0.95 - dd + 0.5, 0, 1))[..., None]
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
