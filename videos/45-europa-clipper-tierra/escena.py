"""Flash Datos · video 45: Europa Clipper pasa rozando la Tierra rumbo a Júpiter (3 dic 2026).

Escena nueva: la nave Europa Clipper (cuerpo dorado, dos alas de paneles solares y antena) llega en
curva hacia la Tierra y pasa por dentro del anillo de los satélites GPS; primer plano de la nave con
Júpiter a lo lejos; vista desde arriba de la «resortera»: trayectoria hiperbólica que se dobla
alrededor de la Tierra con la regla de 3,200 km y flechas de velocidad; mapa del viaje
Tierra → Marte (2025) → Tierra (2026) → Júpiter (2030); Júpiter con Europa y corte de Europa
con la capa de hielo y el océano debajo; cierre con la nave pasando otra vez junto a la Tierra.

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
#  VIDEO 45 · Europa Clipper pasa rozando la Tierra rumbo a Júpiter
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


# ---------------- texturas nuevas: Marte y Europa ----------------
def _sphere_grid(th=256, tw=512):
    la = (0.5 - (np.arange(th) + 0.5) / th) * np.pi
    lo = (np.arange(tw) + 0.5) / tw * 2 * np.pi - np.pi
    LO, LA = np.meshgrid(lo, la)
    return np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO), LA


def _mars_tex():
    x, y, z, LA = _sphere_grid()
    n1 = fbm(x * 2.5 + 1, y * 2.5, z * 2.5, 5, seed=31)
    n2 = fbm(x * 9, y * 9 + 3, z * 9, 3, seed=37)
    dark = np.clip((n1 - 0.48) * 4, 0, 1)
    base = np.stack([0.78 - 0.30 * dark, 0.36 - 0.16 * dark, 0.18 - 0.08 * dark], -1)
    base *= (0.85 + 0.3 * n2)[..., None]
    cap = smooth(1.25, 1.42, np.abs(LA))[..., None]
    base = base * (1 - cap) + np.array([0.92, 0.9, 0.88]) * cap
    return np.clip(base, 0, 1).astype(np.float32) ** 2.2


def _europa_tex():
    x, y, z, LA = _sphere_grid(512, 1024)
    base = fbm(x * 3 + 7, y * 3, z * 3, 5, seed=51)
    col = np.stack([0.86 + 0.10 * base, 0.80 + 0.08 * base, 0.72 + 0.06 * base], -1)
    # «lineae»: grietas largas color óxido
    lines = np.zeros_like(base)
    for i, (f, s) in enumerate(((2.2, 61), (3.4, 67), (5.5, 71), (8.0, 73))):
        n = fbm(x * f, y * f + i, z * f, 3, seed=s)
        lines = np.maximum(lines, np.clip(1 - np.abs(n - 0.5) * (60 / (1 + i * 0.5)), 0, 1) * (1.0 - 0.18 * i))
    rust = np.array([0.55, 0.30, 0.16])
    col = col * (1 - 0.75 * lines[..., None]) + rust * 0.75 * lines[..., None]
    chaos = np.clip((fbm(x * 6, y * 6, z * 6 + 2, 4, seed=81) - 0.6) * 5, 0, 1)
    col = col * (1 - 0.35 * chaos[..., None]) + np.array([0.62, 0.45, 0.32]) * 0.35 * chaos[..., None]
    return np.clip(col, 0, 1).astype(np.float32) ** 2.2


MARS = _mars_tex()
EUROPA = _europa_tex()
JUPL = np.clip(JUP, 0, 1).astype(np.float32) ** 2.2 if JUP.ndim == 3 else JUP

# ---------------- la nave: Europa Clipper (polígonos 3D) ----------------
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


def _ship_parts():
    parts = []
    gold = (0.95, 0.70, 0.28); silver = (0.75, 0.76, 0.80); panel = (0.10, 0.17, 0.48); white = (0.92, 0.92, 0.95)
    for q in _box(-1.3, 1.3, -1.3, 1.3, -3.0, 3.0):
        parts.append((q, gold, "solid"))
    for q in _box(-0.8, 0.8, -0.8, 0.8, -4.2, -3.0):
        parts.append((q, silver, "solid"))
    # alas: 5 paneles por lado, unos 30 m de punta a punta
    for side in (-1, 1):
        x = 1.6
        for k in range(5):
            xa, xb = x, x + 2.6
            q = [np.array([side * xa, 0, -2.0]), np.array([side * xb, 0, -2.0]), np.array([side * xb, 0, 2.0]), np.array([side * xa, 0, 2.0])]
            if side < 0:
                q = q[::-1]
            parts.append((q, panel, "panel"))
            x = xb + 0.18
        b = [np.array([side * 1.3, -0.08, -0.15]), np.array([side * 1.62, -0.08, -0.15]), np.array([side * 1.62, -0.08, 0.15]), np.array([side * 1.3, -0.08, 0.15])]
        parts.append((b if side > 0 else b[::-1], silver, "panel"))
    # antena de alta ganancia arriba del cuerpo
    ring = [np.array([1.6 * math.cos(a), 1.9, 1.6 * math.sin(a)]) for a in np.linspace(0, 2 * np.pi, 20, endpoint=False)]
    parts.append((ring, white, "dish"))
    for q in _box(-0.25, 0.25, 1.3, 1.9, -0.25, 0.25):
        parts.append((q, silver, "solid"))
    # magnetómetro: brazo largo hacia atrás
    parts.append(([np.array([-0.06, 1.0, -3.0]), np.array([0.06, 1.0, -3.0]), np.array([0.06, 1.0, -9.5]), np.array([-0.06, 1.0, -9.5])], silver, "panel"))
    return parts


SHIP = _ship_parts()


def ship_frame(fwd, up=(0, 1, 0)):
    f = unit(fwd)
    r = np.cross(np.asarray(up, float), f)
    if np.linalg.norm(r) < 1e-6:
        r = np.array([1.0, 0, 0])
    r = unit(r); u = np.cross(f, r)
    return np.stack([r, u, f], 1)          # columnas: x local→r, y→u, z→f


def draw_ship(img, cam, P, Rm, scale, light=LIGHT, expo=1.0):
    """Dibuja la nave con polígonos (pintor) en una capa 2x y la mezcla en la imagen HDR."""
    P = np.asarray(P, float)
    cx, cy, cz = pt(cam, P)
    if cz <= 0.05:
        return None
    polys = []
    for q, col, kind in SHIP:
        V = np.array([P + Rm @ (v * scale) for v in q])
        x, y, z = cam.proj(V)
        if np.any(z <= 0.01):
            continue
        n = np.cross(V[1] - V[0], V[2] - V[0])
        if np.linalg.norm(n) < 1e-12:
            continue
        n = unit(n)
        view = unit(cam.O - V.mean(0))
        facing = n @ view
        if kind == "solid" and facing <= 0:
            continue
        nn = n if facing > 0 else -n
        lam = max(float(nn @ light), 0.0)
        c = np.array(col)
        if kind == "panel":
            if facing <= 0 and n[1] * 0 == 0 and col[2] > 0.4:
                c = np.array([0.35, 0.36, 0.40])
            refl = max(float((2 * (nn @ light) * nn - light) @ view), 0) ** 30
            shade = 0.18 + 0.9 * lam + 0.6 * refl
        elif kind == "dish":
            shade = 0.25 + 0.85 * lam
        else:
            shade = 0.12 + 1.0 * lam
        rgb = np.clip(c * shade * expo, 0, 1)
        polys.append((float(z.mean()), list(zip(x * 2, y * 2)), tuple(int(255 * v ** (1 / 1.0)) for v in rgb), kind))
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
        if kind == "panel" and rgb[2] > rgb[0] + 20 and len(pts2) == 4:
            # cuadrícula de celdas solares
            for k in range(1, 4):
                f = k / 4
                a = (pts2[0][0] + (pts2[1][0] - pts2[0][0]) * f, pts2[0][1] + (pts2[1][1] - pts2[0][1]) * f)
                b = (pts2[3][0] + (pts2[2][0] - pts2[3][0]) * f, pts2[3][1] + (pts2[2][1] - pts2[3][1]) * f)
                d.line([a, b], fill=(20, 30, 60, 255), width=1)
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


# ---------------- trayectoria hiperbólica del sobrevuelo ----------------
E_H = 2.0
RP = 1.5                       # 6,371 + 3,200 km ≈ 1.5 radios terrestres
A_H = RP / (E_H - 1)
B_H = A_H * math.sqrt(E_H ** 2 - 1)


def F_of_M(M):
    F = math.asinh(M / E_H) if abs(M) > 1e-9 else 0.0
    for _ in range(30):
        F -= (E_H * math.sinh(F) - F - M) / (E_H * math.cosh(F) - 1)
    return F


def hyp(F, e1=(0, 0, 1), e2=(1, 0, 0)):
    e1 = np.asarray(e1, float); e2 = np.asarray(e2, float)
    return A_H * (E_H - math.cosh(F)) * e1 + B_H * math.sinh(F) * e2


def hyp_vel(F, e1=(0, 0, 1), e2=(1, 0, 0)):
    e1 = np.asarray(e1, float); e2 = np.asarray(e2, float)
    return -A_H * math.sinh(F) * e1 + B_H * math.cosh(F) * e2


# ---------------- satélites ----------------
RSAT = np.random.default_rng(45)
NL = 700
L_R = 1.06 + RSAT.random(NL) ** 2 * 0.25
L_I = RSAT.uniform(0, np.pi, NL); L_O = RSAT.uniform(0, 2 * np.pi, NL); L_P = RSAT.uniform(0, 2 * np.pi, NL)
R_GPS = (6371 + 20200) / 6371
G_O = np.repeat(np.arange(6) * np.pi / 3, 4); G_P = np.tile(np.arange(4) * np.pi / 2, 6) + G_O * 0.3
G_I = math.radians(55)


def sat_points(t):
    ph = L_P + t * 0.9 / L_R ** 1.5
    x = np.cos(ph); y = np.sin(ph)
    P = np.stack([x, y * np.cos(L_I), y * np.sin(L_I)], -1)
    c, s = np.cos(L_O), np.sin(L_O)
    P = np.stack([P[:, 0] * c - P[:, 2] * s, P[:, 1], P[:, 0] * s + P[:, 2] * c], -1) * L_R[:, None]
    phg = G_P + t * 0.11
    xg = np.cos(phg); yg = np.sin(phg)
    Q = np.stack([xg, yg * math.sin(G_I), yg * math.cos(G_I)], -1)
    c, s = np.cos(G_O), np.sin(G_O)
    Q = np.stack([Q[:, 0] * c - Q[:, 2] * s, Q[:, 1], Q[:, 0] * s + Q[:, 2] * c], -1) * R_GPS
    return P, Q


def satellites(img, cam, t, amt=1.0, gps=1.0):
    P, Q = sat_points(t)
    # ocultar los que quedan detrás de la Tierra
    def vis(X):
        d = X - cam.O; L = np.linalg.norm(d, axis=1); dn = d / L[:, None]
        b = dn @ (cam.O); disc = b * b - (cam.O @ cam.O - 1.0)
        tt = -b - np.sqrt(np.maximum(disc, 0))
        return ~((disc > 0) & (tt > 0) & (tt < L))
    v = vis(P)
    splat(img, cam, P[v], np.tile(np.array([[0.9, 0.95, 1.1]]) * 0.010 * amt, (v.sum(), 1)).astype(np.float32))
    if gps > 0:
        v = vis(Q)
        splat(img, cam, Q[v], np.tile(np.array([[1.6, 1.4, 0.7]]) * 0.08 * gps, (v.sum(), 1)).astype(np.float32))


# ---------------- planos ----------------
O3 = np.zeros(3)
FIRST = ["gancho", "nave", "resortera", "marte", "destino", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.22) for i, k in enumerate(FIRST)]
SUB = {"destino_b": SPLIT("destino", 0.40), "cierre_b": SPLIT("cierre", 0.52)}
FL = [b for _, b in SHOTS[1:]] + [SUB["destino_b"], SUB["cierre_b"], CARD - 0.05]
SUNDIR = unit([-0.75, 0.35, 0.55])


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


EARTH_LON = 0.35            # gira la textura para que se vea África (ajustado con cuadros de prueba)


def flyby(img, t, cam, M, scale, show_sats=1.0, gps=1.0, lon=EARTH_LON):
    draw_earth(img, cam, O3, 1.0, t, atm=0.035, glow=0.8, expo=1.0, lon=lon)
    satellites(img, cam, t, show_sats, gps)
    F = F_of_M(M)
    P = hyp(F); Vv = hyp_vel(F)
    Rm = ship_frame(Vv, (0, 1, 0))
    info = draw_ship(img, cam, P, Rm, scale, light=LIGHT)
    return P, F, info


M_RATE = 0.52
TP = 3.9


def sh_gancho(img, t):
    a0, a1 = span("gancho")
    s = (t - a0) / (a1 - a0)
    k = ease(smooth(0.30, 0.82, s))
    M = (t - TP) * M_RATE
    F0 = F_of_M(M); Ps = hyp(F0); vh = unit(hyp_vel(F0))
    near_pos = Ps - 2.1 * vh + np.array([0.0, 0.8, 1.3]); near_tgt = Ps * 0.5
    pos = lerp(near_pos, (0.0, 13.5, 19.0), k)
    tgt = lerp(near_tgt, (0.0, -0.6, 0.0), k)
    cam = Cam(pos, tgt, roll=0.05 * (1 - k))
    P, F, info = flyby(img, t, cam, M, 0.008 + 0.006 * k, 1.0, smooth(0.35, 0.65, s))
    return cam, dict(P=P, F=F, info=info, k=k)


def sh_nave(img, t):
    a0, a1 = span("nave")
    s = (t - a0) / (a1 - a0)
    ang = 0.75 - 1.2 * ease(s)
    D = 2.5 - 0.35 * ease(s)
    cam = Cam((D * math.sin(ang), 0.9 - 0.4 * s, D * math.cos(ang)), (0, -0.05, 0), roll=-0.06)
    # Júpiter muy lejos, al fondo; el Sol fuera de cuadro
    jp = np.array([-0.6, 0.25, -1.0]) * 400
    jinfo = draw_body(img, cam, jp, 10.0, t, JUPL, spin=0.2, tilt=0.15, light=SUNDIR, expo=1.4)
    info = draw_ship(img, cam, O3, ship_frame((0.25, 0.0, -1.0)), 1 / 30, light=SUNDIR, expo=1.05)
    return cam, dict(info=info, jinfo=jinfo, jp=jp)


RE1 = (1, 0, 0); RE2 = (0, 0, -1)


def sh_resortera(img, t):
    a0, a1 = span("resortera")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.9, 12.5 - 0.8 * s, 2.0), (0.9, 0.0, -0.75), roll=0.0)
    # el ritmo de M se ajusta para pasar por el perigeo hacia s ≈ 0.42 (cuando se dice la distancia)
    M = (s - 0.40) * 4.5
    draw_earth(img, cam, O3, 1.0, t, atm=0.035, glow=0.8, expo=1.0, lon=EARTH_LON + 0.6)
    F = F_of_M(M)
    P = hyp(F, RE1, RE2); Vv = hyp_vel(F, RE1, RE2)
    info = draw_ship(img, cam, P, ship_frame(Vv, (0, 1, 0)), 0.016, light=LIGHT)
    return cam, dict(P=P, F=F, info=info, s=s)


# mapa del viaje (escala comprimida): Tierra 2.0, Marte 3.0, Júpiter 4.6
R_E, R_M, R_J = 2.0, 3.0, 4.6
KEY = [(R_E, -0.3), (2.55, 0.6), (R_M, 1.75), (2.45, 3.2), (R_E, 4.45), (3.3, 5.6), (R_J, 6.9)]


def _path():
    from scipy.interpolate import CubicSpline
    u = np.linspace(0, 1, len(KEY))
    r = CubicSpline(u, [k[0] for k in KEY]); th = CubicSpline(u, [k[1] for k in KEY])
    return r, th


PR, PTH = _path()
U_MARS = 2 / 6; U_EARTH = 4 / 6


def path_pt(u):
    r = float(PR(u)); th = float(PTH(u))
    return np.array([r * math.sin(th), 0.0, r * math.cos(th)])


def sun_draw(img, cam, r, t):
    return draw_star(img, cam, O3, r, t, SOL_HOT, SOL_COOL, 1.0, spin=0.04 * t, halo=2.0,
                     halo_col=np.array([1.6, 1.1, 0.5]), tex=SUN_N)


def sh_marte(img, t):
    a0, a1 = span("marte")
    s = (t - a0) / (a1 - a0)
    cam = Cam((0.3, 16.5 - 1.0 * s, 12.5 - 0.5 * s), (0.0, 0.0, -0.3), roll=0.0)
    u = U_MARS - 0.06 + (U_EARTH + 0.02 - U_MARS + 0.06) * ease(s)
    sun_draw(img, cam, 0.42, t)
    Pm = path_pt(U_MARS); Pe = path_pt(U_EARTH); Pj = path_pt(1.0)
    minfo = draw_body(img, cam, Pm, 0.22, t, MARS, spin=0.3 * t, tilt=0.2, light=unit(-Pm), expo=1.5)
    draw_earth(img, cam, Pe, 0.25, t, atm=0.06, glow=1.0, expo=1.4, lon=EARTH_LON)
    jinfo = draw_body(img, cam, Pj, 0.45, t, JUPL, spin=0.25 * t, tilt=0.1, light=unit(-Pj), expo=1.4)
    Ps = path_pt(u)
    du = 0.002
    info = draw_ship(img, cam, Ps, ship_frame(path_pt(u + du) - path_pt(u - du), (0, 1, 0)), 0.012, light=unit(-Ps + np.array([0, 2, 0])))
    return cam, dict(u=u, Pm=Pm, Pe=Pe, Pj=Pj, info=info)


EUR_C = np.array([0.0, 0.0, 0.0])


def cutaway(img, cam, C, r, prog, t):
    """Corte de Europa en el cuadrante de arriba a la derecha: hielo, océano, roca y núcleo."""
    if prog <= 0:
        return None
    cx, cy, cz = pt(cam, C)
    dist = float(np.linalg.norm(np.asarray(C) - cam.O))
    rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
    x0 = int(max(0, cx - 2)); x1 = int(min(W, cx + rpx + 3))
    y0 = int(max(0, cy - rpx - 3)); y1 = int(min(H, cy + 2))
    if x0 >= x1 or y0 >= y1:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx = (xx + 0.5 - cx) / rpx; dy = (cy - yy - 0.5) / rpx
    rho = np.sqrt(dx * dx + dy * dy)
    phi = np.arctan2(dy, dx)
    lim = prog * (np.pi / 2)
    m = (rho < 1.0) & (dx >= 0) & (dy >= 0) & (phi <= lim + 1e-3)
    if not m.any():
        return (cx, cy, rpx)
    reg = img[y0:y1, x0:x1]
    col = np.zeros(rho.shape + (3,), np.float32)
    ice = rho > 0.93
    ocean = (rho > 0.82) & ~ice
    rock = (rho > 0.30) & (rho <= 0.82)
    core = rho <= 0.30
    shimmer = 0.85 + 0.15 * np.sin(rho * 140 - t * 3.0 + phi * 6)
    col[ice] = np.array([0.80, 0.88, 1.00])
    col[ocean] = (np.array([0.02, 0.16, 0.75]) * shimmer[..., None])[ocean]
    rk = fbm(dx * 4, dy * 4, np.full_like(dx, 1.3), 3, seed=91)
    col[rock] = (np.array([0.20, 0.13, 0.09]) * (0.75 + 0.5 * rk)[..., None])[rock]
    col[core] = (np.array([0.55, 0.30, 0.12]) * (0.8 + 0.4 * (1 - rho / 0.3))[..., None])[core]
    # sombra suave hacia el centro del corte para dar volumen
    col *= (0.65 + 0.35 * np.clip(rho, 0, 1))[..., None]
    a = m.astype(np.float32)[..., None]
    reg[:] = reg * (1 - a) + col * a
    return (cx, cy, rpx)


def sh_destino(img, t):
    a0, a1 = span("destino")
    tb = SUB["destino_b"]
    if t < tb:
        s = (t - a0) / (tb - a0)
        cam = Cam((0.4, 0.5, 4.2 - 0.5 * s), (0.0, 0.25, 0.0), roll=0.04)
        jinfo = draw_body(img, cam, (0, 0.6, -1.5), 1.6, t, JUPL, spin=0.12 * t, tilt=0.05, light=SUNDIR, expo=0.75, amb=0.01)
        ang = -0.5 + 0.35 * s
        Pe = np.array([1.05 * math.sin(ang), -0.35, 1.2 * math.cos(ang)])
        einfo = draw_body(img, cam, Pe, 0.16, t, EUROPA, spin=0.2, tilt=0.1, light=SUNDIR, expo=0.8, amb=0.01)
        return cam, dict(mode="jup", jinfo=jinfo, einfo=einfo)
    s = (t - tb) / (a1 - tb)
    cam = Cam((0.0, 0.2, 6.4 - 0.4 * s), (0.0, 0.2, 0.0))
    einfo = draw_body(img, cam, EUR_C, 1.0, t, EUROPA, spin=0.08 * t + 0.6, tilt=0.15, light=unit([-0.5, 0.35, 0.8]), expo=0.8, amb=0.02)
    cinfo = cutaway(img, cam, EUR_C, 1.0, smooth(0.25, 0.75, s), t)
    return cam, dict(mode="eur", einfo=einfo, cinfo=cinfo, cs=smooth(0.25, 0.75, s))


def sh_cierre(img, t):
    a0, a1 = span("cierre")
    tb = SUB["cierre_b"]
    if t < tb:
        s = (t - a0) / (tb - a0)
        cam = Cam((0.1 * s, 0.2 + 0.1 * s, 6.0 - 1.4 * ease(s)), (0.15 * s, 0.2 + 0.15 * s, 0.0))
        einfo = draw_body(img, cam, EUR_C, 1.0, t, EUROPA, spin=0.08 * t + 0.6, tilt=0.15, light=unit([-0.5, 0.35, 0.8]), expo=0.8, amb=0.02)
        cinfo = cutaway(img, cam, EUR_C, 1.0, 1.0, t)
        return cam, dict(mode="eur", einfo=einfo, cinfo=cinfo)
    s = (t - tb) / (END - tb)
    pos = lerp((3.2, 1.3, 5.6), (2.6, 1.0, 4.6), ease(s))
    cam = Cam(pos, (-0.3, 0.1, 0.4), roll=0.05)
    M = (s - 0.35) * 2.2
    P, F, info = flyby(img, t, cam, M, 0.010, 1.0, 0.0)
    return cam, dict(mode="earth", P=P, info=info)


SCENES = dict(gancho=sh_gancho, nave=sh_nave, resortera=sh_resortera, marte=sh_marte, destino=sh_destino, cierre=sh_cierre)


# ---------------- textos y gráficos ----------------
def counter(d, t, a, b, v0, v1, fmt, y, size, col, A, x=W / 2):
    k = ease_out((t - a) / max(b - a, 1e-3))
    txt(d, (x, y), fmt(v0 + (v1 - v0) * k), size, col, A, "Inter-Black.otf", 9)


def poly3(d, cam, pts, col, A, width=3, dash=False):
    P = [pt(cam, p) for p in pts]
    for i in range(len(P) - 1):
        if dash and i % 2 == 1:
            continue
        if P[i][2] > 0.05 and P[i + 1][2] > 0.05:
            d.line([P[i][:2], P[i + 1][:2]], fill=col + (int(A),), width=width)


def circle3(d, cam, R, col, A, width=2, dash=True, n=160, y=0.0):
    pts = [np.array([R * math.sin(a), y, R * math.cos(a)]) for a in np.linspace(0, 2 * np.pi, n)]
    poly3(d, cam, pts, col, A, width, dash)


def arrow(d, p0, p1, col, A, width=10, head=34):
    d.line([p0, p1], fill=col + (A,), width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    a1 = (p1[0] - head * math.cos(ang - 0.45), p1[1] - head * math.sin(ang - 0.45))
    a2 = (p1[0] - head * math.cos(ang + 0.45), p1[1] - head * math.sin(ang + 0.45))
    d.polygon([p1, a1, a2], fill=col + (A,))


def traj_pts(F0, F1, n=90, e1=(0, 0, 1), e2=(1, 0, 0)):
    return [hyp(F, e1, e2) for F in np.linspace(F0, F1, n)]


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0, a1 = span(name)
    if name == "gancho":
        cut = SPLIT("gancho", 0.42)
        draw_label(layer, t, -1, cut, "JUEVES 3 DIC", ["una nave de la NASA pasa por aquí"], YELLOW, 128)
        draw_label(layer, t, cut, a1 + 0.3, "MÁS CERCA", ["que muchos satélites"], WHITE, 124)
        A = int(255 * fade(t, 0.3, a1 + 0.3))
        poly3(d, cam, traj_pts(-2.4, ex["F"], 120), CYAN, A * 0.8, 4)
        poly3(d, cam, traj_pts(ex["F"], 2.4, 120), CYAN, A * 0.30, 3, dash=True)
        Ag = int(255 * fade(t, SPLIT("gancho", 0.45), a1 + 0.3) * 0.75)
        if Ag > 0:
            circle3(d, cam, R_GPS, YELLOW, Ag * 0.7, 3)
            gx, gy, _ = pt(cam, np.array([R_GPS * 0.71, 0, R_GPS * 0.71]))
            txt(d, (min(gx, W - 40), gy + 50), "SATÉLITES GPS", 40, YELLOW, Ag, "Inter-Black.otf", 6, "rm")
            txt(d, (min(gx, W - 40), gy + 96), "20,200 km", 38, WHITE, Ag, "Inter-ExtraBold.otf", 6, "rm")
        if ex["info"] and ex["k"] > 0.3:
            x, y = ex["info"]
            Am = int(255 * fade(t, SPLIT("gancho", 0.55), a1 + 0.3))
            marker(d, x, y, t, CYAN, Am, 30, "NAVE", -1 if x > W * 0.5 else 1, 42)
    elif name == "nave":
        cut = SPLIT("nave", 0.55)
        draw_label(layer, t, a0 + 0.1, cut, "EUROPA CLIPPER", ["lanzada en octubre de 2024"], YELLOW, 118)
        draw_label(layer, t, cut, a1, "NECESITA UN EMPUJÓN", ["para llegar a Júpiter"], WHITE, 100)
        if ex["jinfo"]:
            x, y, r = ex["jinfo"]
            A = int(255 * fade(t, a0 + 0.8, a1) * 0.9)
            if 40 < x < W - 40 and 500 < y < 1200:
                txt(d, (x, y + r + 40), "JÚPITER", 38, WHITE, A, "Inter-Black.otf", 6)
    elif name == "resortera":
        s = ex["s"]
        cut = SPLIT("resortera", 0.55)
        draw_label(layer, t, a0 + 0.1, cut, "3,200 KM", ["de la superficie, el 3 de diciembre"], YELLOW, 132)
        draw_label(layer, t, cut, a1, "RESORTERA", ["sale más rápida y ahorra combustible"], CYAN, 128)
        A = int(255 * fade(t, a0 + 0.1, a1))
        poly3(d, cam, traj_pts(-2.0, 2.0, 160, RE1, RE2), CYAN, A * 0.28, 3, dash=True)
        poly3(d, cam, traj_pts(-2.0, ex["F"], 160, RE1, RE2), CYAN, A * 0.9, 5)
        # regla de 3,200 km en el perigeo
        Ar = int(255 * fade(t, SPLIT("resortera", 0.30), cut + 0.4))
        if Ar > 0:
            p0 = pt(cam, np.array([1.0, 0, 0])); p1 = pt(cam, np.array([RP, 0, 0]))
            d.line([p0[:2], p1[:2]], fill=YELLOW + (Ar,), width=6)
            for p in (p0, p1):
                d.line([(p[0], p[1] - 22), (p[0], p[1] + 22)], fill=YELLOW + (Ar,), width=6)
            k = ease_out((t - SPLIT("resortera", 0.30)) / 0.8)
            txt(d, ((p0[0] + p1[0]) / 2 + 20, p0[1] - 60), f"{int(round(3200 * k / 10) * 10):,} km", 52, YELLOW, Ar, "Inter-Black.otf", 7, "mm")
        # flechas de velocidad: entra y sale
        Aa = int(255 * fade(t, cut, a1))
        if Aa > 0:
            pi = pt(cam, hyp(-1.35, RE1, RE2)); pi2 = pt(cam, hyp(-1.0, RE1, RE2))
            po = pt(cam, hyp(0.55, RE1, RE2)); po2 = pt(cam, hyp(0.85, RE1, RE2))
            arrow(d, pi[:2], pi2[:2], WHITE, int(Aa * 0.8), 8, 28)
            k = ease_out((t - cut) / 0.8)
            tip = (po[0] + (po2[0] - po[0]) * (0.4 + 0.6 * k) * 1.25, po[1] + (po2[1] - po[1]) * (0.4 + 0.6 * k) * 1.25)
            arrow(d, po[:2], tip, YELLOW, Aa, 12, 40)
            txt(d, (tip[0] + 40, tip[1] + 30), "+ RÁPIDA", 50, YELLOW, Aa, "Inter-Black.otf", 7, "lm")
        ex_ = pt(cam, O3)
        txt(d, (ex_[0], ex_[1] - 215), "TIERRA", 42, WHITE, int(A * 0.8), "Inter-Black.otf", 6)
    elif name == "marte":
        cut = SPLIT("marte", 0.50)
        draw_label(layer, t, a0 + 0.1, cut, "MARTE ✓", ["primer empujón, marzo de 2025"], (255, 140, 100), 124)
        draw_label(layer, t, cut, a1, "ÚLTIMO EMPUJÓN", ["la Tierra, 3 de diciembre de 2026"], YELLOW, 112)
        A = int(255 * fade(t, a0 + 0.1, a1))
        circle3(d, cam, R_E, CYAN, A * 0.35, 2)
        circle3(d, cam, R_M, (255, 140, 100), A * 0.30, 2)
        circle3(d, cam, R_J, (220, 190, 150), A * 0.25, 2)
        us = np.linspace(0, 1, 220)
        pts = [path_pt(u) for u in us]
        poly3(d, cam, pts, WHITE, A * 0.35, 3, dash=True)
        done = [path_pt(u) for u in us if u <= ex["u"]] + [path_pt(ex["u"])]
        poly3(d, cam, done, YELLOW, A * 0.95, 5)
        for P, lab, col, dy in ((ex["Pm"], "MARTE · 2025", (255, 150, 110), 70), (ex["Pe"], "TIERRA · 2026", CYAN, -60), (ex["Pj"], "JÚPITER · 2030", (230, 200, 160), 95)):
            x, y, _ = pt(cam, P)
            x = min(max(x, 190), W - 190)
            txt(d, (x, y + dy), lab, 40, col, int(A * 0.95), "Inter-Black.otf", 6, "mm")
    elif name == "destino":
        tb = SUB["destino_b"]
        if ex["mode"] == "jup":
            draw_label(layer, t, a0 + 0.1, tb, "JÚPITER · 2030", ["llegada en abril de 2030"], (240, 205, 160), 118)
            if ex["einfo"]:
                x, y, r = ex["einfo"]
                A = int(255 * fade(t, a0 + 0.5, tb))
                marker(d, x, y, t, CYAN, A, max(26, r + 12), "EUROPA", 1, 44)
        else:
            draw_label(layer, t, tb, a1, "EUROPA", ["luna de Júpiter"], CYAN, 132)
            if ex["cinfo"] and ex["cs"] > 0.6:
                cx, cy, rp = ex["cinfo"]
                A = int(255 * min(1, (ex["cs"] - 0.6) / 0.3) * fade(t, tb, a1))
                xi = cx + rp * 0.965 * math.cos(1.25); yi = cy - rp * 0.965 * math.sin(1.25)
                xo = cx + rp * 0.875 * math.cos(0.8); yo = cy - rp * 0.875 * math.sin(0.8)
                lx, ly = cx + rp * 0.30, cy - rp - 50
                d.line([(xi, yi), (lx, ly + 22)], fill=WHITE + (A,), width=4)
                txt(d, (lx, ly), "HIELO", 46, WHITE, A, "Inter-Black.otf", 6, "mm")
                ox, oy = cx + rp * 0.40, cy - rp * 0.38
                d.line([(xo, yo), (ox + 40, oy - 24)], fill=CYAN + (A,), width=4)
                txt(d, (ox, oy), "OCÉANO", 50, CYAN, A, "Inter-Black.otf", 7, "mm")
    elif name == "cierre":
        tb = SUB["cierre_b"]
        if ex["mode"] == "eur":
            draw_label(layer, t, a0 + 0.1, tb, "BUSCAR VIDA", ["uno de los mejores lugares"], YELLOW, 128)
        else:
            draw_label(layer, t, tb, CARD, "PRIMERO, POR AQUÍ", ["Tierra · 3 de diciembre"], WHITE, 110)
            A = int(255 * fade(t, tb + 0.2, CARD))
            poly3(d, cam, traj_pts(-2.4, 2.4, 140), CYAN, A * 0.4, 3, dash=True)
            if ex["info"]:
                x, y = ex["info"]
                marker(d, x, y, t, CYAN, A, 30, "EUROPA CLIPPER", -1 if x > W * 0.5 else 1, 40)
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
