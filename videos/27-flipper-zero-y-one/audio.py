"""Flash Datos · video 27 (Flipper Zero y Flipper One): efectos y música originales sintetizados según timing.json.
Música: synthwave original en La menor a 124 bpm con bombo, bajo con bombeo, arpegios y una caída fuerte cuando aparece el Flipper One."""
import json, math, os, re
import numpy as np
from scipy.signal import stft, istft, butter, sosfilt
from scipy.io import wavfile

BASE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
TM = json.load(open(os.path.join(BASE, "timing.json")))
SG = {s["id"]: s for s in TM["segments"]}
PP = lambda i, k: SG[i]["parts"][k]
END = TM["end"]
N = int(END * SR)
rng = np.random.default_rng(27)


def norm(s):
    return re.sub(r"[^0-9a-záéíóúñü$]", "", s.lower())


def WT(i, needle, exact=False):
    for p in SG[i]["parts"]:
        for t, w in p[3]:
            x = norm(w)
            if (x == needle) if exact else (needle in x):
                return t
    raise KeyError(i + " " + needle)


G0, Z0 = PP("gancho", 0), PP("zero", 0)
F0, F1, F2 = PP("funciona", 0), PP("funciona", 1), PP("funciona", 2)
P0, P1 = PP("polemica", 0), PP("polemica", 1)
O0, O1, O2 = PP("one", 0), PP("one", 1), PP("one", 2)
R0, K0 = PP("porque", 0), PP("cierre", 0)
TR = [Z0[0] - 0.22, F0[0] - 0.22, P0[0] - 0.22, O0[0] - 0.2, R0[0] - 0.22, K0[0] - 0.22, K0[1] + 0.22]
ENDC = TR[6]
T = {k: WT(*v) for k, v in {
    "hacker": ("gancho", "hacker"), "canada": ("gancho", "canadá"), "prohibir": ("gancho", "prohibir"), "hermano": ("gancho", "hermano"), "esperaban": ("gancho", "esperaban"),
    "zero": ("zero", "zero"), "mano": ("zero", "mano"), "p169": ("zero", "$169"), "segun": ("zero", "según"), "millon": ("zero", "millón"),
    "escucha": ("funciona", "escucha"), "guarda": ("funciona", "guarda"), "repite": ("funciona", "repite"),
    "radio": ("funciona", "radio"), "nfc": ("funciona", "nfc"), "tarjetas": ("funciona", "tarjetas"), "ir": ("funciona", "infrarrojo"), "teles": ("funciona", "teles"),
    "delfin": ("funciona", "delfín"), "y2024": ("polemica", "2024"), "canada2": ("polemica", "canadá"), "prohibir2": ("polemica", "prohibir"), "autos": ("polemica", "autos"),
    "cambian": ("polemica", "cambian"), "clic": ("polemica", "clic"), "one": ("one", "one"), "zero2": ("one", "zero"), "compu": ("one", "computadora"), "linux": ("one", "linux"),
    "nucleos": ("one", "núcleos"), "gb": ("one", "gb"), "ia": ("one", "inteligencia"), "rpi": ("one", "raspberry"),
    "red": ("one", "red"), "wifi": ("one", "wifi"), "hdmi": ("one", "hdmi"), "ranura": ("one", "ranura"), "g5": ("one", "5g"), "disco": ("one", "disco"),
    "router": ("one", "router"), "vpn": ("one", "vpn"), "lab": ("one", "laboratorio"),
    "todos": ("porque", "todos"), "reservas": ("porque", "reservas"), "p20": ("porque", "$20"), "p379": ("porque", "$379"), "kick": ("porque", "kickstarter"),
    "cerca": ("cierre", "cerca"), "cone": ("cierre", "one"), "redes": ("cierre", "redes"), "hermanos": ("cierre", "hermanos"), "gemelos": ("cierre", "gemelos"),
}.items()}
T["no"] = WT("polemica", "no", True)


# ---------------- utilidades ----------------
def place(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or len(sig) == 0:
        return
    if sig.ndim == 1:
        sig = np.stack([sig * math.sqrt((1 - pan) / 2) * 1.414, sig * math.sqrt((1 + pan) / 2) * 1.414], -1)
    s0 = max(0, -i); j = min(len(buf), i + len(sig))
    buf[max(i, 0):j] += sig[s0:j - i] * gain


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x, axis=0)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x, axis=0)


