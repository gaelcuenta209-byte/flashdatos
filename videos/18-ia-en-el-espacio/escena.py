"""Flash Datos · video 18: Google puso una IA en el espacio y respondió con un poema (Proyecto Suncatcher).

Escena nueva: satélite con alas solares que se despliega de la etapa superior del cohete, un chip de IA
que se ilumina por dentro, la orden subiendo desde una antena en Tierra como pulsos cian, la luz del Sol
cargando los paneles, el paso sobre Svalbard con la respuesta bajando como haz amarillo, una tarjeta con
el haiku, la constelación de centros de datos en órbita y los dos satélites de 2027 unidos por láser.

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

def draw_earth(img, cam, C, r, t, atm=0.03, glow=0.55, tilt=math.radians(16), spin=-1.72):
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
    alpha = np.clip((r - dd) / pixw + 0.5, 0, 1)
    region = img[y0:y1, x0:x1]
    hz = (dd > r * 0.995) & (dd < r * (1.0 + 4 * atm))
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
    loc = rot_y(rot_x(n, tilt), spin + 0.01 * t)
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
ORDER = ["hook1", "lanzamiento", "orden", "gemma", "svalbard", "poema", "plan", "cierre"]
FL = [S0[k] - 0.2 for k in ORDER[1:]]
CARD = S1["cierre"] + 0.15
SPLIT = lambda k, f: S0[k] + (S1[k] - S0[k]) * f

FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); RED = (255, 90, 70); ORANGE = (255, 160, 70)
HL_WORDS = {"google", "planet", "ia", "gemma", "haiku", "svalbard"}


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
    txt(d, (W / 2, 1185), "de ciencia y tecnología", 52, CYAN, A, "Inter-ExtraBold.otf", 6)


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


# ---------------- satélite, chip y efectos del video 18 ----------------
R_E = 6371.0
M = 0.001  # un metro en km


def sat_boxes(pos, R, s=M, wing=1.0, glow_body=0.0):
    """Satélite tipo Suncatcher (estilizado): bus, dos alas de 3 paneles, radiador, mástil y antena."""
    pos = np.asarray(pos, float)
    gold = (214, 170, 78); silver = (196, 200, 210); panel = (30, 58, 132); white = (232, 234, 240); dark = (56, 60, 72)
    body = tuple(int(min(255, c + (90 - c * 0.3) * glow_body)) for c in silver)
    out = [(pos, (0.60 * s, 0.45 * s, 0.45 * s), R, body),
           (pos + R @ np.array([0, 0, 0.47 * s]), (0.50 * s, 0.36 * s, 0.03 * s), R, gold),
           (pos + R @ np.array([0, -0.47 * s, 0]), (0.45 * s, 0.03 * s, 0.38 * s), R, white),
           (pos + R @ np.array([0, 0.75 * s, 0]), (0.04 * s, 0.32 * s, 0.04 * s), R, dark),
           (pos + R @ np.array([0, 1.08 * s, 0]), (0.30 * s, 0.03 * s, 0.30 * s), R, white)]
    for side in (-1, 1):
        out.append((pos + R @ np.array([side * 0.72 * s, 0, 0]), (0.12 * s, 0.04 * s, 0.04 * s), R, dark))
        for k in range(3):
            x = side * (0.84 + (1.14 * k + 0.56) * wing) * s
            y = (1 - wing) * k * 0.05 * s
            out.append((pos + R @ np.array([x, y, 0]), (0.55 * s, 0.025 * s, 0.42 * s), R, panel))
    return out


def stage_boxes(pos, R, s=M):
    s = s * 0.7
    return [(np.asarray(pos, float), (0.95 * s, 0.95 * s, 2.2 * s), R, (210, 212, 220)),
            (np.asarray(pos, float) + R @ np.array([0, 0, -2.5 * s]), (0.7 * s, 0.7 * s, 0.35 * s), R, (70, 72, 84))]


def orient_for(lat, lon, target):
    """tilt y spin de draw_earth para que (lat, lon) quede apuntando a 'target' (mundo)."""
    target = np.asarray(target, float); target /= np.linalg.norm(target)
    la, lo = math.radians(lat), math.radians(lon)
    loc = np.array([math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)])
    best = (9, 0, 0)
    for a in np.linspace(-1.55, 1.55, 125):
        for b in np.linspace(-math.pi, math.pi, 241):
            n = rot_x(rot_y(loc, -b), -a)
            e = float(np.sum((n - target) ** 2))
            if e < best[0]:
                best = (e, a, b)
    return best[1], best[2]


def beam(img, cam, A, B, t, col, speed=1.6, n=500, pulses=5, k=1.0, frac=1.0):
    """Haz con pulsos que viajan de A a B (HDR)."""
    if k <= 0:
        return
    u = np.linspace(0, 1, n) * frac
    P = np.asarray(A)[None, :] * (1 - u[:, None]) + np.asarray(B)[None, :] * u[:, None]
    ph = (u * pulses - t * speed) % 1.0
    inten = 0.10 + 1.6 * np.exp(-((ph - 0.5) ** 2) / 0.01)
    c = np.asarray(col)[None, :] * (inten * k)[:, None] * 0.35
    splat(img, cam, P, c, 1.0)


def draw_chip(layer, cx, cy, size, A, pulse=0.0, label="TPU"):
    d = ImageDraw.Draw(layer)
    glow(layer, cx, cy, size * (1.1 + 0.25 * pulse), CYAN, int(A * (0.45 + 0.35 * pulse)))
    h = size / 2
    pin = size * 0.08
    for i in range(7):
        o = -h + size * (i + 0.5) / 7
        for (x0, y0, x1, y1) in [(cx + o - pin / 2, cy - h - pin * 2, cx + o + pin / 2, cy - h),
                                 (cx + o - pin / 2, cy + h, cx + o + pin / 2, cy + h + pin * 2),
                                 (cx - h - pin * 2, cy + o - pin / 2, cx - h, cy + o + pin / 2),
                                 (cx + h, cy + o - pin / 2, cx + h + pin * 2, cy + o + pin / 2)]:
            d.rectangle([x0, y0, x1, y1], fill=(220, 180, 90, A))
    d.rounded_rectangle([cx - h, cy - h, cx + h, cy + h], size * 0.08, fill=(18, 24, 38, A), outline=CYAN + (A,), width=5)
    g = size * 0.36
    for i in range(4):
        for j in range(4):
            on = (math.sin(i * 1.7 + j * 2.3 + pulse * 9) + 1) / 2
            x = cx - g + (i + 0.5) * g / 2; y = cy - g + (j + 0.5) * g / 2
            c = tuple(int(30 + (v - 30) * (0.3 + 0.7 * on * (0.4 + 0.6 * pulse))) for v in CYAN)
            d.rectangle([x - g / 5, y - g / 5, x + g / 5, y + g / 5], fill=c + (A,))
    txt(d, (cx, cy + h + size * 0.32), label, int(size * 0.24), WHITE, A, "Inter-Black.otf", 6)


def terminal(layer, t, a, b, text, y0=330):
    al = fade(t, a, b, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    f = font("Inter-ExtraBold.otf", 52)
    n = int(len(text) * min(1.0, max(0.0, (t - a - 0.2) / 2.2)))
    shown = text[:n]
    words = shown.split(" ")
    lines, cur = [], ""
    for w in words:
        if d.textlength((cur + " " + w).strip(), font=f) > W - 260:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    hgt = 120 + 70 * max(2, len(lines))
    d.rounded_rectangle([90, y0, W - 90, y0 + hgt], 28, fill=(8, 14, 28, int(215 * al)), outline=CYAN + (A,), width=5)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([130 + i * 44, y0 + 30, 156 + i * 44, y0 + 56], fill=c + (A,))
    txt(d, (W - 130, y0 + 43), "TIERRA → SATÉLITE", 30, CYAN, A, "Inter-ExtraBold.otf", 0, "rm")
    for i, ln in enumerate(lines):
        pre = "> " if i == 0 else "  "
        cur_ = "▌" if (i == len(lines) - 1 and int(t * 3) % 2 == 0) else ""
        d.text((130, y0 + 110 + i * 70), pre + ln + cur_, font=f, fill=WHITE + (A,), anchor="lm")


POEM_ES = ["Canica azul abajo.", "Datos que fluyen en silencio.", "La luz de las estrellas", "alimenta mi núcleo."]
POEM_EN = "Blue marble below / Data streams in silent grace / Starlight feeds my core"


def poem_card(layer, t):
    a, b = S0["poema"] - 0.1, FL[6] + 0.05
    al = fade(t, a, b, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    y0 = 300
    d.rounded_rectangle([70, y0, W - 70, y0 + 690], 34, fill=(8, 12, 26, int(200 * al)), outline=YELLOW + (A,), width=6)
    txt(d, (W / 2, y0 + 70), "LA RESPUESTA DESDE ÓRBITA", 44, YELLOW, A, "Inter-Black.otf", 0)
    starts = [SPLIT("poema", 0.14), SPLIT("poema", 0.40), SPLIT("poema", 0.66), SPLIT("poema", 0.78)]
    for i, (ln, ts) in enumerate(zip(POEM_ES, starts)):
        k = ease_out((t - ts) / 0.4)
        if k <= 0:
            continue
        col = YELLOW if i in (0, 2) else WHITE
        txt(d, (W / 2, y0 + 175 + i * 100 + (1 - k) * 20), ln, 64, col, int(A * k), "Inter-Black.otf", 6)
    k = fade(t, SPLIT("poema", 0.2), 99, 0.4)
    txt(d, (W / 2, y0 + 565), "Original en inglés (Gemma 4):", 30, CYAN, int(A * k), "Inter-ExtraBold.otf", 0)
    txt(d, (W / 2, y0 + 600), "Blue marble below / Data streams in silent grace /", 30, (200, 214, 235), int(A * k), "Inter-ExtraBold.otf", 0)
    txt(d, (W / 2, y0 + 640), "Starlight feeds my core", 30, (200, 214, 235), int(A * k), "Inter-ExtraBold.otf", 0)


def sun_glow(img, cam, k=1.0):
    sun = cam.O + LIGHT * 1.0e6
    splat(img, cam, sun[None, :], np.array([[3.0, 2.6, 1.9]]) * 70 * k, 1.0)
    return sun


def scene(t):
    for i, tf in enumerate(FL):
        if t < tf:
            return ORDER[i]
    return ORDER[-1]


def cam_close(P, off, look=(0.0, 0.0, 0.0), roll=0.0):
    return Cam(P + np.asarray(off) * M, P + np.asarray(look) * M, roll)


def segk(name, t):
    i = ORDER.index(name)
    a = 0.0 if i == 0 else FL[i - 1]
    b = FL[i] if i < len(FL) else END
    return (t - a) / (b - a)


P_SAT = np.array([0.0, R_E + 560.0, 0.0])
T_SPLIT_LAN = SPLIT("lanzamiento", 0.50)
T_PLAN2 = SPLIT("plan", 0.36)
T_PLAN3 = SPLIT("plan", 0.66)
FL_EXTRA = [T_PLAN3 - 0.2]

# orientación de la Tierra para el paso sobre Svalbard (78.2° N, 15.6° E)
SV_N = np.array([0.10, 0.62, 0.78]); SV_N /= np.linalg.norm(SV_N)
SV_TILT, SV_SPIN = orient_for(78.2, 15.6, SV_N)
SV_P = SV_N * R_E


def sc_hook1(img, t):
    k = segk("hook1", t)
    cam = cam_close(P_SAT, (-3.0 + 3.0 * k, 2.4, 10.5 - 2.0 * k), (0.0, -1.2, 0.0), 0.04)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    return cam, dict(sats=[(P_SAT, rotm(0.4 + 0.12 * t, 0.25, 0.1), M, 1.0, 0.3 + 0.3 * math.sin(t * 4))])


def sc_lanzamiento(img, t):
    k = segk("lanzamiento", t)
    if t < T_SPLIT_LAN:
        s = (t - FL[0]) / (T_SPLIT_LAN - FL[0])
        cam = cam_close(P_SAT, (9.0, 2.0, 12.0), (-0.3, 0.5, -1.6), 0.0)
        draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
        R = rotm(0.0, 0.0, 0.0)
        sep = ease((s - 0.12) / 0.6)
        stage = P_SAT + np.array([0, 0, -2.6 - 2.4 * sep]) * M
        sat = P_SAT + np.array([0, 0.1 * sep, 0.6 * sep]) * M
        wing = ease((s - 0.5) / 0.45)
        return cam, dict(sats=[(sat, rotm(0.15 * sep, 0.1 * sep, 0.0), M, wing, 0.0)], stage=(stage, R))
    s = (t - T_SPLIT_LAN) / (FL[1] - T_SPLIT_LAN)
    cam = cam_close(P_SAT, (2.0 - 1.5 * s, 1.6, 7.5 - 1.4 * ease(s)), (0.0, 1.9, 0.0), 0.0)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    return cam, dict(sats=[(P_SAT, rotm(0.25 + 0.05 * t, 0.12, 0.0), M, 1.0, 0.6 + 0.4 * math.sin(t * 6))], chip=s)


G_N = np.array([-0.18, 0.30, 0.94]); G_N /= np.linalg.norm(G_N)
G_P = G_N * R_E
ORD_SAT = G_N * (R_E + 2300.0) + np.array([2600.0, 900.0, 0.0])
BIG = 160.0   # escala exagerada del satélite en vistas lejanas (km por "metro")


def sc_orden(img, t):
    k = segk("orden", t)
    cpos = np.array([1200.0, 5200.0, 21500.0 - 1500 * k])
    cam = Cam(cpos, np.array([900.0, 2600.0, 0.0]))
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.014, 0.9)
    tb = SPLIT("orden", 0.25)
    beam(img, cam, G_P, ORD_SAT, t, np.array([0.5, 1.6, 2.6]) * 2.2, 1.4, 600, 6, ease((t - tb) / 0.4), min(1.0, ease((t - tb) / 1.0) + 1e-3))
    splat(img, cam, G_P[None, :], np.array([[0.6, 1.8, 2.8]]) * (8 + 4 * math.sin(t * 8)), 1.0)
    return cam, dict(sats=[(ORD_SAT, rotm(0.6, 0.3, 0.2), BIG, 1.0, 0.0)], G=G_P)


def sc_gemma(img, t):
    k = segk("gemma", t)
    perp = np.cross(LIGHT, [0, 1.0, 0]); perp /= np.linalg.norm(perp)
    cam = cam_close(P_SAT, (-4.5 + 2.0 * k, 1.2, 7.5 - 1.0 * k), (0.0, 0.3, 0.0), -0.04)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    rng = np.random.default_rng(4)
    n = 500
    u = (rng.random(n) + t * 0.9) % 1.0
    side = np.where(rng.random(n) < 0.5, -1.0, 1.0)
    tgt = P_SAT[None, :] + np.stack([side * (1.0 + 2.8 * rng.random(n)), rng.normal(size=n) * 0.03, (rng.random(n) - 0.5) * 0.8], -1) * M
    src = tgt + LIGHT[None, :] * (8.0 * M) + rng.normal(size=(n, 3)) * 1.2 * M
    P = src * (1 - u[:, None]) + tgt * u[:, None]
    col = np.broadcast_to(np.array([2.6, 2.0, 0.8]) * 0.30, (n, 3)) * np.sin(u * math.pi)[:, None]
    splat(img, cam, P, col, 1.0)
    think = 0.5 + 0.5 * math.sin(t * 9)
    return cam, dict(sats=[(P_SAT, rotm(0.2, 0.1, 0.0), M, 1.0, 0.4 + 0.6 * think)], think=think)


def sv_sat_pos(t):
    s = (t - FL[3]) / (FL[4] - FL[3])
    tang = np.cross(SV_N, [0, 0, 1.0]); tang /= np.linalg.norm(tang)
    upv = np.array([0.0, 1.0, 0.0]) - SV_N * SV_N[1]; upv /= np.linalg.norm(upv)
    return SV_P + SV_N * 700.0 + upv * 1350.0 + tang * (-3000 + 6000 * s), s


def sc_svalbard(img, t):
    k = segk("svalbard", t)
    cpos = SV_N * (R_E + 13500.0 - 1500 * k) + np.array([0.0, -2600.0, 1200.0])
    cam = Cam(cpos, SV_P + np.array([0.0, -500.0, 0.0]))
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.014, 0.9, SV_TILT, SV_SPIN - 0.01 * t)
    S, s = sv_sat_pos(t)
    kb = fade(s, 0.30, 0.95, 0.12)
    beam(img, cam, S, SV_P, t, np.array([2.8, 2.2, 0.6]) * 2.5, 1.8, 500, 6, kb)
    return cam, dict(sats=[(S, rotm(0.0, 0.6, 0.0), BIG * 1.9, 1.0, 0.0)], sv=SV_P, beam=kb)


def sc_poema(img, t):
    k = segk("poema", t)
    P = P_SAT
    cam = cam_close(P, (6.0 - 4.0 * k, -1.2, 9.5), (0.0, 2.6, 0.0), 0.08)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.014, 1.1)
    return cam, dict(sats=[(P, rotm(0.5 + 0.1 * t, 0.2, 0.05), M, 1.0, 0.2)])


def ring_sats(n=36, r=R_E + 2200.0, t=0.0):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False) + t * 0.05
    P = np.stack([np.cos(a) * r, np.zeros_like(a), -np.sin(a) * r], -1)
    return P @ rotm(0.0, math.radians(-62), math.radians(18)).T


def sc_plan(img, t):
    if t < T_PLAN3:
        k = (t - FL[5]) / (T_PLAN3 - FL[5])
        cam = Cam(np.array([0.0, 9000.0, 30000.0 - 2500 * k]), np.array([0.0, 1200.0, 0.0]))
        draw_earth(img, cam, np.zeros(3), R_E, t, 0.014, 0.9)
        kc = ease((t - T_PLAN2) / 0.8)
        if kc > 0:
            P = ring_sats(36, t=t)
            nn = len(P)
            col = np.broadcast_to(np.array([0.6, 1.8, 2.8]) * 9 * kc, (nn, 3))
            splat(img, cam, P, np.ascontiguousarray(col), 1.0)
            for i in range(nn):
                A, B = P[i], P[(i + 1) % nn]
                u = np.linspace(0, 1, 30)[:, None]
                splat(img, cam, A * (1 - u) + B * u, np.broadcast_to(np.array([1.0, 0.9, 0.3]) * 0.08 * kc, (30, 3)).copy(), 1.0)
        return cam, dict(sats=[], ring=kc, first=True)
    s = (t - T_PLAN3) / (FL[6] - T_PLAN3)
    A = P_SAT + np.array([-3.4, 0.0, 0.0]) * M
    B = P_SAT + np.array([3.4, 0.3, -0.5]) * M
    cam = cam_close(P_SAT, (0.6 - 1.2 * s, 3.5, 20.0 - 2.0 * s), (0.0, 1.2, 0.0), 0.0)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    kl = ease((s - 0.15) / 0.3)
    if kl > 0:
        u = np.linspace(0, 1, 260)[:, None] * kl
        a2 = A + np.array([0.75, 0, 0]) * M; b2 = B - np.array([0.75, 0, 0]) * M
        splat(img, cam, a2 * (1 - u) + b2 * u, np.broadcast_to(np.array([3.0, 0.7, 0.4]) * 0.35, (260, 3)).copy(), 1.0)
    return cam, dict(sats=[(A, rotm(math.pi / 2 + 0.05, 0.05, 0.0), M * 0.8, 1.0, 0.3), (B, rotm(-math.pi / 2, -0.05, 0.0), M * 0.8, 1.0, 0.3)])


def sc_cierre(img, t):
    k = segk("cierre", t)
    cam = cam_close(P_SAT, (-2.0 + 2.0 * k, 2.4 + 2.0 * k, 9.0 + 9.0 * ease(k)), (0.0, -1.2, 0.0), 0.04)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    return cam, dict(sats=[(P_SAT, rotm(0.4 + 0.12 * t, 0.25, 0.1), M, 1.0, 0.3 + 0.3 * math.sin(t * 4))])


SCENES = {"hook1": sc_hook1, "lanzamiento": sc_lanzamiento, "orden": sc_orden, "gemma": sc_gemma,
          "svalbard": sc_svalbard, "poema": sc_poema, "plan": sc_plan, "cierre": sc_cierre}


def proj1(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def flash_alpha(t):
    a = 0.0
    for tf in FL + FL_EXTRA:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


def overlays(frame_u8, t, name, cam, ex):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    boxes = []
    if "stage" in ex:
        boxes += stage_boxes(ex["stage"][0], ex["stage"][1])
    for (P, R, s, wing, gb) in ex.get("sats", []):
        boxes += sat_boxes(P, R, s, wing, gb)
        if gb > 0.05:
            x, y, _ = proj1(cam, P)
            glow(layer, x, y, 70, CYAN, int(120 * gb))
    draw_boxes(layer, cam, boxes)
    if name == "hook1":
        draw_label(layer, t, 0.0, FL[0] + 0.05, "IA EN ÓRBITA", ["le pidieron un poema", "desde la Tierra"], YELLOW, 124)
    elif name == "lanzamiento":
        draw_label(layer, t, FL[0], T_SPLIT_LAN + 0.05, "1 OCT 2026", ["Proyecto Suncatcher", "Google + Planet"], WHITE, 140)
        if "chip" in ex:
            A = int(255 * fade(t, T_SPLIT_LAN, FL[1] + 0.05, 0.25))
            draw_chip(layer, W / 2, 560, 300 * (0.85 + 0.15 * ease_out(ex["chip"] * 3)), A, 0.5 + 0.5 * math.sin(t * 5), "CHIP DE IA (TPU)")
            txt(d, (W / 2, 290), "COMO LOS DE SUS", 66, WHITE, A)
            txt(d, (W / 2, 362), "CENTROS DE DATOS", 66, YELLOW, A)
    elif name == "orden":
        tb = SPLIT("orden", 0.25)
        terminal(layer, t, FL[1] + 0.1, FL[2] + 0.05, "escribe un haiku sobre estar en el espacio")
        x, y, z = proj1(cam, ex["G"])
        A = int(255 * fade(t, FL[1] + 0.3, FL[2] + 0.05, 0.25))
        if z > 0:
            marker(d, x, y, t, CYAN, A, 30, "ANTENA EN TIERRA", 1, 40)
        txt(d, (W / 2, 1760), "tamaños y alturas exagerados", 34, (200, 210, 230), int(200 * fade(t, FL[1] + 0.3, FL[2])), "Inter-ExtraBold.otf", 5)
    elif name == "gemma":
        A = int(255 * fade(t, FL[2], FL[3] + 0.05, 0.25))
        draw_label(layer, t, FL[2], FL[3] + 0.05, "GEMMA 4", ["pensó la respuesta en órbita", "con energía del Sol"], YELLOW, 150, 330)
    elif name == "svalbard":
        x, y, z = proj1(cam, ex["sv"])
        A = int(255 * fade(t, FL[3] + 0.2, FL[4] + 0.05, 0.25))
        if z > 0:
            marker(d, x, y, t, YELLOW, A, 34, "SVALBARD", 1, 54)
        draw_label(layer, t, FL[3], FL[4] + 0.05, "LA RESPUESTA BAJÓ", ["sobre Svalbard, Noruega"], WHITE, 92)
        txt(d, (W / 2, 1760), "tamaños y alturas exagerados", 34, (200, 210, 230), int(200 * fade(t, FL[3] + 0.3, FL[4])), "Inter-ExtraBold.otf", 5)
    elif name == "poema":
        poem_card(layer, t)
    elif name == "plan":
        if ex.get("first"):
            t1 = T_PLAN2
            draw_label(layer, t, FL[5], t1 + 0.1, "PRIMERA VEZ", ["que un chip así", "responde desde órbita"], YELLOW, 136)
            draw_label(layer, t, t1 + 0.1, T_PLAN3, "LA META", ["centros de datos", "en el espacio"], CYAN, 140)
            txt(d, (W / 2, 1760), "ilustración de la idea", 34, (200, 210, 230), int(200 * fade(t, t1 + 0.2, T_PLAN3)), "Inter-ExtraBold.otf", 5)
        else:
            draw_label(layer, t, T_PLAN3, FL[6] + 0.05, "2027", ["dos satélites", "conectados entre sí"], YELLOW, 170)
    elif name == "cierre":
        draw_label(layer, t, FL[6] + 0.1, CARD + 0.1, "PRIMER POEMA", ["escrito en órbita", "por una máquina"], YELLOW, 124)
    if name != "poema":
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
        for ts in sys.argv[2:]:
            t = float(ts)
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, scene(t), flush=True)
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
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL], "extra", [round(x, 2) for x in FL_EXTRA], "card", round(CARD, 2))
