"""Genera las texturas procedurales (mapas equirectangulares) de la Tierra, Júpiter, el Sol y Betelgeuse."""
import numpy as np, os

TW, TH = 2048, 1024
OUT = os.path.join(os.path.dirname(__file__), "tex")
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(7)
PERM = rng.permutation(256)
P = np.concatenate([PERM, PERM]).astype(np.int64)
VALS = rng.random(256)


def _hash(ix, iy, iz):
    return VALS[P[P[P[ix & 255] + (iy & 255)] + (iz & 255)]]


def vnoise(x, y, z):
    xi, yi, zi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64), np.floor(z).astype(np.int64)
    xf, yf, zf = x - xi, y - yi, z - zi
    u, v, w = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf), zf * zf * (3 - 2 * zf)
    c000 = _hash(xi, yi, zi); c100 = _hash(xi + 1, yi, zi)
    c010 = _hash(xi, yi + 1, zi); c110 = _hash(xi + 1, yi + 1, zi)
    c001 = _hash(xi, yi, zi + 1); c101 = _hash(xi + 1, yi, zi + 1)
    c011 = _hash(xi, yi + 1, zi + 1); c111 = _hash(xi + 1, yi + 1, zi + 1)
    x00 = c000 + u * (c100 - c000); x10 = c010 + u * (c110 - c010)
    x01 = c001 + u * (c101 - c001); x11 = c011 + u * (c111 - c011)
    y0 = x00 + v * (x10 - x00); y1 = x01 + v * (x11 - x01)
    return y0 + w * (y1 - y0)


def fbm(x, y, z, octaves=5, lac=2.0, gain=0.5, seed=0.0):
    tot, amp, norm, f = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        off = seed * 17.31 + o * 31.7
        tot = tot + amp * vnoise(x * f + off, y * f - off * 0.7, z * f + off * 1.3)
        norm += amp; amp *= gain; f *= lac
    return tot / norm


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = t[..., None]
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


j = (np.arange(TH) + 0.5) / TH
i = (np.arange(TW) + 0.5) / TW
lat = (0.5 - j)[:, None] * np.pi * np.ones((1, TW))
lon = (i * 2 * np.pi - np.pi)[None, :] * np.ones((TH, 1))
X = np.cos(lat) * np.sin(lon); Y = np.sin(lat); Z = np.cos(lat) * np.cos(lon)
alat = np.abs(lat)

# ---------- Tierra ----------
wx = fbm(X * 1.6, Y * 1.6, Z * 1.6, 4, seed=3)
wy = fbm(X * 1.6, Y * 1.6, Z * 1.6, 4, seed=5)
n = fbm(X * 1.9 + wx * 1.1, Y * 1.9 + wy * 1.1, Z * 1.9 - wx * 0.8, 6, seed=1)
land = smooth(0.505, 0.525, n)
coast = smooth(0.43, 0.505, n) * (1 - land)
ocean = mix((0.015, 0.07, 0.23), (0.05, 0.28, 0.50), coast)
veg = fbm(X * 5, Y * 5, Z * 5, 4, seed=9)
desert = smooth(0.15, 0.35, 1 - np.abs(np.degrees(lat) - 24 * np.sign(lat)) / 20) * smooth(0.45, 0.6, veg)
landc = mix((0.10, 0.30, 0.08), (0.30, 0.38, 0.14), smooth(0.3, 0.7, veg))
landc = mix(landc, (0.62, 0.50, 0.30), desert)
mount = smooth(0.62, 0.72, n)
landc = mix(landc, (0.42, 0.36, 0.30), mount * 0.7)
earth = mix(ocean, landc, land)
ice = smooth(np.radians(66), np.radians(76), alat + (fbm(X * 6, Y * 6, Z * 6, 3, seed=11) - 0.5) * 0.12)
earth = mix(earth, (0.92, 0.95, 0.98), ice)
cl = fbm(X * 3.2 + wy, Y * 5.0, Z * 3.2 - wx, 6, seed=21)
clouds = smooth(0.50, 0.72, cl) * 0.92
np.save(os.path.join(OUT, "earth.npy"), earth.astype(np.float32))
np.save(os.path.join(OUT, "earth_clouds.npy"), clouds.astype(np.float32))
np.save(os.path.join(OUT, "earth_land.npy"), land.astype(np.float32))
print("tierra lista")