def nrm(y):
    return y / (np.max(np.abs(y)) + 1e-9)


def env_t(dur):
    n = int(dur * SR); return n, np.arange(n) / SR


# ---------------- efectos ----------------
def whoosh(dur, f0=180, f1=2400, f2=300, peak=0.62):
    n = int(dur * SR)
    f, tt, Z = stft(rng.standard_normal(n + 2048), SR, nperseg=1024)
    tt = tt / dur
    fc = np.where(tt < peak, f0 * (f1 / f0) ** (tt / peak), f1 * (f2 / f1) ** ((tt - peak) / (1 - peak)))
    shape = np.exp(-((np.log(np.maximum(f, 20))[:, None] - np.log(fc)[None, :]) ** 2) / (2 * 0.55 ** 2))
    env = np.clip(tt / peak, 0, 1) ** 1.6 * np.clip((1 - tt) / (1 - peak), 0, 1) ** 1.2
    _, y = istft(Z * shape * env[None, :], SR, nperseg=1024)
    y = nrm(y[:n]); pan = np.linspace(-0.6, 0.6, n)
    return np.stack([y * (1 - pan) * 0.8, np.roll(y, 240) * (1 + pan) * 0.8], -1)


def zap(dur=0.32):
    n, t = env_t(dur)
    f = 2600 * (180 / 2600) ** (t / dur)
    tone = np.tanh(3 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t / 0.10)
    crack = bp(rng.standard_normal(n) * (rng.random(n) < 0.08) * np.exp(-t / 0.05), 1500, 9000) * 3
    return nrm(tone * 0.5 + crack * 0.6 + np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.12) * 0.6)


def glitch_sfx(dur=0.38):
    """Ruido digital entrecortado (bitcrush) para las transiciones glitch."""
    n, t = env_t(dur)
    y = np.zeros(n)
    k = 0
    while k < n:
        L = int(SR * rng.uniform(0.012, 0.045))
        kind = rng.integers(3)
        seg = np.arange(min(L, n - k)) / SR
        if kind == 0: y[k:k + len(seg)] = np.sign(np.sin(2 * np.pi * rng.uniform(300, 2400) * seg)) * 0.6
        elif kind == 1: y[k:k + len(seg)] = rng.standard_normal(len(seg)) * 0.7
        else: y[k:k + len(seg)] = 0
        k += L
    step = 6; y = np.repeat(y[::step], step)[:n]
    return nrm(y * np.clip((dur - t) / 0.1, 0, 1))


def boom(dur=1.6, f_hi=70, f_lo=30):
    n, t = env_t(dur)
    body = np.sin(2 * np.pi * np.cumsum(f_lo + f_hi * np.exp(-t / 0.18)) / SR) * np.exp(-t / 0.7)
    y = body + lp(rng.standard_normal(n) * np.exp(-t / 0.25), 240) * 0.9
    return nrm(y * np.clip(t / 0.005, 0, 1))


def thud(dur=0.5):
    n, t = env_t(dur)
    y = np.sin(2 * np.pi * np.cumsum(60 + 120 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.12)
    y += bp(rng.standard_normal(n), 300, 3000) * np.exp(-t / 0.02) * 0.8
    return nrm(y)


def ding(freq, dur=1.0):
    n, t = env_t(dur)
    y = (np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.45) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t / 0.18)
         + 0.15 * np.sin(2 * np.pi * freq * 5.40 * t) * np.exp(-t / 0.08)) * np.clip(t / 0.004, 0, 1)
    return nrm(y)


def blip(freq, dur=0.09, wave="sq"):
    n, t = env_t(dur)
    s = np.sin(2 * np.pi * freq * t)
    y = (np.sign(s) * 0.6 + s * 0.4 if wave == "sq" else s) * np.exp(-t / (dur * 0.35)) * np.clip(t / 0.002, 0, 1)
    return y


def tick(freq=2400, dur=0.06):
    n, t = env_t(dur)
    return nrm(np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.012) + 0.3 * rng.standard_normal(n) * np.exp(-t / 0.004))


