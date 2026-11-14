"""Flash Datos · video 33: encuentran sangre de dinosaurio de 115 millones de años (Aratasaurus, Brasil; PNAS 2026).

Escena nueva: viaje por dentro de un canal vascular de hueso fósil con glóbulos rojos de piedra (elipsoides con trazado
de rayos); terópodo caminando al atardecer con los huesos de la pata resaltados; la Tierra con el noreste de Brasil;
zoom a un corte transversal del hueso con osteonas; comparación de tamaño con un glóbulo humano; molécula de hemo
en 3D con su hierro y el oxígeno que llega; entierro rápido en lodo con poco oxígeno; cristales de hausmanita que
sellan las células; hélice de ADN tachada; gráfica química con el pico del hemo B; regreso al canal y al corte del hueso.

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
    rng = np.random.default_rng(33)
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
    neb = fbm(gx, gy, np.full_like(gx, 3.1), 5, seed=33)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.030, 0.008, 0.030], np.float32)
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

T115 = 2.50          # "…y tiene 115 millones de años"
TMAPA = 9.10         # "un dinosaurio de dos patas del noreste de Brasil"
TTUNEL = 14.70       # entramos al canal
TCOMP = 17.55        # "tres veces más grandes que los tuyos"
TO2 = 23.45          # "la parte de la hemoglobina que llevaba el oxígeno"
TPOCO = 29.80        # "en un lodo con poco oxígeno"
THAUS = 31.75        # "y un mineral, la hausmanita"
TCAPS = 33.95        # "los selló como una cápsula del tiempo"
TNOADN = 37.40       # "no hay ADN"
TCLON = 39.15        # "nadie va a clonar un dinosaurio"
TPRUEBA = 41.10      # "Pero es la primera prueba química…"
SHOTS = [("gancho", 0.0), ("quien", S0["quien"] - 0.2), ("globulos", S0["globulos"] - 0.2), ("comparar", TCOMP),
         ("hemo", S0["hemo"] - 0.2), ("como", S0["como"] - 0.2), ("hausmanita", THAUS), ("adn", S0["adn"] - 0.2),
         ("prueba", TPRUEBA), ("cierre", S0["cierre"] - 0.2)]
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
CUTS = {"gancho": [(2.17, 2.55)], "quien": [(8.82, 9.19)], "globulos": [(17.23, 17.76)], "hemo": [(23.18, 23.68)],
        "como": [(27.17, 27.87), (29.61, 29.91), (31.64, 31.92), (33.68, 34.04)],
        "adn": [(37.08, 37.58), (38.88, 39.26), (40.90, 41.30)]}
SPLITS = {"gancho": ["DINOSAURIO…"], "quien": ["ARATASAURUS,"], "globulos": ["PIEDRA,"], "hemo": ["HEMO,"],
          "como": ["¿CÓMO?", "RÁPIDO,", "OXÍGENO,", "HAUSMANITA,"], "adn": ["OJO:", "ADN,", "dinosaurio."]}

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



# =====================================================================
#  Escena del video 33: sangre de dinosaurio
# =====================================================================
from scipy.ndimage import map_coordinates

LIGHT = np.array([-0.55, 0.65, 0.55]); LIGHT /= np.linalg.norm(LIGHT)
PINK = (255, 120, 140); BONE = (232, 196, 140)


def leader(d, p, q, col, A, wd=4):
    d.line([tuple(p), tuple(q)], fill=col + (int(A),), width=wd)


def sample2(tex, u, v):
    """Muestreo bilineal con repetición en ambos ejes (u, v en unidades de textura)."""
    th, tw = tex.shape[:2]
    u0 = np.floor(u).astype(np.int64); v0 = np.floor(v).astype(np.int64)
    fu = (u - u0).astype(np.float32)[..., None]; fv = (v - v0).astype(np.float32)[..., None]
    ua = u0 % tw; ub = (u0 + 1) % tw; va = v0 % th; vb = (v0 + 1) % th
    return (tex[va, ua] * (1 - fu) + tex[va, ub] * fu) * (1 - fv) + (tex[vb, ua] * (1 - fu) + tex[vb, ub] * fu) * fv


def rot_xyz(ax, ay, az=0.0):
    return rotm(ay, ax, az)


# ---------- pared del canal (hueso fósil) ----------
def make_wall():
    th, tw = 256, 512                                   # th: a lo largo del canal, tw: alrededor
    gy, gx = np.mgrid[0:th, 0:tw].astype(np.float64)
    a = gx / tw * 2 * np.pi
    cx, cz = np.cos(a) * 2.0, np.sin(a) * 2.0
    yy = gy / th * 8.0
    n1 = fbm(cx, yy, cz, 5, seed=41)
    n2 = fbm(cx * 3, yy * 3, cz * 3, 4, seed=42)
    rings = 0.5 + 0.5 * np.sin(gy / th * 2 * np.pi * 22 + n1 * 5)          # láminas del hueso
    base = np.array([0.42, 0.22, 0.10]) * (0.55 + 0.6 * n1[..., None]) * (0.8 + 0.35 * rings[..., None])
    base = base * (0.85 + 0.3 * n2[..., None])
    # lagunas (huequitos oscuros) y vetas rojizas de óxido
    rng = np.random.default_rng(5)
    pits = np.zeros((th, tw), np.float32)
    pits[rng.integers(0, th, 900), rng.integers(0, tw, 900)] = 1
    pits = gaussian_filter(pits, 1.4, mode="wrap") * 9
    base = base * (1 - np.clip(pits, 0, 0.8)[..., None])
    vein = np.clip((n2 - 0.62) * 6, 0, 1)
    base = base * (1 - vein[..., None]) + np.array([0.55, 0.10, 0.06]) * vein[..., None]
    return (np.clip(base, 0, 1) ** 1.6).astype(np.float32)


WALL = make_wall()
RC = 1.0
WALL_ZP = 6.0                                           # periodo de la textura a lo largo del canal


def tunnel(img, cam, bright=1.0, tint=(0.0, 0.0, 0.0)):
    d = cam.dirs(0, H, 0, W)
    ox, oy, oz = cam.O
    dx, dy, dz = d[..., 0], d[..., 1], d[..., 2]
    a = dx * dx + dy * dy + 1e-9
    b = 2 * (ox * dx + oy * dy)
    c = ox * ox + oy * oy - RC * RC
    tt = (-b + np.sqrt(np.maximum(b * b - 4 * a * c, 0))) / (2 * a)
    x = ox + tt * dx; y = oy + tt * dy; z = oz + tt * dz
    ang = np.arctan2(y, x)
    col = sample2(WALL, ang / (2 * np.pi) * WALL.shape[1], z / WALL_ZP * WALL.shape[0])
    ndv = np.clip((x * dx + y * dy) / RC, 0, 1)
    fall = 1.0 / (1.0 + (tt / 2.2) ** 2)
    lit = (0.15 + 1.6 * ndv ** 0.8) * fall
    glowc = np.array([0.30, 0.03, 0.02]) * np.exp(-tt / 9.0)[..., None] * 0.0
    fog = np.exp(-tt / 7.0)[..., None]
    out = col * lit[..., None] * 2.2 * fog + np.array([0.035, 0.006, 0.004]) * (1 - fog) + glowc
    out = out + np.asarray(tint, np.float32) * (1 - ndv[..., None]) * fall[..., None]
    img[:] = out.astype(np.float32) * bright


# ---------- elipsoides con trazado de rayos (glóbulos y átomos) ----------
def ellipsoid(img, cam, C, Rm, s, col, k=1.0, rim=(0, 0, 0), rough=0.0, dimple=0.0, light=None, emit=0.0):
    C = np.asarray(C, float); s = np.asarray(s, float)
    x, y, z = cam.proj(C)
    smax = s.max()
    if z[0] <= smax * 1.05 or k <= 0:
        return
    rpx = smax / z[0] / PIX * 1.25 + 3
    x0 = int(max(0, x[0] - rpx)); x1 = int(min(W, x[0] + rpx)); y0 = int(max(0, y[0] - rpx)); y1 = int(min(H, y[0] + rpx))
    if x0 >= x1 or y0 >= y1:
        return
    d = cam.dirs(y0, y1, x0, x1)
    o = (Rm.T @ (cam.O - C)) / s
    dl = (d @ Rm) / s
    A = (dl * dl).sum(-1)
    od = dl @ o
    clo2 = o @ o - od * od / A
    pw = PIX * z[0] / s.min() * 1.2
    alpha = np.clip((1 - np.sqrt(np.maximum(clo2, 0))) / pw + 0.5, 0, 1)
    sel = alpha > 0
    if not sel.any():
        return
    A_ = A[sel]; od_ = od[sel]
    disc = np.maximum(od_ * od_ - A_ * (o @ o - 1), 0)
    t = (-od_ - np.sqrt(disc)) / A_
    pl = o + t[:, None] * dl[sel]
    nl = pl / s
    n = nl @ Rm.T
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    V = -d[sel]
    L = LIGHT if light is None else light
    ndl = n @ L
    mu = np.clip((n * V).sum(-1), 0, 1)
    c = np.asarray(col, np.float32)
    shade = 0.10 + 1.25 * np.clip(ndl, 0, 1)
    if dimple > 0:
        rho2 = pl[:, 0] ** 2 + pl[:, 2] ** 2
        shade = shade * (1 - dimple * np.exp(-rho2 / 0.22))
    if rough > 0:
        q = pl * 7.0
        sp = (np.sin(q[:, 0] * 3.1 + q[:, 2] * 1.3 + 1.0) * np.sin(q[:, 1] * 2.3 + q[:, 2] * 1.7 - q[:, 0] * 0.9) * np.sin(q[:, 2] * 2.9 + q[:, 0] * 2.1 + 2.0)
              + 0.5 * np.sin(q[:, 0] * 7.3 + q[:, 1] * 5.1 + q[:, 2] * 3.3) * np.sin(q[:, 2] * 6.7 - q[:, 0] * 4.1 + 1.3))
        shade = shade * (1 + rough * sp)
    spec = np.clip((2 * ndl[:, None] * n - L) @ np.zeros(3) + 0, 0, 1)  # (sin especular)
    out = c * shade[:, None] + np.asarray(rim, np.float32) * ((1 - mu) ** 2.2)[:, None] + c * emit
    al = (alpha[sel] * k)[:, None]
    region = img[y0:y1, x0:x1]
    region[sel] = region[sel] * (1 - al) + out * al


def ball(img, cam, C, r, col, k=1.0, emit=0.0, rim=(0.15, 0.15, 0.2)):
    ellipsoid(img, cam, C, np.eye(3), (r, r, r), col, k, rim=rim, emit=emit)


# ---------- glóbulos dentro del canal ----------
rng_c = np.random.default_rng(33)
NC = 70
CELL_Z = -np.sort(rng_c.uniform(0.6, 46.0, NC))
_ang = rng_c.uniform(0, 2 * np.pi, NC); _rad = np.sqrt(rng_c.uniform(0.0, 1.0, NC)) * 0.55
CELL_P = np.stack([np.cos(_ang) * _rad, np.sin(_ang) * _rad, CELL_Z], -1)
CELL_R = [rot_xyz(*rng_c.uniform(-np.pi, np.pi, 3)) for _ in range(NC)]
CELL_W = rng_c.uniform(-0.6, 0.6, (NC, 3))
CELL_S = np.array([0.23, 0.085, 0.20])
CELL_COL = (0.55, 0.035, 0.03)


def cells(img, cam, t, k=1.0, glow=1.0, covered=None):
    rel = CELL_P - cam.O
    order = np.argsort(-(rel @ cam.f))
    drawn = []
    for i in order:
        zf = rel[i] @ cam.f
        if zf < 0.12 or zf > 16:
            continue
        P = CELL_P[i] + np.array([0.05 * math.sin(t * 0.7 + i), 0.05 * math.cos(t * 0.6 + 2 * i), 0])
        Rm = CELL_R[i] @ rot_xyz(*(CELL_W[i] * t * 0.35))
        fogk = math.exp(-zf / 9.0)
        ellipsoid(img, cam, P, Rm, CELL_S, CELL_COL, k * min(1.0, fogk * 1.6), rim=(1.2 * glow, 0.12 * glow, 0.06 * glow), rough=0.35, emit=0.25 * glow)
        drawn.append((i, P))
    return drawn


def tunnel_cam(zc, wob_t, off=(0.0, 0.0), look=None):
    ox = off[0] + 0.10 * math.sin(wob_t * 0.5); oy = off[1] + 0.08 * math.cos(wob_t * 0.4)
    tgt = (0.06 * math.sin(wob_t * 0.3), 0.04 * math.sin(wob_t * 0.45), zc - 5) if look is None else look
    return Cam((ox, oy, zc), tgt, 0.06 * math.sin(wob_t * 0.25))


def red_haze(img, amt):
    yy, xx = np.ogrid[0:H, 0:W]
    r2 = ((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2
    img += (np.exp(-r2 / 0.02) * amt)[..., None] * np.array([0.25, 0.02, 0.015], np.float32)


# ---------- corte transversal del hueso ----------
def make_section(N=1800):
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    c = N / 2
    r = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    nz = fbm(xx / 120.0, yy / 120.0, np.full_like(xx, 1.3), 5, seed=8)
    img = np.zeros((N, N, 3), np.float32)
    ring = (r < 820) & (r > 430)
    bone = np.array([0.40, 0.22, 0.11]) * (0.7 + 0.5 * nz[..., None])
    img[ring] = bone[ring]
    marrow = r <= 430
    img[marrow] = (np.array([0.05, 0.025, 0.02]) * (0.6 + 0.8 * nz[..., None]))[marrow]
    edge = np.exp(-((r - 820) / 6) ** 2) + np.exp(-((r - 430) / 6) ** 2)
    img += edge[..., None] * np.array([0.25, 0.15, 0.08])
    ost = [(c + 625, c, 70, 16)]
    for _ in range(900):
        a = rng.uniform(0, 2 * np.pi); rr = rng.uniform(470, 790); R = rng.uniform(34, 62)
        x, y = c + rr * math.cos(a), c + rr * math.sin(a)
        if all((x - ox) ** 2 + (y - oy) ** 2 > (R + oR) ** 2 * 0.85 for ox, oy, oR, _ in ost):
            ost.append((x, y, R, R * rng.uniform(0.18, 0.26)))
    for (x, y, R, rc) in ost:
        x0, x1, y0, y1 = int(x - R - 2), int(x + R + 3), int(y - R - 2), int(y + R + 3)
        sub_r = np.sqrt((xx[y0:y1, x0:x1] - x) ** 2 + (yy[y0:y1, x0:x1] - y) ** 2)
        m = sub_r < R
        lam = 0.5 + 0.5 * np.cos(sub_r / R * 2 * np.pi * 5)
        reg = img[y0:y1, x0:x1]
        reg[m] = reg[m] * (0.75 + 0.45 * lam[m][:, None]) + np.array([0.06, 0.035, 0.015])
        ca = np.clip(rc - sub_r + 0.5, 0, 1)[..., None]
        cc = np.array([0.30, 0.03, 0.02]) * (0.6 + 0.4 * np.clip(1 - sub_r / rc, 0, 1))[..., None]
        reg[:] = reg * (1 - ca) + cc * ca
        cl = np.exp(-((sub_r - R) / 1.5) ** 2) * m
        reg -= cl[..., None] * reg * 0.5
    img = gaussian_filter(img, (1.0, 1.0, 0))
    return np.clip(img, 0, 2).astype(np.float32), (c + 625, c)


SECT, SECT_T = make_section()


def section_view(img, zoom, cx, cy, angle=0.0, k=1.0):
    """Corte del hueso centrado en (cx, cy) de la textura, con zoom (px de pantalla por px de textura)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ca, sa = math.cos(angle), math.sin(angle)
    X = (xx - W / 2); Y = (yy - H * 0.45)
    u = (X * ca - Y * sa) / zoom + cx; v = (X * sa + Y * ca) / zoom + cy
    out = np.zeros((H, W, 3), np.float32)
    for ch in range(3):
        out[..., ch] = map_coordinates(SECT[..., ch], [v, u], order=1, mode="constant", cval=0.0)
    img[:] = img * (1 - k) + (out * 1.0 + BG * 0.3) * k


