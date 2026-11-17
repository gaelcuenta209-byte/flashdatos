"""Flash Datos · video 36: Starship V4, la nave más grande del mundo va a crecer (anuncio de Musk, 15 nov 2026).

Escena nueva: la nave atrapada en los brazos de la torre que se estira; la nave actual con regla de 52 m;
la actual y la V4 lado a lado mientras la V4 crece a 70 m; la V4 junto a un edificio de 23 pisos y el
propulsor que aparece debajo; vista desde abajo con 6 motores que pasan a 9 y se encienden; las dos naves
en órbita con los tanques llenándose; vuelos de recarga a un depósito en órbita y salida hacia la Luna; y
la torre al atardecer con las dos naves. Base técnica: mallas y partículas de los videos 30 y 34.

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

def draw_earth(img, cam, C, r, t, atm=0.03, glow=0.55):
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


# ---------------- naves (cajas 3D dibujadas como polígonos) ----------------
def box_faces(center, half, R):
    hx, hy, hz = half
    V = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    V = V @ R.T + center
    F = [((0, 1, 3, 2), (-1, 0, 0)), ((4, 6, 7, 5), (1, 0, 0)), ((0, 4, 5, 1), (0, -1, 0)),
         ((2, 3, 7, 6), (0, 1, 0)), ((0, 2, 6, 4), (0, 0, -1)), ((1, 5, 7, 3), (0, 0, 1))]
    return V, [(idx, R @ np.array(nr, float)) for idx, nr in F]


def rotm(yaw, pitch=0.0, roll=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch); cr, sr = math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def draw_boxes(layer, cam, boxes, alpha=1.0):
    """boxes: lista de (centro, medias, R, color_rgb). Ordena caras por profundidad."""
    polys = []
    for c, half, R, col in boxes:
        V, F = box_faces(np.asarray(c, float), half, R)
        x, y, z = cam.proj(V)
        if (z <= 1e-4).any():
            continue
        for idx, nr in F:
            ctr = V[list(idx)].mean(0)
            if (ctr - cam.O) @ nr >= 0:
                continue
            lam = 0.25 + 0.95 * max(0.0, float(nr @ LIGHT))
            shade = tuple(int(min(255, ch * lam)) for ch in col)
            polys.append((float(np.linalg.norm(ctr - cam.O)), [(float(x[i]), float(y[i])) for i in idx], shade))
    polys.sort(key=lambda p: -p[0])
    d = ImageDraw.Draw(layer)
    A = int(255 * alpha)
    for _, pts, shade in polys:
        d.polygon(pts, fill=shade + (A,), outline=(20, 24, 34, A))




# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
SPLIT = lambda k, f: S0[k] + (S1[k] - S0[k]) * f
CARD = S1["cierre"] + 0.2
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
def impact_flash(img, cam, P, t_since, k=1.0):
    if t_since < 0 or t_since > 2.5:
        return
    x, y, z = cam.proj(P)
    if z[0] <= 0:
        return
    s = math.exp(-t_since / 0.25) * 7 * k + math.exp(-t_since / 1.0) * 0.6 * k
    small = np.zeros((H // 4, W // 4, 3), np.float32)
    xi, yi = int(x[0] / 4), int(y[0] / 4)
    if 0 <= xi < W // 4 and 0 <= yi < H // 4:
        small[yi, xi] = np.array([1.0, 0.85, 0.6]) * s * 900
        g = gaussian_filter(small, (3, 3, 0)) + gaussian_filter(small, (14, 14, 0)) * 0.6
        img += ndzoom(g, (4, 4, 1), order=1)[:H, :W]



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





# ================= mundo: cielo, suelo y mar (a media resolución) =================
H2, W2 = H // 2, W // 2
DIRS2 = DIRS[::2, ::2]
_gy, _gx = np.mgrid[0:256, 0:256] / 256.0
GTEX = fbm(_gx * 8, _gy * 8, np.full_like(_gx, 0.3), 5, seed=5).astype(np.float32)
GTEX2 = fbm(_gx * 40, _gy * 40, np.full_like(_gx, 1.7), 3, seed=9).astype(np.float32)

LIGHTS = {
    "dusk": dict(L=(-0.86, 0.15, -0.30), sun=(2.4, 1.40, 0.75), hor=(0.80, 0.34, 0.13), zen=(0.025, 0.045, 0.15),
                 amb=(0.20, 0.17, 0.22), sand=(0.50, 0.36, 0.24), sea=(0.03, 0.05, 0.10), fog=(0.95, 0.52, 0.30)),
    "day": dict(L=(-0.45, 0.78, 0.45), sun=(2.5, 2.35, 2.15), hor=(0.62, 0.76, 0.92), zen=(0.13, 0.28, 0.70),
                amb=(0.22, 0.27, 0.36), sand=(0.62, 0.52, 0.38), sea=(0.04, 0.12, 0.22), fog=(0.66, 0.78, 0.92)),
    "gulf": dict(L=(-0.80, 0.12, -0.45), sun=(2.4, 1.30, 0.70), hor=(0.62, 0.30, 0.14), zen=(0.03, 0.05, 0.16),
                 amb=(0.18, 0.15, 0.20), sand=(0.50, 0.36, 0.24), sea=(0.02, 0.04, 0.08), fog=(0.70, 0.40, 0.25)),
    "space": dict(L=(-0.62, 0.40, 0.68), sun=(2.4, 2.3, 2.15), amb=(0.03, 0.035, 0.05)),
}


def unit(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)


def draw_world(img, cam, mode):
    P = LIGHTS[mode]
    L = unit(P["L"])
    d = DIRS2[..., 0:1] * cam.r + DIRS2[..., 1:2] * cam.u + (-DIRS2[..., 2:3]) * cam.f
    dy = d[..., 1]
    out = np.zeros((H2, W2, 3), np.float32)
    hor = np.array(P["hor"], np.float32); zen = np.array(P["zen"], np.float32)
    k = np.clip(dy + 0.02, 0, 1) ** 0.38
    sky = hor * (1 - k[..., None]) + zen * k[..., None]
    cs = np.clip(d @ L, -1, 1)
    sky += np.array(P["sun"], np.float32) * (np.clip(cs, 0, 1) ** 220 * 4.0 + np.clip(cs, 0, 1) ** 12 * 0.18)[..., None]
    out[:] = sky
    g = dy < -1e-4
    if g.any():
        dg = d[g]
        tt = -cam.O[1] / dg[:, 1]
        Pg = cam.O + tt[:, None] * dg
        x, z = Pg[:, 0], Pg[:, 2]
        n1 = GTEX[((z / 60) * 256).astype(np.int64) % 256, ((x / 60) * 256).astype(np.int64) % 256]
        n2 = GTEX2[((z / 9) * 256).astype(np.int64) % 256, ((x / 9) * 256).astype(np.int64) % 256]
        sand = np.array(P["sand"], np.float32) * (0.75 + 0.45 * n1 + 0.15 * n2)[:, None]
        r = np.sqrt(x * x + z * z)
        pad = smooth(48, 44, r)[:, None]
        concrete = np.array((0.42, 0.42, 0.44), np.float32) * (0.85 + 0.2 * n2)[:, None]
        col = sand * (1 - pad) + concrete * pad
        lit = (0.35 + 1.0 * max(L[1], 0.05) * 1.6)
        col = col * lit * (np.array(P["sun"], np.float32) / 2.3) + np.array(P["amb"], np.float32) * 0.3
        sea = smooth(-520, -560, z)[:, None] if mode != "gulf" else np.ones((len(z), 1), np.float32)
        if mode == "gulf":
            col = col * 0 + (0.85 + 0.3 * n2)[:, None] * 0.0
        refl = hor * 0.55 + np.array(P["sun"], np.float32) * (np.clip(np.reshape(dg * np.array([1, -1, 1]), (-1, 3)) @ L, 0, 1) ** 60 * 1.5)[:, None]
        col = col * (1 - sea) + (np.array(P["sea"], np.float32) + refl * 0.5) * sea
        fogk = (1 - np.exp(-tt / 2600.0))[:, None]
        col = col * (1 - fogk) + np.array(P["fog"], np.float32) * fogk
        out[g] = col
    img[:] = ndzoom(out, (2, 2, 1), order=1)[:H, :W]


# ================= mallas (polígonos sombreados) =================
STEEL = (0.72, 0.73, 0.76); STEEL_D = (0.38, 0.39, 0.42); TILE = (0.035, 0.035, 0.04); TOWER = (0.17, 0.17, 0.19)
ARM = (0.55, 0.56, 0.58)


def F(verts, n, col, spec=0.0, emit=None):
    return (np.asarray(verts, float), np.asarray(n, float), col, spec, emit)


def cyl(faces, R, pos, y0, y1, r0, r1, n=28, col=STEEL, spec=0.55, belly=None, emit=None):
    """Cilindro/cono a lo largo del eje y local. belly=(color) pinta de negro las caras hacia -x local (escudo térmico)."""
    sl = (r0 - r1) / max(y1 - y0, 1e-6)
    for i in range(n):
        a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n; am = (a0 + a1) / 2
        v = [(r0 * math.cos(a0), y0, r0 * math.sin(a0)), (r0 * math.cos(a1), y0, r0 * math.sin(a1)),
             (r1 * math.cos(a1), y1, r1 * math.sin(a1)), (r1 * math.cos(a0), y1, r1 * math.sin(a0))]
        nl = unit((math.cos(am), sl, math.sin(am)))
        c = col
        if belly is not None and math.cos(am) < -0.05:
            c = belly
        e = emit if (emit is not None and belly is not None and math.cos(am) < -0.05) else None
        faces.append(F(np.asarray(v) @ R.T + pos, R @ nl, c, 0.12 if c == TILE else spec, e))


def boxf(faces, center, half, R, col, spec=0.15, emit=None):
    V, FF = box_faces(np.asarray(center, float), half, R)
    for idx, nr in FF:
        faces.append(F(V[list(idx)], nr, col, spec, emit))


def axis_R(axis):
    """Matriz que lleva el eje y local a 'axis'."""
    a = unit(axis); y = np.array([0.0, 1.0, 0.0])
    v = np.cross(y, a); s = np.linalg.norm(v); c = float(y @ a)
    if s < 1e-8:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)


RB_, HB, HS = 4.5, 71.0, 52.0


def booster(faces, pos, R=np.eye(3), fins=True):
    pos = np.asarray(pos, float)
    cyl(faces, R, pos, 0, 3, RB_ * 0.92, RB_, col=STEEL_D)
    for y0, y1 in ((3, 22), (22, 44), (44, 64)):
        cyl(faces, R, pos, y0, y1, RB_, RB_)
    cyl(faces, R, pos, 64, 66, RB_, RB_, col=STEEL_D)        # anillo de separación caliente
    cyl(faces, R, pos, 66, HB, RB_, RB_)
    if fins:
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            c = R @ np.array([math.cos(a) * (RB_ + 1.4), 60.5, math.sin(a) * (RB_ + 1.4)]) + pos
            boxf(faces, c, (1.4, 2.6, 0.25), R @ rotm(-a), (0.30, 0.30, 0.33))
        for k in range(2):                                   # pasadores de captura
            a = math.pi / 2 + k * math.pi
            c = R @ np.array([math.cos(a) * (RB_ + 0.6), 63.0, math.sin(a) * (RB_ + 0.6)]) + pos
            boxf(faces, c, (0.6, 0.5, 0.6), R, (0.25, 0.25, 0.27))


def ship(faces, pos, R=np.eye(3), emit=None):
    pos = np.asarray(pos, float)
    cyl(faces, R, pos, 0, 2, RB_ * 0.95, RB_, col=STEEL_D)
    for y0, y1 in ((2, 18), (18, 34)):
        cyl(faces, R, pos, y0, y1, RB_, RB_, belly=TILE, emit=emit)
    prof = [(34, 1.0), (40, 0.93), (44.5, 0.78), (48, 0.56), (50.5, 0.32), (HS, 0.08)]
    for (y0, f0), (y1, f1) in zip(prof[:-1], prof[1:]):
        cyl(faces, R, pos, y0, y1, RB_ * f0, RB_ * f1, belly=TILE, emit=emit)
    for yy, hh, ww, sz in ((6.0, 4.5, 2.4, 1), (41.0, 3.2, 1.6, 0.85)):       # aletas traseras y delanteras
        for sgn in (-1, 1):
            c = R @ np.array([-0.6, yy, sgn * (RB_ * sz + ww)]) + pos
            boxf(faces, c, (1.2, hh, ww), R, TILE, 0.1, emit)


def tower(faces, x0=-17.0, h=146.0, half=6.0):
    I = np.eye(3)
    for sx in (-1, 1):
        for sz in (-1, 1):
            boxf(faces, (x0 + sx * half, h / 2, sz * half), (0.7, h / 2, 0.7), I, TOWER)
    for y in np.arange(9.0, h, 11.0):
        for sz in (-1, 1):
            boxf(faces, (x0, y, sz * half), (half, 0.35, 0.35), I, TOWER)
        for sx in (-1, 1):
            boxf(faces, (x0 + sx * half, y, 0), (0.35, 0.35, half), I, TOWER)
    boxf(faces, (x0, h + 6, 0), (0.3, 6, 0.3), I, TOWER)


def arms(faces, h, opn, x0=-17.0, half=6.0, L=34.0):
    """opn: 0 cerrado (abrazando un cohete en x=0) … 1 abierto."""
    I = np.eye(3)
    boxf(faces, (x0 + half + 0.8, h, 0), (1.2, 4.5, half + 1), I, (0.42, 0.42, 0.45))
    for side in (-1, 1):
        piv = np.array([x0 + half + 1.5, h, side * (half - 1.0)])
        ang = math.radians(4.0 + 28.0 * opn)
        dvec = np.array([math.cos(ang), 0.0, side * math.sin(ang)])
        c = piv + dvec * L / 2
        boxf(faces, c, (L / 2, 1.6, 1.1), rotm(-math.atan2(dvec[2], dvec[0])), ARM, 0.3)


def launch_mount(faces):
    I = np.eye(3)
    for k in range(8):
        a = k * math.pi / 4
        boxf(faces, (math.cos(a) * 7.5, 18.5, math.sin(a) * 7.5), (2.4, 1.5, 2.4), rotm(-a), (0.36, 0.36, 0.38))
    for k in range(6):
        a = k * math.pi / 3 + 0.3
        boxf(faces, (math.cos(a) * 8.5, 8.75, math.sin(a) * 8.5), (1.3, 8.75, 1.3), I, (0.33, 0.33, 0.35))


def draw_faces(img, cam, faces, mode, glow_emit=0.0):
    if not faces:
        return
    P = LIGHTS[mode]
    L = unit(P["L"]); sun = np.array(P["sun"]); amb = np.array(P["amb"])
    S = 2
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    items = []
    for verts, n, col, spec, emit in faces:
        ctr = verts.mean(0)
        v = ctr - cam.O
        if v @ n >= 0:
            continue
        x, y, z = cam.proj(verts)
        if (z <= 0.3).any():
            continue
        if x.max() < -50 or x.min() > W + 50 or y.max() < -50 or y.min() > H + 50:
            continue
        dist = float(np.linalg.norm(v))
        V = -v / dist
        ndl = float(n @ L)
        c = lin(col)
        sky = amb * (0.6 + 0.4 * n[1])
        dif = max(ndl, 0.0)
        Rr = 2 * ndl * n - L
        sp = max(float(Rr @ V), 0.0) ** 22 * spec * 1.4
        rgb = c * (sun * dif * 0.9 + sky * 1.6 + 0.02) + sun * sp * 0.6
        if emit is not None:
            rgb = rgb + np.array(emit) * glow_emit
        if mode != "space":
            fogk = 1 - math.exp(-dist / 2600.0)
            rgb = rgb * (1 - fogk) + np.array(P["fog"]) * fogk
        enc = tuple(int(min(255, 255 * math.sqrt(max(ch, 0) / 4.0))) for ch in rgb)
        items.append((dist, [(float(x[i]) * S, float(y[i]) * S) for i in range(len(x))], enc))
    items.sort(key=lambda p: -p[0])
    for _, pts, enc in items:
        dr.polygon(pts, fill=enc + (255,), outline=enc + (255,))
    lay = np.asarray(layer.resize((W, H), Image.BILINEAR), np.float32) / 255.0
    a = lay[..., 3:4]
    col = lay[..., :3] ** 2 * 4.0
    img[:] = img * (1 - a) + col * a


# ================= partículas: llamas, humo y plasma =================
def splat2(img, cam, Pts, col, sig=1.4, core=0.35):
    if len(Pts) == 0:
        return
    x, y, z = cam.proj(Pts)
    ok = (z > 0.3) & (x > -40) & (x < W + 40) & (y > -40) & (y < H + 40)
    x, y, c = x[ok], y[ok], col[ok]
    if len(x) == 0:
        return
    small = np.zeros((H // 4, W // 4, 3), np.float32)
    xi = np.clip((x / 4).astype(int), 0, W // 4 - 1); yi = np.clip((y / 4).astype(int), 0, H // 4 - 1)
    np.add.at(small, (yi, xi), c)
    small = gaussian_filter(small, (sig, sig, 0))
    img += ndzoom(small, (4, 4, 1), order=1)[:H, :W]
    if core > 0:
        xf = np.clip(x.astype(int), 0, W - 1); yf = np.clip(y.astype(int), 0, H - 1)
        np.add.at(img, (yf, xf), c * core)


def plume(img, cam, base, axis, length, width, n, t, k=1.0, seed=0, cone=1.5):
    rng = np.random.default_rng(seed * 1000 + int(t * FPS))
    a = unit(axis)
    p1 = unit(np.cross(a, [0.3, 0.1, 0.9])); p2 = np.cross(a, p1)
    u = rng.random(n) ** 0.8
    along = u * length
    rad = width * (0.25 + cone * u) * rng.normal(0, 0.45, n)
    rad2 = width * (0.25 + cone * u) * rng.normal(0, 0.45, n)
    Pts = np.asarray(base) + along[:, None] * a + rad[:, None] * p1 + rad2[:, None] * p2
    hot = np.exp(-u / 0.18)[:, None]
    col = (np.array([2.6, 2.3, 2.1]) * hot + np.array([2.2, 0.85, 0.25]) * (1 - hot) * np.exp(-u * 1.6)[:, None])
    col = col * (k * 260.0 / n)
    splat2(img, cam, Pts, col.astype(np.float32), 1.6, 0.25)


def smoke(img, cam, center, radius, n, t, warm, seed=3):
    rng = np.random.default_rng(seed)
    dirs = rng.normal(size=(n, 3)); dirs[:, 1] = np.abs(dirs[:, 1]) * 0.35
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    rr = radius * (0.35 + 0.65 * rng.random(n) ** 0.5)
    Pts = np.asarray(center) + dirs * rr[:, None] + rng.normal(0, radius * 0.06, (n, 3))
    col = np.array(warm, np.float32)[None, :] * (0.6 + 0.4 * rng.random(n))[:, None] * (60.0 / n)
    splat2(img, cam, Pts, col, 6.0, 0.0)




# ================= video 36: Starship V4 =================
def shipL(faces, pos, R=np.eye(3), L=52.0, emit=None):
    """Nave Starship de longitud L (el barril se estira; la nariz y las aletas conservan su forma)."""
    pos = np.asarray(pos, float)
    yb = L - 18.0
    cyl(faces, R, pos, 0, 2, RB_ * 0.95, RB_, col=STEEL_D)
    nseg = 2 if L < 60 else 3
    edges = np.linspace(2, yb, nseg + 1)
    for y0, y1 in zip(edges[:-1], edges[1:]):
        cyl(faces, R, pos, y0, y1, RB_, RB_, belly=TILE, emit=emit)
    prof = [(0, 1.0), (6, 0.93), (10.5, 0.78), (14, 0.56), (16.5, 0.32), (18, 0.08)]
    for (y0, f0), (y1, f1) in zip(prof[:-1], prof[1:]):
        cyl(faces, R, pos, yb + y0, yb + y1, RB_ * f0, RB_ * f1, belly=TILE, emit=emit)
    for yy, hh, ww, sz in ((6.0, 4.5, 2.4, 1), (yb + 7.0, 3.2, 1.6, 0.85)):
        for sgn in (-1, 1):
            c = R @ np.array([-0.6, yy, sgn * (RB_ * sz + ww)]) + pos
            boxf(faces, c, (1.2, hh, ww), R, TILE, 0.1, emit)


def disk(faces, R, pos, y, r, col, n=20, down=True, emit=None):
    sgn = -1 if down else 1
    v = [(r * math.cos(2 * math.pi * i / n), y, r * math.sin(2 * math.pi * i / n) * -sgn) for i in range(n)]
    faces.append(F(np.asarray(v) @ R.T + pos, R @ np.array([0.0, float(sgn), 0.0]), col, 0.05, emit))


def engine_layout(nvac):
    """Posiciones (x, z, radio de tobera, largo) de los motores vistos desde abajo."""
    out = [(1.25 * math.cos(a), 1.25 * math.sin(a), 0.62, 2.2) for a in (math.pi / 2, math.pi / 2 + 2.094, math.pi / 2 + 4.189)]
    for k in range(nvac):
        a = -math.pi / 2 + k * 2 * math.pi / nvac
        out.append((3.25 * math.cos(a), 3.25 * math.sin(a), 1.05, 3.4))
    return out


def building(faces, x0, z0, w, floors, fh=3.0):
    I = np.eye(3)
    for k in range(floors):
        y = k * fh
        boxf(faces, (x0, y + fh * 0.62, z0), (w / 2, fh * 0.38, w / 2), I, (0.30, 0.42, 0.55), 0.6)   # ventanas
        boxf(faces, (x0, y + fh * 0.12, z0), (w / 2 + 0.25, fh * 0.12, w / 2 + 0.25), I, (0.80, 0.80, 0.78), 0.1)
    boxf(faces, (x0, floors * fh + 0.6, z0), (w / 2 + 0.4, 0.6, w / 2 + 0.4), I, (0.70, 0.70, 0.68), 0.1)


def clamp_ground(faces):
    out = []
    for verts, n, col, spec, e in faces:
        if verts[:, 1].max() <= 0.05:
            continue
        v = verts.copy(); v[:, 1] = np.maximum(v[:, 1], 0.0)
        out.append((v, n, col, spec, e))
    return out


def draw_ball(img, cam, C, r, base, seed=4):
    C = np.asarray(C, float)
    cx, cy, cz = cam.proj(C)
    if cz[0] <= 0:
        return
    dist = float(np.linalg.norm(C - cam.O))
    rpx = math.tan(math.asin(min(r / dist, 0.999))) / PIX
    x0 = int(max(0, cx[0] - rpx - 3)); x1 = int(min(W, cx[0] + rpx + 4))
    y0 = int(max(0, cy[0] - rpx - 3)); y1 = int(min(H, cy[0] + rpx + 4))
    if x0 >= x1 or y0 >= y1:
        return
    d = cam.dirs(y0, y1, x0, x1)
    oc = cam.O - C
    b = d @ oc
    perp2 = np.maximum(float(oc @ oc) - b * b, 0)
    dd = np.sqrt(perp2)
    alpha = np.clip((r - dd) / (np.maximum(-b, 1e-9) * PIX) + 0.5, 0, 1) * (b < 0)
    sel = alpha > 0
    if not sel.any():
        return
    tt = -b[sel] - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = cam.O + tt[:, None] * d[sel]
    n = (P - C) / r
    la, lo = latlon(n)
    nz = fbm(n[:, 0] * 2.5 + 7, n[:, 1] * 2.5 + 3, n[:, 2] * 2.5, 5, seed=seed)
    tex = np.clip(0.55 + 0.9 * (nz - 0.5) + 0.25 * (nz > 0.58), 0.3, 1.25)
    col = lin(base) * tex[:, None] * (0.02 + 1.9 * np.clip(n @ LIGHT, 0, 1))[:, None]
    region = img[y0:y1, x0:x1]
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


# --- línea de tiempo ---
FIRST = ["gancho", "hoy", "v4", "edificio", "motores", "combustible", "luna", "cierre"]
SHOTS = [("gancho", 0.0)] + [(k, S0[k] - 0.2) for k in FIRST[1:]]
FL = [b for _, b in SHOTS[1:]]
TGROW0, TGROW1 = 4.25, 6.6            # la nave se estira en el gancho
TV4 = (S0["v4"] + 0.4, 17.5)          # 52 → 70 m
TDOWN = 22.85                         # "…y es solo la parte de arriba"
TADD = 27.75                          # se agregan 3 Raptor de vacío
TPLAN = 44.75                         # "Pero si se cumple…"


def scene(t):
    name = SHOTS[0][0]
    for a, b in SHOTS:
        if t >= b:
            name = a
    return name


def t0_of(name):
    return dict(SHOTS)[name]


def t1_of(name):
    i = [a for a, _ in SHOTS].index(name)
    return SHOTS[i + 1][1] if i + 1 < len(SHOTS) else END


def U(t, name):
    a, b = t0_of(name), t1_of(name)
    return min(max((t - a) / (b - a), 0.0), 1.0)


def grow_L(t):
    return 52.0 + 18.0 * ease((t - TGROW0) / (TGROW1 - TGROW0))


V4L = lambda t: 52.0 + 18.0 * ease((t - TV4[0]) / (TV4[1] - TV4[0]))
RFLIP = rotm(math.pi)               # panza (losetas negras) hacia +x


# 1 · gancho: la nave en los brazos de la torre… y se estira
def sc_gancho(img, t):
    s = ease(min(t / 8.0, 1.0))
    cam = Cam((52 - 12 * s, 8 + 4 * s, 150 - 22 * s), (-6, 92 + 6 * s, 0))
    draw_world(img, cam, "day")
    L = grow_L(t)
    f = []
    tower(f); arms(f, 102, 0.0); launch_mount(f)
    k = smooth(TGROW0 - 0.2, TGROW0 + 0.3, t) * (1 - smooth(TGROW1, TGROW1 + 0.8, t))
    shipL(f, (0, 60, 0), RFLIP, L, emit=(1.6, 1.3, 0.4))
    draw_faces(img, cam, f, "day", glow_emit=0.07 * k)
    return cam, {"L": L}


# 2 · hoy: la nave actual de pie sobre la plataforma
def sc_hoy(img, t):
    u = ease(U(t, "hoy"))
    ang = 0.55 - 0.30 * u
    rad = 150 - 18 * u
    cam = Cam((math.sin(ang) * rad, 14 + 6 * u, math.cos(ang) * rad), (0, 31, 0))
    draw_world(img, cam, "day")
    f = []
    shipL(f, (0, 0, 0), RFLIP, 52.0)
    draw_faces(img, cam, f, "day")
    return cam, {}


# 3 · v4: la actual y la V4 lado a lado; la V4 crece de 52 a 70 m
def sc_v4(img, t):
    u = ease(U(t, "v4"))
    cam = Cam((40 - 30 * u, 12 + 8 * u, 175 - 10 * u), (0, 38, 0))
    draw_world(img, cam, "day")
    f = []
    shipL(f, (-10, 0, 0), RFLIP, 52.0)
    shipL(f, (10, 0, 0), RFLIP, V4L(t), emit=(1.4, 1.2, 0.4))
    k = smooth(TV4[0] - 0.1, TV4[0] + 0.3, t) * (1 - smooth(TV4[1], TV4[1] + 0.6, t))
    draw_faces(img, cam, f, "day", glow_emit=0.07 * k)
    return cam, {"L": V4L(t)}


# 4 · edificio: la V4 junto a un edificio de 23 pisos; luego aparece el propulsor debajo
def sc_edificio(img, t):
    u = ease(U(t, "edificio"))
    s = ease((t - TDOWN) / 1.1)
    dist = 200 + 140 * s
    look = 36 + 40 * s
    ang = -0.35 + 0.15 * u
    cam = Cam((math.sin(ang) * dist + 2, 10 + 25 * s, math.cos(ang) * dist), (0, look, 0))
    draw_world(img, cam, "dusk" if False else "day")
    f = []
    building(f, -16, 0, 18, 23)
    fs = []
    lift = 71.0 * s
    shipL(fs, (14, lift, 0), RFLIP, 70.0)
    if s > 0:
        booster(fs, (14, lift - 71.0, 0), RFLIP)
        fs = clamp_ground(fs)
    draw_faces(img, cam, f + fs, "day")
    return cam, {"s": s}


# 5 · motores: vista desde abajo; de 6 a 9 motores que se encienden
def sc_motores(img, t):
    u = ease(U(t, "motores"))
    cam = Cam((2.5 - 1.5 * u, -36 + 6 * u, 4 - 1.5 * u), (0, 0, 0), roll=0.6 * u)
    nvac = 3 if t < TADD else 6
    add = ease((t - TADD) / 0.6)
    f = []
    cyl(f, np.eye(3), np.zeros(3), 0, 14, RB_, RB_, col=STEEL, n=40)
    disk(f, np.eye(3), np.zeros(3), 0.0, RB_, STEEL_D, 40, True)
    hot = []
    lay = engine_layout(nvac)
    for i, (x, z, r, ln) in enumerate(lay):
        new = nvac == 6 and i in (4, 6, 8)
        if new:
            drop = (1 - add) * 6.0
        else:
            drop = 0.0
        p = np.array([x, -drop, z])
        cyl(f, np.eye(3), p, -ln, 0, r, r * 0.45, col=(0.30, 0.30, 0.33), n=18, spec=0.7)
        if i < 3:
            ign = smooth(S0["motores"] + 0.3 + 0.25 * i, S0["motores"] + 0.6 + 0.25 * i, t)
        elif not new:
            ign = smooth(S0["motores"] + 1.2 + 0.25 * (i - 3), S0["motores"] + 1.5 + 0.25 * (i - 3), t)
        else:
            j = (4, 6, 8).index(i)
            ign = smooth(TADD + 0.7 + 0.3 * j, TADD + 1.0 + 0.3 * j, t)
        disk(f, np.eye(3), p, -ln, r * 0.98, (0.05, 0.05, 0.06), 18, True, emit=tuple(np.array((1.7, 1.1, 0.55)) * ign) if ign > 0.05 else None)
        hot.append((p + np.array([0, -ln - 0.3, 0]), r, ign, new))
    draw_faces(img, cam, f, "space", glow_emit=1.0)
    rng = np.random.default_rng(int(t * FPS))
    for c, r, ign, new in hot:
        if ign <= 0.02:
            continue
        m = 500
        q = rng.random(m)
        th = rng.random(m) * 2 * math.pi
        rr = r * (0.2 + 0.9 * q) * rng.random(m) ** 0.5
        P = c + np.stack([rr * np.cos(th), -q * 9.0, rr * np.sin(th)], -1)
        col = np.array([2.4, 1.9, 1.5]) * np.exp(-q * 2.5)[:, None] + np.array([0.6, 0.3, 0.9]) * (q[:, None] * 0.3)
        splat2(img, cam, P, (col * (30.0 / m) * ign).astype(np.float32), 2.2, 0.15)
    return cam, {"hot": hot, "nvac": nvac}


# 6 · combustible: la actual y la V4 en órbita, con los tanques llenándose
def sc_combustible(img, t):
    u = ease(U(t, "combustible"))
    cpos = np.array([18 - 14 * u, 34.0, 150 - 15 * u])
    cam_m = Cam(cpos, (0, 33, 0))
    S_km = np.array([0.0, RE_KM + 420.0, 0.0])
    tgt = S_km + (np.array([0, 33, 0]) - cpos) / 1000.0
    cam_km = Cam(S_km + cpos / 1000.0, S_km + cpos / 1000.0 + unit(cam_m.f + np.array([0, -0.06, 0])))
    draw_earth(img, cam_km, np.zeros(3), RE_KM, 210 + t * 2.0, atm=0.004, glow=0.9)
    f = []
    shipL(f, (-11, 0, 0), RFLIP, 52.0)
    shipL(f, (11, 0, 0), RFLIP, 70.0)
    draw_faces(img, cam_m, f, "space")
    return cam_m, {}


# 7 · luna: vuelos de recarga que suben a un depósito en órbita; con la V4 hacen falta menos
MOON_C = np.array([1382.0, 8771.0, -12235.0])
DEPOT_R = RE_KM + 2600.0


def sc_luna(img, t):
    u = ease(U(t, "luna"))
    cam = Cam(np.array([14000.0, 9000.0, 32000.0]) * (1.04 - 0.06 * u), (1500.0, 6750.0, 0))
    draw_earth(img, cam, np.zeros(3), RE_KM, 260 + 6 * u, atm=0.02, glow=0.85)
    draw_ball(img, cam, MOON_C, 1737.0 * 2.2, (0.62, 0.61, 0.60))
    return cam, {"u": u}


# 8 · cierre: atardecer en Starbase con la torre, la nave actual y la V4
def sc_cierre(img, t):
    u = ease(U(t, "cierre"))
    ang = 0.95 - 0.45 * u
    rad = 260 - 50 * u
    cam = Cam((math.sin(ang) * rad - 10, 8 + 10 * u, math.cos(ang) * rad), (-4, 56 + 10 * u, 0))
    draw_world(img, cam, "dusk")
    f = []
    tower(f); launch_mount(f)
    shipL(f, (24, 0, -8), RFLIP, 52.0)
    shipL(f, (24, 0, 16), RFLIP, 70.0)
    draw_faces(img, cam, f, "dusk")
    return cam, {}


SCENES = {"gancho": sc_gancho, "hoy": sc_hoy, "v4": sc_v4, "edificio": sc_edificio, "motores": sc_motores,
          "combustible": sc_combustible, "luna": sc_luna, "cierre": sc_cierre}
MODES = {"motores": "space", "combustible": "space", "luna": "space", "cierre": "dusk"}


def visible(cam, P, C=np.zeros(3), r=RE_KM):
    d = P - cam.O; Ln = np.linalg.norm(d); d = d / Ln
    oc = cam.O - C; b = d @ oc; c = oc @ oc - r * r
    disc = b * b - c
    if disc <= 0:
        return True
    tt = -b - math.sqrt(disc)
    return tt <= 0 or tt >= Ln - 1.0


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def poly3d(d, cam, P_list, col, A, width=6, occl=True):
    prev = None
    for P in P_list:
        x, y, z = pt(cam, P)
        cur = (x, y) if (z > 0 and (not occl or visible(cam, P))) else None
        if prev and cur:
            d.line([prev, cur], fill=col + (A,), width=width)
        prev = cur


def ruler(d, cam, x, z, top, A, col=CYAN, step=10, value=None, side=1):
    """Regla vertical en el mundo (metros) junto a una nave."""
    xb, yb, _ = pt(cam, (x, 0, z)); xt, yt, _ = pt(cam, (x, top, z))
    d.line([(xb, yb), (xt, yt)], fill=col + (A,), width=6)
    for m in range(0, int(top) + 1, step):
        xm, ym, _ = pt(cam, (x, m, z))
        d.line([(xm, ym), (xm + side * 22, ym)], fill=col + (A,), width=5)
    d.line([(xt - 26, yt), (xt + 26, yt)], fill=col + (A,), width=7)
    if value:
        txt(d, (xt + side * 40, yt), value, 64, YELLOW if col == YELLOW else WHITE, A, "Inter-Black.otf", 8, "lm" if side > 0 else "rm")


def overlays(frame_u8, t, name, cam, ex):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0 = t0_of(name); a1 = t1_of(name)
    if name == "gancho":
        draw_label(layer, t, 0.15, TGROW0 - 0.1, "¡ATRAPADA!", ["sábado 14 nov · Starbase"], YELLOW, 140)
        draw_label(layer, t, TGROW0, a1 + 0.05, "¿MÁS GRANDE?", ["el nuevo plan de Musk"], WHITE, 130)
        A = int(255 * fade(t, TGROW0 - 0.1, a1 + 0.05))
        if A > 0:
            ruler(d, cam, 9, 0, 60 + ex["L"], A, YELLOW, value=None) if False else None
            x, y, _ = pt(cam, (0, 60 + ex["L"], 0))
            glow(layer, x, y, 70, YELLOW, int(160 * A / 255 * smooth(TGROW0, TGROW0 + 0.4, t) * (1 - smooth(TGROW1, TGROW1 + 0.5, t))))
    elif name == "hoy":
        mid = SPLIT("hoy", 0.5)
        draw_label(layer, t, a0 + 0.15, mid, "STARSHIP HOY", ["la nave de arriba (V3)"], WHITE, 120)
        draw_label(layer, t, mid, a1 + 0.05, "6 MOTORES", ["Raptor"], CYAN, 124)
        A = int(255 * fade(t, a0 + 0.3, a1))
        if A > 0:
            grow = ease((t - a0 - 0.3) / 1.2)
            ruler(d, cam, 9, 0, 52 * grow, A, CYAN, value=f"{52 * grow:.0f} m")
    elif name == "v4":
        mid = TV4[1]
        draw_label(layer, t, a0 + 0.15, mid, "STARSHIP V4", ["el plan de la próxima versión"], YELLOW, 124)
        draw_label(layer, t, mid, a1 + 0.05, "+40 %", ["más larga (casi)"], YELLOW, 150)
        A = int(255 * fade(t, a0 + 0.2, a1))
        if A > 0:
            Lv = ex["L"]
            ruler(d, cam, -20, 0, 52, A, CYAN, value="52 m", side=-1)
            ruler(d, cam, 20, 0, Lv, A, YELLOW, value=f"{Lv:.0f} m", side=1)
            x0, y0, _ = pt(cam, (-20, 52, 0)); x1, y1, _ = pt(cam, (20, 52, 0))
            for k in range(0, 20):
                xa = x0 + (x1 - x0) * k / 20; xb = x0 + (x1 - x0) * (k + 0.5) / 20
                ya = y0 + (y1 - y0) * k / 20; yb = y0 + (y1 - y0) * (k + 0.5) / 20
                d.line([(xa, ya), (xb, yb)], fill=WHITE + (int(A * 0.7),), width=4)
            xh, yh, _ = pt(cam, (-10, 0, 0)); txt(d, (xh, yh + 45), "HOY", 50, CYAN, A, "Inter-Black.otf", 7)
            xh, yh, _ = pt(cam, (10, 0, 0)); txt(d, (xh, yh + 45), "V4", 54, YELLOW, A, "Inter-Black.otf", 7)
    elif name == "edificio":
        s = ex["s"]
        draw_label(layer, t, a0 + 0.15, TDOWN, "= 23 PISOS", ["unos 70 m de altura"], YELLOW, 130)
        draw_label(layer, t, TDOWN, a1 + 0.05, "SOLO LA NAVE", ["abajo va el propulsor"], WHITE, 124)
        A = int(255 * fade(t, a0 + 0.3, TDOWN + 0.1))
        if A > 0:
            n = 1 + min(22, int(23 * ease((t - a0 - 0.3) / 1.8)))
            xb, yb, _ = pt(cam, (-16, max(n * 3.0 - 5, 2), 9))
            txt(d, (xb, yb), f"{n}", 72, YELLOW, A, "Inter-Black.otf", 8)
            for k in range(n):
                xa, ya, _ = pt(cam, (-25.2, k * 3.0 + 1.5, 9)); xc, yc, _ = pt(cam, (-6.8, k * 3.0 + 1.5, 9))
            ruler(d, cam, 24, 0, 70, A, YELLOW, value="70 m")
        A2 = int(255 * fade(t, TDOWN + 0.9, a1))
        if A2 > 0:
            x, y, _ = pt(cam, (14, 71 + 35, 0)); marker(d, x, y, t, YELLOW, A2, 40, "NAVE", -1, 48)
            x, y, _ = pt(cam, (14, 52, 0)); marker(d, x, y, t, CYAN, A2, 40, "PROPULSOR", -1, 48)
    elif name == "motores":
        draw_label(layer, t, a0 + 0.15, TADD, "6 MOTORES", ["3 normales + 3 de vacío"], WHITE, 124)
        draw_label(layer, t, TADD, a1 + 0.05, "9 MOTORES", ["+3 Raptor de vacío, más potentes"], YELLOW, 140)
        A = int(255 * fade(t, TADD + 0.4, a1))
        if A > 0:
            for c, r, ign, new in ex["hot"]:
                if new:
                    x, y, _ = pt(cam, c + np.array([0, 3.0, 0]))
                    marker(d, x, y, t, YELLOW, A, 58)
        txt(d, (W / 2, 1830), "recreación · vista desde abajo", 34, (220, 225, 235), int(200 * fade(t, a0, a1)), "Inter-ExtraBold.otf", 5)
    elif name == "combustible":
        draw_label(layer, t, a0 + 0.15, a1 + 0.05, "+60 %", ["más combustible"], YELLOW, 160)
        A = int(255 * fade(t, a0 + 0.2, a1))
        if A > 0:
            for xs_, Ls, colr, lab in ((-11, 52.0, CYAN, "HOY"), (11, 70.0, YELLOW, "V4")):
                xb_, yb_, _ = pt(cam, (xs_, 2.0, 0)); xt_, yt_, _ = pt(cam, (xs_, Ls - 18.0, 0))
                xr, _, _ = pt(cam, (xs_ + RB_ * 0.8, 2.0, 0))
                hw = abs(xr - xb_)
                fill = ease((t - a0 - 0.4) / 2.2)
                yf = yb_ + (yt_ - yb_) * fill
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(ov).rectangle([xb_ - hw, yf, xb_ + hw, yb_], fill=(255, 150, 50, int(150 * A / 255)))
                layer.alpha_composite(ov)
                d.rectangle([xb_ - hw, yt_, xb_ + hw, yb_], outline=colr + (A,), width=6)
                txt(d, (xb_, yb_ + 50), lab, 54, colr, A, "Inter-Black.otf", 7)
        txt(d, (W / 2, 1830), "recreación · tanques ilustrativos", 34, (220, 225, 235), int(200 * fade(t, a0, a1)), "Inter-ExtraBold.otf", 5)
    elif name == "luna":
        u = ex["u"]; tl = (t - a0)
        mid = SPLIT("luna", 0.30)
        draw_label(layer, t, a0 + 0.15, mid, "MÁS POR VIAJE", ["cada vuelo lleva más combustible"], WHITE, 120)
        draw_label(layer, t, mid, a1 + 0.05, "MENOS VUELOS", ["para ir a la Luna"], YELLOW, 130)
        A = int(255 * fade(t, a0 + 0.1, a1))
        # depósito en órbita (punto fijo en pantalla, a 9,500 km del centro de la Tierra)
        def hit(px, py, rad):
            dx = ((px + 0.5) / W * 2 - 1) * TX; dy = (1 - (py + 0.5) / H * 2) * TY
            dv = unit(dx * cam.r + dy * cam.u + cam.f)
            bb = dv @ cam.O; cc = cam.O @ cam.O - rad * rad
            disc = bb * bb - cc
            return cam.O + dv * (-bb - math.sqrt(max(disc, 0)))
        dep = hit(250, 900, 9500.0)
        rr_ = np.linalg.norm(dep); e1 = dep / rr_; e2 = unit(np.cross(e1, cam.u)); 
        orbit = [math.cos(a_) * e1 * rr_ + math.sin(a_) * e2 * rr_ for a_ in np.linspace(0, 2 * math.pi, 140)]
        poly3d(d, cam, orbit, CYAN, int(A * 0.45), 3)
        if t < mid:
            flights, dt_, colf, wdt = 6, (mid - a0 - 0.5) / 6, CYAN, 6
            start = a0 + 0.3
        else:
            flights, dt_, colf, wdt = 3, (a1 - mid - 1.8) / 3, YELLOW, 11
            start = mid + 0.2
        pads = [(430, 1180), (640, 1260), (330, 1420), (560, 1460), (760, 1380), (470, 1320)]
        for i in range(flights):
            ts = start + i * dt_
            if t < ts:
                continue
            k = min(1.0, (t - ts) / 0.8)
            P0 = hit(*pads[i % len(pads)], RE_KM)
            Cc = unit(P0 + dep) * (np.linalg.norm(dep) * 1.05)
            pts = [(1 - s_) ** 2 * P0 + 2 * (1 - s_) * s_ * Cc + s_ ** 2 * dep for s_ in np.linspace(0, k, 30)]
            poly3d(d, cam, pts, colf, int(A * (1.0 if k < 1 else 0.45)), wdt, occl=False)
            if k < 1:
                x, y, _ = pt(cam, pts[-1]); glow(layer, x, y, 26 if wdt < 8 else 40, colf, int(230 * A / 255))
        x, y, _ = pt(cam, dep)
        glow(layer, x, y, 50, CYAN, int(200 * A / 255))
        marker(d, x, y, t, WHITE, A, 26, "DEPÓSITO", 1, 42)
        # al final, una nave sale hacia la Luna
        if t > a1 - 1.5:
            k = ease((t - (a1 - 1.5)) / 1.3)
            pts = [dep + (MOON_C - dep) * s * k + np.array([0, 2500 * math.sin(math.pi * s * k), 0]) for s in np.linspace(0, 1, 30)]
            poly3d(d, cam, pts, YELLOW, A, 6, occl=False)
        xm, ym, _ = pt(cam, MOON_C); txt(d, (xm, ym + 260), "LUNA", 48, WHITE, A, "Inter-Black.otf", 7)
        txt(d, (W / 2, 1830), "recreación · no está a escala", 34, (220, 225, 235), int(200 * fade(t, a0, a1)), "Inter-ExtraBold.otf", 5)
    elif name == "cierre":
        draw_label(layer, t, a0 + 0.15, TPLAN, "SOLO UN PLAN", ["sin fecha para su primer vuelo"], WHITE, 124)
        draw_label(layer, t, TPLAN, CARD + 0.1, "AÚN MÁS GRANDE", ["si se cumple"], YELLOW, 100)
        A = int(255 * fade(t, a0 + 0.4, CARD))
        if A > 0:
            x, y, _ = pt(cam, (24, 58, -8)); txt(d, (x, y - 20), "HOY", 44, CYAN, A, "Inter-Black.otf", 7)
            x, y, _ = pt(cam, (24, 76, 16)); txt(d, (x, y - 20), "V4", 50, YELLOW, A, "Inter-Black.otf", 7)
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
    global LIGHT
    name = scene(t)
    mode = MODES.get(name, "day")
    LIGHT = unit(LIGHTS[mode]["L"])
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