def pop(freq=500, dur=0.14):
    n, t = env_t(dur)
    f = freq * (1 + 1.6 * np.exp(-t / 0.02))
    return nrm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035))


def clank(dur=0.35, base=520):
    n, t = env_t(dur)
    y = sum(a * np.sin(2 * np.pi * base * r * t) * np.exp(-t / d) for a, r, d in [(1, 1, 0.09), (0.7, 2.31, 0.06), (0.5, 3.97, 0.04), (0.35, 5.6, 0.03)])
    return nrm(y + 0.5 * rng.standard_normal(n) * np.exp(-t / 0.006))


def rise(dur, f0=200, f1=1200, noise=0.5):
    n, t = env_t(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    nz = hp(rng.standard_normal(n), 2000) * (t / dur) ** 2 * noise
    return nrm((y * 0.6 + nz) * (t / dur) ** 1.5 * np.clip((dur - t) / 0.03, 0, 1))


def warble(dur, f=900):
    """Chirrido de radio (FSK) para las señales del control."""
    n, t = env_t(dur)
    sym = (np.floor(t * 60) % 2) * 2 - 1
    sym *= np.where(rng.random(int(dur * 60) + 2)[np.floor(t * 60).astype(int)] < 0.5, 1, -1)
    y = np.sin(2 * np.pi * np.cumsum(f + 180 * sym) / SR) * np.clip(t / 0.02, 0, 1) * np.clip((dur - t) / 0.05, 0, 1)
    return y * 0.8


def nfc_beep():
    return np.concatenate([blip(1800, 0.09, "sine"), np.zeros(int(0.03 * SR)), blip(2400, 0.12, "sine")])


def buzz(dur=0.45):
    n, t = env_t(dur)
    y = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 117 * t)) * 0.5
    return lp(y, 1800) * np.clip((dur - t) / 0.05, 0, 1) * ((np.floor(t * 9) % 2) * 0.4 + 0.6) * 0.8


def chirp_car():
    a = blip(1500, 0.12, "sine"); return np.concatenate([a, np.zeros(int(0.06 * SR)), a])


def rumble(dur):
    n, t = env_t(dur)
    y = lp(rng.standard_normal(n), 300) * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * t)) + bp(rng.standard_normal(n), 800, 2400) * 0.15 * (np.sin(2 * np.pi * 7 * t) > 0.6)
    return nrm(y * np.clip(t / 0.08, 0, 1) * np.clip((dur - t) / 0.15, 0, 1))


def typing(dur):
    n, t = env_t(dur); y = np.zeros(n); k = 0
    while k < n:
        c = tick(rng.uniform(2500, 4200), 0.03); y[k:k + len(c)] += c[:max(0, min(len(c), n - k))] * rng.uniform(0.5, 1)
        k += int(SR * rng.uniform(0.05, 0.11))
    return y


def shimmer(dur):
    n, t = env_t(dur); y = np.zeros(n)
    for k in range(16):
        fq = 1200 * 2 ** (rng.integers(0, 24) / 12); t0 = rng.uniform(0, dur * 0.8)
        b = blip(fq, 0.25, "sine"); i = int(t0 * SR); y[i:i + len(b)] += b[:max(0, n - i)] * 0.5
    return y * np.clip((dur - t) / 0.2, 0, 1)


def tear():
    n, t = env_t(0.35)
    return nrm(bp(rng.standard_normal(n), 1500, 7000) * (rng.random(n) < 0.4) * np.clip((0.35 - t) / 0.35, 0, 1) ** 0.5)


def arp_up(base, steps=(0, 4, 7, 12, 16), gap=0.06):
    y = np.zeros(int((gap * len(steps) + 0.3) * SR))
    for k, s in enumerate(steps):
        b = blip(base * 2 ** (s / 12), 0.22, "sq"); i = int(k * gap * SR); y[i:i + len(b)] += b
    return y * 0.6


sfx = np.zeros((N, 2))
# transiciones: glitch + zap + whoosh (la de la aparición del One es una caída fuerte)
for i, tf in enumerate(TR[:6]):
    place(sfx, glitch_sfx(), tf - 0.12, 0.30)
    place(sfx, zap(), tf - 0.05, 0.32)
    place(sfx, whoosh(0.55, 300, 3000, 400), tf - 0.35, 0.16)
