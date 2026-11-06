"""Flash Datos · video 20 · Serie "El método", parte 3: la animación 3D y el sonido.

Júpiter que se dibuja en vivo por bloques (como un render), el código del motor, el diagrama de un
rayo por pixel con el Sol como fuente de luz, la textura de la Tierra que se envuelve en la esfera,
cortes rápidos de cámara y cuerpos (Venus, una gigante roja, el Sol) con portadas de videos reales,
un anillo de barras con el espectro real de la música y los efectos, el medidor de volumen a −14 LUFS,
un carrusel con todos los cuerpos y el avance de la parte 4 (GitHub) con un grafo de commits.

Uso:
  python3 escena.py info
  python3 escena.py test 1 5 12 ...
  python3 escena.py chunk <ini> <fin> <out>
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom
from scipy.io import wavfile

BASE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
TY = math.tan(math.radians(20)); TX = TY * W / H
PIX = 2 * TY / H

xs = ((np.arange(W) + 0.5) / W * 2 - 1) * TX
ys = (1 - (np.arange(H) + 0.5) / H * 2) * TY
DX, DY = np.meshgrid(xs, ys)
NRM = np.sqrt(DX * DX + DY * DY + 1)
DIRS = np.stack([DX / NRM, DY / NRM, -1 / NRM], axis=-1)

LIGHT = np.array([-0.55, 0.45, 0.70]); LIGHT /= np.linalg.norm(LIGHT)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
EARTH_S = np.clip(T("earth"), 0, 1)
EARTH = lin(EARTH_S); CLOUDS = T("earth_clouds"); LAND = T("earth_land")
JUP = lin(np.clip(T("jupiter"), 0, 1)); VEN = lin(np.clip(T("venus"), 0, 1))
SUN = T("sun"); BET = T("betelgeuse")

# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
HK0, HK1 = SEG["hook"]["t0"], SEG["hook"]["t1"]
MO0, MO1 = SEG["motor"]["t0"], SEG["motor"]["t1"]
RA0, RA1 = SEG["rayos"]["t0"], SEG["rayos"]["t1"]
TX0, TX1 = SEG["texturas"]["t0"], SEG["texturas"]["t1"]
ES0, ES1 = SEG["escena"]["t0"], SEG["escena"]["t1"]
SO0, SO1 = SEG["sonido"]["t0"], SEG["sonido"]["t1"]
MZ0, MZ1 = SEG["mezcla"]["t0"], SEG["mezcla"]["t1"]
CI0, CI1 = SEG["cierre"]["t0"], SEG["cierre"]["t1"]
CIA = SEG["cierre"]["parts"][0]
CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
END = TM["end"]
NFRAMES = int(round(END * FPS))
FL = [MO0 - 0.15, TX0 - 0.15, ES0 - 0.15, SO0 - 0.15, CIA[0] - 0.15, CIB[0] - 0.15, CARD - 0.05]


def wtime(seg, idx):
    """Momento aproximado de la palabra número idx del segmento (por peso de letras)."""
    words = SEG[seg]["say"].split()
    wts = [len(w) + 1 + (3 if w[-1] in ".,:…?" else 0) for w in words]
    t0, t1 = SEG[seg]["t0"], SEG[seg]["t1"]
    return t0 + (t1 - t0) * sum(wts[:idx]) / sum(wts)


ES_CAM, ES_CUE, ES_ETI = wtime("escena", 10), wtime("escena", 12), wtime("escena", 15)
SO_EF, SO_MU, SO_OR = wtime("sonido", 6), wtime("sonido", 9), wtime("sonido", 16)
RA_HIT, RA_LUZ = wtime("rayos", 9), wtime("rayos", 13)
TX_REAL = wtime("texturas", 8)
REVEAL0, REVEAL1 = 0.3, 3.6

# ---------------- fondo: estrellas y nebulosa verde-azulada (distinta a las partes 1 y 2) ----------------
def make_background():
    rng = np.random.default_rng(20)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1900
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.025 + 0.45 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 50
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 34.0
    neb = fbm(gx, gy, np.full_like(gx, 3.1), 5, seed=2020)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.42) * 2.4, 0, 1) ** 1.5
    bg += neb[..., None] * np.array([0.008, 0.034, 0.050], np.float32)
    return bg


BG = make_background()


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


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)



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



def bloom(img):
    small = img[::4, ::4]
    br = np.clip(small - 0.9, 0, None)
    g = gaussian_filter(br, (5, 5, 0)) * 0.55 + gaussian_filter(br, (22, 22, 0)) * 0.85 + gaussian_filter(br, (60, 60, 0)) * 0.5
    return img + ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)


def project(P, O):
    rel = np.array(P) - O
    depth = -rel[2]
    return (rel[0] / depth / TX + 1) / 2 * W, (1 - rel[1] / depth / TY) / 2 * H, depth



def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s



# ---------------- texto ----------------
FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); RED = (255, 84, 84)
INK = (8, 10, 20)


def txt(d, xy, s, size, col, A, face="Inter-Black.otf", stroke=8, anchor="mm"):
    d.text(xy, s, font=font(face, size), fill=col + (A,), anchor=anchor, stroke_width=stroke, stroke_fill=INK + (A,))


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
    for t0, t1, cap in s["parts"]:
        CAPS += groups_for_part(t0, t1, cap)
for i in range(len(CAPS) - 1):
    if CAPS[i + 1][0] - CAPS[i][1] < 0.7:
        CAPS[i][1] = CAPS[i + 1][0]


def is_hl(w):
    raw = w.strip(".,:…?¿!¡()")
    return any(ch.isdigit() for ch in raw) or (raw.isupper() and len(raw) > 1)


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
            x = W / 2 - total / 2; y = 1330
            for w, wd in zip(g, widths):
                col = YELLOW if is_hl(w) else WHITE
                d.text((x, y), w, font=f, fill=col + (255,), anchor="lm", stroke_width=9, stroke_fill=INK + (255,))
                x += wd + space
            return


def fade(t, a, b, f=0.25):
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / f, (b - t) / f)


def bolt(cx, cy, s):
    pts = [(0.58, 0.0), (0.12, 0.56), (0.44, 0.56), (0.30, 1.0), (0.88, 0.38), (0.55, 0.38), (0.74, 0.0)]
    return [(cx + (px - 0.5) * s, cy + (py - 0.5) * s) for px, py in pts]


def draw_watermark(layer, t):
    if t >= CARD:
        return
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 38)
    tw = d.textlength("FLASH DATOS", font=f)
    x = W / 2 - (tw + 40) / 2
    d.polygon(bolt(x + 14, 212, 40), fill=YELLOW + (230,))
    d.text((x + 40, 212), "FLASH DATOS", font=f, fill=(255, 255, 255, 215), anchor="lm", stroke_width=4, stroke_fill=(8, 10, 20, 160))


def badge(d, t, A):
    """Etiqueta fija de la serie arriba: EL MÉTODO · PARTE 3/5."""
    if A <= 0:
        return
    s = "EL MÉTODO · PARTE 3/5"
    f = font("Inter-ExtraBold.otf", 34)
    tw = d.textlength(s, font=f)
    x0, x1 = W / 2 - tw / 2 - 26, W / 2 + tw / 2 + 26
    d.rounded_rectangle([x0, 252, x1, 304], 26, fill=(10, 16, 34, int(0.8 * A)), outline=CYAN + (A,), width=3)
    d.text((W / 2, 278), s, font=f, fill=CYAN + (A,), anchor="mm")


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        cand = (cur + " " + w).strip()
        if d.textlength(cand, font=f) > maxw and cur:
            lines.append(cur); cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines



def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a




# ---------------- cuerpos y cámara ----------------
CAR_R = 1.6
CAR_TILT = math.radians(18)
CAR_KINDS = ["earth", "ven", "jup", "sun", "bet"]


def star(name, c, r, tex, cc, ce, k, rot):
    return dict(n=name, c=c, r=r, kind="star", tex=tex, cc=cc, ce=ce, k=k, rot=rot)


def make_body(kind, c, r):
    if kind == "sun":
        return star("sun", c, r, SUN, (1.0, 0.62, 0.20), (0.92, 0.20, 0.02), 2.3, 0.02)
    if kind == "bet":
        return star("bet", c, r, BET, (1.0, 0.20, 0.05), (0.42, 0.03, 0.01), 1.45, 0.004)
    return dict(n=kind, c=c, r=r, kind=kind, rot={"earth": 0.12, "jup": 0.10, "ven": 0.03}[kind])


def car_pos(i, t):
    a = 0.35 * (t - CIA[0]) + i * 2 * math.pi / 5 + 0.6
    x, z = CAR_R * math.cos(a), CAR_R * math.sin(a)
    return (x, -z * math.sin(CAR_TILT), z * math.cos(CAR_TILT))


def shot(t):
    """Nombre del plano según el momento."""
    if t < TX0 - 0.15:
        return "jup1"
    if t < ES0 - 0.15:
        return "tierra"
    if t < ES_CAM - 0.1:
        return "grid"
    if t < ES_CUE - 0.1:
        return "venus"
    if t < ES_ETI - 0.1:
        return "gigante"
    if t < SO0 - 0.15:
        return "sol"
    if t < CIA[0] - 0.15:
        return "jup2"
    return "carrusel"


def bodies(t):
    s = shot(t)
    if s == "jup1":
        out = [make_body("jup", (0.0, 0.0, 0.0), 1.0)]
        if t > RA0 - 0.2:
            k = ease_out((t - RA0 + 0.2) / 0.6)
            out.append(make_body("sun", (-1.3, 2.6, -2.5), 0.34 * k + 1e-3))
        return out
    if s in ("tierra", "grid"):
        return [make_body("earth", (0.0, 0.0, 0.0), 1.0)]
    if s == "venus":
        return [make_body("ven", (0.0, 0.0, 0.0), 1.0)]
    if s == "gigante":
        return [make_body("bet", (0.0, 0.0, 0.0), 1.0)]
    if s == "sol":
        return [make_body("sun", (0.0, 0.0, 0.0), 1.0)]
    if s == "jup2":
        return [make_body("jup", (0.0, 0.0, 0.0), 1.0)]
    return [make_body(k, car_pos(i, t), 0.46) for i, k in enumerate(CAR_KINDS)]


def camera(t):
    """Posición de la cámara (mira hacia −z). y > 0 baja los cuerpos en pantalla."""
    s = shot(t)
    if s == "jup1":
        if t < REVEAL1:
            return np.array([0.0, 0.55, 6.4])
        if t < MO0 - 0.15:
            return np.array([0.0, 0.55, lerp(6.4, 6.0, ease((t - REVEAL1) / (MO0 - 0.15 - REVEAL1)))])
        if t < RA0 - 0.15:
            k = (t - MO0 + 0.15) / (RA0 - MO0)
            return np.array([lerp(-0.35, 0.35, k), 0.6, lerp(7.6, 7.0, k)])
        k = (t - RA0 + 0.15) / (TX0 - RA0)
        return np.array([0.0, 0.6, lerp(7.4, 7.0, k)])
    if s == "tierra":
        k = (t - TX0 + 0.15) / (ES0 - TX0)
        return np.array([0.0, 0.55, math.exp(lerp(math.log(7.0), math.log(5.9), ease_out(k)))])
    if s == "grid":
        return np.array([0.0, 0.55, 5.9])
    if s == "venus":
        k = ease_out((t - ES_CAM + 0.1) / (ES_CUE - ES_CAM))
        return np.array([lerp(1.6, -0.25, k), lerp(1.3, 0.5, k), lerp(11.0, 5.6, k)])
    if s == "gigante":
        k = (t - ES_CUE + 0.1) / (ES_ETI - ES_CUE)
        return np.array([0.15, 0.25, lerp(3.9, 3.5, k)])
    if s == "sol":
        k = (t - ES_ETI + 0.1) / (SO0 - ES_ETI)
        return np.array([0.25, 0.45, lerp(7.4, 6.9, k)])
    if s == "jup2":
        if t < MZ0 - 0.1:
            k = (t - SO0 + 0.15) / (MZ0 - SO0)
            return np.array([0.0, 0.5, lerp(9.0, 8.0, ease_out(k))])
        k = (t - MZ0 + 0.1) / (CIA[0] - MZ0)
        return np.array([0.0, 0.5, lerp(8.0, 8.8, k)])
    k = ease_out((t - CIA[0] + 0.15) / 2.0)
    return np.array([0.0, 0.55, lerp(7.0, 9.2, k) + 0.25 * (t - CIA[0]) / (END - CIA[0])])


def shade(body, n, V, t, ndl):
    kind = body["kind"]
    if kind == "star":
        loc = rot_y(n, body["rot"] * t)
        la, lo = latlon(loc)
        g = sample(body["tex"], la, lo)
        mu = np.clip((n * V).sum(-1), 0, 1)
        cc = np.array(body["cc"], np.float32); ce = np.array(body["ce"], np.float32)
        w = (mu ** 0.6)[..., None]
        col = ce * (1 - w) + cc * w
        return col * (body["k"] * (0.55 + 0.9 * (g - 0.55)) * (0.22 + 0.78 * mu ** 0.55))[..., None]
    diff = np.clip(ndl, 0, 1)
    soft = smooth(-0.15, 0.35, ndl) * 0.10
    light = (0.020 + 2.1 * diff + soft)[..., None]
    mu = np.clip((n * V).sum(-1), 0, 1)
    if kind in ("jup", "ven"):
        tilt = -8 if kind == "jup" else 4
        loc = rot_y(rot_x(n, math.radians(tilt)), body["rot"] * t + 0.4)
        la, lo = latlon(loc)
        alb = sample(JUP if kind == "jup" else VEN, la, lo)
        col = alb * light * (0.75 + 0.25 * mu ** 0.5)[..., None]
        if kind == "ven":
            fres = (1 - mu) ** 3
            col = col + np.array([0.9, 0.7, 0.35]) * (fres * 0.5 * np.clip(ndl + 0.3, 0, 1))[..., None]
        return col
    loc = rot_y(rot_x(n, math.radians(16)), -1.72 + body["rot"] * t)
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.88) + 0.80 * cl * 0.88
    R = 2 * ndl[..., None] * n - LIGHT
    spec = np.clip((R * V).sum(-1), 0, 1) ** 60 * (1 - land) * (1 - cl[..., 0]) * 0.5
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85])
    fres = (1 - mu) ** 2.6
    atm = np.array([0.22, 0.50, 1.0]) * (fres * 1.3 * np.clip(ndl + 0.35, 0, 1))[..., None]
    return col + atm


def draw_sphere(img, O, body, t):
    C = np.array(body["c"]); r = body["r"]
    rel = C - O
    dist_c = float(np.linalg.norm(rel))
    if r < 0.01 or dist_c <= r * 1.0001 or rel[2] >= 0:
        return
    depth = -rel[2]
    cxp = (rel[0] / depth / TX + 1) / 2 * W
    cyp = (1 - rel[1] / depth / TY) / 2 * H
    rpx = math.tan(math.asin(r / dist_c)) / PIX
    star_k = body["kind"] == "star"
    halo = 1.10 if body["kind"] == "earth" else (2.2 if star_k else 1.0)
    ext = rpx * halo * 1.15 + 4
    x0 = int(max(0, cxp - ext)); x1 = int(min(W, cxp + ext + 1))
    y0 = int(max(0, cyp - ext)); y1 = int(min(H, cyp + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return
    d = DIRS[y0:y1, x0:x1]
    oc = O - C
    b = d @ oc
    perp2 = np.maximum(float(oc @ oc) - b * b, 0)
    dist = np.sqrt(perp2)
    pixw = np.maximum(-b, 1e-9) * PIX
    alpha = np.clip((r - dist) / pixw + 0.5, 0, 1)
    region = img[y0:y1, x0:x1]
    if star_k:
        cor = np.clip(dist / r - 1, 0, None)
        glow = (np.exp(-cor / 0.12) * 0.55 + np.exp(-cor / 0.40) * 0.18) * (1 - smooth(0.6, 1.2, cor))
        region += (glow * (1 - alpha) * (dist > r * 0.99))[..., None] * np.array(body["cc"]) * body["k"] * 0.6
    if body["kind"] == "earth":
        hz = (dist > r * 0.995) & (dist < r * halo)
        if hz.any():
            dd = (dist[hz] - r) / (0.03 * r)
            P = O + (-b[hz])[:, None] * d[hz]
            nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
            lit = np.clip(nn @ LIGHT + 0.4, 0, 1)
            gl = np.exp(-np.maximum(dd, 0)) * lit * 0.55
            region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([0.25, 0.52, 1.0])
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]; bs = b[sel]
    tt = -bs - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = O + tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    col = shade(body, n, -ds, t, n @ LIGHT)
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


def screen_disc(O, C=(0.0, 0.0, 0.0), r=1.0):
    cx, cy, depth = project(C, O)
    dist = float(np.linalg.norm(np.array(C) - O))
    return cx, cy, math.tan(math.asin(min(0.999, r / dist))) / PIX

# ---------------- gráficos de esta parte ----------------
_mono = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO = _mono if os.path.exists(_mono) else FD + "Inter-ExtraBold.otf"


def mono(size):
    key = ("mono", size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(MONO, size)
    return _fc[key]


def chip(d, cx, cy, s, col, A, size=44, fill=(10, 16, 34)):
    f = font("Inter-Black.otf", size)
    tw = d.textlength(s, font=f)
    d.rounded_rectangle([cx - tw / 2 - 28, cy - size * 0.75, cx + tw / 2 + 28, cy + size * 0.75], int(size * 0.75),
                        fill=fill + (int(0.85 * A),), outline=col + (A,), width=4)
    d.text((cx, cy), s, font=f, fill=col + (A,), anchor="mm")


def tile_grid(O):
    cx, cy, rpx = screen_disc(O)
    TS = 72
    x0 = int((cx - rpx - 8) // TS * TS); x1 = int(cx + rpx + 8)
    y0 = int((cy - rpx - 8) // TS * TS); y1 = int(cy + rpx + 8)
    tiles = [(x, y) for y in range(y0, y1, TS) for x in range(x0, x1, TS)]
    return tiles, TS


def reveal_k(t):
    return min(1.0, max(0.0, (t - REVEAL0) / (REVEAL1 - REVEAL0)))


def wireframe(layer, O, t, A):
    """Malla de alambre de la esfera (la parte que todavía no se dibuja)."""
    d = ImageDraw.Draw(layer)
    V0 = O / np.linalg.norm(O)
    col = CYAN + (int(110 * A),)
    def pt(v):
        x, y, _ = project(v, O)
        return (x, y)
    spin = 0.10 * t + 0.4
    for lat in range(-60, 61, 20):
        la = math.radians(lat); pts = []
        for k in range(0, 361, 6):
            lo = math.radians(k)
            v = np.array([math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)])
            if v @ (O - v) > 0:
                pts.append(pt(v))
            elif len(pts) > 1:
                d.line(pts, fill=col, width=2); pts = []
            else:
                pts = []
        if len(pts) > 1:
            d.line(pts, fill=col, width=2)
    for k in range(0, 360, 30):
        lo = math.radians(k) + spin; pts = []
        for lat in range(-90, 91, 6):
            la = math.radians(lat)
            v = np.array([math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)])
            if v @ (O - v) > 0:
                pts.append(pt(v))
            elif len(pts) > 1:
                d.line(pts, fill=col, width=2); pts = []
            else:
                pts = []
        if len(pts) > 1:
            d.line(pts, fill=col, width=2)


def draw_hook(layer, t, O):
    d = ImageDraw.Draw(layer)
    al = fade(t, 0.1, MO0 - 0.15, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    if t < REVEAL1 + 0.3:
        txt(d, (W / 2, 420), "NO ES UNA FOTO", 100, WHITE, int(A * ease_out(t / 0.5)))
        k = reveal_k(t)
        sub = "dibujando… %d %%" % int(round(100 * k)) if k < 1 else "¡listo!"
        txt(d, (W / 2, 530), sub, 58, CYAN if k < 1 else YELLOW, A, "Inter-ExtraBold.otf", 7)
        # barra de progreso
        bx0, bx1, by = 240, W - 240, 600
        d.rounded_rectangle([bx0, by - 10, bx1, by + 10], 10, fill=(10, 16, 34, int(0.8 * A)), outline=CYAN + (A,), width=3)
        if k > 0:
            d.rounded_rectangle([bx0 + 4, by - 6, bx0 + 4 + (bx1 - bx0 - 8) * k, by + 6], 6, fill=YELLOW + (A,))
        # bloques que se están calculando
        if 0 < k < 1:
            tiles, TS = tile_grid(O)
            i = int(k * len(tiles))
            for j in range(i, min(len(tiles), i + 2)):
                x, y = tiles[j]
                d.rectangle([x, y, x + TS - 1, y + TS - 1], outline=YELLOW + (A,), width=3)
    else:
        k = ease_out((t - REVEAL1 - 0.3) / 0.4)
        txt(d, (W / 2, 430 + (1 - k) * 24), "ASÍ ANIMAMOS", 96, WHITE, int(A * k))
        txt(d, (W / 2, 545 + (1 - k) * 24), "CADA VIDEO", 112, YELLOW, int(A * k))


CODE = ["def draw_sphere(img, O, body, t):",
        "    oc = O - C",
        "    b = d @ oc",
        "    perp2 = oc @ oc - b * b",
        "    tt = -b - sqrt(r*r - perp2)",
        "    P = O + tt * d     # choque",
        "    col = shade(body, n, t)"]


def draw_motor(layer, t):
    al = fade(t, MO0 - 0.1, RA0 - 0.15, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - MO0) / 0.35)) * 40
    x0, x1, y0 = 70, W - 70, 350 + rise
    y1 = y0 + 120 + 60 * len(CODE)
    d.rounded_rectangle([x0, y0, x1, y1], 30, fill=(8, 12, 26, int(0.88 * A)), outline=CYAN + (A,), width=4)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x0 + 34 + 34 * i, y0 + 30, x0 + 56 + 34 * i, y0 + 52], fill=c + (A,))
    d.text((x1 - 36, y0 + 42), "motor 3D · PYTHON", font=font("Inter-Black.otf", 34), fill=YELLOW + (A,), anchor="rm")
    total = sum(len(c) for c in CODE)
    k = (t - MO0 - 0.3) / max(0.5, (MO1 - MO0) * 0.7)
    n = int(total * min(1.0, max(0.0, k)))
    f = mono(34)
    y = y0 + 110; shown = 0
    for ln in CODE:
        part = ln[:max(0, n - shown)]; shown += len(ln)
        if "#" in part:
            a, b2 = part.split("#", 1)
            d.text((x0 + 36, y), a, font=f, fill=WHITE + (A,), anchor="lm")
            d.text((x0 + 36 + d.textlength(a, font=f), y), "#" + b2, font=f, fill=YELLOW + (A,), anchor="lm")
        else:
            colr = CYAN if part.startswith("def") else WHITE
            d.text((x0 + 36, y), part, font=f, fill=colr + (A,), anchor="lm")
        if 0 < len(part) < len(ln) and int(t * 4) % 2 == 0:
            cx = x0 + 36 + d.textlength(part, font=f) + 4
            d.rectangle([cx, y - 20, cx + 5, y + 20], fill=YELLOW + (A,))
        y += 60
    k2 = ease_out((t - (MO0 + 0.72 * (MO1 - MO0))) / 0.3)
    if k2 > 0:
        chip(d, W / 2, y1 + 70, "TRAZADO DE RAYOS", YELLOW, int(A * k2), 52)


EYE = (W - 165, 560)
RAY_TARGETS = [(-0.62, 0.55), (-0.2, 0.85), (0.3, 0.7), (0.75, 0.35), (-0.35, 0.05), (1.25, 0.9), (0.15, -0.3), (-0.8, -0.2), (1.3, -0.1)]


def draw_rayos(layer, t, O):
    al = fade(t, RA0 - 0.1, TX0 - 0.15, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    cx, cy, rpx = screen_disc(O)
    sx, sy, srp = screen_disc(O, (-1.3, 2.6, -2.5), 0.34)
    # pantalla de pixeles junto al ojo
    ex, ey = EYE
    g = 22
    for i in range(5):
        for j in range(5):
            xx, yy = ex - 55 + i * g, ey - 55 + j * g
            d.rectangle([xx, yy, xx + g - 3, yy + g - 3], fill=(20, 40, 70, int(0.9 * A)), outline=CYAN + (int(0.7 * A),), width=1)
    txt(d, (ex, ey - 100), "CÁMARA", 36, CYAN, A, "Inter-Black.otf", 5)
    txt(d, (W / 2 + 60, 380), "1 PIXEL = 1 RAYO", 64, WHITE, int(A * ease_out((t - RA0) / 0.4)))
    for k, (ux, uy) in enumerate(RAY_TARGETS):
        tk = RA0 + 0.3 + 0.23 * k
        s = ease_out((t - tk) / 0.25)
        if s <= 0:
            continue
        hit = ux * ux + uy * uy < 1.0
        tx_, ty_ = cx + ux * rpx * 0.98, cy - uy * rpx * 0.98
        if not hit:
            dx, dy = tx_ - ex, ty_ - ey
            tx_, ty_ = ex + dx * 1.8, ey + dy * 1.8
        sxp = ex - 44 + (k % 5) * g; syp = ey - 44 + (k // 5) * g * 2
        px, py = sxp + (tx_ - sxp) * s, syp + (ty_ - syp) * s
        main = k == 0
        colr = YELLOW if main else (CYAN if hit else (120, 140, 170))
        d.line([(sxp, syp), (px, py)], fill=colr + (int(A * (1.0 if main else 0.65)),), width=6 if main else 3)
        if hit and s >= 1:
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=colr + (A,))
    # el rayo principal: dónde choca y cuánta luz recibe
    hx, hy = cx + RAY_TARGETS[0][0] * rpx * 0.98, cy - RAY_TARGETS[0][1] * rpx * 0.98
    k1 = ease_out((t - RA_HIT) / 0.3)
    if k1 > 0:
        r = 16 + 10 * k1
        d.ellipse([hx - r, hy - r, hx + r, hy + r], outline=YELLOW + (int(A * k1),), width=5)
        txt(d, (hx + 20, hy + 75), "CHOCA", 54, YELLOW, int(A * k1))
    k2 = ease_out((t - RA_LUZ) / 0.4)
    if k2 > 0:
        lx, ly = hx + (sx - hx) * k2, hy + (sy - hy) * k2
        for wdt, a2 in ((16, 0.25), (6, 1.0)):
            d.line([(hx, hy), (lx, ly)], fill=(255, 200, 90, int(A * a2)), width=wdt)
        txt(d, ((hx + sx) / 2 - 70, (hy + sy) / 2 + 10), "LUZ", 60, (255, 200, 90), int(A * k2))


MAP = None


def map_img():
    global MAP
    if MAP is None:
        im = Image.fromarray((EARTH_S * 255).astype(np.uint8)).resize((880, 440), Image.LANCZOS)
        MAP = im.convert("RGBA")
    return MAP


def draw_texturas(layer, t):
    al = fade(t, TX0 - 0.1, ES0 - 0.15, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - TX0 + 0.1) / 0.45)
    x0, y0 = 100, 350 + (1 - k) * 40
    m = map_img().copy()
    m.putalpha(int(A * 0.95))
    layer.alpha_composite(m, (x0, int(y0)))
    d.rectangle([x0 - 3, y0 - 3, x0 + 883, y0 + 443], outline=CYAN + (A,), width=4)
    # cuadrícula de coordenadas
    for i in range(1, 6):
        xx = x0 + 880 * i / 6
        d.line([(xx, y0), (xx, y0 + 440)], fill=CYAN + (int(A * 0.25),), width=1)
    for j in range(1, 3):
        yy = y0 + 440 * j / 3
        d.line([(x0, yy), (x0 + 880, yy)], fill=CYAN + (int(A * 0.25),), width=1)
    d.rounded_rectangle([x0 + 18, y0 + 18, x0 + 400, y0 + 74], 20, fill=(8, 12, 26, int(0.85 * A)))
    d.text((x0 + 36, y0 + 46), "textures.py → tierra", font=mono(30), fill=WHITE + (A,), anchor="lm")
    # línea que recorre el mapa (la textura se envuelve en la esfera)
    sx = x0 + 880 * (((t - TX0) * 0.35) % 1.0)
    d.line([(sx, y0), (sx, y0 + 440)], fill=YELLOW + (A,), width=4)
    for i in range(3):
        ay = y0 + 470 + i * 26 + 12 * math.sin(6 * t + i)
        d.polygon([(W / 2 - 24, ay), (W / 2 + 24, ay), (W / 2, ay + 18)], fill=YELLOW + (int(A * (0.9 - 0.25 * i)),))
    k2 = ease_out((t - TX_REAL) / 0.3)
    if k2 > 0:
        chip(d, W / 2, y0 + 380, "CONTINENTES REALES", YELLOW, int(A * k2), 46)


THUMBS = None


def thumbs():
    global THUMBS
    if THUMBS is None:
        THUMBS = [Image.open(os.path.join(BASE, "thumbs", f"{i}.jpg")).convert("RGBA").resize((260, 462), Image.LANCZOS) for i in range(6)]
    return THUMBS


def draw_grid(layer, t):
    al = fade(t, ES0 - 0.15, ES_CAM - 0.1, 0.15)
    if al <= 0:
        return
    A = int(255 * al)
    layer.alpha_composite(Image.new("RGBA", (W, H), (4, 6, 12, int(150 * al))))
    d = ImageDraw.Draw(layer)
    for i, th in enumerate(thumbs()):
        k = ease_out((t - ES0 - 0.1 - 0.18 * i) / 0.3)
        if k <= 0:
            continue
        cx = 120 + (i % 3) * 290; cy = 350 + (i // 3) * 492 + (1 - k) * 50
        im = th.copy(); im.putalpha(int(A * k))
        layer.alpha_composite(im, (int(cx), int(cy)))
        d.rectangle([cx - 3, cy - 3, cx + 263, cy + 465], outline=(CYAN if i % 2 else YELLOW) + (int(A * k),), width=4)
    k = ease_out((t - wtime("escena", 5)) / 0.3)
    if k > 0:
        chip(d, W / 2, 841, "ESCENA NUEVA", YELLOW, int(A * k), 70)
    k3 = ease_out((t - wtime("escena", 7)) / 0.25)
    if k3 > 0:
        chip(d, W / 2, 950, "NO ES PLANTILLA", WHITE, int(A * k3), 46, (60, 10, 14))


def draw_chips_escena(layer, t, O):
    al = fade(t, ES_CAM - 0.1, SO0 - 0.15, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    labels = [("CÁMARA", ES_CAM), ("CUERPOS", ES_CUE), ("ETIQUETAS", ES_ETI)]
    xs_ = [215, W / 2, W - 215]
    for (s, ts), x in zip(labels, xs_):
        k = ease_out((t - ts + 0.1) / 0.25)
        if k <= 0:
            continue
        active = (shot(t) == {"CÁMARA": "venus", "CUERPOS": "gigante", "ETIQUETAS": "sol"}[s])
        chip(d, x, 380, s, YELLOW if active else CYAN, int(A * k * (1.0 if active else 0.6)), 42)
    if shot(t) == "venus":
        # marco de cámara
        k = ease_out((t - ES_CAM) / 0.4)
        m = 60 + 40 * (1 - k)
        for (ax, ay, sx_, sy_) in ((m, 470, 1, 1), (W - m, 470, -1, 1), (m, 1240, 1, -1), (W - m, 1240, -1, -1)):
            d.line([(ax, ay), (ax + 70 * sx_, ay)], fill=WHITE + (int(A * 0.8),), width=6)
            d.line([(ax, ay), (ax, ay + 70 * sy_)], fill=WHITE + (int(A * 0.8),), width=6)
        if int(t * 2) % 2 == 0:
            d.ellipse([m + 30, 500, m + 56, 526], fill=RED + (A,))
        d.text((m + 70, 513), "REC", font=font("Inter-Black.otf", 36), fill=WHITE + (A,), anchor="lm")
    if shot(t) == "sol":
        cx, cy, rpx = screen_disc(O)
        k = ease_out((t - ES_ETI) / 0.35)
        px, py = cx + rpx * 0.55, cy - rpx * 0.75
        lx, ly = W - 230, 560
        d.line([(px, py), (lx, ly + 50)], fill=WHITE + (int(A * k),), width=5)
        d.ellipse([px - 10, py - 10, px + 10, py + 10], fill=WHITE + (int(A * k),))
        d.rounded_rectangle([lx - 170, ly - 60, lx + 170, ly + 50], 22, fill=(10, 16, 34, int(0.88 * A * k)), outline=YELLOW + (int(A * k),), width=4)
        txt(d, (lx, ly - 5), "SOL", 76, YELLOW, int(A * k), "Inter-Black.otf", 0)


# espectro real de la música y los efectos de este video
try:
    _sr, _wav = wavfile.read(os.path.join(BASE, "out", "sfx_music.wav"))
    MIXW = _wav.astype(np.float32).mean(-1) / 32768.0
except Exception:
    _sr, MIXW = 48000, np.zeros(48000 * 60, np.float32)
NB = 48
_edges = np.geomspace(60, 9000, NB + 1)


def spectrum(t):
    i = int(t * _sr); n = 4096
    seg = MIXW[max(0, i - n // 2): i + n // 2]
    if len(seg) < n:
        seg = np.pad(seg, (0, n - len(seg)))
    F = np.abs(np.fft.rfft(seg * np.hanning(n)))
    fr = np.fft.rfftfreq(n, 1 / _sr)
    out = np.array([F[(fr >= a) & (fr < b)].mean() if ((fr >= a) & (fr < b)).any() else 0 for a, b in zip(_edges, _edges[1:])])
    out = np.log1p(out * 2.0) / 3.2
    return np.clip(out, 0, 1)


def draw_sonido(layer, t, O):
    al = fade(t, SO0 - 0.15, CIA[0] - 0.15, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    cx, cy, rpx = screen_disc(O)
    sp = spectrum(t)
    for i in range(NB * 2):
        v = sp[i if i < NB else 2 * NB - 1 - i]
        a = -math.pi / 2 + i / (2 * NB) * 2 * math.pi
        r0 = rpx + 22; r1 = r0 + 18 + 150 * v
        col = YELLOW if v > 0.55 else CYAN
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=col + (int(A * 0.9),), width=8)
    if t < MZ0 - 0.1:
        k1 = ease_out((t - SO_EF + 0.1) / 0.3)
        k2 = ease_out((t - SO_MU + 0.1) / 0.3)
        if k1 > 0:
            chip(d, 300, 400, "EFECTOS", CYAN, int(A * k1), 56)
        if k2 > 0:
            chip(d, W - 300, 400, "MÚSICA", CYAN, int(A * k2), 56)
        k3 = ease_out((t - wtime("sonido", 11)) / 0.3)
        if k3 > 0:
            txt(d, (W / 2, 505), "sintetizados con código", 54, WHITE, int(A * k3), "Inter-ExtraBold.otf", 7)
        k4 = ease_out((t - SO_OR + 0.1) / 0.25)
        if k4 > 0:
            s = 1.4 - 0.4 * k4
            txt(d, (W / 2, 620), "ORIGINALES", int(104 * s), YELLOW, int(A * k4))
    else:
        draw_mezcla(d, t, A)


def draw_mezcla(d, t, A):
    k = ease_out((t - MZ0 + 0.1) / 0.4)
    A = int(A * k)
    x0, x1, y0, y1 = 110, W - 110, 345, 800
    d.rounded_rectangle([x0, y0, x1, y1], 30, fill=(8, 12, 26, int(0.88 * A)), outline=CYAN + (A,), width=4)
    d.text((x0 + 36, y0 + 46), "MEZCLA", font=font("Inter-Black.otf", 44), fill=YELLOW + (A,), anchor="lm")
    names = ["VOZ", "MÚSICA", "EFECTOS"]
    lv = [0.82, 0.38, 0.55]
    for i, nm in enumerate(names):
        fx = x0 + 110 + i * 150
        d.line([(fx, y0 + 110), (fx, y1 - 90)], fill=(60, 80, 110, A), width=8)
        v = lv[i] + 0.05 * math.sin(3 * t + i)
        fy = (y1 - 90) - (y1 - 200 - y0) * v
        d.rounded_rectangle([fx - 34, fy - 16, fx + 34, fy + 16], 8, fill=WHITE + (A,))
        d.text((fx, y1 - 50), nm, font=font("Inter-Black.otf", 30), fill=WHITE + (A,), anchor="mm")
    # medidor de volumen que llega a −14 LUFS
    mx0, mx1 = x0 + 560, x1 - 50
    top, bot = y0 + 110, y1 - 90
    target = top + (bot - top) * 0.30
    p = ease((t - MZ0) / (0.7 * (MZ1 - MZ0)))
    lev = bot - (bot - target) * p + 6 * math.sin(11 * t) * p
    d.rectangle([mx0, top, mx1, bot], outline=CYAN + (A,), width=3)
    lev = min(lev, bot - 4)
    d.rectangle([mx0 + 6, lev, mx1 - 6, bot - 4], fill=(CYAN if p < 0.98 else YELLOW) + (A,))
    d.line([(mx0 - 20, target), (mx1 + 20, target)], fill=YELLOW + (A,), width=5)
    d.text(((mx0 + mx1) / 2, target - 34), "−14 LUFS", font=font("Inter-Black.otf", 44), fill=YELLOW + (A,), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))
    d.text(((mx0 + mx1) / 2, y1 - 50), "VOLUMEN", font=font("Inter-Black.otf", 30), fill=WHITE + (A,), anchor="mm")
    k2 = ease_out((t - (MZ0 + 0.55 * (MZ1 - MZ0))) / 0.3)
    if k2 > 0:
        txt(d, (W / 2, y1 + 70), "YOUTUBE · INSTAGRAM · TIKTOK", 44, WHITE, int(A * k2), "Inter-Black.otf", 6)


def draw_cierre(layer, t):
    al = fade(t, CIA[0] + 0.1, CIB[0] - 0.15, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - CIA[0] - 0.1) / 0.35)
    txt(d, (W / 2, 420 + (1 - k) * 24), "IMAGEN + SONIDO", 88, WHITE, int(A * k))
    k2 = ease_out((t - (CIA[0] + 0.45 * (CIA[1] - CIA[0]))) / 0.3)
    txt(d, (W / 2, 545), "= CÓDIGO", 120, YELLOW, int(A * k2))


def draw_next(layer, t):
    al = fade(t, CIB[0] - 0.15, CARD + 0.1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    txt(d, (W / 2, 395), "PARTE 4", 128, YELLOW, A)
    txt(d, (W / 2, 515), "GITHUB", 104, WHITE, A)
    txt(d, (W / 2, 605), "el cerebro del canal", 54, CYAN, A, "Inter-ExtraBold.otf", 7)
    # grafo de commits: una rama que sale y vuelve
    gy = 715
    xs_ = [200, 335, 470, 610, 745, 880]
    tb = CIB[0] + 0.4
    for i, x in enumerate(xs_):
        k = ease_out((t - tb - 0.2 * i) / 0.25)
        if k <= 0:
            continue
        if i > 0:
            d.line([(xs_[i - 1], gy), (xs_[i - 1] + (x - xs_[i - 1]) * k, gy)], fill=CYAN + (A,), width=8)
        r = 20 * k
        d.ellipse([x - r, gy - r, x + r, gy + r], fill=(YELLOW if i in (0, 5) else CYAN) + (A,), outline=INK + (A,), width=4)
    kb = ease_out((t - tb - 0.5) / 0.5)
    if kb > 0:
        pts = [(335, gy), (405, gy - 60), (540, gy - 60), (680, gy - 60), (745, gy)]
        n = max(2, int(len(pts) * kb + 0.999))
        d.line(pts[:n], fill=YELLOW + (A,), width=7, joint="curve")
        for p in pts[1:4][:n - 1]:
            d.ellipse([p[0] - 14, p[1] - 14, p[0] + 14, p[1] + 14], fill=YELLOW + (A,), outline=INK + (A,), width=3)
    late = int(A * min(1.0, max(0.0, (t - (CIB[0] + 0.5 * (CIB[1] - CIB[0]))) / 0.3)))
    txt(d, (W / 2, 840), "¡ESTÉN ATENTOS!", 76, WHITE, late)


def draw_endcard(layer, t):
    al = fade(t, CARD, END + 1, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    layer.alpha_composite(Image.new("RGBA", (W, H), (4, 6, 12, int(175 * al))))
    d = ImageDraw.Draw(layer)
    k = ease_out((t - CARD) / 0.4)
    d.polygon(bolt(W / 2, 760, 230 + 40 * k), fill=YELLOW + (A,))
    txt(d, (W / 2, 990), "FLASH DATOS", 104, WHITE, A)
    txt(d, (W / 2, 1100), "Síguenos: mañana la parte 4", 50, CYAN, A, "Inter-ExtraBold.otf", 6)
    txt(d, (W / 2, 1165), "del método", 50, CYAN, A, "Inter-ExtraBold.otf", 6)


def overlays(frame_u8, t, O):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_hook(layer, t, O)
    draw_motor(layer, t)
    draw_rayos(layer, t, O)
    draw_texturas(layer, t)
    draw_grid(layer, t)
    draw_chips_escena(layer, t, O)
    draw_sonido(layer, t, O)
    draw_cierre(layer, t)
    draw_next(layer, t)
    draw_caption(layer, t)
    d = ImageDraw.Draw(layer)
    badge(d, t, int(255 * fade(t, 0.4, CARD, 0.3)))
    draw_watermark(layer, t)
    draw_endcard(layer, t)
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
    O = camera(t)
    img = BG.copy()
    bs = bodies(t)
    bs.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"]) - O)))
    for b in bs:
        draw_sphere(img, O, b, t)
    if t < REVEAL1:
        # render en vivo: los bloques ya calculados muestran el planeta; el resto, la malla de alambre
        k = reveal_k(t)
        tiles, TS = tile_grid(O)
        mask = np.zeros((H, W), bool)
        for (x, y) in tiles[:int(k * len(tiles))]:
            mask[max(0, y):y + TS, max(0, x):x + TS] = True
        img = np.where(mask[..., None], img, BG)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    if t < REVEAL1:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        wireframe(lay, O, t, 1.0)
        a = np.asarray(lay).astype(np.float32) / 255
        u8 = (u8 * (1 - a[..., 3:] * (~mask[..., None])) + a[..., :3] * 255 * a[..., 3:] * (~mask[..., None])).astype(np.uint8)
    return overlays(u8, t, O)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        for ts in sys.argv[2:]:
            t = float(ts)
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, flush=True)
    elif mode == "chunk":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(render(f / FPS).tobytes())
            if f % 60 == 0:
                print(f"{out}: {f}/{b}", flush=True)
        p.stdin.close(); p.wait()
        print("listo", out, flush=True)
    elif mode == "info":
        print("frames", NFRAMES, "end", END, "card", CARD, "cam/cue/eti", round(ES_CAM, 2), round(ES_CUE, 2), round(ES_ETI, 2))
