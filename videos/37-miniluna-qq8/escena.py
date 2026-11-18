"""Flash Datos · video 37: la Tierra tiene una segunda luna temporal, 2026 QQ8 (MPC, 29 oct 2026).

Escena nueva: la Tierra con la Luna y una segunda "luna" diminuta que dibuja lazos; acercamiento a una roca
irregular que gira, comparada con la silueta de un auto; la roca llega de paso y la gravedad la atrapa en
lazos; un satélite chatarra con signo de interrogación que el escaneo convierte en roca natural; diagrama
inclinado con la órbita de la Luna (1×) y la de QQ8 (1.5×); la Tierra con un telescopio que no la alcanza a ver;
la roca que se escapa y un contador de años hasta 2058; y el cierre con las dos lunas.

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



# ======================= video 37: escenas =======================
FIRST = ["gancho", "quien", "captura", "basura", "distancia", "peligro", "salida", "cierre"]
SHOTS = [(k, 0.0 if i == 0 else S0[k] - 0.2) for i, k in enumerate(FIRST)]
FL = [b for _, b in SHOTS[1:]] + [CARD - 0.05]
TREVEAL = 20.53
GRAY = (200, 205, 215)


def scene(t):
    cur = SHOTS[0][0]
    for k, b in SHOTS:
        if t >= b:
            cur = k
    return cur


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def pt(cam, P):
    x, y, z = cam.proj(P)
    return float(x[0]), float(y[0]), float(z[0])


def poly3d(d, cam, pts, col, A, width=6, behind=None):
    """Polilínea 3D; si behind=(C, r), oculta los tramos detrás de esa esfera."""
    prev = None
    for P in pts:
        x, y, z = pt(cam, P)
        ok = z > 0
        if ok and behind is not None:
            C, r = behind
            v = np.asarray(P) - cam.O; dv = np.linalg.norm(v); u = v / dv
            b = float(u @ (cam.O - C)); disc = b * b - (float((cam.O - C) @ (cam.O - C)) - r * r)
            if disc > 0 and (-b - math.sqrt(disc)) < dv:
                ok = False
        cur = (x, y) if ok else None
        if prev and cur:
            d.line([prev, cur], fill=col + (A,), width=width)
        prev = cur


# --- trayectoria de QQ8 en el marco de la Tierra (unidades: el radio de la órbita lunar es 60) ---
R_MOON = 60.0
def qq8(s):
    s = np.asarray(s, float)
    th = 0.6 + 2 * math.pi * 2.25 * s
    far = 340 * ((1 - smooth(0.0, 0.2, s)) + smooth(0.8, 1.0, s))
    R = 90 + 22 * np.sin(2 * th + 0.8) + far
    return np.stack([R * np.cos(th), 7 * np.sin(1.3 * th) + 0.02 * far, R * np.sin(th) * 0.9], -1)


def moon_pos(t):
    a = -0.4 + 0.05 * t
    return np.array([R_MOON * math.cos(a), 0.0, R_MOON * math.sin(a) * 0.9])


def circle3d(R, n=120, sq=0.9, y=0.0):
    a = np.linspace(0, 2 * math.pi, n)
    return np.stack([R * np.cos(a), np.full(n, y), R * np.sin(a) * sq], -1)


def trail(d, layer, cam, s0, s1, A, col=YELLOW, width=5, head=True, behind=None):
    ss = np.linspace(s0, s1, max(8, int((s1 - s0) * 600)))
    P = qq8(ss)
    n = len(P)
    # estela que se desvanece hacia atrás
    seg = 6
    for i in range(0, n - 1, seg):
        k = (i / max(n - 1, 1)) ** 0.8
        poly3d(d, cam, P[i:i + seg + 1], col, int(A * (0.15 + 0.85 * k)), width, behind)
    if head:
        x, y, z = pt(cam, P[-1])
        if z > 0:
            glow(layer, x, y, 34, col, int(220 * A / 255))
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(255, 250, 230, A))
    return P[-1]


# --- roca irregular que gira (en espacio de cámara) ---
_rock_cache = {}
def draw_rock(img, cx, cy, rpx, t, spin=0.6, base=(0.42, 0.38, 0.34), light=None):
    L = unit(light if light is not None else (-0.6, 0.55, 0.58))
    ext = int(rpx * 1.35) + 3
    x0, x1 = int(max(0, cx - ext)), int(min(W, cx + ext))
    y0, y1 = int(max(0, cy - ext)), int(min(H, cy + ext))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    u = (xx - cx) / rpx; v = -(yy - cy) / rpx
    dd2 = u * u + v * v
    rm = 1.32
    inside0 = dd2 < rm * rm
    if not inside0.any():
        return
    uu, vv = u[inside0], v[inside0]
    z0 = np.sqrt(np.maximum(rm * rm - uu * uu - vv * vv, 0))
    n0 = np.stack([uu, vv, z0], -1) / rm
    a1, a2 = spin * t, 0.37 * spin * t + 0.5
    def rot(n):
        return rot_x(rot_y(n, a1), a2)
    def shape(n):
        rn = rot(n)
        return 1.0 + 0.24 * (fbm(rn[:, 0] * 1.3 + 4, rn[:, 1] * 1.3 + 1, rn[:, 2] * 1.3, 3, seed=11) - 0.5) * 2 \
               + 0.25 * rn[:, 0] ** 2 - 0.1 * rn[:, 1] ** 2
    re = shape(n0) * 0.9
    dd = np.sqrt(uu * uu + vv * vv)
    pixw = 1.0 / rpx
    alpha = np.clip((re - dd) / pixw + 0.5, 0, 1)
    zz = np.sqrt(np.maximum(re * re - dd * dd, 0))
    n = np.stack([uu, vv, zz], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    # relieve: cráteres y granos
    rn = rot(n)
    eps = 0.04
    def hgt(p):
        return fbm(p[:, 0] * 5 + 9, p[:, 1] * 5 + 2, p[:, 2] * 5, 4, seed=3)
    h0 = hgt(rn)
    gx = (hgt(rn + np.array([eps, 0, 0])) - h0) / eps
    gy = (hgt(rn + np.array([0, eps, 0])) - h0) / eps
    nb = n - 0.35 * np.stack([gx, gy, np.zeros_like(gx)], -1)
    nb /= np.linalg.norm(nb, axis=-1, keepdims=True)
    ndl = nb @ L
    tex = 0.65 + 0.7 * (fbm(rn[:, 0] * 3 + 1, rn[:, 1] * 3, rn[:, 2] * 3 + 5, 4, seed=8) - 0.5) + 0.25 * (h0 - 0.5)
    rim = (1 - np.clip(n[:, 2], 0, 1)) ** 3 * 0.25
    col = lin(base) * tex[:, None] * (0.025 + 2.2 * np.clip(ndl, 0, 1))[:, None] + rim[:, None] * np.array([0.10, 0.18, 0.35])
    region = img[y0:y1, x0:x1]
    sub = region[inside0]
    a = alpha[:, None]
    region[inside0] = sub * (1 - a) + col * a


def draw_moon(img, cam, C, r):
    draw_ball(img, cam, C, r, (0.72, 0.71, 0.69), seed=6)


def car_poly(x, y, Lpx):
    """Silueta lateral de un auto genérico; (x, y) = punto medio del piso."""
    s = Lpx
    P = [(-0.50, 0.00), (-0.50, -0.20), (-0.44, -0.27), (-0.22, -0.30), (-0.10, -0.46), (0.20, -0.47),
         (0.33, -0.30), (0.47, -0.27), (0.50, -0.18), (0.50, 0.00)]
    return [(x + px * s, y + py * s) for px, py in P]


def cam_earth(dist, elev, azim, target=(0, 0, 0)):
    tgt = np.asarray(target, float)
    pos = tgt + dist * np.array([math.sin(azim) * math.cos(elev), math.sin(elev), math.cos(azim) * math.cos(elev)])
    return Cam(pos, tgt)


RE_V = 8.0     # radio de la Tierra en las vistas lejanas (no está a escala)
RMOON_V = 3.2


def wide_world(img, t, cam, moon=True):
    draw_earth(img, cam, (0, 0, 0), RE_V, t, atm=0.05, glow=0.7)
    if moon:
        draw_moon(img, cam, moon_pos(t), RMOON_V)


# ---------------- tomas ----------------
def sh_gancho(img, t):
    a0, a1 = 0.0, S0["quien"] - 0.2
    k = ease_out((t - a0) / (a1 - a0))
    cam = cam_earth(30 + 700 * k, 0.32 + 0.12 * k, 0.4 - 0.25 * k)
    wide_world(img, t, cam)
    return cam, {}


def sh_quien(img, t):
    a0, a1 = S0["quien"] - 0.2, S0["captura"] - 0.2
    tz = SPLIT("quien", 0.5)
    k = ease((t - tz) / 1.6)
    r = 330 * (1 - k) + 120 * k
    cx = W / 2 + 160 * k; cy = 900 - 40 * k
    draw_rock(img, cx, cy, r, t, spin=0.55)
    return None, {"rock": (cx, cy, r), "k": k}


def sh_captura(img, t):
    a0, a1 = S0["captura"] - 0.2, S0["basura"] - 0.2
    s = 0.02 + 0.36 * ease((t - a0) / (a1 - a0))
    cam = cam_earth(560 - 40 * (t - a0) / (a1 - a0), 1.05, 0.15)
    wide_world(img, t, cam)
    return cam, {"s": s}


def sh_basura(img, t):
    a0 = S0["basura"] - 0.2
    if t >= TREVEAL - 0.15:
        k = ease_out((t - TREVEAL + 0.15) / 0.5)
        draw_rock(img, W / 2, 860, 250 + 30 * k, t, spin=0.5)
    return None, {}


def sh_distancia(img, t):
    a0, a1 = S0["distancia"] - 0.2, S0["peligro"] - 0.2
    k = (t - a0) / (a1 - a0)
    cam = cam_earth(640 - 40 * k, 0.62, 0.0 + 0.15 * k, (0, 0, 8))
    draw_earth(img, cam, (0, 0, 0), RE_V, t, atm=0.05, glow=0.7)
    draw_moon(img, cam, np.array([R_MOON * math.cos(0.3), 0, R_MOON * math.sin(0.3) * 0.9]), RMOON_V)
    return cam, {"k": k}


def sh_peligro(img, t):
    a0, a1 = S0["peligro"] - 0.2, S0["salida"] - 0.2
    k = (t - a0) / (a1 - a0)
    cam = Cam((0, 0, 70 - 4 * k), (0, -6, 0))
    draw_earth(img, cam, (0, -48, -10), 30.0, t, atm=0.03, glow=0.8)
    return cam, {"k": k}


def sh_salida(img, t):
    a0, a1 = S0["salida"] - 0.2, S0["cierre"] - 0.2
    k = ease((t - a0) / (a1 - a0))
    s = 0.62 + 0.38 * k
    cam = cam_earth(560 + 240 * k, 0.95, 0.15 + 0.2 * k)
    wide_world(img, t, cam)
    return cam, {"s": s, "k": k}


def sh_cierre(img, t):
    a0 = S0["cierre"] - 0.2
    k = ease_out((t - a0) / 3.0)
    cam = cam_earth(900 - 230 * k, 0.55 - 0.1 * k, 0.25 + 0.1 * k)
    wide_world(img, t, cam)
    return cam, {"k": k}


SCENES = {"gancho": sh_gancho, "quien": sh_quien, "captura": sh_captura, "basura": sh_basura,
          "distancia": sh_distancia, "peligro": sh_peligro, "salida": sh_salida, "cierre": sh_cierre}

S_GANCHO = 0.62   # dónde va QQ8 en las tomas de conjunto


def junk(t, scale=1.0):
    R = rotm(0.7 * t, 0.45 * t + 0.3, 0.2 * t)
    c = np.zeros(3)
    B = [(c, (1.0, 1.0, 1.3), R, (205, 170, 70))]
    for sgn in (-1, 1):
        B.append((R @ np.array([sgn * 2.9, 0, 0]), (1.8, 0.06, 0.9), R, (55, 85, 160)))
    B.append((R @ np.array([0, 1.25, 0]), (0.18, 0.4, 0.18), R, (180, 182, 190)))
    return B


def overlays(u8, t, name, cam, ex):
    im = Image.fromarray(u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a0 = dict(SHOTS)[name]
    nxt = [b for k, b in SHOTS if b > a0]
    a1 = nxt[0] if nxt else END + 1
    behind = ((np.zeros(3), RE_V))
    if name == "gancho":
        A = 255
        P = trail(d, layer, cam, S_GANCHO - 0.16, S_GANCHO + 0.03 * t / 5.7, A, behind=behind)
        k = ease_out((t - 0.6) / 2.4)
        A2 = int(255 * fade(t, 1.6, a1 + 0.1))
        if A2 > 0:
            x, y, _ = pt(cam, moon_pos(t)); marker(d, x, y, t, CYAN, A2, 24, "LUNA", 1, 44)
            x, y, _ = pt(cam, P); marker(d, x, y, t, YELLOW, A2, 24, "¿2.ª LUNA?", 1 if x < W / 2 else -1, 44)
        draw_label(layer, t, -1, a1, "2 LUNAS", ["por unas semanas"], YELLOW, 140)
    elif name == "quien":
        cx, cy, r = ex["rock"]; k = ex["k"]
        draw_label(layer, t, a0 + 0.1, a1, "2026 QQ8", ["roca de 1 a 2 metros"], YELLOW, 130)
        A = int(255 * min(1.0, max(0.0, (k - 0.6) / 0.4)))
        if A > 0:
            # auto de 4.5 m junto a una roca de 2 m: 2 m ↔ diámetro de la roca
            Lpx = 2 * r * 4.5 / 2.0
            xg = cx - r - 40 - Lpx / 2; yg = cy + r
            d.polygon(car_poly(xg, yg, Lpx), fill=(70, 80, 100, int(A * 0.85)), outline=CYAN + (A,))
            for wx in (-0.3, 0.3):
                rr = Lpx * 0.085
                d.ellipse([xg + wx * Lpx - rr, yg - rr, xg + wx * Lpx + rr, yg + rr], fill=(20, 22, 30, A), outline=CYAN + (A,), width=3)
            d.line([(xg - Lpx / 2, yg + 50), (xg + Lpx / 2, yg + 50)], fill=CYAN + (A,), width=4)
            txt(d, (xg, yg + 95), "auto ≈ 4.5 m", 44, CYAN, A, "Inter-ExtraBold.otf", 6)
            d.line([(cx - r, yg + 50), (cx + r, yg + 50)], fill=YELLOW + (A,), width=4)
            txt(d, (cx, yg + 95), "QQ8 ≈ 1–2 m", 44, YELLOW, A, "Inter-ExtraBold.otf", 6)
    elif name == "captura":
        s = ex["s"]
        A = 255
        poly3d(d, cam, circle3d(R_MOON), CYAN, 90, 3, behind)
        P = trail(d, layer, cam, 0.0, s, A, behind=behind)
        hill = int(255 * fade(t, a0 + 0.2, a1 + 0.2))
        if hill > 0:
            poly3d(d, cam, circle3d(150, 160), WHITE, int(hill * 0.35), 2)
            x, y, _ = pt(cam, (0, 0, 150 * 0.9)); txt(d, (x, y + 40), "zona donde manda la gravedad de la Tierra", 34, WHITE, int(hill * 0.8), "Inter-ExtraBold.otf", 5)
        draw_label(layer, t, a0 + 0.1, a1, "ABRIL 2026", ["la Tierra la atrapa"], YELLOW, 124)
        txt(d, (W / 2, 1830), "recreación · no está a escala", 34, (220, 225, 235), 200, "Inter-ExtraBold.otf", 5)
    elif name == "basura":
        if t < TREVEAL - 0.15:
            jc = Cam((0, 0, 30), (0, 0, 0))
            jl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw_boxes(jl, jc, [(np.asarray(c) + np.array([0, 1.4, 0]), h, R, col) for c, h, R, col in junk(t)])
            layer.alpha_composite(jl)
            A = int(255 * fade(t, a0 + 0.1, TREVEAL - 0.1))
            draw_label(layer, t, a0 + 0.1, TREVEAL - 0.1, "¿BASURA ESPACIAL?", ["así la clasificaron al principio"], RED, 96)
            # escaneo
            ks = (t - (TREVEAL - 1.3)) / 1.15
            if 0 <= ks <= 1:
                ys = 560 + ks * 800
                d.rectangle([60, ys - 3, W - 60, ys + 3], fill=CYAN + (230,))
                glow(layer, W / 2, ys, 60, CYAN, 120)
        else:
            draw_label(layer, t, TREVEAL, a1, "ROCA NATURAL", ["confirmada con telescopios"], YELLOW, 116)
            A = int(255 * fade(t, TREVEAL + 0.3, a1))
            if A > 0:
                x, y = W / 2 + 230, 640
                d.ellipse([x - 42, y - 42, x + 42, y + 42], fill=(60, 200, 120, A))
                d.line([(x - 20, y), (x - 5, y + 17), (x + 22, y - 18)], fill=WHITE + (A,), width=10)
    elif name == "distancia":
        k = ex["k"]
        mp = np.array([R_MOON * math.cos(0.3), 0, R_MOON * math.sin(0.3) * 0.9])
        R2 = 1.5 * R_MOON
        qp = np.array([R2 * math.cos(-2.4), 0, R2 * math.sin(-2.4) * 0.9])
        km = ease((t - a0 - 0.2) / 0.8); kq = ease((t - a0 - 1.0) / 0.9)
        poly3d(d, cam, circle3d(R_MOON)[: max(2, int(120 * km))], CYAN, 200, 4, behind)
        poly3d(d, cam, circle3d(R2, 160)[: max(2, int(160 * kq))], YELLOW, 220, 5, behind)
        if km > 0.6:
            A = int(255 * min(1, (km - 0.6) / 0.4))
            poly3d(d, cam, [mp * s for s in np.linspace(0.15, 0.92, 10)], CYAN, A, 5)
            x, y, _ = pt(cam, mp * 0.55); txt(d, (x + 10, y - 40), "1×", 60, CYAN, A)
            x, y, _ = pt(cam, mp); txt(d, (x, y + 52), "LUNA", 42, WHITE, A, "Inter-Black.otf", 6)
        if kq > 0.6:
            A = int(255 * min(1, (kq - 0.6) / 0.4))
            poly3d(d, cam, [qp * s for s in np.linspace(0.15, 0.97, 10)], YELLOW, A, 5)
            x, y, _ = pt(cam, qp * 0.6); txt(d, (x - 10, y + 50), "1.5×", 64, YELLOW, A)
            x, y, _ = pt(cam, qp); glow(layer, x, y, 30, YELLOW, A); d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(255, 250, 230, A))
            txt(d, (x, y + 48), "QQ8", 42, WHITE, A, "Inter-Black.otf", 6)
        draw_label(layer, t, a0 + 0.1, a1, "1.5 VECES", ["la distancia de la Luna"], YELLOW, 124)
        txt(d, (W / 2, 1830), "recreación · no está a escala", 34, (220, 225, 235), 200, "Inter-ExtraBold.otf", 5)
    elif name == "peligro":
        k = ex["k"]
        # telescopio de aficionado sobre el horizonte
        A = int(255 * fade(t, a0 + 0.2, a1 + 0.3))
        bx, by = 330, 1560
        ang = math.radians(-58)
        L = 210
        tip = (bx + L * math.cos(ang), by + L * math.sin(ang))
        dd_ = (math.sin(ang) * 34, -math.cos(ang) * 34)
        tube = [(bx - dd_[0] * 0.8, by - dd_[1] * 0.8), (bx + dd_[0] * 0.8, by + dd_[1] * 0.8),
                (tip[0] + dd_[0], tip[1] + dd_[1]), (tip[0] - dd_[0], tip[1] - dd_[1])]
        d.line([(bx, by), (bx - 90, by + 190)], fill=(170, 175, 190, A), width=10)
        d.line([(bx, by), (bx + 90, by + 190)], fill=(170, 175, 190, A), width=10)
        d.line([(bx, by), (bx, by + 200)], fill=(170, 175, 190, A), width=10)
        d.polygon(tube, fill=(225, 228, 238, A), outline=(40, 44, 60, A))
        # cono de visión que no llega
        reach = 0.55 + 0.1 * math.sin(t * 2)
        far = (bx + 900 * math.cos(ang), by + 900 * math.sin(ang))
        mid = (tip[0] + (far[0] - tip[0]) * reach, tip[1] + (far[1] - tip[1]) * reach)
        for i in range(10):
            f = i / 10
            p = (tip[0] + (mid[0] - tip[0]) * f, tip[1] + (mid[1] - tip[1]) * f)
            glow(layer, p[0], p[1], 20 + 30 * f, CYAN, int(A * 0.25 * (1 - f)))
        # QQ8 muy lejos: punto apenas visible, marcado
        qx, qy = far
        d.ellipse([qx - 3, qy - 3, qx + 3, qy + 3], fill=(255, 245, 220, int(A * 0.5)))
        rr = 46 + 5 * math.sin(t * 6)
        d.ellipse([qx - rr, qy - rr, qx + rr, qy + rr], outline=YELLOW + (A,), width=5)
        txt(d, (qx - 10, qy + rr + 40), "QQ8 · no se ve", 42, YELLOW, A, "Inter-Black.otf", 6)
        draw_label(layer, t, a0 + 0.1, a1, "NO ES PELIGROSA", ["ni se ve con telescopio de aficionado"], (120, 235, 150), 104)
    elif name == "salida":
        s = ex["s"]; k = ex["k"]
        poly3d(d, cam, circle3d(R_MOON), CYAN, 90, 3, behind)
        P = trail(d, layer, cam, 0.25, s, 255, behind=behind)
        tsplit = SPLIT("salida", 0.42)
        draw_label(layer, t, a0 + 0.1, tsplit, "DIC. – ENE.", ["se escapa de la Tierra"], YELLOW, 124)
        A = int(255 * fade(t, tsplit, a1))
        if A > 0:
            yr = int(round(2026 + 32 * ease((t - tsplit) / 1.6)))
            txt(d, (W / 2, 380), str(yr), 150, YELLOW if yr == 2058 else WHITE, A)
            txt(d, (W / 2, 490), "su próximo acercamiento así", 54, CYAN, A, "Inter-ExtraBold.otf", 7)
        txt(d, (W / 2, 1830), "recreación · no está a escala", 34, (220, 225, 235), 200, "Inter-ExtraBold.otf", 5)
    elif name == "cierre":
        A = int(255 * fade(t, a0 + 0.6, CARD))
        poly3d(d, cam, circle3d(R_MOON), CYAN, int(A * 0.45), 3, behind)
        P = trail(d, layer, cam, S_GANCHO - 0.2, S_GANCHO + 0.02, 255, behind=behind)
        if A > 0:
            x, y, _ = pt(cam, moon_pos(t)); marker(d, x, y, t, CYAN, A, 24, "la de siempre", 1 if x < W / 2 else -1, 42)
            x, y, _ = pt(cam, P); marker(d, x, y, t, YELLOW, A, 24, "de visita", 1 if x < W / 2 else -1, 42)
        draw_label(layer, t, a0 + 0.1, CARD + 0.1, "2 LUNAS", ["por unas semanas más"], YELLOW, 140)
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
