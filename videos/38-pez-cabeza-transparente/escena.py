"""Flash Datos · video 38 · el pez con la cabeza transparente (Macropinna microstoma).

Escena nueva: pez modelado con campos de distancia (SDF) y trazado por pasos (ray marching) a media
resolución, cúpula transparente analítica con reflejo de Fresnel, ojos tubulares que giran, nieve
marina en 3D, descenso con medidor de profundidad, sifonóforo luminoso y visor de cámara 4K.
Los textos (subtítulos, etiquetas, marca de agua, tarjeta final) se dibujan a resolución completa.

Uso:
  python3 escena.py test 1 5 12 ...       -> PNG de prueba en frames_test/
  python3 escena.py chunk <ini> <fin> <out>
  python3 escena.py info
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SC = 0.45                                   # resolución del trazado 3D
LW, LH = int(W * SC), int(H * SC)
FOV = 38.0                                  # grados, vertical

TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
NFRAMES = int(round(END * FPS))
S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
ORDER = ["gancho", "donde", "raro", "manchas", "ojos", "giran", "robo", "video", "cierre"]
FL = [S0[k] - 0.2 for k in ORDER[1:]]
CARD = S1["cierre"] + 0.25


def clamp(x, a=0.0, b=1.0):
    return min(max(x, a), b)


def ease(s):
    s = clamp(s)
    return s * s * s * (s * (6 * s - 15) + 10)


def ease_out(s):
    s = clamp(s)
    return 1 - (1 - s) ** 3


def split(k, f):
    return S0[k] + (S1[k] - S0[k]) * f


def lerp(a, b, s):
    return a + (b - a) * s


def lerpv(a, b, s):
    return [lerp(x, y, s) for x, y in zip(a, b)]


# ---------------- animación del pez ----------------
def eye_angle(t):
    """0 = ojos hacia arriba, 90 = hacia el frente (grados)."""
    a = 0.0
    g0 = split("giran", 0.46)
    a = 82 * ease((t - g0) / 0.9)
    if t > S0["robo"] - 0.3:
        a = 82 * (1 - ease((t - (S0["robo"] - 0.3)) / 0.9))
    if t > S0["video"]:
        a = 35 * (0.5 - 0.5 * math.cos((t - S0["video"]) * 1.3))
    if t > S0["cierre"]:
        a = 70 * ease((t - S0["cierre"]) / 1.2)
    return math.radians(a)


def fish_pose(t):
    """(posición, ángulo de giro sobre Y)."""
    yaw = 0.10 * math.sin(t * 0.7)
    pos = np.array([0.0, 0.03 * math.sin(t * 1.1), 0.0])
    if t > S0["cierre"]:
        s = t - S0["cierre"]
        pos = pos + np.array([0.32 * s * s * 0.5, 0.05 * s, 0.0])
    return pos, yaw


def roty(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rotx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rotz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


DOME_C = np.array([0.58, 0.24, 0.0]); DOME_R = np.array([0.44, 0.34, 0.20])
EYE_B = [np.array([0.58, 0.12, 0.085]), np.array([0.58, 0.12, -0.085])]
EYE_L, EYE_RAD, LENS_RAD = 0.26, 0.044, 0.056
NARES = [np.array([0.925, 0.075, 0.075]), np.array([0.925, 0.075, -0.075])]


def eye_tips(theta):
    d = np.array([math.sin(theta), math.cos(theta), 0.0])
    return [b + d * (EYE_L + 0.02) for b in EYE_B], d


# ---------------- SDF ----------------
def nrm(v):
    return np.sqrt((v * v).sum(-1))


def sd_ell(p, r):
    k0 = nrm(p / r); k1 = nrm(p / (r * r))
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)


def sd_cap(p, a, b, rad):
    pa = p - a; ba = b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return nrm(pa - h[:, None] * ba) - rad


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


class Fish:
    def __init__(self, t):
        self.t = t
        self.th = eye_angle(t)
        self.tips, self.edir = eye_tips(self.th)
        self.wag = 0.32 * math.sin(t * 5.2)
        self.flap = 0.35 * math.sin(t * 3.3)
        self.Rtail = roty(self.wag)
        self.Rpf = [rotx(0.35 + self.flap), rotx(-0.35 - self.flap)]

    def parts(self, p):
        x = p[:, 0]
        f = 1 - 0.58 * np.clip(-x - 0.1, 0, 1) ** 1.4
        q = p.copy(); q[:, 1] = q[:, 1] / f; q[:, 2] = q[:, 2] / f
        body = sd_ell(q, np.array([1.0, 0.33, 0.24])) * f
        # cavidad bajo la cúpula
        cav = np.maximum(sd_ell(p - DOME_C, DOME_R * 0.985), 0.12 - p[:, 1])
        body = np.maximum(body, -cav)
        # aletas
        pt = (p - np.array([-0.98, 0.0, 0.0])) @ self.Rtail
        tail = sd_ell(pt - np.array([-0.22, 0.0, 0.0]), np.array([0.26, 0.30, 0.022]))
        dors = sd_ell(p - np.array([-0.40, 0.30, 0.0]), np.array([0.24, 0.13, 0.018]))
        anal = sd_ell(p - np.array([-0.45, -0.27, 0.0]), np.array([0.26, 0.11, 0.018]))
        pf = []
        for side, R in zip((1, -1), self.Rpf):
            pp = (p - np.array([0.20, -0.08, side * 0.20])) @ R
            pf.append(sd_ell(pp - np.array([-0.05, 0.0, side * 0.20]), np.array([0.30, 0.022, 0.22])))
        fins = np.minimum(np.minimum(tail, dors), np.minimum(anal, np.minimum(pf[0], pf[1])))
        body = smin(body, fins, 0.03)
        tubes = np.minimum(sd_cap(p, EYE_B[0], self.tips[0], EYE_RAD), sd_cap(p, EYE_B[1], self.tips[1], EYE_RAD))
        lens = np.minimum(nrm(p - self.tips[0]) - LENS_RAD, nrm(p - self.tips[1]) - LENS_RAD)
        nares = np.minimum(nrm(p - NARES[0]) - 0.046, nrm(p - NARES[1]) - 0.046)
        return body, fins, tubes, lens, nares

    def sdf(self, p):
        b, _, tu, le, na = self.parts(p)
        return np.minimum(np.minimum(b, tu), np.minimum(le, na))

    def material(self, p):
        b, fi, tu, le, na = self.parts(p)
        m = np.zeros(len(p), np.int8)
        m[fi <= b + 0.004] = 1
        m[tu < np.minimum(b, np.minimum(le, na))] = 2
        m[le < np.minimum(np.minimum(b, tu), na)] = 3
        m[na < np.minimum(np.minimum(b, tu), le)] = 4
        return m

    def normal(self, p):
        e = 0.0025
        n = np.zeros_like(p)
        for i in range(3):
            d = np.zeros(3); d[i] = e
            n[:, i] = self.sdf(p + d) - self.sdf(p - d)
        return n / (nrm(n)[:, None] + 1e-9)


# ---------------- cámara ----------------
def camera(t):
    """(ojo, objetivo, fov) en coordenadas del mundo."""
    pos, _ = fish_pose(t)
    def orbit(az, el, dist, tgt):
        az, el = math.radians(az), math.radians(el)
        tgt = np.array(tgt, float)
        eye = tgt + dist * np.array([math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)])
        return eye, tgt
    # az = 0 mira el costado derecho del pez (+z); az = 90 mira de frente (+x)
    if t < S0["donde"] - 0.2:
        s = t / (S0["donde"] - 0.2)
        e, g = orbit(lerp(58, 38, ease(s)), lerp(14, 8, s), lerp(3.3, 2.6, ease_out(s)), pos + [0.35, 0.18, 0])
        return e, g, FOV
    if t < S0["raro"] - 0.2:
        s = (t - S0["donde"] + 0.2) / (S0["raro"] - S0["donde"])
        depth = 1 - ease(s / 0.92)
        e, g = orbit(25, lerp(6, 10, s), lerp(9.0, 4.2, ease(s)), pos + [0.1, 0.05, 0])
        e = e + np.array([0, 46 * depth, 0]); g = g + np.array([0, 46 * depth - 1.5 * depth, 0])
        return e, g, FOV
    if t < S0["manchas"] - 0.2:
        s = (t - S0["raro"] + 0.2) / (S0["manchas"] - S0["raro"])
        e, g = orbit(lerp(-20, 20, s), lerp(18, 10, s), lerp(4.2, 3.8, s), pos + [0.0, 0.0, 0])
        return e, g, FOV
    if t < S0["ojos"] - 0.2:
        s = (t - S0["manchas"] + 0.2) / (S0["ojos"] - S0["manchas"])
        k = ease_out(s / 0.35)
        e, g = orbit(lerp(55, 86, k), lerp(8, 4, k), lerp(3.4, 2.1, k), pos + lerpv([0.4, 0.1, 0], [0.9, 0.12, 0], k))
        return e, g, FOV
    if t < S0["giran"] - 0.2:
        s = (t - S0["ojos"] + 0.2) / (S0["giran"] - S0["ojos"])
        k = ease_out(s / 0.4)
        e, g = orbit(lerp(86, 50, k) + 8 * s, lerp(4, 30, k), lerp(2.1, 2.0, k), pos + lerpv([0.9, 0.12, 0], [0.62, 0.30, 0], k))
        return e, g, FOV
    if t < S0["robo"] - 0.2:
        s = (t - S0["giran"] + 0.2) / (S0["robo"] - S0["giran"])
        k = ease_out(s / 0.3)
        e, g = orbit(lerp(58, 4, k), lerp(30, 8, k), lerp(2.0, 2.2, k), pos + lerpv([0.62, 0.30, 0], [0.62, 0.32, 0], k))
        return e, g, FOV
    if t < S0["video"] - 0.2:
        s = (t - S0["robo"] + 0.2) / (S0["video"] - S0["robo"])
        k = ease_out(s / 0.35)
        e, g = orbit(lerp(20, 35, s), lerp(-4, -16, k), lerp(3.0, 5.6, k), pos + lerpv([0.3, 0.4, 0], [0.2, 1.3, 0], k))
        return e, g, FOV
    if t < S0["cierre"] - 0.2:
        s = (t - S0["video"] + 0.2) / (S0["cierre"] - S0["video"])
        e, g = orbit(lerp(70, 30, s), lerp(10, 14, s), lerp(2.6, 3.0, s), pos + [0.3, 0.15, 0])
        return e, g, FOV
    s = (t - S0["cierre"] + 0.2) / max(END - S0["cierre"], 0.1)
    p0, _ = fish_pose(S0["cierre"])
    e, g = orbit(lerp(40, 70, s), lerp(10, 16, s), lerp(3.2, 4.4, ease(s)), p0 + [0.35 + 0.6 * s, 0.18, 0])
    return e, g, FOV


def cam_basis(eye, tgt):
    f = tgt - eye; f = f / np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    return f, r, u


def project(pw, eye, tgt, fov):
    """Punto del mundo -> (x, y) en píxeles de salida y profundidad."""
    f, r, u = cam_basis(eye, tgt)
    v = np.asarray(pw) - eye
    z = v @ f
    ty = math.tan(math.radians(fov) / 2); tx = ty * W / H
    x = (v @ r) / np.maximum(z, 1e-6) / tx; y = (v @ u) / np.maximum(z, 1e-6) / ty
    return (x + 1) / 2 * W, (1 - y) / 2 * H, z


# ---------------- fondo ----------------
def depth_light(t):
    """1 = cerca de la superficie, 0 = 600 m."""
    if S0["donde"] - 0.2 <= t < S0["raro"] - 0.2:
        s = (t - S0["donde"] + 0.2) / (S0["raro"] - S0["donde"])
        return 1 - ease(s / 0.92)
    return 0.0


def depth_m(t):
    if t < S0["donde"] - 0.2:
        return 600
    s = (t - S0["donde"] + 0.2) / (S0["raro"] - S0["donde"])
    return int(round(600 * ease(s / 0.92)))


DEEP = np.array([0.002, 0.006, 0.016]); SURF = np.array([0.05, 0.22, 0.42])


def background(dirs, t, f):
    up = dirs[..., 1]
    L = depth_light(t)
    base = DEEP * (1 + 0.8 * np.clip(up, 0, 1)) + (SURF - DEEP) * (L ** 1.5) * (0.35 + 0.65 * np.clip(up + 0.3, 0, 1.3))[..., None] if False else None
    k = np.clip(up * 0.5 + 0.5, 0, 1)[..., None]
    col = DEEP * (0.6 + 1.2 * k) + (SURF - DEEP) * (L ** 1.5) * (0.25 + 0.9 * k)
    # resplandor de las luces del robot hacia el frente
    fw = np.clip((dirs * f).sum(-1), 0, 1)
    col = col + np.array([0.020, 0.045, 0.060]) * (fw ** 18)[..., None] * (1 - 0.5 * L)
    # rayos de sol cerca de la superficie
    if L > 0.02:
        ang = np.arctan2(dirs[..., 0], dirs[..., 2])
        rays = (0.5 + 0.5 * np.sin(ang * 23 + t * 0.6)) * (0.5 + 0.5 * np.sin(ang * 37 - t * 0.4))
        col = col + np.array([0.10, 0.22, 0.25]) * (rays * np.clip(up, 0, 1) ** 2 * L ** 2)[..., None]
    return col


# ---------------- render 3D ----------------
KEY_COL = np.array([1.0, 0.93, 0.82])


def render3d(t):
    eye, tgt, fov = camera(t)
    f, r, u = cam_basis(eye, tgt)
    ty = math.tan(math.radians(fov) / 2); tx = ty * LW / LH
    xs = ((np.arange(LW) + 0.5) / LW * 2 - 1) * tx
    ys = (1 - (np.arange(LH) + 0.5) / LH * 2) * ty
    X, Y = np.meshgrid(xs, ys)
    D = f[None, None] + X[..., None] * r[None, None] + Y[..., None] * u[None, None]
    D = D / nrm(D)[..., None]
    img = background(D, t, f)
    fish = Fish(t)
    pos, yaw = fish_pose(t)
    R = roty(yaw)
    o = (eye - pos) @ R                    # origen en coordenadas del pez
    dl = D.reshape(-1, 3) @ R
    # esfera envolvente
    bc = np.array([-0.05, 0.05, 0.0]); br = 1.55
    oc = o - bc
    b = dl @ oc; c = oc @ oc - br * br
    disc = b * b - c
    hitb = disc > 0
    t0 = np.where(hitb, -b - np.sqrt(np.maximum(disc, 0)), 0)
    t1 = np.where(hitb, -b + np.sqrt(np.maximum(disc, 0)), 0)
    hitb &= t1 > 0
    idx = np.nonzero(hitb)[0]
    tt = np.maximum(t0[idx], 0.02)
    tend = t1[idx]
    act = np.arange(len(idx))
    hit = np.zeros(len(idx), bool)
    for _ in range(70):
        if len(act) == 0:
            break
        p = o + dl[idx[act]] * tt[act][:, None]
        d = fish.sdf(p)
        h = d < 0.0012 * np.maximum(tt[act], 1)
        hit[act[h]] = True
        tt[act] += d * 0.9
        keep = (~h) & (tt[act] < tend[act])
        act = act[keep]
    flat = img.reshape(-1, 3)
    thit = np.full(len(dl), np.inf)
    if hit.any():
        hi = idx[hit]
        P = o + dl[hi] * tt[hit][:, None]
        thit[hi] = tt[hit]
        N = fish.normal(P)
        M = fish.material(P)
        V = -dl[hi]
        # luz principal: focos del robot, arriba de la cámara
        lp = (eye + u * 1.2 + r * 0.6 - pos) @ R
        Ld = lp - P; Ld = Ld / nrm(Ld)[:, None]
        ndl = np.clip((N * Ld).sum(-1), 0, 1)
        Hh = Ld + V; Hh = Hh / nrm(Hh)[:, None]
        spec = np.clip((N * Hh).sum(-1), 0, 1)
        top = np.clip(N[:, 1] * 0.5 + 0.5, 0, 1)
        fres = (1 - np.clip((N * V).sum(-1), 0, 1)) ** 3
        # cuerpo: café oscuro con brillo plateado y manchas
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        spots = 0.5 + 0.5 * np.sin(x * 47 + np.sin(z * 31) * 2) * np.sin(y * 39 + x * 11)
        belly = np.clip(-y * 3 + 0.2, 0, 1)
        alb = np.array([0.060, 0.045, 0.035])[None] * (0.85 + 0.25 * spots)[:, None] + np.array([0.20, 0.19, 0.17])[None] * belly[:, None] * 0.6
        col = alb * (0.05 + 1.6 * ndl)[:, None] * KEY_COL + np.array([0.6, 0.6, 0.55]) * (spec ** 30 * 0.5)[:, None]
        col += np.array([0.03, 0.09, 0.14]) * (fres * (0.4 + top))[:, None]
        # aletas: oscuras, translúcidas
        m1 = M == 1
        col[m1] = (np.array([0.05, 0.05, 0.06]) * (0.2 + 1.0 * ndl[m1])[:, None] + np.array([0.04, 0.10, 0.14]) * (0.3 + fres[m1])[:, None]) * 0.9
        # tubos de los ojos: verde oscuro translúcido
        m2 = M == 2
        col[m2] = np.array([0.03, 0.16, 0.06]) * (0.4 + 1.4 * ndl[m2])[:, None] + np.array([0.3, 0.9, 0.4]) * (spec[m2] ** 40 * 0.5)[:, None] + np.array([0.05, 0.35, 0.10]) * fres[m2][:, None]
        # lentes: verde brillante
        m3 = M == 3
        col[m3] = np.array([0.35, 1.25, 0.30]) * (0.55 + 0.45 * ndl[m3])[:, None] + np.array([1, 1, 1]) * (spec[m3] ** 60)[:, None]
        # orificios del olfato: negros y brillantes
        m4 = M == 4
        col[m4] = np.array([0.006, 0.006, 0.008]) + np.array([0.8, 0.85, 0.9]) * (spec[m4] ** 80 * 0.9)[:, None]
        # niebla del agua
        dist = tt[hit]
        fog = np.exp(-dist * 0.07)[:, None]
        flat[hi] = col * fog + flat[hi] * (1 - fog)
    # cúpula transparente
    q = (o - DOME_C) / DOME_R
    dq = dl / DOME_R
    a2 = (dq * dq).sum(-1); b2 = (dq @ q); c2 = q @ q - 1
    dd = b2 * b2 - a2 * c2
    hd = dd > 0
    sq = np.sqrt(np.maximum(dd, 0))
    tf = (-b2 - sq) / a2; tb = (-b2 + sq) / a2
    for tsurf, gain in ((tb, 0.45), (tf, 1.0)):
        m = hd & (tsurf > 0) & (tsurf < thit)
        if not m.any():
            continue
        P = o + dl[m] * tsurf[m][:, None]
        N = (P - DOME_C) / (DOME_R ** 2); N = N / nrm(N)[:, None]
        V = -dl[m]
        mu = np.abs((N * V).sum(-1))
        fr = 0.03 + 0.97 * (1 - mu) ** 4
        lp = (eye + u * 1.2 + r * 0.6 - pos) @ R
        Ld = lp - P; Ld = Ld / nrm(Ld)[:, None]
        Hh = Ld + V; Hh = Hh / nrm(Hh)[:, None]
        sp = np.abs((N * Hh).sum(-1)) ** 900
        tint = np.array([0.93, 0.98, 1.0])
        flat[m] = flat[m] * (1 - 0.35 * fr * gain)[:, None] * tint + (np.array([0.10, 0.30, 0.40]) * fr[:, None] + sp[:, None] * 0.9) * gain
    return flat.reshape(LH, LW, 3), (eye, tgt, fov), fish


def bloom_small(img):
    from scipy.ndimage import gaussian_filter
    br = np.clip(img - 0.35, 0, None)
    return img + gaussian_filter(br, (4, 4, 0)) * 0.9 + gaussian_filter(br, (14, 14, 0)) * 0.6


def tonemap(x):
    x = np.maximum(x, 0) * 1.25
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)


# ---------------- nieve marina ----------------
_rng = np.random.default_rng(38)
SNOW = np.stack([_rng.uniform(-7, 7, 3200), _rng.uniform(-6, 50, 3200), _rng.uniform(-7, 7, 3200)], -1)
SNOW_S = _rng.uniform(0.6, 1.4, 3200)


def draw_snow(im, t, cam):
    eye, tgt, fov = cam
    p = SNOW + np.stack([0.05 * np.sin(t * 0.3 + SNOW[:, 1]), -0.04 * t + 0 * SNOW[:, 1], 0.05 * np.cos(t * 0.25 + SNOW[:, 0])], -1)
    x, y, z = project(p, eye, tgt, fov)
    ok = (z > 0.25) & (z < 16) & (x > -20) & (x < W + 20) & (y > -20) & (y < H + 20)
    d = ImageDraw.Draw(im, "RGBA")
    L = depth_light(t)
    for xi, yi, zi, si in zip(x[ok], y[ok], z[ok], SNOW_S[ok]):
        rad = max(1.0, 7.0 * si / zi)
        a = int(clamp(150 / (0.6 + zi * 0.35) * (1 - zi / 16), 0, 200) * (0.6 + 0.4 * (1 - L)))
        d.ellipse([xi - rad, yi - rad, xi + rad, yi + rad], fill=(200, 225, 235, a))


# ---------------- texto ----------------
FD = os.path.join(BASE, "fonts", "")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + name, size)
    return _fc[key]


YELLOW = (255, 216, 77); CYAN = (79, 216, 255); WHITE = (255, 255, 255); GREEN = (120, 255, 140); RED = (255, 70, 70)


def txt(d, xy, s, size, col, A, fname="Inter-Black.otf", stroke=8, anchor="mm"):
    d.text(xy, s, font=font(fname, size), fill=col + (A,), anchor=anchor, stroke_width=stroke, stroke_fill=(6, 10, 20, A))


def fade(t, a, b, f=0.25):
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / f, (b - t) / f)


def draw_label(d, t, a, b, title, subs, col=WHITE, size=112):
    al = fade(t, a, b)
    if al <= 0:
        return
    A = int(255 * al)
    y = 380 + (1 - ease_out((t - a) / 0.3)) * 26
    txt(d, (W / 2, y), title, size, col, A)
    y += size * 0.5 + 46
    for s in subs:
        txt(d, (W / 2, y), s, 52, CYAN, A, "Inter-ExtraBold.otf", 7)
        y += 68


HL = {"pez", "cabeza", "transparente", "ojos", "no", "barril", "robot", "octubre", "metros", "años", "veces", "manchas",
      "olfato", "narices", "tubos", "verdes", "giran", "arriba", "frente", "roba", "sifonóforos", "medusas", "minutos", "mira"}


def groups_for_part(t0, t1, text):
    words = text.split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w[-1] in ".,:…?" or len(" ".join(cur)) > 16:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    weights = [sum(len(w) for w in g) + 2 for g in groups]
    tot = sum(weights); tc = t0; out = []
    for g, wt in zip(groups, weights):
        dur = (t1 - t0) * wt / tot
        out.append([tc, tc + dur, g]); tc += dur
    return out


CAPS = []
for s in TM["segments"]:
    for a, b, tx_ in s["parts"]:
        CAPS += groups_for_part(a, b, tx_)
for i in range(len(CAPS) - 1):
    if CAPS[i + 1][0] - CAPS[i][1] < 0.7:
        CAPS[i][1] = CAPS[i + 1][0]


def is_hl(w):
    core = w.strip(".,:…?¿!").lower()
    return any(ch.isdigit() for ch in core) or (w.strip(".,:…?¿!").isupper() and len(core) > 1) or core == "3d" or core == "4k"


def draw_caption(d, t):
    if t >= CARD:
        return
    for (t0, t1, g) in CAPS:
        if t0 <= t < t1:
            k = min(1.0, (t - t0) / 0.09)
            size = int(round(80 * (1.12 - 0.12 * k)))
            f = font("Inter-Black.otf", size)
            words = [w if not w.isupper() else w for w in g]
            disp = [w.upper() for w in words]
            space = d.textlength(" ", font=f)
            widths = [d.textlength(w, font=f) for w in disp]
            total = sum(widths) + space * (len(disp) - 1)
            if total > 990:
                f = font("Inter-Black.otf", int(size * 990 / total))
                space = d.textlength(" ", font=f)
                widths = [d.textlength(w, font=f) for w in disp]
                total = sum(widths) + space * (len(disp) - 1)
            x = W / 2 - total / 2; y = 1300
            for w, dw, wd in zip(words, disp, widths):
                col = YELLOW if is_hl(w) else WHITE
                d.text((x, y), dw, font=f, fill=col + (255,), anchor="lm", stroke_width=9, stroke_fill=(6, 10, 20, 255))
                x += wd + space
            return


def bolt(cx, cy, s):
    pts = [(0.58, 0.0), (0.12, 0.56), (0.44, 0.56), (0.30, 1.0), (0.88, 0.38), (0.55, 0.38), (0.74, 0.0)]
    return [(cx + (px - 0.5) * s, cy + (py - 0.5) * s) for px, py in pts]


def draw_watermark(d):
    f = font("Inter-Black.otf", 38)
    s = "FLASH DATOS"
    tw = d.textlength(s, font=f)
    x = W / 2 - (tw + 40) / 2
    d.polygon(bolt(x + 14, 212, 40), fill=YELLOW + (230,))
    d.text((x + 40, 212), s, font=f, fill=(255, 255, 255, 215), anchor="lm", stroke_width=4, stroke_fill=(8, 10, 20, 160))


def marker(d, x, y, t, col, A, r0=40, label=None, side=1, lsize=50, ly=0):
    rr = r0 + 5 * math.sin(t * 7)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (A,), width=6)
    if label:
        lx = x + side * (rr + 60)
        d.line([x + side * rr * 0.7, y - rr * 0.7 * (1 if ly < 0 else -1) * 0, lx, y + ly], fill=col + (A,), width=5)
        txt(d, (lx + side * 12, y + ly), label, lsize, col, A, "Inter-Black.otf", 7, "lm" if side > 0 else "rm")


def arrow(d, x0, y0, x1, y1, col, A, w=12):
    d.line([x0, y0, x1, y1], fill=col + (A,), width=w)
    ang = math.atan2(y1 - y0, x1 - x0)
    s = w * 3
    pts = [(x1 + math.cos(ang) * s * 0.6, y1 + math.sin(ang) * s * 0.6),
           (x1 + math.cos(ang + 2.4) * s, y1 + math.sin(ang + 2.4) * s),
           (x1 + math.cos(ang - 2.4) * s, y1 + math.sin(ang - 2.4) * s)]
    d.polygon(pts, fill=col + (A,))


def to_world(pl, t):
    pos, yaw = fish_pose(t)
    return roty(yaw) @ pl + pos


def scr(pl, t, cam):
    x, y, z = project(to_world(pl, t), *cam)
    return float(x), float(y), float(z)


# ---------------- sifonóforo ----------------
def siph_points(t):
    pts = []
    for i in range(16):
        s = i / 15
        x = -1.9 + 4.0 * s
        y = 1.55 + 0.18 * math.sin(s * 5 + t * 0.8)
        z = -0.6 + 0.3 * math.sin(s * 3)
        pts.append(np.array([x, y, z]))
    return pts


def draw_siph(im, t, cam):
    al = fade(t, S0["robo"] - 0.1, S0["video"] + 0.1, 0.4)
    if al <= 0:
        return
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    pts = siph_points(t)
    prev = None
    for i, p in enumerate(pts):
        x, y, z = project(p, *cam)
        if z <= 0.2:
            continue
        rr = 150 / z * (0.8 if i % 2 else 1.1)
        if prev:
            d.line([prev, (x, y)], fill=(170, 230, 255, int(150 * al)), width=max(2, int(18 / z)))
        prev = (x, y)
        d.ellipse([x - rr, y - rr * 0.7, x + rr, y + rr * 0.7], fill=(150, 210, 255, int(110 * al)), outline=(220, 245, 255, int(240 * al)), width=4)
        if i % 2 == 0:
            for k in range(3):
                ph = t * 1.5 + i + k
                pts_t = []
                for j in range(14):
                    tp = p + np.array([0.05 * math.sin(ph + j * 0.5) + (k - 1) * 0.05, -0.08 * j, 0.03 * math.cos(ph + j * 0.4)])
                    xx, yy, zz = project(tp, *cam)
                    pts_t.append((xx, yy))
                d.line(pts_t, fill=(255, 140, 190, int(130 * al)), width=max(1, int(8 / z)))
    # presa atrapada (crustáceo diminuto)
    pp = pts[9] + np.array([0.02, -0.75, 0.0])
    x, y, z = project(pp, *cam)
    if z > 0.2:
        rr = 70 / z
        d.ellipse([x - rr, y - rr * 0.6, x + rr, y + rr * 0.6], fill=(255, 140, 60, int(230 * al)))
    g2 = glow.filter(ImageFilter.GaussianBlur(10))
    im.alpha_composite(g2); im.alpha_composite(glow)
    return pts


# ---------------- capas 2D ----------------
def overlays(base, t, cam, fish):
    im = Image.fromarray(base).convert("RGBA")
    draw_snow(im, t, cam)
    draw_siph(im, t, cam)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # gancho
    draw_label(d, t, 0.35, S0["donde"] - 0.25, "CABEZA TRANSPARENTE", ["pez real, filmado en 2026"], YELLOW, 76)
    # donde: medidor de profundidad
    a = fade(t, S0["donde"] - 0.1, S0["raro"] - 0.25)
    if a > 0:
        A = int(255 * a)
        dm = depth_m(t)
        txt(d, (W / 2, 390), f"{dm} m", 150, YELLOW, A)
        txt(d, (W / 2, 520), "Cañón de Monterey, California", 50, CYAN, A, "Inter-ExtraBold.otf", 7)
        txt(d, (W / 2, 585), "20 de octubre de 2026", 50, CYAN, A, "Inter-ExtraBold.otf", 7)
        bx = W - 90; y0, y1 = 300, 1150
        d.line([bx, y0, bx, y1], fill=(255, 255, 255, int(A * 0.6)), width=6)
        for k in range(7):
            yy = y0 + (y1 - y0) * k / 6
            d.line([bx - 18, yy, bx, yy], fill=(255, 255, 255, int(A * 0.6)), width=4)
            txt(d, (bx - 30, yy), f"{k * 100}", 30, WHITE, int(A * 0.8), "Inter-ExtraBold.otf", 4, "rm")
        yy = y0 + (y1 - y0) * dm / 600
        d.polygon([(bx + 4, yy), (bx + 34, yy - 18), (bx + 34, yy + 18)], fill=YELLOW + (A,))
    # raro: 11 avistamientos
    a = fade(t, S0["raro"] + 0.1, S0["manchas"] - 0.25)
    if a > 0:
        A = int(255 * a)
        txt(d, (W / 2, 380), "SOLO 11 VECES", 104, YELLOW, A)
        txt(d, (W / 2, 482), "en unas 7,000 inmersiones", 52, CYAN, A, "Inter-ExtraBold.otf", 7)
        txt(d, (W / 2, 548), "en casi 40 años", 52, CYAN, A, "Inter-ExtraBold.otf", 7)
        for i in range(11):
            ti = S0["raro"] + 0.6 + i * 0.22
            on = t >= ti
            x = W / 2 + (i - 5) * 84; y = 650
            c = YELLOW if on else (90, 100, 120)
            aa = A if on else int(A * 0.5)
            d.ellipse([x - 26, y - 16, x + 26, y + 16], fill=c + (aa,))
            d.polygon([(x - 22, y), (x - 44, y - 16), (x - 44, y + 16)], fill=c + (aa,))
    # manchas: no son ojos
    a = fade(t, S0["manchas"] + 0.5, S0["ojos"] - 0.2)
    if a > 0:
        A = int(255 * a)
        pts = [scr(p, t, cam) for p in NARES]
        for i, (x, y, z) in enumerate(pts):
            if z > 0:
                marker(d, x, y, t, YELLOW, A, r0=max(26, 70 / z))
        mx = sum(p[0] for p in pts) / 2; my = min(p[1] for p in pts)
        txt(d, (mx, my - 150), "NO SON OJOS", 70, YELLOW, A)
        txt(d, (W / 2, 380), "OLFATO", 112, WHITE, A)
        txt(d, (W / 2, 480), "como fosas nasales", 52, CYAN, A, "Inter-ExtraBold.otf", 7)
    # ojos de verdad
    a = fade(t, S0["ojos"] + 0.4, S0["giran"] - 0.2)
    if a > 0:
        A = int(255 * a)
        for tip in fish.tips:
            x, y, z = scr(tip, t, cam)
            if z > 0:
                marker(d, x, y, t, GREEN, A, r0=max(30, 90 / z))
        txt(d, (W / 2, 380), "SUS OJOS", 112, GREEN, A)
        txt(d, (W / 2, 480), "dos tubos verdes", 52, CYAN, A, "Inter-ExtraBold.otf", 7)
        txt(d, (W / 2, 546), "dentro de la cabeza", 52, CYAN, A, "Inter-ExtraBold.otf", 7)
    # giran
    a = fade(t, S0["giran"] + 0.2, S0["robo"] - 0.2)
    if a > 0:
        A = int(255 * a)
        g0 = split("giran", 0.46)
        up = t < g0 + 0.45
        txt(d, (W / 2, 380), "MIRAN ARRIBA" if up else "MIRAN AL FRENTE", 100, YELLOW, A)
        txt(d, (W / 2, 480), "para buscar comida" if up else "para atraparla", 52, CYAN, A, "Inter-ExtraBold.otf", 7)
        tip = fish.tips[0]
        x, y, z = scr(tip + fish.edir * 0.09, t, cam)
        x2, y2, _ = scr(tip + fish.edir * 0.26, t, cam)
        if z > 0:
            arrow(d, x, y, x2, y2, YELLOW, A)
    # robo
    a = fade(t, S0["robo"] + 0.4, S0["video"] - 0.2)
    if a > 0:
        A = int(255 * a)
        txt(d, (W / 2, 380), "SIFONÓFOROS", 104, (255, 160, 200), A)
        txt(d, (W / 2, 480), "parientes de las medusas", 52, CYAN, A, "Inter-ExtraBold.otf", 7)
        txt(d, (W / 2, 546), "(se cree que les roba comida)", 46, WHITE, A, "Inter-ExtraBold.otf", 6)
    # video: visor de cámara
    a = fade(t, S0["video"] - 0.1, S0["cierre"] - 0.2)
    if a > 0:
        A = int(255 * a)
        m, L = 70, 110
        for (cx, cy, sx, sy) in ((m, 300, 1, 1), (W - m, 300, -1, 1), (m, 1520, 1, -1), (W - m, 1520, -1, -1)):
            d.line([cx, cy, cx + sx * L, cy], fill=(255, 255, 255, A), width=7)
            d.line([cx, cy, cx, cy + sy * L], fill=(255, 255, 255, A), width=7)
        if int(t * 2) % 2 == 0:
            d.ellipse([m + 20, 340, m + 52, 372], fill=RED + (A,))
        txt(d, (m + 66, 356), "REC", 40, WHITE, A, "Inter-Black.otf", 5, "lm")
        el = 18 * 60 + 40 + (t - S0["video"]) * 12
        txt(d, (W - m - 20, 356), f"00:{int(el // 60):02d}:{int(el % 60):02d}", 40, WHITE, A, "Inter-Black.otf", 5, "rm")
        three = t > split("video", 0.55)
        txt(d, (W / 2, 470), "4K · 20 MIN", 110, YELLOW, A)
        if three:
            k = ease_out((t - split("video", 0.55)) / 0.3)
            txt(d, (W / 2, 600), "+ 3D", int(80 + 30 * k), CYAN, A)
    draw_caption(d, t)
    draw_watermark(d)
    im.alpha_composite(layer)
    # tarjeta final
    al = fade(t, CARD, END + 1, 0.3)
    if al > 0:
        A = int(255 * al)
        im.alpha_composite(Image.new("RGBA", (W, H), (4, 6, 12, int(185 * al))))
        d2 = ImageDraw.Draw(im)
        k = ease_out((t - CARD) / 0.4)
        d2.polygon(bolt(W / 2, 780, 230 + 40 * k), fill=YELLOW + (A,))
        txt(d2, (W / 2, 1010), "FLASH DATOS", 104, WHITE, A)
        txt(d2, (W / 2, 1120), "Síguenos para más datos", 52, CYAN, A, "Inter-ExtraBold.otf", 6)
        txt(d2, (W / 2, 1185), "de ciencia y del espacio", 52, CYAN, A, "Inter-ExtraBold.otf", 6)
    fa = flash_alpha(t)
    if fa > 0:
        im.alpha_composite(Image.new("RGBA", (W, H), (225, 248, 255, int(235 * fa))))
        if fa > 0.35:
            b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(b).polygon(bolt(W / 2, H / 2, 420), fill=YELLOW + (int(255 * min(1, (fa - 0.35) / 0.4)),))
            im.alpha_composite(b)
    return np.asarray(im.convert("RGB"))


def flash_alpha(t):
    a = 0.0
    for tf in FL:
        dt = t - tf
        if -0.07 <= dt < 0:
            a = max(a, (dt + 0.07) / 0.07)
        elif 0 <= dt < 0.45:
            a = max(a, math.exp(-dt / 0.085))
    return a


_rng2 = np.random.default_rng(5)
GRAIN = _rng2.normal(0, 1, (LH, LW, 1)).astype(np.float32)


def render(t):
    img, cam, fish = render3d(t)
    img = bloom_small(img)
    g = np.roll(GRAIN, int(t * 997) % LW, axis=1)
    img = img + g * 0.0025
    u8 = (tonemap(img) * 255 + 0.5).astype(np.uint8)
    big = np.asarray(Image.fromarray(u8).resize((W, H), Image.BICUBIC))
    return overlays(big, t, cam, fish)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        import time
        os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
        for ts in sys.argv[2:]:
            t = float(ts); t0 = time.time()
            Image.fromarray(render(t)).save(os.path.join(BASE, "frames_test", f"t{t:05.2f}.png"))
            print("ok", t, round(time.time() - t0, 2), "s", flush=True)
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
