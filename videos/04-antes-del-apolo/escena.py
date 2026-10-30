"""Flash Datos · video 04 · "Antes del Apolo 11: la primera misión espacial (Parte 2)".

Escenas: Tierra vista desde arriba con la Luna lejos (gancho) → Sputnik 1 en primer plano con sus antenas y sus "bip"
→ órbita de Gagarin con contador de 108 min → la promesa de Kennedy (ruta Tierra-Luna) → tarjetas de Tereshkova y Leonov
→ línea de tiempo 1957-1969 que regresa al encuadre inicial.

Uso: python3 escena.py test 1 5 ... | chunk <ini> <fin> <out> | info
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

LIGHT0 = np.array([-0.62, 0.45, 0.65]); LIGHT0 /= np.linalg.norm(LIGHT0)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
CYAN_F = np.array([0.31, 0.85, 1.0]) ** 2.2


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
    rng = np.random.default_rng(5)
    bg = np.zeros((H, W, 3), np.float32)
    n = 1600
    x = rng.integers(0, W, n); y = rng.integers(0, H, n)
    inten = 0.025 + 0.45 * rng.random(n) ** 7
    tint = rng.random(n)
    col = np.stack([0.80 + 0.2 * tint, 0.86 + 0.06 * tint, 1.0 - 0.25 * tint], -1)
    np.add.at(bg, (y, x), col * inten[:, None])
    bg = gaussian_filter(bg, (0.6, 0.6, 0))
    big = np.zeros_like(bg)
    m = 45
    bx = rng.integers(0, W, m); by = rng.integers(0, H, m)
    np.add.at(big, (by, bx), np.array([1.0, 0.95, 0.9]) * (1.5 + 3 * rng.random(m))[:, None])
    bg += gaussian_filter(big, (1.3, 1.3, 0))
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 40.0
    neb = fbm(gx, gy, np.full_like(gx, 1.9), 5, seed=79)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.032, 0.018, 0.030], np.float32)
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




# ---------------- texturas: Luna procedural y Tierra ----------------
def make_moon_tex():
    p = os.path.join(BASE, "tex", "moon.npy")
    if os.path.exists(p):
        return np.load(p)
    from noise import fbm
    th, tw = 512, 1024
    la = (0.5 - (np.arange(th) + 0.5) / th) * np.pi
    lo = ((np.arange(tw) + 0.5) / tw) * 2 * np.pi - np.pi
    LO, LA = np.meshgrid(lo, la)
    x = np.cos(LA) * np.sin(LO); y = np.sin(LA); z = np.cos(LA) * np.cos(LO)
    maria = fbm(x * 1.6 + 3, y * 1.6, z * 1.6, 5, seed=21)
    maria = smooth(0.50, 0.62, maria)
    fine = fbm(x * 9, y * 9, z * 9, 4, seed=4)
    alb = 0.60 - 0.30 * maria + 0.10 * (fine - 0.5)
    rng = np.random.default_rng(7)
    P = np.stack([x, y, z], -1)
    for i in range(420):
        v = rng.normal(size=3); v /= np.linalg.norm(v)
        rad = 0.012 + 0.10 * rng.random() ** 3.5
        ang = np.arccos(np.clip(P @ v, -1, 1))
        q = ang / rad
        inner = np.exp(-(q / 0.85) ** 6)
        rim = np.exp(-((q - 1.0) / 0.12) ** 2)
        alb = alb - 0.045 * inner + 0.045 * rim
        if i < 6:
            alb = alb + 0.08 * np.exp(-(q / 4.0) ** 2) * (0.5 + 0.5 * np.cos(LO * 40 + i))
    alb = np.clip(alb, 0.05, 0.95)
    tex = np.stack([alb * 0.98, alb * 0.97, alb * 0.95], -1).astype(np.float32)
    np.save(p, tex)
    return tex


MOON = lin(make_moon_tex())
EARTH = lin(np.clip(T("earth"), 0, 1)); CLOUDS = T("earth_clouds"); LAND = T("earth_land")


def shade(body, n, V, t, L):
    ndl = (n * L).sum(-1)
    mu = np.clip((n * V).sum(-1), 0, 1)
    diff = np.clip(ndl, 0, 1)
    if body["kind"] == "metal":  # Sputnik: aluminio pulido que refleja la Tierra abajo y el espacio arriba
        R = 2 * (n * V).sum(-1)[..., None] * n - V
        down = smooth(-0.05, -0.6, R[..., 1])
        env = np.array([0.006, 0.008, 0.016]) + down[..., None] * np.array([0.10, 0.24, 0.55])
        H_ = L + V; H_ = H_ / np.linalg.norm(H_, axis=-1, keepdims=True)
        spec = np.clip((n * H_).sum(-1), 0, 1) ** 90 * 9.0
        band = 0.04 * (np.abs(np.sin(n[..., 1] * 18)) > 0.97)
        col = np.array([0.55, 0.56, 0.58]) * (0.03 + 0.55 * diff)[..., None] + env * 1.4 + spec[..., None] * np.array([1.0, 0.97, 0.9])
        fres = (1 - mu) ** 3
        return col + fres[..., None] * np.array([0.05, 0.12, 0.3]) * down[..., None]
    if body["kind"] == "moon":
        loc = rot_y(rot_x(n, math.radians(6)), body.get("spin", 0.0))
        la, lo = latlon(loc)
        alb = sample(MOON, la, lo)
        light = body.get("amb", 0.012) + 1.55 * diff ** 0.9
        return alb * light[..., None]
    # Tierra
    loc = rot_y(rot_x(n, math.radians(body.get("tilt", 16))), body.get("spin", -1.72))
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.88) + 0.80 * cl * 0.88
    R = 2 * ndl[..., None] * n - L
    spec = np.clip((R * V).sum(-1), 0, 1) ** 45 * (1 - land) * (1 - cl[..., 0]) * 0.9
    light = (0.015 + 2.0 * diff + smooth(-0.15, 0.35, ndl) * 0.08)[..., None]
    col = col * light + spec[..., None] * np.array([1.0, 0.95, 0.85])
    fres = (1 - mu) ** 2.5
    col = col + np.array([0.25, 0.55, 1.0]) * (fres * 0.9 * np.clip(ndl + 0.3, 0, 1))[..., None]
    return col


def draw_sphere(img, O, body, t):
    C = np.array(body["c"], float); r = body["r"]
    rel = C - O
    dist_c = float(np.linalg.norm(rel))
    full = body.get("full", False)
    if dist_c <= r * 1.0001:
        return
    if full:
        x0, x1, y0, y1 = 0, W, 0, H
    else:
        if rel[2] >= 0:
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
    alpha = np.clip((r - dist) / pixw + 0.5, 0, 1) * (b < 0)
    region = img[y0:y1, x0:x1]
    if body["kind"] == "earth" and not full:  # halo de atmósfera
        hz = (dist > r * 0.995) & (dist < r * 1.06) & (b < 0)
        if hz.any():
            dd = (dist[hz] - r) / (0.018 * r)
            P = O + (-b[hz])[:, None] * d[hz]
            nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
            Lh = light_dir(body, P)
            lit = np.clip((nn * Lh).sum(-1) + 0.35, 0, 1)
            gl = np.exp(-np.maximum(dd, 0)) * lit * 0.35
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
    col = shade(body, n, V, t, light_dir(body, P))
    a = alpha[sel][:, None]
    region[sel] = region[sel] * (1 - a) + col * a


def light_dir(body, P):
    if "lightpos" in body:
        L = np.asarray(body["lightpos"], float) - P
        return L / np.linalg.norm(L, axis=-1, keepdims=True)
    return np.broadcast_to(np.asarray(body.get("L", LIGHT0), float), P.shape)


def bloom(img):
    small = img[::4, ::4]
    br = np.clip(small - 0.9, 0, None)
    g = gaussian_filter(br, (5, 5, 0)) * 0.55 + gaussian_filter(br, (22, 22, 0)) * 0.85 + gaussian_filter(br, (60, 60, 0)) * 0.5
    return img + ndzoom(g, (4, 4, 1), order=1)[:H, :W]


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)




# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
P = lambda sid, k: SEG[sid]["parts"][k]

H2 = SEG["hook2"]["t0"]
SPU0 = SEG["sputnik"]["t0"]; SPU_P2 = P("sputnik", 1)[0]
GAG0 = SEG["gagarin"]["t0"]; GAG_P2 = P("gagarin", 1)[0]; GAG_P2E = P("gagarin", 1)[1]
KEN0 = SEG["kennedy"]["t0"]; KEN1 = SEG["kennedy"]["t1"]
PIO0 = SEG["pioneros"]["t0"]; PIO_P2 = P("pioneros", 1)[0]
CIE0 = SEG["cierre"]["t0"]; CIE1 = SEG["cierre"]["t1"]

FL = [SPU0 - 0.25, GAG0 - 0.15, KEN0 - 0.2, PIO0 - 0.2, CIE0 - 0.2, END - 0.32]
# "bip" del Sputnik: cada 0.75 s durante su escena (el audio usa los mismos tiempos)
BIPS = [round(x, 3) for x in np.arange(FL[0] + 0.45, FL[1] - 0.2, 0.75)]

def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


def lerp_log(a, b, s):
    return math.exp(math.log(a) + (math.log(b) - math.log(a)) * s)


L_MOON = np.array([-0.70, 0.35, 0.62]); L_MOON /= np.linalg.norm(L_MOON)
# encuadre del gancho (y del final, para que el video se repita solo)
E_HOOK = (0.0, -2.6, 0.0); M_HOOK = (0.5, 0.25, -5.0)
L_HOOK = np.array([-0.55, 0.55, 0.62]); L_HOOK /= np.linalg.norm(L_HOOK)
# Sputnik en primer plano
E_SPU = (0.0, -2.75, -1.6)
# órbita de Gagarin
E_GAG = (0.0, 0.05, 0.0); O_GAG = np.array([0.0, 0.0, 5.4])
# la promesa: Tierra-Luna
E_KEN = (-0.9, -2.2, 0.0); M_KEN = (1.0, 1.0, 0.0); O_KEN = np.array([0.0, 0.0, 9.0])


def sputnik_pos(t):
    s = (t - FL[0]) / (FL[1] - FL[0])
    return np.array([lerp(-0.12, 0.20, s), lerp(0.16, 0.06, s), lerp(0.0, -0.1, s)])


def hook_cam(dy):
    return np.array([0.0, dy, 3.4])


def scene(t):
    if t < FL[0]:
        s = ease(t / FL[0])
        return "hook", hook_cam(0.18 * s), [dict(kind="earth", c=E_HOOK, r=2.0, spin=-1.9 + 0.02 * t, L=L_HOOK, tilt=72),
                                            dict(kind="moon", c=M_HOOK, r=0.27, spin=0.4, L=L_HOOK)], {"s": s}
    if t < FL[1]:
        s = (t - FL[0]) / (FL[1] - FL[0])
        O = np.array([0.04 * s, 0.0, 1.55 - 0.12 * s])
        return "sputnik", O, [dict(kind="earth", c=E_SPU, r=2.4, spin=-1.2 + 0.05 * s, L=LIGHT0, tilt=55),
                              dict(kind="metal", c=tuple(sputnik_pos(t)), r=0.105, L=LIGHT0)], {"s": s}
    if t < FL[2]:
        s = (t - FL[1]) / (FL[2] - FL[1])
        return "gagarin", O_GAG + np.array([0.0, 0.0, -0.25 * ease(s)]), [dict(kind="earth", c=E_GAG, r=0.85, spin=-2.4 + 0.5 * s, L=LIGHT0)], {"s": s}
    if t < FL[3]:
        s = ease((t - FL[2]) / (FL[3] - FL[2]))
        return "kennedy", O_KEN + np.array([0.15 * s, 0.1 * s, -0.6 * s]), [dict(kind="earth", c=E_KEN, r=0.6, spin=-1.72 + 0.01 * t, L=LIGHT0),
                                                                     dict(kind="moon", c=M_KEN, r=0.17, spin=0.4, L=LIGHT0)], {"s": s}
    if t < FL[4]:
        s = (t - FL[3]) / (FL[4] - FL[3])
        return "pioneros", np.array([0.0, 0.0, 3.2]), [dict(kind="earth", c=(0.25, -1.2, 0.0), r=1.3, spin=-0.8 + 0.25 * s, L=LIGHT0)], {"s": s}
    s = ease((t - FL[4]) / (END - 0.35 - FL[4]))
    return "cierre", hook_cam(lerp(0.30, 0.0, s)), [dict(kind="earth", c=E_HOOK, r=2.0, spin=-1.9 + 0.02 * (t - END), L=L_HOOK, tilt=72),
                                                     dict(kind="moon", c=M_HOOK, r=0.27, spin=0.4, L=L_HOOK)], {"s": s}


# ---------------- textos ----------------
HL_WORDS = {"luna", "luna.", "salir", "parte", "sputnik", "satélite", "satélite:", "bip", "gagarin", "minutos", "kennedy", "década",
            "tereshkova", "leonov", "urss", "primera", "primer", "humanos"}

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

FD = os.path.join(BASE, "fonts", "") if os.path.isdir(os.path.join(BASE, "fonts")) else "/usr/share/fonts/opentype/inter/"
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); INK = (8, 10, 20)


def is_hl(w):
    core = w.strip(".,:…?¿!¡“”\"").lower()
    return any(ch.isdigit() for ch in core) or core in HL_WORDS

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


def draw_label(layer, t, a, b, title, subs, title_col=WHITE, title_size=118, y0=360):
    al = fade(t, a, b)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - min(1.0, (t - a) / 0.3)) * 24
    y = y0 + rise
    d.text((W / 2, y), title, font=font("Inter-Black.otf", title_size), fill=title_col + (A,), anchor="mm", stroke_width=8, stroke_fill=INK + (A,))
    y += title_size * 0.5 + 44
    for s in subs:
        d.text((W / 2, y), s, font=font("Inter-ExtraBold.otf", 54), fill=CYAN + (A,), anchor="mm", stroke_width=7, stroke_fill=INK + (A,))
        y += 70


def bolt(cx, cy, s):
    pts = [(0.58, 0.0), (0.12, 0.56), (0.44, 0.56), (0.30, 1.0), (0.88, 0.38), (0.55, 0.38), (0.74, 0.0)]
    return [(cx + (px - 0.5) * s, cy + (py - 0.5) * s) for px, py in pts]


def draw_watermark(layer):
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 38)
    txt = "FLASH DATOS"
    tw = d.textlength(txt, font=f)
    x = W / 2 - (tw + 40) / 2
    d.polygon(bolt(x + 14, 212, 40), fill=YELLOW + (230,))
    d.text((x + 40, 212), txt, font=f, fill=(255, 255, 255, 215), anchor="lm", stroke_width=4, stroke_fill=INK + (160,))


def project(O, p):
    rel = np.asarray(p, float) - O
    depth = -rel[2]
    return (rel[0] / depth / TX + 1) / 2 * W, (1 - rel[1] / depth / TY) / 2 * H


def sphere_px(O, c, r):
    x, y = project(O, c)
    rel = np.asarray(c, float) - O
    return x, y, math.tan(math.asin(r / float(np.linalg.norm(rel)))) / PIX





# ---------------- Sputnik: antenas ----------------
ANT = [((-0.80, 0.42, 0.45), 0.66), ((-0.80, -0.40, 0.48), 0.58), ((-0.82, 0.38, -0.42), 0.66), ((-0.84, -0.36, -0.40), 0.58)]


def draw_antennas(img, O, C, r, t, front):
    m = Image.new("L", (W, H), 0)
    hi = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(m); dh = ImageDraw.Draw(hi)
    wob = 0.04 * math.sin(t * 0.9)
    for (dx, dy, dz), ln in ANT:
        v = np.array([dx, dy + wob, dz]); v /= np.linalg.norm(v)
        if (v[2] > 0) != front:
            continue
        base = C + v * r * 0.92
        tip = base + v * ln
        rel = tip - O
        if -rel[2] < 0.05:
            continue
        p0 = project(O, base); p1 = project(O, tip)
        dist = float(np.linalg.norm(base - O))
        wpx = max(2, int(round(0.010 / dist / PIX)))
        dm.line([p0, p1], fill=255, width=wpx)
        dh.line([p0, p1], fill=255, width=max(1, wpx // 3))
    a = np.asarray(m, np.float32)[..., None] / 255.0
    h = np.asarray(hi, np.float32)[..., None] / 255.0
    col = np.array([0.20, 0.21, 0.23], np.float32)
    img[:] = img * (1 - a) + col * a + h * np.array([0.55, 0.52, 0.48], np.float32) * 0.8


# ---------------- dibujos 2D ----------------
def txt(d, xy, s, size, col, A, bold="Inter-Black.otf", anchor="mm", sw=6):
    d.text(xy, s, font=font(bold, size), fill=col + (A,), anchor=anchor, stroke_width=sw, stroke_fill=INK + (A,))


def draw_hook(layer, t, O, final=False):
    mx, my, mr = sphere_px(O, M_HOOK, 0.27)
    d = ImageDraw.Draw(layer)
    if final:
        A = int(255 * fade(t, FL[4] + 0.1, END - 0.6))
    else:
        A = int(255 * fade(t, 0.3, FL[0] - 0.05))
    if A > 0:
        txt(d, (mx, my + mr + 40), "LUNA", 40, WHITE, A, sw=5)


def draw_bips(layer, t, O, C, r):
    x, y, rp = sphere_px(O, C, r)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for k, b in enumerate(BIPS):
        dt = t - b
        if 0 <= dt < 1.0:
            R = rp * 1.05 + dt * 420
            A = int(200 * (1 - dt) ** 1.5)
            d.ellipse([x - R, y - R, x + R, y + R], outline=YELLOW + (A,), width=6)
            if dt < 0.45:
                A2 = int(255 * min(1, (0.45 - dt) / 0.15))
                right = x < W * 0.5
                sx = x + rp * 1.1 + 40 if right else x - rp * 1.1 - 40; sy = y - rp * 0.9 - dt * 60
                txt(d, (sx, sy), "BIP", 58, YELLOW, A2, anchor="lm" if right else "rm", sw=6)
    layer.alpha_composite(g)


def orbit_pt(cx, cy, rx, ry, a, tilt):
    x, y = rx * math.cos(a), ry * math.sin(a)
    c, s = math.cos(tilt), math.sin(tilt)
    return cx + x * c - y * s, cy + x * s + y * c


def draw_gagarin(layer, t, O):
    cx, cy, rp = sphere_px(O, E_GAG, 0.85)
    rx, ry, tilt = rp * 1.2, rp * 0.30, math.radians(-14)
    u2 = ease((t - GAG_P2) / (GAG_P2E - GAG_P2 - 0.3))
    a0 = math.pi * 0.62
    cur = a0 + 2 * math.pi * u2
    d = ImageDraw.Draw(layer)
    al = fade(t, FL[1] + 0.05, FL[2])
    n = 160
    for k in range(n):
        a = a0 + 2 * math.pi * k / n
        x, y = orbit_pt(cx, cy, rx, ry, a, tilt)
        behind = math.sin(a) < 0 and (x - cx) ** 2 + (y - cy) ** 2 < (rp * 0.99) ** 2
        if behind:
            continue
        done = a <= cur
        A = int((230 if done else 80) * al)
        rr = 5 if done else 3
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(CYAN if done else WHITE) + (A,))
    x, y = orbit_pt(cx, cy, rx, ry, cur, tilt)
    hidden = math.sin(cur) < 0 and (x - cx) ** 2 + (y - cy) ** 2 < (rp * 0.99) ** 2
    if not hidden:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pul = 1 + 0.25 * math.sin(t * 9)
        ImageDraw.Draw(g).ellipse([x - 30 * pul, y - 30 * pul, x + 30 * pul, y + 30 * pul], fill=YELLOW + (int(110 * al),))
        layer.alpha_composite(g)
        d = ImageDraw.Draw(layer)
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=YELLOW + (int(255 * al),))
        txt(d, (x, y - 52), "VOSTOK 1", 38, YELLOW, int(255 * al), sw=5)
    draw_label(layer, t, GAG0 - 0.05, GAG_P2 - 0.05, "YURI GAGARIN", ["12 de abril de 1961"], YELLOW, 112)
    if t >= GAG_P2 - 0.05:
        mins = int(round(108 * u2))
        draw_label(layer, t, GAG_P2 - 0.05, FL[2], f"{mins} MIN", ["1 vuelta a la Tierra"], YELLOW, 150)


def bez(p0, p1, p2, u):
    return ((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])


def draw_kennedy(layer, t, O):
    ex, ey, er = sphere_px(O, E_KEN, 0.6)
    mx, my, mr = sphere_px(O, M_KEN, 0.17)
    p0 = (ex + er * 0.75, ey - er * 0.7); p2 = (mx - mr * 1.2, my + mr * 0.9); p1 = (ex + er * 0.3 + 420, ey - 520)
    u = ease((t - KEN0) / (KEN1 - KEN0 - 0.4))
    al = fade(t, FL[2] + 0.05, FL[3])
    d = ImageDraw.Draw(layer)
    for k in range(44):
        a = k / 44
        q = bez(p0, p1, p2, a)
        on = a <= u
        A = int((230 if on else 60) * al)
        d.line([q, bez(p0, p1, p2, a + 0.012)], fill=(YELLOW if on else WHITE) + (A,), width=7 if on else 4)
    # diana sobre la Luna
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    for k in range(2):
        ph = ((t - KEN0) * 0.9 + k * 0.5) % 1.0
        R = mr * (1.3 + 1.6 * ph)
        gd.ellipse([mx - R, my - R, mx + R, my + R], outline=YELLOW + (int(200 * (1 - ph) * al),), width=5)
    layer.alpha_composite(g)
    d = ImageDraw.Draw(layer)
    A = int(255 * al)
    txt(d, (ex, ey + er + 50), "TIERRA", 44, WHITE, A, sw=5)
    txt(d, (mx, my + mr * 3.2 + 30), "META: LUNA", 44, YELLOW, A, sw=5)
    draw_label(layer, t, KEN0 - 0.1, FL[3], "LA PROMESA", ["J. F. Kennedy · 25 mayo 1961", "la Luna antes de 1970"], YELLOW, 116)


def draw_pioneros(layer, t):
    cards = [("VALENTINA TERESHKOVA", "Primera mujer en el espacio", "1963", PIO0 - 0.05),
             ("ALEXÉI LEONOV", "Primera caminata espacial", "1965", PIO_P2 - 0.1)]
    d = ImageDraw.Draw(layer)
    ah = fade(t, FL[3] + 0.05, FL[4])
    if ah > 0:
        A = int(255 * ah)
        txt(d, (W / 2, 400), "PIONEROS", 112, YELLOW, A, sw=8)
        txt(d, (W / 2, 490), "del espacio", 52, CYAN, A, "Inter-ExtraBold.otf")
    for k, (nm, role, tag, a0) in enumerate(cards):
        al = fade(t, a0, FL[4])
        if al <= 0:
            continue
        A = int(255 * al)
        slide = (1 - ease_out((t - a0) / 0.35)) * 140
        y = 690 + k * 200
        x0 = 90 + slide
        hl = (k == 0 and t < PIO_P2 - 0.1) or k == 1
        edge = YELLOW if hl else CYAN
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle([x0, y - 78, W - 90 + slide, y + 78], radius=36, fill=(10, 16, 40, int(205 * al)),
                                              outline=edge + (int(255 * al * (1.0 if hl else 0.55)),), width=5)
        layer.alpha_composite(box)
        d = ImageDraw.Draw(layer)
        d.ellipse([x0 + 24, y - 56, x0 + 136, y + 56], fill=edge + (A,))
        d.text((x0 + 80, y), tag, font=font("Inter-Black.otf", 34), fill=INK + (A,), anchor="mm")
        size = 50 if len(nm) > 15 else 58
        txt(d, (x0 + 164, y - 24), nm, size, WHITE, A, anchor="lm", sw=5)
        txt(d, (x0 + 164, y + 34), role, 38, CYAN, A, "Inter-ExtraBold.otf", anchor="lm", sw=4)


TL = [(1957, "SPUTNIK"), (1961, "GAGARIN"), (1963, "TERESHKOVA"), (1965, "LEONOV"), (1969, "LUNA")]


def draw_timeline(layer, t):
    al = fade(t, FL[4] + 0.05, END - 0.7, 0.35)
    if al <= 0:
        return
    A = int(255 * al)
    xa, xb, y = 120, 960, 640
    X = lambda yr: xa + (yr - 1957) / 12 * (xb - xa)
    u = ease((t - CIE0 - 0.1) / 2.9)
    d = ImageDraw.Draw(layer)
    d.line([xa, y, xb, y], fill=WHITE + (int(90 * al),), width=8)
    d.line([xa, y, lerp(xa, xb, u), y], fill=YELLOW + (A,), width=10)
    for k, (yr, nm) in enumerate(TL):
        x = X(yr)
        reached = lerp(xa, xb, u) >= x - 1
        last = yr == 1969
        col = YELLOW if (reached and last) else (WHITE if reached else (120, 130, 150))
        rr = 22 if last else 13
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col + (A,), outline=INK + (A,), width=4)
        up = True
        txt(d, (x, y - 56 if up else y + 56), str(yr), 40 if not last else 52, col, A, sw=5)
        if k in (0, 4):
            txt(d, (x, y + 52 if up else y - 52), nm, 26 if not last else 34, CYAN if not last else YELLOW, A, "Inter-ExtraBold.otf", sw=4)


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


def overlays(frame_u8, t, name, O, ex):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if name == "hook":
        draw_hook(layer, t, O)
        draw_label(layer, t, 0.15, H2 - 0.05, "ANTES DE LA LUNA", ["había que salir de la Tierra"], YELLOW, 100)
        draw_label(layer, t, H2 - 0.05, FL[0], "PARTE 2", ["del Apolo 11"], YELLOW, 160)
    if name == "sputnik":
        draw_bips(layer, t, O, sputnik_pos(t), 0.105)
        draw_label(layer, t, FL[0] + 0.1, SPU_P2 - 0.05, "SPUTNIK 1", ["4 oct 1957 · URSS"], YELLOW, 124)
        draw_label(layer, t, SPU_P2 - 0.05, FL[1], "1er SATÉLITE", ["esfera de 58 cm · 83.6 kg"], YELLOW, 116)
    if name == "gagarin":
        draw_gagarin(layer, t, O)
    if name == "kennedy":
        draw_kennedy(layer, t, O)
    if name == "pioneros":
        draw_pioneros(layer, t)
    if name == "cierre":
        draw_hook(layer, t, O, final=True)
        draw_timeline(layer, t)
        draw_label(layer, t, CIE0 + 0.05, END - 0.7, "< 12 AÑOS", ["del primer “bip” a la Luna"], YELLOW, 130)
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
    name, O, bodies, ex = scene(t)
    img = BG.copy()
    if name == "pioneros":
        img *= 0.7
    bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"], float) - O)))
    for b in bodies:
        if b["kind"] == "metal":
            C = np.array(b["c"], float)
            draw_antennas(img, O, C, b["r"], t, front=False)
            draw_sphere(img, O, b, t)
            draw_antennas(img, O, C, b["r"], t, front=True)
        else:
            draw_sphere(img, O, b, t)
    if name == "pioneros":
        img *= 0.45
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, name, O, ex)


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
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL], "bips", BIPS)
