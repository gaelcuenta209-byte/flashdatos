"""Flash Datos · video 07 · El desfile de Día de Muertos que inventó James Bond (trazado de rayos de esferas).

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
    rng = np.random.default_rng(21)
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
    neb = fbm(gx, gy, np.full_like(gx, 0.3), 5, seed=12)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.030, 0.010, 0.030], np.float32)  # tinte magenta muy tenue
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



# ---------------- materiales del video 07 ----------------
def shade_flat(body, n, V, t, L):
    ndl = (n * L).sum(-1)
    diff = np.clip(ndl, 0, 1)
    mu = np.clip((n * V).sum(-1), 0, 1)
    base = lin(body["col"])
    Hh = L + V; Hh = Hh / np.linalg.norm(Hh, axis=-1, keepdims=True)
    spec = np.clip((n * Hh).sum(-1), 0, 1) ** 40 * body.get("spec", 0.5)
    rim = (1 - mu) ** 3 * 0.25
    col = base * (body.get("amb", 0.10) + 1.5 * diff)[..., None] + spec[..., None] + rim[..., None] * np.array([1.0, 0.6, 0.9])
    return col * body.get("gain", 1.0) + base * body.get("glow", 0.0)


_shade_base = shade


def shade(body, n, V, t, L):
    if body["kind"] == "flat":
        return shade_flat(body, n, V, t, L)
    return _shade_base(body, n, V, t, L) * body.get("gain", 1.0)


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
P = lambda sid, k: SEG[sid]["parts"][k]
H1 = SEG["hook1"]; H2 = SEG["hook2"]
SPE0 = SEG["spectre"]["t0"]; SPE_P2 = P("spectre", 1)[0]
PROB0 = SEG["problema"]["t0"]; PRE0 = SEG["pregunta"]["t0"]; REAL0 = SEG["realidad"]["t0"]
HOY0 = SEG["hoy"]["t0"]; CIE0 = SEG["cierre"]["t0"]
FL = [SPE0 - 0.2, PROB0 - 0.15, REAL0 - 0.2, HOY0 - 0.12, CIE0 - 0.15, END - 0.32]


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


BONE = (0.96, 0.93, 0.86); HOLE = (0.06, 0.04, 0.08); MARI = (1.0, 0.55, 0.05); MARI2 = (1.0, 0.72, 0.10)
MAG = (0.95, 0.20, 0.60); PUR = (0.55, 0.25, 0.85); TEAL = (0.10, 0.75, 0.75)


def calavera(cx, cy, cz, s, t, gain=1.0):
    """Calavera de esferas con corona de cempasúchil."""
    b = []
    def add(dx, dy, dz, r, col, **kw):
        b.append(dict(kind="flat", c=(cx + dx * s, cy + dy * s, cz + dz * s), r=r * s, col=col, gain=gain, **kw))
    add(0, 0.35, 0, 1.25, BONE, spec=0.35)                      # cráneo
    add(0, -0.55, 0.15, 0.85, BONE, spec=0.3)                   # mandíbula / mejillas
    for sx in (-1, 1):
        add(0.45 * sx, 0.05, 1.02, 0.36, HOLE, spec=0.1, amb=0.0)   # cuencas
        add(0.45 * sx, 0.05, 1.33, 0.07, (1.0, 0.6, 0.15), glow=2.5)  # brillo en los ojos
        add(0.80 * sx, 0.70, 0.75, 0.13, MAG, spec=0.6)              # adornos de colores
        add(0.95 * sx, 0.30, 0.70, 0.10, TEAL, spec=0.6)
    add(0, -0.33, 1.10, 0.15, HOLE, amb=0.0)                    # nariz
    for k in range(6):                                          # boca
        add(-0.37 + k * 0.148, -0.82, 0.70, 0.12, HOLE, amb=0.0)
    for k in range(6):                                          # dientes
        add(-0.37 + k * 0.148, -0.82, 0.78, 0.085, BONE, spec=0.4)
    add(0, 1.15, 0.85, 0.16, MAG, spec=0.6)                     # flor en la frente
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        add(0.22 * math.cos(a), 1.15 + 0.22 * math.sin(a), 0.80, 0.11, MARI2, spec=0.3)
    for k in range(13):                                         # corona de cempasúchil
        a = math.radians(200 - k * 15.5)
        rr = 1.32
        bob = 0.03 * math.sin(t * 3 + k)
        add(rr * math.cos(a), 0.35 + rr * math.sin(a) * 0.95 + bob, 0.35, 0.24 if k % 2 else 0.2, MARI if k % 2 else MARI2, spec=0.25)
    return b


O_HOOK = np.array([0.0, 0.0, 9.4]); SK = (0.0, -0.1, 0.0)

# desfile: fila de figuras que avanza
RNGP = np.random.default_rng(4)
NPAR = 120
PAR_X = RNGP.uniform(-1.6, 1.6, NPAR)
PAR_Z = -np.linspace(0, 60, NPAR) + RNGP.uniform(-0.3, 0.3, NPAR)
PAR_COL = [BONE, MARI, MAG, PUR, TEAL, MARI2]
PAR_C = RNGP.integers(0, len(PAR_COL), NPAR)


def parade(t, gain=1.0, ghost=0.0):
    b = []
    speed = 2.2
    for i in range(NPAR):
        z = ((PAR_Z[i] + t * speed) % 60.0) - 60.0 - 0.5
        x = PAR_X[i]
        hop = abs(math.sin(t * 5 + i)) * 0.12
        col = PAR_COL[PAR_C[i]]
        if ghost > 0:
            g = 0.35
            col = tuple(c * (1 - ghost) + g * ghost for c in col)
        b.append(dict(kind="flat", c=(x, -1.2 + hop, z), r=0.24, col=col, gain=gain, spec=0.4, op=lerp(1.0, 0.35, ghost)))
        b.append(dict(kind="flat", c=(x, -1.62 + hop, z), r=0.30, col=PAR_COL[(PAR_C[i] + 2) % len(PAR_COL)], gain=gain * lerp(1, 0.6, ghost),
                      spec=0.2, op=lerp(1.0, 0.35, ghost)))
    return b


O_PAR = np.array([0.0, 0.4, 7.0])


def scene(t):
    if t < FL[0] or t >= FL[5]:
        tt = t if t < FL[0] else 0.0
        O = O_HOOK - np.array([0, 0, 0.6 * ease_out(tt / 5.0)])
        return "hook", O, calavera(*SK, 1.0, t)
    if t < SPE_P2 - 0.1:  # México / CDMX
        u = ease((t - FL[0]) / 2.0)
        spin = math.radians(lerp(-60, -99.13, u)); tilt = lerp(5, 19.43, u)
        O = np.array([0.0, 0.1, 9.6 - 0.9 * ease((t - FL[0]) / (SPE_P2 - FL[0]))])
        return "cdmx", O, [dict(kind="earth", c=(0.0, 0.35, 0.0), r=2.2, tilt=tilt, spin=spin)]
    if t < FL[1]:
        return "extras", O_PAR, parade(t)
    if t < FL[2]:
        gh = ease((t - FL[1]) / 0.8)
        return "fantasma", O_PAR, parade(t, gain=lerp(1.0, 0.5, gh), ghost=gh)
    if t < FL[3]:
        return "real", O_PAR + np.array([0, 0.2, 0.0]), parade(t, gain=1.15)
    if t < FL[4]:
        O = O_HOOK + np.array([0, 0, 1.6])
        return "hoy", O, calavera(*SK, 0.85, t)
    O = O_HOOK - np.array([0, 0, 0.6 * ease_out((t - FL[4]) / 4.0)]) + np.array([0, 0, 1.6]) * (1 - ease((t - FL[4]) / 1.5))
    return "cierre", O, calavera(*SK, lerp(0.85, 1.0, ease((t - FL[4]) / 1.5)), t)


HL_WORDS = {"desfile", "james", "bond", "broma", "broma…", "spectre", "cdmx", "extras", "nunca", "ciudad?", "realidad!", "edición…",
            "millón", "antiquísima;", "cine.", "desfile", "sí…"}

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



PAPEL = [(255, 84, 160), (255, 160, 40), (79, 216, 255), (160, 110, 255), (120, 230, 120), (255, 216, 77)]


def papel_picado(layer, t, A, y0=290, n=7):
    """Banderines de papel picado (dibujo original)."""
    if A <= 0:
        return
    d = ImageDraw.Draw(layer)
    w = W / n
    d.line([0, y0 - 4, W, y0 + 4], fill=(230, 230, 230, int(A * 0.7)), width=4)
    for k in range(n):
        x0 = k * w + 8; x1 = (k + 1) * w - 8
        sway = 6 * math.sin(t * 2.2 + k)
        col = PAPEL[k % len(PAPEL)]
        top = y0
        bot = y0 + 120 + sway
        pts = [(x0, top), (x1, top), (x1, bot - 18), (x0 + (x1 - x0) * 0.75, bot), (x0 + (x1 - x0) * 0.5, bot - 18),
               (x0 + (x1 - x0) * 0.25, bot), (x0, bot - 18)]
        d.polygon(pts, fill=col + (int(A * 0.9),))
        cx = (x0 + x1) / 2
        # recortes
        d.ellipse([cx - 14, top + 30, cx + 14, top + 58], fill=(0, 0, 0, 0))
        for dx in (-26, 26):
            d.polygon([(cx + dx, top + 70), (cx + dx - 9, top + 86), (cx + dx + 9, top + 86)], fill=(0, 0, 0, 0))
        d.rectangle([cx - 4, top + 66, cx + 4, top + 96], fill=(0, 0, 0, 0))


def clapper(layer, cx, cy, s, A, t, label="2015"):
    d = ImageDraw.Draw(layer)
    w, h = 300 * s, 210 * s
    box(layer, [cx - w / 2, cy - h / 2 + 40 * s, cx + w / 2, cy + h / 2], (20, 22, 30, A), WHITE + (A,), int(5 * s), int(18 * s))
    d = ImageDraw.Draw(layer)
    ang = math.radians(-18 * max(0.0, math.sin(min(1.0, max(0.0, t)) * math.pi)))
    # tablilla superior con franjas
    bx0, by0 = cx - w / 2, cy - h / 2
    pts = [(0, 0), (w, 0), (w, 40 * s), (0, 40 * s)]
    rot = [(bx0 + x * math.cos(ang) - y * math.sin(ang), by0 + x * math.sin(ang) + y * math.cos(ang)) for x, y in pts]
    d.polygon(rot, fill=WHITE + (A,))
    for k in range(5):
        x0 = k * w / 5 + 10 * s
        q = [(x0, 0), (x0 + 30 * s, 0), (x0 + 10 * s, 40 * s), (x0 - 20 * s, 40 * s)]
        q = [(bx0 + x * math.cos(ang) - y * math.sin(ang), by0 + x * math.sin(ang) + y * math.cos(ang)) for x, y in q]
        d.polygon(q, fill=(20, 22, 30, A))
    txt(d, (cx, cy + 40 * s), label, int(82 * s), YELLOW, A, sw=5)


def draw_hook(layer, t, O):
    tt = t if t < FL[0] else 0.0
    papel_picado(layer, t, 255)
    if t < FL[0]:
        draw_label(layer, t, -1, H2["t0"] - 0.05, "JAMES BOND", ["inspiró este desfile"], YELLOW, 140, y0=520)
        al = fade(t, H2["t0"] - 0.05, FL[0], 0.12)
        if al > 0:
            d = ImageDraw.Draw(layer)
            A = int(255 * al)
            k = ease_out((t - H2["t0"] + 0.05) / 0.25)
            txt(d, (W / 2, 560), "Y NO ES BROMA", int(90 + 30 * k), RED, A, sw=8)
    else:
        draw_label(layer, 0.5, -1, 99, "JAMES BOND", ["inspiró este desfile"], YELLOW, 140, y0=520)


def draw_cdmx(layer, t, O):
    d = ImageDraw.Draw(layer)
    x, y = project(O, (0.0, 0.35, 2.2))
    al = fade(t, FL[0] + 2.0, SPE_P2, 0.3)
    if al > 0:
        A = int(255 * al)
        for k in range(3):
            ph = ((t * 1.2) + k / 3) % 1.0
            rr = 22 + 100 * ph
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=YELLOW + (int(A * (1 - ph)),), width=6)
        d.ellipse([x - 15, y - 15, x + 15, y + 15], fill=YELLOW + (A,), outline=INK + (A,), width=4)
        bx = x + 36
        box(layer, [bx, y - 140, bx + 260, y - 52], (10, 16, 40, int(215 * al)), YELLOW + (A,), 4, 28)
        d = ImageDraw.Draw(layer)
        txt(d, (bx + 130, y - 96), "CDMX", 50, WHITE, A, sw=4)
    ac = fade(t, FL[0] + 0.1, SPE_P2, 0.25)
    if ac > 0:
        clapper(layer, W / 2, 1560, 1.0, int(255 * ac), (t - FL[0]) / 0.6)
    draw_label(layer, t, FL[0] + 0.1, SPE_P2, "SPECTRE (2015)", ["abrió con un desfile", "en el Centro Histórico"], YELLOW, 110)


def draw_extras(layer, t, O):
    d = ImageDraw.Draw(layer)
    al = fade(t, SPE_P2 - 0.1, FL[1] + 0.05, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    n = int(1500 * ease_out((t - SPE_P2 + 0.1) / 1.4))
    txt(d, (W / 2, 380), f"+{n:,}", 170, YELLOW, A, sw=9)
    txt(d, (W / 2, 520), "EXTRAS", 76, WHITE, A, sw=7)


def draw_fantasma(layer, t, O):
    d = ImageDraw.Draw(layer)
    al = fade(t, FL[1] + 0.05, FL[2] + 0.05, 0.2)
    if al > 0 and t < PRE0 - 0.1:
        A = int(255 * al)
        txt(d, (W / 2, 380), "NUNCA", 160, RED, A, sw=9)
        txt(d, (W / 2, 520), "había existido", 70, WHITE, A, "Inter-ExtraBold.otf", sw=7)
        # sello "FICCIÓN"
        k = ease_out((t - PROB0 - 1.2) / 0.25)
        if k > 0:
            st = Image.new("RGBA", (620, 220), (0, 0, 0, 0))
            sd = ImageDraw.Draw(st)
            sd.rounded_rectangle([10, 10, 610, 210], radius=24, outline=RED + (int(A * k),), width=12)
            sd.text((310, 112), "SOLO EN EL CINE", font=font("Inter-Black.otf", 66), fill=RED + (int(A * k),), anchor="mm")
            st = st.rotate(-10, expand=True, resample=Image.BICUBIC)
            sc = 1.4 - 0.4 * k
            st = st.resize((int(st.width * sc), int(st.height * sc)), Image.LANCZOS)
            layer.alpha_composite(st, (int(W / 2 - st.width / 2), int(860 - st.height / 2)))
    ap = fade(t, PRE0 - 0.15, FL[2] + 0.05, 0.15)
    if ap > 0:
        A = int(255 * ap)
        k = ease_out((t - PRE0 + 0.15) / 0.3)
        txt(d, (W / 2, 420), "¿Y LA", int(110 + 20 * k), WHITE, A, sw=8)
        txt(d, (W / 2, 560), "CIUDAD?", int(130 + 20 * k), YELLOW, A, sw=8)


def draw_real(layer, t, O):
    papel_picado(layer, t, int(255 * fade(t, FL[2], FL[3] + 0.05, 0.3)), y0=600)
    draw_label(layer, t, FL[2] + 0.1, FL[3], "2016", ["¡lo hizo REALIDAD!"], YELLOW, 190, y0=380)


def draw_hoy(layer, t, O):
    d = ImageDraw.Draw(layer)
    al = fade(t, FL[3] + 0.05, FL[4] + 0.05, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    papel_picado(layer, t, A)
    # 10 velas: una por edición
    n_on = int(min(10, max(0, (t - HOY0) / 0.22 + 1)))
    y = 1540
    for k in range(10):
        x = W / 2 + (k - 4.5) * 92
        on = k < n_on
        d.rectangle([x - 16, y - 10, x + 16, y + 70], fill=(240, 232, 215, A) if on else (90, 90, 100, A))
        if on:
            fl = 1 + 0.15 * math.sin(t * 13 + k * 2)
            d.ellipse([x - 12 * fl, y - 52 * fl, x + 12 * fl, y - 12], fill=(255, 190, 60, A))
            d.ellipse([x - 6, y - 36, x + 6, y - 14], fill=(255, 245, 200, A))
    big = t > P("hoy", 0)[0] + 2.6
    if not big:
        txt(d, (W / 2, 520), "10.ª EDICIÓN", 120, YELLOW, A, sw=8)
        txt(d, (W / 2, 640), "hoy", 60, CYAN, A, "Inter-ExtraBold.otf", sw=6)
    else:
        A2 = int(A * min(1.0, (t - P("hoy", 0)[0] - 2.6) / 0.25))
        txt(d, (W / 2, 520), "+1 MILLÓN", 130, YELLOW, A2, sw=8)
        txt(d, (W / 2, 640), "de personas en los últimos años", 50, CYAN, A2, "Inter-ExtraBold.otf", sw=6)


def draw_endcard(layer, t, t0):
    """Cierre del video: marca y llamada a seguir el canal."""
    al = fade(t, t0, END - 0.3, 0.3)
    if al <= 0:
        return
    A = int(255 * al)
    dim = Image.new("RGBA", (W, H), (6, 8, 18, int(160 * al)))
    layer.alpha_composite(dim)
    d = ImageDraw.Draw(layer)
    k = ease_out((t - t0) / 0.4)
    d.polygon(bolt(W / 2, 780, 230 + 40 * k), fill=YELLOW + (A,))
    txt(d, (W / 2, 1010), "FLASH DATOS", 104, WHITE, A, sw=8)
    txt(d, (W / 2, 1120), "Síguenos para más", 52, CYAN, A, "Inter-ExtraBold.otf", sw=6)
    txt(d, (W / 2, 1185), "curiosidades", 52, CYAN, A, "Inter-ExtraBold.otf", sw=6)


def draw_cierre(layer, t, O):
    papel_picado(layer, t, 255)
    p2 = P("cierre", 1)
    al = fade(t, FL[4] + 0.05, p2[0] + 0.2, 0.25)
    if al > 0:
        A = int(255 * al)
        for k, (yy, top, sub, col) in enumerate([(1500, "TRADICIÓN", "antiquísima", CYAN), (1500, "DESFILE", "nació en el cine", YELLOW)]):
            x = W / 2 + (-1 if k == 0 else 1) * 250
            box(layer, [x - 230, yy - 90, x + 230, yy + 90], (10, 16, 40, int(215 * al)), col + (A,), 5)
            d = ImageDraw.Draw(layer)
            txt(d, (x, yy - 28), top, 58, WHITE, A, sw=5)
            txt(d, (x, yy + 36), sub, 40, col, A, "Inter-ExtraBold.otf", sw=4)
    draw_label(layer, t, p2[0] - 0.05, p2[1] + 0.25, "LA REALIDAD", ["le copió al cine"], YELLOW, 140, y0=520)
    draw_endcard(layer, t, p2[1] + 0.15)


def overlays(frame_u8, t, name, O, bodies):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    {"hook": draw_hook, "cdmx": draw_cdmx, "extras": draw_extras, "fantasma": draw_fantasma, "real": draw_real,
     "hoy": draw_hoy, "cierre": draw_cierre}[name](layer, t, O)
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
    if name in ("hook", "hoy", "cierre", "real"):
        # resplandor naranja de cempasúchil detrás de la escena
        img = img + GLOW * (1.2 if name != "real" else 0.8)
    if name == "fantasma":
        img *= 0.6
    bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"], float) - O)))
    for b in bodies:
        draw_sphere(img, O, b, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, name, O, bodies)


_gy, _gx = np.mgrid[0:H, 0:W]
GLOW = (np.exp(-(((_gx - W / 2) / 520.0) ** 2 + ((_gy - 900) / 700.0) ** 2)) * 0.10)[..., None] * np.array([1.0, 0.45, 0.10], np.float32)
GLOW = GLOW.astype(np.float32)
del _gy, _gx

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
