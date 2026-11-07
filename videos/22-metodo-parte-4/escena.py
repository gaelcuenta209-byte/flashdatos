"""Flash Datos · video 22 · Serie "El método", parte 4: GitHub, el cerebro del canal.

Un núcleo 3D con circuitos de luz (el repositorio) al centro. Los archivos del canal
(manual, guiones, historial e ideas) entran en órbita como nodos; la cámara sube a la nube
sobre la Tierra con la computadora apagada; aparecen las dos acciones automáticas (voz y
medios) como nodos que se encienden; la tubería ElevenLabs → voz.yml → narración, la del
video → medios.yml → enlace público, y ese enlace llega a Metricool y a las tres redes.
Cierre con la cadena de pasos unida y el avance de la parte 5.

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


# ---------------- fondo: estrellas y nebulosa índigo-magenta (distinta a las partes 1-3) ----------------
def make_background():
    rng = np.random.default_rng(22)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1900
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.025 + 0.45 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.82 + 0.18 * tint, 0.86 + 0.05 * tint, 1.0 - 0.22 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 46
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 34.0
    neb = fbm(gx, gy, np.full_like(gx, 2.7), 5, seed=2222)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.44) * 2.4, 0, 1) ** 1.5
    yy = np.linspace(0, 1, H)[:, None]
    bg += neb[..., None] * (np.array([0.030, 0.012, 0.055], np.float32) * (1 - yy[..., None]) + np.array([0.010, 0.018, 0.055], np.float32) * yy[..., None])
    return bg


BG = make_background()

# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
HK0, HK1 = SEG["hook"]["t0"], SEG["hook"]["t1"]
RE0, RE1 = SEG["repo"]["t0"], SEG["repo"]["t1"]
NU0, NU1 = SEG["nube"]["t0"], SEG["nube"]["t1"]
AC0, AC1 = SEG["acciones"]["t0"], SEG["acciones"]["t1"]
VO0, VO1 = SEG["voz"]["t0"], SEG["voz"]["t1"]
ME0, ME1 = SEG["medios"]["t0"], SEG["medios"]["t1"]
MT0, MT1 = SEG["metricool"]["t0"], SEG["metricool"]["t1"]
CI0, CI1 = SEG["cierre"]["t0"], SEG["cierre"]["t1"]
CIA = SEG["cierre"]["parts"][0]
CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
END = TM["end"]
NFRAMES = int(round(END * FPS))
GH_T = HK0 + 2.45          # "vive en GitHub" (después de la pausa de "computadora:")
FL = [NU0 - 0.18, AC0 - 0.18, CIA[0] - 0.18, CIB[0] - 0.15, CARD - 0.05]

# momentos de cada archivo (pausas reales de la voz: "todo:" 5.6 s, "tareas," 7.9 s)
FILE_T = [RE0 + 1.75, RE0 + 4.0, RE0 + 5.25, RE0 + 7.35]
FILES = ["MANUAL", "GUIONES", "HISTORIAL", "IDEAS"]
FILE_N = ["MANUAL.md", "script.json", "historial.json", "ideas.json"]
FILE_COLS = [(1.0, 0.82, 0.25), (0.30, 0.85, 1.0), (1.0, 0.45, 0.66), (0.55, 1.0, 0.45)]


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


# ---------------- cuerpos ----------------
R_ORB = 1.42
TILT = math.radians(20)


def file_pos(i, t):
    a = 0.38 * t + i * math.pi / 2 + 0.6
    x, z = R_ORB * math.cos(a), R_ORB * math.sin(a)
    y = -z * math.sin(TILT); z = z * math.cos(TILT)
    return (x, y + 0.05 * math.sin(1.1 * t + i), z)


ACT_COLS = [(1.0, 0.80, 0.22), (0.30, 0.85, 1.0)]


def act_pos(i, t):
    s = -1 if i == 0 else 1
    return (s * 1.85, 0.25 + 0.06 * math.sin(1.4 * t + i), 0.2)


def shot(t):
    if t < NU0 - 0.18:
        return "core"
    if t < AC0 - 0.18:
        return "nube"
    return "core"


def bodies(t):
    sh = shot(t)
    if sh == "nube":
        a = 0.25 * (t - NU0)
        return [dict(n="earth", c=(0.0, -3.05, -0.6), r=2.55, kind="earth", rot=0.03),
                dict(n="core", c=(0.36 + 0.06 * math.sin(a), -0.16 + 0.03 * math.sin(2 * a), -0.3 + 0.12 * math.cos(a)), r=0.21, kind="core")]
    out = [dict(n="core", c=(0.0, 0.0, 0.0), r=1.0, kind="core")]
    if t > FILE_T[0] - 0.3:
        for i, col in enumerate(FILE_COLS):
            k = ease_out((t - FILE_T[i] + 0.1) / 0.45)
            if t < AC0 - 0.18 and k <= 0:
                continue
            if t >= AC0 - 0.18:
                k = 1.0
            pulse = 1.0 + 0.25 * math.sin(4 * t + 1.7 * i)
            out.append(dict(n=f"f{i}", c=file_pos(i, t), r=0.09 * k + 1e-3, kind="glow", col=col, k=pulse))
    if t > AC0 + 0.3 and t < CIB[0] - 0.15:
        for i, col in enumerate(ACT_COLS):
            on = ease_out((t - (AC0 + 0.6 + 0.9 * i)) / 0.4)
            if on <= 0:
                continue
            hot = 1.0
            if VO0 - 0.2 < t < VO1 + 0.2 and i == 0:
                hot = 1.6 + 0.4 * math.sin(12 * t)
            if ME0 - 0.2 < t < ME1 + 0.2 and i == 1:
                hot = 1.6 + 0.4 * math.sin(12 * t)
            out.append(dict(n=f"a{i}", c=act_pos(i, t), r=0.20 * on + 1e-3, kind="glow", col=col, k=hot))
    return out


def camera(t):
    """(x, y, distancia) de la cámara. y > 0 baja el núcleo en pantalla."""
    if t < NU0 - 0.18:
        if t < 3.0:
            D = math.exp(lerp(math.log(16.0), math.log(6.2), ease_out(t / 3.0)))
        elif t < RE0:
            D = lerp(6.2, 6.0, (t - 3.0) / (RE0 - 3.0))
        else:
            D = lerp(6.0, 7.2, ease((t - RE0) / (NU0 - RE0)))
        return 0.0, 0.55, D
    if t < AC0 - 0.18:
        k = (t - NU0 + 0.18) / (AC0 - NU0)
        return 0.0, 0.05 - 0.15 * k, lerp(4.9, 4.4, ease(k))
    if t < VO0 - 0.3:
        return 0.0, 0.62, lerp(8.6, 8.0, (t - AC0) / (VO0 - AC0))
    if t < ME0 - 0.3:
        k = ease((t - VO0 + 0.3) / 0.9)
        return lerp(0.0, -0.95, k), 0.62, lerp(8.0, 7.0, k)
    if t < MT0 - 0.3:
        k = ease((t - ME0 + 0.3) / 1.0)
        return lerp(-0.95, 0.95, k), 0.62, 7.0
    if t < CIA[0] - 0.18:
        k = ease((t - MT0 + 0.3) / 1.4)
        return lerp(0.95, 0.0, k), 0.62, lerp(7.0, 9.0, k)
    if t < CIB[0] - 0.15:
        return 0.0, 0.62, lerp(8.2, 7.4, (t - CIA[0]) / (CIB[0] - CIA[0]))
    return 0.0, 0.55, lerp(6.6, 6.0, min(1.0, (t - CIB[0]) / (END - CIB[0])))


def circuit(la, lo, t):
    """Circuitos de luz del núcleo: celdas con pistas horizontales/verticales y pulsos que viajan."""
    NU, NV = 22, 14
    u = (lo + np.pi) / (2 * np.pi) * NU
    v = (la + np.pi / 2) / np.pi * NV
    ci = np.floor(u).astype(np.int64); cj = np.floor(v).astype(np.int64)
    fu = u - ci; fv = v - cj
    h = (ci * 73856093) ^ (cj * 19349663)
    h = (h ^ (h >> 7)) & 1023
    wline = 0.055
    horiz = ((h & 3) != 0) * np.exp(-((fv - 0.5) / wline) ** 2)
    vert = ((h & 12) == 4) * np.exp(-((fu - 0.5) / wline) ** 2) * (fv > 0.5)
    vert2 = ((h & 48) == 16) * np.exp(-((fu - 0.5) / wline) ** 2) * (fv < 0.5)
    pad = ((h & 64) != 0) * np.exp(-(((fu - 0.5) ** 2 + (fv - 0.5) ** 2) / 0.012))
    lines = np.clip(horiz + vert + vert2, 0, 1)
    pulse = 0.5 + 0.5 * np.sin(u * 1.7 - 5.0 * t + (h % 17))
    pulse = pulse ** 6
    yel = (h % 5 == 0)
    return lines, pad, pulse, yel


def shade(body, n, V, t, ndl):
    if body["kind"] == "glow":
        mu = np.clip((n * V).sum(-1), 0, 1)
        c = lin(body["col"])
        return c * (body["k"] * (0.9 + 2.4 * mu ** 0.7))[..., None]
    mu = np.clip((n * V).sum(-1), 0, 1)
    if body["kind"] == "core":
        diff = np.clip(ndl, 0, 1)
        loc = rot_y(rot_x(n, math.radians(14)), 0.22 * t)
        la, lo = latlon(loc)
        lines, pad, pulse, yel = circuit(la, lo, t)
        base = np.array([0.010, 0.016, 0.040]) * (0.35 + 1.8 * diff)[..., None]
        cy = lin((0.31, 0.85, 1.0)); yl = lin((1.0, 0.85, 0.30))
        tint = np.where(yel[..., None], yl, cy)
        glow = (lines * (0.35 + 2.6 * pulse) + pad * 1.6)[..., None] * tint
        spec = np.clip(((2 * ndl[..., None] * n - LIGHT) * V).sum(-1), 0, 1) ** 40 * 0.35
        fres = (1 - mu) ** 2.4
        rim = np.array([0.20, 0.55, 1.0]) * (fres * 1.1)[..., None]
        return base + glow * 0.9 + spec[..., None] + rim
    # Tierra
    diff = np.clip(ndl, 0, 1)
    soft = smooth(-0.15, 0.35, ndl) * 0.10
    light = (0.020 + 2.1 * diff + soft)[..., None]
    loc = rot_y(rot_x(n, math.radians(12)), -2.3 + body["rot"] * t)
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.9) + 0.85 * cl * 0.9
    R = 2 * ndl[..., None] * n - LIGHT
    spec = np.clip((R * V).sum(-1), 0, 1) ** 90 * (1 - land) * (1 - cl[..., 0]) * 0.35
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85])
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
    """Etiqueta fija de la serie arriba: EL MÉTODO · PARTE 4/5."""
    if A <= 0:
        return
    s = "EL MÉTODO · PARTE 4/5"
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
def draw_hook(layer, t):
    al = fade(t, 0.0, RE0 - 0.05, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out(t / 0.5)
    a1 = int(A * k * (1 - 0.55 * ease_out((t - GH_T) / 0.3)))
    laptop(d, W / 2, 520, 230, WHITE, a1)
    # tachado en rojo
    kx = ease_out((t - 1.45) / 0.3)
    if kx > 0:
        d.line([(W / 2 - 170, 300), (W / 2 - 170 + 340 * kx, 300 + 300 * kx)], fill=RED + (a1,), width=20)
    txt(d, (W / 2, 640), "NO VIVE EN UNA COMPUTADORA", 58, WHITE, a1)
    kg = ease_out((t - GH_T) / 0.35)
    if kg > 0:
        a2 = int(A * kg)
        d.rectangle([0, 340, W, 700], fill=(4, 6, 12, int(0.55 * a2)))
        txt(d, (W / 2, 430 + 20 * (1 - kg)), "VIVE EN", 84, WHITE, a2)
        txt(d, (W / 2, 545 + 20 * (1 - kg)), "GITHUB", 150, YELLOW, a2)
        sub = int(A * min(1.0, max(0.0, (t - GH_T - 0.6) / 0.3)))
        txt(d, (W / 2, 660), "el CEREBRO del canal", 56, CYAN, sub, "Inter-ExtraBold.otf", 7)


def draw_repo(layer, t, O):
    al = fade(t, RE0 - 0.05, NU0 - 0.18, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    # panel tipo explorador de archivos
    x0, x1, y0 = 120, W - 120, 350
    rows = sum(1 for ft in FILE_T if t > ft - 0.1)
    y1 = y0 + 112 + 76 * 4
    k = ease_out((t - RE0) / 0.35)
    Ap = int(A * k)
    d.rounded_rectangle([x0, y0, x1, y1], 30, fill=PANEL + (int(0.86 * Ap),), outline=CYAN + (Ap,), width=4)
    # carpeta
    fx, fy = x0 + 50, y0 + 56
    d.polygon([(fx, fy - 20), (fx + 22, fy - 20), (fx + 30, fy - 12), (fx + 58, fy - 12), (fx + 58, fy + 22), (fx, fy + 22)], fill=YELLOW + (Ap,))
    d.text((fx + 80, fy), "REPOSITORIO", font=font("Inter-Black.otf", 46), fill=WHITE + (Ap,), anchor="lm")
    d.line([(x0 + 30, y0 + 104), (x1 - 30, y0 + 104)], fill=CYAN + (int(Ap * 0.5),), width=2)
    y = y0 + 150
    for i in range(4):
        kr = ease_out((t - FILE_T[i] + 0.05) / 0.3)
        if kr > 0:
            ar = int(Ap * kr)
            xx = x0 + 60 - 40 * (1 - kr)
            col = tuple(int(255 * c) for c in FILE_COLS[i])
            d.ellipse([xx - 16, y - 16, xx + 16, y + 16], fill=col + (ar,))
            d.text((xx + 40, y), FILES[i], font=font("Inter-Black.otf", 50), fill=WHITE + (ar,), anchor="lm", stroke_width=5, stroke_fill=INK + (ar,))
            d.text((x1 - 40, y), FILE_N[i], font=mono(34), fill=col + (ar,), anchor="rm")
        y += 76
    # líneas de los nodos al núcleo y etiqueta en cada nodo
    cx, cy, _ = project((0.0, 0.0, 0.0), O)
    for i in range(4):
        kr = ease_out((t - FILE_T[i]) / 0.4)
        if kr <= 0:
            continue
        p = project(file_pos(i, t), O)
        col = tuple(int(255 * c) for c in FILE_COLS[i])
        d.line([(p[0], p[1]), (lerp(p[0], cx, 0.55), lerp(p[1], cy, 0.55))], fill=col + (int(110 * kr * al),), width=4)


def draw_nube(layer, t, O):
    al = fade(t, NU0 - 0.18, AC0 - 0.18, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - NU0 + 0.1) / 0.4)
    cloud(d, W / 2, 440 + 20 * (1 - k), 300, CYAN, int(A * k))
    txt(d, (W / 2, 470), "EN LA NUBE", 64, WHITE, int(A * k))
    # computadora apagada
    k2 = ease_out((t - (NU0 + 1.9)) / 0.35)
    if k2 > 0:
        a2 = int(A * k2)
        laptop(d, W / 2 - 170, 760, 150, (130, 140, 160), a2)
        txt(d, (W / 2 + 90, 700), "COMPUTADORA", 50, WHITE, a2, stroke=6)
        txt(d, (W / 2 + 90, 765), "APAGADA", 60, YELLOW, a2, stroke=6)
    # etiqueta del núcleo en órbita
    b = [x for x in bodies(t) if x["n"] == "core"][0]
    p = project(b["c"], O)
    r = 0.21 / p[2] / PIX
    txt(d, (p[0], p[1] - r - 40), "GITHUB", 44, YELLOW, A, stroke=6)


def draw_acciones(layer, t, O):
    al = fade(t, AC0 - 0.18, VO0 - 0.1, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - AC0 + 0.1) / 0.4)
    gear(d, W / 2 - 230, 470, 70, YELLOW, int(A * k), 1.4 * t)
    gear(d, W / 2 - 128, 545, 46, CYAN, int(A * k), -2.1 * t + 0.2)
    txt(d, (W / 2 + 110, 440), "2", 190, YELLOW, int(A * k))
    txt(d, (W / 2, 640), "ACCIONES AUTOMÁTICAS", 70, WHITE, int(A * k))
    sub = int(A * min(1.0, max(0.0, (t - AC0 - 1.2) / 0.3)))
    txt(d, (W / 2, 720), "se activan solas con cada cambio", 44, CYAN, sub, "Inter-ExtraBold.otf", 6)
    # etiquetas sobre los nodos de acción
    for i, lab in enumerate(["VOZ", "MEDIOS"]):
        on = ease_out((t - (AC0 + 0.6 + 0.9 * i)) / 0.4)
        if on <= 0:
            continue
        p = project(act_pos(i, t), O)
        col = tuple(int(255 * c) for c in ACT_COLS[i])
        txt(d, (p[0], p[1] - 95), lab, 46, col, int(A * on), stroke=6)


def label_act(d, O, t, i, lab, A):
    p = project(act_pos(i, t), O)
    col = tuple(int(255 * c) for c in ACT_COLS[i])
    txt(d, (p[0], p[1] - 100), lab, 44, col, A, stroke=6)


def draw_voz(layer, t, O):
    al = fade(t, VO0 - 0.15, ME0 - 0.15, 0.22)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    txt(d, (W / 2, 380), "ACCIÓN 1 · voz.yml", 54, YELLOW, A)
    k1 = ease_out((t - VO0) / 0.3)
    k2 = ease_out((t - VO0 - 0.5) / 0.3)
    k3 = ease_out((t - VO0 - 1.1) / 0.3)
    # tres cajas en columna
    box(d, 200, 450, W - 200, 560, CYAN, int(A * k1), "ELEVENLABS", None, 52)
    arrow(d, W / 2, 566, W / 2, 626, CYAN, int(A * k2), k2)
    box(d, 200, 632, W - 200, 742, YELLOW, int(A * k2), "BAJA LA VOZ", None, 50)
    gear(d, 268, 687, 34, YELLOW, int(A * k2), 3 * t)
    arrow(d, W / 2, 748, W / 2, 808, YELLOW, int(A * k3), k3)
    d.rounded_rectangle([200, 814, W - 200, 944], 26, fill=PANEL + (int(0.9 * A * k3),), outline=GREEN + (int(A * k3),), width=4)
    wave(d, W / 2 - 160, 879, 230, 40, t, GREEN, int(A * k3), 13, k3)
    d.text((W / 2 + 120, 879), "narracion.mp3", font=mono(32), fill=WHITE + (int(A * k3),), anchor="mm")
    packet(d, W / 2, 560, W / 2, 940, t, VO0 + 1.3, 1.0, YELLOW, A)


def draw_medios(layer, t, O):
    al = fade(t, ME0 - 0.15, MT0 - 0.15, 0.22)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    txt(d, (W / 2, 380), "ACCIÓN 2 · medios.yml", 54, CYAN, A)
    k1 = ease_out((t - ME0) / 0.3)
    k2 = ease_out((t - ME0 - 0.6) / 0.3)
    k3 = ease_out((t - ME0 - 1.6) / 0.3)
    # video terminado (tarjeta tipo reproductor)
    Ak = int(A * k1)
    d.rounded_rectangle([200, 450, W - 200, 600], 26, fill=PANEL + (int(0.9 * Ak),), outline=WHITE + (Ak,), width=4)
    d.polygon([(260, 490), (260, 560), (320, 525)], fill=YELLOW + (Ak,))
    d.text((350, 505), "VIDEO TERMINADO", font=font("Inter-Black.otf", 44), fill=WHITE + (Ak,), anchor="lm")
    d.text((350, 556), "FlashDatos_22.mp4", font=mono(32), fill=CYAN + (Ak,), anchor="lm")
    arrow(d, W / 2, 606, W / 2, 666, CYAN, int(A * k2), k2)
    box(d, 200, 672, W - 200, 782, CYAN, int(A * k2), "LO SUBE A GITHUB", None, 48)
    gear(d, 262, 727, 32, CYAN, int(A * k2), -3 * t)
    arrow(d, W / 2, 788, W / 2, 848, CYAN, int(A * k3), k3)
    Ak3 = int(A * k3)
    d.rounded_rectangle([140, 854, W - 140, 990], 68, fill=(10, 30, 26, int(0.92 * Ak3)), outline=GREEN + (Ak3,), width=5)
    link_icon(d, 230, 922, 80, GREEN, Ak3)
    d.text((300, 900), "ENLACE PÚBLICO", font=font("Inter-Black.otf", 48), fill=GREEN + (Ak3,), anchor="lm")
    d.text((300, 952), "…/releases/video-22", font=mono(32), fill=WHITE + (Ak3,), anchor="lm")
    packet(d, W / 2, 600, W / 2, 850, t, ME0 + 0.9, 1.1, CYAN, A)


NETS = [("YOUTUBE", (255, 80, 80)), ("INSTAGRAM", (255, 115, 200)), ("TIKTOK", (90, 235, 235))]


def draw_metricool(layer, t, O):
    al = fade(t, MT0 - 0.15, CIA[0] - 0.18, 0.22)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k0 = ease_out((t - MT0 + 0.1) / 0.3)
    Ak = int(A * k0)
    d.rounded_rectangle([250, 360, W - 250, 450], 45, fill=(10, 30, 26, int(0.92 * Ak)), outline=GREEN + (Ak,), width=4)
    link_icon(d, 320, 405, 60, GREEN, Ak)
    d.text((380, 405), "ENLACE", font=font("Inter-Black.otf", 46), fill=GREEN + (Ak,), anchor="lm")
    k1 = ease_out((t - MT0 - 0.35) / 0.3)
    arrow(d, W / 2, 456, W / 2, 520, GREEN, int(A * k1), k1)
    box(d, 230, 526, W - 230, 646, YELLOW, int(A * k1), "METRICOOL", "publica", 58, 34)
    packet(d, W / 2, 450, W / 2, 530, t, MT0 + 0.3, 0.5, GREEN, A)
    xs_ = [W / 2 - 300, W / 2, W / 2 + 300]
    for i, (nm, col) in enumerate(NETS):
        kk = ease_out((t - MT0 - 1.0 - 0.3 * i) / 0.3)
        if kk <= 0:
            continue
        a2 = int(A * kk)
        x = xs_[i]
        arrow(d, W / 2, 652, x, 730, col, a2, kk, 5)
        d.ellipse([x - 58, 740, x + 58, 856], fill=PANEL + (a2,), outline=col + (a2,), width=6)
        d.polygon([(x - 16, 772), (x - 16, 824), (x + 26, 798)], fill=col + (a2,))
        txt(d, (x, 898), nm, 40, WHITE, a2, stroke=6)
        packet(d, W / 2, 652, x, 740, t, MT0 + 1.3 + 0.3 * i, 0.5, col, A)


STEPS = ["IDEA", "GUION", "VOZ", "3D", "VIDEO", "PUBLICAR"]


def draw_cierre(layer, t, O):
    al = fade(t, CIA[0] - 0.18, CIB[0] - 0.15, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - CIA[0] + 0.1) / 0.35)
    txt(d, (W / 2, 390), "LA MEMORIA", 96, WHITE, int(A * k))
    txt(d, (W / 2, 480), "DEL CANAL", 70, YELLOW, int(A * k))
    # cadena de pasos (como commits en una rama)
    y = 680
    n = len(STEPS)
    xs_ = [150 + i * (W - 300) / (n - 1) for i in range(n)]
    t0 = CIA[0] + 1.2
    dt = (CIA[1] - CIA[0] - 1.4) / n
    for i in range(n):
        kk = ease_out((t - (t0 + dt * i)) / 0.25)
        if kk <= 0:
            continue
        a2 = int(A * kk)
        if i > 0:
            d.line([(xs_[i - 1] + 30, y), (lerp(xs_[i - 1] + 30, xs_[i] - 30, kk), y)], fill=CYAN + (a2,), width=8)
        r = 30 * (0.6 + 0.4 * kk)
        d.ellipse([xs_[i] - r, y - r, xs_[i] + r, y + r], fill=YELLOW + (a2,), outline=INK + (a2,), width=4)
        lab_y = y - 70 if i % 2 == 0 else y + 70
        txt(d, (xs_[i], lab_y), STEPS[i], 38, WHITE, a2, stroke=6)
    # líneas que unen nodos 3D con el núcleo
    cx, cy, _ = project((0.0, 0.0, 0.0), O)
    pts = [project(file_pos(i, t), O) for i in range(4)] + [project(act_pos(i, t), O) for i in range(2)]
    for p in pts:
        d.line([(p[0], p[1]), (cx, cy)], fill=CYAN + (int(70 * al),), width=3)
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        d.line([(a[0], a[1]), (b[0], b[1])], fill=YELLOW + (int(90 * al * k),), width=3)


AIS = [("CLAUDE", YELLOW), ("ELEVENLABS", CYAN), ("GITHUB", WHITE), ("METRICOOL", GREEN)]


def draw_next(layer, t):
    al = fade(t, CIB[0] - 0.15, CARD + 0.1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    txt(d, (W / 2, 390), "PARTE 5", 128, YELLOW, A)
    txt(d, (W / 2, 505), "TODO CONECTADO", 84, WHITE, A)
    # cuatro herramientas en rombo que se conectan
    cx, cy, rr = W / 2, 760, 165
    pos = [(cx, cy - rr), (cx + rr * 1.7, cy), (cx, cy + rr), (cx - rr * 1.7, cy)]
    nl = 0
    span = CIB[1] - CIB[0]
    for j in range(4):
        if t > CIB[0] + 0.6 + j * 0.22 * span:
            nl = j + 1
    for j in range(nl):
        a, b = pos[j], pos[(j + 1) % 4]
        d.line([a, b], fill=CYAN + (int(A * 0.8),), width=6)
        d.line([a, (cx, cy)], fill=YELLOW + (int(A * 0.4),), width=4)
    d.polygon(bolt(cx, cy, 90 + 6 * math.sin(6 * t)), fill=YELLOW + (A,))
    for j, (nm, col) in enumerate(AIS):
        kk = ease_out((t - CIB[0] - 0.15 * j) / 0.3)
        a2 = int(A * kk)
        f = font("Inter-Black.otf", 38)
        tw = d.textlength(nm, font=f)
        x, y = pos[j]
        d.rounded_rectangle([x - tw / 2 - 22, y - 34, x + tw / 2 + 22, y + 34], 34, fill=PANEL + (a2,), outline=col + (a2,), width=4)
        d.text((x, y), nm, font=f, fill=col + (a2,), anchor="mm")
    late = int(A * min(1.0, max(0.0, (t - (CIB[0] + 0.55 * span)) / 0.3)))
    txt(d, (W / 2, 1040), "¡ESTÉN ATENTOS!", 76, WHITE, late)


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
    txt(d, (W / 2, 1100), "Síguenos: mañana la parte 5", 50, CYAN, A, "Inter-ExtraBold.otf", 6)
    txt(d, (W / 2, 1165), "del método", 50, CYAN, A, "Inter-ExtraBold.otf", 6)


def overlays(frame_u8, t, O):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_hook(layer, t)
    draw_repo(layer, t, O)
    draw_nube(layer, t, O)
    draw_acciones(layer, t, O)
    draw_voz(layer, t, O)
    draw_medios(layer, t, O)
    draw_metricool(layer, t, O)
    draw_cierre(layer, t, O)
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
        print("frames", NFRAMES, "end", END, "card", CARD, "files", [round(x, 2) for x in FILE_T])
