"""Flash Datos · video 29: Marte podría seguir vivo (gas de las grietas de Alba Mons).

Escena nueva: Marte procedural con relieve (Tharsis, Olympus Mons, Alba Mons, Valles Marineris),
gas que sale de Alba Mons, la sonda ExoMars TGO midiendo, la Tierra con un volcán, el terreno marciano
con grietas (de cerca y desde el aire), una gráfica de flujo y un corte del subsuelo con magma.

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
P2 = SEG["sonda"]["parts"][1][0]
SHOTS = [("gancho", 0.0), ("sonda", S0["sonda"] - 0.2), ("tierra", P2 - 0.2), ("grietas", S0["grietas"] - 0.2),
         ("cuanto", S0["cuanto"] - 0.2), ("magma", S0["magma"] - 0.2), ("cierre", S0["cierre"] - 0.2)]
ORDER = [a for a, _ in SHOTS]
FL = [b for _, b in SHOTS[1:]]
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
    txt(d, (W / 2, 1185), "del espacio", 52, CYAN, A, "Inter-ExtraBold.otf", 6)


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




# ================= Marte, Alba Mons y el gas =================
R_M = 1.0                      # radio de Marte (unidad de la escena)
KM = 1.0 / 3390.0
ALBA_LAT, ALBA_LON = math.radians(40.5), math.radians(-109.6)
OLY_LAT, OLY_LON = math.radians(18.6), math.radians(-133.8)
GAS = np.array([0.45, 1.9, 1.35])          # verde-cian para el gas (visualización)
GREEN = (120, 255, 170)


def sph(lat, lon):
    return np.stack([np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)], -1)


def ang_dist(lat, lon, lat0, lon0):
    v = sph(lat, lon); v0 = sph(np.float64(lat0), np.float64(lon0))
    return np.arccos(np.clip((v * v0).sum(-1), -1, 1))


def make_mars():
    path = os.path.join(BASE, "tex", "mars.npz")
    if os.path.exists(path):
        z = np.load(path)
        return z["alb"], z["hgt"]
    TW_, TH_ = 2048, 1024
    lon = ((np.arange(TW_) + 0.5) / TW_ * 2 - 1) * np.pi
    lat = (0.5 - (np.arange(TH_) + 0.5) / TH_) * np.pi
    LON, LAT = np.meshgrid(lon, lat)
    v = sph(LAT, LON)
    X, Y, Z = v[..., 0] * 2.2, v[..., 1] * 2.2, v[..., 2] * 2.2
    n1 = fbm(X, Y, Z, 6, seed=3)
    n2 = fbm(X * 3, Y * 3, Z * 3, 5, seed=8)
    dark = np.clip((n1 - 0.5) * 3.2 + 0.25, 0, 1) * smooth(0.95, 0.2, np.abs(LAT))
    bright = np.array([0.80, 0.44, 0.24]); mid = np.array([0.62, 0.32, 0.18]); drk = np.array([0.30, 0.16, 0.10])
    alb = bright[None, None] * (1 - dark[..., None]) + drk[None, None] * dark[..., None]
    alb = alb * (0.85 + 0.3 * n2[..., None])
    alb = alb * (1 - 0.25 * smooth(0.55, 0.9, n2))[..., None] + mid * 0.25 * smooth(0.55, 0.9, n2)[..., None]
    # cráteres
    rng = np.random.default_rng(4)
    hgt = (n1 - 0.5) * 0.6 + (n2 - 0.5) * 0.25
    for _ in range(260):
        la0 = math.asin(rng.uniform(-1, 1)); lo0 = rng.uniform(-np.pi, np.pi); rr = 0.012 + 0.07 * rng.random() ** 3
        dd = ang_dist(LAT, LON, la0, lo0) / rr
        m = dd < 1.6
        if not m.any():
            continue
        prof = np.where(dd < 1, -0.6 * (1 - dd ** 2), 0.25 * np.exp(-((dd - 1.0) / 0.18) ** 2))
        hgt[m] += prof[m] * (0.5 + rr * 4)
    # Tharsis, Olympus Mons, Alba Mons, Valles Marineris
    tharsis = np.exp(-(ang_dist(LAT, LON, math.radians(2), math.radians(-105)) / 0.45) ** 2)
    hgt += 1.2 * tharsis
    for la0, lo0 in [(math.radians(-8.4), math.radians(-120.5)), (math.radians(1.5), math.radians(-112.5)), (math.radians(11.8), math.radians(-104.5))]:
        dd = ang_dist(LAT, LON, la0, lo0)
        hgt += 1.6 * np.exp(-(dd / 0.05) ** 2) - 0.5 * np.exp(-(dd / 0.012) ** 2)
    dd = ang_dist(LAT, LON, OLY_LAT, OLY_LON)
    hgt += 3.0 * np.exp(-(dd / 0.07) ** 1.6) - 0.8 * np.exp(-(dd / 0.018) ** 2) + 0.7 * np.exp(-((dd - 0.115) / 0.008) ** 2)
    dd = ang_dist(LAT, LON, ALBA_LAT, ALBA_LON)
    hgt += 1.1 * np.exp(-(dd / 0.20) ** 2) - 0.35 * np.exp(-(dd / 0.022) ** 2)
    # fosas concéntricas alrededor de Alba Mons (aspecto de grietas)
    ring = np.sin(dd * 140 + 3 * n2) * np.exp(-((dd - 0.24) / 0.09) ** 2)
    hgt -= 0.12 * np.clip(ring - 0.7, 0, 1) * 4
    vm_lon0, vm_lon1 = math.radians(-95), math.radians(-45)
    s = np.clip((LON - vm_lon0) / (vm_lon1 - vm_lon0), 0, 1)
    vlat = math.radians(-9) + math.radians(3) * s
    vm = np.exp(-((LAT - vlat) / np.radians(1.6 + 1.5 * np.sin(s * np.pi))) ** 2) * ((LON > vm_lon0) & (LON < vm_lon1))
    hgt -= 1.4 * vm * (0.7 + 0.6 * n2)
    alb = alb * (1 - 0.35 * vm[..., None])
    alb = alb * (1 + 0.10 * tharsis[..., None])
    # casquetes polares
    cap = smooth(math.radians(78), math.radians(84), np.abs(LAT) + 0.04 * (n2 - 0.5))
    alb = alb * (1 - cap[..., None]) + np.array([0.92, 0.90, 0.88]) * cap[..., None]
    alb = np.clip(alb, 0, 1).astype(np.float32); hgt = hgt.astype(np.float32)
    np.savez(path, alb=alb, hgt=hgt)
    return alb, hgt


MARS_ALB, MARS_H = make_mars()
MARS_ALB_L = lin(MARS_ALB)
_hy, _hx = np.gradient(MARS_H)
MARS_GX = (_hx * 0.9).astype(np.float32); MARS_GY = (_hy * 0.9).astype(np.float32)


def alba_world(spin):
    """Posición de Alba Mons en el mundo para un giro dado (giro: lon_textura = lon_mundo + spin)."""
    return sph(np.float64(ALBA_LAT), np.float64(ALBA_LON - spin)) * R_M


def draw_mars(img, cam, C, r, spin, desat=0.0, atm=0.035, glow=0.7):
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
        lit = np.clip(nn @ LIGHT + 0.3, 0, 1)
        gl = np.exp(-np.maximum((dd[hz] - r) / (atm * r), 0)) * lit * glow
        region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([0.95, 0.55, 0.35]) * (1 - desat * 0.7)
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]; bs = b[sel]
    tt = -bs - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = cam.O + tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    loc = rot_y(n, spin)
    la, lo = latlon(loc)
    alb = sample(MARS_ALB_L, la, lo)
    gx = sample(MARS_GX, la, lo); gy = sample(MARS_GY, la, lo)
    # base tangente (este, norte) en el mundo
    east = np.stack([np.cos(lo), np.zeros_like(lo), -np.sin(lo)], -1)
    north = np.stack([-np.sin(la) * np.sin(lo), np.cos(la), -np.sin(la) * np.cos(lo)], -1)
    east = rot_y(east, -spin); north = rot_y(north, -spin)
    nb = n - (gx[:, None] * east - gy[:, None] * north) * 1.2
    nb /= np.linalg.norm(nb, axis=-1, keepdims=True)
    ndl = nb @ LIGHT
    ndl0 = n @ LIGHT
    diff = np.clip(ndl, 0, 1) * smooth(-0.08, 0.12, ndl0)
    light = (0.012 + 2.0 * diff)[..., None]
    col = alb * light
    if desat > 0:
        g = (col * np.array([0.3, 0.55, 0.15])).sum(-1, keepdims=True)
        col = col * (1 - desat) + g * np.array([0.85, 0.88, 0.95]) * desat
    V = -ds
    mu = np.clip((n * V).sum(-1), 0, 1)
    col = col + np.array([0.75, 0.42, 0.26]) * ((1 - mu) ** 3 * 0.9 * np.clip(ndl0 + 0.2, 0, 1))[..., None] * (1 - desat * 0.6)
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


def occluded(cam, P, C=np.zeros(3), r=R_M):
    """True para puntos tapados por el planeta."""
    d = P - cam.O
    L = np.linalg.norm(d, axis=-1)
    d = d / L[:, None]
    oc = cam.O - C
    b = d @ oc
    c = float(oc @ oc) - r * r
    disc = b * b - c
    t0 = -b - np.sqrt(np.maximum(disc, 0))
    return (disc > 0) & (t0 > 0) & (t0 < L - 1e-4)


def gas_plume(img, cam, base, normal, t, height, width, k, n=1400, seed=2, C=np.zeros(3), r=R_M, cull=True):
    """Hilos de gas que salen de las grietas: partículas que suben y se dispersan."""
    if k <= 0.01:
        return
    rng = np.random.default_rng(seed)
    normal = np.asarray(normal, float); normal /= np.linalg.norm(normal)
    a = np.cross(normal, [0.3, 0.1, 0.9]); a /= np.linalg.norm(a); b = np.cross(normal, a)
    src = rng.integers(0, 9, n)
    sa = rng.normal(size=9) * width * 0.9; sb = rng.normal(size=9) * width * 0.9
    ph = rng.random(n)
    age = (ph + t * (0.22 + 0.1 * rng.random(n))) % 1.0
    h = age ** 0.8 * height
    sw = width * (0.08 + 0.9 * age)
    wob = np.sin(age * 9 + src * 1.7 + t * 1.3)
    off_a = sa[src] + rng.normal(size=n) * sw + wob * sw * 0.6 + age * width * 1.4
    off_b = sb[src] + rng.normal(size=n) * sw
    P = np.asarray(base) + normal * h[:, None] + a * off_a[:, None] + b * off_b[:, None]
    inten = (np.sin(np.pi * age) ** 1.5) * k * (0.5 + 0.5 * rng.random(n))
    col = GAS[None, :] * inten[:, None] * 0.26
    if cull:
        m = ~occluded(cam, P, C, r)
        P, col = P[m], col[m]
    splat(img, cam, P, col, 1.0)


def tgo_boxes(pos, R, s):
    gold = (214, 170, 72); panel = (36, 62, 130); grey = (176, 180, 190); white = (230, 232, 238)
    out = [(pos, (1.6 * s, 1.0 * s, 1.0 * s), R, gold),
           (pos + R @ np.array([0, 1.15 * s, 0]), (1.1 * s, 0.12 * s, 1.1 * s), R, white),
           (pos + R @ np.array([0, -1.05 * s, 0.3 * s]), (0.35 * s, 0.12 * s, 0.35 * s), R, grey)]
    for side in (-1, 1):
        out.append((pos + R @ np.array([0, 0, side * 1.35 * s]), (0.08 * s, 0.08 * s, 0.35 * s), R, grey))
        for k in range(3):
            out.append((pos + R @ np.array([0, 0, side * (2.4 + 1.55 * k) * s]), (0.95 * s, 0.03 * s, 0.72 * s), R, panel))
    return out


def scene(t):
    name = ORDER[0]
    for nm, t0 in SHOTS:
        if t >= t0:
            name = nm
    return name


def shot_k(name, t):
    i = ORDER.index(name)
    a = SHOTS[i][1]
    b = SHOTS[i + 1][1] if i + 1 < len(SHOTS) else END
    return (t - a) / (b - a)


# ---------------- terreno (plano con relieve sombreado) ----------------
def make_ground(kind):
    path = os.path.join(BASE, "tex", f"ground_{kind}.npy")
    if os.path.exists(path):
        return np.load(path)
    N_ = 2048
    u = (np.arange(N_) + 0.5) / N_
    X, Y = np.meshgrid(u, u)          # X: a lo largo, Y: a lo ancho
    rng = np.random.default_rng(12 if kind == "fine" else 13)
    if kind == "fine":       # 8 m x 8 m: arena, piedras y dos grietas de ~30 cm
        hgt = fbm(X * 24, Y * 24, np.full_like(X, 1.0), 6, seed=5) * 0.6 + fbm(X * 160, Y * 160, np.full_like(X, 2.0), 3, seed=6) * 0.15
        crack = np.zeros_like(X)
        for yc, amp, w in [(0.50, 0.035, 0.019), (0.70, 0.025, 0.010)]:
            yl = yc + amp * np.sin(X * 2 * np.pi * 2.0 + yc * 9) + 0.025 * (fbm(X * 30, np.full_like(X, yc * 7), np.zeros_like(X), 4, seed=9) - 0.5)
            dist = np.abs(Y - yl)
            ww = w * (0.75 + 0.5 * fbm(X * 40, np.full_like(X, yc), np.ones_like(X), 3, seed=11))
            crack = np.maximum(crack, smooth(ww, ww * 0.55, dist))
        stones = np.zeros_like(X)
        for _ in range(500):
            cx_, cy_, rr = rng.random(), rng.random(), 0.002 + 0.012 * rng.random() ** 3
            ii = slice(max(0, int((cy_ - rr * 1.5) * N_)), min(N_, int((cy_ + rr * 1.5) * N_) + 1))
            jj = slice(max(0, int((cx_ - rr * 1.5) * N_)), min(N_, int((cx_ + rr * 1.5) * N_) + 1))
            dd = np.sqrt((X[ii, jj] - cx_) ** 2 + (Y[ii, jj] - cy_) ** 2) / rr
            stones[ii, jj] = np.maximum(stones[ii, jj], np.clip(1 - dd ** 2, 0, 1) ** 0.6)
        hgt = hgt + stones * 0.5 - crack * 1.5
        scale = 8.0 / N_
        base = np.array([0.66, 0.36, 0.20])
    else:                    # 60 km x 60 km: crestas con enjambres de grietas largas
        hgt = fbm(X * 6, Y * 6, np.full_like(X, 3.0), 6, seed=7) * 0.9
        ridges = np.zeros_like(X)
        crack = np.zeros_like(X)
        for yc in [0.22, 0.44, 0.63, 0.82]:
            yl = yc + 0.02 * np.sin(X * 2 * np.pi * 1.3 + yc * 11)
            ridges += np.exp(-((Y - yl) / 0.045) ** 2)
            for j in range(7):
                off = (j - 3) * 0.0055 + 0.0015 * rng.normal()
                seg = fbm(X * 6, np.full_like(X, yc * 13 + j), np.zeros_like(X), 3, seed=j) > 0.47
                dist = np.abs(Y - yl - off - 0.0012 * np.sin(X * 140 + j))
                crack = np.maximum(crack, smooth(0.0019, 0.0007, dist) * seg * np.exp(-((Y - yl) / 0.035) ** 2))
        hgt = hgt + ridges * 1.6 - crack * 0.6 + fbm(X * 90, Y * 90, np.full_like(X, 8.0), 4, seed=21) * 0.06
        scale = 60000.0 / N_
        base = np.array([0.70, 0.40, 0.23])
    n2 = fbm(X * 50, Y * 50, np.full_like(X, 4.0), 4, seed=14)
    gy, gx = np.gradient(hgt)
    k = 220.0 if kind == "fine" else 160.0
    nrm = np.stack([-gx * k, np.ones_like(gx), -gy * k], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Ld = np.array([-0.5, 0.55, -0.35]); Ld /= np.linalg.norm(Ld)
    sh = np.clip(nrm @ Ld, 0, 1)
    col = base[None, None] * (0.8 + 0.4 * n2[..., None])
    col = col * (0.10 + 1.25 * sh[..., None])
    col = col * (1 - 0.92 * crack[..., None])
    out = lin(np.clip(col, 0, 1.5) ** (1 / 1.0)).astype(np.float32)
    np.save(path, out)
    np.save(path.replace(".npy", "_crack.npy"), crack.astype(np.float32))
    return out


def mips(tex):
    lv = [tex]
    while lv[-1].shape[0] > 64:
        a = lv[-1]
        lv.append(((a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4).astype(np.float32))
    return lv


GROUND = {k: mips(make_ground(k)) for k in ("fine", "coarse")}
EXTENT = {"fine": 8.0, "coarse": 20000.0}
CRACK_C = np.load(os.path.join(BASE, "tex", "ground_coarse_crack.npy"))


def sample2d(tex, u, v):
    th, tw = tex.shape[:2]
    x = u * tw - 0.5; y = v * th - 0.5
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[..., None].astype(np.float32); fy = (y - y0)[..., None].astype(np.float32)
    xa, xb = x0 % tw, (x0 + 1) % tw; ya, yb = y0 % th, (y0 + 1) % th
    return (tex[ya, xa] * (1 - fx) + tex[ya, xb] * fx) * (1 - fy) + (tex[yb, xa] * (1 - fx) + tex[yb, xb] * fx) * fy


SKY_TOP = lin((0.30, 0.22, 0.20)); SKY_HOR = lin((0.86, 0.64, 0.46)); HAZE = lin((0.80, 0.58, 0.42))


def draw_ground(img, cam, kind, fog):
    d = cam.dirs(0, H, 0, W)
    dy = d[..., 1]
    sky = dy >= -0.002
    s = np.clip(dy, 0, 1)[..., None]
    img[:] = SKY_HOR * (1 - s ** 0.45) + SKY_TOP * s ** 0.45
    g = ~sky
    dg = d[g]
    tt = -cam.O[1] / dg[:, 1]
    P = cam.O + tt[:, None] * dg
    ext = EXTENT[kind]
    u = P[:, 0] / ext + 0.5; v = P[:, 2] / ext + 0.5
    lv = GROUND[kind]
    texel = ext / lv[0].shape[0]
    foot = tt * PIX / np.maximum(np.abs(dg[:, 1]), 0.02) ** 0.5
    lod = np.clip(np.log2(np.maximum(foot / texel, 1e-6)), 0, len(lv) - 1)
    li = np.floor(lod).astype(int); lf = (lod - li)[:, None]
    col = np.zeros((len(tt), 3), np.float32)
    for l in range(len(lv)):
        m = li == l
        if not m.any():
            continue
        c0 = sample2d(lv[l], u[m], v[m])
        c1 = sample2d(lv[min(l + 1, len(lv) - 1)], u[m], v[m])
        col[m] = c0 * (1 - lf[m]) + c1 * lf[m]
    fz = 1 - np.exp(-tt / fog)
    col = col * (1 - fz[:, None]) + HAZE * fz[:, None]
    img[g] = col
    return P


# ---------------- escenas ----------------
def mars_cam(dist, yaw, pitch, look=(0, 0, 0), roll=0.0):
    pos = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)]) * dist
    return Cam(pos, np.asarray(look, float), roll)


SPIN0 = ALBA_LON + 0.80       # Alba Mons queda un poco a la derecha del centro


def sc_gancho(img, t):
    k = shot_k("gancho", t)
    spin = SPIN0 - 0.55 + 0.10 * t
    cam = mars_cam(7.2 - 1.6 * ease(k), 0.0, 0.42 + 0.08 * k, (-0.25 * ease(k), 0.10 + 0.2 * ease(k), 0))
    tw = SPLIT("gancho", 0.48)
    desat = 1 - ease((t - tw + 0.2) / 0.9)
    draw_mars(img, cam, np.zeros(3), R_M, spin, desat)
    A = alba_world(spin)
    gk = ease((t - tw) / 0.8)
    gas_plume(img, cam, A * 1.004, A, t, 0.30, 0.05, gk * 2.2, 3000)
    return cam, dict(A=A, gk=gk, tw=tw)


def sc_sonda(img, t):
    k = shot_k("sonda", t)
    spin = SPIN0 - 0.25 + 0.06 * t
    cam = mars_cam(5.6 - 0.4 * k, -0.20 + 0.25 * k, 0.50, (-0.2, 0.15, 0))
    draw_mars(img, cam, np.zeros(3), R_M, spin)
    A = alba_world(spin)
    gas_plume(img, cam, A * 1.004, A, t, 0.28, 0.045, 2.0, 3000)
    # la sonda cruza delante de la cámara
    s = 0.004
    fwd = cam.f; right = cam.r; up = cam.u
    P = cam.O + fwd * 0.16 + right * (0.06 - 0.10 * ease(k)) + up * (0.012 - 0.008 * k)
    R = rotm(0.9 + 0.35 * k, 0.25, 0.15)
    return cam, dict(A=A, P=P, R=R, s=s, k=k)


def sc_tierra(img, t):
    k = shot_k("tierra", t)
    R_E_ = 1.0
    cam = Cam(np.array([0.2, 0.75, 2.7 - 0.2 * k]), np.array([0.0, 1.05, 0]))
    draw_earth(img, cam, np.zeros(3), R_E_, t * 3, 0.03, 0.6)
    V = np.array([0.18, 0.93, 0.30]); V /= np.linalg.norm(V)
    gas_plume(img, cam, V * 1.003, V, t, 0.16, 0.02, 3.0, 2200, seed=7)
    x, y, _ = cam.proj(V * 1.004)
    return cam, dict(V=V, k=k)


def sc_grietas(img, t):
    k = shot_k("grietas", t)
    tsplit = SPLIT("grietas", 0.46)
    if t < tsplit:
        kk = (t - SHOTS[ORDER.index("grietas")][1]) / (tsplit - SHOTS[ORDER.index("grietas")][1])
        x = -1.5 + 1.2 * kk
        cam = Cam(np.array([x, 1.55 - 0.25 * kk, 1.4]), np.array([x + 0.6, 0.0, -0.4]), 0.02)
        draw_ground(img, cam, "fine", 60.0)
        for i, zc in enumerate([0.0, 1.6]):
            for j in range(4):
                xb = -1.2 + j * 1.1 + 0.3 * i
                gas_plume(img, cam, np.array([xb, 0.0, zc]), np.array([0.05, 1.0, 0.0]), t + j, 1.4, 0.10, 4.0, 1100, seed=20 + i * 4 + j, cull=False)
        return cam, dict(close=True, kk=kk, tsplit=tsplit, cx=x + 0.5)
    kk = (t - tsplit) / (FL[ORDER.index("grietas")] - tsplit)
    alt = 5000.0 * (12000.0 / 5000.0) ** ease(kk)
    x = -3000.0 + 2500.0 * kk
    cam = Cam(np.array([x, alt, -2000.0 + alt * 0.55]), np.array([x + 300, 0.0, -2000.0 - alt * 0.05]), 0.0)
    draw_ground(img, cam, "coarse", 90000.0)
    rng = np.random.default_rng(31)
    for j in range(12):
        yc = [0.22, 0.44, 0.63, 0.82][j % 4]
        px = (rng.random() - 0.5) * 14000.0
        pz = (yc - 0.5) * 20000.0
        gas_plume(img, cam, np.array([px, 0.0, pz]), np.array([0.1, 1.0, 0.0]), t + j, 900.0, 160.0, 2.2, 500, seed=40 + j, cull=False)
    return cam, dict(close=False, kk=kk, tsplit=tsplit, alt=alt)


def sc_cuanto(img, t):
    k = shot_k("cuanto", t)
    spin = SPIN0 + 0.05 + 0.05 * k
    cam = mars_cam(4.6 - 0.3 * ease(k), 0.05 + 0.1 * k, 0.55, (-0.45, 0.45, 0), 0.0)
    draw_mars(img, cam, np.zeros(3), R_M, spin)
    A = alba_world(spin)
    gas_plume(img, cam, A * 1.004, A, t, 0.26, 0.045, 2.0, 3000)
    return cam, dict(A=A, k=k)


# corte del subsuelo (2D pintado, más alto que la pantalla)
CUT_H = 3000
SURF_Y = 700


def make_cut():
    path = os.path.join(BASE, "tex", "corte.npy")
    if os.path.exists(path):
        return np.load(path)
    yy, xx = np.mgrid[0:CUT_H, 0:W].astype(np.float64)
    n = fbm(xx / 160.0, yy / 60.0, np.full_like(xx, 5.0), 5, seed=17)
    n2 = fbm(xx / 40.0, yy / 40.0, np.full_like(xx, 6.0), 4, seed=18)
    surf = SURF_Y + 40 * np.sin(xx / 210.0) + 25 * (fbm(xx / 90.0, np.zeros_like(xx), np.zeros_like(xx), 4, seed=19) - 0.5)
    depth = yy - surf
    strata = np.sin(depth / 38.0 + n * 6.0) * 0.5 + 0.5
    rock = np.array([0.42, 0.22, 0.14]) * (0.7 + 0.3 * strata[..., None]) * (0.8 + 0.4 * n2[..., None])
    rock = rock * (1 - 0.55 * smooth(0, 2200, depth))[..., None]
    ice = smooth(20, 40, depth) * smooth(300, 230, depth)
    rock = rock * (1 - 0.25 * ice[..., None]) + np.array([0.30, 0.42, 0.55]) * 0.25 * ice[..., None] * (0.7 + 0.5 * n2[..., None])
    s = np.clip(-depth / 700.0, 0, 1)[..., None]
    sky = np.array([0.86, 0.64, 0.46]) * (1 - s ** 0.5) + np.array([0.30, 0.22, 0.20]) * s ** 0.5
    top = smooth(-2, 2, depth)[..., None]
    col = sky * (1 - top) + rock * top
    out = lin(np.clip(col, 0, 1)).astype(np.float32)
    np.save(path, out)
    return out


CUT = make_cut()
CHAMBER = (560.0, 2380.0)
_rngc = np.random.default_rng(23)


def crack_paths():
    paths = []
    for i, x_end in enumerate([300, 470, 640, 820]):
        pts = []
        steps = 40
        for j in range(steps + 1):
            f = j / steps
            y = CHAMBER[1] - 160 + (SURF_Y + 30 - (CHAMBER[1] - 160)) * f
            x = CHAMBER[0] + (x_end - CHAMBER[0]) * f ** 0.8 + 26 * math.sin(f * 17 + i * 2) + _rngc.normal() * 8
            pts.append((x, y))
        paths.append(pts)
    return paths


CRACKS = crack_paths()


def magma_view(t):
    k = shot_k("magma", t)
    tz = SPLIT("magma", 0.36)
    s = ease((t - tz) / 2.4)
    off = 0 + (CUT_H - H) * s
    return off, s, tz


def sc_magma(img, t):
    off, s, tz = magma_view(t)
    o = int(round(off))
    img[:] = CUT[o:o + H]
    # brillo de la cámara de magma
    yy, xx = np.mgrid[0:H // 4, 0:W // 4]
    cx_, cy_ = CHAMBER[0] / 4, (CHAMBER[1] - off) / 4
    rr = np.sqrt(((xx - cx_) / 1.0) ** 2 + ((yy - cy_) / 0.45) ** 2)
    pulse = 1 + 0.12 * math.sin(t * 3.0)
    core = np.clip(1 - rr / 48, 0, 1) ** 0.7
    halo = np.exp(-rr / 40) * 0.35
    g = np.zeros((H // 4, W // 4, 3), np.float32)
    g += core[..., None] * np.array([3.0, 1.2, 0.25]) * pulse + halo[..., None] * np.array([1.4, 0.4, 0.08]) * pulse
    img += ndzoom(g, (4, 4, 1), order=1)[:H, :W]
    return None, dict(off=off, s=s, tz=tz)


def sc_cierre(img, t):
    k = shot_k("cierre", t)
    spin = SPIN0 - 0.2 + 0.08 * t / 10
    cam = mars_cam(5.6 + 1.6 * ease(k), -0.35 + 0.2 * k, 0.40, (0.0, 0.10, 0))
    draw_mars(img, cam, np.zeros(3), R_M, spin)
    A = alba_world(spin)
    br = 0.75 + 0.45 * math.sin(t * 1.6) ** 2
    gas_plume(img, cam, A * 1.004, A, t, 0.26, 0.045, br * 1.8, 3000)
    return cam, dict(A=A, k=k)


SCENES = {"gancho": sc_gancho, "sonda": sc_sonda, "tierra": sc_tierra, "grietas": sc_grietas,
          "cuanto": sc_cuanto, "magma": sc_magma, "cierre": sc_cierre}


def proj1(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def tag(d, x, y, t, col, A, label, side=1, r0=34):
    marker(d, x, y, t, col, A, r0, label, side, 46)


def overlays(frame_u8, t, name, cam, ex):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    i = ORDER.index(name)
    a0 = SHOTS[i][1]; b0 = SHOTS[i + 1][1] if i + 1 < len(SHOTS) else END
    if name == "gancho":
        tw = ex["tw"]
        draw_label(layer, t, 0.0, tw, "¿PLANETA MUERTO?", ["así lo creíamos"], WHITE, 98)
        draw_label(layer, t, tw, b0 + 0.05, "SALE GAS", ["de las grietas de Marte"], YELLOW, 140)
        if ex["gk"] > 0.3:
            x, y, z = proj1(cam, ex["A"] * 1.03)
            tag(d, x, y, t, GREEN, int(255 * min(1, (ex["gk"] - 0.3) / 0.4) * fade(t, tw, b0, 0.2)), None)
    elif name == "sonda":
        draw_boxes(layer, cam, tgo_boxes(ex["P"], ex["R"], ex["s"]))
        tm = SPLIT("sonda", 0.30)
        draw_label(layer, t, a0, tm + 0.05, "EXOMARS TGO", ["sonda de la ESA", "en órbita de Marte"], CYAN, 128)
        draw_label(layer, t, tm + 0.05, b0 + 0.05, "HCl", ["cloruro de hidrógeno", "sobre Alba Mons"], YELLOW, 170)
        x, y, z = proj1(cam, ex["A"] * 1.0)
        A_ = int(255 * fade(t, tm + 0.3, b0, 0.25))
        if A_:
            tag(d, x, y, t, YELLOW, A_, "ALBA MONS", -1 if x > W * 0.55 else 1)
        # línea de medición sonda -> gas
        xs_, ys_, _ = proj1(cam, ex["P"])
        xg, yg, _ = proj1(cam, ex["A"] * 1.07)
        Am = int(200 * fade(t, a0 + 0.8, b0, 0.3))
        if Am:
            nseg = 22
            for j in range(nseg):
                if (j + int(t * 12)) % 2:
                    continue
                f0, f1 = j / nseg, (j + 0.6) / nseg
                d.line([(xs_ + (xg - xs_) * f0, ys_ + (yg - ys_) * f0), (xs_ + (xg - xs_) * f1, ys_ + (yg - ys_) * f1)], fill=CYAN + (Am,), width=5)
    elif name == "tierra":
        draw_label(layer, t, a0, b0 + 0.05, "EN LA TIERRA", ["este gas sale", "de los volcanes"], CYAN, 130)
        x, y, z = proj1(cam, ex["V"] * 1.0)
        A_ = int(255 * fade(t, a0 + 0.3, b0, 0.25))
        if A_:
            tag(d, x, y, t, ORANGE, A_, "VOLCÁN", -1)
    elif name == "grietas":
        if ex["close"]:
            draw_label(layer, t, a0, ex["tsplit"], "GRIETAS NUEVAS", ["nunca vistas en Marte"], YELLOW, 104)
            al = fade(t, a0 + 0.9, ex["tsplit"], 0.25)
            if al > 0:
                A_ = int(255 * al)
                xa, ya, _ = proj1(cam, np.array([ex["cx"], 0.0, -0.17]))
                xb, yb, _ = proj1(cam, np.array([ex["cx"], 0.0, 0.17]))
                y0 = min(ya, yb) - 30
                d.line([(xa, ya), (xb, yb)], fill=WHITE + (A_,), width=6)
                for xq, yq in ((xa, ya), (xb, yb)):
                    d.ellipse([xq - 10, yq - 10, xq + 10, yq + 10], fill=WHITE + (A_,))
                txt(d, (W / 2, y0 - 60), "unos palmos de ancho", 54, WHITE, A_, "Inter-ExtraBold.otf", 7)
        else:
            draw_label(layer, t, ex["tsplit"], b0 + 0.05, "DECENAS DE KM", ["en enjambres sobre", "las crestas"], YELLOW, 108)
            txt(d, (W / 2, 1760), "recreación · escala aproximada", 34, (230, 220, 210), int(200 * fade(t, ex["tsplit"], b0)), "Inter-ExtraBold.otf", 5)
    elif name == "cuanto":
        k = ex["k"]
        A1 = int(255 * fade(t, a0, b0 + 0.05, 0.25))
        pop = ease_out((t - a0 - 0.1) / 0.3)
        txt(d, (W / 2, 380), "< 3 KG/S", int(150 * (0.7 + 0.3 * pop)), YELLOW, A1)
        txt(d, (W / 2, 480), "menos de 3 kilos por segundo", 54, CYAN, A1, "Inter-ExtraBold.otf", 7)
        # comparación con volcanes de la Tierra
        tb = SPLIT("cuanto", 0.45)
        al = fade(t, tb, b0 + 0.05, 0.3)
        if al > 0:
            A_ = int(255 * al)
            gx0, gx1 = 140, W - 140
            sc = lambda v: gx0 + (gx1 - gx0) * math.log10(1 + v) / math.log10(1 + 150)
            gyy = 1040
            d.rounded_rectangle([gx0 - 30, gyy - 140, gx1 + 30, gyy + 150], 28, fill=(8, 10, 20, int(150 * al)))
            txt(d, (gx0, gyy - 95), "MARTE", 44, WHITE, A_, "Inter-Black.otf", 5, "lm")
            g = ease((t - tb) / 0.6)
            d.rounded_rectangle([gx0, gyy - 60, gx0 + max(16, (sc(3) - gx0) * g), gyy - 30], 12, fill=YELLOW + (A_,))
            txt(d, (gx0, gyy + 20), "VOLCANES DE LA TIERRA", 44, WHITE, A_, "Inter-Black.otf", 5, "lm")
            g2 = ease((t - tb - 0.3) / 0.9)
            d.rounded_rectangle([sc(3), gyy + 55, sc(3) + (sc(150) - sc(3)) * g2, gyy + 85], 12, fill=CYAN + (A_,))
            txt(d, (sc(3), gyy + 120), "unos pocos", 34, CYAN, A_, "Inter-ExtraBold.otf", 4, "lm")
            txt(d, (gx1, gyy + 120), "+100 kg/s", 34, CYAN, A_, "Inter-ExtraBold.otf", 4, "rm")
            d.line([(sc(3), gyy - 70), (sc(3), gyy + 95)], fill=WHITE + (int(150 * al),), width=3)
        x, y, z = proj1(cam, ex["A"] * 1.0)
    elif name == "magma":
        off, s, tz = ex["off"], ex["s"], ex["tz"]
        # grietas y gas que sube por ellas
        Ac = int(255 * min(1, s * 1.5))
        for pi_, pts in enumerate(CRACKS):
            pp = [(x, y - off) for x, y in pts]
            d.line(pp, fill=(18, 10, 8, max(Ac, 120)), width=9)
            d.line(pp, fill=(255, 150, 60, int(Ac * 0.45)), width=3)
            if s > 0.3:
                for j in range(9):
                    f = ((t * 0.28 + j / 9 + pi_ * 0.13) % 1.0)
                    idx = f * (len(pp) - 1); i0 = int(idx); fr = idx - i0
                    x = pp[i0][0] * (1 - fr) + pp[min(i0 + 1, len(pp) - 1)][0] * fr
                    y = pp[i0][1] * (1 - fr) + pp[min(i0 + 1, len(pp) - 1)][1] * fr
                    glow(layer, x, y, 26, GREEN, 200 * min(1, (s - 0.3) / 0.3))
        # gas saliendo a la superficie
        for pi_, pts in enumerate(CRACKS):
            x0, y0 = pts[-1][0], pts[-1][1] - off
            for j in range(6):
                f = (t * 0.35 + j / 6 + pi_ * 0.21) % 1.0
                glow(layer, x0 + 40 * f * math.sin(j + t), y0 - 260 * f, 30 + 50 * f, GREEN, 150 * (1 - f))
        draw_label(layer, t, a0, tz + 0.3, "SIN ERUPCIÓN", ["nadie ha visto una"], WHITE, 130, 330)
        draw_label(layer, t, tz + 0.3, b0 + 0.05, "¿MAGMA ACTIVO?", ["es la hipótesis", "de los científicos"], YELLOW, 104, 330)
        ys = SURF_Y - off
        if -50 < ys < H:
            txt(d, (W - 60, ys + 120), "hielo", 40, (200, 230, 255), int(220 * fade(t, a0 + 0.3, b0)), "Inter-ExtraBold.otf", 5, "rm")
        yc = CHAMBER[1] - off
        if yc < H - 60:
            txt(d, (CHAMBER[0], yc + 170), "MAGMA", 60, ORANGE, int(255 * min(1, s * 2) * fade(t, a0, b0 + 1, 0.2)), "Inter-Black.otf", 7)
        txt(d, (W / 2, 1830), "recreación · no está a escala", 34, (230, 220, 210), int(200 * fade(t, a0 + 0.3, b0)), "Inter-ExtraBold.otf", 5)
    elif name == "cierre":
        draw_label(layer, t, a0 + 0.1, CARD + 0.1, "DORMIDO,", ["no muerto"], YELLOW, 150)
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


LIGHT_MARS = np.array([-0.62, 0.42, 0.66]); LIGHT_MARS /= np.linalg.norm(LIGHT_MARS)
LIGHT_END = np.array([-0.85, 0.25, 0.30]); LIGHT_END /= np.linalg.norm(LIGHT_END)


def render(t):
    global LIGHT
    name = scene(t)
    LIGHT = LIGHT_END if name == "cierre" else LIGHT_MARS
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
        print("frames", NFRAMES, "shots", [(a, round(b, 2)) for a, b in SHOTS], "card", round(CARD, 2))