# ---------- dinosaurio (silueta de terópodo, vista lateral) ----------
DINO_BODY = [(-1.0, 0.43), (-0.62, 0.53), (-0.30, 0.60), (-0.12, 0.65), (0.10, 0.67), (0.26, 0.64), (0.36, 0.66), (0.44, 0.76),
             (0.50, 0.86), (0.58, 0.89), (0.70, 0.87), (0.79, 0.81), (0.78, 0.785), (0.70, 0.78), (0.62, 0.765), (0.55, 0.755),
             (0.49, 0.72), (0.44, 0.62), (0.36, 0.50), (0.22, 0.44), (0.05, 0.42), (-0.12, 0.45), (-0.38, 0.47), (-0.70, 0.45)]
DINO_ARM = [(0.33, 0.55), (0.38, 0.49), (0.44, 0.46), (0.45, 0.48), (0.40, 0.52), (0.37, 0.57)]
DINO_EYE = (0.65, 0.835)


def leg_pts(phase, hip=(0.0, 0.52)):
    a1 = -0.15 + 0.42 * math.sin(phase)
    L1, L2, L3 = 0.21, 0.20, 0.11
    hx, hy = hip
    kx, ky = hx + L1 * math.sin(a1 + 0.35), hy - L1 * math.cos(a1 + 0.35)
    a2 = a1 - 0.75 + 0.2 * max(0, math.cos(phase))
    ax_, ay_ = kx + L2 * math.sin(a2), ky - L2 * math.cos(a2)
    a3 = a2 + 0.95
    fx, fy = ax_ + L3 * math.sin(a3), ay_ - L3 * math.cos(a3)
    return [(hx, hy), (kx, ky), (ax_, ay_), (fx, fy), (fx + 0.08, fy - 0.005)]


