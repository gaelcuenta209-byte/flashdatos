"""Flash Datos · renderizador 3D (trazado de rayos de esferas) para el video 01.

Uso:
  python3 render.py test 0.0 9.0 ...        -> PNG de prueba en frames_test/
  python3 render.py chunk <ini> <fin> <out> -> MP4 de los cuadros [ini, fin)
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom as ndzoom

BASE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
TY = math.tan(math.radians(20)); TX = TY * W / H
PIX = 2 * TY / H

# ---------------- datos físicos (unidades: radios terrestres) ----------------
RE = 1.0
RJ = 69911 / 6371
RS = 696000 / 6371
RB = 764 * RS                      # Betelgeuse, ~764 radios solares (Joyce et al. 2020)
AU = 149597870.7 / 6371
GAP = 1.8
Y_S = GAP * RS + RS
Y_J = Y_S + RS + GAP * RJ + RJ
Y_E = Y_J + RJ + GAP * RE + RE

# ---------------- rayos de cámara ----------------
xs = ((np.arange(W) + 0.5) / W * 2 - 1) * TX
ys = (1 - (np.arange(H) + 0.5) / H * 2) * TY
DX, DY = np.meshgrid(xs, ys)
NRM = np.sqrt(DX * DX + DY * DY + 1)
DIRS = np.stack([DX / NRM, DY / NRM, -1 / NRM], axis=-1)

LIGHT = np.array([-0.62, 0.50, 0.60]); LIGHT /= np.linalg.norm(LIGHT)


def lin(c):
    return np.asarray(c, dtype=np.float32) ** 2.2


T = lambda n: np.load(os.path.join(BASE, "tex", n + ".npy"))
EARTH = lin(np.clip(T("earth"), 0, 1)); CLOUDS = T("earth_clouds"); LAND = T("earth_land")
JUP = lin(np.clip(T("jupiter"), 0, 1)); SUN = T("sun"); BET = T("betelgeuse")


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


# ---------------- fondo estrellado ----------------
def make_background():
    rng = np.random.default_rng(3)
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
    # nebulosa muy tenue
    from noise import fbm
    gy, gx = np.mgrid[0:120, 0:68] / 40.0
    neb = fbm(gx, gy, np.full_like(gx, 0.7), 5, seed=77)
    neb = ndzoom(neb, (H / 120, W / 68), order=1)
    neb = np.clip((neb - 0.45) * 2.2, 0, 1) ** 1.6
    bg += neb[..., None] * np.array([0.020, 0.010, 0.040], np.float32)
    return bg


BG = make_background()

# ---------------- cuerpos ----------------
def stack_bodies():
    return [
        dict(n="bet", c=(0.0, -RB, 0.0), r=RB, kind="star", tex=BET, cc=(1.0, 0.20, 0.05), ce=(0.42, 0.03, 0.01), k=1.45, rot=0.003),
        dict(n="sun", c=(0.0, Y_S, 0.0), r=RS, kind="star", tex=SUN, cc=(1.0, 0.62, 0.20), ce=(0.92, 0.20, 0.02), k=2.3, rot=0.02),
        dict(n="jup", c=(0.0, Y_J, 0.0), r=RJ, kind="jup", rot=0.10),
        dict(n="earth", c=(0.0, Y_E, 0.0), r=RE, kind="earth", rot=0.045),
    ]


def diagram_bodies():
    return [dict(n="bet", c=(0.0, 0.0, 0.0), r=RB, kind="star", tex=BET, cc=(1.0, 0.20, 0.05), ce=(0.42, 0.03, 0.01), k=1.45, rot=0.003)]


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


def shade(body, n, V, t, ndl):
    kind = body["kind"]
    if kind == "star":
        loc = rot_y(n, body["rot"] * t)
        la, lo = latlon(loc)
        g = sample(body["tex"], la, lo)
        mu = np.clip((n * V).sum(-1), 0, 1)
        cc = np.array(body["cc"], np.float32); ce = np.array(body["ce"], np.float32)
        w = (mu ** 0.6)[..., None]
        col = ce * (1 - w) + cc * w
        return col * (body["k"] * (0.55 + 0.9 * (g - 0.55)) * (0.22 + 0.78 * mu ** 0.55))[..., None]
    diff = np.clip(ndl, 0, 1)
    soft = smooth(-0.15, 0.35, ndl) * 0.10
    light = (0.018 + 2.1 * diff + soft)[..., None]
    if kind == "jup":
        loc = rot_y(rot_x(n, math.radians(-8)), body["rot"] * t + 0.4)
        la, lo = latlon(loc)
        alb = sample(JUP, la, lo)
        mu = np.clip((n * V).sum(-1), 0, 1)
        col = alb * light * (0.75 + 0.25 * mu ** 0.5)[..., None]
        return col
    # Tierra: inclinada para mostrar México y América
    loc = rot_y(rot_x(n, math.radians(16)), -1.72 + body["rot"] * t)
    la, lo = latlon(loc)
    alb = sample(EARTH, la, lo)
    cl = sample(CLOUDS, la, lo + 0.015 * t)[..., None]
    land = sample(LAND, la, lo)
    col = alb * (1 - cl * 0.88) + 0.80 * cl * 0.88
    R = 2 * ndl[..., None] * n - LIGHT
    spec = np.clip((R * V).sum(-1), 0, 1) ** 45 * (1 - land) * (1 - cl[..., 0]) * 0.9
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
    ang = math.asin(r / dist_c)
    rpx = math.tan(ang) / PIX
    halo = 1.10 if body["kind"] == "earth" else 1.0
    if rpx < 0.8:  # demasiado pequeño: punto luminoso
        if not (-5 < cxp < W + 5 and -5 < cyp < H + 5):
            return
        if body["kind"] == "star":
            amp = np.array(body["cc"]) * body["k"] * 3.0 * max(rpx, 0.25) ** 2 * 4
        else:
            amp = np.array([0.6, 0.6, 0.6]) * max(rpx, 0.2) ** 2
        yy, xx = np.mgrid[-4:5, -4:5]
        g = np.exp(-(xx ** 2 + yy ** 2) / (2 * 0.75 ** 2))
        ix, iy = int(round(cxp)), int(round(cyp))
        y0, y1 = max(iy - 4, 0), min(iy + 5, H); x0, x1 = max(ix - 4, 0), min(ix + 5, W)
        if y0 < y1 and x0 < x1:
            img[y0:y1, x0:x1] += g[(y0 - iy + 4):(y1 - iy + 4), (x0 - ix + 4):(x1 - ix + 4), None] * amp
        return
    ext = rpx * halo * 1.15 + 4
    # en perspectiva, una esfera grande se deforma cerca de los bordes: margen generoso
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
    disc = np.maximum(r * r - perp2[sel], 0)
    tt = -bs - np.sqrt(disc)
    P = O + tt[:, None] * ds
    n = P - C; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    V = -ds
    ndl = n @ LIGHT
    col = shade(body, n, V, t, ndl)
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

K = {
    "earth": (Y_E, 5.2),
    "jup": (Y_J + 0.3 * RJ, 7.6 * RJ),
    "sun": (Y_S + 0.25 * RS, 7.6 * RS),
    "bet_h": (1154.0, 9606.0),
    "bet_full": (-0.86 * RB, RB / (0.80 * TX)),
}
D_DIAG0 = 1.15 * RB / TX
D_DIAG1 = 1.12 * 5.203 * AU / TX

F1 = SEG["tierra"]["t0"] - 0.25
F2 = SEG["orbitas"]["t0"] - 0.15
F3 = SEG["cierre1"]["t0"] + 1.4
F4 = END - 0.32
FLASHES = [F1, F2, F3, F4]


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = min(max(s, 0.0), 1.0)
    return 1 - (1 - s) ** 3


def move(ka, kb, s):
    (ya, da), (yb, db) = ka, kb
    D = math.exp(math.log(da) + (math.log(db) - math.log(da)) * s)
    w = (D - da) / (db - da) if abs(db - da) > 1e-9 else s
    return ya + (yb - ya) * w, D


def push(k, s, amt=0.06):
    y, d = k
    return y, d * (1 - amt * s)


def camera(t):
    """Devuelve (escena, y, D)."""
    if t < F1:
        if t < 2.9:
            return ("stack",) + move(K["earth"], K["sun"], ease_out(t / 2.9))
        return ("stack",) + push(K["sun"], (t - 2.9) / (F1 - 2.9), 0.08)
    j0 = SEG["jupiter"]["t0"]; s0 = SEG["sol"]["t0"]; b0 = SEG["betel"]["t0"]
    if t < j0:
        return ("stack",) + push((K["earth"][0], 5.7), (t - F1) / (j0 - F1), 0.09)
    if t < s0:
        if t < j0 + 1.9:
            return ("stack",) + move(K["earth"], K["jup"], ease((t - j0) / 1.9))
        return ("stack",) + push(K["jup"], (t - j0 - 1.9) / (s0 - j0 - 1.9), 0.06)
    if t < b0:
        if t < s0 + 2.0:
            return ("stack",) + move(K["jup"], K["sun"], ease((t - s0) / 2.0))
        return ("stack",) + push(K["sun"], (t - s0 - 2.0) / (b0 - s0 - 2.0), 0.06)
    if t < F2:
        if t < b0 + 2.2:
            return ("stack",) + move(K["sun"], K["bet_h"], ease((t - b0) / 2.2))
        return ("stack",) + push(K["bet_h"], (t - b0 - 2.2) / max(F2 - b0 - 2.2, 0.1), 0.05)
    if t < F3:
        z0 = ring_times()[3] + 0.6
        if t < z0:
            return ("diag", 0.0, D_DIAG0 * (1 - 0.03 * (t - F2) / max(z0 - F2, 0.1)))
        s = ease((t - z0) / max(F3 - z0 - 0.1, 0.1))
        return ("diag", 0.0, math.exp(math.log(D_DIAG0 * 0.97) + (math.log(D_DIAG1) - math.log(D_DIAG0 * 0.97)) * s))
    if t < F4:
        c2 = SEG["cierre2"]["t0"]
        return ("stack",) + move(K["bet_h"], K["bet_full"], ease((t - F3) / max(c2 + 0.5 - F3, 0.1)))
    return ("stack",) + K["earth"]


# ---------------- subtítulos ----------------
HL_WORDS = {"millones", "diminuto", "betelgeuse", "marte", "mercurio", "venus", "km"}


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


def word_times(seg):
    words = seg["say"].split()
    wts = [len(w) + 1 + (3 if w[-1] in ".,:…?" else 0) for w in words]
    tot = sum(wts); t = seg["t0"]; out = []
    for w, wt in zip(words, wts):
        out.append((w.strip(".,…?¿:").lower(), t)); t += (seg["t1"] - seg["t0"]) * wt / tot
    return out


def ring_times():
    return TM["rings"]


CAPS = []
for s in TM["segments"]:
    for t0, t1, txt in s["parts"]:
        CAPS += groups_for_part(t0, t1, txt)
for i in range(len(CAPS) - 1):  # sostener el subtítulo en pausas cortas
    if CAPS[i + 1][0] - CAPS[i][1] < 0.7:
        CAPS[i][1] = CAPS[i + 1][0]

FD = os.path.join(BASE, "fonts", "") if os.path.isdir(os.path.join(BASE, "fonts")) else "/usr/share/fonts/opentype/inter/"
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255)


def is_hl(w):
    core = w.strip(".,:…?¿!").lower()
    return any(ch.isdigit() for ch in core) or core in HL_WORDS


def draw_caption(layer, t):
    for (t0, t1, g) in CAPS:
        if t0 <= t < t1:
            k = min(1.0, (t - t0) / 0.09)
            size = int(round(80 * (1.12 - 0.12 * k)))
            f = font("Inter-Black.otf", size)
            d = ImageDraw.Draw(layer)
            space = d.textlength(" ", font=f)
            widths = [d.textlength(w, font=f) for w in g]
            total = sum(widths) + space * (len(g) - 1)
            x = W / 2 - total / 2; y = 1250
            for w, wd in zip(g, widths):
                col = YELLOW if is_hl(w) else WHITE
                d.text((x, y), w, font=f, fill=col + (255,), anchor="lm", stroke_width=9, stroke_fill=(8, 10, 20, 255))
                x += wd + space
            return


def fade(t, a, b, f=0.25):
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / f, (b - t) / f)


def draw_label(layer, t, a, b, title, subs, title_col=WHITE, title_size=118):
    al = fade(t, a, b)
    if al <= 0:
        return
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rise = (1 - min(1.0, (t - a) / 0.3)) * 24
    y = 360 + rise
    d.text((W / 2, y), title, font=font("Inter-Black.otf", title_size), fill=title_col + (A,), anchor="mm", stroke_width=8, stroke_fill=(8, 10, 20, A))
    y += title_size * 0.5 + 44
    for s in subs:
        d.text((W / 2, y), s, font=font("Inter-ExtraBold.otf", 54), fill=CYAN + (A,), anchor="mm", stroke_width=7, stroke_fill=(8, 10, 20, A))
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
    d.text((x + 40, 212), txt, font=f, fill=(255, 255, 255, 215), anchor="lm", stroke_width=4, stroke_fill=(8, 10, 20, 160))


ORB = [("Mercurio", 0.387, (235, 235, 235)), ("Venus", 0.723, (255, 209, 102)), ("Tierra", 1.0, (79, 216, 255)), ("Marte", 1.524, (255, 150, 180))]
JUP_ORB = ("Júpiter", 5.203, (184, 242, 139))


def draw_diagram(layer, t, D):
    rt = ring_times()
    scale = (H / 2) / (D * TY)
    S2 = 2
    big = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy = W / 2 * S2, H / 2 * S2
    items = ORB + [JUP_ORB]
    for i, (name, au, col) in enumerate(items):
        t0 = rt[i]
        if t < t0:
            continue
        k = min(1.0, (t - t0) / 0.45)
        R = au * AU * scale * S2
        bb = [cx - R, cy - R, cx + R, cy + R]
        d.arc(bb, -90, -90 + 360 * k, fill=col + (255,), width=10)
    big = big.resize((W, H), Image.LANCZOS)
    layer.alpha_composite(big)
    # leyenda
    d = ImageDraw.Draw(layer)
    al = fade(t, F2 + 0.1, F3 + 1, 0.25)
    A = int(255 * al)
    d.text((W / 2, 330), "Betelgeuse en lugar del Sol", font=font("Inter-Black.otf", 64), fill=WHITE + (A,), anchor="mm", stroke_width=7, stroke_fill=(8, 10, 20, A))
    rows = [items[0:2], items[2:4], items[4:5]]
    y = 425
    idx = 0
    for row in rows:
        f = font("Inter-ExtraBold.otf", 48)
        labels = [(n + (" (queda fuera)" if n == "Júpiter" else "")) for n, _, _ in row]
        widths = [d.textlength(l, font=f) + 46 for l in labels]
        total = sum(widths) + 50 * (len(row) - 1)
        x = W / 2 - total / 2
        for (n, au, col), lab, wd in zip(row, labels, widths):
            ti = rt[idx]; idx += 1
            if t >= ti:
                a2 = int(A * min(1.0, (t - ti) / 0.2))
                d.ellipse([x, y - 14, x + 28, y + 14], fill=col + (a2,))
                d.text((x + 44, y), lab, font=f, fill=WHITE + (a2,), anchor="lm", stroke_width=6, stroke_fill=(8, 10, 20, a2))
            x += wd + 50
        y += 66


def draw_marker(layer, t, cam):
    c2 = SEG["cierre2"]["t0"]
    al = fade(t, c2, F4 + 0.05, 0.2)
    if al <= 0:
        return
    _, cyw, D = cam
    rel_y = Y_S - cyw
    sx = W / 2; sy = (1 - rel_y / D / TY) / 2 * H
    A = int(255 * al)
    d = ImageDraw.Draw(layer)
    rr = 30 + 6 * math.sin((t - c2) * 8)
    d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], outline=YELLOW + (A,), width=6)
    d.line([sx, sy - rr, sx, sy - 190], fill=YELLOW + (A,), width=5)
    f = font("Inter-Black.otf", 52)
    d.text((sx, sy - 316), "Aquí están el Sol,", font=f, fill=WHITE + (A,), anchor="mm", stroke_width=7, stroke_fill=(8, 10, 20, A))
    d.text((sx, sy - 250), "Júpiter y la Tierra", font=f, fill=WHITE + (A,), anchor="mm", stroke_width=7, stroke_fill=(8, 10, 20, A))


def flash_alpha(t):
    a = 0.0
    for tf in FLASHES:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


def overlays(frame_u8, t, cam):
    im = Image.fromarray(frame_u8).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if cam[0] == "diag":
        draw_diagram(layer, t, cam[2])
    s = SEG
    draw_label(layer, t, -1, F1, "1.3 MILLONES", ["de Tierras caben en el Sol"], YELLOW, 124)
    draw_label(layer, t, s["tierra"]["t0"] + 0.15, s["jupiter"]["t0"], "TIERRA", ["12,742 km de diámetro"])
    draw_label(layer, t, s["jupiter"]["t0"] + 1.0, s["sol"]["t0"], "JÚPITER", ["11 veces más ancho", "+1,300 Tierras adentro"])
    draw_label(layer, t, s["sol"]["t0"] + 1.2, s["betel"]["t0"], "SOL", ["109 veces más ancho", "1.3 millones de Tierras"])
    draw_label(layer, t, s["betel"]["t0"] + 1.4, F2, "BETELGEUSE", ["supergigante roja"], (255, 120, 80), 110)
    if cam[0] == "stack" and F3 <= t < F4 + 0.1:
        draw_marker(layer, t, cam)
    draw_caption(layer, t)
    draw_watermark(layer)
    im.alpha_composite(layer)
    fa = flash_alpha(t)
    if fa > 0:
        fl = Image.new("RGBA", (W, H), (225, 248, 255, int(235 * fa)))
        im.alpha_composite(fl)
        if fa > 0.35:
            b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(b).polygon(bolt(W / 2, H / 2, 420), fill=YELLOW + (int(255 * min(1, (fa - 0.35) / 0.4)),))
            im.alpha_composite(b)
    return np.asarray(im.convert("RGB"))


def render(t):
    cam = camera(t)
    scene, cy, D = cam
    O = np.array([0.0, cy, D])
    img = BG.copy()
    bodies = stack_bodies() if scene == "stack" else diagram_bodies()
    bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"]) - O)))
    for b in bodies:
        draw_sphere(img, O, b, t)
    img = bloom(img)
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    return overlays(u8, t, cam)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        for ts in sys.argv[2:]:
            t = float(ts)
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, camera(t), flush=True)
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
        print("frames", NFRAMES, "rings", ring_times())