place(sfx, rise(2.0, 150, 1600), TR[3] - 2.0, 0.07)
place(sfx, boom(2.2, 80, 28), TR[3], 0.5)
place(sfx, ding(1760.0, 1.2), ENDC + 0.05, 0.22); place(sfx, zap(), ENDC - 0.05, 0.3)
# glitches pequeños
for tt in (T["hacker"], T["esperaban"] + 0.1):
    place(sfx, glitch_sfx(0.22), tt - 0.08, 0.18)

# gancho: pings de radio, sello, el hermano mayor que sube
for k in range(7):
    tp = k * 0.5
    if tp < T["hermano"]:
        place(sfx, blip(1320, 0.18, "sine"), tp + 0.05, 0.06, pan=-0.2 + 0.4 * (k % 2))
place(sfx, whoosh(0.4, 400, 2600, 600), T["canada"] - 0.2, 0.12)
place(sfx, thud(), T["prohibir"], 0.38); place(sfx, boom(1.0), T["prohibir"], 0.25)
place(sfx, rise(0.7, 80, 400, 0.2), T["hermano"] - 0.1, 0.12); place(sfx, boom(1.6, 60, 26), T["hermano"] + 0.55, 0.35)

# el Zero
place(sfx, whoosh(0.6, 200, 2200, 300), TR[0] + 0.05, 0.14)
place(sfx, pop(620), T["mano"], 0.14)
for k in range(10): place(sfx, tick(2600 + 80 * k, 0.04), T["p169"] - 0.05 + k * 0.045, 0.06)
place(sfx, ding(2093.0, 0.9), T["p169"] + 0.45, 0.16); place(sfx, ding(2637.0, 0.9), T["p169"] + 0.53, 0.12)
place(sfx, pop(520), T["segun"], 0.12)
for k in range(26): place(sfx, blip(900 + 40 * k, 0.05), T["segun"] + 0.12 + k * (T["millon"] + 0.3 - T["segun"] - 0.12) / 26, 0.04, pan=(k % 5 - 2) * 0.3)
place(sfx, boom(1.3), T["millon"], 0.22); place(sfx, ding(1568.0, 1.0), T["millon"] + 0.05, 0.18)

# cómo funciona
for k, key in enumerate(("escucha", "guarda", "repite")):
    place(sfx, pop(500 + 120 * k), T[key] - 0.05, 0.14)
place(sfx, tick(3000, 0.05), T["escucha"] - 0.1, 0.2)
place(sfx, warble(T["guarda"] - T["escucha"] - 0.2), T["escucha"], 0.07)
place(sfx, arp_up(1046.5, (0, 7, 12)), T["guarda"], 0.12)
place(sfx, warble(0.9, 1100), T["repite"], 0.07)
place(sfx, rumble(0.9), T["repite"] + 0.35, 0.14)
place(sfx, ding(1318.5, 1.0), T["repite"] + 1.0, 0.18)
for key in ("radio", "nfc", "ir"):
    place(sfx, whoosh(0.4, 300, 2600, 500), T[key] - 0.3, 0.12); place(sfx, thud(0.3), T[key] - 0.02, 0.15)
place(sfx, nfc_beep(), T["tarjetas"], 0.12)
place(sfx, tick(1500, 0.05), T["teles"], 0.2); place(sfx, blip(160, 0.4, "sine"), T["teles"] + 0.02, 0.1)
place(sfx, pop(700), T["delfin"], 0.14)
for k in range(1, 4):
    tl = T["delfin"] + 0.2 + k * (F2[1] - T["delfin"] - 0.2) / 4
    place(sfx, arp_up(784.0 * 2 ** (k / 12)), tl, 0.12)
for k in range(10): place(sfx, blip(1500 + 100 * (k % 4), 0.05), F2[0] + 0.3 + k * 0.32, 0.04, pan=0.5 * math.sin(k))