def draw_dino(d, ox, oy, sc, phase, A, fill=(28, 18, 26), rim=(255, 150, 70), glow_leg=0.0, rot=0.0):
    def tr(p):
        x, y = p
        if rot:
            x, y = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
        return (ox + x * sc, oy - y * sc)
    far = leg_pts(phase + math.pi)
    near = leg_pts(phase)
    fa = int(A)
    for pts, colf in ((far, tuple(int(v * 0.7) for v in fill)), ):
        P = [tr(p) for p in pts]
        for (p, q, w) in zip(P[:-1], P[1:], (0.085, 0.05, 0.035, 0.03)):
            d.line([p, q], fill=colf + (fa,), width=max(2, int(w * sc)), joint="curve")
    body = [tr(p) for p in DINO_BODY]
    d.polygon(body, fill=fill + (fa,))
    d.line(body + [body[0]], fill=rim + (int(fa * 0.55),), width=max(2, int(sc * 0.008)))
    d.polygon([tr(p) for p in DINO_ARM], fill=fill + (fa,))
    P = [tr(p) for p in near]
    d.ellipse([P[0][0] - 0.07 * sc, P[0][1] - 0.07 * sc, P[0][0] + 0.07 * sc, P[0][1] + 0.07 * sc], fill=fill + (fa,))
    for (p, q, w) in zip(P[:-1], P[1:], (0.09, 0.055, 0.04, 0.03)):
        d.line([p, q], fill=fill + (fa,), width=max(2, int(w * sc)), joint="curve")
    e = tr(DINO_EYE)
    d.ellipse([e[0] - 0.012 * sc, e[1] - 0.012 * sc, e[0] + 0.012 * sc, e[1] + 0.012 * sc], fill=(255, 200, 80, fa))
    if glow_leg > 0:
        g = int(255 * glow_leg)
        for (p, q) in zip(P[:2], P[1:3]):
            d.line([p, q], fill=YELLOW + (g,), width=max(3, int(0.022 * sc)))
            for e_ in (p, q):
                d.ellipse([e_[0] - 0.02 * sc, e_[1] - 0.02 * sc, e_[0] + 0.02 * sc, e_[1] + 0.02 * sc], fill=YELLOW + (g,))
    return P


