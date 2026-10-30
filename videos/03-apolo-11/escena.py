"""Flash Datos · video 03 · "Así llegamos a la Luna: Apolo 11".

Escenas: Luna (gancho) → despegue del Saturno V sobre la Tierra → tripulación → viaje Tierra-Luna con contador
→ Eagle baja y Columbia en órbita → horizonte lunar con huellas → regreso al encuadre inicial.

Uso: python3 escena.py test 1 5 ... | chunk <ini> <fin> <out> | info
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom

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
    if body["kind"] == "moon":
        loc = rot_y(rot_x(n, math.radians(6)), body.get("spin", 0.0))
        la, lo = latlon(loc)
        alb = sample(MOON, la, lo)
        light = body.get("amb", 0.012) + 1.55 * diff ** 0.9
        return alb * light[..., None]
    # Tierra
    loc = rot_y(rot_x(n, math.radians(16)), body.get("spin", -1.72))
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
COH0 = SEG["cohete"]["t0"]; COH1 = SEG["cohete"]["t1"]; COH_P2 = P("cohete", 1)[0]
TRI0 = SEG["tripulacion"]["t0"]; TRI_P = [P("tripulacion", k)[0] for k in range(3)]
VIA0 = SEG["viaje"]["t0"]; VIA1 = SEG["viaje"]["t1"]
SEP0 = SEG["separacion"]["t0"]; SEP_P2 = P("separacion", 1)[0]; SEP_P1E = P("separacion", 0)[1]
PAS0 = SEG["paso"]["t0"]; PAS_P2 = P("paso", 1)[0]; PAS_P3 = P("paso", 2)[0]
CIE0 = SEG["cierre"]["t0"]; CIE_P2 = P("cierre", 1)[0]

FL = [COH0 - 0.25, TRI0 - 0.2, VIA0 - 0.2, SEP0 - 0.2, PAS0 - 0.2, CIE0 - 0.2, END - 0.32]
D_HOOK0, D_HOOK1 = 4.4, 3.4


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

# escena del viaje
E_TRIP = (-0.9, -2.2, 0.0); M_TRIP = (1.0, 1.0, 0.0); O_TRIP = np.array([0.0, 0.0, 9.0])
# escena del descenso
M_SEP = (0.0, -0.75, 0.0); O_SEP = np.array([0.0, 0.0, 3.1])
# horizonte lunar
M_SUR = (0.0, -1.035, -1.2); E_SUR = (-0.30, 0.30, -3.2)


def scene(t):
    if t < FL[0]:
        s = ease(t / FL[0])
        D = lerp_log(D_HOOK0, D_HOOK1, s)
        return "moon", np.array([0.0, 0.0, D]), [dict(kind="moon", c=(0, 0, 0), r=1.0, spin=0.35 + 0.012 * t, L=L_MOON)], {}
    if t < FL[1]:
        s = (t - FL[0]) / (FL[1] - FL[0])
        O = np.array([0.0, 0.0, 3.0])
        return "launch", O, [dict(kind="earth", c=(0.0, -2.75 - 0.25 * s, 0.0), r=1.9, spin=-1.72 + 0.03 * s, L=LIGHT0)], {"s": s}
    if t < FL[3]:
        name = "crew" if t < FL[2] else "trip"
        O = O_TRIP if name == "trip" else np.array([0.0, 0.0, 10.5])
        return name, O, [dict(kind="earth", c=E_TRIP, r=0.6, spin=-1.72 + 0.01 * t, L=LIGHT0),
                         dict(kind="moon", c=M_TRIP, r=0.17, spin=0.4, L=LIGHT0)], {}
    if t < FL[4]:
        s = ease((t - FL[3]) / (FL[4] - FL[3]))
        O = O_SEP + np.array([0.0, -0.10 * s, -0.25 * s])
        return "descent", O, [dict(kind="moon", c=M_SEP, r=1.0, spin=0.35 + 0.02 * (t - FL[3]), L=L_MOON)], {}
    if t < FL[5]:
        s = (t - FL[4]) / (FL[5] - FL[4])
        O = np.array([0.0, 0.0, -0.12 * s])
        return "surface", O, [dict(kind="earth", c=E_SUR, r=0.13, spin=-1.0, L=np.array([-0.95, 0.15, 0.25])),
                              dict(kind="moon", c=M_SUR, r=1.0, spin=0.2, L=np.array([-0.55, 0.30, 0.78]), amb=0.004)], {"s": s}
    s = ease((t - FL[5]) / (END - 0.4 - FL[5]))
    D = lerp_log(2.6, D_HOOK0, s)
    return "moon", np.array([0.0, 0.0, D]), [dict(kind="moon", c=(0, 0, 0), r=1.0, spin=lerp(0.62, 0.35, s), L=L_MOON)], {}


# ---------------- textos ----------------
HL_WORDS = {"humanos", "luna", "llegaron?", "saturno", "v", "armstrong", "aldrin", "collins", "eagle", "solo", "primero", "vivo", "km", "otro", "mundo"}


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
    core = w.strip(".,:…?¿!").lower()
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




# ---------------- dibujos 2D ----------------
def draw_rocket(layer, cx, base_y, h, t, flame=1.0):
    """Saturno V estilizado: tres etapas blancas con bandas negras, nave y torre de escape."""
    d = ImageDraw.Draw(layer)
    w = h * 0.085
    y = base_y
    if flame > 0:
        fl = 1 + 0.12 * math.sin(t * 47) + 0.08 * math.sin(t * 23)
        L = h * 0.42 * fl * flame
        d.polygon([(cx - w * 0.55, y), (cx + w * 0.55, y), (cx, y + L)], fill=(255, 140, 40, 230))
        d.polygon([(cx - w * 0.33, y), (cx + w * 0.33, y), (cx, y + L * 0.62)], fill=(255, 228, 120, 250))
        d.polygon([(cx - w * 0.14, y), (cx + w * 0.14, y), (cx, y + L * 0.32)], fill=(255, 255, 240, 255))
    # aletas
    d.polygon([(cx - w * 0.5, y - h * 0.10), (cx - w * 0.95, y), (cx - w * 0.5, y)], fill=(40, 42, 50, 255))
    d.polygon([(cx + w * 0.5, y - h * 0.10), (cx + w * 0.95, y), (cx + w * 0.5, y)], fill=(40, 42, 50, 255))
    st1 = h * 0.38; st2 = h * 0.26; st3 = h * 0.16
    d.rectangle([cx - w / 2, y - st1, cx + w / 2, y], fill=(238, 240, 244, 255))
    for k in (0.12, 0.55):
        d.rectangle([cx - w / 2, y - st1 * (k + 0.07), cx + w / 2, y - st1 * k], fill=(25, 26, 32, 255))
    y -= st1
    d.rectangle([cx - w / 2, y - st2, cx + w / 2, y], fill=(238, 240, 244, 255))
    d.rectangle([cx - w / 2, y - st2 * 0.12, cx + w / 2, y], fill=(25, 26, 32, 255))
    y -= st2
    w3 = w * 0.78
    d.polygon([(cx - w / 2, y), (cx + w / 2, y), (cx + w3 / 2, y - h * 0.03), (cx - w3 / 2, y - h * 0.03)], fill=(225, 228, 234, 255))
    y -= h * 0.03
    d.rectangle([cx - w3 / 2, y - st3, cx + w3 / 2, y], fill=(238, 240, 244, 255))
    d.rectangle([cx - w3 / 2, y - st3 * 0.25, cx + w3 / 2, y - st3 * 0.12], fill=(25, 26, 32, 255))
    y -= st3
    d.polygon([(cx - w3 / 2, y), (cx + w3 / 2, y), (cx + w3 * 0.12, y - h * 0.07), (cx - w3 * 0.12, y - h * 0.07)], fill=(210, 214, 222, 255))
    y -= h * 0.07
    d.line([cx, y, cx, y - h * 0.08], fill=(230, 80, 60, 255), width=max(2, int(w * 0.10)))
    return y - h * 0.08


def draw_lander(layer, cx, cy, s, A=255):
    d = ImageDraw.Draw(layer)
    gold = (226, 176, 60, A); grey = (200, 204, 212, A); dark = (40, 40, 48, A)
    d.polygon([(cx - s * 0.5, cy), (cx + s * 0.5, cy), (cx + s * 0.42, cy - s * 0.45), (cx - s * 0.42, cy - s * 0.45)], fill=gold)
    d.polygon([(cx - s * 0.32, cy - s * 0.45), (cx + s * 0.32, cy - s * 0.45), (cx + s * 0.22, cy - s * 0.85), (cx - s * 0.22, cy - s * 0.85)], fill=grey)
    d.rectangle([cx - s * 0.08, cy - s * 0.75, cx + s * 0.08, cy - s * 0.62], fill=dark)
    lw = max(2, int(s * 0.06))
    for sg in (-1, 1):
        d.line([cx + sg * s * 0.40, cy - s * 0.1, cx + sg * s * 0.78, cy + s * 0.42], fill=grey, width=lw)
        d.line([cx + sg * s * 0.86, cy + s * 0.42, cx + sg * s * 0.66, cy + s * 0.42], fill=grey, width=lw)
    d.line([cx, cy, cx, cy + s * 0.42], fill=grey, width=lw)


def draw_footprint(layer, cx, cy, s, A=255, ang=-0.25):
    """Huella de bota vista desde arriba, con relieve de suela."""
    d = ImageDraw.Draw(layer)
    ca, sa = math.cos(ang), math.sin(ang)

    def tr(x, y):
        return (cx + (x * ca - y * sa) * s, cy + (x * sa + y * ca) * s)
    outline = []
    for k in range(48):
        a = 2 * math.pi * k / 48
        rx = 0.36 if math.sin(a) < 0 else 0.30
        outline.append(tr(rx * math.cos(a), 0.95 * math.sin(a) - 0.05 * math.cos(a) ** 2))
    d.polygon(outline, fill=(52, 52, 56, A))
    for k in range(-7, 8):
        y = k * 0.11
        half = 0.30 * math.sqrt(max(0, 1 - (y / 0.95) ** 2))
        d.line([tr(-half, y), tr(half, y)], fill=(92, 92, 98, A), width=max(2, int(s * 0.035)))


def draw_crew(layer, t):
    names = [("NEIL ARMSTRONG", "Comandante", "CDR"), ("BUZZ ALDRIN", "Piloto del módulo lunar", "LMP"), ("MICHAEL COLLINS", "Piloto del módulo de mando", "CMP")]
    d = ImageDraw.Draw(layer)
    al_head = fade(t, FL[1] + 0.05, FL[2])
    if al_head > 0:
        A = int(255 * al_head)
        d.text((W / 2, 400), "APOLO 11", font=font("Inter-Black.otf", 112), fill=YELLOW + (A,), anchor="mm", stroke_width=8, stroke_fill=INK + (A,))
        d.text((W / 2, 490), "la tripulación", font=font("Inter-ExtraBold.otf", 52), fill=CYAN + (A,), anchor="mm", stroke_width=6, stroke_fill=INK + (A,))
    for k, (nm, role, tag) in enumerate(names):
        a0 = TRI_P[k] - 0.1
        al = fade(t, a0, FL[2])
        if al <= 0:
            continue
        A = int(255 * al)
        slide = (1 - ease_out((t - a0) / 0.35)) * 120
        y = 640 + k * 175
        x0 = 110 + slide
        hl = 1.0 if (k == 2 and t >= TRI_P[2]) or (k < 2 and TRI_P[k] <= t < TRI_P[k + 1]) else 0.55
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle([x0, y - 70, W - 110 + slide, y + 70], radius=34, fill=(10, 16, 40, int(200 * al)), outline=(YELLOW if hl > 0.9 else CYAN) + (int(255 * al * hl),), width=5)
        layer.alpha_composite(box)
        d = ImageDraw.Draw(layer)
        d.ellipse([x0 + 26, y - 50, x0 + 126, y + 50], fill=(YELLOW if hl > 0.9 else CYAN) + (A,))
        d.text((x0 + 76, y), tag, font=font("Inter-Black.otf", 30), fill=INK + (A,), anchor="mm")
        d.text((x0 + 156, y - 22), nm, font=font("Inter-Black.otf", 54), fill=WHITE + (A,), anchor="lm", stroke_width=5, stroke_fill=INK + (A,))
        d.text((x0 + 156, y + 32), role, font=font("Inter-ExtraBold.otf", 38), fill=CYAN + (A,), anchor="lm", stroke_width=4, stroke_fill=INK + (A,))


def bez(p0, p1, p2, u):
    return ((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])


def draw_trip(layer, t, O):
    ex, ey, er = sphere_px(O, E_TRIP, 0.6)
    mx, my, mr = sphere_px(O, M_TRIP, 0.17)
    p0 = (ex + er * 0.7, ey - er * 0.75); p2 = (mx - mr * 0.9, my + mr * 0.6); p1 = (ex + 520, ey - 380)
    u = ease((t - VIA0 - 0.1) / (VIA1 - VIA0 - 0.2))
    d = ImageDraw.Draw(layer)
    for k in range(60):
        a = k / 60
        q = bez(p0, p1, p2, a)
        A = 230 if a <= u else 70
        d.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], fill=(CYAN if a <= u else WHITE) + (A,))
    q = bez(p0, p1, p2, u)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([q[0] - 26, q[1] - 26, q[0] + 26, q[1] + 26], fill=YELLOW + (110,))
    layer.alpha_composite(g)
    d = ImageDraw.Draw(layer)
    d.ellipse([q[0] - 12, q[1] - 12, q[0] + 12, q[1] + 12], fill=YELLOW + (255,))
    al = fade(t, FL[2] + 0.1, FL[3])
    if al > 0:
        A = int(255 * al)
        km = int(round(384000 * u / 1000.0)) * 1000
        dia = 4 * u
        d.text((W / 2, 380), f"{km:,} km", font=font("Inter-Black.otf", 120), fill=YELLOW + (A,), anchor="mm", stroke_width=8, stroke_fill=INK + (A,))
        d.text((W / 2, 480), f"día {dia:.1f} de 4", font=font("Inter-ExtraBold.otf", 56), fill=CYAN + (A,), anchor="mm", stroke_width=6, stroke_fill=INK + (A,))
        d.text((ex, ey + er + 50), "TIERRA", font=font("Inter-Black.otf", 44), fill=WHITE + (A,), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))
        d.text((mx, my + mr + 46), "LUNA", font=font("Inter-Black.otf", 44), fill=WHITE + (A,), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))


def draw_descent(layer, t, O):
    cx, cy, r = sphere_px(O, M_SEP, 1.0)
    d = ImageDraw.Draw(layer)
    orx, ory = min(r * 1.05, 430), 105
    ocy = cy - r * 0.62
    al = fade(t, FL[3] + 0.05, FL[4])
    A = int(255 * al)
    pts = [(cx + orx * math.cos(a), ocy + ory * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 80)]
    d.line(pts, fill=CYAN + (int(150 * al),), width=4)
    # Columbia recorre la parte de atrás de la órbita (arriba) de derecha a izquierda
    ph = math.pi * 1.05 + 0.9 * math.pi * ((t - FL[3]) / (FL[4] - FL[3]))
    colx, coly = cx + orx * math.cos(ph), ocy + ory * math.sin(ph)
    d.ellipse([colx - 13, coly - 13, colx + 13, coly + 13], fill=CYAN + (A,))
    d.text((colx, coly - 46), "COLUMBIA", font=font("Inter-Black.otf", 40), fill=CYAN + (A,), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))
    # Eagle baja de la órbita a la superficie
    u = ease((t - SEP0 - 0.2) / (SEP_P1E - SEP0 + 0.3))
    sx, sy = cx - r * 0.12, cy - r * 0.93
    start = (cx - orx * 0.55, ocy - ory * 0.85)
    ex = lerp(start[0], sx, u); ey = lerp(start[1], sy, u * u)
    if u < 1:
        fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(fl).polygon([(ex - 10, ey + 8), (ex + 10, ey + 8), (ex, ey + 46 + 8 * math.sin(t * 40))], fill=(255, 200, 90, int(200 * al)))
        layer.alpha_composite(fl)
    draw_lander(layer, ex, ey - 6, 62, A)
    d = ImageDraw.Draw(layer)
    d.text((ex, ey - 96), "EAGLE", font=font("Inter-Black.otf", 44), fill=YELLOW + (A,), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))


def draw_surface(layer, t, O):
    d = ImageDraw.Draw(layer)
    a1 = fade(t, PAS0 + 0.4, FL[5])
    if a1 > 0:
        k = ease_out((t - PAS0 - 0.4) / 0.4)
        draw_footprint(layer, W / 2 - 120, 1620, 300 * (0.85 + 0.15 * k), int(255 * a1 * k), -0.18)
    a2 = fade(t, PAS_P3 + 0.3, FL[5])
    if a2 > 0:
        k = ease_out((t - PAS_P3 - 0.3) / 0.4)
        draw_footprint(layer, W / 2 + 170, 1500, 260 * (0.85 + 0.15 * k), int(255 * a2 * k), 0.12)
    draw_lander(layer, 830, 1020, 150, 255)


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
    if name == "launch":
        s = ex["s"]
        rise = ease((t - FL[0] - 0.2) / (FL[1] - FL[0] - 0.2))
        h = 900
        base = lerp(1660, 640, rise ** 1.6)
        draw_rocket(layer, W / 2 + 260, base, h, t, flame=min(1.0, (t - FL[0]) / 0.3))
        al = fade(t, FL[0] + 0.1, FL[1])
        A = int(255 * al)
        d = ImageDraw.Draw(layer)
        d.text((330, 420), "SATURNO V", font=font("Inter-Black.otf", 92), fill=YELLOW + (A,), anchor="mm", stroke_width=8, stroke_fill=INK + (A,))
        if t >= COH_P2 - 0.1:
            A2 = int(255 * fade(t, COH_P2 - 0.1, FL[1]))
            d.text((330, 560), "110 m", font=font("Inter-Black.otf", 150), fill=WHITE + (A2,), anchor="mm", stroke_width=9, stroke_fill=INK + (A2,))
            d.text((330, 670), "≈ edificio de", font=font("Inter-ExtraBold.otf", 46), fill=CYAN + (A2,), anchor="mm", stroke_width=5, stroke_fill=INK + (A2,))
            d.text((330, 728), "36 pisos", font=font("Inter-ExtraBold.otf", 46), fill=CYAN + (A2,), anchor="mm", stroke_width=5, stroke_fill=INK + (A2,))
            d.text((330, 800), "16 jul 1969", font=font("Inter-ExtraBold.otf", 42), fill=WHITE + (A2,), anchor="mm", stroke_width=5, stroke_fill=INK + (A2,))
    if name == "crew":
        draw_crew(layer, t)
    if name == "trip":
        draw_trip(layer, t, O)
    if name == "descent":
        draw_descent(layer, t, O)
        draw_label(layer, t, SEP0 + 0.1, SEP_P2 - 0.1, "MÓDULO EAGLE", ["Armstrong + Aldrin bajan"], YELLOW, 104)
        draw_label(layer, t, SEP_P2 - 0.1, FL[4], "COLUMBIA", ["Collins, solo en órbita"], CYAN, 104)
    if name == "surface":
        draw_surface(layer, t, O)
        draw_label(layer, t, PAS0 + 0.1, PAS_P2 - 0.1, "PRIMER PASO", ["Neil Armstrong"], YELLOW, 112)
        draw_label(layer, t, PAS_P2 - 0.1, PAS_P3 - 0.1, "UN GRAN SALTO", ["para la humanidad"], WHITE, 108)
        draw_label(layer, t, PAS_P3 - 0.1, FL[5], "+19 MIN", ["Buzz Aldrin"], YELLOW, 130)
    draw_label(layer, t, 0.15, H2 - 0.05, "20 JUL 1969", ["2 humanos en la Luna"], YELLOW, 124)
    draw_label(layer, t, H2 - 0.05, FL[0], "¿CÓMO?", ["384,000 km de distancia"], WHITE, 140)
    draw_label(layer, t, CIE0 + 0.1, CIE_P2 - 0.05, "~600 MILLONES", ["lo vieron en vivo"], YELLOW, 112)
    draw_label(layer, t, CIE_P2 - 0.05, FL[6], "20 JUL 1969", ["la humanidad,", "en otro mundo"], YELLOW, 124)
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
    if name == "surface":
        img *= 0.55
    if name == "crew":
        img *= 0.7
    bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"], float) - O)))
    for b in bodies:
        draw_sphere(img, O, b, t)
    if name == "crew":
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
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL])
