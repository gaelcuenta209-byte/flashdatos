"""Flash Datos · video 34: la torre de SpaceX atrapó una Starship que volvía de la órbita (vuelo 15).

Escena nueva: la nave baja con motores vista desde el pie de la torre y los brazos la atrapan; vista aérea
de Starbase; 14 trazas de órbita que se acumulan alrededor de la Tierra; la nave soltando 26 Starlink sobre
la Tierra; reentrada vista desde abajo con la panza al rojo; caída de panza, giro a vertical, motores y
atrapada; globo con la trayectoria que vuelve a Starbase; el propulsor estallando en el golfo de México; y la
nave en los brazos al atardecer. Base técnica: mallas y partículas del video 30.

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
TC1 = 3.85                                 # gancho: los brazos se cierran
TSAT = SPLIT("orbita", 0.47)               # corte: de las vueltas a los satélites
TFLIP0, TFLIP1 = 21.45, 22.75              # giro a vertical
TC2 = 25.55                                # atrapada principal
TIMP = 36.35                               # el propulsor toca el agua
SHOTS = [("gancho", 0.0), ("quien", S0["quien"] - 0.2), ("vueltas", S0["orbita"] - 0.2), ("satelites", TSAT),
         ("reentrada", S0["reentrada"] - 0.2), ("atrapada", S0["atrapada"] - 0.2), ("primera", S0["primera"] - 0.2),
         ("propulsor", S0["propulsor"] - 0.2), ("cierre", S0["cierre"] - 0.2)]
ORDER = [a for a, _ in SHOTS]
FL = [b for _, b in SHOTS[1:]]
CARD = S1["cierre"] + 0.2
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


# ================= escenas (video 34) =================
def scene(t):
    name = SHOTS[0][0]
    for a, b in SHOTS:
        if t >= b:
            name = a
    return name


def t0_of(name):
    return dict(SHOTS)[name]


def catch_y(t, tc, y_top, y_end=60.0, dur=3.2, p=2.0):
    """Altura de la nave que baja frenando y queda en los brazos en tc (con un pequeño rebote)."""
    if t <= tc:
        s = min(max((t - (tc - dur)) / dur, 0.0), 1.0)
        return y_end + (y_top - y_end) * (1 - s) ** p
    return y_end - 0.7 * math.sin(min((t - tc) / 0.45, 1) * math.pi) * math.exp(-(t - tc) * 2.5)


def ship_engines(img, cam, pos, R, t, k, seed=3):
    if k <= 0.01:
        return
    axis = R @ np.array([0, -1.0, 0])
    for dx, dz in ((1.8, 0), (-0.9, 1.56), (-0.9, -1.56)):
        b = np.asarray(pos, float) + R @ np.array([dx, -0.3, dz])
        plume(img, cam, b, axis, 24, 0.9, 900, t, 0.6 * k, seed, 0.6)


# 1 · gancho: desde abajo de la torre, la nave baja con motores y los brazos la atrapan
def sc_gancho(img, t):
    s = ease(min(t / 6.2, 1.0))
    cam = Cam((48 - 14 * s, 4 + 3 * s, 118 - 18 * s), (-6, 112 - 8 * s, 0))
    draw_world(img, cam, "day")
    sy = catch_y(t, TC1, 300, dur=3.85, p=1.7)
    opn = 1.0 - ease((t - (TC1 - 1.1)) / 1.0)
    f = []
    tower(f); arms(f, 102, opn); launch_mount(f)
    R = rotm(math.pi)
    ship(f, (0, sy, 0), R)
    draw_faces(img, cam, f, "day")
    if t < TC1:
        ship_engines(img, cam, (0, sy, 0), R, t, min(1.0, (TC1 - t) / 0.4))
    return cam, {"sy": sy}


# 2 · quién: vista aérea de Starbase con la nave en los brazos
def sc_quien(img, t):
    a0 = t0_of("quien")
    s = ease((t - a0) / (FL[1] - a0))
    ang = 2.2 + 0.5 * s
    rad = 250 - 30 * s
    cam = Cam((math.sin(ang) * rad - 17, 150 - 25 * s, math.cos(ang) * rad), (-10, 75, 0))
    draw_world(img, cam, "day")
    f = []
    tower(f); arms(f, 102, 0.0); launch_mount(f)
    ship(f, (0, 60, 0), rotm(math.pi))
    draw_faces(img, cam, f, "day")
    return cam, {}


# --- espacio: unidades en km para la Tierra ---
RE_KM = 6371.0
INC = math.radians(26)


def ring_pt(th, shift, r):
    p = np.array([math.cos(th) * r, 0.0, math.sin(th) * r])
    c, s = math.cos(INC), math.sin(INC)
    p = np.array([p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]])
    return rot_y(p, shift)


def visible(cam, P, C=np.zeros(3), r=RE_KM):
    d = P - cam.O; L = np.linalg.norm(d); d = d / L
    oc = cam.O - C; b = d @ oc; c = oc @ oc - r * r
    disc = b * b - c
    if disc <= 0:
        return True
    tt = -b - math.sqrt(disc)
    return tt <= 0 or tt >= L - 1.0


# 3 · vueltas: la Tierra vista desde lejos y 14 trazas que se acumulan
def sc_vueltas(img, t):
    a0 = t0_of("vueltas")
    u = (t - a0) / (TSAT - a0)
    ang = -0.5 + 0.35 * u
    cam = Cam((math.sin(ang) * 23000, 9000 - 1500 * u, math.cos(ang) * 23000), (0, -200, 0))
    draw_earth(img, cam, np.zeros(3), RE_KM, 50 + 5 * u, atm=0.02, glow=0.85)
    return cam, {"u": u}


# 4 · satélites: la nave de frente, con la puerta lateral soltando Starlink, y la Tierra de noche abajo
def sc_satelites(img, t):
    a0 = TSAT
    u = (t - a0) / (FL[3] - a0)
    yaw = -0.9 + 0.3 * u
    dist = 120 - 15 * u
    cpos = np.array([math.sin(yaw) * dist, 38.0 - 6 * u, math.cos(yaw) * dist])
    Rs = rotm(0.0, 0.0, -math.pi / 2)
    f = []
    f = ship_space(f, Rs)
    for p, Rb in sats(t, a0 + 0.25):
        boxf(f, Rs @ (p - np.array([0, HS / 2, 0])), (1.6, 0.18, 1.0), Rb, (0.55, 0.57, 0.62), 0.6)
    cam_m = Cam(cpos, (-4, 2, 4))
    S_km = np.array([0.0, RE_KM + 260.0, 0.0])
    cam_km = Cam(S_km + cpos / 1000.0, S_km + cpos / 1000.0 + cam_m.f)
    draw_earth(img, cam_km, np.zeros(3), RE_KM, 120 + t * 2.0, atm=0.0035, glow=0.9)
    draw_faces(img, cam_m, f, "space")
    return cam_m, {}


HS_ = 52.0


def ship_space(f, R, emit=None):
    ship(f, (0, -HS_ / 2, 0), np.eye(3), emit)
    return [(verts @ R.T, R @ n, col, spec, e) for verts, n, col, spec, e in f]


def sats(t, t0):
    out = []
    for i in range(26):
        ti = t0 + i * 0.09
        if t < ti:
            break
        dt = t - ti
        rng = np.random.default_rng(100 + i)
        p = np.array([4.0 + 2.0 * dt + rng.normal(0, 0.5), 30.0 - 2.5 * i * 0.0 + rng.normal(0, 0.6) + 1.5 * dt * rng.normal(),
                      RB_ + 1.5 + 8.0 * dt + 2.0 * dt * rng.random()])
        out.append((p, rotm(0.4 * dt * (i % 3 - 1), 0.25 * dt, 0.1 * dt)))
    return out


# 5 · reentrada: vista desde abajo y adelante, la panza al rojo vivo
def sc_reentrada(img, t):
    a0 = t0_of("reentrada")
    u = (t - a0) / (FL[4] - a0)
    alt = 80.0 - 20 * u
    Rs = rotm(0.0, 0.0, math.radians(90 - 50)) @ rotm(0.0, 0.0, 0.0)
    Rs = rotm(0.0, 0.0, math.radians(40))
    heat = (0.65 + 0.35 * math.sin(t * 11) ** 2) * min(1.0, 0.4 + u * 1.2)
    f = []
    f = ship_space(f, Rs, emit=(2.6, 0.9, 0.35))
    yaw = -0.55 + 0.25 * u
    cpos = np.array([math.sin(yaw) * 125, -60.0 + 10 * u, math.cos(yaw) * 125])
    cam_m = Cam(cpos, (-6, -4, 0), roll=0.12)
    S_km = np.array([0.0, RE_KM + alt, 0.0])
    cam_km = Cam(S_km + cpos / 1000.0, S_km + cpos / 1000.0 + cam_m.f)
    draw_earth(img, cam_km, np.zeros(3), RE_KM, 160 + t * 2.0, atm=0.0018, glow=0.8)
    belly = Rs @ np.array([-1.0, 0, 0])
    axis = Rs @ np.array([0, 1.0, 0])
    vel = unit(belly)                       # cae con la panza por delante
    rng = np.random.default_rng(int(t * FPS) + 7)
    n = 3600
    along = rng.random(n) ** 1.5 * 70
    yl = rng.uniform(-HS_ / 2, HS_ / 2, n)
    side = rng.normal(0, 1.0, n)
    perp = unit(np.cross(axis, belly))
    Pts = (belly * (RB_ + 1.2))[None, :] + yl[:, None] * axis + side[:, None] * perp * (RB_ * (1 + along / 25))[:, None] \
        - vel[None, :] * along[:, None]
    hot = np.exp(-along / 10)[:, None]
    col = (np.array([2.8, 1.7, 1.4]) * hot + np.array([2.4, 0.5, 1.0]) * (1 - hot)) * (2800.0 / n) * heat
    draw_faces(img, cam_m, f, "space", glow_emit=heat * 0.12)
    splat2(img, cam_m, Pts, col.astype(np.float32), 4.0, 0.0)
    return cam_m, {"heat": heat}


# 6 · atrapada: cae de panza, gira a vertical, enciende motores y los brazos la cierran
def atr_state(t):
    if t < TFLIP0:
        y = 330 - 45 * (t - (S0["atrapada"] - 0.2)); r = math.pi / 2
    elif t < TFLIP1:
        s = ease((t - TFLIP0) / (TFLIP1 - TFLIP0))
        y0 = 330 - 45 * (TFLIP0 - (S0["atrapada"] - 0.2))
        y = y0 - 40 * (t - TFLIP0); r = math.pi / 2 * (1 - s)
    else:
        y0 = 330 - 45 * (TFLIP0 - (S0["atrapada"] - 0.2)) - 40 * (TFLIP1 - TFLIP0)
        y = catch_y(t, TC2, y0, dur=TC2 - TFLIP1, p=1.6); r = 0.0
    return y, r


def sc_atrapada(img, t):
    a0 = t0_of("atrapada")
    sy, rr = atr_state(t)
    s = ease((t - a0) / (FL[5] - a0))
    look = lerp(sy + 26, 95, smooth(TC2 - 2.0, TC2, t))
    cam = Cam((-150 + 30 * s, 25 + 20 * s, 190 - 30 * s), (-6, float(look), 0))
    draw_world(img, cam, "day")
    # nave: pivote en el centro (y local 26); panza hacia +x cuando es vertical (rotm(pi))
    Rv = rotm(math.pi) @ rotm(0.0, 0.0, 0.0)
    R = rotm(math.pi) @ rotm(0.0, 0.0, rr)
    ctr = np.array([0.0, sy + 26, 0.0])
    pos = ctr - R @ np.array([0, 26.0, 0])
    opn = 1.0 - ease((t - (TC2 - 1.2)) / 1.1)
    f = []
    tower(f); arms(f, 102, opn); launch_mount(f)
    ship(f, pos, R)
    draw_faces(img, cam, f, "day")
    if TFLIP0 + 0.9 < t < TC2:
        ship_engines(img, cam, pos, R, t, min(1.0, (t - TFLIP0 - 0.9) / 0.3, (TC2 - t) / 0.35))
    return cam, {"sy": sy}


# 7 · primera: la Tierra con Starbase marcada y la trayectoria que vuelve al mismo punto
TX_LAT, TX_LON = math.radians(25.99), math.radians(-97.15)
PH_PRIM = 210.0


def earth_dir(lat, lon, tt):
    loc = np.array([math.cos(lat) * math.sin(lon), math.sin(lat), math.cos(lat) * math.cos(lon)])
    return rot_x(rot_y(loc, -(-1.72 + 0.03 * tt)), -math.radians(16))


def sc_primera(img, t):
    a0 = t0_of("primera")
    u = (t - a0) / (FL[6] - a0)
    n = earth_dir(TX_LAT, TX_LON, PH_PRIM)
    side = unit(np.cross(n, [0, 1, 0]))
    cpos = n * 17500 + side * (2500 - 4000 * u) + np.array([0, 2500, 0])
    cam = Cam(cpos, n * 2500)
    draw_earth(img, cam, np.zeros(3), RE_KM, PH_PRIM, atm=0.02, glow=0.85)
    return cam, {"u": u, "n": n}


# 8 · propulsor: cae inclinado al golfo de México y estalla en el agua
def sc_propulsor(img, t):
    a0 = t0_of("propulsor")
    s = ease((t - a0) / (FL[7] - a0))
    cam = Cam((-30 + 20 * s, 12 + 4 * s, 430 - 30 * s), (25, 150 - 110 * smooth(a0, TIMP, t), 0))
    draw_world(img, cam, "gulf")
    f = []
    if t < TIMP:
        k = (TIMP - t) / (TIMP - a0)
        by = 0 + 400 * k ** 1.25
        bx = 40 - 90 * k
        R = rotm(0.0, 0.0, math.radians(-14 - 10 * (1 - k)))
        booster(f, (bx, by, 0), R)
        draw_faces(img, cam, f, "dusk")
        plume(img, cam, (bx, by - 0.5, 0), R @ np.array([0, -1.0, 0]), 30, 2.0, 1500, t, 0.9, 6, 0.8)
        # rastro de vapor
        rng = np.random.default_rng(5)
        m = 900
        q = rng.random(m)
        P = np.stack([bx - 90 * q * (a0 - t + 3) / 3 * 0 + (-90 * q), by + 520 * q * 0.45 + 40 * q, rng.normal(0, 3, m)], -1)
        P = np.array([bx, by + 72, 0.0]) + np.stack([-75 * q, 280 * q, rng.normal(0, 2 + 6 * q, m)], -1)
        splat2(img, cam, P, (np.array([1.6, 1.6, 1.7]) * (0.6 / m * 60) * (1 - q)[:, None]).astype(np.float32), 3.0, 0.0)
    else:
        dt = t - TIMP
        rng = np.random.default_rng(11)
        m = 2600
        v = rng.normal(size=(m, 3)); v[:, 1] = np.abs(v[:, 1]) * 2.2 + 0.4
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        sp = 70 + 130 * rng.random(m)
        P = np.array([40.0, 0, 0]) + v * sp[:, None] * dt
        P[:, 1] = np.maximum(P[:, 1] - 45 * dt * dt, 0)
        fade_ = math.exp(-dt / 2.0)
        splat2(img, cam, P, (np.array([1.8, 1.9, 2.0]) * (420.0 / m) * fade_ * np.ones((m, 1))).astype(np.float32), 2.5, 0.2)
        fire = math.exp(-dt / 0.5)
        if fire > 0.02:
            Q = np.array([40.0, 6, 0]) + rng.normal(0, 1, (1200, 3)) * (12 + 70 * min(dt, 1)) * np.array([1, 0.8, 1])
            Q[:, 1] = np.abs(Q[:, 1])
            splat2(img, cam, Q, (np.array([2.6, 1.2, 0.35]) * (600.0 / 1200) * fire * np.ones((1200, 1))).astype(np.float32), 5.0, 0.0)
        smoke(img, cam, (40, 40 + 50 * min(dt, 1.5), 0), 40 + 60 * min(dt, 1.5), 1200, t, (1.4, 1.3, 1.3), 8)
        impact_flash(img, cam, np.array([[40.0, 8, 0]]), dt, 0.6)
    return cam, {}


# 9 · cierre: la nave en los brazos, de frente al atardecer
def sc_cierre(img, t):
    a0 = t0_of("cierre")
    s = ease((t - a0) / (END - a0))
    ang = 0.75 - 0.35 * s
    rad = 150 - 25 * s
    cam = Cam((math.sin(ang) * rad, 6 + 8 * s, math.cos(ang) * rad), (-6, 92 + 6 * s, 0))
    draw_world(img, cam, "dusk")
    f = []
    tower(f); arms(f, 102, 0.0); launch_mount(f)
    ship(f, (0, 60, 0), rotm(math.pi))
    draw_faces(img, cam, f, "dusk")
    return cam, {}


SCENES = {"gancho": sc_gancho, "quien": sc_quien, "vueltas": sc_vueltas, "satelites": sc_satelites,
          "reentrada": sc_reentrada, "atrapada": sc_atrapada, "primera": sc_primera, "propulsor": sc_propulsor,
          "cierre": sc_cierre}
MODES = {"propulsor": "dusk", "vueltas": "space", "satelites": "space", "reentrada": "space", "primera": "space", "cierre": "dusk"}


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def poly3d(d, cam, P_list, col, A, width=6):
    prev = None
    for P in P_list:
        x, y, z = pt(cam, P)
        cur = (x, y) if (z > 0 and visible(cam, P)) else None
        if prev and cur:
            d.line([prev, cur], fill=col + (A,), width=width)
        prev = cur


def overlays(frame_u8, t, name, cam, ex):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0 = t0_of(name)
    if name == "gancho":
        draw_label(layer, t, 0.15, TC1 - 0.1, "DESDE EL ESPACIO", ["Starship · SpaceX"], WHITE, 108)
        draw_label(layer, t, TC1, FL[0] + 0.05, "¡ATRAPADA!", ["con los brazos de la torre"], YELLOW, 140)
        if t >= TC1 - 0.2:
            A = int(255 * fade(t, TC1 - 0.2, FL[0] + 0.05))
            x, y, _ = pt(cam, (-2, 102, 7)); marker(d, x, y, t, CYAN, A, 40)
            x, y, _ = pt(cam, (-2, 102, -7)); marker(d, x, y, t, CYAN, A, 40)
    elif name == "quien":
        mid = SPLIT("quien", 0.45)
        draw_label(layer, t, a0 + 0.15, mid, "SÁBADO 14 NOV", ["vuelo 15 de Starship"], YELLOW, 120)
        draw_label(layer, t, mid, FL[1] + 0.05, "3:20 P.M.", ["Starbase, Texas", "(misma hora que en CDMX)"], WHITE, 130)
        A = int(255 * fade(t, a0 + 0.4, FL[1]))
        if A > 0:
            x, y, _ = pt(cam, (0, 88, 0)); marker(d, x, y, t, YELLOW, A, 46, "NAVE", 1, 46)
    elif name == "vueltas":
        u = ex["u"]
        laps = 1 + min(13, int(14 * u))
        A = int(255 * min(1, (t - a0) / 0.3))
        r = RE_KM + 260 * 4
        for k in range(laps):
            frac = 1.0 if k < laps - 1 else (14 * u - k) % 1.0 if laps < 14 else 1.0
            pts = [ring_pt(i / 90 * 2 * math.pi * frac, -k * math.radians(23.5), r) for i in range(91)]
            colk = YELLOW if k == laps - 1 else CYAN
            poly3d(d, cam, pts, colk, int(A * (1.0 if k == laps - 1 else 0.55)), 6 if k == laps - 1 else 4)
        draw_label(layer, t, a0 + 0.1, TSAT + 0.05, f"VUELTA {laps}", ["de 14 alrededor de la Tierra"], YELLOW, 130)
        txt(d, (W / 2, 1830), "recreación · altura exagerada", 34, (220, 225, 235), int(200 * fade(t, a0, TSAT)), "Inter-ExtraBold.otf", 5)
    elif name == "satelites":
        draw_label(layer, t, a0 + 0.1, FL[3] + 0.05, "26 STARLINK", ["satélites V3, los más grandes"], CYAN, 130)
    elif name == "reentrada":
        mid = SPLIT("reentrada", 0.45)
        draw_label(layer, t, a0 + 0.15, mid, "22.5 HORAS", ["después del despegue"], YELLOW, 140)
        draw_label(layer, t, mid, FL[4] + 0.05, "REENTRADA", ["envuelta en plasma"], ORANGE, 124)
    elif name == "atrapada":
        draw_label(layer, t, a0 + 0.15, TFLIP1, "GIRO A VERTICAL", ["de panza a de pie"], WHITE, 104)
        draw_label(layer, t, TFLIP1, TC2 - 1.1, "MOTORES", ["para frenar"], ORANGE, 124)
        draw_label(layer, t, TC2 - 1.1, TC2, "LOS PALILLOS", ["brazos de la torre"], CYAN, 120)
        draw_label(layer, t, TC2, FL[5] + 0.05, "¡ATRAPADA!", ["al primer intento"], YELLOW, 140)
    elif name == "primera":
        u = ex["u"]; n = ex["n"]
        A = int(255 * min(1, (t - a0) / 0.3))
        r = RE_KM + 900
        P0 = n * RE_KM
        e1 = unit(np.cross(n, [0.3, 1, 0.2])); e2 = np.cross(n, e1)
        frac = min(1.0, max(0.0, (u - 0.05) / 0.6))
        pts = []
        for i in range(121):
            th = i / 120 * 2 * math.pi * frac
            h = RE_KM + 900 * math.sin(min(th, 2 * math.pi - th, 0.6) / 0.6 * math.pi / 2) if th < 2 * math.pi else RE_KM
            pts.append((n * math.cos(th) + e1 * math.sin(th)) * h)
        poly3d(d, cam, pts, YELLOW, A, 7)
        x, y, _ = pt(cam, P0)
        glow(layer, x, y, 60, YELLOW, int(200 * A / 255))
        marker(d, x, y, t, WHITE, A, 30, "STARBASE", 1, 46)
        draw_label(layer, t, a0 + 0.15, FL[6] + 0.05, "PRIMERA VEZ", ["vuelve de la órbita y la atrapan", "donde despegó"], YELLOW, 140)
        txt(d, (W / 2, 1830), "recreación · trayectoria ilustrativa", 34, (220, 225, 235), int(200 * fade(t, a0, FL[6])), "Inter-ExtraBold.otf", 5)
    elif name == "propulsor":
        mid = TIMP - 0.1
        draw_label(layer, t, a0 + 0.15, mid, "EL PROPULSOR", ["no volvió a la torre"], WHITE, 118)
        draw_label(layer, t, mid, FL[7] + 0.05, "GOLFO DE MÉXICO", ["ahí terminó"], CYAN, 104)
    elif name == "cierre":
        draw_label(layer, t, a0 + 0.15, CARD + 0.1, "VOLVER A VOLAR", ["la meta: naves reutilizables"], YELLOW, 120)
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