def make_dusk():
    yy = (np.arange(H) / H)[:, None, None]
    top = np.array([0.02, 0.01, 0.05]); mid = np.array([0.22, 0.06, 0.08]); low = np.array([0.95, 0.38, 0.10])
    s1 = np.clip(yy / 0.45, 0, 1); s2 = np.clip((yy - 0.40) / 0.25, 0, 1) ** 1.3
    sky = top * (1 - s1) + mid * s1
    sky = sky * (1 - s2) + low * s2
    sky = np.broadcast_to(sky, (H, W, 3)).astype(np.float32).copy()
    sky += BG * 0.5 * (1 - np.clip(yy / 0.45, 0, 1))
    yy2, xx2 = np.ogrid[0:H, 0:W]
    r = np.sqrt((xx2 - 760) ** 2 + (yy2 - 1060) ** 2)
    sky += (np.clip(1 - r / 95, 0, 1) ** 0.3 * 2.5)[..., None] * np.array([1.0, 0.65, 0.3], np.float32)
    sky += (np.exp(-r / 260) * 0.6)[..., None] * np.array([1.0, 0.45, 0.15], np.float32)
    return sky


DUSK = make_dusk()


def ridge(xs, seed, amp, base, freq):
    return base + amp * np.array([fbm(np.array([v * freq]), np.array([seed * 0.37]), np.array([0.5]), 5, seed=seed)[0] for v in xs]) - amp * 0.5


RIDGE_X = np.arange(0, 3 * W, 2) / W
R_FAR = ridge(RIDGE_X, 11, 260, 1060, 1.6)
R_NEAR = ridge(RIDGE_X, 12, 120, 1200, 3.0)


def dusk_scene(img, layer, t, scroll):
    img[:] = DUSK
    d = ImageDraw.Draw(layer)
    for R, col, sp in ((R_FAR, (52, 22, 34), 0.25), (R_NEAR, (30, 14, 24), 0.6)):
        off = (scroll * sp) % W
        xs = np.arange(0, W + 4, 4)
        idx = ((xs + off) / 2).astype(int) % len(R)
        pts = [(x, R[i]) for x, i in zip(xs, idx)] + [(W, H), (0, H)]
        d.polygon(pts, fill=col + (255,))
    # volcán humeante a lo lejos
    vx = 260 - (scroll * 0.25) % (W + 600) + 300
    d.polygon([(vx - 230, 1110), (vx - 40, 880), (vx + 40, 880), (vx + 230, 1110)], fill=(45, 20, 30, 255))
    for k in range(6):
        ph = (t * 0.35 + k / 6) % 1
        rr = 30 + 90 * ph
        d.ellipse([vx - rr + 60 * ph, 870 - 260 * ph - rr, vx + rr + 60 * ph, 870 - 260 * ph + rr], fill=(80, 50, 60, int(55 * (1 - ph))))
    d.rectangle([0, 1250, W, H], fill=(18, 9, 16, 255))
    # helechos
    rng = np.random.default_rng(3)
    for k in range(14):
        x = (rng.uniform(0, W * 2) - scroll * 1.1) % (W + 200) - 100
        h = rng.uniform(60, 130)
        for j in range(-3, 4):
            d.line([(x, 1255), (x + j * h * 0.22, 1255 - h * (1 - abs(j) * 0.12))], fill=(14, 7, 12, 255), width=5)


# ---------- la Tierra (para ubicar Brasil) ----------
EARTH = np.clip(np.load(os.path.join(BASE, "tex", "earth.npy")), 0, 1).astype(np.float32) ** 2.2


def earth_disk(img, layer, px, py, R, lat0, lon0, A):
    if A <= 0 or R < 4:
        return None
    x0, x1 = int(max(px - R - 30, 0)), int(min(px + R + 31, W)); y0, y1 = int(max(py - R - 30, 0)), int(min(py + R + 31, H))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xx - px) / R; ny = -(yy - py) / R
    r2 = nx * nx + ny * ny
    m = r2 < 1
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    cl, sl = math.cos(lat0), math.sin(lat0)
    wy = ny * cl + nz * sl; wz = -ny * sl + nz * cl; wx = nx
    lat = np.arcsin(np.clip(wy, -1, 1)); lon = np.arctan2(wx, wz) + lon0
    col = sample(EARTH, lat, (lon + np.pi) % (2 * np.pi) - np.pi)
    Lp = np.array([-0.5, 0.45, 0.74]); Lp /= np.linalg.norm(Lp)
    ndl = np.clip(nx * Lp[0] + ny * Lp[1] + nz * Lp[2], 0, 1)
    col = col * (0.12 + 1.6 * ndl)[..., None] + np.array([0.2, 0.45, 1.0]) * ((1 - nz) ** 2.5 * 0.9)[..., None]
    aa = np.clip((1 - np.sqrt(r2)) * R + 0.5, 0, 1)[..., None] * (A / 255)
    region = img[y0:y1, x0:x1]
    halo = np.exp(-np.maximum(np.sqrt(r2) - 1, 0) * R / 14) * (r2 >= 1)
    region += (halo * 0.35 * A / 255)[..., None] * np.array([0.3, 0.55, 1.0], np.float32)
    region[:] = region * (1 - aa) + col * aa

    def proj(la, lo):
        v = np.array([math.cos(la) * math.sin(lo - lon0), math.sin(la), math.cos(la) * math.cos(lo - lon0)])
        y2 = v[1] * cl - v[2] * sl; z2 = v[1] * sl + v[2] * cl
        return px + v[0] * R, py - y2 * R, z2
    return proj


