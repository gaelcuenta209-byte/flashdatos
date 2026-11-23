"""Flash Datos · video 41: una estrella gigante se tragó a su compañera en Andrómeda (AT 2025abao, "Bao").

Escena nueva: supergigante roja con granulación y una compañera amarilla que cae en espiral (contador de
vueltas 1→7, chorro de gas), Andrómeda hecha de partículas con zoom a la estrella, el Sol a escala como un
puntito, erupción con cascarón de gas, vista infrarroja estilo Webb con el espejo hexagonal, capas de polvo
de siglos con la espiral reconstruida y la estrella única final.


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
#  VIDEO 41 · Big Bao se traga a Little Bao (Andrómeda) · escena nueva
# =====================================================================

def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


BET_N = np.clip((BET - 0.34) / 0.56, 0, 1).astype(np.float32)
BIG_HOT = np.array([1.7, 0.58, 0.14]); BIG_COOL = np.array([0.55, 0.10, 0.02])
SML_HOT = np.array([3.2, 2.7, 1.7]); SML_COOL = np.array([2.0, 1.4, 0.6])


def draw_star(img, cam, C, r, t, hot, cool, expo=1.0, spin=0.0, halo=1.0, halo_col=None, tex_scale=1.0):
    """Estrella emisiva con granulación (textura de supergigante), oscurecimiento al limbo y halo."""
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
        loc = rot_y(n, spin)
        la, lo = latlon(loc)
        g = sample(BET_N, la * tex_scale, lo * tex_scale)
        g = 0.5 + (g - 0.5) * (0.8 + 0.2 * math.sin(t * 1.3))
        col = cool[None, :] * (1 - g[:, None]) + hot[None, :] * g[:, None]
        limb = (0.28 + 0.72 * mu ** 0.55)[:, None]
        col = col * limb * expo
        a = alpha[sel][:, None]
        region[sel] = region[sel] * (1 - a) + col * a
    return (cx, cy, rpx)


# ---------------- órbita de Little Bao ----------------
U1 = np.array([1.0, 0.0, 0.0])
U2 = unit([0.0, 0.24, -1.0])
R_BIG, R_SML = 1.0, 0.15


def orb(a, phi):
    return a * (math.cos(phi) * U1 + math.sin(phi) * U2)


def draw_pair(img, cam, t, Pl, expo_big=1.0, show_small=True, spin=0.0):
    """Dibuja las dos estrellas en el orden correcto de profundidad."""
    zb = (np.zeros(3) - cam.O) @ cam.f
    zs = (Pl - cam.O) @ cam.f
    infos = {}
    order = [("s", zs), ("b", zb)] if show_small else [("b", zb)]
    order.sort(key=lambda q: -q[1])
    for k, _ in order:
        if k == "b":
            infos["b"] = draw_star(img, cam, np.zeros(3), R_BIG, t, BIG_HOT, BIG_COOL, expo_big, spin=0.05 * t + spin)
        else:
            infos["s"] = draw_star(img, cam, Pl, R_SML, t, SML_HOT, SML_COOL, 1.0, spin=0.4 * t, halo=1.6, halo_col=np.array([1.4, 1.1, 0.6]), tex_scale=1.0)
    return infos


RNG = np.random.default_rng(41)
STREAM_U = RNG.random(700); STREAM_J = RNG.standard_normal((700, 3))


def gas_stream(img, cam, Pl, phi, a, amt=1.0):
    """Chorro de gas de la gigante hacia la compañera y estela detrás de ella."""
    if amt <= 0:
        return
    # puente de gas: de la superficie de la gigante a la compañera, curvado hacia atrás en la órbita
    u = STREAM_U
    ang = phi - 0.55 * u * (1 - u) * 2.2
    rad = R_BIG * 0.98 + (a - R_BIG * 0.98) * u
    P = rad[:, None] * (np.cos(ang)[:, None] * U1 + np.sin(ang)[:, None] * U2) + STREAM_J * (0.05 + 0.10 * u * (1 - u))[:, None]
    col = np.stack([2.0 - 0.6 * u, 0.75 + 0.25 * u, 0.18 + 0.2 * u], -1) * 0.035 * amt
    splat(img, cam, P, col.astype(np.float32))
    # estela de la compañera
    k = np.arange(1, 160)
    ang2 = phi - k * 0.012
    P2 = (a + 0.002 * k)[:, None] * (np.cos(ang2)[:, None] * U1 + np.sin(ang2)[:, None] * U2) + RNG.standard_normal((len(k), 3)) * 0.015
    col2 = np.stack([np.full(len(k), 1.8), np.full(len(k), 1.1), np.full(len(k), 0.5)], -1) * (0.05 * np.exp(-k / 60.0) * amt)[:, None]
    splat(img, cam, P2, col2.astype(np.float32))


def orbit_ring(d, cam, a, col, A, width=3, dash=3):
    phis = np.linspace(0, 2 * np.pi, 181)
    P = np.array([orb(a, p) for p in phis])
    x, y, vis = vis_mask(cam, P, np.zeros(3), R_BIG)
    for j in range(len(P) - 1):
        if dash and (j // dash) % 2 == 1:
            continue
        if vis[j] and vis[j + 1]:
            d.line([(x[j], y[j]), (x[j + 1], y[j + 1])], fill=col + (A,), width=width)


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


# ---------------- Andrómeda de partículas ----------------
def make_galaxy():
    rng = np.random.default_rng(31)
    n_arm, n_disk, n_bulge = 26000, 16000, 9000
    r = rng.exponential(1.15, n_arm) + 0.25
    arm = rng.integers(0, 2, n_arm)
    th = arm * math.pi + np.log(r) / math.tan(math.radians(17)) + rng.normal(0, 0.22, n_arm)
    ra = np.stack([r * np.cos(th), rng.normal(0, 0.035, n_arm), r * np.sin(th)], -1)
    ca = np.where((rng.random(n_arm) < 0.12)[:, None], np.array([1.0, 0.45, 0.65]), np.array([0.62, 0.75, 1.0]))
    rd = rng.exponential(1.4, n_disk) + 0.1
    td = rng.random(n_disk) * 2 * math.pi
    dk = np.stack([rd * np.cos(td), rng.normal(0, 0.05, n_disk), rd * np.sin(td)], -1)
    cd = np.tile(np.array([0.85, 0.82, 0.78]), (n_disk, 1))
    bg_ = rng.normal(0, 1, (n_bulge, 3)) * np.array([0.42, 0.28, 0.42]) * rng.exponential(1.0, (n_bulge, 1)) ** 0.7
    cb = np.tile(np.array([1.0, 0.82, 0.55]), (n_bulge, 1))
    P = np.concatenate([ra, dk, bg_]); Cc = np.concatenate([ca * 0.7, cd * 0.45, cb * 0.9])
    ok = np.linalg.norm(P, axis=-1) < 5.2
    P, Cc = P[ok], Cc[ok]
    # inclinación de ~77° y ángulo de posición en pantalla
    P = rot_x(P, math.radians(-77 + 90) * -1 + 0)
    c, s = math.cos(math.radians(38)), math.sin(math.radians(38))
    P = np.stack([P[:, 0] * c - P[:, 1] * s, P[:, 0] * s + P[:, 1] * c, P[:, 2]], -1)
    return P, Cc.astype(np.float32)


GAL_P, GAL_C = make_galaxy()
BAO_IN_GAL = None


def bao_spot():
    # un punto en un brazo, al suroeste del núcleo (posición ilustrativa)
    global BAO_IN_GAL
    if BAO_IN_GAL is None:
        d2 = np.linalg.norm(GAL_P - np.array([-1.05, -0.75, 0.0]), axis=-1)
        BAO_IN_GAL = GAL_P[int(np.argmin(d2))]
    return BAO_IN_GAL


# ---------------- tomas ----------------
FIRST = ["gancho", "andromeda", "compania", "orbitas", "webb", "polvo", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.22) for i, k in enumerate(FIRST)]
GAL_CUT = S0["andromeda"] + 1.75          # de la galaxia a la estrella
FL = [b for _, b in SHOTS[1:]] + [GAL_CUT, CARD - 0.05]
PLUNGE = 4.0                               # en el gancho, la compañera desaparece


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
    cam = Cam((0.6 - 1.0 * s, 1.6 - 0.4 * s, 10.6 - 1.4 * ease_out(s)), (0, 0.1, 0), roll=0.18)
    u = min(1.0, t / PLUNGE)
    phi = 0.8 + 2 * math.pi * 1.7 * u ** 1.35
    a = 1.75 - (1.75 - 0.9) * u ** 1.6
    Pl = orb(a, phi)
    burst = 0.0 if t < PLUNGE else math.exp(-(t - PLUNGE) / 0.9)
    expo = 1.0 + 1.6 * burst
    if t < PLUNGE:
        gas_stream(img, cam, Pl, phi, a, 0.6 + 0.8 * u)
    info = draw_pair(img, cam, t, Pl, expo, show_small=t < PLUNGE - 0.05)
    if t >= PLUNGE:
        ring_burst(img, cam, t - PLUNGE, orb(R_BIG, phi), 1.0)
    return cam, dict(info=info, Pl=Pl, phi=phi)


def ring_burst(img, cam, dt, P0, amt):
    """Destello en el punto de impacto: anillo de chispas que se expande."""
    if dt < 0 or dt > 2.5:
        return
    n = 500
    rng = np.random.default_rng(7)
    dirs = rng.standard_normal((n, 3)); dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
    nP = unit(P0)
    dirs = dirs + nP * 1.2; dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
    v = 0.6 + 0.8 * rng.random(n)
    P = P0[None, :] + dirs * (v * (1 - math.exp(-dt / 0.6)) * 1.3)[:, None]
    f = math.exp(-dt / 0.7) * amt
    col = np.tile(np.array([3.0, 2.0, 0.9], np.float32), (n, 1)) * 0.12 * f
    splat(img, cam, P, col)


def sh_andromeda(img, t):
    a0, a1 = span("andromeda")
    if t < GAL_CUT:
        s = (t - a0) / (GAL_CUT - a0)
        tgt = bao_spot() * ease(s) * 0.85
        cam = Cam((tgt[0] * 0.4, tgt[1] * 0.4, 11.5 - 4.5 * ease(s)), tgt, roll=0.0)
        splat(img, cam, GAL_P, GAL_C * 0.55)
        # resplandor del núcleo
        x, y, z = pt(cam, np.zeros(3))
        yy, xx = np.mgrid[0:H:4, 0:W:4]
        dd = np.sqrt((xx - x) ** 2 + ((yy - y) * 1.0) ** 2)
        img += ndzoom((np.exp(-dd / 70) * 0.9)[..., None].astype(np.float32) * np.array([1.0, 0.8, 0.55], np.float32), (4, 4, 1), order=1)[:H, :W]
        return cam, dict(gal=True, spot=bao_spot())
    s = (t - GAL_CUT) / (a1 - GAL_CUT)
    cam = Cam((-0.7 + 0.4 * s, 0.25, 5.4 - 0.4 * s), (-0.35, -0.25, 0))
    info = draw_star(img, cam, np.zeros(3), R_BIG, t, BIG_HOT, BIG_COOL, 1.0, spin=0.05 * t)
    sun = np.array([-0.8, -1.0, 1.9])
    splat(img, cam, sun[None, :], np.array([[6.0, 5.2, 3.2]], np.float32))
    return cam, dict(gal=False, info=info, sun=sun)


def sh_compania(img, t):
    a0, a1 = span("compania")
    s = (t - a0) / (a1 - a0)
    cam = Cam((1.0 - 1.4 * s, 2.6 - 0.4 * s, 11.6 - 0.8 * s), (0, -0.1, 0))
    a = 1.95 - 0.15 * s
    phi = 1.9 + 2 * math.pi * (t - a0) / 4.6
    Pl = orb(a, phi)
    gas_stream(img, cam, Pl, phi, a, 0.45 + 0.35 * s)
    info = draw_pair(img, cam, t, Pl)
    return cam, dict(info=info, Pl=Pl, a=a)


ORB_A0, ORB_A1 = 1.8, 1.0


def orbit_state(t):
    a0, a1 = span("orbitas")
    t_end = S1["orbitas"] - 3.2          # termina de caer antes de "Otras fusiones…"
    u = min(1.0, max(0.0, (t - (a0 + 0.15)) / (t_end - a0 - 0.15)))
    phi0 = 1.9 + 2 * math.pi * (a0 - S0["compania"] + 0.22) / 4.6
    phi = phi0 + 2 * math.pi * 7 * u ** 1.3
    a = ORB_A0 - (ORB_A0 - ORB_A1) * u ** 1.5
    revs = 7 * u ** 1.3
    return phi, a, revs, u, t_end


def sh_orbitas(img, t):
    a0, a1 = span("orbitas")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.0, 6.4 - 1.0 * s, 8.4 - 0.6 * s), (0, -0.3, 0))
    phi, a, revs, u, t_end = orbit_state(t)
    Pl = orb(a, phi)
    merged = t > t_end
    if not merged:
        gas_stream(img, cam, Pl, phi, a, 0.6 + 0.7 * u)
        # rastro de la espiral ya recorrida
        k = np.linspace(0, u, 900)
        ph_ = 1.9 + 2 * math.pi * (a0 - S0["compania"] + 0.22) / 4.6 + 2 * math.pi * 7 * k ** 1.3
        aa = ORB_A0 - (ORB_A0 - ORB_A1) * k ** 1.5
        P = aa[:, None] * (np.cos(ph_)[:, None] * U1 + np.sin(ph_)[:, None] * U2)
        w = np.exp(-(u - k) * 4.0)[:, None]
        splat(img, cam, P, (np.array([0.35, 0.75, 1.0], np.float32) * 0.05 * w).astype(np.float32))
    burst = math.exp(-(t - t_end) / 1.1) if merged else 0.0
    info = draw_pair(img, cam, t, Pl, 1.0 + 1.3 * burst, show_small=not merged)
    if merged:
        ring_burst(img, cam, t - t_end, orb(R_BIG, phi), 1.0)
    return cam, dict(info=info, revs=revs, merged=merged, t_end=t_end)


RNG_EJ = np.random.default_rng(29)
EJ_D = RNG_EJ.standard_normal((2600, 3)); EJ_D /= np.linalg.norm(EJ_D, axis=-1, keepdims=True)
EJ_V = 0.5 + RNG_EJ.random(2600) ** 2 * 1.4
DUST_R = np.concatenate([np.full(1400, r) for r in (1.6, 2.1, 2.7, 3.3, 4.0)]) * (1 + RNG_EJ.normal(0, 0.06, 7000))
DUST_D = RNG_EJ.standard_normal((7000, 3)); DUST_D /= np.linalg.norm(DUST_D, axis=-1, keepdims=True)
DUST_D[:, 1] *= 0.55                     # más polvo cerca del plano de la órbita
DUST_D /= np.linalg.norm(DUST_D, axis=-1, keepdims=True)
DUST_B = (0.4 + RNG_EJ.random(7000)) * np.repeat(np.array([1.0, 0.85, 0.7, 0.55, 0.42]), 1400)


def ir_view(img, k):
    """Mezcla hacia una paleta infrarroja (falso color tipo Webb)."""
    if k <= 0:
        return
    lum = img[..., 0] * 0.5 + img[..., 1] * 0.35 + img[..., 2] * 0.15
    ir = np.stack([lum * 1.25, lum * 0.62, lum * 0.22 + lum ** 2 * 0.05], -1)
    img[:] = img * (1 - k) + ir * k


def webb_k(t):
    return smooth(S0["webb"] + 3.3, S0["webb"] + 4.4, t)


def sh_webb(img, t):
    a0, a1 = span("webb")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.5 - 1.0 * s, 0.9, 9.5 + 3.0 * ease_out(s)), (0, -0.1, 0))
    te = t - (S0["webb"] + 1.4)             # "estalló en brillo"
    flare = 0.0 if te < 0 else (1 - math.exp(-te / 0.25)) * math.exp(-te / 2.6)
    expo = 1.0 + 2.2 * flare
    if te > 0:
        r = R_BIG + EJ_V * (1 - math.exp(-te / 2.2)) * 2.4
        P = EJ_D * r[:, None]
        heat = math.exp(-te / 1.6)
        col = np.stack([np.full(len(r), 2.4), np.full(len(r), 1.0 + 1.0 * heat), np.full(len(r), 0.3 + 0.8 * heat)], -1)
        splat(img, cam, P, (col * 0.09 * (0.4 + 0.6 * math.exp(-te / 4))).astype(np.float32))
    info = draw_star(img, cam, np.zeros(3), R_BIG * 1.08, t, BIG_HOT * 1.05, BIG_COOL, expo, spin=0.05 * t, halo=1.0 + 1.5 * flare)
    ir_view(img, webb_k(t))
    return cam, dict(info=info, flare=flare)


def sh_polvo(img, t):
    a0, a1 = span("polvo")
    s = (t - a0) / (a1 - a0)
    ang = -0.5 + 0.6 * s
    R = 13.5 - 1.5 * s
    cam = Cam((R * math.sin(ang), 2.4, R * math.cos(ang)), (0, 0, 0))
    rr = DUST_R * (1 + 0.03 * s)
    P = DUST_D * rr[:, None]
    col = np.stack([DUST_B * 1.6, DUST_B * 0.75, DUST_B * 0.28], -1) * 0.16
    splat(img, cam, P, col.astype(np.float32))
    info = draw_star(img, cam, np.zeros(3), R_BIG * 1.1, t, BIG_HOT, BIG_COOL, 0.9, spin=0.05 * t)
    ir_view(img, 1.0)
    return cam, dict(info=info)


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    s = (t - a0) / (END - a0)
    cam = Cam((-0.6 + 1.2 * s, 0.7, 7.0 + 2.6 * ease_out(s)), (0, 0.05, 0))
    rr = DUST_R * 1.25
    P = DUST_D * rr[:, None]
    col = np.stack([DUST_B * 1.2, DUST_B * 0.5, DUST_B * 0.2], -1) * 0.05
    splat(img, cam, P, col.astype(np.float32))
    pulse = 1.0 + 0.06 * math.sin(t * 2.2)
    info = draw_star(img, cam, np.zeros(3), R_BIG * 1.15 * pulse, t, BIG_HOT * 1.15, BIG_COOL * 1.1, 1.1, spin=0.05 * t, halo=1.3)
    return cam, dict(info=info)


SCENES = dict(gancho=sh_gancho, andromeda=sh_andromeda, compania=sh_compania, orbitas=sh_orbitas,
              webb=sh_webb, polvo=sh_polvo, cierre=sh_cierre)


# ---------------- textos y gráficos ----------------
def calendar(layer, t, a, b, xy, size, top="OCTUBRE", big="2025"):
    al = fade(t, a, b, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    k = ease_out((t - a) / 0.45)
    w_ = h_ = size * (0.8 + 0.2 * k)
    d = ImageDraw.Draw(layer)
    x0, y1 = xy[0] - w_ / 2, xy[1] - h_ / 2
    d.rounded_rectangle([x0, y1, x0 + w_, y1 + h_], 28, fill=(245, 247, 252, A))
    d.rounded_rectangle([x0, y1, x0 + w_, y1 + h_ * 0.28], 28, fill=(220, 80, 50, A))
    d.rectangle([x0, y1 + h_ * 0.16, x0 + w_, y1 + h_ * 0.28], fill=(220, 80, 50, A))
    d.text((xy[0], y1 + h_ * 0.14), top, font=font("Inter-Black.otf", int(40 * w_ / 300)), fill=(255, 255, 255, A), anchor="mm")
    d.text((xy[0], y1 + h_ * 0.64), big, font=font("Inter-Black.otf", int(120 * w_ / 300)), fill=(20, 24, 36, A), anchor="mm")


def webb_mirror(layer, cx, cy, s, A, k=1.0):
    """Espejo segmentado (18 hexágonos dorados) y espejo secundario, dibujo propio."""
    d = ImageDraw.Draw(layer)
    hexes = []
    for q in range(-2, 3):
        for r_ in range(-2, 3):
            if abs(q + r_) <= 2 and not (q == 0 and r_ == 0):
                hexes.append((q, r_))
    hexes.sort(key=lambda h: (abs(h[0]) + abs(h[1]) + abs(h[0] + h[1])) / 2)
    nshow = int(round(len(hexes) * k))
    for i, (q, r_) in enumerate(hexes[:nshow]):
        x = cx + s * 1.5 * q
        y = cy + s * math.sqrt(3) * (r_ + q / 2)
        pts = [(x + s * 0.95 * math.cos(math.radians(60 * j)), y + s * 0.95 * math.sin(math.radians(60 * j))) for j in range(6)]
        shade = 0.82 + 0.18 * math.sin(i * 1.7)
        d.polygon(pts, fill=(int(235 * shade), int(185 * shade), int(70 * shade), A), outline=(255, 235, 160, A))
    if k > 0.95:
        top = cy - s * 4.4
        for sx in (-1, 1):
            d.line([(cx + sx * s * 2.6, cy - s * 1.8), (cx, top)], fill=(200, 200, 210, A), width=4)
        d.line([(cx, cy + s * 2.6), (cx, top)], fill=(200, 200, 210, A), width=4)
        d.ellipse([cx - s * 0.35, top - s * 0.35, cx + s * 0.35, top + s * 0.35], fill=(230, 230, 235, A))


def counter(layer, t, revs, A):
    d = ImageDraw.Draw(layer)
    n = min(7, int(revs) + 1)
    txt(d, (W / 2, 450), f"VUELTA {n}", 120, YELLOW, A)
    # 7 puntitos de progreso
    for i in range(7):
        x = W / 2 + (i - 3) * 78; y = 560
        fill = YELLOW if i < n else (70, 80, 100)
        d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=fill + (A,), outline=(8, 10, 20, A), width=4)


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    if name == "gancho":
        draw_label(layer, t, -1, PLUNGE - 0.2, "ESTRELLA", ["devora estrella"], YELLOW, 150)
        info = ex["info"]
        if t < PLUNGE - 0.3 and info.get("s"):
            As = int(255 * fade(t, 0.3, PLUNGE - 0.3))
            x, y, r = info["s"]
            marker(d, x, y, t, CYAN, As, 34)
        Ar = int(255 * fade(t, PLUNGE + 0.2, a1 + 0.3))
        if Ar > 0:
            draw_label(layer, t, PLUNGE + 0.2, a1 + 0.3, "CASI EN VIVO", ["en la galaxia vecina"], RED, 120)
            if int(t * 2.5) % 2 == 0:
                d.ellipse([W / 2 - 330, 340, W / 2 - 290, 380], fill=RED + (Ar,))
    elif name == "andromeda":
        if ex["gal"]:
            draw_label(layer, t, a0 + 0.1, GAL_CUT, "ANDRÓMEDA", ["la galaxia grande más cercana"], CYAN, 130)
            x, y, _ = pt(cam, ex["spot"])
            Am = int(255 * fade(t, a0 + 0.6, GAL_CUT + 0.2))
            marker(d, x, y, t, YELLOW, Am, 30 + 20 * smooth(GAL_CUT - 0.6, GAL_CUT, t), "AQUÍ", 1, 52)
        else:
            draw_label(layer, t, GAL_CUT, a1, "BIG BAO", ["7 veces la masa del Sol"], (255, 140, 70), 140)
            x, y, _ = pt(cam, ex["sun"])
            As = int(255 * fade(t, GAL_CUT + 1.0, a1))
            marker(d, x, y, t, YELLOW, As, 26, "EL SOL", 1, 48)
            txt(d, (x + 70, y + 60), "(a escala)", 38, WHITE, int(As * 0.9), "Inter-ExtraBold.otf", 6, "lm")
            Ar = int(255 * fade(t, GAL_CUT + 1.8, a1))
            txt(d, (W / 2, 1150), "350 VECES EL RADIO DEL SOL", 58, CYAN, Ar, "Inter-Black.otf", 8)
    elif name == "compania":
        info = ex["info"]
        A = int(255 * fade(t, a0 + 0.2, a1))
        orbit_ring(d, cam, ex["a"], CYAN, int(A * 0.4), 3, 3)
        if info.get("s"):
            x, y, r = info["s"]
            marker(d, x, y, t, CYAN, A, 34)
            side = 1 if x < W * 0.6 else -1
            txt(d, (x + side * 60, y - 20), "LITTLE BAO", 50, WHITE, A, "Inter-Black.otf", 7, "lm" if side > 0 else "rm")
            txt(d, (x + side * 60, y + 35), "0.7 masas solares", 40, CYAN, A, "Inter-ExtraBold.otf", 6, "lm" if side > 0 else "rm")
        draw_label(layer, t, a0 + 0.1, a1, "LITTLE BAO", ["10 veces menos masa"], CYAN, 120)
    elif name == "orbitas":
        revs, merged = ex["revs"], ex["merged"]
        A = int(255 * fade(t, a0 + 0.1, ex["t_end"] + 0.6))
        if A > 0:
            counter(layer, t, revs, A)
            txt(d, (W / 2, 650), "≈ 7 AÑOS", 64, CYAN, A, "Inter-Black.otf", 8)
        Am = int(255 * fade(t, ex["t_end"] + 0.4, a1))
        if Am > 0:
            txt(d, (W / 2, 420), "7 VUELTAS", 130, YELLOW, Am)
            txt(d, (W / 2, 560), "vs.", 60, WHITE, Am, "Inter-ExtraBold.otf", 7)
            txt(d, (W / 2, 690), "MILES", 130, CYAN, Am)
            txt(d, (W / 2, 790), "en otras fusiones", 52, CYAN, Am, "Inter-ExtraBold.otf", 7)
    elif name == "webb":
        calendar(layer, t, a0 + 0.1, S0["webb"] + 3.3, (W / 2, 470), 280)
        kw = webb_k(t)
        if kw > 0:
            Aw = int(255 * fade(t, S0["webb"] + 3.3, a1))
            webb_mirror(layer, W / 2, 480, 46, Aw, ease_out((t - S0["webb"] - 3.3) / 0.9))
            txt(d, (W / 2, 740), "JAMES WEBB", 96, YELLOW, Aw)
            txt(d, (W / 2, 830), "infrarrojo medio", 52, CYAN, Aw, "Inter-ExtraBold.otf", 7)
    elif name == "polvo":
        info = ex["info"]
        draw_label(layer, t, a0 + 0.1, S0["polvo"] + 2.9, "POLVO", ["soltado durante siglos"], (255, 170, 90), 150)
        Ar = int(255 * fade(t, S0["polvo"] + 2.6, a1))
        if Ar > 0:
            k = ease((t - S0["polvo"] - 2.6) / 2.0)
            kk = np.linspace(0, k, 400)
            ph = 2 * math.pi * 7 * kk ** 1.3
            aa = ORB_A0 - (ORB_A0 - ORB_A1) * kk ** 1.5
            P = aa[:, None] * (np.cos(ph)[:, None] * U1 + np.sin(ph)[:, None] * U2)
            x, y, vis = vis_mask(cam, P, np.zeros(3), R_BIG * 1.1)
            for j in range(len(P) - 1):
                if vis[j] and vis[j + 1]:
                    d.line([(x[j], y[j]), (x[j + 1], y[j + 1])], fill=CYAN + (Ar,), width=5)
            draw_label(layer, t, S0["polvo"] + 2.6, a1, "LA PISTA", ["para reconstruir el choque"], CYAN, 130)
    elif name == "cierre":
        draw_label(layer, t, a0 + 0.1, S0["cierre"] + 2.9, "2 → 1", ["dos estrellas, ahora una sola"], YELLOW, 170)
        draw_label(layer, t, S0["cierre"] + 2.9, CARD, "PRIMERA VEZ", ["una fusión casi en tiempo real"], CYAN, 130)
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
