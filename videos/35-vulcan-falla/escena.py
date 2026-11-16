"""Flash Datos · video 35: el Vulcan de ULA falló y se perdieron 40 satélites de Amazon Leo (15 nov 2026).

Escena nueva: 40 puntos de luz que suben desde la Tierra y se apagan antes de llegar a la órbita; el Vulcan
(primera etapa naranja, seis propulsores sólidos) despegando junto al mar en Cabo Cañaveral; la separación de
los propulsores a T+1:40 en el cielo alto; la etapa Centaur con su pila de satélites que se bambolea hasta la
anomalía de T+10:00; la trayectoria que se queda corta de la órbita prevista; los cinco vuelos del Vulcan en
fila; el globo con ~400 satélites de Amazon contra la meta de 3,200; y la nube de Starlink. Base técnica:
mallas y partículas de los videos 30 y 34.

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
# ---------------- línea de tiempo (video 35) ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
SPLIT = lambda k, f: S0[k] + (S1[k] - S0[k]) * f
ORDER = ["gancho", "cohete", "normal", "falla", "perdida", "primera", "amazon", "cierre"]
SHOTS = [("gancho", 0.0)] + [(k, S0[k] - 0.2) for k in ORDER[1:]]
FL = [b for _, b in SHOTS[1:]]
CARD = S1["cierre"] + 0.2
TGONE = SPLIT("gancho", 0.62)               # "…y ninguno llegó"
TLIFT = S0["cohete"] + 0.9                  # despegue
TSRB = SPLIT("normal", 0.40)                # se sueltan los propulsores (T+1:40)
TWOB = SPLIT("falla", 0.22)                 # empieza a girar raro
TANOM = SPLIT("falla", 0.70)                # "a los diez minutos, algo salió mal"
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




# ================= video 35: Vulcan, Centaur y satélites =================
LIGHTS["high"] = dict(L=(-0.50, 0.55, 0.65), sun=(2.5, 2.35, 2.15), hor=(0.30, 0.48, 0.78), zen=(0.006, 0.012, 0.045),
                      amb=(0.12, 0.15, 0.22), sand=(0.40, 0.42, 0.40), sea=(0.03, 0.08, 0.16), fog=(0.42, 0.58, 0.82))
LIGHTS["pad"] = dict(L=(-0.55, 0.62, 0.55), sun=(2.5, 2.30, 2.05), hor=(0.70, 0.80, 0.92), zen=(0.16, 0.34, 0.74),
                     amb=(0.22, 0.27, 0.36), sand=(0.36, 0.42, 0.26), sea=(0.04, 0.13, 0.24), fog=(0.70, 0.80, 0.92))

VORANGE = (0.82, 0.46, 0.20); VWHITE = (0.88, 0.88, 0.90); VSIL = (0.70, 0.72, 0.76); VDARK = (0.10, 0.10, 0.11)
SRBW = (0.80, 0.80, 0.80); GOLD = (0.78, 0.60, 0.22); PANEL = (0.10, 0.13, 0.25)
RV = 2.7                     # radio del Vulcan (5.4 m)
SRB_ANG = [math.radians(a) for a in (30, 75, 120, 210, 255, 300)]
RE_KM = 6371.0


def xform(faces, R, pos):
    pos = np.asarray(pos, float)
    return [(v @ R.T + pos, R @ n, c, s, e) for v, n, c, s, e in faces]


def srb_mesh(f, a):
    x, z = math.cos(a) * (RV + 0.85), math.sin(a) * (RV + 0.85)
    p = np.array([x, 0.0, z]); I = np.eye(3)
    cyl(f, I, p, -1.6, 0.6, 0.45, 0.8, n=12, col=VDARK, spec=0.2)
    cyl(f, I, p, 0.6, 21.5, 0.8, 0.8, n=12, col=SRBW, spec=0.35)
    cyl(f, I, p, 21.5, 24.5, 0.8, 0.05, n=12, col=SRBW, spec=0.35)


def vulcan_mesh(srbs=True, booster=True, upper=True, fairing=True, n=26):
    """Vulcan en coordenadas locales (m): base del cohete en y=0, eje +y."""
    f = []; I = np.eye(3); o = np.zeros(3)
    if booster:
        for dx in (-1.2, 1.2):                                        # dos motores BE-4
            cyl(f, I, np.array([dx, 0, 0]), -2.4, 0.0, 1.05, 0.55, n=12, col=VDARK, spec=0.3)
        cyl(f, I, o, 0.0, 1.0, RV * 0.94, RV, n=n, col=VDARK, spec=0.2)
        for y0, y1 in ((1, 12), (12, 23), (23, 33)):
            cyl(f, I, o, y0, y1, RV, RV, n=n, col=VORANGE, spec=0.18)
        cyl(f, I, o, 33, 35, RV, RV, n=n, col=VDARK, spec=0.2)       # interetapa
        if srbs:
            for a in SRB_ANG:
                srb_mesh(f, a)
    if upper:
        if not booster:
            cyl(f, I, o, 32.6, 35.0, 1.1, 0.35, n=12, col=VSIL, spec=0.5)   # tobera RL10
        cyl(f, I, o, 35, 47, RV, RV, n=n, col=VSIL, spec=0.55)
        cyl(f, I, o, 47, 47.6, RV, RV * 0.96, n=n, col=VDARK, spec=0.2)
        if fairing:
            cyl(f, I, o, 47.6, 61, RV * 1.02, RV * 1.02, n=n, col=VWHITE, spec=0.3)
            prof = [(61, 1.02), (64, 0.86), (66.5, 0.60), (68.2, 0.30), (69.0, 0.06)]
            for (y0, f0), (y1, f1) in zip(prof[:-1], prof[1:]):
                cyl(f, I, o, y0, y1, RV * f0, RV * f1, n=n, col=VWHITE, spec=0.3)
        else:                                                         # pila de 40 satélites (10 capas × 4)
            cyl(f, I, o, 47.6, 48.6, 1.2, 1.0, n=12, col=VDARK)
            for k in range(10):
                y = 49.2 + k * 1.15
                for j in range(4):
                    a = j * math.pi / 2 + 0.785
                    c = np.array([math.cos(a) * 1.25, y, math.sin(a) * 1.25])
                    boxf(f, c, (1.05, 0.45, 0.75), rotm(-a), GOLD if k % 2 == 0 else (0.62, 0.64, 0.70), 0.6)
    return f


def vul_engines(img, cam, R, pos, t, k_main, k_srb, srb_on=True, L=1.0, seed=0, srb_off=None):
    pos = np.asarray(pos, float); down = R @ np.array([0, -1.0, 0])
    for dx in (-1.2, 1.2):
        plume(img, cam, pos + R @ np.array([dx, -2.4, 0]), down, 34 * L, 0.9, 900, t, 1.3 * k_main, seed + int(dx > 0), 0.9)
    if srb_on:
        for i, a in enumerate(SRB_ANG):
            b = pos + R @ np.array([math.cos(a) * (RV + 0.85), -1.6, math.sin(a) * (RV + 0.85)])
            plume(img, cam, b, down, 40 * L, 0.8, 700, t, 1.5 * k_srb, seed + 7 + i, 1.1)


def vis_mask(cam, P, r=RE_KM):
    d = P - cam.O; L = np.linalg.norm(d, axis=1); d = d / L[:, None]
    oc = cam.O; b = d @ oc; c = oc @ oc - r * r
    disc = b * b - c
    tt = -b - np.sqrt(np.maximum(disc, 0))
    return (disc <= 0) | (tt <= 0) | (tt >= L - 1.0)


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def poly3d(d, cam, P_list, col, A, width=6, dash=0):
    P = np.asarray(P_list, float)
    x, y, z = cam.proj(P); ok = (z > 0) & vis_mask(cam, P)
    for i in range(len(P) - 1):
        if ok[i] and ok[i + 1] and (dash == 0 or (i // dash) % 2 == 0):
            d.line([(x[i], y[i]), (x[i + 1], y[i + 1])], fill=col + (A,), width=width)


def geo(lat, lon, t, r=RE_KM):
    """Punto de la superficie (lat, lon en grados) en el globo de draw_earth en el tiempo t."""
    la, lo = math.radians(lat), math.radians(lon)
    loc = np.array([math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)])
    A = -1.72 + 0.03 * t
    return rot_x(rot_y(loc, -A), math.radians(-16)) * r


def shell(nsat, seed, incs, r, t, w=0.05):
    rng = np.random.default_rng(seed)
    inc = rng.choice(np.radians(incs), nsat)
    raan = rng.random(nsat) * 2 * np.pi
    u = rng.random(nsat) * 2 * np.pi + w * t
    x = np.cos(u); y = np.sin(u)
    # plano orbital: rotar por inclinación (eje x) y RAAN (eje y)
    px, py, pz = x, y * np.sin(inc), y * np.cos(inc)
    X = px * np.cos(raan) + pz * np.sin(raan); Z = -px * np.sin(raan) + pz * np.cos(raan)
    return np.stack([X, py, Z], 1) * r


def dots(img, cam, P, col, k):
    if len(P) == 0 or k <= 0:
        return
    m = vis_mask(cam, P)
    P = P[m]
    splat2(img, cam, P, np.tile(np.array(col, np.float32) * k, (len(P), 1)), 0.9, 0.45)


def scene(t):
    name = SHOTS[0][0]
    for a, b in SHOTS:
        if t >= b:
            name = a
    return name


def t0_of(name):
    return dict(SHOTS)[name]


# 1 · gancho: 40 luces suben desde Florida hacia la órbita… y se apagan
def gancho_pts(t):
    rng = np.random.default_rng(4)
    delay = np.arange(40) * 0.045
    s = np.clip((t - 0.2 - delay) / 3.0, 0, 1)
    th = 0.03 + 0.80 * (1 - (1 - s) ** 3) + rng.normal(0, 0.006, 40) * s
    h = 1 + 0.10 * np.sin(np.clip(th / 0.8, 0, 1) * math.pi / 2) ** 0.8 + rng.normal(0, 0.003, 40) * s
    if t > TGONE:                                                       # caen de vuelta, ya apagadas
        h = h - 0.03 * (t - TGONE) ** 2
    lat_off = rng.normal(0, 0.012, 40) * s
    n0 = unit(geo(28.5, -80.6, 40.0)); e = unit(np.cross(np.array([0.25, 1.0, 0.1]), n0))
    e = unit(e * 0.7 + np.cross(n0, e) * 0.5)
    side = np.cross(n0, e)
    return [(n0 * math.cos(a) + e * math.sin(a) + side * lo) * RE_KM * hh for a, hh, lo in zip(th, h, lat_off)], n0, e


def sc_gancho(img, t):
    u = t / FL[0]
    pts, n0, e = gancho_pts(t)
    mid = unit(n0 + e * 0.40)
    side = unit(np.cross(n0, e))
    cpos = mid * RE_KM * (3.2 - 0.25 * u) + side * 5200 - e * 2600
    cam = Cam(cpos, unit(n0 + e * 0.30) * RE_KM * 0.95)
    draw_earth(img, cam, np.zeros(3), RE_KM, 40.0, atm=0.02, glow=0.9)
    P = np.array(pts)
    if t < TGONE:
        dots(img, cam, P, (1.6, 1.35, 0.6), 2.4)
    else:
        k = max(0.0, 1 - (t - TGONE) / 0.9)
        if k > 0:
            dots(img, cam, P, (2.2, 0.35, 0.25), 2.4 * (0.3 + 0.7 * k) * (0.6 + 0.4 * math.sin((t - TGONE) * 20) ** 2))
    return cam, {"n0": n0, "e": e}


# 2 · cohete: el Vulcan despega junto al mar en Cabo Cañaveral
VUL_FULL = vulcan_mesh()


def lift_y(t):
    s = max(0.0, t - TLIFT)
    return 2.6 * s * s + 1.2 * s


def tower_mesh():
    f = []; I = np.eye(3); x0 = -13.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            boxf(f, (x0 + sx * 2.5, 45, sz * 2.5), (0.4, 45, 0.4), I, (0.30, 0.31, 0.33))
    for y in np.arange(6.0, 90, 8.0):
        boxf(f, (x0, y, 0), (2.9, 0.25, 2.9), I, (0.30, 0.31, 0.33))
    return f


TOWER_F = tower_mesh()


def sc_cohete(img, t):
    a0 = t0_of("cohete")
    u = (t - a0) / (FL[1] - a0)
    y = lift_y(t)
    cam = Cam((62 - 10 * u, 5 + 3 * u, 120 - 12 * u), (0, 30 + 0.75 * y, 0))
    draw_world(img, cam, "pad")
    s = max(0.0, t - TLIFT)
    if t > TLIFT - 0.6:
        k = min(1.0, (t - TLIFT + 0.6) / 0.6)
        smoke(img, cam, (0, 4, 0), 10 + 16 * min(s, 4), 700, t, (2.4, 2.3, 2.2), 5)
        smoke(img, cam, (-25 - 4 * s, 6, 10), 9 + 9 * min(s, 4), 500, t, (2.0, 1.95, 1.9), 6)
    f = list(TOWER_F) + xform(VUL_FULL, np.eye(3), (0, 3.2 + y, 0))
    draw_faces(img, cam, f, "pad")
    if t > TLIFT - 0.6:
        k_main = min(1.0, (t - TLIFT + 0.6) / 0.4)
        k_srb = 1.0 if t > TLIFT else 0.0
        vul_engines(img, cam, np.eye(3), (0, 3.2 + y, 0), t, k_main, k_srb, True, 0.6 + 0.4 * min(s / 2, 1), 1)
    return cam, {"y": y}


# 3 · normal: cielo alto, T+1:40, se sueltan los seis propulsores
def sc_normal(img, t):
    a0 = t0_of("normal")
    u = (t - a0) / (FL[2] - a0)
    tilt = math.radians(-24)
    R = rotm(0, 0, tilt)
    base = np.array([0.0, 26000.0, 0.0])
    cam = Cam(base + np.array([58 - 12 * u, 14 - 6 * u, 92 - 10 * u]), base + R @ np.array([0, 28, 0]) + np.array([0, -4, 0]))
    draw_world(img, cam, "high")
    f = xform(vulcan_mesh(srbs=False), R, base)
    sep = t >= TSRB
    if not sep:
        f += xform([x for a in SRB_ANG for x in (lambda ff: (srb_mesh(ff, a), ff)[1])([])], R, base)
    else:
        ds = t - TSRB
        for i, a in enumerate(SRB_ANG):
            out = np.array([math.cos(a), 0, math.sin(a)])
            drift = R @ (out * (2.5 * ds + 1.2 * ds * ds) + np.array([0, -9 * ds * ds - 4 * ds, 0]))
            rr = rotm(0, 0, tilt) @ rotm(-a, 0, 0) @ rotm(0, 0, 0.45 * ds * (1 + 0.2 * i)) @ rotm(a, 0, 0)
            ff = []; srb_mesh(ff, a)
            ctr = np.array([math.cos(a) * (RV + 0.85), 11.0, math.sin(a) * (RV + 0.85)])
            ff = [(v - ctr, n, c, s_, e) for v, n, c, s_, e in ff]
            f += xform(ff, rr, base + R @ ctr + drift)
    draw_faces(img, cam, f, "high")
    vul_engines(img, cam, R, base, t, 1.0, 1.0 if not sep else 0.0, not sep, 1.5, 3)
    if sep and t - TSRB < 0.6:
        impact_flash(img, cam, base + R @ np.array([0, 22, 0]), t - TSRB, 0.25)
    return cam, {"R": R, "base": base}


# 4 · falla: la Centaur con sus satélites, bamboleo y anomalía a T+10:00
UPPER = vulcan_mesh(srbs=False, booster=False, fairing=False)
BOOST = vulcan_mesh(srbs=False, upper=False)


def wobble(t):
    if t < TWOB:
        return 0.0, 0.0
    s = t - TWOB
    amp = min(1.0, s / 3.0) * 0.30 + max(0.0, t - TANOM) * 0.35
    return amp * math.sin(s * 2.3), amp * 0.7 * math.sin(s * 3.1 + 1.0)


def sc_falla(img, t):
    a0 = t0_of("falla")
    u = (t - a0) / (FL[3] - a0)
    p, r = wobble(t)
    spin = 0.0 if t < TANOM else (t - TANOM) * 0.9
    R = rotm(spin, p, -math.radians(78) + r)          # casi horizontal, en órbita de subida
    cpos = np.array([-30 + 14 * u, 22 - 4 * u, 95 - 14 * u])
    cam_m = Cam(cpos, R @ np.array([0, 44, 0]))
    S_km = np.array([0.0, RE_KM + 180.0, 0.0])
    cam_km = Cam(S_km + cpos / 1000.0, S_km + cpos / 1000.0 + cam_m.f)
    draw_earth(img, cam_km, np.zeros(3), RE_KM, 52 + 3 * u, atm=0.004, glow=0.9)
    f = xform(UPPER, R, (0, 0, 0))
    ds = t - a0
    if ds < 2.2:                                       # la primera etapa se aleja
        R0 = rotm(0, 0, -math.radians(78))
        off = R0 @ np.array([0, -1.0, 0]) * (3 + 6 * ds * ds)
        f += xform(BOOST, R0 @ rotm(0, 0, 0.1 * ds), off)
    draw_faces(img, cam_m, f, "space")
    noz = R @ np.array([0, 32.6, 0]); down = R @ np.array([0, -1.0, 0])
    if t < TANOM:
        k = min(1.0, max(0.0, (ds - 0.6) / 0.4))
        if k > 0:
            rng = np.random.default_rng(int(t * FPS))
            u_ = rng.random(700) ** 0.8
            Pp = noz + down[None, :] * (u_ * 26)[:, None] + rng.normal(0, 1, (700, 3)) * (0.4 + 2.2 * u_)[:, None]
            col = np.array([0.6, 0.9, 2.4]) * np.exp(-u_ * 2.2)[:, None] * (k * 200 / 700)
            splat2(img, cam_m, Pp, col.astype(np.float32), 1.5, 0.2)
    else:                                              # nube de gas y la llama se apaga
        ta = t - TANOM
        rng = np.random.default_rng(31)
        n = 900
        dirs = rng.normal(size=(n, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        sp = 4 + 10 * rng.random(n)
        Pp = R @ np.array([0, 40, 0]) + dirs * (sp * ta)[:, None]
        col = np.array([1.6, 1.5, 1.45]) * (60.0 / n) * math.exp(-ta / 1.4) * 2.5
        splat2(img, cam_m, Pp, np.tile(col, (n, 1)).astype(np.float32), 3.0, 0.0)
        impact_flash(img, cam_m, R @ np.array([0, 40, 0]), ta, 0.5)
    return cam_m, {"R": R}


# 5 · pérdida: la trayectoria se queda corta de la órbita prevista
def traj(t):
    n0 = unit(geo(28.5, -80.6, 60.0)); e = unit(np.cross(np.array([0.3, 1.0, 0.0]), n0))
    e = unit(e * 0.75 + np.cross(n0, e) * 0.45)
    ring = [(n0 * math.cos(a) + e * math.sin(a)) * RE_KM * 1.17 for a in np.linspace(0, 2 * math.pi, 181)]
    path = []
    for a in np.linspace(0, 1.25, 90):
        h = 1 + 0.07 * math.sin(min(a / 0.85, 1) * math.pi / 2) - (0.0 if a < 0.85 else 0.35 * (a - 0.85) ** 2)
        path.append((n0 * math.cos(a) + e * math.sin(a)) * RE_KM * h)
    return n0, e, ring, path


def sc_perdida(img, t):
    a0 = t0_of("perdida")
    u = (t - a0) / (FL[4] - a0)
    n0, e, ring, path = traj(t)
    mid = unit(n0 + e * 0.7)
    side = unit(np.cross(n0, e))
    cam = Cam(side * RE_KM * (4.6 - 0.3 * u) + mid * RE_KM * 1.2, mid * RE_KM * 0.55)
    draw_earth(img, cam, np.zeros(3), RE_KM, 60.0, atm=0.02, glow=0.9)
    return cam, {"n0": n0, "e": e, "ring": ring, "path": path, "u": u}


# 6 · primera: los cinco vuelos del Vulcan en fila
VUL_SMALL = vulcan_mesh(n=16)
ROWX = [-56, -28, 0, 28, 56]


def sc_primera(img, t):
    a0 = t0_of("primera")
    u = (t - a0) / (FL[5] - a0)
    s = ease(u)
    cam = Cam((-14 + 28 * s, 26, 400 - 25 * s), (-4 + 8 * s, 14, 0))
    f = []
    for x in ROWX:
        f += xform(VUL_SMALL, rotm(0.4), (x, 0, 0))
    draw_faces(img, cam, f, "space")
    return cam, {"u": u}


# 7 · amazon: ~400 satélites en órbita contra la meta de 3,200
AMZ_INC = (51.9, 42.0, 33.0)


def sc_amazon(img, t):
    a0 = t0_of("amazon")
    u = (t - a0) / (FL[6] - a0)
    ang = 0.6 + 0.5 * u
    cam = Cam((math.sin(ang) * 26000, 7000, math.cos(ang) * 26000), (0, -600, 0))
    draw_earth(img, cam, np.zeros(3), RE_KM, 70 + 4 * u, atm=0.02, glow=0.85)
    dots(img, cam, shell(400, 1, AMZ_INC, RE_KM * 1.10, t), (1.8, 1.45, 0.45), 2.2 * min(1, (t - a0) / 0.5))
    tg = SPLIT("amazon", 0.55)
    if t > tg:
        k = min(1.0, (t - tg) / 0.8)
        dots(img, cam, shell(2800, 2, AMZ_INC, RE_KM * 1.10, t), (0.35, 0.8, 1.2), 0.9 * k)
    return cam, {"u": u}


# 8 · cierre: la nube de Starlink frente a los satélites de Amazon
def sc_cierre(img, t):
    a0 = t0_of("cierre")
    u = (t - a0) / (END - a0)
    ang = 1.3 + 0.45 * u
    cam = Cam((math.sin(ang) * (27000 - 3000 * u), 3000, math.cos(ang) * (27000 - 3000 * u)), (0, 0, 0))
    draw_earth(img, cam, np.zeros(3), RE_KM, 80 + 4 * u, atm=0.02, glow=0.85)
    dots(img, cam, shell(4000, 3, (53.0, 43.0, 70.0, 97.6), RE_KM * 1.085, t, 0.06), (1.1, 1.15, 1.25), 0.6)
    dots(img, cam, shell(400, 1, AMZ_INC, RE_KM * 1.10, t), (1.8, 1.45, 0.45), 2.2)
    return cam, {"u": u}


SCENES = {"gancho": sc_gancho, "cohete": sc_cohete, "normal": sc_normal, "falla": sc_falla, "perdida": sc_perdida,
          "primera": sc_primera, "amazon": sc_amazon, "cierre": sc_cierre}
MODES = {"gancho": "space", "cohete": "pad", "normal": "high", "falla": "space", "perdida": "space",
         "primera": "space", "amazon": "space", "cierre": "space"}


def clock(t):
    """Reloj de misión mostrado en pantalla (comprimido, no en tiempo real)."""
    if t < TLIFT:
        return None
    if t < TSRB:
        s = (t - TLIFT) / (TSRB - TLIFT); return 100 * s ** 1.4
    a0 = t0_of("falla")
    if t < a0:
        return 100 + (t - TSRB) * 6
    if t < TANOM:
        return 250 + (600 - 250) * (t - a0) / (TANOM - a0)
    return 600


def draw_clock(d, t, A, col=WHITE):
    c = clock(t)
    if c is None or A <= 0:
        return
    m, s = int(c // 60), int(c % 60)
    txt(d, (W / 2, 1600), f"T+ {m:02d}:{s:02d}", 92, col, A, "Inter-Black.otf", 8)


def overlays(frame_u8, t, name, cam, ex):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0 = t0_of(name)
    if name == "gancho":
        draw_label(layer, t, 0.15, TGONE, "40 SATÉLITES", ["de Amazon, rumbo a la órbita"], YELLOW, 124)
        draw_label(layer, t, TGONE, FL[0] + 0.05, "NINGUNO LLEGÓ", ["domingo 15 de noviembre"], RED, 122)
        n0 = ex["n0"]; x, y, _ = pt(cam, n0 * RE_KM)
        A = int(255 * fade(t, 0.3, FL[0]))
        marker(d, x, y, t, CYAN, A, 26, "FLORIDA", 1 if x < W / 2 else -1, 44)
    elif name == "cohete":
        mid = SPLIT("cohete", 0.55)
        draw_label(layer, t, a0 + 0.15, mid, "VULCAN", ["el cohete nuevo de ULA", "Cabo Cañaveral, Florida"], WHITE, 140)
        draw_label(layer, t, mid, FL[1] + 0.05, "6 PROPULSORES", ["de combustible sólido"], YELLOW, 116)
        draw_clock(d, t, int(255 * fade(t, TLIFT, FL[1] + 0.1, 0.15)))
    elif name == "normal":
        draw_label(layer, t, a0 + 0.15, TSRB, "T+ 1:40", ["minuto y cuarenta segundos"], YELLOW, 140)
        draw_label(layer, t, TSRB, FL[2] + 0.05, "SE SOLTARON", ["todo parecía normal"], CYAN, 124)
        draw_clock(d, t, int(255 * fade(t, a0, FL[2] + 0.1, 0.15)))
    elif name == "falla":
        draw_label(layer, t, a0 + 0.15, TWOB, "ETAPA CENTAUR", ["con los 40 satélites"], WHITE, 112)
        draw_label(layer, t, TWOB, TANOM, "GIRA RARO", ["movimientos extraños"], ORANGE, 124)
        draw_label(layer, t, TANOM, FL[3] + 0.05, "ANOMALÍA", ["a los 10 minutos del despegue"], RED, 136)
        draw_clock(d, t, int(255 * fade(t, a0, FL[3] + 0.1, 0.15)), RED if t >= TANOM else WHITE)
        txt(d, (W / 2, 1830), "recreación · la causa aún se investiga", 34, (220, 225, 235), int(200 * fade(t, a0, FL[3])), "Inter-ExtraBold.otf", 5)
    elif name == "perdida":
        u = ex["u"]; A = int(255 * min(1, (t - a0) / 0.3))
        poly3d(d, cam, ex["ring"], YELLOW, A, 6, dash=3)
        path = ex["path"]; npts = max(2, int(len(path) * min(1.0, u / 0.55)))
        poly3d(d, cam, path[:npts], RED, A, 8)
        RP = np.asarray(ex["ring"]); rx, ry, rz = cam.proj(RP); okr = vis_mask(cam, RP) & (rz > 0) & (ry > 560) & (ry < 1200)
        if okr.any():
            i = int(np.argmax(np.where(okr, rx, -1e9))); txt(d, (min(rx[i], W - 30), ry[i] - 50), "ÓRBITA PREVISTA", 44, YELLOW, A, "Inter-Black.otf", 6, "rm")
        if u > 0.55:
            x, y, _ = pt(cam, path[npts - 1]); B = int(A * min(1, (u - 0.55) / 0.1))
            d.line([x - 34, y - 34, x + 34, y + 34], fill=RED + (B,), width=12); d.line([x - 34, y + 34, x + 34, y - 34], fill=RED + (B,), width=12)
        draw_label(layer, t, a0 + 0.1, FL[4] + 0.05, "0 DE 40", ["llegaron a la órbita"], RED, 150)
        txt(d, (W / 2, 1830), "recreación · trayectoria ilustrativa", 34, (220, 225, 235), int(200 * fade(t, a0, FL[4])), "Inter-ExtraBold.otf", 5)
    elif name == "primera":
        u = ex["u"]
        labs = [("1", "ENE 2024", WHITE), ("2", "OCT 2024", ORANGE), ("3", "", WHITE), ("4", "FEB 2026", ORANGE), ("5", "NOV 2026", RED)]
        for i, (x, (num, date, col)) in enumerate(zip(ROWX, labs)):
            ti = a0 + 0.2 + i * 0.35
            if t < ti:
                continue
            A = int(255 * min(1, (t - ti) / 0.25) * fade(t, a0, FL[5] + 0.3, 0.2))
            px, py, _ = pt(cam, (x, -8, 0))
            txt(d, (px, py + 10), num, 72, col, A)
            if date:
                txt(d, (px, py + 72), date.split()[0], 36, col, A, "Inter-ExtraBold.otf", 5)
                txt(d, (px, py + 112), date.split()[1], 36, col, A, "Inter-ExtraBold.otf", 5)
            if col == RED:
                hx, hy, _ = pt(cam, (x, 34, 0))
                B = int(A * (0.75 + 0.25 * math.sin(t * 8)))
                d.line([hx - 70, hy - 70, hx + 70, hy + 70], fill=RED + (B,), width=14); d.line([hx - 70, hy + 70, hx + 70, hy - 70], fill=RED + (B,), width=14)
        mid = SPLIT("primera", 0.42)
        draw_label(layer, t, a0 + 0.15, mid, "5.º VUELO", ["del Vulcan"], YELLOW, 140)
        draw_label(layer, t, mid, FL[5] + 0.05, "9 MESES", ["sin volar, arreglando", "las toberas de los propulsores"], CYAN, 140)
    elif name == "amazon":
        tg = SPLIT("amazon", 0.55)
        draw_label(layer, t, a0 + 0.15, tg, "≈400", ["satélites de Amazon arriba"], YELLOW, 150)
        draw_label(layer, t, tg, FL[6] + 0.05, "META: 3,200+", ["para competir con Starlink"], CYAN, 124)
        txt(d, (W / 2, 1830), "ilustrativo · altura exagerada", 34, (220, 225, 235), int(200 * fade(t, a0, FL[6])), "Inter-ExtraBold.otf", 5)
    elif name == "cierre":
        mid = SPLIT("cierre", 0.42)
        draw_label(layer, t, a0 + 0.15, mid, "CAUSA", ["aún en investigación"], WHITE, 130)
        draw_label(layer, t, mid, CARD + 0.1, "STARLINK", ["sigue ganando la carrera"], WHITE, 140)
        A = int(255 * fade(t, mid, CARD + 0.1))
        if A > 0:
            d.ellipse([W / 2 - 300, 640, W / 2 - 272, 668], fill=(235, 240, 250, A)); txt(d, (W / 2 - 255, 654), "Starlink", 40, WHITE, A, "Inter-ExtraBold.otf", 5, "lm")
            d.ellipse([W / 2 + 40, 640, W / 2 + 68, 668], fill=YELLOW + (A,)); txt(d, (W / 2 + 85, 654), "Amazon Leo", 40, YELLOW, A, "Inter-ExtraBold.otf", 5, "lm")
        txt(d, (W / 2, 1830), "ilustrativo · altura exagerada", 34, (220, 225, 235), int(200 * fade(t, a0, CARD)), "Inter-ExtraBold.otf", 5)
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
    mode = MODES.get(name, "space")
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
        print("frames", NFRAMES, "shots", [(a, round(b, 2)) for a, b in SHOTS], "card", round(CARD, 2),
              "lift", round(TLIFT, 2), "srb", round(TSRB, 2), "wob", round(TWOB, 2), "anom", round(TANOM, 2))
