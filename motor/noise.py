import numpy as np
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


