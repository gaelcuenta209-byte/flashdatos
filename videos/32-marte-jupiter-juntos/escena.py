"""Flash Datos · video 32: Marte y Júpiter se ven casi pegados en el cielo (15 y 16 de noviembre de 2026).

Escena nueva: cielo de madrugada con silueta de cerros y los dos planetas juntos; la cámara sale al espacio y
recorre la línea de mirada Tierra → Marte → Júpiter (posiciones heliocéntricas reales del 16 nov 2026);
calendario, reloj y brújula hacia el este; un dedo junto a la pareja para medir 1.2°; lupas de telescopio con
Júpiter y Marte en 3D; vista del Sistema Solar con órbitas y distancias (195 y 788 millones de km); pulsos de luz
que tardan 11 y 44 minutos en llegar; regreso al cielo del amanecer.

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
    rng = np.random.default_rng(32)
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
    neb = fbm(gx, gy, np.full_like(gx, 3.1), 5, seed=32)
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

TREVEAL = 5.00                    # "pero entre ellos…": del cielo al espacio
TFINAL = 55.00                    # "Y para verlo…": regreso al cielo
SHOTS = [("cielo", 0.0), ("linea", TREVEAL), ("cuando", S0["cuando"] - 0.2), ("dedo", S0["dedo"] - 0.2), ("cual", S0["cual"] - 0.2),
         ("ilusion", S0["ilusion"] - 0.2), ("luz", S0["luz"] - 0.2), ("cierre", S0["cierre"] - 0.2), ("final", TFINAL)]
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
CUTS = {"gancho": [(4.53, 5.21)], "cuando": [(11.38, 11.75), (13.99, 14.38)], "dedo": [(20.88, 21.40)],
        "cual": [(26.91, 27.50), (29.81, 30.25)], "ilusion": [(33.64, 34.18), (38.50, 38.84), (42.31, 42.88)],
        "luz": [(48.44, 48.92)], "cierre": [(54.54, 55.16), (57.40, 57.94)]}
SPLITS = {"gancho": ["cielo…"], "cuando": ["AMANECER,", "16,"], "dedo": ["distancia:"],
          "cual": ["JÚPITER."], "ilusion": ["ILUSIÓN.", "nosotros,", "MILLONES:"],
          "luz": ["ojos;"], "cierre": ["Tierra.", "telescopio:"]}

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


# ---------------- texturas ----------------
TEXD = os.path.join(BASE, "tex", "")
JUP = np.clip(np.load(TEXD + "jupiter.npy"), 0, 1).astype(np.float32) ** 2.2
EARTH = np.clip(np.load(TEXD + "earth.npy"), 0, 1).astype(np.float32) ** 2.2


def make_mars():
    ty, tx = np.mgrid[0:256, 0:512]
    lat = (0.5 - (ty + 0.5) / 256) * np.pi; lon = ((tx + 0.5) / 512 * 2 - 1) * np.pi
    vx, vy, vz = np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)
    n1 = fbm(vx * 2.2 + 5, vy * 2.2, vz * 2.2, 6, seed=21)
    n2 = fbm(vx * 7 + 1, vy * 7, vz * 7, 4, seed=22)
    dark = np.clip((n1 - 0.48) * 4.0, 0, 1)                       # regiones oscuras (tipo Syrtis)
    base = np.array([0.80, 0.42, 0.22]) * (1 - dark[..., None] * 0.55)
    base = base * (0.85 + 0.3 * n2[..., None])
    cap = smooth(1.22, 1.36, np.abs(lat)) * (lat > 0) + smooth(1.30, 1.42, np.abs(lat)) * (lat < 0)
    base = base * (1 - cap[..., None]) + np.array([0.95, 0.93, 0.90]) * cap[..., None]
    return np.clip(base, 0, 1).astype(np.float32) ** 2.2


MARS = make_mars()


def sphere(img, cam, C, r, kind, t, light=None, k=1.0, spin=0.0):
    """Esfera con textura. light=None: la luz viene del Sol en el origen."""
    C = np.asarray(C, float)
    x, y, z = cam.proj(C)
    if z[0] <= r * 1.05:
        return
    rpx = r / z[0] / PIX * (3.2 if kind == "sun" else 1.25) + 4
    if rpx < 1.6:
        glow_pt(img, x[0], y[0], {"jup": (1.0, 0.9, 0.7), "mars": (1.0, 0.45, 0.25), "earth": (0.4, 0.6, 1.0), "sun": (1.0, 0.8, 0.5)}[kind], 1.2 * k, 1.0)
        return
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
    if kind == "sun":
        halo = np.exp(-np.maximum(dist - r, 0) / (0.35 * r)) * (dist > r * 0.98)
        region += (halo * 0.55 * k)[..., None] * np.array([1.0, 0.65, 0.25], np.float32)
    elif kind == "earth":
        halo = np.exp(-np.maximum(dist - r, 0) / (0.05 * r)) * (dist > r)
        region += (halo * 0.25 * k)[..., None] * np.array([0.3, 0.55, 1.0], np.float32)
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]
    tt = -b[sel] - np.sqrt(np.maximum(r * r - perp2[sel], 0))
    P = cam.O + tt[:, None] * ds
    n = (P - C) / r
    V = -ds
    mu = np.clip((n * V).sum(-1), 0, 1)
    if kind == "sun":
        col = np.array([1.0, 0.72, 0.35]) * (1.6 * (0.55 + 0.45 * mu ** 0.5))[:, None]
    else:
        if light is None:
            L = -C / max(np.linalg.norm(C), 1e-6)
        else:
            L = np.asarray(light, float); L = L / np.linalg.norm(L)
        ndl = n @ L
        lit = (0.015 + 1.9 * np.clip(ndl, 0, 1) + 0.08 * smooth(-0.15, 0.3, ndl))[:, None]
        a = spin * t
        lx = n[:, 0] * math.cos(a) + n[:, 2] * math.sin(a); lz = -n[:, 0] * math.sin(a) + n[:, 2] * math.cos(a)
        lat = np.arcsin(np.clip(n[:, 1], -1, 1)); lon = np.arctan2(lx, lz)
        tex = {"jup": JUP, "mars": MARS, "earth": EARTH}[kind]
        col = sample(tex, lat, lon) * lit * (0.75 + 0.25 * mu ** 0.5)[:, None]
        if kind == "earth":
            col = col + np.array([0.2, 0.45, 1.0]) * ((1 - mu) ** 2.5 * 1.0 * np.clip(ndl + 0.3, 0, 1))[:, None]
        if kind == "mars":
            col = col + np.array([1.0, 0.55, 0.35]) * ((1 - mu) ** 3 * 0.25 * np.clip(ndl + 0.2, 0, 1))[:, None]
    al = alpha[sel][:, None] * k
    region[sel] = region[sel] * (1 - al) + col * al


def glow_pt(img, x, y, col, amp, size=1.0, spikes=0.0):
    """Punto de luz (planeta visto a simple vista) en la imagen lineal."""
    if not (-80 < x < W + 80 and -80 < y < H + 80):
        return
    R = int(60 * size) + 4
    ix, iy = int(round(x)), int(round(y))
    y0, y1 = max(iy - R, 0), min(iy + R + 1, H); x0, x1 = max(ix - R, 0), min(ix + R + 1, W)
    if y0 >= y1 or x0 >= x1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx = xx - x; dy = yy - y
    r2 = dx * dx + dy * dy
    g = np.exp(-r2 / (2 * (2.2 * size) ** 2)) * 3.0 + np.exp(-r2 / (2 * (7 * size) ** 2)) * 0.45 + np.exp(-r2 / (2 * (22 * size) ** 2)) * 0.10
    if spikes > 0:
        sp = (np.exp(-dy * dy / (2 * 1.1 ** 2)) + np.exp(-dx * dx / (2 * 1.1 ** 2))) * np.exp(-np.sqrt(r2) / (26 * size))
        g = g + sp * spikes
    img[y0:y1, x0:x1] += (g * amp)[..., None] * np.asarray(col, np.float32)


# ---------------- Sistema Solar (posiciones heliocéntricas reales del 16 nov 2026, 02 h UTC) ----------------
SC = 5.0                                      # unidades de escena por UA
def hel(x, y, z=0.0):
    return np.array([x * SC, z * SC, -y * SC])


P_E = hel(0.5905, 0.7934); P_M = hel(-0.4848, 1.5344, 0.044); P_J = hel(-3.7492, 3.7730, 0.0682)
R_E, R_M, R_J, R_S = 0.55, 0.50, 1.55, 0.75   # radios exagerados para que se vean


def orbit_pts(rad, n=1400):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([np.cos(a) * rad * SC, np.zeros_like(a), -np.sin(a) * rad * SC], -1)


ORB_E = orbit_pts(0.989, 900); ORB_M = orbit_pts(1.61, 1200); ORB_J = orbit_pts(5.32, 3200)
SIGHT_DIR = (P_J - P_E) / np.linalg.norm(P_J - P_E)
SIGHT_LEN = float(np.linalg.norm(P_J - P_E))
rng_a = np.random.default_rng(9)
_ast_r = rng_a.uniform(2.2, 3.3, 2600); _ast_a = rng_a.uniform(0, 2 * np.pi, 2600)
AST = np.stack([np.cos(_ast_a) * _ast_r * SC, rng_a.normal(0, 0.08, 2600) * SC, -np.sin(_ast_a) * _ast_r * SC], -1)


def sightline(buf, cam, upto=1.0, w=0.7, dash_t=None):
    u = np.linspace(0, upto, int(1800 * max(upto, 0.05)))
    P = P_E + np.outer(u * SIGHT_LEN, SIGHT_DIR)
    ww = np.full(len(u), w, np.float32)
    if dash_t is not None:
        ww *= (0.45 + 0.55 * (np.sin(u * 160 - dash_t * 10) > 0))
    buf.add(cam, P, (1.0, 0.85, 0.30), ww, glow=0.6)


def solar_system(img, buf, cam, t, orbit_k=1.0, sight=0.0, dash=False):
    buf.add(cam, ORB_E, (0.35, 0.6, 1.0), 0.55 * orbit_k, glow=0.3)
    buf.add(cam, ORB_M, (1.0, 0.45, 0.30), 0.50 * orbit_k, glow=0.3)
    buf.add(cam, ORB_J, (1.0, 0.80, 0.55), 0.45 * orbit_k, glow=0.3)
    buf.add(cam, AST, (0.6, 0.6, 0.65), 0.12 * orbit_k, glow=0.05)
    if sight > 0:
        sightline(buf, cam, sight, 0.8, t if dash else None)
    buf.into(img)
    sphere(img, cam, (0, 0, 0), R_S, "sun", t)
    sphere(img, cam, P_E, R_E, "earth", t, spin=0.3)
    sphere(img, cam, P_M, R_M, "mars", t, spin=0.25)
    sphere(img, cam, P_J, R_J, "jup", t, spin=0.35)


def tag3d(d, cam, P, s, col, A, size=46, dy=-70, fn="Inter-Black.otf", dx=0):
    x, y, z = cam.proj(np.asarray(P, float)[None])
    if z[0] > 0.3 and -100 < x[0] < W + 100:
        xx = min(max(x[0] + dx, 230), W - 230)
        txt(d, (xx, y[0] + dy), s, size, col, A, fn, 7)


# ---------------- cielo de madrugada ----------------
def make_sky():
    yy = (np.arange(H) / H)[:, None, None]
    top = np.array([0.002, 0.004, 0.018]); mid = np.array([0.010, 0.020, 0.075]); low = np.array([0.20, 0.085, 0.035])
    s1 = np.clip(yy / 0.62, 0, 1); s2 = np.clip((yy - 0.62) / 0.33, 0, 1) ** 1.6
    sky = top * (1 - s1) + mid * s1
    sky = sky * (1 - s2) + low * s2
    sky = np.broadcast_to(sky, (H, W, 3)).astype(np.float32).copy()
    sky += BG * 0.55 * (1 - np.clip((yy - 0.55) / 0.3, 0, 1))
    # cerros
    xs_ = np.arange(W)
    gx = xs_ / W * 3.0
    ridge1 = 1580 + 90 * np.array([fbm(np.array([v]), np.array([0.3]), np.array([0.7]), 5, seed=4)[0] for v in gx]) - 40
    ridge2 = 1690 + 70 * np.array([fbm(np.array([v * 1.7]), np.array([2.1]), np.array([0.2]), 5, seed=6)[0] for v in gx]) - 30
    Y = np.arange(H)[:, None]
    m1 = np.clip(Y - ridge1[None, :] + 0.5, 0, 1)
    m2 = np.clip(Y - ridge2[None, :] + 0.5, 0, 1)
    sky = sky * (1 - m1[..., None]) + np.array([0.010, 0.012, 0.024]) * m1[..., None]
    sky = sky * (1 - m2[..., None]) + np.array([0.003, 0.003, 0.008]) * m2[..., None]
    # lucecitas de un pueblo
    rng = np.random.default_rng(12)
    for _ in range(70):
        x = int(rng.uniform(80, W - 80)); y = int(ridge2[x] + rng.uniform(25, 160))
        if y < H - 2:
            sky[y:y + 2, x:x + 2] += np.array([1.0, 0.65, 0.3]) * rng.uniform(0.15, 0.6)
    return sky, ridge1


SKY, RIDGE = make_sky()
PXDEG = 95.0                                     # escala del cielo (más grande que la real, para que se vea)
SKY_J = np.array([590.0, 820.0])
SKY_M = SKY_J + np.array([-1.0, -1.0]) / math.sqrt(2) * 1.2 * PXDEG
SKY_R = SKY_J + np.array([-0.62, 0.78]) * 4.3 * PXDEG   # Régulo, 4.3° abajo a la izquierda


def sky_frame(img, t, zoom=1.0, center=None, dawn=0.0):
    """Cielo con los planetas; zoom alrededor de center (en píxeles)."""
    if center is None:
        center = SKY_J * 0.5 + SKY_M * 0.5
    if zoom == 1.0:
        img[:] = SKY
    else:
        cy, cx = center[1], center[0]
        Y0 = (np.arange(H) - cy) / zoom + cy; X0 = (np.arange(W) - cx) / zoom + cx
        yi = np.clip(Y0.astype(int), 0, H - 1); xi = np.clip(X0.astype(int), 0, W - 1)
        img[:] = SKY[yi][:, xi]
    if dawn > 0:
        yy = (np.arange(H) / H)[:, None, None]
        img += (np.clip((yy - 0.45) / 0.5, 0, 1) ** 2 * dawn)[..., :] * np.array([0.25, 0.12, 0.05], np.float32)

    def tr(p):
        return (p - center) * zoom + center
    j = tr(SKY_J); m = tr(SKY_M); r = tr(SKY_R)
    s = 1.0 + 0.35 * (zoom - 1)
    glow_pt(img, r[0], r[1], (0.75, 0.85, 1.0), 0.20 + 0.04 * math.sin(t * 7.3), 0.8 * s)
    glow_pt(img, m[0], m[1], (1.0, 0.42, 0.20), 0.55, 1.0 * s, spikes=0.0)
    glow_pt(img, j[0], j[1], (1.0, 0.93, 0.80), 2.4, 1.25 * s, spikes=0.9)
    return j, m, r


def leader(d, p, q, col, A, wd=4):
    d.line([tuple(p), tuple(q)], fill=col + (int(A),), width=wd)


def draw_finger(layer, x, ytip, wpx, A):
    d = ImageDraw.Draw(layer)
    col = (46, 34, 32, int(A)); rim = (150, 95, 60, int(A * 0.9))
    half = wpx / 2
    d.rounded_rectangle([x - half, ytip, x + half, H + 40], radius=int(half), fill=col)
    d.line([(x + half - 3, ytip + half), (x + half - 3, H)], fill=rim, width=5)
    # uña y nudillos
    d.rounded_rectangle([x - half * 0.62, ytip + 10, x + half * 0.62, ytip + half * 1.5], radius=int(half * 0.55), outline=(90, 66, 58, int(A)), width=4)
    for k in (2.6, 3.0, 5.4):
        d.arc([x - half * 0.8, ytip + half * k, x + half * 0.8, ytip + half * k + 30], 200, 340, fill=(80, 60, 55, int(A)), width=3)


def clock_icon(d, cx, cy, R, A, hh=5, mm=0):
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(8, 12, 30, int(A * 0.7)), outline=CYAN + (int(A),), width=6)
    for i in range(12):
        a = i / 12 * 2 * math.pi
        d.line([(cx + (R - 8) * math.sin(a), cy - (R - 8) * math.cos(a)), (cx + (R - 20) * math.sin(a), cy - (R - 20) * math.cos(a))], fill=WHITE + (int(A),), width=4)
    ah = (hh % 12 + mm / 60) / 12 * 2 * math.pi; am = mm / 60 * 2 * math.pi
    d.line([(cx, cy), (cx + R * 0.5 * math.sin(ah), cy - R * 0.5 * math.cos(ah))], fill=YELLOW + (int(A),), width=9)
    d.line([(cx, cy), (cx + R * 0.75 * math.sin(am), cy - R * 0.75 * math.cos(am))], fill=WHITE + (int(A),), width=6)


def chip(d, cx, cy, top, big, A, col=YELLOW):
    w, h = 190, 170
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 22, fill=(8, 12, 30, int(A * 0.8)), outline=col + (int(A),), width=5)
    d.rectangle([cx - w / 2 + 3, cy - h / 2 + 3, cx + w / 2 - 3, cy - h / 2 + 46], fill=col + (int(A * 0.9),))
    txt(d, (cx, cy - h / 2 + 25), top, 34, (10, 12, 24), A, "Inter-Black.otf", 0)
    txt(d, (cx, cy + 22), big, 88, WHITE, A, sw=4)


INSET_CAM = Cam((0, 0, 0), (0, 0, -1))


def inset_sphere(img, layer, px, py, rpx, kind, t, A, col):
    """Lupa de telescopio con el planeta en 3D, centrada en (px, py) con radio rpx."""
    if A <= 0:
        return
    D = 40.0
    X = (px / W * 2 - 1) * TX * D; Y = (1 - py / H * 2) * TY * D
    r = rpx * PIX * D * 0.78
    disk = np.zeros((H, W), np.float32)
    yy, xx = np.ogrid[0:H, 0:W]
    m = ((xx - px) ** 2 + (yy - py) ** 2) < (rpx * 1.0) ** 2
    img[m] = img[m] * (1 - 0.85 * A / 255) + np.array([0.004, 0.006, 0.016]) * 0.85 * A / 255
    sphere(img, INSET_CAM, (X, Y, -D), r, kind, t, light=(-0.6, 0.35, 0.75), k=A / 255, spin=0.35)
    d = ImageDraw.Draw(layer)
    d.ellipse([px - rpx, py - rpx, px + rpx, py + rpx], outline=col + (int(A),), width=7)


# ---------------- cámaras ----------------
TOWARD_E = np.array([0.824, 0.0, 0.566])
C_MID = P_E + SIGHT_DIR * SIGHT_LEN * 0.71


def top_cam(D, yaw=0.0, c=C_MID, hk=0.93):
    h = np.array([TOWARD_E[0] * math.cos(yaw) - TOWARD_E[2] * math.sin(yaw), 0, TOWARD_E[0] * math.sin(yaw) + TOWARD_E[2] * math.cos(yaw)])
    return Cam(c + h * D * (1 - hk) * 1.6 + np.array([0, D * hk, 0]), c)


def cam_for(name, t):
    if name == "linea":
        s = ease((t - TREVEAL) / (S0["cuando"] - 0.2 - TREVEAL - 0.6))
        back = P_E - SIGHT_DIR * 5.0 + np.array([0, 0.5, 0])
        far = top_cam(60.0, 0.15)
        pos = lerp(back, far.O, s)
        tgt = lerp(P_J, C_MID, s)
        return Cam(pos, tgt)
    if name == "ilusion":
        s = (t - S0["ilusion"]) / (S0["luz"] - S0["ilusion"])
        return top_cam(60.0 - 2.5 * ease(s), 0.15 + 0.12 * s)
    if name == "luz":
        s = (t - S0["luz"]) / (S0["cierre"] - S0["luz"])
        return top_cam(57.5 - 1.5 * s, 0.27 + 0.06 * s)
    if name == "cierre":
        s = ease((t - S0["cierre"] + 0.2) / (TFINAL - S0["cierre"]))
        side = np.cross(SIGHT_DIR, np.array([0, 1.0, 0])); side /= np.linalg.norm(side)
        pos = P_E - SIGHT_DIR * (3.5 + 2 * s) + side * (2.5 - 2.0 * s) + np.array([0, 1.4, 0])
        return Cam(pos, P_J)
    return Cam((0, 0, 30), (0, 0, 0))


# ---------------- render ----------------
def scene(t):
    name, ts = shot(t)
    cam = cam_for(name, t)
    img = BG.copy()
    buf = Buf()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    if name == "cielo":
        z = 1.0 + 0.06 * t
        j, m, r = sky_frame(img, t, z)
        A = 255 * min(1.0, (t + 0.2) / 0.5)
        draw_label(layer, t, 0.0, TREVEAL, "CASI PEGADOS", ["este domingo, antes del amanecer"], YELLOW, 110)
        al = 255 * fade(t, 0.5, TREVEAL + 0.3, 0.3)
        leader(d, j + np.array([22, 22]), j + np.array([150, 120]), WHITE, al * 0.8)
        txt(d, (j[0] + 165, j[1] + 160), "JÚPITER", 54, WHITE, al, sw=7)
        leader(d, m + np.array([-20, -20]), m + np.array([-110, -110]), RED, al * 0.8)
        txt(d, (m[0] - 120, m[1] - 150), "MARTE", 54, RED, al, sw=7)
    elif name == "linea":
        s = ease((t - TREVEAL) / (S0["cuando"] - 0.2 - TREVEAL - 0.6))
        solar_system(img, buf, cam, t, 0.35 + 0.65 * s, sight=1.0, dash=True)
        A = 255 * smooth(0.25, 0.6, s)
        tag3d(d, cam, P_E, "TIERRA", CYAN, A, 44, -60)
        tag3d(d, cam, P_M, "MARTE", RED, A, 46, -60)
        tag3d(d, cam, P_J, "JÚPITER", YELLOW, A, 50, 0, "Inter-Black.otf", 210)
        if s > 0.55:
            al = 255 * smooth(0.55, 0.8, s) * fade(t, TREVEAL, S0["cuando"] + 0.3, 0.2)
            x1, y1, _ = cam.proj(P_M[None]); x2, y2, _ = cam.proj(P_J[None])
            off = np.array([-70, 0])
            p1 = np.array([x1[0], y1[0]]) + off; p2 = np.array([x2[0], y2[0]]) + off
            leader(d, p1, p2, YELLOW, al, 6)
            for p in (p1, p2):
                leader(d, p - np.array([0, 18]), p + np.array([0, 18]), YELLOW, al, 6)
            mid = (p1 + p2) / 2
            txt(d, (min(max(mid[0] - 230, 280), W - 280), mid[1] - 60), "≈ 600 MILLONES", 58, YELLOW, al, sw=8)
            txt(d, (min(max(mid[0] - 230, 280), W - 280), mid[1] + 5), "DE KM", 58, YELLOW, al, sw=8)
        draw_label(layer, t, TREVEAL + 0.05, S0["cuando"] + 0.2, "PERO NO ESTÁN JUNTOS", [], WHITE, 92)
    elif name == "cuando":
        s = (t - ts) / (S0["dedo"] - ts)
        j, m, r = sky_frame(img, t, 0.92 + 0.08 * s, dawn=0.15 * s)
        draw_label(layer, t, ts + 0.05, S0["dedo"] + 0.2, "ANTES DEL AMANECER", [], YELLOW, 98)
        a1 = 255 * fade(t, ts + 0.3, S0["dedo"], 0.25)
        k1 = ease_out((t - ts - 0.3) / 0.4); k2 = ease_out((t - 11.9) / 0.4)
        if k1 > 0:
            chip(d, W / 2 - 115, 560 + 30 * (1 - k1), "DOMINGO", "15", a1 * min(1, k1))
            chip(d, W / 2 + 115, 560 + 30 * (1 - k1), "LUNES", "16", a1 * min(1, k1), CYAN)
        if k2 > 0:
            clock_icon(d, 880, 1060, 95, a1 * min(1, k2), 5, 0)
            txt(d, (880, 1195), "5:00 a. m.", 46, WHITE, a1 * min(1, k2), "Inter-Black.otf", 6)
        a3 = 255 * fade(t, 14.3, S0["dedo"], 0.25)
        if a3 > 0:
            yb = RIDGE[W // 2] - 40
            k3 = ease_out((t - 14.3) / 0.5)
            d.polygon([(W / 2, yb - 120 * k3), (W / 2 - 38, yb - 60 * k3), (W / 2 + 38, yb - 60 * k3)], fill=YELLOW + (int(a3),))
            d.line([(W / 2, yb - 60 * k3), (W / 2, yb)], fill=YELLOW + (int(a3),), width=14)
            txt(d, (W / 2, yb + 50), "ESTE", 60, YELLOW, a3, sw=8)
            leader(d, j + np.array([25, 0]), j + np.array([200, 0]), WHITE, a3 * 0.7)
            txt(d, (j[0] + 300, j[1]), "muy alto", 46, WHITE, a3, "Inter-ExtraBold.otf", 6)
        a4 = 255 * fade(t, 12.0, S0["dedo"], 0.3)
        txt(d, (r[0], r[1] + 50), "Régulo (Leo)", 36, CYAN, a4 * 0.85, "Inter-ExtraBold.otf", 5)
    elif name == "dedo":
        z = 1.6
        ctr = SKY_J * 0.5 + SKY_M * 0.5
        j, m, r = sky_frame(img, t, z, ctr, dawn=0.18)
        A = 255 * min(1.0, (t - ts) / 0.3)
        # medida del ángulo entre los dos planetas
        a1 = 255 * fade(t, ts + 0.4, S0["cual"] + 0.2, 0.25)
        k = ease_out((t - ts - 0.4) / 0.6)
        if k > 0:
            v = (j - m); n = np.array([v[1], -v[0]]) / np.linalg.norm(v)
            p1 = m - n * 60; p2 = m - n * 60 + v * k
            leader(d, p1, p2, YELLOW, a1, 6)
            for p in (p1, p2):
                leader(d, p - n * 18, p + n * 18, YELLOW, a1, 6)
            q = (m + j) / 2 - n * 150
            txt(d, (q[0], q[1]), "1.2°", 96, YELLOW, a1 * min(1, k * 1.5), sw=9)
        # el dedo sube desde abajo
        kf = ease_out((t - 21.0) / 0.9)
        if kf > 0:
            fw = 1.4 * PXDEG * z
            xf = j[0] + 250
            ytip = H + 40 - (H + 40 - (m[1] - 40)) * kf
            draw_finger(layer, xf, ytip, fw, 255 * fade(t, 21.0, S0["cual"] + 0.2, 0.25))
            a2 = 255 * fade(t, 21.6, S0["cual"] + 0.2, 0.25)
            txt(d, (xf, ytip - 70), "≈ 1 DEDO", 58, WHITE, a2, sw=8)
        draw_label(layer, t, ts + 0.05, S0["cual"] + 0.2, "POCO MÁS DE 1 GRADO", ["con el brazo estirado"], WHITE, 92)
    elif name == "cual":
        s = (t - ts) / (S0["ilusion"] - ts)
        z = 1.25 + 0.15 * s
        j, m, r = sky_frame(img, t, z, None, dawn=0.2)
        aJ = 255 * fade(t, ts + 0.2, S0["ilusion"] + 0.2, 0.3)
        aM = 255 * fade(t, 27.4, S0["ilusion"] + 0.2, 0.3)
        d.ellipse([j[0] - 48, j[1] - 48, j[0] + 48, j[1] + 48], outline=YELLOW + (int(aJ),), width=5)
        if aM > 0:
            d.ellipse([m[0] - 40, m[1] - 40, m[0] + 40, m[1] + 40], outline=RED + (int(aM),), width=5)
        kJ = ease_out((t - ts - 0.3) / 0.5); kM = ease_out((t - 27.6) / 0.5)
        if kJ > 0:
            inset_sphere(img, layer, 790, 1075, 140 * kJ, "jup", t, aJ * min(1, kJ), YELLOW)
            leader(d, j + np.array([40, 34]), np.array([790 - 100, 1075 - 100]), YELLOW, aJ * 0.6, 3)
            txt(d, (790, 1255), "JÚPITER", 54, YELLOW, aJ, sw=7)
        if kM > 0:
            inset_sphere(img, layer, 250, 560, 100 * kM, "mars", t, aM * min(1, kM), RED)
            leader(d, m + np.array([-34, -30]), np.array([250 + 72, 560 + 72]), RED, aM * 0.6, 3)
            txt(d, (250, 700), "MARTE", 50, RED, aM, sw=7)
        draw_label(layer, t, ts + 0.05, 27.35, "EL MÁS BRILLANTE", ["Júpiter · magnitud −2.1"], YELLOW, 100, y0=330)
        draw_label(layer, t, 27.45, S0["ilusion"] + 0.2, "13 VECES MÁS TENUE", ["Marte, el puntito rojizo"], RED, 96, y0=330)
    elif name == "ilusion":
        solar_system(img, buf, cam, t, 1.0, sight=min(1.0, 0.3 + (t - ts) / 1.5), dash=True)
        A = 255 * min(1.0, (t - ts) / 0.4)
        tag3d(d, cam, (0, 0, 0), "SOL", ORANGE, A * 0.9, 40, -60)
        tag3d(d, cam, P_E, "TIERRA", CYAN, A, 44, -55)
        tag3d(d, cam, P_M, "MARTE", RED, A, 44, -55)
        tag3d(d, cam, P_J, "JÚPITER", YELLOW, A, 50, 0, "Inter-Black.otf", 210)
        draw_label(layer, t, ts + 0.05, 34.1, "ES UNA ILUSIÓN", ["de perspectiva"], WHITE, 104)
        aM = 255 * fade(t, 34.2, S0["luz"] + 0.2, 0.25)
        aJ = 255 * fade(t, 38.85, S0["luz"] + 0.2, 0.25)
        if aM > 0:
            tag3d(d, cam, (P_E + P_M) / 2, "195 MILLONES km", RED, aM, 46, 0, "Inter-Black.otf", 250)
        if aJ > 0:
            tag3d(d, cam, P_E + (P_J - P_E) * 0.55, "≈ 790 MILLONES km", YELLOW, aJ, 52, 0, "Inter-Black.otf", -250)
        draw_label(layer, t, 34.2, 38.8, "MARTE", ["a 195 millones de km de nosotros"], RED, 100)
        draw_label(layer, t, 38.85, 42.85, "JÚPITER", ["a casi 790 millones de km"], YELLOW, 100)
        draw_label(layer, t, 42.9, S0["luz"] + 0.2, "4 VECES MÁS LEJOS", [], ORANGE, 104)
    elif name == "luz":
        solar_system(img, buf, cam, t, 0.9, sight=1.0)
        # pulsos de luz que viajan hacia la Tierra (tiempo comprimido)
        t0p = S0["luz"] + 0.2
        for P0, dur, col in ((P_M, 2.2, (1.0, 0.5, 0.3)), (P_J, 4.6, (1.0, 0.9, 0.6))):
            L = np.linalg.norm(P0 - P_E)
            ph = (t - t0p) / dur
            if 0 <= ph <= 1.0:
                c = P0 + (P_E - P0) * ease(ph)
                rngp = np.random.default_rng(3)
                pts = c + rngp.normal(0, 0.12, (500, 3)) - np.outer(rngp.random(500) * 1.6, (P_E - P0) / L)
                buf2 = Buf(); buf2.add(cam, pts, col, 1.2, glow=1.2); buf2.into(img)
                burst(img, cam, c[None], 0.30, col)
            elif ph > 1.0 and ph < 1.5:
                burst(img, cam, P_E[None], 0.8 * (1.5 - ph), col)
        A = 255 * fade(t, ts + 0.1, S0["cierre"] + 0.2, 0.25)
        kM = min(1.0, max(0.0, (t - t0p) / 2.2)); kJ = min(1.0, max(0.0, (t - t0p) / 4.6))
        d.rounded_rectangle([90, 330, 510, 560], 26, fill=(8, 12, 30, int(A * 0.75)), outline=RED + (int(A),), width=6)
        txt(d, (300, 390), "LUZ DE MARTE", 40, RED, A, "Inter-Black.otf", 5)
        txt(d, (300, 480), f"{int(round(11 * kM))} MIN", 96, WHITE, A, sw=6)
        d.rounded_rectangle([570, 330, 990, 560], 26, fill=(8, 12, 30, int(A * 0.75)), outline=YELLOW + (int(A),), width=6)
        txt(d, (780, 390), "LUZ DE JÚPITER", 40, YELLOW, A, "Inter-Black.otf", 5)
        txt(d, (780, 480), f"{int(round(44 * kJ))} MIN", 96, WHITE, A, sw=6)
        tag3d(d, cam, P_E, "TIERRA", CYAN, A, 44, -60)
    elif name == "cierre":
        solar_system(img, buf, cam, t, 0.6, sight=1.0, dash=True)
        A = 255 * min(1.0, (t - ts) / 0.3)
        tag3d(d, cam, P_M, "MARTE", RED, A, 44, -60)
        tag3d(d, cam, P_J, "JÚPITER", YELLOW, A, 48, -90)
        draw_label(layer, t, ts + 0.05, TFINAL + 0.2, "MISMA LÍNEA DE MIRADA", ["vistos desde la Tierra"], YELLOW, 90)
    elif name == "final":
        s = (t - TFINAL) / (END - TFINAL)
        j, m, r = sky_frame(img, t, 1.0 + 0.06 * s, dawn=0.1 + 0.2 * s)
        draw_label(layer, t, TFINAL + 0.05, CARD, "SIN TELESCOPIO", ["solo tus ojos y un cielo despejado"], GREEN, 104)
        al = 255 * fade(t, TFINAL + 0.4, CARD, 0.3)
        check(d, W / 2, 640, 110, GREEN, al, 16)
        txt(d, (j[0] + 165, j[1] + 160), "JÚPITER", 50, WHITE, al * 0.9, sw=7)
        txt(d, (m[0] - 120, m[1] - 150), "MARTE", 50, RED, al * 0.9, sw=7)
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