# ---------- Júpiter ----------
turb = fbm(X * 4, Y * 1.2, Z * 4, 5, seed=31) - 0.5
turb2 = fbm(X * 12, Y * 3, Z * 12, 4, seed=33) - 0.5
phase = np.sin(lat) * 9.5 + turb * 1.6 + turb2 * 0.35
band = 0.5 + 0.5 * np.sin(phase * np.pi)
cream = (0.93, 0.87, 0.75); tan = (0.78, 0.58, 0.38); brown = (0.52, 0.33, 0.20)
jup = mix(cream, tan, band)
belt = smooth(0.0, 0.6, 1 - np.abs(np.abs(np.degrees(lat)) - 15) / 9)
jup = mix(jup, brown, belt * smooth(0.4, 0.9, band) * 0.8)
# Gran Mancha Roja
dlon = np.angle(np.exp(1j * (lon - 0.9)))
dl = (dlon / 0.20) ** 2 + ((lat - np.radians(-22)) / 0.075) ** 2
spot = smooth(1.15, 0.6, dl + turb2 * 0.6)
jup = mix(jup, (0.78, 0.36, 0.22), spot * 0.9)
polar = 1 - 0.35 * np.abs(np.sin(lat)) ** 4
jup = jup * polar[..., None]
np.save(os.path.join(OUT, "jupiter.npy"), jup.astype(np.float32))
print("jupiter listo")

# ---------- Sol ----------
g = fbm(X * 30, Y * 30, Z * 30, 4, seed=41)
g2 = fbm(X * 6, Y * 6, Z * 6, 3, seed=43)
sun = 0.82 + 0.35 * (g - 0.5) * 2 * 0.5 + 0.18 * (g2 - 0.5)
np.save(os.path.join(OUT, "sun.npy"), sun.astype(np.float32))
print("sol listo")

# ---------- Betelgeuse ----------
b1 = fbm(X * 2.6, Y * 2.6, Z * 2.6, 4, seed=51)
b2 = fbm(X * 11, Y * 11, Z * 11, 4, seed=53)
bet = 0.65 + 0.55 * (b1 - 0.5) * 2 * 0.6 + 0.25 * (b2 - 0.5)
np.save(os.path.join(OUT, "betelgeuse.npy"), bet.astype(np.float32))
print("betelgeuse lista")

# ---------- Venus (nubes amarillentas con bandas y forma de "Y") ----------
w1 = fbm(X * 2.2, Y * 2.2, Z * 2.2, 4, seed=61) - 0.5
streak = fbm(X * 3.0, Y * 14.0, Z * 3.0, 5, seed=63) - 0.5
fine = fbm(X * 9.0, Y * 22.0, Z * 9.0, 3, seed=65) - 0.5
chev = np.abs(lat) * 2.4 - 0.55 * np.cos(lon - 0.6)          # "Y" acostada que apunta al oeste
phase = chev + w1 * 1.4 + streak * 0.9
band = 0.5 + 0.5 * np.sin(phase * np.pi * 1.6)
light_c = (0.99, 0.93, 0.76); mid_c = (0.93, 0.80, 0.55); dark_c = (0.76, 0.58, 0.34)
ven = mix(light_c, mid_c, band)
ven = mix(ven, dark_c, smooth(0.62, 0.95, band) * smooth(-0.1, 0.25, streak + 0.1) * 0.75)
ven = ven * (1 + 0.10 * fine[..., None])
ven = mix(ven, (0.99, 0.95, 0.85), smooth(0.85, 1.35, np.abs(lat)) * 0.8)   # polos más claros
np.save(os.path.join(OUT, "venus.npy"), np.clip(ven, 0, 1).astype(np.float32))
print("venus lista")
