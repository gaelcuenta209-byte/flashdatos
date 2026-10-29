"""Textura de la Tierra con continentes reales (contornos simplificados) y nubes procedurales."""
import numpy as np, os
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from noise import fbm, smooth, mix
from continents import POLYGONS, WATER, GREENLAND

TW, TH = 2048, 1024
S = 2  # supermuestreo del contorno
OUT = os.path.join(os.path.dirname(__file__), "tex")


def to_px(pts):
    return [((lon + 180) / 360 * TW * S, (90 - lat) / 180 * TH * S) for lon, lat in pts]


img = Image.new("L", (TW * S, TH * S), 0)
d = ImageDraw.Draw(img)
for poly in POLYGONS:
    d.polygon(to_px(poly), fill=255)
for poly in WATER:
    d.polygon(to_px(poly), fill=0)
mask = np.asarray(img.resize((TW, TH), Image.LANCZOS), dtype=np.float32) / 255.0

j = (np.arange(TH) + 0.5) / TH
i = (np.arange(TW) + 0.5) / TW
lat = (0.5 - j)[:, None] * np.pi * np.ones((1, TW))
lon = (i * 2 * np.pi - np.pi)[None, :] * np.ones((TH, 1))
X = np.cos(lat) * np.sin(lon); Y = np.sin(lat); Z = np.cos(lat) * np.cos(lon)
alat = np.abs(lat); dlat = np.degrees(lat)

# costa irregular: desenfoque + ruido
soft = gaussian_filter(mask, 2.0)
jit = fbm(X * 22, Y * 22, Z * 22, 4, seed=61) - 0.5
land = smooth(0.42, 0.58, soft + jit * 0.35)
shelf = smooth(0.05, 0.45, gaussian_filter(mask, 6.0)) * (1 - land)

ocean = mix((0.012, 0.06, 0.21), (0.03, 0.17, 0.36), shelf * 0.8)
veg = fbm(X * 5, Y * 5, Z * 5, 4, seed=9)
# desiertos por región (lon, lat, radio lon, radio lat, peso)
DESERTS = [(5,23,22,8,1.0),(28,24,9,7,1.0),(46,23,11,7,1.0),(62,29,9,5,0.8),(71,27,4,3,0.6),(100,42,14,5,0.8),(83,40,6,3,0.7),(132,-25,14,7,1.0),(18,-24,7,6,0.8),(-70,-23,2.5,6,0.8),(-111,31,7,5,0.8),(-68,-45,3.5,5,0.5),(57,41,8,4,0.6)]
desert = np.zeros_like(lat)
LD = np.degrees(lon)
for lo, la, rlo, rla, w in DESERTS:
    dd = ((LD - lo) / rlo) ** 2 + ((dlat - la) / rla) ** 2
    desert = np.maximum(desert, w * np.exp(-dd * 0.9))
desert = smooth(0.22, 0.52, desert + (veg - 0.5) * 0.75)
tropic = smooth(0.0, 1.0, 1 - np.abs(dlat) / 18)
green = mix((0.16, 0.30, 0.09), (0.06, 0.24, 0.06), tropic)
landc = mix(green, (0.33, 0.36, 0.17), smooth(0.35, 0.7, veg) * (1 - tropic))
landc = mix(landc, (0.66, 0.52, 0.31), desert)
boreal = smooth(np.radians(50), np.radians(60), alat)
landc = mix(landc, (0.20, 0.25, 0.14), boreal * 0.8)
tundra = smooth(np.radians(63), np.radians(70), alat)
landc = mix(landc, (0.45, 0.43, 0.36), tundra * 0.8)
earth = mix(ocean, landc, land)
icej = (fbm(X * 6, Y * 6, Z * 6, 3, seed=11) - 0.5) * 0.10
seaice = smooth(np.radians(74), np.radians(80), alat + icej)
gimg = Image.new("L", (TW, TH), 0)
ImageDraw.Draw(gimg).polygon([((lo + 180) / 360 * TW, (90 - la) / 180 * TH) for lo, la in GREENLAND], fill=255)
landice = gaussian_filter(np.asarray(gimg, dtype=np.float32) / 255.0, 2.5) * smooth(np.radians(59), np.radians(63), alat)
ant = smooth(np.radians(-62), np.radians(-66), lat)  # Antártida
earth = mix(earth, (0.93, 0.95, 0.98), np.clip(seaice + landice + ant * land, 0, 1))

wx = fbm(X * 1.6, Y * 1.6, Z * 1.6, 4, seed=3)
wy = fbm(X * 1.6, Y * 1.6, Z * 1.6, 4, seed=5)
cl = fbm(X * 3.2 + wy, Y * 5.5, Z * 3.2 - wx, 6, seed=21)
itcz = smooth(0.0, 1.0, 1 - np.abs(dlat - 5) / 10) * 0.08
storm = smooth(0.0, 1.0, 1 - np.abs(alat - np.radians(55)) / np.radians(12)) * 0.07
clouds = smooth(0.52, 0.74, cl + itcz + storm) * 0.9

np.save(os.path.join(OUT, "earth.npy"), earth.astype(np.float32))
np.save(os.path.join(OUT, "earth_clouds.npy"), clouds.astype(np.float32))
np.save(os.path.join(OUT, "earth_land.npy"), land.astype(np.float32))
m = earth * (1 - clouds[..., None] * 0.85) + clouds[..., None] * 0.85
Image.fromarray((np.clip(earth, 0, 1) * 255).astype("uint8")).resize((1024, 512)).save(os.path.join(OUT, "earth_preview.png"))
Image.fromarray((np.clip(m, 0, 1) * 255).astype("uint8")).resize((1024, 512)).save(os.path.join(OUT, "earthc_preview.png"))
print("tierra real lista")
