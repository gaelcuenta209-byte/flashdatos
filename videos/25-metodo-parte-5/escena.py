"""Flash Datos · video 25 · Serie "El método", parte 5/5: todo conectado, así funciona solo.

La Tierra con la luz del día que cambia: un botón PUBLICAR que se aprieta solo; Metricool
(nodo verde) reparte el video a tres nodos en órbita (YouTube, Instagram y TikTok); un Sol
que sale por la izquierda, pasa por arriba y se pone a la derecha marca las tres tareas de
Claude (reporte de la mañana, video del día, verificación de la tarde); un celular con el
"SÍ" y el aviso si algo falla; y al final la cámara se aleja y siete nodos (Claude,
ElevenLabs, GitHub, Metricool y las tres redes) forman una constelación alrededor de la
Tierra: el método completo. Cierre de la serie sin suspenso.

Uso:
  python3 escena.py info
  python3 escena.py test 1 5 12 ...
  python3 escena.py chunk <ini> <fin> <out>
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom

BASE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
TY = math.tan(math.radians(20)); TX = TY * W / H
PIX = 2 * TY / H

xs = ((np.arange(W) + 0.5) / W * 2 - 1) * TX
ys = (1 - (np.arange(H) + 0.5) / H * 2) * TY
DX, DY = np.meshgrid(xs, ys)
NRM = np.sqrt(DX * DX + DY * DY + 1)
DIRS = np.stack([DX / NRM, DY / NRM, -1 / NRM], axis=-1)

LIGHT = np.array([-0.50, 0.55, 0.67]); LIGHT /= np.linalg.norm(LIGHT)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
EARTH = lin(np.clip(T("earth"), 0, 1)); CLOUDS = T("earth_clouds"); LAND = T("earth_land")


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




LIGHT0 = LIGHT.copy()
LCOL = np.array([1.0, 1.0, 1.0])


# ---------------- fondo: estrellas y nebulosa azul-dorada (distinta a las partes 1-4) ----------------
def make_background():
    rng = np.random.default_rng(25)
    bg = np.zeros((H, W, 3), np.float32)
    n = 2000
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.025 + 0.45 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.86 + 0.14 * tint, 0.88 + 0.04 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 50
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.88]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 34.0
    neb = fbm(gx, gy, np.full_like(gx, 5.1), 5, seed=2525)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.4, 0, 1) ** 1.5
    yy = np.linspace(0, 1, H)[:, None]
    bg += neb[..., None] * (np.array([0.012, 0.026, 0.060], np.float32) * (1 - yy[..., None]) + np.array([0.050, 0.030, 0.010], np.float32) * yy[..., None])
    return bg


BG = make_background()

# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
HK0, HK1 = SEG["hook"]["t0"], SEG["hook"]["t1"]
MT0, MT1 = SEG["metricool"]["t0"], SEG["metricool"]["t1"]
TA0, TA1 = SEG["tareas"]["t0"], SEG["tareas"]["t1"]
MA0, MA1 = SEG["manana"]["t0"], SEG["manana"]["t1"]
VI0, VI1 = SEG["video"]["t0"], SEG["video"]["t1"]
TR0, TR1 = SEG["tarde"]["t0"], SEG["tarde"]["t1"]
SI0, SI1 = SEG["si"]["t0"], SEG["si"]["t1"]
CI0, CI1 = SEG["cierre"]["t0"], SEG["cierre"]["t1"]
CIA = SEG["cierre"]["parts"][0]
CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
END = TM["end"]
NFRAMES = int(round(END * FPS))
PRESS_T = HK0 + 1.55          # el botón se aprieta solo
FAIL_T = SI0 + 1.9            # "Y si algo falla…"
FL = [MT0 - 0.18, TA0 - 0.18, SI0 - 0.18, CIA[0] - 0.18, CIB[0] - 0.15, CARD - 0.05]
DAY0, DAY1 = TA0 - 0.18, SI0 - 0.18

NETS = [("YOUTUBE", (1.0, 0.32, 0.32)), ("INSTAGRAM", (1.0, 0.45, 0.80)), ("TIKTOK", (0.35, 0.92, 0.92))]
CONST = [("CLAUDE", (1.0, 0.82, 0.25)), ("ELEVENLABS", (0.30, 0.85, 1.0)), ("GITHUB", (0.92, 0.94, 1.0)),
         ("METRICOOL", (0.47, 0.94, 0.55)), ("YOUTUBE", (1.0, 0.32, 0.32)), ("INSTAGRAM", (1.0, 0.45, 0.80)),
         ("TIKTOK", (0.35, 0.92, 0.92))]
MC_COL = (0.47, 0.94, 0.55)
def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s



def keyinterp(t, keys):
    if t <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if t <= b:
            return lerp(va, vb, ease((t - a) / (b - a)))
    return keys[-1][1]


def shot(t):
    if t < MT0 - 0.18:
        return "hook"
    if t < DAY0:
        return "metricool"
    if t < DAY1:
        return "day"
    if t < CIA[0] - 0.18:
        return "si"
    return "const"


SUN_KEYS = []


def sun_theta(t):
    keys = [(DAY0, 172.0), (MA0, 162.0), (MA1, 132.0), (VI0, 118.0), (VI1, 64.0), (TR0, 46.0), (DAY1, 12.0)]
    return math.radians(keyinterp(t, keys))


def sun_pos(t):
    th = sun_theta(t)
    return (1.55 * math.cos(th), 0.12 + 1.38 * math.sin(th), -2.4)


def sun_col(t):
    th = math.degrees(sun_theta(t))
    k = math.sin(math.radians(th))           # 0 en el horizonte, 1 arriba
    warm = np.array([1.0, 0.62, 0.30]); noon = np.array([1.0, 0.95, 0.80])
    return warm + (noon - warm) * k


def set_light(t):
    global LIGHT, LCOL
    if shot(t) == "day":
        s = np.array(sun_pos(t)); s /= np.linalg.norm(s)
        L = s + np.array([0.0, 0.0, 0.95]); L /= np.linalg.norm(L)
        LIGHT = L
        LCOL = 0.35 + 0.65 * sun_col(t)
    else:
        LIGHT = LIGHT0.copy(); LCOL = np.array([1.0, 1.0, 1.0])


R_NET = 1.22
TILT = math.radians(18)


def ring_pos(a, R, tilt, y0=0.0):
    x, z = R * math.cos(a), R * math.sin(a)
    return (x, y0 - z * math.sin(tilt), z * math.cos(tilt))


def net_pos(i, t):
    return ring_pos(0.42 * t + i * 2 * math.pi / 3 + 0.9, R_NET, TILT)


R_CON = 1.72
TILT_C = math.radians(24)


def const_pos(i, t):
    return ring_pos(0.22 * t + i * 2 * math.pi / 7 + 1.2, R_CON, TILT_C, 0.05)


def const_on(i, t):
    t0 = CIA[0] + 0.4 + i * 0.42
    return ease_out((t - t0) / 0.35)


def bodies(t):
    sh = shot(t)
    out = [dict(n="earth", c=(0.0, 0.0, 0.0), r=1.0, kind="earth", rot=0.05)]
    if sh == "metricool":
        k = ease_out((t - MT0 - 0.15) / 0.4)
        out.append(dict(n="mc", c=(0.0, 1.42 + 0.04 * math.sin(2 * t), 0.25), r=0.17 * k + 1e-3, kind="glow", col=MC_COL,
                        k=1.0 + 0.3 * math.sin(6 * t)))
    if sh in ("metricool", "day", "si"):
        for i, (nm, col) in enumerate(NETS):
            k = 1.0 if sh != "metricool" else ease_out((t - (MT0 + 1.4 + 0.45 * i)) / 0.35)
            if k <= 0:
                continue
            hot = 1.0
            if sh == "day" and TR0 + 0.3 * i < t < TR1 + 0.4:
                hot = 1.7
            out.append(dict(n=f"n{i}", c=net_pos(i, t), r=0.11 * k + 1e-3, kind="glow", col=col, k=hot))
    if sh == "day":
        out.append(dict(n="sun", c=sun_pos(t), r=0.30, kind="sun"))
    if sh == "const":
        for i, (nm, col) in enumerate(CONST):
            k = const_on(i, t)
            if k <= 0:
                continue
            out.append(dict(n=f"c{i}", c=const_pos(i, t), r=0.13 * k + 1e-3, kind="glow", col=col, k=1.0 + 0.25 * math.sin(3 * t + i)))
    return out


def camera(t):
    """(x, y, distancia) de la cámara. y > 0 baja la Tierra en pantalla."""
    sh = shot(t)
    if sh == "hook":
        D = math.exp(lerp(math.log(15.0), math.log(6.0), ease_out(t / 3.2)))
        return 0.0, 0.58, D
    if sh == "metricool":
        k = (t - MT0 + 0.18) / (DAY0 - MT0 + 0.18)
        return 0.0, 0.62, lerp(8.0, 7.3, ease(k))
    if sh == "day":
        k = (t - DAY0) / (DAY1 - DAY0)
        return lerp(-0.12, 0.12, ease(k)), 0.60, lerp(7.2, 6.8, k)
    if sh == "si":
        k = (t - DAY1) / (CIA[0] - DAY1)
        return 0.0, 0.05, lerp(8.6, 8.0, ease(k))
    if t < CIB[0] - 0.15:
        k = (t - CIA[0] + 0.18) / (CIB[0] - CIA[0])
        return 0.0, 0.35, lerp(8.5, 11.8, ease(k))
    k = min(1.0, (t - CIB[0] + 0.15) / (END - CIB[0]))
    return 0.0, 0.35, lerp(11.8, 10.6, ease(k))


def shade(body, n, V, t, ndl):
    mu = np.clip((n * V).sum(-1), 0, 1)
    if body["kind"] == "glow":
        c = lin(body["col"])
        return c * (body["k"] * (0.9 + 2.4 * mu ** 0.7))[..., None]
    if body["kind"] == "sun":
        c = lin(tuple(sun_col(t)))
        limb = 0.55 + 0.45 * mu ** 0.5
        return c * (5.0 * limb)[..., None]
    # Tierra
    diff = np.clip(ndl, 0, 1)
    soft = smooth(-0.15, 0.35, ndl) * 0.10
    light = (0.020 + 2.1 * diff + soft)[..., None] * LCOL
    loc = rot_y(rot_x(n, math.radians(12)), -2.0 + body["rot"] * t)
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.9) + 0.85 * cl * 0.9
    R = 2 * ndl[..., None] * n - LIGHT
    spec = np.clip((R * V).sum(-1), 0, 1) ** 90 * (1 - land) * (1 - cl[..., 0]) * 0.35
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85]) * LCOL
    # luces de ciudades en el lado de noche (todo funciona aunque sea de noche)
    night = smooth(0.05, -0.25, ndl) * land * (1 - cl[..., 0])
    city = (np.sin(lo * 90) * np.sin(la * 110) > 0.55) * night * 0.10
    col = col + city[..., None] * np.array([1.0, 0.75, 0.35])
    fres = (1 - mu) ** 2.6
    atm = np.array([0.22, 0.50, 1.0]) * (fres * 1.3 * np.clip(ndl + 0.35, 0, 1))[..., None]
    return col + atm
def draw_sphere(img, O, body, t):
    C = np.array(body["c"]); r = body["r"]
    rel = C - O
    dist_c = float(np.linalg.norm(rel))
    if dist_c <= r * 1.0001 or rel[2] >= 0:
        return
    depth = -rel[2]
    cxp = (rel[0] / depth / TX + 1) / 2 * W
    cyp = (1 - rel[1] / depth / TY) / 2 * H
    rpx = math.tan(math.asin(r / dist_c)) / PIX
    halo = 1.10 if body["kind"] in ("earth", "core") else 1.0
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
    if halo > 1.0:
        hz = (dist > r * 0.995) & (dist < r * halo)
        if hz.any():
            dd = (dist[hz] - r) / (0.03 * r)
            if body["kind"] == "earth":
                P = O + (-b[hz])[:, None] * d[hz]
                nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
                lit = np.clip(nn @ LIGHT + 0.4, 0, 1)
                gl = np.exp(-np.maximum(dd, 0)) * lit * 0.55
                region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([0.25, 0.52, 1.0])
            else:
                gl = np.exp(-np.maximum(dd, 0) * 0.6) * 0.30
                region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([0.15, 0.55, 1.0])
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

# ---------------- texto ----------------
FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); RED = (255, 84, 84)
GREEN = (120, 240, 140); PINK = (255, 115, 168)
INK = (8, 10, 20); PANEL = (12, 18, 38)


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
    """Etiqueta fija de la serie arriba: EL MÉTODO · PARTE 5/5."""
    if A <= 0:
        return
    s = "EL MÉTODO · PARTE 5/5"
    f = font("Inter-ExtraBold.otf", 34)
    tw = d.textlength(s, font=f)
    x0, x1 = W / 2 - tw / 2 - 26, W / 2 + tw / 2 + 26
    d.rounded_rectangle([x0, 252, x1, 304], 26, fill=(10, 16, 34, int(0.8 * A)), outline=CYAN + (A,), width=3)
    d.text((W / 2, 278), s, font=f, fill=CYAN + (A,), anchor="mm")


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


# ---------------- iconos dibujados ----------------
def laptop(d, cx, cy, s, col, A, on=True):
    w, h = 1.0 * s, 0.62 * s
    d.rounded_rectangle([cx - w / 2, cy - h, cx + w / 2, cy], int(0.06 * s), outline=col + (A,), width=max(3, int(s * 0.05)), fill=(6, 8, 16, A))
    d.polygon([(cx - 0.62 * s, cy + 0.02 * s), (cx + 0.62 * s, cy + 0.02 * s), (cx + 0.70 * s, cy + 0.12 * s), (cx - 0.70 * s, cy + 0.12 * s)], fill=col + (A,))
    # símbolo de encendido
    r = 0.16 * s; py = cy - h / 2
    d.arc([cx - r, py - r, cx + r, py + r], -60, 240, fill=col + (A,), width=max(3, int(s * 0.04)))
    d.line([(cx, py - r * 1.25), (cx, py - r * 0.1)], fill=col + (A,), width=max(3, int(s * 0.04)))


def cloud(d, cx, cy, s, col, A, fill=None):
    circles = [(-0.30, 0.05, 0.22), (-0.05, -0.12, 0.30), (0.25, 0.0, 0.24), (0.0, 0.10, 0.22)]
    f = fill if fill else (12, 18, 38)
    for dx, dy, r in circles:
        d.ellipse([cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s], fill=col + (A,))
    for dx, dy, r in circles:
        r2 = r - 0.045
        d.ellipse([cx + (dx - r2) * s, cy + (dy - r2) * s, cx + (dx + r2) * s, cy + (dy + r2) * s], fill=f + (A,))
    d.rectangle([cx - 0.30 * s, cy + 0.05 * s, cx + 0.25 * s, cy + 0.27 * s], fill=f + (A,))
    d.line([(cx - 0.30 * s, cy + 0.305 * s), (cx + 0.25 * s, cy + 0.305 * s)], fill=col + (A,), width=max(3, int(0.045 * s)))


def gear(d, cx, cy, r, col, A, ang=0.0, teeth=8):
    pts = []
    for i in range(teeth * 4):
        a = ang + i * 2 * math.pi / (teeth * 4)
        rr = r if (i % 4) in (0, 1) else r * 0.78
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=col + (A,))
    d.ellipse([cx - r * 0.34, cy - r * 0.34, cx + r * 0.34, cy + r * 0.34], fill=PANEL + (A,))


def link_icon(d, cx, cy, s, col, A):
    w = max(3, int(s * 0.12))
    d.rounded_rectangle([cx - 0.55 * s, cy - 0.22 * s, cx + 0.05 * s, cy + 0.22 * s], int(0.22 * s), outline=col + (A,), width=w)
    d.rounded_rectangle([cx - 0.05 * s, cy - 0.22 * s, cx + 0.55 * s, cy + 0.22 * s], int(0.22 * s), outline=col + (A,), width=w)


def wave(d, cx, cy, wdt, hgt, t, col, A, n=17, k=1.0):
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * wdt / n
        h = (6 + hgt * abs(math.sin(6.0 * t + i * 0.8)) * math.exp(-((i - (n - 1) / 2) / (n / 3.2)) ** 2)) * k
        d.rounded_rectangle([x - wdt / n * 0.3, cy - h, x + wdt / n * 0.3, cy + h], 5, fill=col + (A,))


def box(d, x0, y0, x1, y1, col, A, title=None, sub=None, tsize=46, ssize=32, fill=PANEL):
    d.rounded_rectangle([x0, y0, x1, y1], 26, fill=fill + (int(0.9 * A),), outline=col + (A,), width=4)
    cx = (x0 + x1) / 2
    if title and sub:
        d.text((cx, (y0 + y1) / 2 - ssize * 0.55), title, font=font("Inter-Black.otf", tsize), fill=WHITE + (A,), anchor="mm")
        d.text((cx, (y0 + y1) / 2 + tsize * 0.62), sub, font=font("Inter-ExtraBold.otf", ssize), fill=col + (A,), anchor="mm")
    elif title:
        d.text((cx, (y0 + y1) / 2), title, font=font("Inter-Black.otf", tsize), fill=WHITE + (A,), anchor="mm")


def arrow(d, x0, y0, x1, y1, col, A, k=1.0, w=6):
    if k <= 0:
        return
    xe, ye = lerp(x0, x1, k), lerp(y0, y1, k)
    d.line([(x0, y0), (xe, ye)], fill=col + (A,), width=w)
    ang = math.atan2(ye - y0, xe - x0)
    s = 22
    d.polygon([(xe, ye), (xe - s * math.cos(ang - 0.5), ye - s * math.sin(ang - 0.5)), (xe - s * math.cos(ang + 0.5), ye - s * math.sin(ang + 0.5))], fill=col + (A,))


def packet(d, x0, y0, x1, y1, t, t0, dur, col, A):
    k = (t - t0) / dur
    if 0 <= k <= 1:
        x, y = lerp(x0, x1, ease(k)), lerp(y0, y1, ease(k))
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=col + (A,), outline=WHITE + (A,), width=3)


def mono(size):
    return font("Inter-ExtraBold.otf", size)


# ---------------- gráficos de esta parte ----------------
def rgb(c):
    return tuple(int(255 * x) for x in c)


def check(d, cx, cy, s, col, A, w=None):
    w = w or max(4, int(s * 0.16))
    d.line([(cx - 0.45 * s, cy), (cx - 0.12 * s, cy + 0.32 * s), (cx + 0.5 * s, cy - 0.38 * s)], fill=col + (A,), width=w, joint="curve")


def clock(d, cx, cy, r, col, A, ang):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PANEL + (A,), outline=col + (A,), width=max(3, int(r * 0.12)))
    d.line([(cx, cy), (cx + 0.5 * r * math.sin(ang / 12), cy - 0.5 * r * math.cos(ang / 12))], fill=WHITE + (A,), width=max(3, int(r * 0.1)))
    d.line([(cx, cy), (cx + 0.78 * r * math.sin(ang), cy - 0.78 * r * math.cos(ang))], fill=col + (A,), width=max(2, int(r * 0.07)))


def draw_hook(layer, t):
    al = fade(t, 0.0, MT0 - 0.18, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out(t / 0.45)
    a1 = int(A * k)
    # reloj digital con la hora de la serie
    txt(d, (W / 2, 390), "22:00", 120, WHITE, a1)
    # botón PUBLICAR que se aprieta solo (sin cursor ni dedo)
    p = ease_out((t - PRESS_T) / 0.12) * (1 - ease_out((t - PRESS_T - 0.12) / 0.25))
    s = 1 - 0.08 * p
    on = t > PRESS_T
    bw, bh = 520 * s, 130 * s
    cx, cy = W / 2, 560
    col = GREEN if on else YELLOW
    if on:
        g = max(0.0, 1 - (t - PRESS_T) / 0.6)
        if g > 0:
            rr = 30 + 160 * (1 - g)
            d.rounded_rectangle([cx - bw / 2 - rr, cy - bh / 2 - rr * 0.5, cx + bw / 2 + rr, cy + bh / 2 + rr * 0.5], 90,
                                outline=GREEN + (int(a1 * g),), width=6)
    d.rounded_rectangle([cx - bw / 2, cy - bh / 2 + 10 * p, cx + bw / 2, cy + bh / 2 + 10 * p], 65, fill=col + (a1,), outline=INK + (a1,), width=6)
    label = "PUBLICADO" if on else "PUBLICAR"
    d.text((cx + (28 if on else 0), cy + 10 * p), label, font=font("Inter-Black.otf", int(64 * s)), fill=INK + (a1,), anchor="mm")
    if on:
        check(d, cx - 190 * s, cy + 10 * p, 52, INK, a1, 11)
    ks = ease_out((t - PRESS_T - 0.5) / 0.35)
    if ks > 0:
        txt(d, (W / 2, 700), "¡SALIÓ SOLO!", 76, YELLOW, int(A * ks))


def draw_metricool(layer, t, O):
    al = fade(t, MT0 - 0.18, DAY0, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - MT0 + 0.05) / 0.35)
    Ak = int(A * k)
    d.rounded_rectangle([230, 350, W - 230, 470], 34, fill=PANEL + (int(0.9 * Ak),), outline=GREEN + (Ak,), width=4)
    # calendario
    cx0, cy0 = 300, 410
    d.rounded_rectangle([cx0 - 34, cy0 - 30, cx0 + 34, cy0 + 34], 8, outline=GREEN + (Ak,), width=5)
    d.rectangle([cx0 - 34, cy0 - 30, cx0 + 34, cy0 - 14], fill=GREEN + (Ak,))
    for gx in range(3):
        for gy in range(2):
            d.rectangle([cx0 - 22 + gx * 17, cy0 - 4 + gy * 17, cx0 - 12 + gx * 17, cy0 + 6 + gy * 17], fill=WHITE + (Ak,))
    d.text((W / 2 + 40, 410), "METRICOOL", font=font("Inter-Black.otf", 66), fill=WHITE + (Ak,), anchor="mm")
    ks = ease_out((t - MT0 - 0.6) / 0.3)
    clock(d, W / 2 - 230, 540, 34, YELLOW, int(A * ks), 2.5 * (t - MT0))
    d.text((W / 2 - 180, 540), "a la hora programada", font=font("Inter-ExtraBold.otf", 44), fill=YELLOW + (int(A * ks),), anchor="lm",
           stroke_width=5, stroke_fill=INK + (int(A * ks),))
    # líneas del nodo de Metricool a las redes y etiquetas
    mc = project((0.0, 1.42, 0.25), O)
    for i, (nm, col) in enumerate(NETS):
        kk = ease_out((t - (MT0 + 1.4 + 0.45 * i)) / 0.35)
        if kk <= 0:
            continue
        p = project(net_pos(i, t), O)
        c = rgb(col)
        d.line([(mc[0], mc[1]), (lerp(mc[0], p[0], kk), lerp(mc[1], p[1], kk))], fill=c + (int(A * 0.7),), width=5)
        hw = d.textlength(nm, font=font("Inter-Black.otf", 40)) / 2 + 12
        txt(d, (min(max(p[0], hw), W - hw), p[1] - 62), nm, 40, c, int(A * kk), stroke=6)
        # paquete que viaja
        kp = (t - (MT0 + 1.6 + 0.45 * i)) / 0.6
        if 0 <= kp <= 1:
            x, y = lerp(mc[0], p[0], ease(kp)), lerp(mc[1], p[1], ease(kp))
            d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=c + (A,), outline=WHITE + (A,), width=3)


SLOTS = [("MAÑANA", MA0), ("LUEGO", VI0), ("TARDE", TR0)]


def draw_tareas(layer, t):
    al = fade(t, TA0 - 0.18, MA0 - 0.05, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - TA0 + 0.1) / 0.35)
    txt(d, (W / 2, 420), "3", 210, YELLOW, int(A * k))
    txt(d, (W / 2, 560), "TAREAS DE CLAUDE", 74, WHITE, int(A * k))
    for i in range(3):
        kk = ease_out((t - (TA0 + 0.8 + 0.35 * i)) / 0.3)
        if kk <= 0:
            continue
        x = W / 2 + (i - 1) * 190
        clock(d, x, 680, 46, CYAN, int(A * kk), 3 * t + i * 2)
    ks = ease_out((t - TA0 - 1.9) / 0.3)
    txt(d, (W / 2, 780), "programadas cada día", 46, CYAN, int(A * ks), "Inter-ExtraBold.otf", 6)


def draw_timeline(d, t, A):
    """Barra con las tres tareas del día; la activa se ilumina."""
    y = 372
    xs_ = [W / 2 - 300, W / 2, W / 2 + 300]
    d.line([(xs_[0], y), (xs_[2], y)], fill=CYAN + (int(A * 0.5),), width=5)
    cur = 0
    for i, (lab, t0) in enumerate(SLOTS):
        if t >= t0 - 0.2:
            cur = i
    for i, (lab, t0) in enumerate(SLOTS):
        act = i == cur
        done = i < cur
        col = YELLOW if act else (GREEN if done else (120, 130, 150))
        r = 24 if act else 17
        d.ellipse([xs_[i] - r, y - r, xs_[i] + r, y + r], fill=col + (A,), outline=INK + (A,), width=4)
        if done:
            check(d, xs_[i], y, 18, INK, A, 5)
        d.text((xs_[i], y + 52), lab, font=font("Inter-Black.otf", 40 if act else 34), fill=(col if act else WHITE) + (A,), anchor="mm",
               stroke_width=5, stroke_fill=INK + (A,))


def bulb(d, cx, cy, s, col, A):
    d.ellipse([cx - 0.45 * s, cy - 0.6 * s, cx + 0.45 * s, cy + 0.3 * s], fill=col + (A,))
    d.rectangle([cx - 0.22 * s, cy + 0.22 * s, cx + 0.22 * s, cy + 0.5 * s], fill=(200, 205, 220, A))
    d.line([(cx - 0.22 * s, cy + 0.36 * s), (cx + 0.22 * s, cy + 0.36 * s)], fill=INK + (A,), width=3)


def draw_day(layer, t, O):
    al = fade(t, MA0 - 0.15, DAY1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    draw_timeline(d, t, A)
    x0, x1, y0, y1 = 150, W - 150, 470, 720
    # tarjeta de la mañana: reporte
    am = fade(t, MA0 - 0.1, VI0 - 0.1, 0.2)
    if am > 0:
        a = int(A * am)
        d.rounded_rectangle([x0, y0, x1, y1], 30, fill=PANEL + (int(0.9 * a),), outline=YELLOW + (a,), width=4)
        d.text((x0 + 40, y0 + 52), "REPORTE", font=font("Inter-Black.otf", 54), fill=WHITE + (a,), anchor="lm")
        d.text((x0 + 40, y0 + 108), "estadísticas", font=font("Inter-ExtraBold.otf", 36), fill=CYAN + (a,), anchor="lm")
        hs = [0.45, 0.7, 0.55, 0.9, 0.75]
        for i, h in enumerate(hs):
            kb = ease_out((t - (MA0 + 0.5 + 0.18 * i)) / 0.35)
            bx = x0 + 50 + i * 62
            bh = 90 * h * kb
            d.rectangle([bx, y1 - 30 - bh, bx + 40, y1 - 30], fill=(CYAN if i != 3 else YELLOW) + (a,))
        ki = ease_out((t - (MA0 + 2.6)) / 0.35)
        if ki > 0:
            ai = int(a * ki)
            for j in range(3):
                bulb(d, x1 - 300 + j * 90, y0 + 150, 60, YELLOW, ai)
            d.text((x1 - 210, y1 - 50), "IDEAS VIRALES", font=font("Inter-Black.otf", 40), fill=YELLOW + (ai,), anchor="mm")
    # tarjeta de "luego": el video del día
    vd = fade(t, VI0 - 0.1, TR0 - 0.1, 0.2)
    if vd > 0:
        a = int(A * vd)
        d.rounded_rectangle([x0, y0, x1, y1], 30, fill=PANEL + (int(0.9 * a),), outline=CYAN + (a,), width=4)
        d.polygon([(x0 + 44, y0 + 30), (x0 + 44, y0 + 86), (x0 + 92, y0 + 58)], fill=YELLOW + (a,))
        d.text((x0 + 120, y0 + 58), "VIDEO DEL DÍA", font=font("Inter-Black.otf", 54), fill=WHITE + (a,), anchor="lm")
        steps = ["GUION", "VOZ", "3D", "ENLACE"]
        cols = [WHITE, CYAN, YELLOW, GREEN]
        sw = (x1 - x0 - 80) / 4
        for i, s in enumerate(steps):
            ks = ease_out((t - (VI0 + 1.3 + 0.55 * i)) / 0.3)
            cx = x0 + 40 + sw * (i + 0.5)
            cy = y0 + 175
            on = int(a * (0.25 + 0.75 * ks))
            d.rounded_rectangle([cx - sw / 2 + 8, cy - 46, cx + sw / 2 - 8, cy + 46], 23, fill=PANEL + (a,), outline=cols[i] + (on,), width=4)
            d.text((cx, cy), s, font=font("Inter-Black.otf", 32), fill=cols[i] + (on,), anchor="mm")
            if i > 0 and ks > 0:
                d.line([(cx - sw / 2 - 8, cy), (cx - sw / 2 + 8, cy)], fill=cols[i] + (on,), width=6)
    # tarjeta de la tarde: verificación
    tr = fade(t, TR0 - 0.1, DAY1, 0.2)
    if tr > 0:
        a = int(A * tr)
        d.rounded_rectangle([x0, y0, x1, y1], 30, fill=PANEL + (int(0.9 * a),), outline=GREEN + (a,), width=4)
        d.text((W / 2, y0 + 58), "VERIFICACIÓN", font=font("Inter-Black.otf", 54), fill=WHITE + (a,), anchor="mm")
        for i, (nm, col) in enumerate(NETS):
            kk = ease_out((t - (TR0 + 0.5 + 0.4 * i)) / 0.3)
            cy = y0 + 125 + i * 40
            c = rgb(col)
            d.text((W / 2 - 40, cy), nm, font=font("Inter-Black.otf", 34), fill=c + (a,), anchor="rm")
            if kk > 0:
                check(d, W / 2 + 30, cy, 30 * kk + 1, GREEN, a, 7)
                d.text((W / 2 + 80, cy), "salió", font=font("Inter-ExtraBold.otf", 30), fill=GREEN + (int(a * kk),), anchor="lm")


def phone(d, cx, cy, s, col, A):
    w, h = 0.56 * s, 1.0 * s
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], int(0.09 * s), fill=(6, 8, 16, A), outline=col + (A,), width=max(4, int(s * 0.025)))
    d.rounded_rectangle([cx - 0.07 * s, cy - h / 2 + 0.035 * s, cx + 0.07 * s, cy - h / 2 + 0.06 * s], 6, fill=col + (A,))


def draw_si(layer, t, O):
    al = fade(t, SI0 - 0.18, CIA[0] - 0.18, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - SI0 + 0.1) / 0.35)
    a1 = int(A * k)
    pcx, pcy, ps = W / 2, 880, 420
    phone(d, pcx, pcy + 30 * (1 - k), ps, WHITE, a1)
    txt(d, (W / 2, 385), "NOSOTROS SOLO DAMOS", 60, WHITE, a1)
    txt(d, (W / 2, 485), "EL SÍ", 110, YELLOW, a1)
    # botón SÍ dentro del celular
    pt = SI0 + 0.9
    p = ease_out((t - pt) / 0.1) * (1 - ease_out((t - pt - 0.1) / 0.25))
    on = t > pt
    r = 85 * (1 - 0.08 * p)
    by = pcy + 40
    if on:
        g = max(0.0, 1 - (t - pt) / 0.7)
        if g > 0:
            rr = r + 120 * (1 - g)
            d.ellipse([pcx - rr, by - rr, pcx + rr, by + rr], outline=GREEN + (int(a1 * g),), width=6)
    d.ellipse([pcx - r, by - r, pcx + r, by + r], fill=(GREEN if on else YELLOW) + (a1,), outline=INK + (a1,), width=6)
    d.text((pcx, by), "SÍ", font=font("Inter-Black.otf", int(80 * r / 85)), fill=INK + (a1,), anchor="mm")
    # aviso al celular si algo falla
    kf = ease_out((t - FAIL_T) / 0.35)
    if kf > 0:
        af = int(A * kf)
        y = lerp(560, 640, kf)
        bw = 500
        d.rounded_rectangle([pcx - bw / 2, y - 62, pcx + bw / 2, y + 62], 26, fill=(40, 14, 18, int(0.95 * af)), outline=RED + (af,), width=4)
        d.polygon([(pcx - bw / 2 + 60, y - 32), (pcx - bw / 2 + 24, y + 32), (pcx - bw / 2 + 96, y + 32)], fill=YELLOW + (af,))
        d.text((pcx - bw / 2 + 60, y + 12), "!", font=font("Inter-Black.otf", 40), fill=INK + (af,), anchor="mm")
        d.text((pcx - bw / 2 + 125, y - 18), "AVISO", font=font("Inter-Black.otf", 42), fill=WHITE + (af,), anchor="lm")
        d.text((pcx - bw / 2 + 125, y + 26), "algo falló", font=font("Inter-ExtraBold.otf", 34), fill=RED + (af,), anchor="lm")


def draw_const(layer, t, O):
    al = fade(t, CIA[0] - 0.18, CARD + 0.1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    pts = [project(const_pos(i, t), O) for i in range(len(CONST))]
    ec = project((0.0, 0.0, 0.0), O)
    ons = [const_on(i, t) for i in range(len(CONST))]
    # líneas: cada nodo con la Tierra y con el siguiente
    for i in range(len(CONST)):
        if ons[i] <= 0:
            continue
        c = rgb(CONST[i][1])
        d.line([(pts[i][0], pts[i][1]), (ec[0], ec[1])], fill=c + (int(A * 0.35 * ons[i]),), width=3)
        j = (i + 1) % len(CONST)
        if ons[j] > 0 and (j != 0 or ons[-1] >= 1):
            d.line([(pts[i][0], pts[i][1]), (lerp(pts[i][0], pts[j][0], ons[j]), lerp(pts[i][1], pts[j][1], ons[j]))], fill=YELLOW + (int(A * 0.75),), width=4)
    for i, (nm, col) in enumerate(CONST):
        if ons[i] <= 0:
            continue
        p = pts[i]
        dy = -48 if p[1] < ec[1] else 50
        f = font("Inter-Black.otf", 32)
        hw = d.textlength(nm, font=f) / 2 + 12
        txt(d, (min(max(p[0], hw), W - hw), p[1] + dy), nm, 32, rgb(col), int(A * ons[i]), stroke=5)


def draw_cierre(layer, t, O):
    al = fade(t, CIA[0] - 0.18, CIB[0] - 0.15, 0.22)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - CIA[0] + 0.1) / 0.35)
    txt(d, (W / 2, 390), "EL MÉTODO", 104, WHITE, int(A * k))
    txt(d, (W / 2, 495), "COMPLETO", 96, YELLOW, int(A * k))
    k1 = ease_out((t - CIA[0] - 1.4) / 0.3)
    k2 = ease_out((t - CIA[0] - 2.5) / 0.3)
    y = 620
    if k1 > 0:
        a = int(A * k1)
        d.rounded_rectangle([90, y - 40, 470, y + 40], 40, fill=PANEL + (int(0.9 * a),), outline=CYAN + (a,), width=4)
        d.text((280, y), "PRIMER MENSAJE", font=font("Inter-Black.otf", 36), fill=CYAN + (a,), anchor="mm")
    if k2 > 0:
        a = int(A * k2)
        arrow(d, 480, y, 560, y, YELLOW, a, k2, 7)
        d.rounded_rectangle([570, y - 40, W - 70, y + 40], 40, fill=PANEL + (int(0.9 * a),), outline=YELLOW + (a,), width=4)
        d.text(((570 + W - 70) / 2, y), "FUNCIONA SOLO", font=font("Inter-Black.otf", 36), fill=YELLOW + (a,), anchor="mm")


def draw_gracias(layer, t):
    al = fade(t, CIB[0] - 0.15, CARD + 0.1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - CIB[0] + 0.1) / 0.35)
    txt(d, (W / 2, 420 + 20 * (1 - k)), "¡GRACIAS!", 140, YELLOW, int(A * k))
    txt(d, (W / 2, 545), "FIN DE LA SERIE", 64, WHITE, int(A * k))
    for i in range(5):
        kk = ease_out((t - (CIB[0] + 0.2 + 0.12 * i)) / 0.25)
        x = W / 2 + (i - 2) * 90
        r = 24
        d.ellipse([x - r, 640 - r, x + r, 640 + r], fill=YELLOW + (int(A * kk),), outline=INK + (int(A * kk),), width=4)
        d.text((x, 640), str(i + 1), font=font("Inter-Black.otf", 28), fill=INK + (int(A * kk),), anchor="mm")


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
    txt(d, (W / 2, 1100), "Síguenos para más", 50, CYAN, A, "Inter-ExtraBold.otf", 6)
    txt(d, (W / 2, 1165), "ciencia y tecnología", 50, CYAN, A, "Inter-ExtraBold.otf", 6)


def overlays(frame_u8, t, O):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_hook(layer, t)
    draw_metricool(layer, t, O)
    draw_tareas(layer, t)
    draw_day(layer, t, O)
    draw_si(layer, t, O)
    draw_const(layer, t, O)
    draw_cierre(layer, t, O)
    draw_gracias(layer, t)
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
    set_light(t)
    cx, cy, D = camera(t)
    O = np.array([cx, cy, D])
    img = BG.copy()
    bs = bodies(t)
    bs.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"]) - O)))
    for b in bs:
        draw_sphere(img, O, b, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
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
        print("frames", NFRAMES, "end", END, "card", CARD)
