"""Flash Datos · video 44: Gemínidas 2026, la lluvia de estrellas que viene de un asteroide.

Escena nueva: cielo nocturno con montañas y pinos en silueta, Vía Láctea y meteoros que salen del
radiante en Géminis (Cástor y Pólux); cometa con sus dos colas frente al asteroide 3200 Faetón;
vista del sistema solar con la órbita alargada de Faetón rozando el Sol y dejando su rastro de polvo;
la Tierra cruzando la corriente y granitos que se encienden en la atmósfera; Luna creciente al 20 %
que se mete tras los cerros al anochecer; reloj a las 2 a. m. y el resplandor de la ciudad que se
apaga; cierre con el mismo cielo del inicio.

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
#  VIDEO 44 · Gemínidas 2026: la lluvia de estrellas que viene de un asteroide
# =====================================================================
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
SUN_N = np.clip((SUNT - 0.63) / 0.38, 0, 1).astype(np.float32)
SOL_HOT = np.array([3.0, 2.3, 1.05]); SOL_COOL = np.array([1.9, 1.0, 0.32])

# ---------------- cielo nocturno (plano 2D con paralaje) ----------------
PADX, PADY = 240, 320


def _sky_stars():
    rng = np.random.default_rng(44)
    HH, WW = H + PADY, W + PADX
    sk = np.zeros((HH, WW, 3), np.float32)
    n = 5200
    x = rng.integers(0, WW, n); y = rng.integers(0, HH, n)
    inten = 0.03 + 0.7 * rng.random(n) ** 9
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(sk, (y, x), col * inten[:, None])
    sk = gaussian_filter(sk, (0.7, 0.7, 0))
    big = np.zeros_like(sk)
    m = 110
    bx = rng.integers(0, WW, m); by = rng.integers(0, HH, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.96, 0.92]) * (1.2 + 3.5 * rng.random(m))[:, None])
    sk += gaussian_filter(big, (1.3, 1.3, 0))
    # Vía Láctea: banda diagonal tenue con nubes oscuras
    gy, gx = np.mgrid[0:HH // 8, 0:WW // 8].astype(np.float32)
    u = (gx * 8 - WW * 0.62) * 0.8 + (gy * 8 - HH * 0.35) * 0.6
    band = np.exp(-(u / 260.0) ** 2)
    nz = fbm(gx / 22.0, gy / 22.0, np.full_like(gx, 3.3), 5, seed=31)
    dk = fbm(gx / 9.0, gy / 9.0, np.full_like(gx, 7.7), 4, seed=37)
    mw = band * np.clip(nz * 1.3 - 0.2, 0, 1) * np.clip(1.2 - dk * 1.1, 0, 1)
    mw = ndzoom(mw, (HH / mw.shape[0], WW / mw.shape[1]), order=1)[:HH, :WW]
    sk += mw[..., None] * np.array([0.055, 0.058, 0.075], np.float32)
    sk += (mw[..., None] ** 2) * np.array([0.0, 0.0, 0.0], np.float32)
    return sk


SKY = _sky_stars()
_gy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]


def hill_profile(seed, base, amp, x):
    rng = np.random.default_rng(seed)
    h = np.zeros_like(x, dtype=np.float64)
    for k in range(1, 7):
        h += amp / k ** 1.2 * np.sin(x / W * math.pi * (k * 1.3 + rng.random()) + rng.random() * 6)
    return base + h


XS = np.arange(W, dtype=np.float64)
# árboles (pinos) en la silueta
RT = np.random.default_rng(8)
TREES = [(RT.uniform(0, W), RT.uniform(28, 70)) for _ in range(22)]


def sky_bg(img, hz, drift=(0, 0), twi=0.0, city=0.0, glow_side=-1):
    """Cielo: degradado + estrellas + Vía Láctea; hz = altura del horizonte en px (y)."""
    ox = int(PADX / 2 + drift[0]); oy = int(PADY / 2 + drift[1])
    ox = min(max(ox, 0), PADX); oy = min(max(oy, 0), PADY)
    img[:] = SKY[oy:oy + H, ox:ox + W]
    yy = np.arange(H, dtype=np.float32)[:, None, None]
    k = np.clip(1 - (hz - yy) / (hz + 1), 0, 1) ** 3          # 0 arriba → 1 en el horizonte
    img += np.array([0.004, 0.007, 0.022], np.float32) + k * np.array([0.03, 0.05, 0.11], np.float32)
    if twi > 0:   # crepúsculo
        img *= (1 - 0.6 * twi * k)
        img += (k ** 1.5) * twi * np.array([0.55, 0.22, 0.07], np.float32) + (k ** 0.7) * twi * np.array([0.03, 0.06, 0.16], np.float32)
    if city > 0:  # contaminación lumínica de una ciudad a un lado
        xx = np.arange(W, dtype=np.float32)[None, :, None]
        side = np.exp(-((xx - (W * 0.15 if glow_side < 0 else W * 0.85)) / (W * 0.45)) ** 2)
        img *= (1 - 0.5 * city * side * k)
        img += city * side * (k ** 2.2) * np.array([0.65, 0.36, 0.12], np.float32) + city * side * k * np.array([0.08, 0.05, 0.03], np.float32)


def hills(img, hz, seed=3, amp=60, lights=0.0, parallax=0.0, trees=True):
    h1 = hill_profile(seed, hz, amp, XS + parallax)
    h2 = hill_profile(seed + 10, hz + 70, amp * 0.7, XS + parallax * 1.8)
    yy = np.arange(H, dtype=np.float32)[:, None]
    for h, col in ((h1, np.array([0.006, 0.008, 0.016], np.float32)), (h2, np.array([0.002, 0.003, 0.006], np.float32))):
        a = np.clip(yy - h[None, :] + 0.5, 0, 1)
        img[:] = img * (1 - a[..., None]) + col * a[..., None]
    if trees:
        lay = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(lay)
        for (tx, th) in TREES:
            x = (tx + parallax * 1.8) % (W + 100) - 50
            base = hill_profile(seed + 10, hz + 70, amp * 0.7, np.array([x]))[0] + 6
            for j in range(4):
                w = th * (0.42 - 0.08 * j); y1 = base - th * (0.25 + 0.25 * j)
                d.polygon([(x - w, base - th * 0.22 * j), (x + w, base - th * 0.22 * j), (x, y1 - th * 0.25)], fill=255)
            d.rectangle([x - 3, base - 8, x + 3, base + 10], fill=255)
        a = np.asarray(lay, np.float32)[..., None] / 255.0
        img[:] = img * (1 - a)
    if lights > 0:
        rng = np.random.default_rng(seed + 99)
        n = 60
        lx = rng.integers(0, int(W * 0.45), n); ly = (h2[lx] + rng.integers(8, 120, n)).astype(int)
        ok = ly < H
        pts = np.zeros((H, W, 3), np.float32)
        np.add.at(pts, (ly[ok], lx[ok]), np.array([2.5, 1.6, 0.7], np.float32) * lights)
        img += gaussian_filter(pts, (1.2, 1.2, 0))


# ---------------- meteoros ----------------
RM = np.random.default_rng(1213)
NM = 900
M_T = np.sort(RM.random(NM)) * 60.0            # nacimiento (s)
M_U = RM.random(NM)                            # umbral de tasa
M_TH = RM.random(NM) * 2 * np.pi               # dirección desde el radiante
M_D0 = 60 + RM.random(NM) ** 0.8 * 900          # distancia inicial al radiante (px)
M_L = 220 + RM.random(NM) * 520                # recorrido (px)
M_DUR = 0.35 + RM.random(NM) * 0.55
M_B = 1.6 + RM.random(NM) ** 3 * 5.0
M_C = RM.random(NM)
M_COL = np.where(M_C[:, None] < 0.68, np.array([1.0, 1.0, 1.05]),
                 np.where(M_C[:, None] < 0.9, np.array([1.25, 1.0, 0.55]), np.array([0.6, 1.3, 0.75])))


def meteors(img, t, rad, rate, hz=H, drift=(0, 0), scale=1.0, force=()):
    """Estelas desde el radiante. rate = fracción de la lista que se ve (0..1)."""
    lay = np.zeros((H // 2, W // 2, 3), np.float32)
    rx, ry = rad[0] - drift[0], rad[1] - drift[1]
    idx = np.nonzero((M_T <= t) & (M_T + M_DUR > t) & ((M_U < rate) | np.isin(np.arange(NM), force)))[0]
    for i in idx:
        p = (t - M_T[i]) / M_DUR[i]
        dx, dy = math.cos(M_TH[i]), math.sin(M_TH[i])
        dhead = (M_D0[i] + M_L[i] * p) * scale
        tail = min(M_L[i] * scale * 0.55, (dhead - M_D0[i] * scale) + 30)
        env = math.sin(math.pi * min(p * 1.15, 1.0)) ** 0.8
        n = 40
        s = np.linspace(0, 1, n)
        xs = rx + dx * (dhead - tail * (1 - s)); ys = ry + dy * (dhead - tail * (1 - s))
        w = (s ** 2.2) * env * M_B[i]
        ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < min(hz, H))
        if not ok.any():
            continue
        np.add.at(lay, ((ys[ok] / 2).astype(int), (xs[ok] / 2).astype(int)), M_COL[i] * w[ok, None] * 0.9)
    if len(idx):
        lay = gaussian_filter(lay, (0.7, 0.7, 0)) * 2.2 + gaussian_filter(lay, (4, 4, 0)) * 1.2
        img += ndzoom(lay, (2, 2, 1), order=1)[:H, :W]


# Géminis: posiciones relativas al radiante (px), Cástor y Pólux
GEM = [(-70, -40, 1.6, "CÁSTOR"), (40, 20, 2.0, "PÓLUX"), (-150, 160, 0.7, None), (-40, 210, 0.8, None),
       (-230, 300, 0.7, None), (-80, 360, 0.6, None), (60, 280, 0.6, None)]
GEM_L = [(0, 2), (2, 4), (1, 3), (3, 6), (2, 3), (3, 5)]


def gemini_stars(img, rad, drift, A=1.0):
    pts = np.zeros((H // 2, W // 2, 3), np.float32)
    for (gx, gy, b, _) in GEM:
        x = rad[0] + gx - drift[0]; y = rad[1] + gy - drift[1]
        if 0 <= x < W and 0 <= y < H:
            pts[int(y / 2), int(x / 2)] += np.array([1.0, 0.95, 0.85]) * b * 6 * A
    img += ndzoom(gaussian_filter(pts, (1.0, 1.0, 0)), (2, 2, 1), order=1)[:H, :W]


def sky_shot(img, t, rad, rate, hz, drift, twi=0.0, city=0.0, lights=0.0, gem=1.0, seed=3, parallax=0.0, force=()):
    sky_bg(img, hz, drift, twi, city)
    if gem > 0:
        gemini_stars(img, rad, drift, gem)
    meteors(img, t, rad, rate, hz + 40, drift, force=force)
    hills(img, hz, seed, lights=lights, parallax=parallax)


# ---------------- espacio: Sol, órbita de Faetón y su polvo ----------------
AU = 3.0
Q_F = 0.14 * AU; QA_F = 2.40 * AU
A_F = (Q_F + QA_F) / 2; E_F = (QA_F - Q_F) / (QA_F + Q_F); B_F = A_F * math.sqrt(1 - E_F ** 2)
INC = math.radians(14)


def orbit_pt(M):
    """Punto de la órbita de Faetón para anomalía media M (array o escalar). Perihelio hacia +z."""
    M = np.asarray(M, float)
    E = M.copy()
    for _ in range(12):
        E = E - (E - E_F * np.sin(E) - M) / (1 - E_F * np.cos(E))
    x = A_F * (np.cos(E) - E_F); y = B_F * np.sin(E)
    # plano orbital: x→z (perihelio hacia la cámara), y→x, inclinado
    P = np.stack([y, 0.0 * x, x], -1)
    return P


RD = np.random.default_rng(77)
ND = 9000
D_M = RD.random(ND) * 2 * np.pi
D_J = RD.standard_normal((ND, 3)) * 0.05
D_B = 0.4 + RD.random(ND)


def dust(img, cam, amt=1.0, Mf=0.0, grow=2 * np.pi, bright=1.0):
    if amt <= 0:
        return
    back = (Mf - D_M) % (2 * np.pi)
    vis = back < grow
    P = orbit_pt(D_M[vis]) + D_J[vis] * (0.5 + np.abs(orbit_pt(D_M[vis])[:, 2:3]) * 0.04)
    k = np.exp(-back[vis] / 9.0)
    col = np.stack([1.4 + 0 * k, 1.05 + 0 * k, 0.65 + 0.4 * k], -1) * (0.022 * amt * bright * D_B[vis])[:, None]
    splat(img, cam, P, col.astype(np.float32))


def sun(img, cam, r=0.32, expo=1.0, t=0.0):
    return draw_star(img, cam, O3, r, t, SOL_HOT, SOL_COOL, expo, spin=0.04 * t, halo=2.2,
                     halo_col=np.array([1.6, 1.1, 0.5]), tex=SUN_N, tex_scale=1.0)


def ring_line(d, cam, f, n, col, A, width=3, dash=False):
    pts = [pt(cam, f(i / (n - 1))) for i in range(n)]
    for i in range(n - 1):
        if dash and i % 3 == 2:
            continue
        if pts[i][2] > 0.1 and pts[i + 1][2] > 0.1:
            d.line([pts[i][:2], pts[i + 1][:2]], fill=col + (A,), width=width)


# ---------------- planos ----------------
O3 = np.zeros(3)
FIRST = ["gancho", "origen", "rastro", "cruce", "luna", "hora", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.22) for i, k in enumerate(FIRST)]
SUB = {"origen_b": SPLIT("origen", 0.42), "origen_c": SPLIT("origen", 0.70), "cruce_b": SPLIT("cruce", 0.52)}
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


RAD0 = (W * 0.58, 520)


def sh_gancho(img, t):
    a0, a1 = span("gancho")
    s = (t - a0) / (a1 - a0)
    drift = (-40 * s, 30 - 60 * s)
    rate = 0.45 + 0.5 * ease(s * 1.2)
    sky_shot(img, t, RAD0, rate, 1480, drift, parallax=-30 * s, force=[i for i in range(NM) if 1.6 < M_T[i] < 2.4][:3])
    return None, dict(drift=drift)


COMET_P = np.array([0.0, 0.0, 0.0])
RC = np.random.default_rng(5)
NC = 6000
C_S = RC.random(NC); C_J = RC.standard_normal((NC, 2)); C_K = RC.random(NC)


def sh_origen(img, t):
    a0, a1 = span("origen")
    tb, tc = SUB["origen_b"], SUB["origen_c"]
    if t < tb:
        s = (t - a0) / (tb - a0)
        rad = (W * 0.52, 640)
        drift = (20 * s, -30 * s)
        sky_shot(img, t + 7.0, rad, 0.75, 1520, drift, gem=1.6, seed=5, parallax=20 * s)
        return None, dict(mode="sky", rad=rad, drift=drift)
    if t < tc:
        s = (t - tb) / (tc - tb)
        img[:] = BG
        cam = Cam((0.3 - 0.4 * s, 0.4, 7.0 - 0.5 * s), (0, -0.2, 0))
        # cola de cometa: polvo (amarillento, curvo) e iones (azul, recta), lejos del Sol (arriba a la derecha)
        tail_dir = unit([0.55, 0.85, -0.2])
        L = 4.5 * C_S ** 0.9
        curve = np.array([0.6, -0.15, 0.0])
        Pd = COMET_P + L[:, None] * tail_dir + (L ** 2)[:, None] * curve * 0.12 + np.concatenate([C_J * (0.04 + 0.16 * C_S[:, None]), np.zeros((NC, 1))], 1)
        ion = C_K < 0.4
        Pd[ion] = COMET_P + L[ion, None] * unit([0.35, 0.95, -0.1]) + np.concatenate([C_J[ion] * 0.03, np.zeros((ion.sum(), 1))], 1)
        col = np.where(ion[:, None], np.array([0.45, 0.8, 2.0]), np.array([1.7, 1.4, 0.9])) * (0.045 * (1 - C_S) ** 1.5 + 0.004)[:, None]
        splat(img, cam, Pd, col.astype(np.float32))
        x, y, _ = pt(cam, COMET_P)
        yy, xx = np.mgrid[0:H:4, 0:W:4]
        dd = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
        g = np.exp(-dd / 14) * 3.0 + np.exp(-dd / 70) * 0.6
        img += ndzoom(g[..., None].astype(np.float32) * np.array([0.8, 1.0, 1.2], np.float32), (4, 4, 1), order=1)[:H, :W]
        return cam, dict(mode="comet", c=(x, y))
    s = (t - tc) / (a1 - tc)
    img[:] = BG
    cam = Cam((0.0, 0.25, 6.0 - 0.9 * ease(s)), (0, -0.4, 0))
    sunv = unit([-0.9, 0.3, 0.3])
    info = draw_body(img, cam, O3, 1.0, t, ROCK, spin=0.35 * t, tilt=0.5, light=sunv, tint=(0.62, 0.62, 0.66), expo=0.9, amb=0.01)
    return cam, dict(mode="rock", info=info)


def mf_rastro(t):
    a0, a1 = span("rastro")
    u = (t - a0) / (a1 - a0)
    return -1.1 + 2.0 * u          # pasa por el perihelio (M = 0) a la mitad del plano


def cam_space(s):
    return Cam((1.2 - 1.0 * s, 15.5 - 1.0 * s, 9.5 + 0.6 * s), (0.0, -1.6, -2.4), roll=0.02)


def sh_rastro(img, t):
    a0, a1 = span("rastro")
    s = (t - a0) / (a1 - a0)
    img[:] = BG
    cam = cam_space(s)
    sun(img, cam, 0.34, 1.0, t)
    Mf = mf_rastro(t)
    grow = 0.25 + 6.0 * ease(min(1.0, s * 1.15))
    dust(img, cam, 1.0, Mf, grow, 1.1)
    Pf = orbit_pt(Mf)
    info = draw_body(img, cam, Pf, 0.13, t, ROCK, spin=t, light=unit(-Pf + np.array([0, 0.3, 0])), expo=1.6)
    return cam, dict(Pf=Pf, info=info)


EARTH_C = np.array([0.0, 0.0, 0.0])
_Ms = np.linspace(0.0, np.pi, 4000)
_rr = np.linalg.norm(orbit_pt(_Ms)[:, [0, 2]], axis=1)
_PX = orbit_pt(_Ms[np.argmin(np.abs(_rr - AU))])
TH_X = math.atan2(_PX[0], _PX[2])


def sh_cruce(img, t):
    a0, a1 = span("cruce")
    tb = SUB["cruce_b"]
    if t < tb:
        s = (t - a0) / (tb - a0)
        img[:] = BG
        cam = cam_space(1.0 + 0.3 * s)
        sun(img, cam, 0.34, 1.0, t)
        dust(img, cam, 1.0, 0.9, 2 * np.pi, 1.1)
        # la Tierra recorre su órbita (r = 1 UA) y entra en la corriente
        th = TH_X + 0.10 * (s - 0.6)
        Pe = AU * np.array([math.sin(th), 0.0, math.cos(th)])
        draw_earth(img, cam, Pe, 0.16, t, atm=0.06, glow=1.0, expo=1.4)
        return cam, dict(mode="orb", Pe=Pe, th=th)
    s = (t - tb) / (a1 - tb)
    img[:] = BG
    cam = Cam(np.array([2.9, 1.5, -3.2]) * (1.0 - 0.05 * s), (0.0, 0.75, 0.0), roll=-0.05)
    draw_earth(img, cam, EARTH_C, 1.0, t, atm=0.035, glow=0.8, expo=1.0, lon=-1.9)
    cdir = unit(cam.O)
    # granitos que entran a la atmósfera: estelas rectas que se encienden en el limbo del lado nocturno
    rng = np.random.default_rng(int(t * 30))
    lay = np.zeros((H // 2, W // 2, 3), np.float32)
    tt0 = t - tb
    for i in range(70):
        r0 = np.random.default_rng(1000 + i)
        st = r0.random() * 7.0; dur = 0.45 + 0.3 * r0.random()
        p = (tt0 - st) / dur
        if not (0 <= p < 1):
            continue
        while True:
            v = unit(r0.standard_normal(3))
            if 0.08 < v @ cdir < 0.45 and v[1] > -0.2:
                break
        Phit = v * 1.04
        dv = unit(-v * 0.6 + np.cross(v, cdir) * 0.8)
        L = 0.35
        head = Phit - dv * L * (1 - p)
        tail = head - dv * 0.25
        hx, hy, _ = pt(cam, head); tx, ty, _ = pt(cam, tail)
        burn = smooth(0.55, 0.85, p)
        n = 30
        ss = np.linspace(0, 1, n)
        xs = tx + (hx - tx) * ss; ys = ty + (hy - ty) * ss
        w = ss ** 2 * (0.6 + 9.0 * burn) * (1 - smooth(0.9, 1.0, p))
        ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
        c = np.array([1.2, 1.0, 0.7]) if burn < 0.5 else np.array([1.6, 1.4, 1.0])
        np.add.at(lay, ((ys[ok] / 2).astype(int), (xs[ok] / 2).astype(int)), c * w[ok, None])
    lay = gaussian_filter(lay, (0.9, 0.9, 0)) + gaussian_filter(lay, (5, 5, 0)) * 0.7
    img += ndzoom(lay, (2, 2, 1), order=1)[:H, :W]
    return cam, dict(mode="earth")


def sh_luna(img, t):
    a0, a1 = span("luna")
    s = (t - a0) / (a1 - a0)
    hz = 1500
    sky_bg(img, hz, (0, -40), twi=0.85 - 0.55 * s)
    cam = Cam((0, 0, 0), (0, 0, -1))
    # Luna creciente (≈20 %): la luz viene de detrás y de abajo, del Sol ya oculto
    lt = unit([0.55, -0.7, -0.42])
    my = 0.10 - 0.16 * ease(s)
    C = np.array([0.04, my, -1.0]) * 30
    info = draw_body(img, cam, C, 1.25, t, MOONT, spin=0.0, tilt=0.0, light=lt, tint=(1.0, 0.97, 0.9), expo=1.5, amb=0.035)
    hills(img, hz, seed=11, amp=55, parallax=0.0)
    return cam, dict(info=info, hz=hz)


def sh_hora(img, t):
    a0, a1 = span("hora")
    s = (t - a0) / (a1 - a0)
    city = 1.0 - smooth(0.42, 0.75, s)
    rate = 0.18 + 0.7 * smooth(0.45, 0.85, s)
    drift = (-60 + 50 * s, 10 - 40 * s)
    rad = (W * 0.62, 470)
    sky_shot(img, t + 3.0, rad, rate, 1460, drift, city=1.6 * city, lights=1.2 * city, gem=1.3, seed=21, parallax=60 * s)
    return None, dict(rad=rad, drift=drift, city=city)


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    s = min(1.0, (t - a0) / (END - a0))
    drift = (-40 + 30 * s, 30 - 30 * s)
    sky_shot(img, t + 11.0, RAD0, 0.85, 1480, drift, parallax=-30 + 20 * s)
    return None, dict(drift=drift)


SCENES = dict(gancho=sh_gancho, origen=sh_origen, rastro=sh_rastro, cruce=sh_cruce, luna=sh_luna, hora=sh_hora, cierre=sh_cierre)


# ---------------- textos y gráficos ----------------
def counter(d, t, a, b, v0, v1, fmt, y, size, col, A):
    k = ease_out((t - a) / max(b - a, 1e-3))
    txt(d, (W / 2, y), fmt(v0 + (v1 - v0) * k), size, col, A, "Inter-Black.otf", 9)


def clock(d, x, y, r, hh, mm, A):
    d.ellipse([x - r, y - r, x + r, y + r], outline=WHITE + (A,), width=8)
    for i in range(12):
        a = i / 12 * 2 * math.pi
        d.line([(x + math.sin(a) * r * 0.82, y - math.cos(a) * r * 0.82), (x + math.sin(a) * r * 0.94, y - math.cos(a) * r * 0.94)], fill=WHITE + (A,), width=5)
    ah = (hh % 12 + mm / 60) / 12 * 2 * math.pi; am = mm / 60 * 2 * math.pi
    d.line([(x, y), (x + math.sin(ah) * r * 0.5, y - math.cos(ah) * r * 0.5)], fill=YELLOW + (A,), width=12)
    d.line([(x, y), (x + math.sin(am) * r * 0.78, y - math.cos(am) * r * 0.78)], fill=CYAN + (A,), width=7)
    d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=YELLOW + (A,))


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    if name == "gancho":
        cut = SPLIT("gancho", 0.62)
        draw_label(layer, t, -1, cut, "+100 POR HORA", ["estrellas fugaces · 13 de diciembre"], YELLOW, 124)
        draw_label(layer, t, cut, a1 + 0.3, "¿Y EL COMETA?", ["estas no vienen de uno"], WHITE, 118)
    elif name == "origen":
        tb, tc = SUB["origen_b"], SUB["origen_c"]
        if ex["mode"] == "sky":
            draw_label(layer, t, a0 + 0.1, tb, "GEMÍNIDAS", ["de las lluvias más intensas del año"], YELLOW, 132)
            A = int(255 * fade(t, a0 + 0.6, tb) * 0.9)
            rx, ry = ex["rad"]; dx, dy = ex["drift"]
            for (i, j) in GEM_L:
                p1 = (rx + GEM[i][0] - dx, ry + GEM[i][1] - dy); p2 = (rx + GEM[j][0] - dx, ry + GEM[j][1] - dy)
                d.line([p1, p2], fill=CYAN + (int(A * 0.55),), width=3)
            for (gx, gy, b, nm) in GEM:
                if nm:
                    txt(d, (rx + gx - dx + (-24 if gx < 0 else 24), ry + gy - dy - 34), nm, 34, WHITE, A, "Inter-ExtraBold.otf", 5, "rm" if gx < 0 else "lm")
        elif ex["mode"] == "comet":
            draw_label(layer, t, tb, tc, "CASI TODAS", ["nacen de cometas"], WHITE, 124)
            x, y = ex["c"]
            A = int(255 * fade(t, tb + 0.15, tc))
            txt(d, (x - 30, y + 90), "COMETA", 52, CYAN, A, "Inter-Black.otf", 7, "mm")
        else:
            draw_label(layer, t, tc, a1, "ASTEROIDE", ["3200 FAETÓN"], YELLOW, 132)
    elif name == "rastro":
        draw_label(layer, t, a0 + 0.1, SPLIT("rastro", 0.55), "MUY CERCA DEL SOL", ["en una órbita muy alargada"], WHITE, 112)
        draw_label(layer, t, SPLIT("rastro", 0.55), a1, "RASTRO DE POLVO", ["y roca, a lo largo de su órbita"], YELLOW, 118)
        A = int(255 * fade(t, a0 + 0.3, a1))
        ring_line(d, cam, lambda u: orbit_pt(u * 2 * np.pi - np.pi), 120, CYAN, int(A * 0.35), 3, dash=True)
        ring_line(d, cam, lambda u: AU * np.array([math.sin(u * 2 * np.pi), 0, math.cos(u * 2 * np.pi)]), 120, WHITE, int(A * 0.18), 2, dash=True)
        if ex["info"]:
            x, y, r = ex["info"]
            marker(d, x, y, t, CYAN, A, 34, "FAETÓN", 1 if x < W * 0.6 else -1, 46)
        sx, sy, _ = pt(cam, O3)
        txt(d, (sx, sy + 95), "SOL", 44, WHITE, int(A * 0.85), "Inter-Black.otf", 6)
    elif name == "cruce":
        tb = SUB["cruce_b"]
        if ex["mode"] == "orb":
            draw_label(layer, t, a0 + 0.1, tb, "CADA DICIEMBRE", ["la Tierra cruza el rastro"], WHITE, 118)
            A = int(255 * fade(t, a0 + 0.2, tb))
            ring_line(d, cam, lambda u: AU * np.array([math.sin(u * 2 * np.pi), 0, math.cos(u * 2 * np.pi)]), 140, WHITE, int(A * 0.3), 2, dash=True)
            x, y, _ = pt(cam, ex["Pe"])
            marker(d, x, y, t, YELLOW, A, 38, "TIERRA", -1, 46)
        else:
            draw_label(layer, t, tb, a1, "¡SE ENCIENDEN!", [], YELLOW, 128)
            A = int(255 * fade(t, tb + 0.2, a1))
            counter(d, t, tb + 0.2, tb + 1.4, 0, 35, lambda v: f"{int(round(v))} KM/S", 610, 112, WHITE, A)
            txt(d, (W / 2, 690), "≈ 126,000 km/h", 50, CYAN, int(A * fade(t, tb + 1.4, a1 + 1)), "Inter-ExtraBold.otf", 6)
    elif name == "luna":
        draw_label(layer, t, a0 + 0.1, SPLIT("luna", 0.5), "LUNA AL 20 %", ["casi no estorba"], WHITE, 124)
        draw_label(layer, t, SPLIT("luna", 0.5), a1, "SE METE TEMPRANO", ["hacia las 9 de la noche"], CYAN, 112)
        if ex["info"]:
            x, y, r = ex["info"]
            A = int(255 * fade(t, a0 + 0.4, a1) * 0.9)
            txt(d, (x, y + r + 50), "LUNA", 44, WHITE, A, "Inter-Black.otf", 6)
    elif name == "hora":
        cut = SPLIT("hora", 0.45)
        draw_label(layer, t, a0 + 0.1, cut, "13 → 14 DIC", ["madrugada del lunes 14"], YELLOW, 128)
        draw_label(layer, t, cut, a1, "LEJOS DE LA CIUDAD", ["cielo oscuro = muchas más"], WHITE, 108)
        A = int(255 * fade(t, a0 + 0.3, a1))
        k = ease_out((t - a0 - 0.3) / 1.4)
        hh = 22 + 4 * k; mm = (hh % 1) * 60
        clock(d, W / 2, 690, 105, int(hh) % 24, int(mm), A)
        txt(d, (W / 2, 845), "2:00 A. M." if k > 0.98 else f"{int(hh) % 12 or 12}:{int(mm):02d}", 66, WHITE, A, "Inter-Black.otf", 8)
        if ex["city"] > 0.3:
            Ac = int(255 * fade(t, cut, a1) * min(1, (ex["city"] - 0.3) / 0.3))
            txt(d, (W * 0.2, 1225), "CIUDAD", 44, ORANGE, Ac, "Inter-Black.otf", 6)
    elif name == "cierre":
        cut = SPLIT("cierre", 0.45)
        draw_label(layer, t, a0 + 0.1, cut, "CADA LUZ…", ["que cruce el cielo"], WHITE, 124)
        draw_label(layer, t, cut, CARD, "UN PEDACITO", ["de asteroide encendiéndose"], YELLOW, 124)
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
