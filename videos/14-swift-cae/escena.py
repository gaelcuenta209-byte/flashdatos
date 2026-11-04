"""Flash Datos · video 14: el telescopio Swift de la NASA cae a la Tierra.

Escena nueva: el observatorio Swift armado en 3D (cuerpo, BAT, telescopios y paneles),
un estallido de rayos gamma con chorros, la órbita en espiral sobre una atmósfera que se infla
con el Sol, el robot de rescate que pierde el control, la reentrada con plasma y la ruptura en pedazos.

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
ORDER = ["hook1", "swift", "record", "frenado", "rescate", "reentrada", "riesgo", "cierre"]
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
HL_WORDS = {"swift", "nasa", "gamma", "robot"}


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


# ---------------- Swift, robot y efectos ----------------
R_E = 6371.0
M = 0.001  # un metro en km


def heat_col(col, h):
    hot = np.array([255, 120, 45], float)
    c = np.asarray(col, float) * (1 - 0.75 * h) + hot * 0.75 * h
    return tuple(int(min(255, x)) for x in c)


def swift_boxes(pos, R, h=0.0, s=M):
    white = (226, 228, 236); gold = (216, 172, 74); grey = (150, 156, 168); panel = (34, 60, 128); dark = (60, 64, 76)
    hb = lambda c: heat_col(c, h)
    out = [(pos, (0.75 * s, 1.35 * s, 0.75 * s), R, hb(gold)),                                   # cuerpo con mylar dorado
           (pos + R @ np.array([0, 1.62 * s, 0]), (1.45 * s, 0.26 * s, 0.95 * s), R, hb(grey)),   # BAT (máscara codificada)
           (pos + R @ np.array([0, 1.92 * s, 0]), (1.30 * s, 0.04 * s, 0.82 * s), R, hb(dark)),
           (pos + R @ np.array([0.40 * s, -0.10 * s, 0.95 * s]), (0.28 * s, 0.28 * s, 0.55 * s), R, hb(white)),   # XRT
           (pos + R @ np.array([-0.42 * s, -0.25 * s, 0.85 * s]), (0.20 * s, 0.20 * s, 0.45 * s), R, hb(white))]  # UVOT
    for side in (-1, 1):
        out.append((pos + R @ np.array([side * 0.95 * s, 0, 0]), (0.20 * s, 0.05 * s, 0.05 * s), R, hb(grey)))
        for k in (0, 1):
            off = R @ np.array([side * (1.75 + 1.25 * k) * s, 0, 0])
            out.append((pos + off, (0.60 * s, 0.04 * s, 0.95 * s), R, hb(panel)))
    return out


def link_boxes(pos, R, s=M, arm=1.0):
    body = (200, 204, 214); panel = (40, 66, 132); orange = (240, 140, 50)
    out = [(pos, (0.9 * s, 0.9 * s, 0.9 * s), R, body),
           (pos + R @ np.array([0, 0, 0.95 * s]), (0.7 * s, 0.7 * s, 0.05 * s), R, orange)]
    for side in (-1, 1):
        out.append((pos + R @ np.array([side * 2.0 * s, 0, 0]), (1.0 * s, 0.04 * s, 0.7 * s), R, panel))
    for i in range(3):
        a = i * 2 * math.pi / 3 + 0.5
        dirv = np.array([math.cos(a) * 0.55, math.sin(a) * 0.55, -1.0]); dirv /= np.linalg.norm(dirv)
        L = (1.0 + 1.0 * arm) * s
        c = dirv * (0.9 * s + L / 2)
        yaw = math.atan2(dirv[0], dirv[2]); pitch = -math.asin(dirv[1])
        Ra = R @ rotm(yaw, pitch)
        out.append((pos + R @ c, (0.09 * s, 0.09 * s, L / 2), Ra, (230, 232, 238)))
    return out


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


def plasma(img, cam, P, vdir, h, length, seed, n=900, width=1.0):
    """Estela de plasma detrás de la nave (HDR)."""
    if h <= 0.01:
        return
    rng = np.random.default_rng(seed)
    vdir = np.asarray(vdir, float); vdir /= np.linalg.norm(vdir)
    a = np.cross(vdir, [0, 1, 0]); a /= np.linalg.norm(a); b = np.cross(vdir, a)
    u = rng.random(n) ** 1.6
    spread = (0.6 + 2.2 * u) * M * 1.2 * width
    off = (rng.normal(size=n)[:, None] * a + rng.normal(size=n)[:, None] * b) * spread[:, None]
    Pp = np.asarray(P) - vdir * (u * length + 1.2 * M)[:, None] + off
    hot = np.exp(-u * 3.0)
    col = (np.array([3.2, 2.6, 1.8]) * hot[:, None] + np.array([2.4, 0.8, 0.2]) * (1 - hot)[:, None]) * (h * (0.5 + 0.5 * rng.random(n)))[:, None] * 1.1
    splat(img, cam, Pp, col, 1.0)


def sat_frame(t, alt=270.0, speed=0.0):
    P = np.array([0.0, R_E + alt, 0.0])
    return P


def scene(t):
    for i, tf in enumerate(FL):
        if t < tf:
            return ORDER[i]
    return ORDER[-1]


SUN_DIR = LIGHT


def gamma_burst(img, cam, P, ts, k=1.0):
    if ts < 0:
        return
    a = math.exp(-ts / 0.35) * 6 + 0.9 * math.exp(-ts / 3.0)
    rng = np.random.default_rng(5)
    jet = np.array([0.35, 0.94, 0.0]); jet /= np.linalg.norm(jet)
    n = 600
    u = rng.random(n) ** 1.3 * min(1.0, ts / 0.6 + 0.2)
    sgn = np.where(rng.random(n) < 0.5, -1, 1)
    side = np.cross(jet, cam.f); side /= np.linalg.norm(side) + 1e-9
    D = float(np.linalg.norm(P - cam.O))
    Pp = P + (sgn * u * D * 0.10)[:, None] * jet + (rng.normal(size=n) * u * D * 0.006)[:, None] * side
    col = np.broadcast_to(np.array([1.1, 0.9, 2.6]) * a * 0.18 * k, (n, 3)) * (1 - u[:, None] * 0.7)
    splat(img, cam, Pp, col, 1.0)
    splat(img, cam, P[None, :], np.array([[2.4, 2.2, 3.0]]) * a * 60 * k, 1.0)


GRB_DIR = np.array([-0.55, 0.75, -0.45]); GRB_DIR /= np.linalg.norm(GRB_DIR)
GRB_T = SPLIT("swift", 0.40)


def cam_close(P, off, look=(0.0, -0.4, 0.0), roll=0.0):
    return Cam(P + np.asarray(off) * M, P + np.asarray(look) * M, roll)


def sc_hook1(img, t):
    P = sat_frame(t, 250)
    k = t / (S1["hook1"] + 0.3)
    cam = cam_close(P, (-6.0 + 3.0 * k, 3.5, 30.0 - 5.0 * k), (1.5, 1.2, 0.0), 0.05)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    h = 0.15 + 0.6 * ease(k)
    plasma(img, cam, P, (1, -0.08, 0), h, 22 * M * (0.4 + h), int(t * 30))
    return cam, dict(P=P, R=rotm(0.35 + 0.25 * t, 0.15, 0.25 * math.sin(t * 1.3)), h=h * 0.6)


def sc_swift(img, t):
    P = sat_frame(t, 560)
    k = (t - FL[0]) / (FL[1] - FL[0])
    cam = cam_close(P, (8.0 - 6 * k, 3.0, 26.0), (0.0, 2.2, 0.0))
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    bd = cam.dirs(720, 721, 790, 791)[0, 0]
    B = cam.O + bd * 4.0e5
    gamma_burst(img, cam, B, t - GRB_T)
    turn = ease((t - GRB_T - 0.1) / 1.1)   # Swift gira rápido hacia el estallido
    yaw = 0.9 * (1 - turn) + (math.atan2(bd[0], bd[2])) * turn
    pit = -0.6 * turn
    return cam, dict(P=P, R=rotm(yaw, pit, 0.0), h=0.0, B=B)


def orbit_pts(r, inc=math.radians(20.6), n=240, a0=0.0, a1=2 * math.pi):
    a = np.linspace(a0, a1, n)
    P = np.stack([np.cos(a) * r, np.zeros_like(a), -np.sin(a) * r], -1)
    return P @ rotm(0, inc, 0).T


def sc_record(img, t):
    k = (t - FL[1]) / (FL[2] - FL[1])
    cpos = np.array([0.0, 9000.0, 30000.0]) * (1.0 - 0.06 * k)
    cam = Cam(cpos, np.array([0.0, 400.0, 0.0]))
    draw_earth(img, cam, np.zeros(3), R_E, t)
    return cam, dict(k=k)


VIS_R0, VIS_R1 = R_E + 2200, R_E + 260   # altura exagerada para que se vea


def spiral_r(s):
    return VIS_R0 + (VIS_R1 - VIS_R0) * s ** 1.6


def sc_frenado(img, t):
    k = (t - FL[2]) / (FL[3] - FL[2])
    cpos = np.array([-6000.0, 7000.0, 27000.0])
    cam = Cam(cpos, np.array([1800.0, 0.0, 0.0]))
    sun = cam.O + SUN_DIR * 1.0e6
    splat(img, cam, sun[None, :], np.array([[3.0, 2.5, 1.6]]) * (60 + 15 * math.sin(t * 3)), 1.0)
    atm = 0.012 + 0.05 * ease((k - 0.3) / 0.4) * (1 + 0.08 * math.sin(t * 5))
    draw_earth(img, cam, np.zeros(3), R_E, t, atm, 0.55 + 1.2 * ease((k - 0.3) / 0.4))
    return cam, dict(k=k, atm=atm, sun=sun)


def sc_rescate(img, t):
    P = sat_frame(t, 300)
    k = (t - FL[3]) / (FL[4] - FL[3])
    cam = cam_close(P, (5.0, 3.5, 36.0), (4.2, 1.5, 0.0))
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.012, 0.9)
    tfail = SPLIT("rescate", 0.52)
    app = ease((t - FL[3]) / (tfail - FL[3]))
    Lp = P + np.array([13.0 - 5.0 * app, 0.6, 1.0]) * M
    if t > tfail:
        dt = t - tfail
        Lp = Lp + np.array([2.2 * dt, 1.0 * dt, -1.5 * dt]) * M
        RL = rotm(math.pi / 2 + 2.6 * dt * dt + 1.2 * dt, 1.9 * dt, 2.2 * dt)
    else:
        RL = rotm(math.pi / 2 + 0.05 * math.sin(t), 0, 0)
    return cam, dict(P=P, R=rotm(0.5 + 0.08 * t, 0.1, 0.0), h=0.0, L=Lp, RL=RL, fail=tfail)


def sc_reentrada(img, t):
    P = sat_frame(t, 90)
    k = (t - FL[4]) / (FL[5] - FL[4])
    sh = 0.25 * M * math.sin(t * 61) * (1 + k)
    cam = cam_close(P, (-8.0 + 3.0 * k, 3.5 + sh / M, 38.0 - 6 * k), (3.0, 1.5, 0.0), 0.06)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.016, 1.3)
    h = 0.75 + 0.25 * ease(k * 2)
    plasma(img, cam, P, (1, -0.12, 0), h, 70 * M, int(t * 30), 1500, 1.8)
    return cam, dict(P=P, R=rotm(0.6 + 0.9 * t, 0.3 * math.sin(t * 2), 0.4 * t), h=h)


def frag_state(t, i, rng):
    ts = max(0.0, t - FL[5])
    d = rng.normal(size=3); d /= np.linalg.norm(d)
    v = (0.6 + 1.6 * rng.random()) * M * 1.8
    return d * v * ts * (1 + 0.4 * ts), rotm(rng.random() * 6 + ts * rng.normal() * 3, ts * rng.normal() * 2, ts * rng.normal() * 2)


def sc_riesgo(img, t):
    P = sat_frame(t, 80)
    k = (t - FL[5]) / (FL[6] - FL[5])
    cam = cam_close(P, (-2.0, 4.0, 55.0 + 10 * k), (3.0, 2.0, 0.0), 0.06)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.016, 1.3)
    rng = np.random.default_rng(3)
    frs = []
    for i in range(14):
        off, R = frag_state(t, i, rng)
        life = 1 - ease((k - 0.25 - 0.04 * i) / 0.45)
        frs.append((P + off, R, life))
        if life > 0.02:
            plasma(img, cam, P + off, (1, -0.12, 0), life, 18 * M, int(t * 30) + i * 7, 160, 0.5)
    return cam, dict(P=P, frs=frs, k=k)


def sc_cierre(img, t):
    k = (t - FL[6]) / (END - FL[6])
    P = sat_frame(t, 300)
    cam = cam_close(P, (0.0, 1500.0, 2600.0 - 600 * ease(k)), (0.0, -900.0, -6000.0), 0.0)
    draw_earth(img, cam, np.zeros(3), R_E, t, 0.014, 0.9)
    s = ease((t - FL[6]) / 2.4)
    if s < 1:
        Q = np.array([-1200.0 + 2400 * s, R_E + 70.0, -2600.0])
        rng = np.random.default_rng(int(t * 30))
        n = 300
        u = rng.random(n)
        Pp = Q - np.array([1.0, 0.02, 0]) * (u * 380)[:, None]
        col = np.broadcast_to(np.array([3.0, 1.6, 0.6]) * (1 - s) * 0.5, (n, 3)) * (1 - u[:, None])
        splat(img, cam, Pp, col, 1.0)
    return cam, dict(k=k)


SCENES = {"hook1": sc_hook1, "swift": sc_swift, "record": sc_record, "frenado": sc_frenado, "rescate": sc_rescate,
          "reentrada": sc_reentrada, "riesgo": sc_riesgo, "cierre": sc_cierre}


def proj1(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def overlays(frame_u8, t, name, cam, ex):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if name in ("hook1", "swift", "rescate", "reentrada"):
        if name == "rescate":
            draw_boxes(layer, cam, link_boxes(ex["L"], ex["RL"], M, 1.0) + swift_boxes(ex["P"], ex["R"], 0.0))
        else:
            draw_boxes(layer, cam, swift_boxes(ex["P"], ex["R"], ex["h"]))
        if ex["h"] > 0:
            x, y, _ = proj1(cam, ex["P"] + np.array([1.2, 0, 0]) * M)
            glow(layer, x, y, 360 * (0.5 + ex["h"]), (255, 140, 50), 170 * ex["h"])
            glow(layer, x, y, 140 * (0.5 + ex["h"]), (255, 235, 190), 150 * ex["h"])
    if name == "hook1":
        draw_label(layer, t, 0.0, FL[0] + 0.05, "HOY · 4 NOV", ["El telescopio Swift de la NASA", "vuelve a la Tierra"], YELLOW, 120)
    elif name == "swift":
        tl = GRB_T - 0.1
        draw_label(layer, t, FL[0], tl, "SWIFT", ["NASA · lanzado en 2004"], CYAN, 150)
        draw_label(layer, t, tl, FL[1] + 0.05, "RAYOS GAMMA", ["las explosiones más", "poderosas del universo"], YELLOW, 118)
        x, y, z = proj1(cam, ex["B"])
        if z > 0 and t > GRB_T + 0.3:
            marker(d, x, y, t, CYAN, int(255 * fade(t, GRB_T + 0.3, FL[1] + 0.05, 0.2)), 54, None)
    elif name == "record":
        k = ex["k"]
        r = R_E + 900
        P = orbit_pts(r)
        x, y, z = cam.proj(P)
        front = z < float(np.linalg.norm(cam.O)) - 1500
        pts = list(zip(x.tolist(), y.tolist()))
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=CYAN + (230 if front[i] else 80,), width=5)
        a = t * 2.2
        xs_, ys_, _ = proj1(cam, orbit_pts(r, n=2, a0=a, a1=a + 0.01)[0])
        d.ellipse([xs_ - 14, ys_ - 14, xs_ + 14, ys_ + 14], fill=YELLOW + (255,))
        tmid = SPLIT("record", 0.45)
        A1 = int(255 * fade(t, FL[1], 99, 0.25))
        if t < tmid + 0.25:
            A = int(A1 * (1 - ease((t - tmid) / 0.25)))
            txt(d, (W / 2, 390), "2 AÑOS", 150, WHITE, A)
            txt(d, (W / 2, 490), "lo que iba a durar", 54, CYAN, A, "Inter-ExtraBold.otf", 7)
        if t > tmid:
            A = int(A1 * ease((t - tmid) / 0.25))
            n = int(round(2 + 20 * ease((t - tmid) / 1.4)))
            txt(d, (W / 2, 390), f"{n} AÑOS", 170, YELLOW, A)
            txt(d, (W / 2, 495), "más de 10 veces lo planeado", 54, CYAN, A, "Inter-ExtraBold.otf", 7)
        # barra
        bx0, bx1, by = 160, W - 160, 600
        A = int(220 * fade(t, FL[1], 99, 0.25))
        d.rounded_rectangle([bx0, by - 16, bx1, by + 16], 16, outline=WHITE + (A,), width=4)
        fill = (2 + 20 * ease((t - tmid) / 1.4)) / 22 if t > tmid else 2 / 22
        d.rounded_rectangle([bx0 + 6, by - 10, bx0 + 6 + (bx1 - bx0 - 12) * fill, by + 10], 10, fill=YELLOW + (A,))
    elif name == "frenado":
        k = ex["k"]
        sp = np.linspace(0, 1, 400)
        turns = 4.0
        ang = -sp * turns * 2 * math.pi - 0.6
        rr = spiral_r(sp)
        P = np.stack([np.cos(ang) * rr, np.zeros_like(ang), -np.sin(ang) * rr], -1) @ rotm(0, math.radians(20.6), 0).T
        x, y, z = cam.proj(P)
        dist_c = float(np.linalg.norm(cam.O))
        s_now = min(1.0, 0.05 + 0.95 * ease((k - 0.05) / 0.9))
        nn = int(s_now * 399)
        for i in range(nn):
            behind = z[i] > dist_c - 200 and math.hypot(x[i] - proj1(cam, np.zeros(3))[0], y[i] - proj1(cam, np.zeros(3))[1]) < 0
            col = YELLOW if i > nn - 80 else CYAN
            al = 230 if i > nn - 80 else 120
            d.line([(x[i], y[i]), (x[i + 1], y[i + 1])], fill=col + (al,), width=5)
        d.ellipse([x[nn] - 14, y[nn] - 14, x[nn] + 14, y[nn] + 14], fill=WHITE + (255,), outline=YELLOW + (255,), width=4)
        t2 = SPLIT("frenado", 0.25)
        draw_label(layer, t, FL[2], t2 + 0.1, "SIN MOTOR", ["no puede subir solo"], WHITE, 140)
        draw_label(layer, t, t2 + 0.1, FL[3] + 0.05, "EL SOL INFLA", ["la atmósfera y el aire", "lo va frenando"], YELLOW, 120)
        txt(d, (W / 2, 1760), "altura exagerada para que se vea", 34, (200, 210, 230), int(200 * fade(t, FL[2] + 0.3, FL[3])), "Inter-ExtraBold.otf", 5)
    elif name == "rescate":
        tf = ex["fail"]
        x, y, _ = proj1(cam, ex["L"])
        A = int(255 * fade(t, FL[3] + 0.3, tf, 0.2))
        if A:
            marker(d, x, y, t, CYAN, A, 70, "ROBOT", -1 if x > W / 2 else 1, 46)
        draw_label(layer, t, FL[3], tf, "RESCATE", ["robot LINK · julio de 2026"], CYAN, 140)
        al = fade(t, tf, FL[4] + 0.05, 0.15)
        if al > 0:
            A = int(255 * al)
            pop = ease_out((t - tf) / 0.25)
            f = font("Inter-Black.otf", int(104 * (0.8 + 0.2 * pop)))
            lab = "CANCELADO"
            tw = d.textlength(lab, font=f)
            d.rounded_rectangle([W / 2 - tw / 2 - 34, 330, W / 2 + tw / 2 + 34, 470], 26, fill=(40, 6, 6, int(210 * al)), outline=RED + (A,), width=7)
            d.text((W / 2, 400), lab, font=f, fill=RED + (A,), anchor="mm")
            txt(d, (W / 2, 535), "perdió el control · agosto de 2026", 52, WHITE, A, "Inter-ExtraBold.otf", 7)
    elif name == "reentrada":
        tm = SPLIT("reentrada", 0.45)
        draw_label(layer, t, FL[4], tm + 0.1, "≈1,500 KG", ["casi mil quinientos kilos"], WHITE, 140)
        draw_label(layer, t, tm + 0.1, FL[5] + 0.05, "+27,000 KM/H", ["unos 7.5 km cada segundo"], YELLOW, 118)
    elif name == "riesgo":
        boxes = []
        rng = np.random.default_rng(8)
        cols = [(226, 228, 236), (216, 172, 74), (34, 60, 128), (150, 156, 168)]
        for i, (Pf, R, life) in enumerate(ex["frs"]):
            if life <= 0.02:
                continue
            hs = (0.15 + 0.45 * rng.random(3)) * M * (0.6 + 0.4 * life)
            boxes.append((Pf, tuple(hs), R, heat_col(cols[i % 4], 0.9)))
            x, y, _ = proj1(cam, Pf)
            glow(layer, x, y, 90 * life, (255, 160, 70), 130 * life)
        draw_boxes(layer, cam, boxes)
        tm = SPLIT("riesgo", 0.32)
        draw_label(layer, t, FL[5], tm + 0.1, "CASI TODO", ["se quema en el aire"], WHITE, 140)
        draw_label(layer, t, tm + 0.1, FL[6] + 0.05, "1 EN 2,100", ["probabilidad de que", "un trozo lastime a alguien"], YELLOW, 140)
    elif name == "cierre":
        draw_label(layer, t, FL[6] + 0.1, CARD + 0.1, "GRACIAS, SWIFT", ["2004 – 2026"], YELLOW, 112)
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


LIGHT_DAY = LIGHT.copy()
LIGHT_NIGHT = np.array([0.25, -0.12, -1.0]); LIGHT_NIGHT /= np.linalg.norm(LIGHT_NIGHT)


def render(t):
    global LIGHT
    name = scene(t)
    LIGHT = LIGHT_NIGHT if name in ("reentrada", "riesgo") else LIGHT_DAY
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
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL], "card", round(CARD, 2), "grb", round(GRB_T, 2))
