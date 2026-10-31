"""Flash Datos · video 06 · Plutón podría tener un nuevo vecino: 2026 ED138 (trazado de rayos de esferas).

Uso:
  python3 escena.py test 1.0 5.0 ...        -> PNG de prueba en frames_test/
  python3 escena.py chunk <ini> <fin> <out> -> MP4 de los cuadros [ini, fin)
  python3 escena.py info
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
W, H, FPS = 1080, 1920, 30
TY = math.tan(math.radians(20)); TX = TY * W / H
PIX = 2 * TY / H

xs = ((np.arange(W) + 0.5) / W * 2 - 1) * TX
ys = (1 - (np.arange(H) + 0.5) / H * 2) * TY
DX, DY = np.meshgrid(xs, ys)
NRM = np.sqrt(DX * DX + DY * DY + 1)
DIRS = np.stack([DX / NRM, DY / NRM, -1 / NRM], axis=-1)

LIGHT0 = np.array([-0.55, 0.55, 0.62]); LIGHT0 /= np.linalg.norm(LIGHT0)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
EARTH = lin(np.clip(T("earth"), 0, 1)); CLOUDS = T("earth_clouds"); LAND = T("earth_land")
GOLD = lin([1.0, 0.78, 0.34]); ICE = lin([0.62, 0.90, 1.0])


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


def make_background():
    rng = np.random.default_rng(13)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1500
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.025 + 0.42 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 40
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 40.0
    neb = fbm(gx, gy, np.full_like(gx, 0.3), 5, seed=44)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.016, 0.012, 0.034], np.float32)  # nebulosa violeta muy tenue
    return bg


BG = make_background()


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


def shade(body, n, V, t, L):
    ndl = (n * L).sum(-1)
    mu = np.clip((n * V).sum(-1), 0, 1)
    diff = np.clip(ndl, 0, 1)
    kind = body["kind"]
    if kind in ("gold", "ice"):
        base = GOLD if kind == "gold" else ICE
        R = 2 * (n * V).sum(-1)[..., None] * n - V
        up = smooth(-0.2, 0.8, R[..., 1])
        env = (np.array([0.05, 0.035, 0.015]) + up[..., None] * np.array([0.30, 0.22, 0.10])) if kind == "gold" else \
              (np.array([0.03, 0.06, 0.09]) + up[..., None] * np.array([0.25, 0.42, 0.55]))
        Hh = L + V; Hh = Hh / np.linalg.norm(Hh, axis=-1, keepdims=True)
        spec = np.clip((n * Hh).sum(-1), 0, 1) ** 70 * 7.0
        fres = (1 - mu) ** 3
        col = base * (0.06 + 1.25 * diff)[..., None] + env * base * 1.6 + spec[..., None] * np.array([1.0, 0.95, 0.85])
        col = col + fres[..., None] * base * 0.6
        return col * body.get("gain", 1.0)
    # Tierra
    loc = rot_y(rot_x(n, math.radians(body.get("tilt", 16))), body.get("spin", -1.72))
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.85) + 0.80 * cl * 0.85
    R = 2 * ndl[..., None] * n - L
    spec = np.clip((R * V).sum(-1), 0, 1) ** 45 * (1 - land) * (1 - cl[..., 0]) * 0.9
    light = (0.03 + 2.0 * diff + smooth(-0.15, 0.35, ndl) * 0.10)[..., None]
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85])
    fres = (1 - mu) ** 2.5
    col = col + np.array([0.25, 0.55, 1.0]) * (fres * 0.9 * np.clip(ndl + 0.3, 0, 1))[..., None]
    return col * body.get("gain", 1.0)


def draw_sphere(img, O, body, t):
    C = np.array(body["c"], float); r = body["r"]
    if r <= 1e-4:
        return
    rel = C - O
    dist_c = float(np.linalg.norm(rel))
    if dist_c <= r * 1.0001 or rel[2] >= 0:
        return
    depth = -rel[2]
    cxp = (rel[0] / depth / TX + 1) / 2 * W
    cyp = (1 - rel[1] / depth / TY) / 2 * H
    rpx = math.tan(math.asin(r / dist_c)) / PIX
    ext = rpx * 1.12 + 6
    ext *= 1.0 + 0.6 * min(1.0, rpx / H)
    x0 = int(max(0, cxp - ext)); x1 = int(min(W, cxp + ext + 1))
    y0 = int(max(0, cyp - ext)); y1 = int(min(H, cyp + ext + 1))
    if x0 >= x1 or y0 >= y1:
        return
    d = DIRS[y0:y1, x0:x1]
    oc = O - C
    b = d @ oc
    occ = float(oc @ oc)
    perp2 = np.maximum(occ - b * b, 0)
    dist = np.sqrt(perp2)
    pixw = np.maximum(-b, 1e-9) * PIX
    alpha = np.clip((r - dist) / pixw + 0.5, 0, 1) * (b < 0) * body.get("op", 1.0)
    region = img[y0:y1, x0:x1]
    if body["kind"] == "earth":
        hz = (dist > r * 0.995) & (dist < r * 1.06) & (b < 0)
        if hz.any():
            dd = (dist[hz] - r) / (0.018 * r)
            P = O + (-b[hz])[:, None] * d[hz]
            nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
            lit = np.clip(nn @ LIGHT0 + 0.35, 0, 1)
            gl = np.exp(-np.maximum(dd, 0)) * lit * 0.35 * body.get("gain", 1.0)
            region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([0.30, 0.60, 1.0])
    sel = alpha > 0
    if not sel.any():
        return
    ds = d[sel]; bs = b[sel]
    disc = np.maximum(r * r - perp2[sel], 0)
    tt = -bs - np.sqrt(disc)
    P = O + tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    V = -ds
    col = shade(body, n, V, t, np.broadcast_to(LIGHT0, P.shape))
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



# ---------------- texturas propias del video 06 ----------------
from noise import fbm as _fbm


def sphere_grid(h=256, w=512):
    lat = (0.5 - (np.arange(h) + 0.5) / h) * np.pi
    lon = ((np.arange(w) + 0.5) / w * 2 - 1) * np.pi
    LO, LA = np.meshgrid(lon, lat)
    x = np.cos(LA) * np.sin(LO); y = np.sin(LA); z = np.cos(LA) * np.cos(LO)
    return LA, LO, x, y, z


def make_pluto():
    LA, LO, x, y, z = sphere_grid()
    n1 = _fbm(x * 3 + 5, y * 3, z * 3, 6, seed=3)
    n2 = _fbm(x * 9, y * 9, z * 9 + 2, 4, seed=8)
    base = np.array([0.80, 0.66, 0.52]) * (0.82 + 0.3 * n2[..., None])
    dark = np.array([0.38, 0.22, 0.15]) * (0.8 + 0.4 * n2[..., None])
    belt = smooth(0.15, -0.25, LA + 0.25 * (n1 - 0.5))  # región oscura ecuatorial
    col = base * (1 - belt[..., None] * 0.85) + dark * belt[..., None] * 0.85
    # "corazón" claro (Tombaugh Regio), centrado al frente
    def blob(lat0, lon0, r):
        d = np.arccos(np.clip(np.sin(LA) * math.sin(lat0) + np.cos(LA) * math.cos(lat0) * np.cos(LO - lon0), -1, 1))
        return smooth(r, r * 0.7, d + 0.06 * (n2 - 0.5))
    heart = np.maximum(np.maximum(blob(math.radians(22), math.radians(-12), 0.42), blob(math.radians(24), math.radians(14), 0.38)),
                       blob(math.radians(5), math.radians(0), 0.33))
    col = col * (1 - heart[..., None]) + np.array([0.86, 0.83, 0.78]) * heart[..., None]
    return lin(np.clip(col, 0, 1))


def make_ed138():
    LA, LO, x, y, z = sphere_grid()
    n1 = _fbm(x * 4, y * 4 + 3, z * 4, 6, seed=21)
    n2 = _fbm(x * 14, y * 14, z * 14, 3, seed=5)
    col = np.array([0.66, 0.55, 0.50]) * (0.7 + 0.5 * n1[..., None]) * (0.85 + 0.25 * n2[..., None])
    cr = smooth(0.62, 0.70, n2)[..., None]
    col = col * (1 - 0.35 * cr)
    return lin(np.clip(col, 0, 1))


PLUTO = make_pluto(); ED = make_ed138()
L_SUN = np.array([-0.75, 0.35, 0.55]); L_SUN /= np.linalg.norm(L_SUN)


def shade_tex(body, n, V, t, L):
    ndl = (n * L).sum(-1)
    diff = np.clip(ndl, 0, 1)
    loc = rot_y(rot_x(n, math.radians(body.get("tilt", 0))), body.get("spin", 0.0) + body.get("rot", 0.0) * t)
    la, lo = latlon(loc)
    alb = sample(body["tex"], la, lo) * body.get("alb", 1.0)
    light = body.get("amb", 0.02) + 1.45 * diff ** 0.9
    mu = np.clip((n * V).sum(-1), 0, 1)
    rim = (1 - mu) ** 3 * np.clip(ndl + 0.3, 0, 1) * 0.15
    return alb * light[..., None] + rim[..., None] * np.array([0.6, 0.7, 1.0])


def shade_sun(body, n, V, t, L):
    mu = np.clip((n * V).sum(-1), 0, 1)
    k = body.get("k", 3.0)
    return np.array([1.0, 0.72, 0.30]) * (k * (0.35 + 0.65 * mu ** 0.5))[..., None]


_shade_base = shade


def shade(body, n, V, t, L):
    if body["kind"] == "tex":
        return shade_tex(body, n, V, t, L) * body.get("gain", 1.0)
    if body["kind"] == "sun":
        return shade_sun(body, n, V, t, L)
    return _shade_base(body, n, V, t, L)


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
P = lambda sid, k: SEG[sid]["parts"][k]

NOM0 = SEG["nombre"]["t0"]; TAM0 = SEG["tamano"]["t0"]; CLUB0 = SEG["club"]["t0"]; CLUB_P2 = P("club", 1)[0]
PRE0 = SEG["pregunta"]["t0"]; RUB0 = SEG["rubin"]["t0"]; RUB_P2 = P("rubin", 1)[0]
MIS0 = SEG["misterio"]["t0"]; CIE0 = SEG["cierre"]["t0"]
FL = [NOM0 - 0.2, TAM0 - 0.2, CLUB0 - 0.15, PRE0 - 0.25, RUB0 - 0.2, MIS0 - 0.2, END - 0.32]


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


R_PL = 1.0; R_ED = 1500 / 2377 * R_PL; R_ED_MIN = 600 / 2377 * R_PL
PL_HOOK = (-0.45, 1.3, 0.0); ED_HOOK = (0.75, -2.55, -6.0)
O_HOOK = np.array([0.0, 0.0, 8.6])
# vecinos nuevos (puntos tenues) para el cierre
NB = np.random.default_rng(9)
NEIGH = [(NB.uniform(-5.0, 5.0), NB.uniform(-7.0, 4.0), NB.uniform(-40, -16)) for _ in range(16)]
NEIGH_T = np.sort(NB.uniform(CIE0 + 0.3, CIE0 + 3.2, 16))


def scene(t):
    if t < FL[0] or t >= FL[6]:
        tt = t if t < FL[0] else 0.0
        O = O_HOOK - np.array([0, 0, 0.5 * ease_out(tt / 4.5)])
        b = [dict(kind="tex", tex=PLUTO, c=PL_HOOK, r=R_PL, spin=0.25, rot=0.05, tilt=8, L=L_SUN),
             dict(kind="tex", tex=ED, c=ED_HOOK, r=R_ED, spin=0.0, rot=0.08, tilt=0, gain=lerp(0.25, 1.0, ease((tt - 1.0) / 2.0)))]
        return "hook", O, b
    if t < FL[1]:  # diagrama de órbitas
        return "orbitas", np.array([0.0, 0.0, 10.0]), [dict(kind="sun", c=(0.0, -0.2, 0.0), r=0.32, k=3.2)]
    if t < FL[2]:  # Plutón vs ED138
        u = ease((t - FL[1]) / 1.0)
        O = np.array([0.0, 0.0, 8.2 - 0.3 * ease((t - FL[1]) / 5.0)])
        b = [dict(kind="tex", tex=PLUTO, c=(-0.62, -0.2, 0.0), r=R_PL, spin=0.0, rot=0.06, tilt=10, L=L_SUN),
             dict(kind="tex", tex=ED, c=(1.02, -0.2 - (R_PL - R_ED), 0.0), r=R_ED * ease_out((t - FL[1] - 0.3) / 0.8), spin=0.3, rot=0.1)]
        return "tamano", O, b
    if t < FL[3]:  # el club de los planetas enanos
        sizes = [("Ceres", 939, 0.0), ("Plutón", 2377, 0.0), ("Eris", 2326, 0.0), ("Haumea", 1560, 0.0), ("Makemake", 1430, 0.0)]
        O = np.array([0.0, 0.0, 13.5])
        b = []
        for i, (nm, d, _) in enumerate(sizes):
            ti = CLUB0 + 0.3 + 0.45 * i
            r = 0.62 * d / 2377 * ease_out((t - ti) / 0.4)
            x = -1.8 + (i % 3) * 1.8; y = 1.35 - (i // 3) * 1.7
            gray = dict(kind="tex", tex=PLUTO if nm == "Plutón" else ED, c=(x, y, 0.0), r=r, spin=0.5 * i, rot=0.1,
                        alb=1.0 if nm == "Plutón" else (0.75 + 0.1 * i))
            b.append(gray)
        if t >= CLUB_P2:
            b.append(dict(kind="tex", tex=ED, c=(1.8, 1.35 - 1.7, 0.0), r=0.62 * 1500 / 2377 * ease_out((t - CLUB_P2) / 0.4), spin=0.3, rot=0.1))
        return "club", O, b
    if t < FL[4]:  # ¿por qué nadie lo vio?
        O = np.array([0.0, 0.0, 8.0 - 1.0 * ease((t - FL[3]) / 2.0)])
        return "pregunta", O, [dict(kind="tex", tex=ED, c=(0.0, 0.3, -30.0), r=R_ED, spin=0.2, rot=0.1, gain=0.6)]
    if t < FL[5]:  # Vera Rubin en Chile
        u = ease((t - FL[4]) / 2.4)
        spin = math.radians(lerp(-20, -70.7, u)); tilt = lerp(5, -30.2, u)
        O = np.array([0.0, 0.1, 9.6 - 0.8 * ease((t - FL[4]) / (FL[5] - FL[4]))])
        return "rubin", O, [dict(kind="earth", c=(0.0, 0.35, 0.0), r=2.2, tilt=tilt, spin=spin)]
    if t < FL[6] - 0.0:
        if t < CIE0:  # misterio: ¿oscuro y grande o claro y chico?
            ph = 0.5 - 0.5 * math.cos((t - MIS0 - 0.4) * 2 * math.pi / 2.6)
            ph = ph if t > MIS0 + 0.4 else 0.0
            r = lerp(R_ED_MIN, R_ED, ph) * 1.9
            alb = lerp(1.6, 0.45, ph)
            return "misterio", np.array([0.0, 0.0, 6.0]), [dict(kind="tex", tex=ED, c=(0.0, 0.0, 0.0), r=r, spin=0.3, rot=0.15, alb=alb, _ph=ph)]
        # cierre: más vecinos y regreso al encuadre inicial
        O = O_HOOK + np.array([0, 0, 0.9]) * (1 - ease((t - CIE0) / (END - 0.5 - CIE0)))
        b = [dict(kind="tex", tex=PLUTO, c=PL_HOOK, r=R_PL, spin=0.25, rot=0.05, tilt=8, L=L_SUN),
             dict(kind="tex", tex=ED, c=ED_HOOK, r=R_ED, spin=0.0, rot=0.08)]
        for k, p in enumerate(NEIGH):
            if t > NEIGH_T[k]:
                b.append(dict(kind="tex", tex=ED, c=p, r=0.22 + 0.12 * (k % 3), spin=k, rot=0.1, alb=0.6 + 0.1 * (k % 4),
                              gain=min(1.0, (t - NEIGH_T[k]) / 0.4)))
        return "cierre", O, b
    return "hook", O_HOOK, []


HL_WORDS = {"plutón", "vecino", "vecino…", "ed138", "neptuno", "km", "mitad", "planetas", "enanos", "sexto", "nadie", "tenue",
            "vera", "rubin", "cámara", "misterio", "luz", "último", "último…"}

# ---------------- subtítulos y textos ----------------
def groups_for_part(t0, t1, text):
    words = text.split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w[-1] in ".,:…?" or len(" ".join(cur)) > 17:
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
    for t0, t1, txt in s["parts"]:
        CAPS += groups_for_part(t0, t1, txt)
for i in range(len(CAPS) - 1):
    if CAPS[i + 1][0] - CAPS[i][1] < 0.7:
        CAPS[i][1] = CAPS[i + 1][0]

FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); INK = (8, 10, 20); RED = (255, 84, 84)


def is_hl(w):
    core = w.strip(".,:…?¿!").lower()
    return any(ch.isdigit() for ch in core) or core in HL_WORDS or w.strip(".,:…?¿!").isupper() and len(core) > 1


def draw_caption(layer, t, y=1250):
    for (t0, t1, g) in CAPS:
        if t0 <= t < t1:
            k = min(1.0, (t - t0) / 0.09)
            size = int(round(80 * (1.12 - 0.12 * k)))
            f = font("Inter-Black.otf", size)
            d = ImageDraw.Draw(layer)
            space = d.textlength(" ", font=f)
            widths = [d.textlength(w, font=f) for w in g]
            total = sum(widths) + space * (len(g) - 1)
            if total > W - 80:
                size = int(size * (W - 80) / total); f = font("Inter-Black.otf", size)
                space = d.textlength(" ", font=f); widths = [d.textlength(w, font=f) for w in g]
                total = sum(widths) + space * (len(g) - 1)
            x = W / 2 - total / 2
            for w, wd in zip(g, widths):
                col = YELLOW if is_hl(w) else WHITE
                d.text((x, y), w, font=f, fill=col + (255,), anchor="lm", stroke_width=9, stroke_fill=INK + (255,))
                x += wd + space
            return


def fade(t, a, b, f=0.25):
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / f, (b - t) / f)


def txt(d, xy, s, size, col, A, fname="Inter-Black.otf", anchor="mm", sw=7):
    d.text(xy, s, font=font(fname, size), fill=col + (A,), anchor=anchor, stroke_width=sw, stroke_fill=INK + (A,))


def draw_label(layer, t, a, b, title, subs, title_col=WHITE, title_size=118, y0=360, sub_col=CYAN):
    al = fade(t, a, b)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - min(1.0, (t - a) / 0.3)) * 24
    y = y0 + rise
    f = font("Inter-Black.otf", title_size)
    while d.textlength(title, font=f) > W - 90 and title_size > 40:
        title_size -= 4; f = font("Inter-Black.otf", title_size)
    d.text((W / 2, y), title, font=f, fill=title_col + (A,), anchor="mm", stroke_width=8, stroke_fill=INK + (A,))
    y += title_size * 0.5 + 44
    for s in subs:
        txt(d, (W / 2, y), s, 54, sub_col, A, "Inter-ExtraBold.otf")
        y += 70


def bolt(cx, cy, s):
    pts = [(0.58, 0.0), (0.12, 0.56), (0.44, 0.56), (0.30, 1.0), (0.88, 0.38), (0.55, 0.38), (0.74, 0.0)]
    return [(cx + (px - 0.5) * s, cy + (py - 0.5) * s) for px, py in pts]


def draw_watermark(layer):
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 38)
    s = "FLASH DATOS"
    tw = d.textlength(s, font=f)
    x = W / 2 - (tw + 40) / 2
    d.polygon(bolt(x + 14, 212, 40), fill=YELLOW + (230,))
    d.text((x + 40, 212), s, font=f, fill=(255, 255, 255, 215), anchor="lm", stroke_width=4, stroke_fill=INK + (160,))


def project(O, p):
    rel = np.asarray(p, float) - O
    depth = -rel[2]
    return (rel[0] / depth / TX + 1) / 2 * W, (1 - rel[1] / depth / TY) / 2 * H


def box(layer, xy, fill, outline, width=5, radius=34):
    b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(b).rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    layer.alpha_composite(b)


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a



def ring_marker(d, x, y, t, col, A, big=110):
    for k in range(3):
        ph = ((t * 1.2) + k / 3) % 1.0
        rr = 22 + big * ph
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (int(A * (1 - ph)),), width=6)


def dashed_circle(d, x, y, r, col, A, n=28, width=5):
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = a0 + math.pi / n
        d.arc([x - r, y - r, x + r, y + r], math.degrees(a0), math.degrees(a1), fill=col + (A,), width=width)


def draw_hook(layer, t, O):
    d = ImageDraw.Draw(layer)
    tt = t if t < FL[0] else 0.0
    draw_label(layer, t if t < FL[0] else 0.5, -1, FL[0] if t < FL[0] else 99, "PLUTÓN", ["tiene un NUEVO VECINO"], YELLOW, 140)
    al = min(1.0, max(0.0, (tt - 0.8) / 0.4)) if t < FL[0] else 1.0
    if al > 0:
        x, y = project(O, ED_HOOK)
        ring_marker(d, x, y, t, YELLOW, int(255 * al), 120)
        txt(d, (x + 150, y), "¿?", 70, YELLOW, int(255 * al), sw=6)


def draw_orbits(layer, t, O):
    S2 = 2
    big = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy = project(O, (0.0, -0.2, 0.0))
    cx *= S2; cy *= S2
    k = 7.0 * S2  # píxeles por UA
    tilt = 0.45
    def orbit(a, e, rot, col, t0, w=8, dash=False):
        if t < t0:
            return
        u = ease_out((t - t0) / 0.7)
        pts = []
        for th in np.linspace(0, 2 * math.pi * u, 200):
            r = a * (1 - e * e) / (1 + e * math.cos(th))
            x = r * math.cos(th + rot); y = r * math.sin(th + rot)
            pts.append((cx + x * k, cy + y * k * tilt))
        if len(pts) > 1:
            d.line(pts, fill=col + (255,), width=w, joint="curve")
    orbit(30.1, 0.009, 0.0, (79, 216, 255), NOM0 + 0.1)          # Neptuno
    orbit(39.5, 0.249, 2.0, (235, 235, 235), NOM0 + 0.5)          # Plutón
    orbit(50.0, 0.42, 0.6, (255, 216, 77), NOM0 + 1.2, 10)        # ED138 (ilustrativa)
    big = big.resize((W, H), Image.LANCZOS)
    layer.alpha_composite(big)
    dd = ImageDraw.Draw(layer)
    A = int(255 * fade(t, NOM0 + 0.2, FL[1] + 0.05))
    if A > 0:
        y = 1560
        items = [("Neptuno", (79, 216, 255)), ("Plutón", (235, 235, 235)), ("2026 ED138", (255, 216, 77))]
        f = font("Inter-ExtraBold.otf", 44)
        widths = [dd.textlength(n, font=f) + 46 for n, _ in items]
        x = W / 2 - (sum(widths) + 40 * 2) / 2
        for (n, col), wd in zip(items, widths):
            dd.ellipse([x, y - 13, x + 26, y + 13], fill=col + (A,))
            dd.text((x + 40, y), n, font=f, fill=WHITE + (A,), anchor="lm", stroke_width=5, stroke_fill=INK + (A,))
            x += wd + 40
        txt(dd, (W / 2, 1630), "órbita de ED138: ilustración", 34, (170, 180, 200), A, "Inter-ExtraBold.otf", sw=4)
    draw_label(layer, t, FL[0] + 0.1, FL[1], "2026 ED138", ["más allá de NEPTUNO"], YELLOW, 140)


def draw_tamano(layer, t, O):
    d = ImageDraw.Draw(layer)
    A = int(255 * fade(t, FL[1] + 0.3, FL[2] + 0.05))
    if A <= 0:
        return
    x1, y1 = project(O, (-0.62, -0.2 - R_PL - 0.25, 0.0))
    txt(d, (x1, y1 + 20), "PLUTÓN", 50, WHITE, A, sw=5)
    txt(d, (x1, y1 + 78), "2,377 km", 46, CYAN, A, "Inter-ExtraBold.otf", sw=5)
    cE = (1.02, -0.2 - (R_PL - R_ED), 0.0)
    x2, y2 = project(O, (cE[0], cE[1] - R_ED - 0.25, 0.0))
    A2 = int(A * min(1.0, max(0.0, (t - FL[1] - 0.6) / 0.3)))
    txt(d, (x2, y2 + 20), "ED138", 50, YELLOW, A2, sw=5)
    txt(d, (x2, y2 + 78), "hasta 1,500 km", 46, CYAN, A2, "Inter-ExtraBold.otf", sw=5)
    draw_label(layer, t, FL[1] + 0.2, FL[2], "HASTA 1,500 KM", ["más de la mitad de Plutón"], YELLOW, 120)


def draw_club(layer, t, O):
    d = ImageDraw.Draw(layer)
    names = ["Ceres", "Plutón", "Eris", "Haumea", "Makemake"]
    for i, nm in enumerate(names):
        ti = CLUB0 + 0.3 + 0.45 * i
        if t < ti:
            continue
        A = int(255 * min(1.0, (t - ti) / 0.25) * fade(t, CLUB0, FL[3] + 0.05))
        x = -1.8 + (i % 3) * 1.8; y = 1.35 - (i // 3) * 1.7
        px, py = project(O, (x, y - 0.82, 0.0))
        txt(d, (px, py), nm, 46, WHITE, A, "Inter-ExtraBold.otf", sw=5)
    px, py = project(O, (1.8, 1.35 - 1.7, 0.0))
    if t < CLUB_P2:
        A = int(255 * min(1.0, max(0.0, (t - CLUB0 - 2.6) / 0.3)))
        dashed_circle(d, px, py, 80, YELLOW, A)
        txt(d, (px, py), "?", 110, YELLOW, A, sw=6)
    else:
        A = int(255 * fade(t, CLUB_P2, FL[3] + 0.05))
        ring_marker(d, px, py, t, YELLOW, A, 90)
        tx, ty = project(O, (1.8, 1.35 - 1.7 - 0.82, 0.0))
        txt(d, (tx, ty), "¿ED138?", 46, YELLOW, A, sw=5)
    draw_label(layer, t, CLUB0 + 0.1, CLUB_P2 - 0.05, "SOLO 5", ["planetas enanos reconocidos"], YELLOW, 150)
    draw_label(layer, t, CLUB_P2 - 0.05, FL[3], "¿EL SEXTO?", ["si se confirma"], YELLOW, 140)


def draw_pregunta(layer, t, O):
    d = ImageDraw.Draw(layer)
    A = int(255 * fade(t, FL[3] + 0.05, FL[4] + 0.05, 0.2))
    if A <= 0:
        return
    k = ease_out((t - FL[3]) / 0.5)
    d.text((W / 2, 800), "?", font=font("Inter-Black.otf", int(560 + 140 * k)), fill=YELLOW + (A,), anchor="mm", stroke_width=14, stroke_fill=INK + (A,))
    txt(d, (W / 2, 380), "¿POR QUÉ", 120, WHITE, A, sw=8)
    txt(d, (W / 2, 510), "NADIE LO VIO?", 110, WHITE, A, sw=8)


def draw_rubin(layer, t, O):
    d = ImageDraw.Draw(layer)
    x, y = project(O, (0.0, 0.35, 2.2))
    al = fade(t, FL[4] + 2.3, FL[5] + 0.05, 0.3)
    if al > 0:
        A = int(255 * al)
        ring_marker(d, x, y, t, YELLOW, A, 100)
        d.ellipse([x - 15, y - 15, x + 15, y + 15], fill=YELLOW + (A,), outline=INK + (A,), width=4)
        bx = x + 36
        box(layer, [bx, y - 140, bx + 300, y - 52], (10, 16, 40, int(215 * al)), YELLOW + (A,), 4, 28)
        d = ImageDraw.Draw(layer)
        txt(d, (bx + 150, y - 96), "CHILE", 48, WHITE, A, sw=4)
    draw_label(layer, t, FL[4] + 0.1, RUB_P2 - 0.05, "LEJANÍSIMO Y TENUE", ["lo halló el observatorio", "VERA RUBIN"], YELLOW, 92)
    draw_label(layer, t, RUB_P2 - 0.05, FL[5], "LA CÁMARA MÁS", ["grande jamás hecha", "para astronomía"], YELLOW, 104)
    ac = fade(t, RUB_P2 + 0.2, FL[5] + 0.05, 0.25)
    if ac > 0:
        A = int(255 * ac)
        cx, cy = W / 2, 1560
        box(layer, [cx - 300, cy - 75, cx + 300, cy + 75], (10, 16, 40, int(215 * ac)), CYAN + (A,), 5)
        d = ImageDraw.Draw(layer)
        txt(d, (cx, cy), "3,200 MEGAPÍXELES", 60, CYAN, A, sw=5)


def draw_misterio(layer, t, O, ph):
    d = ImageDraw.Draw(layer)
    A = int(255 * fade(t, FL[5] + 0.1, CIE0 + 0.05))
    if A <= 0:
        return
    km = int(round(lerp(600, 1500, ph) / 10) * 10)
    txt(d, (W / 2, 380), f"¿{km:,} KM?", 130, YELLOW, A, sw=8)
    sub = "más oscuro → más grande" if ph > 0.5 else "más brillante → más chico"
    txt(d, (W / 2, 510), sub, 54, CYAN, A, "Inter-ExtraBold.otf", sw=6)
    txt(d, (W / 2, 1560), "depende de cuánta LUZ refleje", 50, WHITE, A, "Inter-ExtraBold.otf", sw=6)


def draw_cierre(layer, t, O):
    d = ImageDraw.Draw(layer)
    for k, p in enumerate(NEIGH):
        if t > NEIGH_T[k]:
            x, y = project(O, p)
            A = int(255 * min(1.0, (t - NEIGH_T[k]) / 0.3) * fade(t, CIE0, END - 0.35, 0.2))
            ring_marker(d, x, y, t + k * 0.2, YELLOW, int(A * 0.7), 50)
    draw_label(layer, t, CIE0 + 0.1, END - 0.4, "NO SERÁ EL ÚLTIMO", ["Plutón podría tener", "muchos vecinos más"], YELLOW, 104)


def overlays(frame_u8, t, name, O, bodies):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if name == "hook":
        draw_hook(layer, t, O)
    elif name == "orbitas":
        draw_orbits(layer, t, O)
    elif name == "tamano":
        draw_tamano(layer, t, O)
    elif name == "club":
        draw_club(layer, t, O)
    elif name == "pregunta":
        draw_pregunta(layer, t, O)
    elif name == "rubin":
        draw_rubin(layer, t, O)
    elif name == "misterio":
        draw_misterio(layer, t, O, bodies[0].get("_ph", 0.0))
    else:
        draw_cierre(layer, t, O)
    draw_caption(layer, t)
    draw_watermark(layer)
    im.alpha_composite(layer)
    fa = flash_alpha(t)
    if fa > 0:
        fl = Image.new("RGBA", (W, H), (255, 246, 225, int(235 * fa)))
        im.alpha_composite(fl)
        if fa > 0.35:
            b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(b).polygon(bolt(W / 2, H / 2, 420), fill=YELLOW + (int(255 * min(1, (fa - 0.35) / 0.4)),))
            im.alpha_composite(b)
    return np.asarray(im.convert("RGB"))


def render(t):
    name, O, bodies = scene(t)
    img = BG.copy()
    if name == "pregunta":
        img *= 0.8
    bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"], float) - O)))
    for b in bodies:
        draw_sphere(img, O, b, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, name, O, bodies)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        for ts in sys.argv[2:]:
            t = float(ts)
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, scene(t)[0], flush=True)
    elif mode == "chunk":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(render(f / FPS).tobytes())
            if f % 30 == 0:
                print(f"{out}: {f}/{b}", flush=True)
        p.stdin.close(); p.wait()
        print("listo", out, flush=True)
    elif mode == "info":
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL])