# la polémica
for k in range(12): place(sfx, tick(1800 + 60 * k, 0.04), P0[0] - 0.2 + k * (T["y2024"] - P0[0] + 0.2) / 12, 0.08)
place(sfx, thud(0.4), T["y2024"], 0.2)
place(sfx, whoosh(0.4, 400, 2400, 600), T["canada2"] - 0.25, 0.12)
place(sfx, thud(), T["prohibir2"], 0.4); place(sfx, boom(1.2), T["prohibir2"], 0.28)
for k in range(4): place(sfx, blip(950 if k % 2 else 760, 0.22, "sine"), T["autos"] + k * 0.25, 0.07)
clicks = [P1[0] - 0.12 + 0.35, T["cambian"] + 0.1, T["clic"] - 0.35]
for c in clicks:
    place(sfx, tick(3200, 0.04), c, 0.18); place(sfx, warble(0.45, 1200), c + 0.05, 0.05); place(sfx, chirp_car(), c + 0.62, 0.08)
tr = T["clic"] + 0.15
place(sfx, warble(0.5, 1200), tr, 0.05); place(sfx, buzz(), tr + 0.58, 0.12)
place(sfx, whoosh(0.4, 600, 2600, 400), T["no"] - 0.2, 0.1)
place(sfx, arp_up(1046.5, (0, 4, 7, 12)), T["no"] + 0.05, 0.14)

# el Flipper One
for k in range(4): place(sfx, whoosh(0.45, 250, 2600, 400), TR[3] + 0.1 + k * 0.12, 0.08)
place(sfx, clank(0.4, 380), T["one"] - 0.02, 0.24); place(sfx, boom(1.4, 70, 30), T["one"], 0.3)
place(sfx, whoosh(0.35, 800, 3200, 700), T["zero2"] + 0.2, 0.14)
place(sfx, pop(480), T["compu"], 0.14); place(sfx, pop(640), T["linux"], 0.14)
place(sfx, typing(1.4), T["compu"] - 0.05, 0.08)
a0 = O1[0] - 0.1
for k in range(8): place(sfx, blip(523.25 * 2 ** ([0, 2, 3, 5, 7, 8, 10, 12][k] / 12), 0.09), a0 + 0.15 + k * (T["nucleos"] + 0.1 - a0 - 0.15) / 8, 0.07)
place(sfx, whoosh(0.4, 200, 2000, 300), T["gb"] - 0.3, 0.12); place(sfx, clank(0.3, 600), T["gb"] + 0.08, 0.15)
place(sfx, shimmer(1.0), T["ia"], 0.12)
place(sfx, rise(0.9, 200, 900, 0.1), T["rpi"], 0.08); place(sfx, ding(1760.0, 1.0), T["rpi"] + 0.6, 0.18)
for key in ("red", "wifi", "hdmi", "ranura"): place(sfx, pop(560 if key != "wifi" else 760), T[key], 0.13)
for key in ("g5", "disco"): place(sfx, whoosh(0.3, 400, 2400, 500), T[key] - 0.2, 0.1); place(sfx, clank(0.25, 700), T[key] + 0.15, 0.13)
place(sfx, whoosh(0.5, 2000, 400, 150, 0.3), T["router"] - 0.35, 0.14)
for k in range(12): place(sfx, blip(1700 + 200 * (k % 3), 0.04), T["router"] + 0.1 + k * 0.18, 0.035, pan=0.6 * math.sin(k * 1.3))
place(sfx, tick(1200, 0.06), T["vpn"] + 0.3, 0.2); place(sfx, ding(1318.5, 0.6), T["vpn"] + 0.32, 0.1)
place(sfx, shimmer(0.9), T["lab"], 0.1)

# por qué ahora
for k in range(9): place(sfx, pop(420 + 60 * (k % 5)), T["todos"] - 0.2 + k * 0.11, 0.1, pan=(k % 3 - 1) * 0.5)
place(sfx, arp_up(1318.5, (0, 7)), T["reservas"], 0.14)
place(sfx, tear(), T["p20"] - 0.1, 0.16); place(sfx, thud(0.3), T["p20"] + 0.1, 0.14)
for k in range(12): place(sfx, tick(2400 + 60 * k, 0.04), T["p379"] - 0.1 + k * 0.05, 0.06)
place(sfx, ding(2093.0, 0.9), T["p379"] + 0.5, 0.16); place(sfx, ding(2637.0, 0.9), T["p379"] + 0.58, 0.13)
place(sfx, pop(600), T["kick"], 0.12)

