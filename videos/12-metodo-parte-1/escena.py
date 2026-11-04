"""Flash Datos · video 12 · Serie "El método", parte 1: el primer mensaje.

La Tierra al centro con cuatro nodos de luz en órbita (las IAs que después se conectan),
el primer mensaje escrito en una burbuja de chat, el descarte de los videos para niños,
el nacimiento del logo, los cinco pasos del flujo y el adelanto de la parte 2.

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

LIGHT = np.array([-0.55, 0.45, 0.70]); LIGHT /= np.linalg.norm(LIGHT)


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


# ---------------- fondo: estrellas y una nebulosa azul-violeta (distinta a la del video 01) ----------------
def make_background():
    rng = np.random.default_rng(12)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1800
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
    gy, gx = np.mgrid[0:120, 0:68] / 36.0
    neb = fbm(gx, gy, np.full_like(gx, 1.9), 5, seed=1212)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.42) * 2.4, 0, 1) ** 1.5
    bg += neb[..., None] * np.array([0.012, 0.022, 0.060], np.float32)
    return bg


BG = make_background()

# ---------------- cuerpos ----------------
R_ORB = 1.32
TILT = math.radians(16)
NODE_COLS = [(1.0, 0.82, 0.25), (0.25, 0.80, 1.0), (1.0, 0.42, 0.62), (0.55, 1.0, 0.45)]


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


def node_angle(t):
    return 0.42 * t + 0.9 * max(0.0, min(t, PA1) - PL0)


def node_pos(i, t):
    a = node_angle(t) + i * math.pi / 2
    x, z = R_ORB * math.cos(a), R_ORB * math.sin(a)
    y = -z * math.sin(TILT); z = z * math.cos(TILT)
    return (x, y + 0.08 * math.sin(1.3 * t + i), z)


def bodies(t):
    out = [dict(n="earth", c=(0.0, 0.0, 0.0), r=1.0, kind="earth", rot=0.05)]
    for i, col in enumerate(NODE_COLS):
        pulse = 1.0 + 0.25 * math.sin(4 * t + 1.7 * i)
        out.append(dict(n=f"n{i}", c=node_pos(i, t), r=0.085, kind="glow", col=col, k=pulse))
    return out


def shade(body, n, V, t, ndl):
    if body["kind"] == "glow":
        mu = np.clip((n * V).sum(-1), 0, 1)
        c = lin(body["col"])
        return c * (body["k"] * (0.9 + 2.4 * mu ** 0.7))[..., None]
    diff = np.clip(ndl, 0, 1)
    soft = smooth(-0.15, 0.35, ndl) * 0.10
    light = (0.020 + 2.1 * diff + soft)[..., None]
    loc = rot_y(rot_x(n, math.radians(18)), -1.55 + body["rot"] * t)
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.88) + 0.80 * cl * 0.88
    R = 2 * ndl[..., None] * n - LIGHT
    spec = np.clip((R * V).sum(-1), 0, 1) ** 90 * (1 - land) * (1 - cl[..., 0]) * 0.35
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85])
    mu = np.clip((n * V).sum(-1), 0, 1)
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
    halo = 1.10 if body["kind"] == "earth" else 1.0
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


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
HK0, HK1 = SEG["hook"]["t0"], SEG["hook"]["t1"]
PR0, PR1 = SEG["prompt"]["t0"], SEG["prompt"]["t1"]
DE0, DE1 = SEG["descarte"]["t0"], SEG["descarte"]["t1"]
NO0, NO1 = SEG["nombre"]["t0"], SEG["nombre"]["t1"]
PL0, PL1 = SEG["plan"]["t0"], SEG["plan"]["t1"]
PA0, PA1 = SEG["pasos"]["t0"], SEG["pasos"]["t1"]
CI0, CI1 = SEG["cierre"]["t0"], SEG["cierre"]["t1"]
CIA = SEG["cierre"]["parts"][0]
CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
END = TM["end"]
NFRAMES = int(round(END * FPS))
FL = [NO0 - 0.2, PL0 - 0.15, CIB[0] - 0.15, CARD - 0.05]


def wtime(seg, idx):
    """Momento aproximado de la palabra número idx del segmento (por peso de letras)."""
    words = SEG[seg]["say"].split()
    wts = [len(w) + 1 + (3 if w[-1] in ".,:…?" else 0) for w in words]
    t0, t1 = SEG[seg]["t0"], SEG[seg]["t1"]
    return t0 + (t1 - t0) * sum(wts[:idx]) / sum(wts)


# pasos: "Investigar, escribir, poner la voz, animar y publicar en tres redes, y que nosotros solo diéramos el sí."
STEP_T = [wtime("pasos", i) for i in (0, 1, 2, 5, 7)]
SI_T = wtime("pasos", len(SEG["pasos"]["say"].split()) - 1) - 0.1
STEPS = ["INVESTIGAR", "ESCRIBIR", "PONER LA VOZ", "ANIMAR EN 3D", "PUBLICAR"]


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


def camera(t):
    """Devuelve (y de la cámara, distancia). y > 0 baja la Tierra en pantalla."""
    if t < 2.6:
        return 0.55, math.exp(lerp(math.log(15.0), math.log(6.6), ease_out(t / 2.6)))
    if t < NO0 - 0.2:
        return 0.55, lerp(6.6, 6.0, (t - 2.6) / (NO0 - 0.2 - 2.6))
    if t < PL0 - 0.15:
        return 0.55, lerp(5.6, 5.2, (t - NO0 + 0.2) / (PL0 - NO0 + 0.05))
    if t < PA0:
        return 0.55, lerp(5.2, 8.6, ease((t - PL0 + 0.15) / (PA0 - PL0 + 0.15)))
    if t < CIB[0] - 0.15:
        return 0.55, lerp(8.6, 7.6, (t - PA0) / (CIB[0] - 0.15 - PA0))
    return 0.55, lerp(6.4, 6.0, min(1.0, (t - CIB[0] + 0.15) / (END - CIB[0])))


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
    """Etiqueta fija de la serie arriba: EL MÉTODO · PARTE 1/5."""
    if A <= 0:
        return
    s = "EL MÉTODO · PARTE 1/5"
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


PROMPT = "Queremos un canal de ciencia y tecnología, con animaciones 3D y sonidos originales."


def draw_bubble(layer, t, a, b, k_type, small=False):
    al = fade(t, a, b, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - a) / 0.35)) * 40
    x0, x1 = 80, W - 80
    y0 = 345 + rise
    f = font("Inter-ExtraBold.otf", 50)
    lines = wrap(d, PROMPT, f, x1 - x0 - 80)
    y1 = y0 + 112 + 66 * len(lines)
    d.rounded_rectangle([x0, y0, x1, y1], 36, fill=(14, 22, 44, int(0.86 * A)), outline=CYAN + (A,), width=4)
    d.polygon([(x1 - 120, y1 - 2), (x1 - 60, y1 + 52), (x1 - 60, y1 - 2)], fill=(14, 22, 44, int(0.86 * A)))
    d.line([(x1 - 120, y1), (x1 - 60, y1 + 52), (x1 - 60, y1)], fill=CYAN + (A,), width=4)
    d.text((x0 + 40, y0 + 52), "EL PRIMER MENSAJE", font=font("Inter-Black.otf", 36), fill=YELLOW + (A,), anchor="lm")
    n = int(len(PROMPT) * min(1.0, max(0.0, k_type)))
    shown = 0; y = y0 + 128
    for ln in lines:
        part = ln[:max(0, n - shown)]
        shown += len(ln) + 1
        d.text((x0 + 40, y), part, font=f, fill=WHITE + (A,), anchor="lm")
        if 0 < len(part) < len(ln) or (part == ln and shown >= n and k_type < 1.05):
            if int(t * 3) % 2 == 0 or k_type < 1:
                cx = x0 + 40 + d.textlength(part, font=f) + 6
                d.rectangle([cx, y - 26, cx + 6, y + 26], fill=CYAN + (A,))
        y += 66


def draw_kids(layer, t):
    al = fade(t, DE0 + 0.05, DE1 + 0.2, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - DE0) / 0.3)) * 24
    y = 420 + rise
    txt(d, (W / 2, y), "VIDEOS", 104, WHITE, A)
    txt(d, (W / 2, y + 112), "PARA NIÑOS", 104, WHITE, A)
    k = ease_out((t - (DE0 + 0.55 * (DE1 - DE0))) / 0.28)
    if k > 0:
        xa, xb = 150, 150 + (W - 300) * k
        d.line([(xa, y + 120), (xb, y - 10)], fill=RED + (A,), width=22)
        a2 = int(A * min(1.0, k * 1.4))
        txt(d, (W / 2, y + 240), "DESCARTADO", 64, RED, a2, "Inter-Black.otf", 7)


def draw_logo(layer, t):
    al = fade(t, NO0 - 0.2, PL0 - 0.2, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - NO0 + 0.2) / 0.45)
    s = 120 + 90 * k + 6 * math.sin(6 * t)
    d.polygon(bolt(W / 2, 445, s), fill=YELLOW + (A,), outline=INK + (A,))
    txt(d, (W / 2, 610), "FLASH DATOS", 108, WHITE, A)
    sub = int(A * min(1.0, max(0.0, (t - NO0 - 1.6) / 0.3)))
    txt(d, (W / 2, 705), "ciencia en 40 segundos", 54, CYAN, sub, "Inter-ExtraBold.otf", 7)


def draw_plan(layer, t):
    al = fade(t, PL0 + 0.1, PA0 + 0.1, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - PL0) / 0.3)) * 24
    txt(d, (W / 2, 420 + rise), "QUE TODO", 120, WHITE, A)
    k = min(1.0, max(0.0, (t - (PL0 + 0.62 * (PL1 - PL0))) / 0.25))
    txt(d, (W / 2, 548 + rise), "FUNCIONE SOLO", 104, YELLOW, int(A * k))


def check(d, cx, cy, s, col, A):
    d.line([(cx - 0.5 * s, cy), (cx - 0.15 * s, cy + 0.35 * s), (cx + 0.55 * s, cy - 0.4 * s)], fill=col + (A,), width=int(s * 0.22), joint="curve")


def draw_steps(layer, t):
    al = fade(t, PA0 - 0.05, CIA[0] - 0.05, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 52)
    y = 360
    for i, (st, ts) in enumerate(zip(STEPS, STEP_T)):
        k = ease_out((t - ts + 0.05) / 0.25)
        if k <= 0:
            y += 84
            continue
        a2 = int(A * min(1.0, k))
        x = 210 - 60 * (1 - k)
        d.ellipse([x - 32, y - 32, x + 32, y + 32], fill=tuple(int(255 * c) for c in NODE_COLS[i % 4]) + (a2,))
        d.text((x, y), str(i + 1), font=font("Inter-Black.otf", 38), fill=INK + (a2,), anchor="mm")
        d.text((x + 60, y), st, font=f, fill=WHITE + (a2,), anchor="lm", stroke_width=7, stroke_fill=INK + (a2,))
        if i < len(STEPS) - 1 and t > STEP_T[i + 1] - 0.05:
            d.line([(x, y + 34), (x, y + 50)], fill=CYAN + (a2,), width=5)
        y += 84
    k = ease_out((t - SI_T) / 0.3)
    if k > 0:
        a2 = int(A * k)
        bx, by = W - 190, 520
        r = 92 * (0.6 + 0.4 * k)
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=YELLOW + (a2,), outline=INK + (a2,), width=6)
        d.text((bx, by - 8), "SÍ", font=font("Inter-Black.otf", int(76 * (0.6 + 0.4 * k))), fill=INK + (a2,), anchor="mm")


def draw_links(layer, t, O):
    """Líneas entre los nodos: las IAs que se conectan (avance de las partes 4 y 5)."""
    al = fade(t, PA0 + 0.4, CARD, 0.4)
    if al <= 0:
        return
    pts = [project(node_pos(i, t), O) for i in range(4)]
    d = ImageDraw.Draw(layer)
    nlinks = 4 if t > PA0 + 2.0 else (2 if t > PA0 + 1.2 else 1)
    for i in range(nlinks):
        a, b = pts[i], pts[(i + 1) % 4]
        A = int(150 * al)
        d.line([(a[0], a[1]), (b[0], b[1])], fill=CYAN + (A,), width=4)
    cx, cy, _ = project((0.0, 0.0, 0.0), O)
    for p in pts:
        d.line([(p[0], p[1]), (cx, cy)], fill=YELLOW + (int(60 * al),), width=3)


def draw_inicio(layer, t):
    al = fade(t, CIA[0] + 0.2, CIA[1] + 0.2, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - CIA[0]) / 0.3)) * 24
    txt(d, (W / 2, 430 + rise), "UN MENSAJE", 104, WHITE, A)
    txt(d, (W / 2, 548 + rise), "lo empezó todo", 60, CYAN, A, "Inter-ExtraBold.otf", 7)


def draw_next(layer, t):
    al = fade(t, CIB[0] - 0.15, CARD + 0.1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - CIB[0] + 0.15) / 0.4)
    txt(d, (W / 2, 400), "PARTE 2", 128, YELLOW, A)
    txt(d, (W / 2, 520), "LA VOZ", 96, WHITE, A)
    # ondas de voz animadas
    n = 15
    for i in range(n):
        x = W / 2 + (i - (n - 1) / 2) * 34
        h = (18 + 70 * abs(math.sin(5.5 * t + i * 0.7)) * math.exp(-((i - 7) / 5.0) ** 2)) * k
        d.rounded_rectangle([x - 9, 640 - h, x + 9, 640 + h], 9, fill=CYAN + (A,))
    late = int(A * min(1.0, max(0.0, (t - (CIB[0] + 0.45 * (CIB[1] - CIB[0]))) / 0.3)))
    txt(d, (W / 2, 790), "¡ESTÉN ATENTOS!", 76, WHITE, late)


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
    txt(d, (W / 2, 1100), "Síguenos: mañana la parte 2", 50, CYAN, A, "Inter-ExtraBold.otf", 6)
    txt(d, (W / 2, 1165), "del método", 50, CYAN, A, "Inter-ExtraBold.otf", 6)


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


def draw_title(layer, t):
    al = fade(t, 0.0, PR0 - 0.1, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out(t / 0.6)
    txt(d, (W / 2, 420), "ASÍ HACEMOS", 92, WHITE, int(A * k))
    txt(d, (W / 2, 530), "ESTE CANAL", 112, YELLOW, int(A * k))
    sub = int(A * min(1.0, max(0.0, (t - 1.2) / 0.3)))
    txt(d, (W / 2, 640), "con inteligencia artificial", 54, CYAN, sub, "Inter-ExtraBold.otf", 7)


def overlays(frame_u8, t, O):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_links(layer, t, O)
    draw_title(layer, t)
    k_type = (t - (PR0 + 0.2)) / max(0.1, (PR1 - PR0 - 0.6))
    draw_bubble(layer, t, PR0 - 0.05, DE0 - 0.05, k_type)
    draw_kids(layer, t)
    draw_logo(layer, t)
    draw_plan(layer, t)
    draw_steps(layer, t)
    draw_inicio(layer, t)
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
    cy, D = camera(t)
    O = np.array([0.0, cy, D])
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
        print("frames", NFRAMES, "end", END, "card", CARD, "pasos", [round(x, 2) for x in STEP_T], "si", round(SI_T, 2))
