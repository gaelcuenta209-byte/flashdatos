"""Flash Datos · video 31: una teoría dice que el universo tiene el doble de edad (26,700 millones de años).

Escena nueva (galaxias de partículas): reloj cósmico que marca 13.8 y salta a 26.7 sobre una espiral que gira;
túnel del tiempo con anillos de miles de millones de años hasta el Big Bang, que se aleja al doble; galaxia con
halo violeta de materia oscura que se deshace mientras la galaxia sigue girando; constantes físicas flotantes y
una onda de luz que se estira y enrojece ("luz cansada"); 175 mini galaxias que se encienden una por una y los
primeros elementos (H, He, Li) saliendo del Big Bang; el espejo dorado del James Webb frente a una galaxia
temprana gigante; una esfera con el fondo cósmico de microondas y regreso al reloj con la edad oficial.

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


def rotm(yaw, pitch=0.0, roll=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch); cr, sr = math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


# ---------------- fondo ----------------
def make_background():
    rng = np.random.default_rng(31)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1800
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.02 + 0.42 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 40
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.4 + 2.6 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    gy, gx = np.mgrid[0:120, 0:68] / 40.0
    neb = fbm(gx, gy, np.full_like(gx, 3.1), 5, seed=31)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.014, 0.014, 0.050], np.float32)
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


# ---------------- partículas ----------------
class Buf:
    """Acumula partículas: capa nítida (resolución completa) y capa de brillo (1/4)."""

    def __init__(self):
        self.sharp = np.zeros((H, W, 3), np.float32)
        self.soft = np.zeros((H // 4, W // 4, 3), np.float32)

    def add(self, cam, P, col, w=1.0, glow=0.35, near=0.05):
        x, y, z = cam.proj(P)
        ok = (z > near) & (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
        if not ok.any():
            return
        x, y, z = x[ok], y[ok], z[ok]
        c = np.broadcast_to(np.asarray(col, np.float32), (len(ok), 3))[ok]
        ww = np.broadcast_to(np.asarray(w, np.float32), (len(ok),))[ok]
        cw = c * ww[:, None]
        # reparto bilineal para que las partículas no "salten" de píxel en píxel
        xi = np.floor(x).astype(np.int64); yi = np.floor(y).astype(np.int64)
        fx = (x - xi).astype(np.float32)[:, None]; fy = (y - yi).astype(np.float32)[:, None]
        np.add.at(self.sharp, (yi, xi), cw * (1 - fx) * (1 - fy))
        np.add.at(self.sharp, (yi, xi + 1), cw * fx * (1 - fy))
        np.add.at(self.sharp, (yi + 1, xi), cw * (1 - fx) * fy)
        np.add.at(self.sharp, (yi + 1, xi + 1), cw * fx * fy)
        if glow > 0:
            np.add.at(self.soft, (np.clip(yi // 4, 0, H // 4 - 1), np.clip(xi // 4, 0, W // 4 - 1)), cw * glow)

    def into(self, img):
        img += gaussian_filter(self.sharp, (0.75, 0.75, 0))
        g = gaussian_filter(self.soft, (1.6, 1.6, 0)) * 0.10 + gaussian_filter(self.soft, (6, 6, 0)) * 0.05
        img += ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def make_galaxy(n, R, arms, seed, twist=2.6, warm=0.0):
    rng = np.random.default_rng(seed)
    nb = int(n * 0.22); nd = n - nb
    r = np.clip(rng.exponential(R / 3.2, nd), 0.03 * R, 1.25 * R)
    arm = rng.integers(0, arms, nd)
    th = arm * 2 * np.pi / arms + twist * np.log(r / R + 0.08) + rng.normal(0, 0.28, nd) * (0.5 + r / R)
    y = rng.normal(0, 0.035 * R, nd) * np.exp(-r / R)
    rb = np.abs(rng.normal(0, 0.13 * R, nb))
    thb = rng.random(nb) * 2 * np.pi
    yb = rng.normal(0, 0.09 * R, nb)
    rr = np.concatenate([r, rb]); tt = np.concatenate([th, thb]); yy = np.concatenate([y, yb])
    col = np.zeros((n, 3), np.float32)
    k = (rr / R)[:, None]
    disk = np.array([0.55, 0.70, 1.0]) * (1 - warm) + np.array([1.0, 0.55, 0.35]) * warm
    core = np.array([1.0, 0.80, 0.52])
    col[:] = core * np.exp(-k * 4) + disk * (1 - np.exp(-k * 4))
    pink = rng.random(n) < 0.035
    col[pink] = np.array([1.0, 0.40, 0.62])
    w = (0.55 + 0.9 * rng.random(n) ** 3).astype(np.float32)
    w[nd:] *= 1.25
    return dict(r=rr.astype(np.float32), th=tt.astype(np.float32), y=yy.astype(np.float32), col=col, w=w, R=R)


def galaxy_points(g, t, omega=0.55, R=np.eye(3), pos=(0, 0, 0), scale=1.0):
    # curva de rotación casi plana: la velocidad angular baja con el radio
    ang = g["th"] + omega * t / np.sqrt(g["r"] / g["R"] + 0.12)
    P = np.stack([g["r"] * np.cos(ang), g["y"], g["r"] * np.sin(ang)], -1) * scale
    return P @ R.T + np.asarray(pos, float)


def bloom(img):
    small = img[::4, ::4]
    br = np.clip(small - 0.85, 0, None)
    g = gaussian_filter(br, (5, 5, 0)) * 0.55 + gaussian_filter(br, (22, 22, 0)) * 0.8 + gaussian_filter(br, (60, 60, 0)) * 0.45
    return img + ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)


def burst(img, cam, P, s, col=(1.0, 0.85, 0.6)):
    x, y, z = cam.proj(P)
    if z[0] <= 0 or s <= 0:
        return
    small = np.zeros((H // 4, W // 4, 3), np.float32)
    xi, yi = int(x[0] / 4), int(y[0] / 4)
    if 0 <= xi < W // 4 and 0 <= yi < H // 4:
        small[yi, xi] = np.array(col) * s * 900
        g = gaussian_filter(small, (2.5, 2.5, 0)) + gaussian_filter(small, (12, 12, 0)) * 0.6
        img += ndzoom(g, (4, 4, 1), order=1)[:H, :W]


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
CARD = S1["cierre"] + 0.15
END = TM["end"]
NFRAMES = int(round(END * FPS))

TJUMP = 7.30                     # "casi el doble": el reloj se rompe
TCMB_OUT = 58.60                 # del fondo cósmico al reloj final
SHOTS = [("gancho", 0.0), ("cifra", S0["cifra"] - 0.2), ("oscuro", S0["oscuro"] - 0.2), ("idea", S0["idea"] - 0.2),
         ("pruebas", S0["pruebas"] - 0.2), ("webb", S0["webb"] - 0.2), ("cmb", S0["cierre"] - 0.2), ("final", TCMB_OUT)]
FL = [b for _, b in SHOTS[1:]]


def shot(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s[1]:
            cur = s
    return cur


FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); RED = (255, 90, 70); ORANGE = (255, 160, 70)
VIOLET = (190, 120, 255); GREEN = (110, 235, 140)


def groups_for_part(t0, t1, text):
    words = text.split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w[-1] in ".,:…?!" or len(" ".join(cur)) > 17:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    weights = [sum(len(w) for w in g) + 2 + (5 if g[-1][-1] in ".,:…" else 0) for g in groups]
    tot = sum(weights); t = t0; out = []
    for g, wt in zip(groups, weights):
        dur = (t1 - t0) * wt / tot
        out.append([t, t + dur, g]); t += dur
    return out


# pausas reales de la voz dentro de cada segmento (para que los subtítulos no se adelanten)
CUTS = {"gancho": [(4.51, 5.16)], "cifra": [(10.98, 11.09), (12.48, 12.95)], "oscuro": [(18.48, 19.01), (22.59, 22.98)],
        "idea": [(26.53, 26.99), (30.34, 30.88)], "pruebas": [(38.91, 39.01)], "webb": [(46.31, 46.46), (47.68, 48.06)],
        "cierre": [(51.26, 51.77), (53.28, 53.66), (55.80, 56.31), (58.25, 58.83)]}
SPLITS = {"gancho": ["años…"], "cifra": ["GUPTA,", "OTTAWA,"], "oscuro": ["loco:", "OSCURA,"],
          "idea": ["lugar,", "tiempo…"], "pruebas": ["GALAXIAS"], "webb": ["que,", "actual,"],
          "cierre": ["OJO:", "MINORITARIA", "difícil,", "microondas."]}

CAPS = []
for s in TM["segments"]:
    for t0, t1, txt_ in s["parts"]:
        words = txt_.split()
        cuts = CUTS.get(s["id"], []); marks = SPLITS.get(s["id"], [])
        pieces, cur, mi = [], [], 0
        for w in words:
            cur.append(w)
            if mi < len(marks) and w == marks[mi]:
                pieces.append(cur); cur = []; mi += 1
        if cur:
            pieces.append(cur)
        if len(pieces) != len(cuts) + 1:
            CAPS += groups_for_part(t0, t1, txt_)
            continue
        a = t0
        for k, p in enumerate(pieces):
            b = cuts[k][0] if k < len(cuts) else t1
            CAPS += groups_for_part(a, b, " ".join(p))
            if k < len(cuts):
                a = cuts[k][1]
for i in range(len(CAPS) - 1):
    if CAPS[i + 1][0] - CAPS[i][1] < 0.7:
        CAPS[i][1] = CAPS[i + 1][0]


def is_hl(w):
    core = w.strip(".,:…?¿!¡()")
    return any(ch.isdigit() for ch in core) or (core.isupper() and len(core) > 1)


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
            x = W / 2 - total / 2; y = 1340
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
    d.text(xy, s, font=font(fn, size), fill=col + (int(A),), anchor=anchor, stroke_width=sw, stroke_fill=(8, 10, 20, int(A)))


def draw_label(layer, t, a, b, title, subs, title_col=WHITE, title_size=112, y0=370, sub_col=CYAN):
    al = fade(t, a, b)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - min(1.0, (t - a) / 0.3)) * 24
    y = y0 + rise
    f = font("Inter-Black.otf", title_size)
    tw = d.textlength(title, font=f)
    if tw > W - 70:
        title_size = int(title_size * (W - 70) / tw)
    txt(d, (W / 2, y), title, title_size, title_col, A)
    y += title_size * 0.5 + 44
    for s in subs:
        txt(d, (W / 2, y), s, 54, sub_col, A, "Inter-ExtraBold.otf", 7)
        y += 70


def check(d, x, y, s, col, A, wd=10):
    d.line([(x - s * 0.5, y), (x - s * 0.15, y + s * 0.38), (x + s * 0.55, y - s * 0.42)], fill=col + (int(A),), width=wd, joint="curve")


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


# ---------------- objetos de la escena ----------------
GAL_MAIN = make_galaxy(110000, 10.0, 2, seed=1, twist=2.4)
GAL_DM = make_galaxy(90000, 10.0, 4, seed=2, twist=2.0)
GAL_EARLY = make_galaxy(80000, 10.0, 3, seed=5, twist=1.6, warm=0.75)
GAL_SRC = make_galaxy(9000, 1.0, 2, seed=8)

rng_h = np.random.default_rng(11)
_nh = 45000
_u = rng_h.normal(0, 1, (_nh, 3)); _u /= np.linalg.norm(_u, axis=1, keepdims=True)
_rh = 30.0 * np.sqrt(rng_h.random(_nh)) ** 1.6 + 2.0
HALO = (_u * _rh[:, None]).astype(np.float32)
HALO_W = (0.35 + 0.65 * rng_h.random(_nh) ** 2).astype(np.float32) * np.exp(-_rh / 26.0).astype(np.float32)
HALO_V = rng_h.normal(0, 1, (_nh, 3)).astype(np.float32)

# 175 mini galaxias
rng_m = np.random.default_rng(175)
MINI_POS = np.stack([rng_m.uniform(-14, 14, 175), rng_m.uniform(-24, 24, 175), rng_m.uniform(-40, -8, 175)], -1)
MINI_ORDER = rng_m.permutation(175)
MINI_R = [rotm(rng_m.uniform(0, 6.3), rng_m.uniform(-1.3, 1.3), rng_m.uniform(-0.5, 0.5)) for _ in range(175)]
MINI_G = [make_galaxy(500, 1.0, int(rng_m.integers(2, 4)), seed=100 + i, twist=2.2, warm=float(rng_m.random() * 0.5)) for i in range(175)]

# túnel del tiempo: anillos cada mil millones de años
GYR = 2.0
RING_N = 520
_ra = np.linspace(0, 2 * np.pi, RING_N, endpoint=False)
RING = np.stack([np.cos(_ra), np.sin(_ra), np.zeros_like(_ra)], -1) * 2.4
rng_t = np.random.default_rng(4)
DUST = np.stack([rng_t.normal(0, 3.0, 6000), rng_t.normal(0, 3.0, 6000), -rng_t.uniform(0, 26.7 * GYR, 6000)], -1)

# fondo cósmico de microondas (textura procedural, colores tipo Planck)
_ty, _tx = np.mgrid[0:256, 0:512]
_lat = (0.5 - (_ty + 0.5) / 256) * np.pi; _lon = ((_tx + 0.5) / 512 * 2 - 1) * np.pi
_vx, _vy, _vz = np.cos(_lat) * np.sin(_lon), np.sin(_lat), np.cos(_lat) * np.cos(_lon)
_n = fbm(_vx * 6 + 9, _vy * 6, _vz * 6, 6, seed=3)
_n = (_n - _n.mean()) / _n.std()
_cm = np.array([[0.02, 0.05, 0.45], [0.10, 0.45, 0.95], [0.85, 0.90, 0.95], [1.0, 0.70, 0.20], [0.85, 0.18, 0.05]])
_x = np.clip((_n + 2.2) / 4.4, 0, 1) * 4
_i = np.clip(np.floor(_x).astype(int), 0, 3); _f = (_x - _i)[..., None]
CMB = (_cm[_i] * (1 - _f) + _cm[_i + 1] * _f).astype(np.float32) ** 2.2


def draw_cmb_sphere(img, cam, C, r, t, k=1.0):
    C = np.asarray(C, float)
    x, y, z = cam.proj(C)
    if z[0] <= 0:
        return
    rpx = r / z[0] / PIX * 1.25 + 4
    x0 = int(max(0, x[0] - rpx)); x1 = int(min(W, x[0] + rpx)); y0 = int(max(0, y[0] - rpx)); y1 = int(min(H, y[0] + rpx))
    if x0 >= x1 or y0 >= y1:
        return
    d = cam.dirs(y0, y1, x0, x1)
    oc = cam.O - C
    b = d @ oc
    perp2 = np.maximum(oc @ oc - b * b, 0)
    dist = np.sqrt(perp2)
    pixw = np.maximum(-b, 1e-9) * PIX
    alpha = np.clip((r - dist) / pixw + 0.5, 0, 1)
    region = img[y0:y1, x0:x1]
    halo = np.exp(-np.maximum(dist - r, 0) / (0.022 * r)) * (dist > r)
    region += (halo * 0.25 * k)[..., None] * np.array([0.5, 0.6, 1.0], np.float32)
    sel = alpha > 0
    if not sel.any():
        return
    tt = -b[sel] - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = cam.O + tt[:, None] * d[sel]
    nrm = (P - C) / r
    a = 0.18 * t
    lx = nrm[:, 0] * math.cos(a) + nrm[:, 2] * math.sin(a); lz = -nrm[:, 0] * math.sin(a) + nrm[:, 2] * math.cos(a)
    lat = np.arcsin(np.clip(nrm[:, 1], -1, 1)); lon = np.arctan2(lx, lz)
    col = sample(CMB, lat, lon)
    mu = np.clip(-(nrm * d[sel]).sum(-1), 0, 1)
    col = col * (0.35 + 0.85 * mu ** 0.5)[:, None] * 0.9 * k
    al = alpha[sel][:, None] * k
    region[sel] = region[sel] * (1 - al) + col * al


# ---------------- reloj cósmico (capa 2D) ----------------
def draw_clock(layer, t, value, A, broken=0.0, col_num=YELLOW, cy=830, R=290, sub="MIL MILLONES DE AÑOS", hand_turns=0.0):
    if A <= 0:
        return
    d = ImageDraw.Draw(layer)
    cx = W / 2
    S2 = 2
    big = Image.new("RGBA", (int(2 * R + 80) * S2, int(2 * R + 80) * S2), (0, 0, 0, 0))
    bd = ImageDraw.Draw(big)
    o = (R + 40) * S2
    bd.ellipse([o - R * S2, o - R * S2, o + R * S2, o + R * S2], fill=(6, 10, 26, int(A * 0.62)), outline=CYAN + (int(A),), width=7 * S2)
    bd.ellipse([o - (R - 26) * S2, o - (R - 26) * S2, o + (R - 26) * S2, o + (R - 26) * S2], outline=CYAN + (int(A * 0.35),), width=2 * S2)
    for i in range(60):
        a = i / 60 * 2 * math.pi
        L = 30 if i % 5 == 0 else 13
        wd = 6 if i % 5 == 0 else 3
        r0 = R - 10; r1 = R - 10 - L
        bd.line([(o + r0 * S2 * math.sin(a), o - r0 * S2 * math.cos(a)), (o + r1 * S2 * math.sin(a), o - r1 * S2 * math.cos(a))], fill=WHITE + (int(A * 0.85),), width=wd * S2)
    ha = 2 * math.pi * (hand_turns + t * 0.08)
    hl = (R - 60) * S2
    bd.line([(o, o), (o + hl * math.sin(ha), o - hl * math.cos(ha))], fill=YELLOW + (int(A * 0.55),), width=6 * S2)
    if broken > 0:
        rng = np.random.default_rng(7)
        for j in range(7):
            a = rng.uniform(0, 2 * math.pi); pts = [(o + R * S2 * math.sin(a), o - R * S2 * math.cos(a))]
            rad = R
            L = (0.25 + 0.5 * rng.random()) * R * broken
            while R - rad < L:
                rad -= 22 + 30 * rng.random(); a += rng.normal(0, 0.10)
                pts.append((o + rad * S2 * math.sin(a), o - rad * S2 * math.cos(a)))
            bd.line(pts, fill=(255, 255, 255, int(A * min(1, broken * 2))), width=4 * S2)
    big = big.resize((int(2 * R + 80), int(2 * R + 80)), Image.LANCZOS)
    layer.alpha_composite(big, (int(cx - R - 40), int(cy - R - 40)))
    txt(d, (cx, cy - 30), value, 168, col_num, A, sw=10)
    txt(d, (cx, cy + 95), sub, 40, WHITE, A, "Inter-ExtraBold.otf", 6)


# ---------------- espejo del James Webb ----------------
def hex_centers():
    out = []
    for q in range(-2, 3):
        for r in range(-2, 3):
            s = -q - r
            if max(abs(q), abs(r), abs(s)) <= 2 and (q, r) != (0, 0):
                out.append((1.5 * q, math.sqrt(3) * (r + q / 2)))
    return out


HEX = hex_centers()


def draw_jwst(layer, cam, C, Rm, t, A):
    if A <= 0:
        return
    C = np.asarray(C, float)
    e1 = Rm[:, 0]; e2 = Rm[:, 1]; nrm = Rm[:, 2]
    S = 0.98
    polys = []
    viewdir = cam.O - C; viewdir /= np.linalg.norm(viewdir)
    for i, (hx, hy) in enumerate(HEX):
        cc = C + e1 * hx + e2 * hy
        # superficie ligeramente cóncava: cada hexágono inclinado hacia el centro
        n_i = nrm - 0.04 * (e1 * hx + e2 * hy); n_i /= np.linalg.norm(n_i)
        V = [cc + S * (e1 * math.cos(k * math.pi / 3) + e2 * math.sin(k * math.pi / 3)) for k in range(6)]
        x, y, z = cam.proj(np.array(V))
        if (z <= 0).any():
            continue
        L = np.array([-0.5, 0.6, 0.62]); L /= np.linalg.norm(L)
        h = L + viewdir; h /= np.linalg.norm(h)
        sp = max(0.0, float(n_i @ h)) ** 30
        sweep = math.exp(-((hx + hy * 0.4) - (t * 2.2 % 12 - 6)) ** 2 / 2.0)
        base = 0.55 + 0.25 * max(0.0, float(n_i @ L))
        b = min(1.0, base + 0.9 * sp + 0.35 * sweep)
        colr = (int(255 * min(1, 0.98 * b + 0.05)), int(255 * min(1, 0.72 * b + 0.04)), int(255 * min(1, 0.22 * b)))
        polys.append((float(z.mean()), list(zip(x, y)), colr))
    d = ImageDraw.Draw(layer)
    # puntales y espejo secundario
    sec = C + nrm * 4.6
    xs_, ys_, zs_ = cam.proj(np.array([sec] + [C + 3.2 * (e1 * math.cos(a) + e2 * math.sin(a)) for a in (math.pi / 2, math.pi / 2 + 2.09, math.pi / 2 + 4.19)]))
    for poly in sorted(polys, key=lambda p: -p[0]):
        d.polygon(poly[1], fill=poly[2] + (int(A),), outline=(60, 40, 10, int(A)))
    if (zs_ > 0).all():
        for k in range(1, 4):
            d.line([(xs_[0], ys_[0]), (xs_[k], ys_[k])], fill=(150, 150, 160, int(A)), width=6)
        rr = 12
        d.ellipse([xs_[0] - rr, ys_[0] - rr, xs_[0] + rr, ys_[0] + rr], fill=(230, 190, 90, int(A)))


# ---------------- render ----------------
def ring_pos(gyr):
    return -gyr * GYR


def bb_depth(t):
    s = ease((t - 12.95) / 2.3)
    return 13.8 + (26.7 - 13.8) * s


def cam_for(name, t):
    if name in ("gancho", "final"):
        a = 0.35 + 0.025 * t
        return Cam((math.sin(a) * 30, 15 + 0.0 * t, math.cos(a) * 30), (0, -3, 0))
    if name == "cifra":
        s = (t - S0["cifra"]) / (S0["oscuro"] - S0["cifra"])
        z = 6.0 - 10.0 * ease(s)
        return Cam((1.0, 0.3, z), (0, 0.15, z - 30), roll=0.05 * math.sin(t * 0.5))
    if name == "oscuro":
        s = (t - S0["oscuro"]) / (S0["idea"] - S0["oscuro"])
        a = 0.9 + 0.35 * s
        D = 78 - 18 * ease(s)
        return Cam((math.sin(a) * D, 0.55 * D, math.cos(a) * D), (0, -4, 0))
    if name == "idea":
        s = (t - S0["idea"]) / (S0["pruebas"] - S0["idea"])
        return Cam((-1.0 + 2.0 * s, 0.6, 13.0 - 2.0 * s), (0, -0.4, -6))
    if name == "pruebas":
        s = (t - S0["pruebas"]) / (S0["webb"] - S0["pruebas"])
        return Cam((2.0 - 4.0 * s, 0.5, 18.0 - 8.0 * ease(s)), (0, 0, -24))
    if name == "webb":
        s = (t - S0["webb"]) / (S0["cierre"] - S0["webb"])
        return Cam((-3.0 + 1.5 * s, -2.0 + 1.0 * s, 16.0 - 3.0 * s), (0.6, 2.2, -60))
    if name == "cmb":
        s = (t - S0["cierre"]) / (TCMB_OUT - S0["cierre"])
        return Cam((0, 0, 30 - 6 * ease(s)), (0, 0, 0))
    return Cam((0, 0, 30), (0, 0, 0))


CONSTS = [("c", "velocidad de la luz", (-2.0, 2.0, -4)), ("G", "gravedad", (2.0, 1.4, -6)), ("α", "estructura fina", (-1.9, -0.5, -5)), ("h", "constante de Planck", (1.8, -0.9, -3.5))]


def scene(t):
    name, ts = shot(t)
    cam = cam_for(name, t)
    img = BG.copy()
    buf = Buf()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    if name in ("gancho", "final"):
        R = rotm(0.0, 0.18)
        buf.add(cam, galaxy_points(GAL_MAIN, t, 0.30, R, (0, -3, 0)), GAL_MAIN["col"], GAL_MAIN["w"] * 0.11)
        buf.into(img)
        if name == "gancho":
            A = 255 * min(1.0, (t + 0.3) / 0.4)
            br = smooth(TJUMP - 0.1, TJUMP + 0.5, t)
            if t < TJUMP:
                val, coln = "13.8", YELLOW
            else:
                s = ease((t - TJUMP) / 1.1)
                val = f"{13.8 + (26.7 - 13.8) * s:.1f}"; coln = tuple(int(c) for c in lerp(YELLOW, ORANGE, s))
            draw_clock(layer, t, val, A, broken=br, col_num=coln, hand_turns=3.0 * ease((t - TJUMP) / 1.2))
            draw_label(layer, t, 0.0, S0["cifra"] - 0.15, "EDAD DEL UNIVERSO", [], WHITE, 74, y0=420)
            if t > TJUMP + 0.2:
                al = fade(t, TJUMP + 0.2, S0["cifra"] + 0.2, 0.2)
                txt(d, (W / 2, 1185), "¿CASI EL DOBLE?", 66, ORANGE, 255 * al)
        else:
            A = 255 * min(1.0, (t - TCMB_OUT) / 0.3)
            draw_clock(layer, t, "13.8", A, col_num=YELLOW)
            draw_label(layer, t, TCMB_OUT + 0.1, CARD, "EDAD OFICIAL", ["la teoría de 26.7 aún no se acepta"], GREEN, 92, y0=410)
    elif name == "cifra":
        bb = bb_depth(t)
        for g in range(0, 27):
            if g > bb + 0.01:
                break
            z = ring_pos(g)
            col = (0.45, 0.8, 1.0) if g <= 13.8 else (1.0, 0.65, 0.25)
            w = 0.35 if g % 5 else 0.9
            buf.add(cam, RING * (1.0 if g % 5 else 1.15) + np.array([0, 0, z]), col, w, glow=0.5)
        # anillo del modelo actual (13.8)
        k13 = 1.0 if bb < 14.2 else 0.55
        buf.add(cam, RING * 1.3 + np.array([0, 0, ring_pos(13.8)]), (1.0, 0.35, 0.3), 1.1 * k13, glow=0.6)
        m = DUST[:, 2] > ring_pos(bb)
        buf.add(cam, DUST[m], (0.55, 0.65, 1.0), 0.18, glow=0.2)
        buf.into(img)
        burst(img, cam, np.array([[0, 0, ring_pos(bb)]]), 0.55 + 0.12 * math.sin(t * 9), (1.0, 0.9, 0.7))
        # etiquetas en los anillos
        for g, lab, col in ((5, "hace 5", WHITE), (13.8, "13.8 · modelo actual", RED), (20, "hace 20", ORANGE)):
            if g > bb:
                continue
            x, y, z = cam.proj(np.array([[0.0, 2.4 * (1.3 if g == 13.8 else 1.15), ring_pos(g)]]))
            if z[0] > 0.5 and 60 < x[0] < W - 60 and 600 < y[0] < 1240:
                al = 255 * min(1.0, max(0.0, 1.6 - z[0] / 30))
                txt(d, (x[0], y[0] - 30), lab, 40 if g != 13.8 else 44, col, al, "Inter-ExtraBold.otf", 6)
        x, y, z = cam.proj(np.array([[0, 0.9, ring_pos(bb)]]))
        if z[0] > 0:
            txt(d, (x[0], y[0] - 40), "BIG BANG", 46, YELLOW, 230, "Inter-Black.otf", 7)
        draw_label(layer, t, S0["cifra"] + 0.1, 12.85, "RAJENDRA GUPTA", ["Universidad de Ottawa", "modelo CCC+TL"], WHITE, 96)
        if t > 12.95:
            al = fade(t, 12.95, S0["oscuro"] + 0.3, 0.25)
            k = ease((t - 12.95) / 2.3)
            draw_label(layer, t, 12.95, S0["oscuro"] + 0.3, f"{int(round((13.8 + 12.9 * k) * 10)) * 100:,} MILLONES", ["de años, según esta teoría"], YELLOW, 104)
    elif name == "oscuro":
        R = rotm(0.3, 0.42)
        buf.add(cam, galaxy_points(GAL_DM, t, 0.45, R, (0, -4, 0)), GAL_DM["col"], GAL_DM["w"] * 0.10)
        dis = smooth(19.4, 21.8, t)
        if dis < 1:
            P = HALO * (1 + 0.8 * dis) + HALO_V * (dis * 9.0) + np.array([0, -4, 0])
            buf.add(cam, P, (0.55, 0.25, 1.0), HALO_W * 0.20 * (1 - dis) * (0.85 + 0.15 * math.sin(t * 3)), glow=0.9)
        buf.into(img)
        draw_label(layer, t, S0["oscuro"] + 0.05, 19.45, "MATERIA OSCURA", ["el halo invisible que \"sostiene\"", "a las galaxias"], VIOLET, 100)
        draw_label(layer, t, 19.55, 22.85, "NO LA NECESITA", ["ni materia oscura", "ni energía oscura"], RED, 104)
        draw_label(layer, t, 22.95, S0["idea"] + 0.3, "NUNCA DETECTADAS", ["directamente"], WHITE, 98)
        if 19.55 < t < 22.85:
            al = fade(t, 19.55, 22.85, 0.2)
            x, y, z = cam.proj(np.array([[0, -4, 0]]))
            s = 120 * ease_out((t - 19.55) / 0.3)
            d.line([(x[0] - s, y[0] - s), (x[0] + s, y[0] + s)], fill=RED + (int(150 * al),), width=14)
            d.line([(x[0] - s, y[0] + s), (x[0] + s, y[0] - s)], fill=RED + (int(150 * al),), width=14)
    elif name == "idea":
        tw = 30.6
        if t < tw:
            buf.add(cam, DUST[::3] * np.array([2.5, 2.5, 0.35]) + np.array([0, 0, 4]), (0.5, 0.6, 1.0), 0.12, glow=0.2)
            buf.into(img)
            for i, (sym, nm, p) in enumerate(CONSTS):
                p = np.array(p) + np.array([0.15 * math.sin(t * 0.9 + i), 0.12 * math.cos(t * 0.7 + i * 2), 0])
                x, y, z = cam.proj(p[None])
                al = 255 * fade(t, S0["idea"] + 0.2 + 0.25 * i, tw, 0.25)
                sz = int(2700 / z[0])
                wob = 0.5 + 0.5 * math.sin(t * (2.0 + i * 0.6) + i)
                txt(d, (x[0], y[0]), sym, sz, YELLOW if i % 2 == 0 else CYAN, al, sw=8)
                bw = 170
                d.rounded_rectangle([x[0] - bw / 2, y[0] + sz * 0.62, x[0] + bw / 2, y[0] + sz * 0.62 + 16], 8, outline=WHITE + (int(al * 0.8),), width=3)
                d.rounded_rectangle([x[0] - bw / 2, y[0] + sz * 0.62, x[0] - bw / 2 + bw * (0.25 + 0.6 * wob), y[0] + sz * 0.62 + 16], 8, fill=WHITE + (int(al * 0.8),))
                txt(d, (x[0], y[0] + sz * 0.62 + 48), nm, 32, WHITE, al * 0.9, "Inter-ExtraBold.otf", 5)
            draw_label(layer, t, 27.0, tw, "CONSTANTES", ["que cambian con el tiempo"], YELLOW, 110)
        else:
            # onda de luz: sale azul de una galaxia lejana y llega roja, más estirada
            src = np.array([-7.0, 3.0, -16.0]); dst = np.array([5.0, -2.5, 4.0])
            buf.add(cam, galaxy_points(GAL_SRC, t, 0.5, rotm(0.4, 0.9), src, 1.6), GAL_SRC["col"], GAL_SRC["w"] * 0.5)
            prog = ease_out((t - tw) / 2.6)
            u = np.linspace(0, 1, 5000)
            u = u[u <= prog]
            if len(u):
                axis = dst - src; L = np.linalg.norm(axis); ax = axis / L
                side = np.cross(ax, np.array([0, 0, 1.0])); side /= np.linalg.norm(side)
                lam = 0.9 * (1 + 1.6 * u)                      # la longitud de onda se estira
                phase = np.cumsum(2 * np.pi / lam * (L / len(np.linspace(0, 1, 5000))))
                P = src + np.outer(u * L, ax) + np.outer(0.45 * np.sin(phase - t * 8), side)
                col = lerp(np.array([0.35, 0.6, 1.0]), np.array([1.0, 0.25, 0.12]), u[:, None] ** 0.9)
                buf.add(cam, P, col, 0.9 * (1.0 - 0.45 * u), glow=0.8)
            buf.into(img)
            draw_label(layer, t, tw + 0.05, S0["pruebas"] + 0.3, "LUZ CANSADA", ["pierde energía en el viaje", "y se ve más roja"], ORANGE, 112)
    elif name == "pruebas":
        te = 39.0
        if t < te:
            nshow = int(175 * ease_out((t - 34.6) / 3.8)) if t > 34.6 else 0
            for j in range(nshow):
                i = MINI_ORDER[j]
                age = t - (34.6 + 3.8 * j / 175)
                k = min(1.0, max(age, 0) / 0.3)
                g = MINI_G[i]
                buf.add(cam, galaxy_points(g, t + i, 0.9, MINI_R[i], MINI_POS[i]), g["col"], g["w"] * 0.9 * k, glow=0.5)
            buf.into(img)
            al = fade(t, 34.6, te, 0.25)
            A = 255 * al
            txt(d, (W / 2, 400), f"{nshow}", 180, YELLOW, A, sw=10)
            txt(d, (W / 2, 525), "GALAXIAS", 76, WHITE, A)
            txt(d, (W / 2, 600), "su giro, reproducido sin materia oscura", 40, CYAN, A, "Inter-ExtraBold.otf", 6)
            if nshow >= 175:
                check(d, W / 2 + 250, 400, 110, GREEN, A, 16)
        else:
            s = t - te
            burst(img, cam, np.array([[0, 0, -12]]), 3.5 * math.exp(-s / 0.6) + 0.6, (1.0, 0.9, 0.7))
            rng = np.random.default_rng(5)
            dirs = rng.normal(0, 1, (4000, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
            sp = rng.random(4000) ** 0.5
            P = np.array([0, 0, -12]) + dirs * (sp * 9 * ease_out(s / 1.5))[:, None]
            buf.add(cam, P, (1.0, 0.75, 0.45), 0.35 * math.exp(-s / 1.5) + 0.08, glow=0.6)
            buf.into(img)
            els = [("H", "hidrógeno", (-300, 760), CYAN), ("He", "helio", (300, 720), YELLOW), ("Li", "litio", (0, 1020), (255, 140, 200))]
            for i, (sym, nm, (ox, oy), col) in enumerate(els):
                k = ease_out((s - 0.2 - 0.25 * i) / 0.5)
                if k <= 0:
                    continue
                cx = W / 2 + ox * k; cy = 880 + (oy - 880) * k
                A = 255 * min(1.0, k) * fade(t, te, S0["webb"] + 0.3, 0.2)
                r = 92
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(8, 12, 30, int(A * 0.75)), outline=col + (int(A),), width=7)
                txt(d, (cx, cy - 8), sym, 80, col, A, sw=6)
                txt(d, (cx, cy + r + 34), nm, 38, WHITE, A, "Inter-ExtraBold.otf", 5)
            draw_label(layer, t, te + 0.05, S0["webb"] + 0.3, "PRIMEROS ELEMENTOS", ["tras el Big Bang"], WHITE, 92, y0=390)
    elif name == "webb":
        s = (t - S0["webb"]) / (S0["cierre"] - S0["webb"])
        gpos = np.array([0.6, 4.0, -60.0])
        grow = 0.75 + 0.5 * ease(s)
        buf.add(cam, galaxy_points(GAL_EARLY, t, 0.5, rotm(0.6, 1.0), gpos, grow), GAL_EARLY["col"], GAL_EARLY["w"] * 0.13, glow=0.5)
        buf.into(img)
        Rm = rotm(0.38, -0.30) @ np.array([[1, 0, 0], [0, 1, 0], [0, 0, -1.0]])
        draw_jwst(layer, cam, np.array([-3.2, -7.8, -6.0]), Rm, t, 255 * min(1.0, (t - S0["webb"] + 0.2) / 0.3))
        draw_label(layer, t, S0["webb"] + 0.05, 46.3, "JAMES WEBB", ["ve galaxias gigantes", "muy cerca del Big Bang"], YELLOW, 108)
        draw_label(layer, t, 46.4, S0["cierre"] + 0.3, "¿DEMASIADO JÓVENES?", ["para el modelo actual"], ORANGE, 96)
        x, y, z = cam.proj(gpos[None])
        al = fade(t, 42.6, S0["cierre"], 0.3)
        if al > 0 and z[0] > 0:
            rr = 150 * grow + 6 * math.sin(t * 6)
            d.ellipse([x[0] - rr, y[0] - rr, x[0] + rr, y[0] + rr], outline=ORANGE + (int(220 * al),), width=5)
    elif name == "cmb":
        k = min(1.0, (t - S0["cierre"] + 0.2) / 0.4)
        draw_cmb_sphere(img, cam, (0, -0.9, 0), 4.6, t, k)
        draw_label(layer, t, S0["cierre"] + 0.05, 53.5, "TEORÍA MINORITARIA", ["todavía no está aceptada"], RED, 98)
        draw_label(layer, t, 53.6, TCMB_OUT + 0.2, "SU PRUEBA MÁS DIFÍCIL", ["el fondo cósmico de microondas"], WHITE, 84)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    im = Image.fromarray(u8).convert("RGBA")
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


render = scene

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        for ts in sys.argv[2:]:
            t = float(ts)
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, shot(t)[0], flush=True)
    elif mode == "chunk":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(render(f / FPS).tobytes())
            if f % 30 == 0:
                print(f"{out}: {f}/{b}", flush=True)
        p.stdin.close(); p.wait()
        print("listo", out, flush=True)
    elif mode == "info":
        print("frames", NFRAMES)