# ---------- molécula de hemo ----------
def make_heme():
    atoms, bonds = [("Fe", 0.0, 0.0)], []
    def add(kind, r, deg):
        atoms.append((kind, r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg))))
        return len(atoms) - 1
    meso = []
    ring = []
    for k in range(4):
        ph = 90 * k
        n = add("N", 2.0, ph)
        a1 = add("C", 3.0, ph - 22); a2 = add("C", 3.0, ph + 22)
        b1 = add("C", 4.25, ph - 9.5); b2 = add("C", 4.25, ph + 9.5)
        s1 = add("C", 5.7, ph - 13); s2 = add("C", 5.7, ph + 13)
        bonds += [(0, n), (n, a1), (n, a2), (a1, b1), (a2, b2), (b1, b2), (b1, s1), (b2, s2)]
        ring.append((a1, a2))
        meso.append(add("C", 3.42, ph + 45))
    for k in range(4):
        bonds += [(ring[k][1], meso[k]), (meso[k], ring[(k + 1) % 4][0])]
    P = np.array([[x, y, 0.0] for _, x, y in atoms]) * 0.21
    return [a[0] for a in atoms], P, bonds


HEME_K, HEME_P, HEME_B = make_heme()
ATOM = {"C": (0.075, (0.42, 0.42, 0.48)), "N": (0.088, (0.20, 0.35, 1.0)), "Fe": (0.15, (1.0, 0.42, 0.10)), "O": (0.10, (1.0, 0.12, 0.10))}


