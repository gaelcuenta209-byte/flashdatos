"""Flash Datos · video 05 · El robo de Binance (trazado de rayos de esferas).

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
    rng = np.random.default_rng(5)
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
    neb = fbm(gx, gy, np.full_like(gx, 0.3), 5, seed=91)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.030, 0.018, 0.006], np.float32)  # tinte dorado muy tenue
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


# ---------------- línea de tiempo ----------------
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
P = lambda sid, k: SEG[sid]["parts"][k]

H1 = SEG["hook1"]; H2 = SEG["hook2"]
BIN0 = SEG["binance"]["t0"]; BIN_P2 = P("binance", 1)[0]
REC0 = SEG["record"]["t0"]; GIRO0 = SEG["giro"]["t0"]
COR0 = SEG["corea"]["t0"]; COR_P2 = P("corea", 1)[0]
CAR0 = SEG["carrera"]["t0"]; CIE0 = SEG["cierre"]["t0"]
FL = [BIN0 - 0.2, REC0 - 0.2, COR0 - 0.2, CAR0 - 0.2, END - 0.32]


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def lerp(a, b, s):
    return a + (b - a) * s


# ---------------- bóveda de monedas ----------------
RNG = np.random.default_rng(42)
NCOIN = 150
_k = np.arange(NCOIN) + 0.5
_phi = np.arccos(1 - 2 * _k / NCOIN); _th = math.pi * (1 + 5 ** 0.5) * _k
_rad = 1.85 * (0.35 + 0.65 * RNG.random(NCOIN) ** 0.5)
PILE = np.stack([np.cos(_th) * np.sin(_phi), np.cos(_phi) * 0.92, np.sin(_th) * np.sin(_phi)], -1) * _rad[:, None] + np.array([0.0, 0.35, 0.0])
FLYDIR = PILE - np.array([0.0, 0.35, 0.0]); FLYDIR /= np.linalg.norm(FLYDIR, axis=-1, keepdims=True)
FLYDIR = FLYDIR + RNG.normal(0, 0.25, FLYDIR.shape); FLYDIR /= np.linalg.norm(FLYDIR, axis=-1, keepdims=True)
LAUNCH = np.sort(RNG.uniform(0.7, 6.0, NCOIN))[RNG.permutation(NCOIN)]
COIN_R = 0.17 * (0.85 + 0.3 * RNG.random(NCOIN))
FROZEN = RNG.random(NCOIN) < 0.52           # algo más de la mitad: "más de 3,000 de 6,300 millones"
FREEZE_T = CAR0 + 0.15 + 1.3 * RNG.random(NCOIN)
SCATTER_T = CIE0 + 0.4 + 4.5 * RNG.random(NCOIN)
O_PILE = np.array([0.0, 0.0, 9.6])


def pile_coins(t, mode):
    out = []
    for i in range(NCOIN):
        p = PILE[i]; r = COIN_R[i]; kind = "gold"; op = 1.0
        wob = 0.03 * math.sin(t * 2.1 + i)
        p = p + np.array([0.0, wob, 0.0])
        if mode == "hook":
            dt = t - LAUNCH[i]
            if dt > 0:
                s = dt * 2.2 + dt * dt * 3.5
                p = p + FLYDIR[i] * s
                op = max(0.0, 1 - dt / 1.4)
                if op <= 0:
                    continue
        else:  # carrera / cierre
            if FROZEN[i] and t >= FREEZE_T[i]:
                kind = "ice"
            if not FROZEN[i]:
                dt = t - SCATTER_T[i]
                if dt > 0:
                    s = dt * 1.6 + dt * dt * 2.2
                    p = p + FLYDIR[i] * s
                    r = r * max(0.15, 1 - dt / 1.6)
                    op = max(0.0, 1 - dt / 1.5)
                    if op <= 0:
                        continue
        out.append(dict(kind=kind, c=tuple(p), r=r, op=op))
    return out


# ---------------- Tierra con anillo y 10 cadenas ----------------
E_BIN = (0.0, -0.55, 0.0); R_BIN = 1.95
O_BIN = np.array([0.0, 0.25, 9.0])
NRING = 60
RING_TILT = math.radians(18)
CHAIN_COLS = [(255, 216, 77), (79, 216, 255), (255, 120, 180), (140, 255, 160), (255, 160, 80),
              (190, 150, 255), (255, 255, 255), (80, 255, 230), (255, 90, 90), (170, 210, 255)]
CHAIN_T = [BIN_P2 + 0.1 + 0.2 * k for k in range(10)]


def ring_pos(i, t):
    a = 2 * math.pi * i / NRING + 0.35 * t
    v = np.array([math.cos(a) * 2.9, 0.0, math.sin(a) * 2.9])
    c, s = math.cos(RING_TILT), math.sin(RING_TILT)
    v = np.array([v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c])
    return np.array(E_BIN) + v


def chain_dir(k):
    a = math.radians(18 + k * 16)
    return np.array([math.cos(a), math.sin(a), 0.12])


def chain_origin(k):
    d = chain_dir(k); d = d / np.linalg.norm(d)
    return np.array(E_BIN) + d * R_BIN * 1.04, d


def bin_coins(t):
    out = []
    for k in range(10):
        org, d = chain_origin(k)
        for j in range(6):
            i = k * 6 + j
            rp = ring_pos(i, t)
            if t < CHAIN_T[k]:
                out.append(dict(kind="gold", c=tuple(rp), r=0.11)); continue
            dt = t - CHAIN_T[k]
            s = dt * 3.4 - j * 0.5
            if s < 0:
                u = ease(dt / (j * 0.5 / 3.4 + 1e-3))
                p = lerp(rp, org, u)
            else:
                p = org + d * s
            out.append(dict(kind="gold", c=tuple(p), r=0.11))
    return out


# ---------------- Récord: Bybit vs Binance ----------------
R_BIG = 1.35; R_SMALL = R_BIG * math.sqrt(1.5 / 6.3)  # área proporcional al monto
O_REC = np.array([0.0, 0.0, 11.2])


# ---------------- Corea ----------------
E_KOR = (0.0, 0.35, 0.0); R_KOR = 2.2
O_KOR = np.array([0.0, 0.1, 9.8])
KOR_LAT, KOR_LON = 39.5, 127.0


def scene(t):
    if t < FL[0]:
        bodies = pile_coins(t, "hook")
        return "hook", O_PILE - np.array([0, 0, 0.35 * ease_out(t / 6.5)]), bodies
    if t < FL[1]:
        s = ease((t - FL[0]) / 1.4)
        spin = lerp(-1.2, -0.2, (t - FL[0]) / (FL[1] - FL[0]))
        O = O_BIN - np.array([0.0, 0.0, 0.8 * s]) + np.array([0, 0.0, 0.0])
        if t > BIN_P2:
            O = O + np.array([0.0, 0.35, 1.2]) * ease((t - BIN_P2) / 1.5)
        earth = dict(kind="earth", c=E_BIN, r=R_BIN, tilt=12, spin=spin)
        return "binance", O, [earth] + bin_coins(t)
    if t < FL[2]:
        g = ease_out((t - REC0 - 0.5) / 0.9)
        dim = 1.0 if t < GIRO0 else lerp(1.0, 0.25, ease((t - GIRO0) / 0.8))
        O = O_REC - np.array([0, 0, 0.6 * ease((t - FL[1]) / (FL[2] - FL[1]))])
        bodies = [dict(kind="gold", c=(-1.45, -0.55, 0.0), r=R_SMALL * ease_out((t - FL[1]) / 0.6), gain=dim),
                  dict(kind="gold", c=(0.78, -0.55, 0.0), r=max(R_SMALL, R_BIG * g) if t > REC0 + 0.5 else R_SMALL * 0.0, gain=dim)]
        return "record", O, bodies
    if t < FL[3]:
        u = ease((t - FL[2]) / 2.6)
        spin = math.radians(lerp(60, KOR_LON, u)); tilt = lerp(20, KOR_LAT, u)
        O = O_KOR - np.array([0, 0, 0.9 * ease((t - FL[2]) / (FL[3] - FL[2]))])
        earth = dict(kind="earth", c=E_KOR, r=R_KOR, tilt=tilt, spin=spin)
        bodies = [earth]
        if t > COR_P2:  # monedas que caen hacia el marcador
            tgt = np.array(E_KOR) + np.array([0, 0, R_KOR])
            for j in range(14):
                st = COR_P2 + 0.25 * j
                dt = t - st
                if dt < 0:
                    continue
                ph = (dt % 2.2) / 2.2
                a = j * 2.4
                start = tgt + np.array([math.cos(a) * 3.2, 2.6 + math.sin(a) * 0.8, 1.2])
                p = lerp(start, tgt, ease(ph))
                bodies.append(dict(kind="gold", c=tuple(p), r=0.09 * (1 - 0.6 * ph), op=1.0))
        return "corea", O, bodies
    bodies = pile_coins(t, "carrera")
    return "carrera", O_PILE + np.array([0, 0, 0.6 * ease((t - FL[3]) / 2.0)]), bodies


# ---------------- subtítulos y textos ----------------
HL_WORDS = {"millones", "minutos", "binance", "blockchains", "robo", "cripto", "historia", "récord", "quién", "quién.", "cuánto",
            "tradertraitor", "corea", "norte", "nuclear", "congelaron", "resto", "resto?", "esconderlo", "banco", "banco…", "no"}


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


def draw_clock(layer, t, a, b):
    al = fade(t, a, b, 0.2)
    if al <= 0:
        return
    A = int(255 * al)
    u = min(1.0, max(0.0, (t - 0.6) / 5.4))
    secs = int(u * 20 * 60)
    s = f"{secs // 60:02d}:{secs % 60:02d}"
    cx, cy = W / 2, 1530
    box(layer, [cx - 250, cy - 78, cx + 250, cy + 78], (10, 16, 40, int(215 * al)), RED + (A,), 5)
    d = ImageDraw.Draw(layer)
    # ícono de reloj
    ix = cx - 170
    d.ellipse([ix - 42, cy - 42, ix + 42, cy + 42], outline=WHITE + (A,), width=7)
    ang = -math.pi / 2 + u * 2 * math.pi * 6
    d.line([ix, cy, ix + 30 * math.cos(ang), cy + 30 * math.sin(ang)], fill=RED + (A,), width=7)
    d.line([ix, cy, ix, cy - 24], fill=WHITE + (A,), width=6)
    txt(d, (cx + 55, cy), s, 92, WHITE if u < 1 else RED, A, sw=6)


def draw_hook(layer, t):
    draw_label(layer, t, -1, H1["t1"] + 0.2, "$6,300 MILLONES", ["desaparecieron"], YELLOW, 122)
    draw_clock(layer, t, -1, H1["t1"] + 0.25)
    al = fade(t, H2["t0"] - 0.1, FL[0], 0.15)
    if al > 0:
        A = int(255 * al)
        d = ImageDraw.Draw(layer)
        cx, cy = W / 2, 760
        # banco tachado
        box(layer, [cx - 230, cy - 200, cx + 230, cy + 200], (10, 16, 40, int(200 * al)), WHITE + (int(120 * al),), 4)
        d.polygon([(cx - 170, cy - 60), (cx, cy - 150), (cx + 170, cy - 60)], fill=WHITE + (A,))
        for k in range(4):
            x = cx - 120 + k * 80
            d.rectangle([x - 18, cy - 45, x + 18, cy + 90], fill=WHITE + (A,))
        d.rectangle([cx - 175, cy + 100, cx + 175, cy + 130], fill=WHITE + (A,))
        d.line([cx - 210, cy - 180, cx + 210, cy + 180], fill=RED + (A,), width=26)
        txt(d, (W / 2, 420), "NO FUE UN BANCO", 104, RED, A)


def draw_binance(layer, t, O):
    draw_label(layer, t, FL[0] + 0.1, BIN_P2 - 0.05, "BINANCE", ["la casa de cripto más", "grande del mundo"], YELLOW, 140)
    al = fade(t, BIN_P2 - 0.05, FL[1] + 0.05, 0.25)
    if al <= 0:
        return
    A = int(255 * al)
    n = sum(1 for ct in CHAIN_T if t >= ct)
    d = ImageDraw.Draw(layer)
    txt(d, (W / 2, 380), f"{n}", 190, YELLOW, A, sw=9)
    txt(d, (W / 2, 520), "BLOCKCHAINS" if n != 1 else "BLOCKCHAIN", 64, WHITE, A)
    # estelas de cada cadena
    big = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db = ImageDraw.Draw(big)
    for k in range(10):
        if t < CHAIN_T[k]:
            continue
        dt = t - CHAIN_T[k]
        p0, dd = chain_origin(k)
        L = min(9.0, dt * 3.4 + 0.2)
        pts = [project(O, p0 + dd * s) for s in np.linspace(0, L, 12)]
        a2 = int(A * min(1.0, dt / 0.25) * 0.85)
        db.line(pts, fill=CHAIN_COLS[k] + (a2,), width=9, joint="curve")
    layer.alpha_composite(big)


def draw_record(layer, t, O):
    d = ImageDraw.Draw(layer)
    al = fade(t, FL[1] + 0.1, GIRO0 + 0.25, 0.25)
    if al > 0:
        A = int(255 * al)
        xs_, ys_ = project(O, (-1.45, -0.55 - R_SMALL - 0.3, 0.0))
        txt(d, (xs_, ys_ + 10), "BYBIT 2025", 46, WHITE, A, "Inter-ExtraBold.otf", sw=5)
        txt(d, (xs_, ys_ + 64), "$1,500 M", 54, CYAN, A, sw=5)
        if t > REC0 + 0.6:
            A2 = int(A * min(1.0, (t - REC0 - 0.6) / 0.3))
            xb, yb = project(O, (0.78, -0.55 - R_BIG - 0.3, 0.0))
            txt(d, (xb, yb + 10), "BINANCE 2026", 50, WHITE, A2, "Inter-ExtraBold.otf", sw=5)
            txt(d, (xb, yb + 70), "$6,300 M", 64, YELLOW, A2, sw=6)
    draw_label(layer, t, REC0 + 0.6, GIRO0, "RÉCORD", ["más de 4 veces el anterior"], YELLOW, 150)
    ag = fade(t, GIRO0 + 0.1, FL[2] + 0.05, 0.25)
    if ag > 0:
        A = int(255 * ag)
        k = ease_out((t - GIRO0 - 0.1) / 0.5)
        size = int(560 + 160 * k)
        d.text((W / 2, 820), "?", font=font("Inter-Black.otf", size), fill=YELLOW + (A,), anchor="mm", stroke_width=14, stroke_fill=INK + (A,))
        txt(d, (W / 2, 380), "¿QUIÉN?", 140, WHITE, A, sw=8)


def draw_korea(layer, t, O):
    tgt = np.array(E_KOR) + np.array([0, 0, R_KOR])
    x, y = project(O, tgt)
    al = fade(t, FL[2] + 2.3, FL[3] + 0.05, 0.3)
    if al > 0:
        A = int(255 * al)
        d = ImageDraw.Draw(layer)
        for k in range(3):
            ph = ((t * 1.3) + k / 3) % 1.0
            rr = 20 + 110 * ph
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=RED + (int(A * (1 - ph)),), width=6)
        d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=RED + (A,), outline=WHITE + (A,), width=4)
        bx = x + 40
        box(layer, [bx, y - 140, bx + 430, y - 50], (10, 16, 40, int(215 * al)), RED + (A,), 4, 28)
        d = ImageDraw.Draw(layer)
        txt(d, (bx + 215, y - 95), "COREA DEL NORTE", 44, WHITE, A, sw=4)
    draw_label(layer, t, FL[2] + 0.1, COR_P2 - 0.05, "TRADERTRAITOR", ["hackers de élite", "según TRM Labs y Chainalysis"], RED, 112)
    draw_label(layer, t, COR_P2 - 0.05, FL[3], "¿PARA QUÉ?", ["su programa nuclear,", "según expertos"], YELLOW, 130)


def draw_carrera(layer, t):
    nf = int(sum(1 for i in range(NCOIN) if FROZEN[i] and t >= FREEZE_T[i]) / max(1, FROZEN.sum()) * 3000)
    al = fade(t, FL[3] + 0.1, CIE0 + 0.1, 0.25)
    if al > 0:
        A = int(255 * al)
        d = ImageDraw.Draw(layer)
        txt(d, (W / 2, 360), f"+${nf:,} M", 120, CYAN, A, sw=8)
        txt(d, (W / 2, 470), "CONGELADOS", 64, WHITE, A)
    ar = fade(t, P("carrera", 0)[1] - 0.9, CIE0 + 0.2, 0.2)
    if ar > 0:
        d = ImageDraw.Draw(layer)
        txt(d, (W / 2, 1560), "¿Y EL RESTO?", 96, YELLOW, int(255 * ar), sw=8)
    draw_label(layer, t, CIE0 + 0.1, END - 0.5, "CONTRARRELOJ", ["los hackers intentan", "esconder el resto"], YELLOW, 120)


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


def overlays(frame_u8, t, name, O):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if name == "hook":
        draw_hook(layer, t)
    elif name == "binance":
        draw_binance(layer, t, O)
    elif name == "record":
        draw_record(layer, t, O)
    elif name == "corea":
        draw_korea(layer, t, O)
    else:
        draw_carrera(layer, t)
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
    if name == "record" and t > GIRO0:
        img *= lerp(1.0, 0.4, ease((t - GIRO0) / 0.8))
    bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"], float) - O)))
    for b in bodies:
        draw_sphere(img, O, b, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, name, O)


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
