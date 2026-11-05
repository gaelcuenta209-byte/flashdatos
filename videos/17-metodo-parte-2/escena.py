"""Flash Datos · video 17 · Serie "El método", parte 2: la voz.

Una estrella de sonido cian al centro que late con la narración real (su envolvente sale de
voz/narracion.mp3), ondas de sonido que se expanden en su plano y dos lunas que son las dos
tomas de ElevenLabs. La cámara orbita alrededor (en la parte 1 solo se acercaba de frente).
Gráficos: fuentes verificadas, la hoja del guion, la onda de la voz, las dos tomas, el camino
ElevenLabs → GitHub → narracion.mp3 y la línea de tiempo con las pausas y los subtítulos.

Uso:
  python3 escena.py info
  python3 escena.py test 1 5 12 ...
  python3 escena.py chunk <ini> <fin> <out>
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom, uniform_filter1d

BASE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
TY = math.tan(math.radians(20)); TX = TY * W / H
PIX = 2 * TY / H

xs = ((np.arange(W) + 0.5) / W * 2 - 1) * TX
ys = (1 - (np.arange(H) + 0.5) / H * 2) * TY
DX, DY = np.meshgrid(xs, ys)
NRM = np.sqrt(DX * DX + DY * DY + 1)
DIRS = np.stack([DX / NRM, DY / NRM, -1 / NRM], axis=-1)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
SUN = np.clip(T("sun"), 0, 1); VENUS = lin(np.clip(T("venus"), 0, 1)); JUP = lin(np.clip(T("jupiter"), 0, 1))
SUN_L = SUN.mean(-1) if SUN.ndim == 3 else SUN
SUN_L = (SUN_L - SUN_L.min()) / (SUN_L.max() - SUN_L.min() + 1e-9)


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



def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------- fondo: estrellas y una nebulosa verde-azulada (distinta a la de la parte 1) ----------------
def make_background():
    rng = np.random.default_rng(17)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1700
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.025 + 0.45 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.78 + 0.2 * tint, 0.88 + 0.06 * tint, 1.0 - 0.2 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 45
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([0.9, 0.97, 1.0]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 30.0
    neb = fbm(gx, gy, np.full_like(gx, 3.3), 5, seed=1717)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.6, 0, 1) ** 1.4
    bg += neb[..., None] * np.array([0.006, 0.040, 0.050], np.float32)
    return bg


BG = make_background()

# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
HK0, HK1 = SEG["hook"]["t0"], SEG["hook"]["t1"]
IN0, IN1 = SEG["investiga"]["t0"], SEG["investiga"]["t1"]
GU0, GU1 = SEG["guion"]["t0"], SEG["guion"]["t1"]
VO0, VO1 = SEG["voz"]["t0"], SEG["voz"]["t1"]
TO0, TO1 = SEG["tomas"]["t0"], SEG["tomas"]["t1"]
GH0, GH1 = SEG["github"]["t0"], SEG["github"]["t1"]
PS0, PS1 = SEG["pausas"]["t0"], SEG["pausas"]["t1"]
CI0, CI1 = SEG["cierre"]["t0"], SEG["cierre"]["t1"]
CIA = SEG["cierre"]["parts"][0]
CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
END = TM["end"]
NFRAMES = int(round(END * FPS))
FL = [IN0 - 0.15, VO0 - 0.15, GH0 - 0.15, CIB[0] - 0.15, CARD - 0.05]


def wtime(seg, idx):
    """Momento aproximado de la palabra número idx del segmento (por peso de letras)."""
    words = SEG[seg]["say"].split()
    wts = [len(w) + 1 + (3 if w[-1] in ".,:…?" else 0) for w in words]
    t0, t1 = SEG[seg]["t0"], SEG[seg]["t1"]
    return t0 + (t1 - t0) * sum(wts[:idx]) / sum(wts)


HK_B = wtime("hook", 12)            # "Así le dimos voz al canal."
SRC_T = [wtime("investiga", i) for i in (17, 19, 21)]   # NASA, ESA, universidades
DOS_T = wtime("investiga", 12)
GANCHO_T = wtime("guion", 5); FINAL_T = wtime("guion", 12)
CARLOS_T = wtime("voz", 8)
ELIGE_T = wtime("tomas", 5)
MP3_T = wtime("github", 5)

# ---------------- envolvente real de la voz ----------------
ENV_FPS = 60


def load_env():
    cache = os.path.join(BASE, "out", "env.npy")
    if os.path.exists(cache):
        return np.load(cache)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(BASE, "voz", "narracion.mp3"),
                          "-ac", "1", "-ar", "12000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = 12000 // ENV_FPS
    n = len(a) // hop
    rms = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1))
    rms = uniform_filter1d(rms, 3)
    rms = np.clip(rms / (np.percentile(rms, 97) + 1e-9), 0, 1.2)
    pad = int(TM.get("voice_offset", 0.1) * ENV_FPS)
    env = np.concatenate([np.zeros(pad), rms])
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.save(cache, env)
    return env


ENV = load_env()


def env_at(t):
    i = t * ENV_FPS
    i0 = int(i)
    if i0 < 0 or i0 + 1 >= len(ENV):
        return 0.0
    f = i - i0
    return float(ENV[i0] * (1 - f) + ENV[i0 + 1] * f)


# ---------------- cuerpos ----------------
TILT = math.radians(14)
R_MOON = 2.05


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


def plane_pt(r, a):
    """Punto en el plano inclinado de la estrella (órbitas y ondas)."""
    x, z = r * math.cos(a), r * math.sin(a)
    return np.array([x, -z * math.sin(TILT), z * math.cos(TILT)])


def moon_pos(i, t):
    a = 0.30 * t + 1.1 + i * math.pi
    return plane_pt(R_MOON, a)


def take_state(i, t):
    """Brillo extra de cada toma: la toma 1 se elige, la toma 2 se apaga."""
    on = fade(t, TO0 - 0.1, TO1 + 0.6, 0.3)
    k = smooth(ELIGE_T - 0.1, ELIGE_T + 0.4, t)
    if i == 0:
        return 1.0, on * (0.5 + 0.9 * k)
    return 1.0 - 0.65 * k * on, 0.0


def bodies(t):
    e = env_at(t)
    out = [dict(n="star", c=np.zeros(3), r=1.0 + 0.025 * e, kind="star", e=e)]
    for i, (tex, r) in enumerate(((VENUS, 0.24), (JUP, 0.21))):
        dim, halo = take_state(i, t)
        out.append(dict(n=f"m{i}", c=moon_pos(i, t), r=r, kind="moon", tex=tex, dim=dim, halo=halo, i=i))
    return out


def shade(body, n, V, t):
    mu = np.clip((n * V).sum(-1), 0, 1)
    if body["kind"] == "star":
        loc = rot_y(rot_x(n, math.radians(10)), 0.08 * t)
        la, lo = latlon(loc)
        g = sample(SUN_L, la, lo + 0.02 * np.sin(3 * la + t))
        g = np.clip((g - 0.35) * 1.8, 0, 1) ** 1.3
        base = np.array([0.006, 0.05, 0.20]) + g[..., None] * np.array([0.05, 0.45, 0.85])
        k = 0.30 + 0.75 * body["e"]
        limb = 0.45 + 0.55 * mu ** 0.5
        rim = ((1 - mu) ** 3)[..., None] * np.array([0.3, 1.2, 1.6])
        return base * (k * limb)[..., None] + rim * (0.35 + 0.6 * body["e"])
    C = body["c"]
    L = -C / np.linalg.norm(C)          # luz que viene de la estrella
    ndl = n @ L
    diff = np.clip(ndl, 0, 1)
    loc = rot_y(n, 0.25 * t + body["i"])
    la, lo = latlon(loc)
    alb = sample(body["tex"], la, lo)
    col = alb * (0.015 + 2.0 * diff * body["dim"])[..., None]
    fres = (1 - mu) ** 2.5
    col = col + np.array([0.3, 0.8, 1.0]) * (fres * 0.35 * np.clip(ndl + 0.3, 0, 1) * body["dim"])[..., None]
    return col


def draw_sphere(img, O, body, t, R):
    """O: cámara (mundo); R: matriz mundo→cámara (filas = derecha, arriba, atrás)."""
    C = R @ (np.asarray(body["c"]) - O)   # centro en espacio de cámara
    r = body["r"]
    dist_c = float(np.linalg.norm(C))
    if dist_c <= r * 1.0001 or C[2] >= 0:
        return
    depth = -C[2]
    cxp = (C[0] / depth / TX + 1) / 2 * W
    cyp = (1 - C[1] / depth / TY) / 2 * H
    rpx = math.tan(math.asin(r / dist_c)) / PIX
    halo = 1.35 if body["kind"] == "star" else (1.9 if body.get("halo", 0) > 0 else 1.0)
    ext = rpx * halo * 1.1 + 4
    x0 = int(max(0, cxp - ext)); x1 = int(min(W, cxp + ext + 1))
    y0 = int(max(0, cyp - ext)); y1 = int(min(H, cyp + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return
    d = DIRS[y0:y1, x0:x1]
    b = -(d @ C)
    perp2 = np.maximum(float(C @ C) - b * b, 0)
    dist = np.sqrt(perp2)
    pixw = np.maximum(-b, 1e-9) * PIX
    alpha = np.clip((r - dist) / pixw + 0.5, 0, 1)
    region = img[y0:y1, x0:x1]
    if body["kind"] == "star":
        gl = np.exp(-np.maximum(dist - r, 0) / (0.12 * r)) * (dist > r * 0.99)
        region += (gl * (0.25 + 0.5 * body["e"]) * (1 - alpha))[..., None] * np.array([0.10, 0.55, 1.0])
    elif body.get("halo", 0) > 0:
        gl = np.exp(-np.maximum(dist - r, 0) / (0.25 * r)) * (dist > r * 0.99)
        region += (gl * body["halo"] * (1 - alpha))[..., None] * np.array([1.0, 0.80, 0.25])
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]; bs = b[sel]
    tt = -bs - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    nw = n @ R; Vw = (-ds) @ R          # de cámara a mundo (R ortonormal)
    col = shade(body, nw, Vw, t)
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
    """Etiqueta fija de la serie arriba: EL MÉTODO · PARTE 2/5."""
    if A <= 0:
        return
    s = "EL MÉTODO · PARTE 2/5"
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



def project(P, O, R):
    rel = R @ (np.asarray(P) - O)
    depth = -rel[2]
    if depth <= 1e-3:
        return None
    return (rel[0] / depth / TX + 1) / 2 * W, (1 - rel[1] / depth / TY) / 2 * H, depth


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


# ---------------- cámara en órbita: (tiempo, azimut, elevación, distancia) ----------------
def cam_keys():
    return [(0.0, -1.10, 0.10, 16.0), (2.4, -0.75, 0.22, 7.2), (IN0 - 0.15, -0.45, 0.30, 6.8),
            (IN0, -0.20, 0.42, 6.4), (GU0, 0.15, 0.38, 6.6), (VO0 - 0.15, 0.35, 0.30, 6.9),
            (VO0, 0.55, 0.18, 6.0), (TO0, 0.75, 0.30, 7.4), (TO1 + 0.3, 1.05, 0.48, 8.2),
            (GH0, 1.15, 0.50, 8.0), (PS0, 1.40, 0.32, 7.0), (CIA[0], 1.65, 0.22, 6.6),
            (CIB[0] - 0.15, 1.80, 0.25, 6.4), (CIB[0], 2.05, 0.40, 7.6), (END, 2.40, 0.30, 7.0)]


KEYS = cam_keys()


def camera(t):
    for (ta, aa, ea, da), (tb, ab, eb, db) in zip(KEYS, KEYS[1:]):
        if ta <= t < tb:
            s = (t - ta) / max(1e-6, tb - ta)
            s = ease_out(s) if ta == 0.0 else ease(s)
            az = lerp(aa, ab, s); el = lerp(ea, eb, s)
            dd = math.exp(lerp(math.log(da), math.log(db), s))
            break
    else:
        _, az, el, dd = KEYS[-1]
    O = np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)]) * dd
    fwd = -O / np.linalg.norm(O)
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    # mirar un poco por encima de la estrella para que quede en la mitad baja (los gráficos van arriba)
    aim = up * 0.55 * dd / 6.6
    fwd = (aim - O); fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    R = np.stack([right, up, -fwd])
    return O, R


# ---------------- ondas de sonido en el plano de la estrella ----------------
WAVE_PERIOD = 0.55


def draw_waves(layer, t, O, R, star_r):
    d = ImageDraw.Draw(layer)
    sc = project(np.zeros(3), O, R)
    if sc is None:
        return
    srad = math.tan(math.asin(min(0.99, star_r / np.linalg.norm(O)))) / PIX
    k0 = int(t / WAVE_PERIOD)
    for k in range(k0 - 6, k0 + 1):
        tb = k * WAVE_PERIOD
        age = t - tb
        if tb < 0 or age < 0 or age > 3.2:
            continue
        amp = env_at(tb)
        if amp < 0.08:
            continue
        rr = 1.08 + age * 0.85
        A = int(255 * min(1.0, 0.3 + amp) * (1 - age / 3.2) ** 1.2)
        if A < 6:
            continue
        pts = []
        for j in range(97):
            p = project(plane_pt(rr, j / 96 * 2 * math.pi), O, R)
            if p is None:
                pts.append(None); continue
            hidden = math.hypot(p[0] - sc[0], p[1] - sc[1]) < srad and p[2] > sc[2]
            pts.append(None if hidden else (p[0], p[1]))
        col = CYAN if k % 2 else (150, 240, 255)
        for a, b in zip(pts, pts[1:]):
            if a and b:
                d.line([a, b], fill=col + (A,), width=6)


# ---------------- gráficos ----------------
def env_bars(d, cx, cy, n, gap, wbar, hmax, t, A, col=None, lag=0.035):
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * gap
        e = env_at(t - abs(i - (n - 1) / 2) * lag)
        h = 6 + hmax * e * (0.55 + 0.45 * math.exp(-((i - (n - 1) / 2) / (n / 3)) ** 2))
        d.rounded_rectangle([x - wbar / 2, cy - h, x + wbar / 2, cy + h], int(wbar / 2), fill=(col or CYAN) + (A,))


def draw_hook(layer, t):
    al = fade(t, 0.0, IN0 - 0.1, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    a1 = int(A * (1 - smooth(HK_B - 0.2, HK_B + 0.1, t)))
    a2 = int(A * smooth(HK_B - 0.1, HK_B + 0.2, t))
    k = ease_out(t / 0.6)
    if a1 > 0:
        txt(d, (W / 2, 400), "ESTA VOZ", 112, WHITE, int(a1 * k))
        env_bars(d, W / 2, 545, 19, 40, 20, 70, t, int(a1 * k))
        txt(d, (W / 2, 690), "la crea una IA", 64, YELLOW, a1, "Inter-ExtraBold.otf", 8)
    if a2 > 0:
        txt(d, (W / 2, 410), "ASÍ LE DIMOS", 92, WHITE, a2)
        txt(d, (W / 2, 520), "VOZ AL CANAL", 112, YELLOW, a2)
        env_bars(d, W / 2, 650, 23, 34, 16, 50, t, a2)


def check(d, cx, cy, s, col, A):
    d.line([(cx - 0.5 * s, cy), (cx - 0.15 * s, cy + 0.35 * s), (cx + 0.55 * s, cy - 0.4 * s)], fill=col + (A,), width=max(3, int(s * 0.22)), joint="curve")


def draw_sources(layer, t):
    al = fade(t, IN0 - 0.05, GU0 - 0.05, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - IN0) / 0.3)) * 30
    txt(d, (W / 2, 370 + rise), "INVESTIGAR Y VERIFICAR", 64, WHITE, A)
    # lupa
    lx, ly = 190, 520 + rise
    d.ellipse([lx - 52, ly - 52, lx + 52, ly + 52], outline=CYAN + (A,), width=12)
    d.line([(lx + 38, ly + 38), (lx + 92, ly + 92)], fill=CYAN + (A,), width=18)
    names = ["NASA", "ESA", "UNIVERSIDADES"]
    y = 470 + rise
    for nm, ts in zip(names, SRC_T):
        k = ease_out((t - ts + 0.1) / 0.25)
        if k > 0:
            a2 = int(A * k)
            x0 = 330 + 50 * (1 - k)
            f = font("Inter-Black.otf", 46)
            tw = d.textlength(nm, font=f)
            d.rounded_rectangle([x0, y - 36, x0 + tw + 120, y + 36], 34, fill=(12, 26, 46, int(0.85 * a2)), outline=CYAN + (a2,), width=3)
            d.text((x0 + 28, y), nm, font=f, fill=WHITE + (a2,), anchor="lm")
            check(d, x0 + tw + 78, y, 38, YELLOW, a2)
        y += 92
    k = ease_out((t - DOS_T) / 0.3)
    if k > 0:
        txt(d, (W / 2, 790 + rise), "2 FUENTES POR DATO", 58, YELLOW, int(A * k), "Inter-Black.otf", 7)


def draw_script(layer, t):
    al = fade(t, GU0 - 0.05, VO0 - 0.1, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - GU0) / 0.35)) * 50
    x0, x1, y0 = 200, W - 200, 350 + rise
    y1 = y0 + 470
    d.rounded_rectangle([x0, y0, x1, y1], 28, fill=(236, 242, 250, int(0.94 * A)), outline=CYAN + (A,), width=4)
    d.text((x0 + 36, y0 + 46), "GUION", font=font("Inter-Black.otf", 40), fill=INK + (A,), anchor="lm")
    prog = (t - GU0) / max(0.1, GU1 - GU0)
    widths = [0.92, 0.80, 0.86, 0.70, 0.88, 0.62]
    for i, wv in enumerate(widths):
        ly = y0 + 120 + i * 58
        k = min(1.0, max(0.0, prog * 7 - i * 0.9))
        if k <= 0:
            continue
        lw = (x1 - x0 - 72) * wv * k
        col = (90, 100, 120)
        if i == 0 and t > GANCHO_T - 0.1:
            col = (230, 170, 20)
        if i == len(widths) - 1 and t > FINAL_T - 0.1:
            col = (20, 150, 200)
        d.rounded_rectangle([x0 + 36, ly - 13, x0 + 36 + lw, ly + 13], 13, fill=col + (A,))
    kg = ease_out((t - GANCHO_T) / 0.3)
    if kg > 0:
        tag(d, x1 - 10, y0 + 120, "GANCHO", YELLOW, int(A * kg))
    kf = ease_out((t - FINAL_T) / 0.3)
    if kf > 0:
        tag(d, x1 - 10, y0 + 120 + 5 * 58, "FINAL", CYAN, int(A * kf))
        check(d, x0 + 36 + (x1 - x0 - 72) * 0.62 + 45, y0 + 120 + 5 * 58, 34, (20, 150, 90), int(A * kf))


def tag(d, x, y, s, col, A):
    f = font("Inter-Black.otf", 38)
    tw = d.textlength(s, font=f)
    d.rounded_rectangle([x - 20, y - 30, x + tw + 24, y + 30], 30, fill=col + (A,), outline=INK + (A,), width=4)
    d.text((x + 2, y), s, font=f, fill=INK + (A,), anchor="lm")


def draw_voice(layer, t):
    al = fade(t, VO0 - 0.15, TO0 - 0.05, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - VO0 + 0.15) / 0.4)
    txt(d, (W / 2, 390), "ELEVENLABS", 110, WHITE, int(A * k))
    env_bars(d, W / 2, 560, 27, 34, 18, 95, t, A)
    kc = ease_out((t - CARLOS_T) / 0.35)
    if kc > 0:
        a2 = int(A * kc)
        s1 = "voz: CARLOS GARZA"
        f = font("Inter-Black.otf", 50)
        tw = d.textlength(s1, font=f)
        d.rounded_rectangle([W / 2 - tw / 2 - 34, 690, W / 2 + tw / 2 + 34, 770], 40, fill=YELLOW + (a2,), outline=INK + (a2,), width=5)
        d.text((W / 2, 730), s1, font=f, fill=INK + (a2,), anchor="mm")
        txt(d, (W / 2, 820), "narrador mexicano", 50, CYAN, a2, "Inter-ExtraBold.otf", 7)


def draw_takes(layer, t):
    al = fade(t, TO0 - 0.05, GH0 - 0.1, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    kpick = smooth(ELIGE_T - 0.1, ELIGE_T + 0.3, t)
    for i in range(2):
        k = ease_out((t - TO0 - 0.25 * i) / 0.3)
        if k <= 0:
            continue
        a2 = int(A * k * (1 - 0.6 * kpick if i == 1 else 1))
        cx = W / 2 + (i - 0.5) * 440
        y0 = 380 + 30 * (1 - k)
        sel = i == 0 and kpick > 0
        outline = YELLOW if sel else CYAN
        wdt = 4 + int(5 * kpick) if sel else 3
        d.rounded_rectangle([cx - 200, y0, cx + 200, y0 + 330], 30, fill=(12, 22, 42, int(0.88 * a2)), outline=outline + (a2,), width=wdt)
        d.text((cx, y0 + 60), f"TOMA {i + 1}", font=font("Inter-Black.otf", 56), fill=WHITE + (a2,), anchor="mm")
        rng = np.random.default_rng(40 + i)
        hs = rng.random(13)
        for j in range(13):
            x = cx - 156 + j * 26
            h = 10 + 50 * hs[j] * (0.6 + 0.4 * abs(math.sin(4 * t + j + i)))
            d.rounded_rectangle([x - 8, y0 + 175 - h, x + 8, y0 + 175 + h], 8, fill=(outline if sel else CYAN) + (a2,))
        if sel:
            check(d, cx, y0 + 280, 46, YELLOW, int(a2 * kpick))
    if kpick > 0:
        txt(d, (W / 2 - 220, 790), "LA MÁS CLARA", 54, YELLOW, int(A * kpick), "Inter-Black.otf", 7)


def file_icon(d, cx, cy, s, A, label):
    x0, y0, x1, y1 = cx - 0.38 * s, cy - 0.5 * s, cx + 0.38 * s, cy + 0.5 * s
    c = 0.22 * s
    d.polygon([(x0, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1), (x0, y1)], fill=(236, 242, 250, A), outline=CYAN + (A,))
    d.polygon([(x1 - c, y0), (x1 - c, y0 + c), (x1, y0 + c)], fill=(170, 200, 230, A))
    for j in range(5):
        x = cx - 0.22 * s + j * 0.11 * s
        h = 0.06 * s + 0.1 * s * abs(math.sin(j * 1.7 + 1))
        d.line([(x, cy + 0.05 * s - h), (x, cy + 0.05 * s + h)], fill=(20, 120, 200, A), width=max(3, int(0.05 * s)))
    d.text((cx, y1 + 38), label, font=font("Inter-Black.otf", 36), fill=WHITE + (A,), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))


def box(d, cx, cy, wb, hb, s, col, A, size=40):
    d.rounded_rectangle([cx - wb / 2, cy - hb / 2, cx + wb / 2, cy + hb / 2], 24, fill=(12, 22, 42, int(0.9 * A)), outline=col + (A,), width=4)
    d.text((cx, cy), s, font=font("Inter-Black.otf", size), fill=WHITE + (A,), anchor="mm")


def draw_github(layer, t):
    al = fade(t, GH0 - 0.15, PS0 + 0.1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    xs_ = [180, W / 2, W - 180]
    y = 520
    k1 = ease_out((t - GH0 + 0.1) / 0.3)
    box(d, xs_[0], y, 270, 110, "ElevenLabs", CYAN, int(A * k1), 38)
    k2 = ease_out((t - wtime("github", 1)) / 0.3)
    if k2 > 0:
        box(d, xs_[1], y, 260, 140, "", YELLOW, int(A * k2))
        d.text((xs_[1], y - 24), "GitHub", font=font("Inter-Black.otf", 44), fill=WHITE + (int(A * k2),), anchor="mm")
        d.text((xs_[1], y + 30), "acción", font=font("Inter-ExtraBold.otf", 34), fill=YELLOW + (int(A * k2),), anchor="mm")
        d.line([(xs_[0] + 140, y), (xs_[1] - 135, y)], fill=CYAN + (int(A * k2),), width=6)
    k3 = ease_out((t - MP3_T) / 0.3)
    if k3 > 0:
        d.line([(xs_[1] + 135, y), (xs_[2] - 80, y)], fill=CYAN + (int(A * k3),), width=6)
        file_icon(d, xs_[2], y - 10, 150, int(A * k3), "narracion.mp3")
    # paquete de audio que viaja por la tubería
    p = ((t - GH0) / max(0.3, GH1 - GH0)) % 1.0
    px = lerp(xs_[0] + 140, xs_[2] - 80, p)
    if k2 > 0:
        d.ellipse([px - 14, y - 14, px + 14, y + 14], fill=YELLOW + (int(A * k2),))
    txt(d, (W / 2, 380), "BAJA EL AUDIO", 80, WHITE, int(A * k1))


def draw_timeline(layer, t):
    al = fade(t, PS0 - 0.05, CIA[0] - 0.05, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    txt(d, (W / 2, 370), "PAUSAS = SUBTÍTULOS", 66, WHITE, A)
    x0, x1, yc = 80, W - 80, 560
    reveal = ease((t - PS0) / 1.2)
    span = TM["end"]
    n = 240
    for j in range(int(n * reveal)):
        tt = j / n * span
        e = float(ENV[min(len(ENV) - 1, int(tt * ENV_FPS))]) if tt * ENV_FPS < len(ENV) else 0
        x = x0 + (x1 - x0) * j / n
        h = 2 + 70 * e
        d.line([(x, yc - h), (x, yc + h)], fill=CYAN + (int(A * 0.9),), width=3)
    # pausas detectadas (huecos entre segmentos) y bloques de subtítulos
    kp = ease_out((t - PS0 - 1.3) / 0.4)
    segs = TM["segments"]
    if kp > 0:
        for a, b in zip(segs, segs[1:]):
            xm = x0 + (x1 - x0) * ((a["t1"] + b["t0"]) / 2) / span
            d.line([(xm, yc - 95), (xm, yc + 95)], fill=YELLOW + (int(A * kp),), width=5)
            d.polygon([(xm - 12, yc - 110), (xm + 12, yc - 110), (xm, yc - 92)], fill=YELLOW + (int(A * kp),))
    kb = ease_out((t - PS0 - 2.2) / 0.5)
    if kb > 0:
        for i, s in enumerate(segs):
            xa = x0 + (x1 - x0) * s["t0"] / span + 3
            xb = x0 + (x1 - x0) * s["t1"] / span - 3
            yb = yc + 135 + (i % 2) * 38
            d.rounded_rectangle([xa, yb - 15, xb, yb + 15], 10, fill=(WHITE if i % 2 else YELLOW) + (int(A * kb),))
        txt(d, (W / 2, yc + 260), "cada subtítulo, justo a tiempo", 46, CYAN, int(A * kb), "Inter-ExtraBold.otf", 6)
    # cabezal que recorre la línea
    ph = x0 + (x1 - x0) * min(1.0, max(0.0, (t - PS0) / (PS1 - PS0)))
    d.line([(ph, yc - 105), (ph, yc + 105)], fill=WHITE + (A,), width=4)


def draw_verified(layer, t):
    al = fade(t, CIA[0] + 0.1, CIA[1] + 0.25, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - ease_out((t - CIA[0]) / 0.3)) * 24
    txt(d, (W / 2, 400 + rise), "CADA PALABRA", 96, WHITE, A)
    k = ease_out((t - (CIA[0] + 0.5 * (CIA[1] - CIA[0]))) / 0.3)
    if k > 0:
        a2 = int(A * k)
        f = font("Inter-Black.otf", 68)
        s = "DATO VERIFICADO"
        tw = d.textlength(s, font=f)
        d.rounded_rectangle([W / 2 - tw / 2 - 110, 480 + rise, W / 2 + tw / 2 + 40, 580 + rise], 50, fill=YELLOW + (a2,), outline=INK + (a2,), width=6)
        check(d, W / 2 - tw / 2 - 55, 530 + rise, 48, INK, a2)
        d.text((W / 2 + 35, 530 + rise), s, font=f, fill=INK + (a2,), anchor="mm")


def draw_next(layer, t):
    al = fade(t, CIB[0] - 0.15, CARD + 0.1, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    txt(d, (W / 2, 390), "PARTE 3", 128, YELLOW, A)
    txt(d, (W / 2, 505), "ANIMACIÓN 3D", 92, WHITE, A)
    # cubo de alambre que gira (adelanto del motor 3D)
    k = ease_out((t - CIB[0] + 0.15) / 0.4)
    a = 1.3 * t; b = 0.5
    V = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
    V = rot_x(rot_y(V, a), b)
    s = 85 * k
    P = [(W / 2 + v[0] * s * (1 + 0.15 * v[2]), 665 - v[1] * s * (1 + 0.15 * v[2])) for v in V]
    for i in range(8):
        for j in range(i + 1, 8):
            if bin(i ^ j).count("1") == 1:
                d.line([P[i], P[j]], fill=CYAN + (A,), width=5)
    late = int(A * min(1.0, max(0.0, (t - (CIB[0] + 0.45 * (CIB[1] - CIB[0]))) / 0.3)))
    txt(d, (W / 2, 830), "¡ESTÉN ATENTOS!", 76, WHITE, late)


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
    txt(d, (W / 2, 1100), "Síguenos: mañana la parte 3", 50, CYAN, A, "Inter-ExtraBold.otf", 6)
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


def overlays(frame_u8, t, O, R, star_r):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_waves(layer, t, O, R, star_r)
    draw_hook(layer, t)
    draw_sources(layer, t)
    draw_script(layer, t)
    draw_voice(layer, t)
    draw_takes(layer, t)
    draw_github(layer, t)
    draw_timeline(layer, t)
    draw_verified(layer, t)
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
    O, R = camera(t)
    img = BG.copy()
    bs = bodies(t)
    bs.sort(key=lambda b: -float(np.linalg.norm(np.asarray(b["c"]) - O)))
    for b in bs:
        draw_sphere(img, O, b, t, R)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, O, R, bs and [b for b in bs if b["kind"] == "star"][0]["r"])


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
        print("frames", NFRAMES, "end", END, "card", CARD, "elige", round(ELIGE_T, 2), "fuentes", [round(x, 2) for x in SRC_T])