def make_bokeh():
    rng = np.random.default_rng(4)
    b = np.zeros((H // 4, W // 4, 3), np.float32)
    for _ in range(26):
        x, y = rng.integers(0, W // 4), rng.integers(0, H // 4)
        b[y, x] = np.array([0.9, 0.06, 0.05]) * rng.uniform(40, 140)
    b = gaussian_filter(b, (9, 9, 0))
    return ndzoom(b, (4, 4, 1), order=1)[:H, :W] * 0.8


BOKEH = make_bokeh()


def micro_bg(img, t, k=1.0):
    sh = int(18 * math.sin(t * 0.3))
    img[:] = BG * 0.35 + np.roll(BOKEH, sh, axis=1) * k


# ---------- ADN ----------
def dna_points(t, n=900):
    u = np.linspace(-1, 1, n)
    y = u * 2.6
    a = u * 9.0 + t * 1.3
    r = 0.55
    s1 = np.stack([np.cos(a) * r, y, np.sin(a) * r], -1)
    s2 = np.stack([np.cos(a + np.pi) * r, y, np.sin(a + np.pi) * r], -1)
    rungs = []
    for k in range(0, n, 22):
        f = np.linspace(0, 1, 26)[:, None]
        rungs.append(s1[k] * (1 - f) + s2[k] * f)
    return s1, s2, np.concatenate(rungs)


def draw_x(d, cx, cy, s, A, wd=26):
    d.line([(cx - s, cy - s), (cx + s, cy + s)], fill=RED + (int(A),), width=wd)
    d.line([(cx - s, cy + s), (cx + s, cy - s)], fill=RED + (int(A),), width=wd)


def fmt_int(n):
    return f"{int(n):,}"


# ---------------- render ----------------
def scene(t):
    name, ts = shot(t)
    img = BG.copy()
    buf = Buf()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    if name == "gancho":
        zc = 1.2 - 0.32 * t
        cam = tunnel_cam(zc, t + 3.0)
        tunnel(img, cam)
        cells(img, cam, t)
        red_haze(img, 0.6)
        draw_label(layer, t, -1, S0["quien"], "SANGRE DE", [], WHITE, 100, y0=360)
        draw_label(layer, t, -1, S0["quien"], "DINOSAURIO", [], RED, 150, y0=470)
        a = 255 * fade(t, T115, S0["quien"], 0.2)
        if a > 0:
            k = ease_out((t - T115) / 0.35)
            sz = int(150 + 30 * (1 - k))
            txt(d, (W / 2, 1010), "115", sz, YELLOW, a, sw=10)
            txt(d, (W / 2, 1125), "MILLONES DE AÑOS", 66, YELLOW, a, sw=8)
    elif name == "quien":
        scroll = (t - ts) * 160
        bgl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dusk_scene(img, bgl, t, scroll)
        db = ImageDraw.Draw(bgl)
        ph = (t - ts) * 5.0
        bob = 6 * abs(math.sin(ph))
        k_m = smooth(TMAPA, TMAPA + 0.5, t)
        gl = smooth(6.6, 7.0, t) * (1 - k_m) * (0.65 + 0.35 * math.sin(t * 9))
        P = draw_dino(db, 430, 1252 - bob, 560, ph, 255, glow_leg=gl)
        arr = np.asarray(bgl).astype(np.float32) / 255
        al = arr[..., 3:4]
        img[:] = img * (1 - al) + (arr[..., :3] ** 2.2) * 1.1 * al
        if gl > 0.05:
            a = 255 * min(1.0, gl * 1.5)
            leader(d, ((P[1][0] + P[2][0]) / 2 + 25, (P[1][1] + P[2][1]) / 2), (800, 1150), YELLOW, a * 0.8, 4)
            txt(d, (840, 1150), "HUESOS", 52, YELLOW, a, sw=7)
            txt(d, (840, 1210), "DE LA PATA", 44, YELLOW, a, "Inter-ExtraBold.otf", 6)
        draw_label(layer, t, ts + 0.05, TMAPA + 0.1, "ARATASAURUS", ["terópodo · hace 115 millones de años"], YELLOW, 110)
        if k_m > 0:
            img *= (1 - 0.85 * k_m)
            R = 330 * ease_out((t - TMAPA) / 0.6)
            proj = earth_disk(img, layer, W / 2, 800, R, math.radians(-10), math.radians(-48) + 0.05 * (t - TMAPA), 255 * k_m)
            d = ImageDraw.Draw(layer)
            if proj is not None and t > TMAPA + 0.45:
                x, y, z = proj(math.radians(-7.3), math.radians(-39.6))
                ap = 255 * smooth(TMAPA + 0.45, TMAPA + 0.8, t)
                pulse = 1 + 0.25 * math.sin(t * 8)
                d.ellipse([x - 16 * pulse, y - 16 * pulse, x + 16 * pulse, y + 16 * pulse], outline=YELLOW + (int(ap),), width=6)
                d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=YELLOW + (int(ap),))
                leader(d, (x + 14, y - 14), (x + 120, y - 170), YELLOW, ap, 5)
                txt(d, (min(x + 150, W - 200), y - 215), "AQUÍ", 60, YELLOW, ap, sw=8)
            draw_label(layer, t, TMAPA + 0.1, S0["globulos"] + 0.2, "NORESTE DE BRASIL", ["cuenca de Araripe"], CYAN, 98, y0=330)
    elif name == "globulos":
        if t < TTUNEL:
            s = (t - ts) / (TTUNEL - ts)
            z = 0.55 * (68.0 / 0.55) ** (ease(s) ** 1.15)
            cx = SECT.shape[1] / 2 * (1 - ease(min(1, s * 1.6))) + SECT_T[0] * ease(min(1, s * 1.6))
            cy = SECT.shape[0] / 2 * (1 - ease(min(1, s * 1.6))) + SECT_T[1] * ease(min(1, s * 1.6))
            section_view(img, z, cx, cy, 0.25 * s)
            img *= (1 - smooth(0.82, 1.0, s))
            a = 255 * fade(t, ts + 0.05, TTUNEL - 0.35, 0.2)
            draw_label(layer, t, ts + 0.05, TTUNEL - 0.3, "DENTRO DEL HUESO", ["corte de la pata, al microscopio"], WHITE, 100)
            if s < 0.45:
                aa = 255 * fade(t, ts + 0.3, ts + (TTUNEL - ts) * 0.45, 0.2)
                x = W / 2 + (SECT_T[0] - cx) * z; y = H * 0.45 + (SECT_T[1] - cy) * z
                d.ellipse([x - 22 * z / 0.55 * 0.6, y - 22 * z / 0.55 * 0.6, x + 22 * z / 0.55 * 0.6, y + 22 * z / 0.55 * 0.6], outline=YELLOW + (int(aa),), width=5)
        else:
            k = smooth(TTUNEL, TTUNEL + 0.6, t)
            zc = 3.0 - 0.45 * (t - TTUNEL)
            cam = tunnel_cam(zc, t)
            tunnel(img, cam)
            cells(img, cam, t)
            red_haze(img, 0.4)
            img *= k
            draw_label(layer, t, TTUNEL + 0.1, TCOMP + 0.2, "GLÓBULOS ROJOS", ["convertidos en piedra"], RED, 112)
    elif name == "comparar":
        micro_bg(img, t, 0.5)
        cam = Cam((0, 0, 6.5), (0, 0, 0))
        s = t - ts
        Rd = rot_xyz(1.05 + 0.1 * math.sin(s * 0.8), 0.4 + 0.25 * s, 0.15)
        Rh = rot_xyz(1.0 + 0.1 * math.cos(s * 0.9), -0.3 - 0.3 * s, -0.1)
        kd = ease_out(s / 0.4); kh = ease_out((s - 0.35) / 0.4)
        ellipsoid(img, cam, (-0.50, 0.0, 0), Rd, np.array([0.23, 0.085, 0.20]) * 2.3 * kd + 1e-3, CELL_COL, min(1, kd), rim=(1.0, 0.1, 0.05), rough=0.35, emit=0.2)
        if kh > 0:
            ellipsoid(img, cam, (0.78, 0.0, 0), Rh, np.array([0.075, 0.028, 0.075]) * 2.3 * kh + 1e-3, (0.9, 0.06, 0.04), min(1, kh), rim=(1.0, 0.25, 0.2), dimple=0.65, emit=0.15)
        A = 255 * fade(t, ts + 0.1, S0["hemo"] + 0.2, 0.2)
        x1, y1, _ = cam.proj(np.array([[-0.50, 0.0, 0]])); x2, y2, _ = cam.proj(np.array([[0.78, 0.0, 0]]))
        txt(d, (x1[0], 1100), "DINOSAURIO", 52, RED, A, sw=7)
        txt(d, (x1[0], 1165), "≈ 23 µm", 64, WHITE, A, sw=7)
        ah = A * min(1, max(0, kh))
        txt(d, (x2[0], 1100), "HUMANO", 52, PINK, ah, sw=7)
        txt(d, (x2[0], 1165), "≈ 7.5 µm", 64, WHITE, ah, sw=7)
        draw_label(layer, t, ts + 0.05, S0["hemo"] + 0.2, "3 VECES MÁS GRANDES", ["que tus glóbulos rojos"], YELLOW, 104)
    elif name == "hemo":
        micro_bg(img, t, 0.7)
        cam = Cam((0, 0, 7.0), (0, -0.05, 0))
        s = t - ts
        Rm = rot_xyz(-0.85 + 0.08 * math.sin(s * 0.6), 0.45 * math.sin(s * 0.45), 0.0)
        kin = ease_out(s / 0.6)
        P = (HEME_P * (0.6 + 0.4 * kin)) @ Rm.T + np.array([0, -0.05, 0])
        nrm = Rm @ np.array([0, 0, 1.0])
        for (i, j) in HEME_B:
            f = np.linspace(0, 1, 40)[:, None]
            pts = P[i] * (1 - f) + P[j] * f
            col = (1.0, 0.55, 0.25) if 0 in (i, j) else (0.75, 0.80, 0.95)
            buf.add(cam, pts, col, 0.9 * kin, glow=0.5)
        buf.into(img)
        items = [(P[i], HEME_K[i]) for i in range(len(P))]
        ko = smooth(TO2, TO2 + 1.2, t)
        if t > TO2 - 0.2:
            fe = P[0]
            drop = (1 - ease(ko)) * 1.6
            o1 = fe + nrm * (0.30 + drop) + Rm @ np.array([0.0, 0.0, 0.0])
            o2 = o1 + nrm * 0.12 + (Rm @ np.array([0.16, 0, 0]))
            items += [(o1, "O"), (o2, "O")]
            bb = Buf(); f = np.linspace(0, 1, 30)[:, None]
            bb.add(cam, o1 * (1 - f) + o2 * f, (1.0, 0.4, 0.3), 1.0, glow=0.6)
            if ko > 0.9:
                bb.add(cam, fe * (1 - f) + o1 * f, (1.0, 0.5, 0.3), 0.8 * smooth(0.9, 1.0, ko), glow=0.8)
            bb.into(img)
        items.sort(key=lambda it: -((it[0] - cam.O) @ cam.f))
        for p, kk in items:
            r, col = ATOM[kk]
            ball(img, cam, p, r * (0.6 + 0.4 * kin), col, min(1, kin * 1.5), emit=0.6 if kk == "Fe" else (0.25 if kk == "O" else 0.0),
                 rim=(0.6, 0.25, 0.1) if kk == "Fe" else (0.12, 0.12, 0.18))
        if ko > 0.95:
            burst(img, cam, P[0][None], 0.25 * (1 - smooth(TO2 + 1.2, TO2 + 2.0, t)), (1.0, 0.5, 0.3))
        A = 255 * fade(t, ts + 0.4, S0["como"], 0.25)
        x, y, _ = cam.proj(P[0][None])
        leader(d, (x[0] - 24, y[0] - 20), (x[0] - 150, y[0] - 230), (255, 160, 70), A * 0.8, 4)
        txt(d, (x[0] - 170, y[0] - 270), "HIERRO (Fe)", 50, (255, 160, 70), A, sw=7)
        if ko > 0.3:
            ao = 255 * smooth(0.3, 0.7, ko) * fade(t, TO2, S0["como"], 0.25)
            o1x, o1y, _ = cam.proj(o2[None])
            txt(d, (o1x[0] + 40, o1y[0] - 90), "OXÍGENO", 54, (255, 110, 100), ao, sw=7)
        draw_label(layer, t, ts + 0.05, TO2 - 0.1, "HEMO", ["el corazón de la hemoglobina"], RED, 140)
        draw_label(layer, t, TO2, S0["como"] + 0.2, "LLEVABA EL OXÍGENO", ["por todo su cuerpo"], YELLOW, 96)
    elif name == "como":
        s = t - ts
        img[:] = BG * 0.4
        # corte del suelo: cielo arriba, lodo que va tapando el cuerpo
        d.rectangle([0, 0, W, H], fill=(10, 8, 16, 255))
        d.rectangle([0, 560, W, H], fill=(58, 40, 30, 255))
        rngl = np.random.default_rng(9)
        lvl = 1180 - 520 * ease(min(1.0, s / 3.6))
        bands = [(70, 52, 40), (88, 66, 48), (62, 48, 40), (96, 74, 52), (74, 58, 46)]
        draw_dino(d, 520, 1210, 520, 0.6, 255, fill=(40, 26, 30), rim=(160, 90, 60), rot=-0.06)
        # capas de lodo (con borde ondulado) que suben
        for k in range(5):
            top = lvl + k * 110
            if top > H:
                break
            xs = np.arange(0, W + 20, 20)
            ys = top + 10 * np.sin(xs / 90.0 + k * 1.7 + s * 0.5)
            pts = [(x, y) for x, y in zip(xs, ys)] + [(W, H), (0, H)]
            d.polygon(pts, fill=bands[k % 5] + (255,))
            d.line([(x, y) for x, y in zip(xs, ys)], fill=(120, 95, 70, 255), width=3)
        for k in range(60):
            x = rngl.uniform(0, W); y = rngl.uniform(lvl, H)
            r = rngl.uniform(2, 6)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(40, 30, 24, 200))
        # burbujas de oxígeno que se apagan
        ao = 1 - smooth(TPOCO, TPOCO + 1.4, t)
        for k in range(9):
            ph = (s * 0.35 + k / 9) % 1
            x = 140 + k * 100 + 20 * math.sin(s * 2 + k)
            y = 1150 - ph * 380
            if y < lvl + 20:
                continue
            a = 255 * ao * min(1, (1 - ph) * 3) * min(1, s * 2)
            if a <= 0:
                continue
            d.ellipse([x - 30, y - 30, x + 30, y + 30], outline=CYAN + (int(a),), width=5)
            txt(d, (x, y), "O₂", 28, CYAN, a, "Inter-Black.otf", 0)
    elif name == "hausmanita":
        s = t - ts
        cam = Cam((0.05, 0.02, CELL_P[5][2] + 2.1 - 0.10 * s), CELL_P[5] + np.array([0.0, -0.08, 0]), 0.05)
        tunnel(img, cam, 0.85)
        drawn = cells(img, cam, t, glow=1.0)
        red_haze(img, 0.3)
        # cristales de hausmanita (Mn3O4) que crecen alrededor de los glóbulos
        kc = smooth(ts + 0.2, ts + 2.4, t)
        rngx = np.random.default_rng(21)
        cryst = []
        for i, P in drawn:
            nn = 16
            dirs_ = rngx.normal(0, 1, (nn, 3)); dirs_ /= np.linalg.norm(dirs_, axis=1, keepdims=True)
            pos = P + dirs_ * np.array([0.27, 0.22, 0.27])
            born = rngx.uniform(0, 1, nn)
            sz = rngx.uniform(0.025, 0.05, nn)
            for p, b, z_ in zip(pos, born, sz):
                if kc > b:
                    cryst.append((p, z_ * min(1, (kc - b) * 4), rngx.uniform(0, np.pi)))
        cryst.sort(key=lambda c: -((c[0] - cam.O) @ cam.f))
        for p, z_, rot in cryst:
            x, y, zz = cam.proj(p[None])
            if zz[0] < 0.15:
                continue
            r = z_ / zz[0] / PIX
            if r < 1.5:
                continue
            cx_, cy_ = x[0], y[0]
            pts = [(cx_ + r * math.cos(rot + k * math.pi / 2) * (1.0 if k % 2 == 0 else 0.6), cy_ + r * math.sin(rot + k * math.pi / 2) * (1.0 if k % 2 == 0 else 0.6)) for k in range(4)]
            fogA = int(255 * min(1, math.exp(-zz[0] / 6) * 1.5))
            d.polygon(pts, fill=(52, 40, 38, fogA))
            d.polygon([pts[0], pts[1], (cx_, cy_)], fill=(150, 120, 105, fogA))
            d.polygon([pts[1], pts[2], (cx_, cy_)], fill=(95, 75, 68, fogA))
        draw_label(layer, t, ts + 0.05, TCAPS, "HAUSMANITA", ["un mineral de manganeso"], ORANGE, 112)
        draw_label(layer, t, TCAPS, S0["adn"] + 0.2, "CÁPSULA DEL TIEMPO", [], YELLOW, 100)
        a = 255 * fade(t, TCAPS + 0.2, S0["adn"] + 0.2, 0.25)
        if a > 0:
            n = 115_000_000 * ease_out((t - TCAPS - 0.2) / 1.6)
            d.rounded_rectangle([170, 980, 910, 1180], 28, fill=(8, 10, 20, int(a * 0.75)), outline=YELLOW + (int(a),), width=6)
            txt(d, (W / 2, 1050), fmt_int(n), 92, WHITE, a, sw=6)
            txt(d, (W / 2, 1135), "AÑOS SELLADOS", 44, YELLOW, a, "Inter-Black.otf", 5)
    elif name == "adn":
        s = t - ts
        micro_bg(img, t, 0.35)
        cam = Cam((0, 0, 7.0), (0, 0.1, 0), 0.35)
        s1, s2, rg = dna_points(t)
        dim = 1 - 0.55 * smooth(TNOADN, TNOADN + 0.4, t)
        buf.add(cam, s1, (0.30, 0.85, 1.0), 1.2 * dim, glow=0.6)
        buf.add(cam, s2, (0.75, 0.45, 1.0), 1.2 * dim, glow=0.6)
        buf.add(cam, rg, (1.0, 0.85, 0.35), 0.45 * dim, glow=0.3)
        buf.into(img)
        draw_label(layer, t, ts + 0.05, TNOADN, "¿Y EL ADN?", [], WHITE, 110)
        a = 255 * fade(t, TNOADN, S0["adn"] + 99, 0.2)
        if a > 0:
            k = ease_out((t - TNOADN) / 0.3)
            draw_x(d, W / 2, 860, 260 * k, a, 34)
        draw_label(layer, t, TNOADN, TCLON, "NO HAY ADN", [], RED, 124)
        draw_label(layer, t, TCLON, TPRUEBA + 0.2, "NO SE PUEDE CLONAR", ["sin ADN no hay receta"], RED, 98)
    elif name == "prueba":
        s = t - ts
        cam = tunnel_cam(-8.0 - 0.2 * s, t)
        tunnel(img, cam, 0.35)
        cells(img, cam, t, k=0.45)
        A = 255 * fade(t, ts + 0.1, S0["cierre"] + 0.2, 0.25)
        x0, x1, y0, y1 = 120, 960, 640, 1180
        d.rounded_rectangle([x0 - 30, y0 - 40, x1 + 30, y1 + 70], 30, fill=(6, 8, 18, int(A * 0.85)), outline=CYAN + (int(A),), width=5)
        d.line([(x0, y1), (x1, y1)], fill=WHITE + (int(A * 0.8),), width=4)
        d.line([(x0, y0), (x0, y1)], fill=WHITE + (int(A * 0.8),), width=4)
        kp = ease_out((t - ts - 0.4) / 1.5)
        rngp = np.random.default_rng(2)
        xs = np.linspace(0, 1, 160)
        noise = np.convolve(rngp.normal(0, 1, 160), np.ones(5) / 5, "same") * 0.03
        yv = 0.06 + np.abs(noise) + 0.85 * kp * np.exp(-((xs - 0.62) / 0.025) ** 2) + 0.18 * np.exp(-((xs - 0.3) / 0.03) ** 2)
        reveal = min(1.0, s / 1.2)
        pts = [(x0 + xv * (x1 - x0), y1 - yy * (y1 - y0) * 0.92) for xv, yy in zip(xs, yv) if xv <= reveal]
        if len(pts) > 1:
            d.line(pts, fill=YELLOW + (int(A),), width=6, joint="curve")
        ak = A * smooth(0.5, 0.9, kp)
        if ak > 0:
            px = x0 + 0.62 * (x1 - x0); py = y1 - (0.06 + 0.85) * (y1 - y0) * 0.92
            txt(d, (px + 150, py + 20), "HEMO B", 56, RED, ak, sw=7)
            check(d, px + 150, py + 100, 70, GREEN, ak, 12)
        txt(d, (W / 2, y1 + 32), "análisis químico del hueso", 38, CYAN, A, "Inter-ExtraBold.otf", 5)
        draw_label(layer, t, ts + 0.05, S0["cierre"] + 0.2, "PRIMERA PRUEBA QUÍMICA", ["de sangre dentro de sus células"], GREEN, 90)
    elif name == "cierre":
        s = t - ts
        TB = ts + 3.0
        if t < TB:
            zc = -2.0 + 0.5 * s
            cam = tunnel_cam(zc, t + 1.0)
            tunnel(img, cam)
            cells(img, cam, t)
            red_haze(img, 0.5)
            img *= 1 - smooth(TB - 0.5, TB, t)
        else:
            u = (t - TB) / (END - TB)
            z = 0.5 * (40.0 / 0.5) ** (1 - ease(min(1, u * 1.15)))
            pw_ = ease(min(1, u * 1.15)) ** 3
            cx = SECT.shape[1] / 2 * pw_ + SECT_T[0] * (1 - pw_)
            cy = SECT.shape[0] / 2 * pw_ + SECT_T[1] * (1 - pw_)
            section_view(img, z, cx, cy, -0.2 * u)
            img *= smooth(TB, TB + 0.4, t)
        draw_label(layer, t, ts + 0.05, CARD, "115 MILLONES DE AÑOS", ["y su sangre todavía deja huella"], YELLOW, 96)

    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    im = Image.fromarray(u8).convert("RGBA")
    if name == "como":
        im = layer.copy(); layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        # vuelve a dibujar las etiquetas encima (la escena 2D ocupa toda la capa)
        draw_label(layer, t, ts + 0.05, TPOCO, "ENTIERRO RÁPIDO", ["lo cubrió el lodo"], ORANGE, 104)
        draw_label(layer, t, TPOCO, THAUS + 0.2, "POCO OXÍGENO", ["casi nada lo descompuso"], CYAN, 108)
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