# resumen
place(sfx, whoosh(0.6, 300, 2800, 400), TR[5] + 0.05, 0.12)
place(sfx, blip(1320, 0.2, "sine"), T["cerca"] - 0.05, 0.08); place(sfx, shimmer(0.8), T["redes"], 0.1)
place(sfx, arp_up(1046.5, (0, 4, 7)), T["hermanos"], 0.13); place(sfx, buzz(0.3), T["gemelos"], 0.07)


# ---------------- música ----------------
def music():
    bpm = 124; beat = 60 / bpm; t = np.arange(N) / SR
    roots = [110.0, 87.31, 130.81, 98.0]                        # La, Fa, Do, Sol
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    bar = beat * 4
    ci = (np.floor(t / (bar * 2)) % 4).astype(int)
    # nivel de cada sección (intro suave, corte antes de la caída, resumen sin bombo)
    def sec(lo, hi): return ((t >= lo) & (t < hi)).astype(float)
    brk0 = T["no"] - 0.4
    drums = sec(TR[0], brk0) + sec(TR[3], TR[5])
    full = drums.copy()
    soft = 1 - drums
    # bombeo por pulso (sidechain del bombo)
    ph = (t % beat) / beat
    pump = 0.25 + 0.75 * np.clip(ph / 0.45, 0, 1) ** 0.8
    pump = np.where(drums > 0, pump, 1.0)
    out = np.zeros((N, 2))
    # colchón (saw desafinado)
    pad = np.zeros((N, 2))
    for v in range(3):
        f = np.array([c[v] for c in chords])[ci]
        for side, det in ((0, -0.08), (1, 0.08)):
            phs = 2 * np.pi * np.cumsum(f * 2 ** (det / 12)) / SR
            pad[:, side] += sum(np.sin(k * phs) / k for k in range(1, 7)) * 0.12
    pad = lp(pad, 2200)
    out += pad * (pump * (0.55 + 0.45 * full))[:, None]
    # bajo en corcheas
    f = np.array(roots)[ci] / 2 * np.where((np.floor(t / (beat / 2)) % 4) == 3, 2, 1)
    phs = 2 * np.pi * np.cumsum(f) / SR
    bass = sum(np.sin(k * phs) / k ** 1.2 for k in range(1, 9))
    e8 = np.exp(-((t % (beat / 2)) / 0.12))
    bass = lp(bass * e8, 900) * 0.5
    out += (bass * pump * (0.25 + 0.75 * full))[:, None]
    # arpegio en semicorcheas
    s16 = beat / 4
    for k in range(int(END / s16) + 1):
        ta = k * s16
        if ta >= END: break
        c = chords[int(ta / (bar * 2)) % 4]
        fq = c[[0, 1, 2, 1, 2, 0, 1, 2][k % 8]] * 2 * (2 if k % 16 >= 12 else 1)
        b = blip(fq, 0.16, "sq") * 0.07
        g = 0.6 + 0.4 * (1 if (TR[0] <= ta < brk0) or (TR[3] <= ta) else 0.5)
        place(out, lp(b, 4000), ta, g, pan=0.45 if k % 2 else -0.45)
    # batería
    kick_n = int(0.3 * SR); kt = np.arange(kick_n) / SR
    kick = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-kt / 0.035)) / SR) * np.exp(-kt / 0.16)
    kick[:200] += np.linspace(1, 0, 200) * 0.6
    hat = hp(rng.standard_normal(int(0.06 * SR)), 7000) * np.exp(-np.arange(int(0.06 * SR)) / SR / 0.012)
    clap = bp(rng.standard_normal(int(0.2 * SR)), 900, 4000) * np.exp(-np.arange(int(0.2 * SR)) / SR / 0.05)
    for k, bt in enumerate(np.arange(0, END, beat)):
        on = (TR[0] <= bt < brk0) or (TR[3] <= bt < TR[5])
        if on:
            place(out, kick * 0.9, bt)
            if k % 2 == 1: place(out, clap * 0.35, bt)
        place(out, hat * (0.18 if on else 0.08), bt + beat / 2)
    out = lp(out, 9000)
    fade = np.clip((END - t) / 1.8, 0, 1) * np.clip(t / 0.15, 0, 1)
    return out * fade[:, None] / np.max(np.abs(out))


mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
pk = np.max(np.abs(sfx))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx / max(1.0, pk) * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s · pico sfx", round(float(pk), 2))
