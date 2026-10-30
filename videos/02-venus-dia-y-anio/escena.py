"""Flash Datos · video 02 · "En Venus, un día dura más que un año".

Escenas: Venus de cerca (gancho y día de 243 días) → órbita alrededor del Sol con la carrera día/año →
Venus girando al revés → amanecer por el oeste sobre las nubes → ecuador a 6.5 km/h → regreso al encuadre inicial.

Uso:
  python3 escena.py test 0.0 9.0 ...        -> PNG de prueba en frames_test/
  python3 escena.py chunk <ini> <fin> <out> -> MP4 de los cuadros [ini, fin)
  python3 escena.py info
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
VEN = lin(np.clip(T("venus"), 0, 1)); SUNT = T("sun")
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


# ---------------- sombreado ----------------
def shade(body, n, V, t, L):
    ndl = (n * L).sum(-1)
    mu = np.clip((n * V).sum(-1), 0, 1)
    if body["kind"] == "star":
        loc = rot_y(n, 0.02 * t)
        la, lo = latlon(loc)
        g = sample(SUNT, la, lo)
        cc = np.array((1.0, 0.62, 0.20), np.float32); ce = np.array((0.92, 0.20, 0.02), np.float32)
        w = (mu ** 0.6)[..., None]
        col = ce * (1 - w) + cc * w
        return col * (2.3 * (0.55 + 0.9 * (g - 0.55)) * (0.22 + 0.78 * mu ** 0.55))[..., None]
    # Venus: nubes con rotación retrógrada (el ángulo crece = la cara visible se mueve de derecha a izquierda)
    loc = rot_y(rot_x(n, math.radians(-12)), body["spin"])
    la, lo = latlon(loc)
    alb = sample(VEN, la, lo)
    diff = np.clip(ndl, 0, 1)
    soft = smooth(-0.25, 0.35, ndl) * 0.10
    light = body.get("amb", 0.02) + 1.15 * diff ** 0.85 + soft
    col = alb * np.array([1.0, 0.80, 0.52]) * light[..., None]
    if body.get("equator", 0) > 0:
        eq = np.exp(-(la / 0.018) ** 2) * body["equator"]
        col = col * (1 - eq[..., None]) + CYAN_F * 1.6 * eq[..., None]
    if body.get("marker", 0) > 0:
        m = np.array([0.0, 0.0, 1.0])  # punto del ecuador en coordenadas locales
        dot = np.clip((loc * m).sum(-1), -1, 1)
        ang = np.arccos(dot)
        spot = np.exp(-(ang / 0.055) ** 2) * body["marker"]
        ring = np.exp(-((ang - 0.10) / 0.018) ** 2) * body["marker"] * 0.8
        col = col * (1 - spot[..., None]) + CYAN_F * 2.2 * spot[..., None] + CYAN_F * 1.4 * ring[..., None]
    fres = (1 - mu) ** 2.2
    col = col + np.array([1.0, 0.62, 0.25]) * (fres * 0.45 * np.clip(ndl + 0.35, 0, 1))[..., None]
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
    if body["kind"] == "venus" and not full:  # halo de atmósfera
        hz = (dist > r * 0.995) & (dist < r * 1.06) & (b < 0)
        if hz.any():
            dd = (dist[hz] - r) / (0.018 * r)
            P = O + (-b[hz])[:, None] * d[hz]
            nn = P - C; nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
            Lh = light_dir(body, P)
            lit = np.clip((nn * Lh).sum(-1) + 0.35, 0, 1)
            gl = np.exp(-np.maximum(dd, 0)) * lit * 0.35
            region[hz] += (gl * (1 - alpha[hz]))[:, None] * np.array([1.0, 0.62, 0.25])
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

DIA0 = SEG["dia"]["t0"]; DIA_P2 = P("dia", 1)[0]; DIA1 = SEG["dia"]["t1"]
ANIO0 = SEG["anio"]["t0"]; CAR0 = SEG["carrera"]["t0"]; CAR_P2 = P("carrera", 1)[0]
REV0 = SEG["reversa"]["t0"]; REV_P2 = P("reversa", 1)[0]; REV_P3 = P("reversa", 2)[0]
LEN0 = SEG["lento"]["t0"]; LEN_P2 = P("lento", 1)[0]
CIE0 = SEG["cierre"]["t0"]; CIE_P2 = P("cierre", 1)[0]

FL = [DIA0 - 0.25, ANIO0 - 0.2, REV0 - 0.2, REV_P3 - 0.2, LEN0 - 0.2, END - 0.32]
T_YEAR = CAR0 + 1.0           # momento en que se completa el año (dice "Su año se termina...")
ORBIT_R = 3.6
D_HOOK0, D_HOOK1 = 6.6, 5.5


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


def sim_days(t):
    """Días terrestres transcurridos en la escena de la órbita."""
    return 224.7 * ease((t - (ANIO0 + 0.1)) / (T_YEAR - ANIO0 - 0.1))


def dia_progress(t):
    return ease((t - DIA_P2) / (DIA1 - DIA_P2 - 0.1))


def venus_cam(D):
    return np.array([0.0, 0.016 * D, D])


def sun_dir(t):
    s = ease_out((t - FL[3]) / (FL[4] - FL[3] + 0.3))
    elev = math.radians(lerp(-10.9, -5.2, s))
    v = np.array([-0.125, 0.0, -1.0]); v /= np.linalg.norm(v)
    d = np.array([v[0] * math.cos(elev), math.sin(elev), v[2] * math.cos(elev)])
    return d / np.linalg.norm(d)


def scene(t):
    """Devuelve (nombre, O, cuerpos, extra)."""
    if t < FL[0]:
        D = lerp_log(D_HOOK0, D_HOOK1, ease_out(t / FL[0]))
        return "venus", venus_cam(D), [dict(kind="venus", c=(0, 0, 0), r=1.0, spin=0.9 + 0.05 * t)], {}
    if t < FL[1]:
        D = lerp(6.1, 5.7, (t - FL[0]) / (FL[1] - FL[0]))
        spin = -0.9 + 2 * math.pi * dia_progress(t)   # el marcador arranca a la derecha y da una vuelta completa
        mk = min(1.0, max(0.0, (t - DIA0) / 0.4))
        return "venus", venus_cam(D), [dict(kind="venus", c=(0, 0, 0), r=1.0, spin=spin, marker=mk)], {}
    if t < FL[2]:
        d = sim_days(t)
        th = 2 * math.pi * d / 224.7
        D = lerp(28.5, 26.5, (t - FL[1]) / (FL[2] - FL[1]))
        O = np.array([0.0, 0.85, D])
        vpos = (ORBIT_R * math.cos(th), ORBIT_R * math.sin(th), 0.0)
        bodies = [dict(kind="star", c=(0, 0, 0), r=1.0),
                  dict(kind="venus", c=vpos, r=0.42, spin=2 * math.pi * d / 243.0, lightpos=(0, 0, 0), amb=0.03)]
        return "orbit", O, bodies, dict(d=d, th=th)
    if t < FL[3]:
        D = lerp(6.9, 6.5, (t - FL[2]) / (FL[3] - FL[2]))
        return "venus", venus_cam(D), [dict(kind="venus", c=(0, 0, 0), r=1.0, spin=1.3 + 0.55 * (t - FL[2]))], {}
    if t < FL[4]:
        O = np.array([0.0, 1.012, 0.0])
        sd = sun_dir(t)
        bodies = [dict(kind="star", c=tuple(O + sd * 60.0), r=60.0 * 0.028),
                  dict(kind="venus", c=(0, 0, 0), r=1.0, spin=2.2, full=True, L=sd, amb=0.10)]
        return "horizon", O, bodies, dict(sd=sd)
    if t < CIE0:
        D = lerp(3.55, 3.35, (t - FL[4]) / (CIE0 - FL[4]))
        return "venus", venus_cam(D), [dict(kind="venus", c=(0, 0, 0), r=1.0, spin=-0.55 + 0.10 * (t - FL[4]), equator=0.9 * min(1, (t - FL[4]) / 0.5),
                                             marker=min(1, (t - FL[4]) / 0.5))], {}
    s = ease((t - CIE0) / (END - 0.4 - CIE0))
    D = lerp_log(3.35, D_HOOK0, s)
    spin_end = -0.55 + 0.10 * (CIE0 - FL[4])
    return "venus", venus_cam(D), [dict(kind="venus", c=(0, 0, 0), r=1.0, spin=lerp(spin_end, 0.9, s), equator=0.9 * (1 - s), marker=1 - s)], {}


# ---------------- textos ----------------
HL_WORDS = {"día", "año", "años", "revés", "oeste", "venus", "lento", "km/h", "error"}


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


def draw_bars(layer, t, d_days):
    A = int(255 * fade(t, FL[1] + 0.05, FL[2] + 1, 0.25))
    if A <= 0:
        return
    d = ImageDraw.Draw(layer)
    x0, x1 = 110, W - 110
    rows = [("AÑO", "vuelta al Sol", 224.7, 225, YELLOW, 330), ("DÍA", "vuelta sobre sí mismo", 243.0, 243, CYAN, 480)]
    done_year = d_days >= 224.69
    for name, desc, total, shown, col, y in rows:
        f1 = font("Inter-Black.otf", 54); f2 = font("Inter-ExtraBold.otf", 38)
        d.text((x0, y), name, font=f1, fill=col + (A,), anchor="lm", stroke_width=6, stroke_fill=INK + (A,))
        d.text((x0 + d.textlength(name, font=f1) + 18, y + 4), desc, font=f2, fill=WHITE + (A,), anchor="lm", stroke_width=5, stroke_fill=INK + (A,))
        val = f"{min(int(d_days), shown)} / {shown} días"
        d.text((x1, y + 2), val, font=font("Inter-Black.otf", 44), fill=WHITE + (A,), anchor="rm", stroke_width=6, stroke_fill=INK + (A,))
        by = y + 52
        d.rounded_rectangle([x0, by, x1, by + 34], radius=17, fill=(255, 255, 255, int(A * 0.18)), outline=(255, 255, 255, int(A * 0.5)), width=2)
        frac = min(1.0, d_days / total)
        if frac > 0.01:
            d.rounded_rectangle([x0 + 4, by + 4, x0 + 4 + (x1 - x0 - 8) * frac, by + 30], radius=13, fill=col + (A,))
    if done_year:
        k = min(1.0, (t - T_YEAR) / 0.18)
        s = int(52 * (1.35 - 0.35 * k))
        d.text((W / 2, 640), "¡AÑO COMPLETO!", font=font("Inter-Black.otf", s), fill=YELLOW + (A,), anchor="mm", stroke_width=7, stroke_fill=INK + (A,))
        if t > CAR_P2 - 0.1:
            a2 = int(A * min(1.0, (t - CAR_P2 + 0.1) / 0.25))
            d.text((W / 2, 708), "y a su día le faltan 18", font=font("Inter-ExtraBold.otf", 46), fill=CYAN + (a2,), anchor="mm", stroke_width=6, stroke_fill=INK + (a2,))


def draw_orbit(layer, t, O, ex):
    S2 = 2
    big = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy, _ = sphere_px(O, (0, 0, 0), 1.0)
    rx = project(O, (ORBIT_R, 0, 0))[0] - cx
    A = int(255 * fade(t, FL[1], FL[2] + 1, 0.3))
    # órbita punteada
    n = 120
    for i in range(n):
        if i % 2:
            continue
        a0 = 360 * i / n; a1 = 360 * (i + 1) / n
        d.arc([(cx - rx) * S2, (cy - rx) * S2, (cx + rx) * S2, (cy + rx) * S2], a0, a1, fill=(255, 255, 255, int(A * 0.35)), width=5)
    # recorrido del año en amarillo (sentido antihorario, desde arriba)
    frac = min(1.0, ex["d"] / 224.7)
    if frac > 0.002:
        d.arc([(cx - rx) * S2, (cy - rx) * S2, (cx + rx) * S2, (cy + rx) * S2], -360 * frac, 0, fill=YELLOW + (A,), width=12)
    big = big.resize((W, H), Image.LANCZOS)
    layer.alpha_composite(big)
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 40)
    d.text((cx, cy + 150), "SOL", font=f, fill=(255, 200, 120, A), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))
    vx, vy, vr = sphere_px(O, (ORBIT_R * math.cos(ex["th"]), ORBIT_R * math.sin(ex["th"]), 0), 0.42)
    d.text((vx, vy - vr - 34), "VENUS", font=f, fill=WHITE + (A,), anchor="mm", stroke_width=5, stroke_fill=INK + (A,))


def draw_spin_arrow(layer, t, O):
    a = fade(t, REV_P2 - 0.15, FL[3] + 0.05, 0.2)
    if a <= 0:
        return
    cx, cy, R = sphere_px(O, (0, 0, 0), 1.0)
    grow = ease_out((t - REV_P2 + 0.15) / 0.6)
    S2 = 2
    big = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    A = int(255 * a)
    phi0 = math.radians(20); phi1 = math.radians(20 + 140 * grow)
    pts = []
    for i in range(60):
        ph = phi0 + (phi1 - phi0) * i / 59
        pts.append(((cx + 1.10 * R * math.cos(ph)) * S2, (cy + 0.26 * R * math.sin(ph)) * S2))
    d.line(pts, fill=YELLOW + (A,), width=26, joint="curve")
    # punta de flecha hacia la izquierda (rotación retrógrada vista desde aquí)
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    ang = math.atan2(yb - ya, xb - xa)
    L = 70 * S2
    tip = (xb + math.cos(ang) * 30, yb + math.sin(ang) * 30)
    left = (tip[0] - L * math.cos(ang - 0.5), tip[1] - L * math.sin(ang - 0.5))
    right = (tip[0] - L * math.cos(ang + 0.5), tip[1] - L * math.sin(ang + 0.5))
    d.polygon([tip, left, right], fill=YELLOW + (A,))
    big = big.resize((W, H), Image.LANCZOS)
    layer.alpha_composite(big)


def horizon_y(O, x_px):
    """Altura en pantalla del horizonte de Venus (esfera de radio 1 en el origen) en la columna x."""
    h = float(np.linalg.norm(O))
    dip = math.acos(1.0 / h)
    dx = (x_px / W * 2 - 1) * TX
    e = -math.tan(dip) * math.sqrt(1 + dx * dx)
    return (1 - e / TY) / 2 * H


def draw_horizon_labels(layer, t, O):
    A = int(255 * fade(t, FL[3] + 0.15, FL[4] + 0.05, 0.25))
    if A <= 0:
        return
    d = ImageDraw.Draw(layer)
    f = font("Inter-Black.otf", 58)
    for x, txt, col in ((190, "OESTE", YELLOW), (W - 190, "ESTE", WHITE)):
        y = horizon_y(O, x)
        d.line([x, y + 12, x, y + 60], fill=col + (A,), width=5)
        d.text((x, y + 100), txt, font=f, fill=col + (A,), anchor="mm", stroke_width=7, stroke_fill=INK + (A,))


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
    if name == "orbit":
        draw_orbit(layer, t, O, ex)
        draw_bars(layer, t, ex["d"])
    if name == "horizon":
        draw_horizon_labels(layer, t, O)
    if name == "venus" and FL[2] <= t < FL[3]:
        draw_spin_arrow(layer, t, O)
    draw_label(layer, t, -1, FL[0], "1 DÍA > 1 AÑO", ["en Venus"], YELLOW, 124)
    n_days = int(round(243 * dia_progress(t)))
    draw_label(layer, t, DIA0 + 0.15, FL[1], "UN DÍA EN VENUS", [f"{n_days} de 243 días terrestres"], WHITE, 100)
    draw_label(layer, t, REV_P2 - 0.1, FL[3], "GIRA AL REVÉS", ["al contrario que la Tierra"], YELLOW, 112)
    draw_label(layer, t, FL[3] + 0.1, FL[4], "EL SOL SALE", ["por el OESTE"], WHITE, 112, y0=330)
    draw_label(layer, t, LEN0 + 0.1, LEN_P2 - 0.05, "6.5 km/h", ["velocidad de su ecuador"], YELLOW, 140)
    draw_label(layer, t, LEN_P2 - 0.05, CIE0 + 0.2, "6.5 km/h", ["más lento que", "alguien trotando"], YELLOW, 140)
    draw_label(layer, t, CIE_P2, FL[5], "1 DÍA > 1 AÑO", ["en Venus"], YELLOW, 124)
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


def sky_glow(img, O, t, sd):
    """Atmósfera anaranjada de Venus que se enciende con el amanecer."""
    e = DIRS[..., 1]
    h = float(np.linalg.norm(O)); e_h = -math.sin(math.acos(1.0 / h))
    rise = ease_out((t - FL[3]) / 1.2)
    cosang = np.clip(DIRS @ sd, -1, 1)
    ang = np.arccos(cosang)
    above = smooth(e_h - 0.004, e_h + 0.004, e)
    band = np.exp(-np.maximum(e - e_h, 0) / 0.05) * above
    glow = np.exp(-ang / 0.06) * 0.9 + np.exp(-ang / 0.25) * 0.22
    surf = 0.35 + 0.65 * above
    img += (band * 0.45 * rise)[..., None] * np.array([1.0, 0.42, 0.10])
    img += (glow * rise * surf)[..., None] * np.array([1.0, 0.60, 0.25])


def render(t):
    name, O, bodies, ex = scene(t)
    img = BG.copy()
    if name == "horizon":
        img *= 0.6
    bodies.sort(key=lambda b: -float(np.linalg.norm(np.array(b["c"], float) - O)))
    for b in bodies:
        draw_sphere(img, O, b, t)
    if name == "horizon":
        sky_glow(img, O, t, ex["sd"])
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
        print("frames", NFRAMES, "flashes", [round(x, 2) for x in FL], "año", round(T_YEAR, 2))
