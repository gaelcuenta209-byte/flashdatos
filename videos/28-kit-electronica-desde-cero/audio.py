"""Flash Datos · video 28 (kit para empezar en la electrónica desde cero): efectos y música originales sintetizados según timing.json.
Música: electro original en Re menor a 118 bpm con bombo, bajo con bombeo y arpegios; corte antes de "sin soldar" y caída fuerte ahí."""
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
rng = np.random.default_rng(28)


def norm(s):
    return re.sub(r"[^0-9a-záéíóúñü$]", "", s.lower())


def WT(i, needle, exact=False):
    for p in SG[i]["parts"]:
        for t, w in p[3]:
            x = norm(w)
            if (x == needle) if exact else (needle in x):
                return t
    raise KeyError(i + " " + needle)


G0, K0, K1 = PP("gancho", 0), PP("kit", 0), PP("kit", 1)
M0, M1, B0, B1 = PP("micro", 0), PP("micro", 1), PP("proto", 0), PP("proto", 1)
O0, O1, S0, S1, C0 = PP("osci", 0), PP("osci", 1), PP("cautin", 0), PP("cautin", 1), PP("cierre", 0)
TR = [K0[0] - 0.22, M0[0] - 0.22, B0[0] - 0.22, O0[0] - 0.22, S0[0] - 0.22, C0[0] - 0.22, C0[1] + 0.22]
SUB = {"box": K1[0] - 0.1, "esp": M1[0] - 0.1, "xray": B1[0] - 0.1, "hand": O1[0] - 0.1, "pen": S1[0] - 0.1}
ENDC = TR[6]
T = {k: WT(*v) for k, v in {
    "electronica": ("gancho", "electrónica"), "cero": ("gancho", "cero"), "cinco": ("gancho", "5", True), "cosas": ("gancho", "cosas"), "funciona": ("gancho", "funciona"),
    "resist": ("kit", "resistencias"), "frenan": ("kit", "frenan"), "leds": ("kit", "leds"), "luz": ("kit", "luz"), "capa": ("kit", "capacitores"), "carga": ("kit", "carga"),
    "trans": ("kit", "transistores"), "interr": ("kit", "interruptores"), "elec": ("kit", "electricidad"),
    "super": ("kit", "súper"), "elegoo": ("kit", "elegoo"), "arduino": ("kit", "arduino"), "sensores": ("kit", "sensores"), "motores": ("kit", "motores"), "tutorial": ("kit", "tutorial"),
    "micro": ("micro", "microcontrolador"), "compu": ("micro", "computadora"), "lee": ("micro", "lee", True), "ejecuta": ("micro", "ejecuta"), "controla": ("micro", "controla", True),
    "uno": ("micro", "uno", True), "internet": ("micro", "internet"), "esp": ("micro", "esp32"), "nucleos": ("micro", "núcleos"), "mhz": ("micro", "240"), "wifi": ("micro", "wifi"), "bt": ("micro", "bluetooth"),
    "proto": ("proto", "protoboard"), "p830": ("proto", "830"), "puntos": ("proto", "puntos"), "fila": ("proto", "fila"), "lamina": ("proto", "lámina"),
    "rieles": ("proto", "rieles"), "positivo": ("proto", "positivo"), "negativo": ("proto", "negativo"), "sin": ("proto", "sin", True), "soldar": ("proto", "soldar"),
    "osci": ("osci", "osciloscopio"), "multi": ("osci", "multímetro"), "numero": ("osci", "número"), "dibuja": ("osci", "dibuja"), "voltaje": ("osci", "voltaje"), "tiempo": ("osci", "tiempo"), "moverse": ("osci", "moverse"),
    "bolsillo": ("osci", "bolsillo"), "tres": ("osci", "3", True), "fnirsi": ("osci", "fnirsi"), "canales": ("osci", "canales"), "generador": ("osci", "generador"),
    "cautin": ("cautin", "cautín"), "caliente": ("cautin", "caliente"), "estano": ("cautin", "estaño"), "c200": ("cautin", "200"), "enfria": ("cautin", "enfriarse"), "electricamente": ("cautin", "eléctricamente"),
    "pinecil": ("cautin", "pinecil"), "usbc": ("cautin", "usbc"), "doce": ("cautin", "12"), "c400": ("cautin", "400"), "toques": ("cautin", "toques"),
    "ccosas": ("cierre", "cosas"), "armar": ("cierre", "armar"), "programar": ("cierre", "programar"), "medir": ("cierre", "medir"), "soldar2": ("cierre", "soldar"), "links": ("cierre", "links"), "descripcion": ("cierre", "descripción"),
}.items()}
T["multi2"] = [t for p in SG["osci"]["parts"] for t, w in p[3] if norm(w) == "multímetro"][1]


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
# transiciones: glitch + zap + whoosh
for i, tf in enumerate(TR[:6]):
    place(sfx, whoosh(0.5), tf - 0.4, 0.22)
    place(sfx, glitch_sfx(), tf - 0.12, 0.2)
    place(sfx, zap(), tf - 0.02, 0.16)
for ts in SUB.values():
    place(sfx, whoosh(0.35, 300, 2600, 500), ts - 0.2, 0.14)
# gancho: el 0 que late, sello, el 5 y los objetos que salen
for k in range(6): place(sfx, thud(0.3), 0.1 + k * 0.42, 0.12 if k < 5 else 0.0)
place(sfx, pop(700), T["electronica"], 0.14)
place(sfx, clank(0.4, 380), T["cero"], 0.24); place(sfx, thud(0.5), T["cero"], 0.3)
place(sfx, boom(1.4), T["cinco"], 0.42); place(sfx, glitch_sfx(0.3), T["cinco"] - 0.05, 0.16)
for k in range(5): place(sfx, pop(520 + 90 * k), T["cinco"] + 0.12 + k * 0.1, 0.13, pan=[0, 0.6, 0.4, -0.4, -0.6][k])
place(sfx, ding(1046.5, 0.9), T["funciona"], 0.1)
# kit de componentes
for key, f in (("resist", 520), ("leds", 620), ("capa", 700), ("trans", 780)): place(sfx, pop(f), T[key], 0.15)
place(sfx, warble(0.8, 260), T["frenan"], 0.07)
place(sfx, ding(1318.5, 0.7), T["luz"], 0.1); place(sfx, shimmer(0.6), T["luz"], 0.07)
place(sfx, rise(1.1, 300, 1500, 0.2), T["carga"] - 0.1, 0.1)
for k in range(4): place(sfx, tick(1900, 0.05), T["interr"] + k * 0.5, 0.18)
for key in ("arduino", "sensores", "motores", "tutorial"): place(sfx, pop(600), T[key], 0.13)
place(sfx, rumble(0.9), T["motores"], 0.08)
place(sfx, arp_up(523.25), T["super"], 0.1)
# microcontrolador
place(sfx, thud(0.5), T["micro"], 0.22)
for k in range(3): place(sfx, blip(900 + 120 * k, 0.07), T["lee"] + k * 0.1, 0.08, pan=-0.5)
place(sfx, typing(1.6), T["ejecuta"], 0.1)
place(sfx, blip(1568, 0.12, "sine"), T["controla"], 0.1); place(sfx, rumble(0.8), T["controla"] + 0.1, 0.07)
place(sfx, whoosh(0.4, 400, 2600, 600), T["internet"] - 0.2, 0.12)
place(sfx, clank(0.3, 640), T["esp"], 0.16)
for k in range(2): place(sfx, ding(880 * (1.5 if k else 1), 0.5), T["nucleos"] + k * 0.18, 0.08)
for k in range(10): place(sfx, tick(2400 + 80 * k, 0.04), T["mhz"] - 0.05 + k * 0.05, 0.06)
place(sfx, warble(0.5, 1200), T["wifi"], 0.06); place(sfx, blip(2093, 0.1, "sine"), T["bt"], 0.09)
# protoboard
place(sfx, thud(0.5), T["proto"], 0.2)
for k in range(18): place(sfx, tick(2000 + 60 * k, 0.04), T["p830"] - 0.1 + k * 0.05, 0.06, pan=(k % 5 - 2) * 0.3)
place(sfx, ding(987.8, 0.6), T["puntos"], 0.1)
place(sfx, shimmer(0.8), SUB["xray"] + 0.1, 0.08)
place(sfx, pop(760), T["fila"], 0.13); place(sfx, clank(0.3, 900), T["lamina"], 0.14)
place(sfx, pop(520), T["positivo"], 0.12); place(sfx, pop(420), T["negativo"], 0.12)
for k in range(4): place(sfx, clank(0.2, 1100 + 100 * k), T["sin"] - 0.1 + k * 0.08, 0.08)
place(sfx, boom(1.3), T["soldar"], 0.32); place(sfx, ding(1318.5, 0.8), T["soldar"] + 0.05, 0.1)
# osciloscopio
place(sfx, thud(0.5), T["osci"], 0.2)
for k in range(4): place(sfx, blip(1400, 0.05), T["numero"] + k * 0.12, 0.06)
place(sfx, rise(1.4, 220, 900, 0.1), T["dibuja"] - 0.05, 0.08)
place(sfx, warble(1.2, 440), T["moverse"], 0.06)
place(sfx, pop(640), T["bolsillo"], 0.12); place(sfx, clank(0.35, 500), T["tres"], 0.2)
for key, f in (("canales", 700), ("multi2", 820), ("generador", 940)): place(sfx, pop(f), T[key], 0.13)
# cautín
place(sfx, rise(1.2, 120, 700, 0.6), T["caliente"] - 0.3, 0.1)
place(sfx, hp(rng.standard_normal(int(2.2 * SR)), 3000) * np.linspace(0, 1, int(2.2 * SR)) ** 0.5 * np.linspace(1, 0, int(2.2 * SR)) * 0.5, T["estano"], 0.06)
place(sfx, ding(1760, 0.5), T["c200"], 0.07)
place(sfx, shimmer(0.7), T["enfria"] + 0.3, 0.09)
place(sfx, zap(0.3), T["electricamente"], 0.1)
place(sfx, clank(0.25, 820), T["usbc"], 0.14)
for k in range(12): place(sfx, tick(1800, 0.04), T["doce"] - 0.2 + k * 0.09, 0.06)
place(sfx, rise(0.8, 300, 1600, 0.3), T["c400"] - 0.2, 0.09)
place(sfx, buzz(0.5), T["toques"], 0.16); place(sfx, thud(0.4), T["toques"], 0.2)
# cierre
for key in ("armar", "programar", "medir", "soldar2"): place(sfx, ding(1046.5 if key != "soldar2" else 1568, 0.5), T[key], 0.09)
place(sfx, arp_up(659.25), T["links"], 0.1); place(sfx, pop(500), T["descripcion"], 0.12)
place(sfx, boom(1.6), ENDC, 0.3); place(sfx, shimmer(1.0), ENDC + 0.1, 0.1)


# ---------------- música ----------------
def music():
    bpm = 118; beat = 60 / bpm; t = np.arange(N) / SR
    roots = [146.83, 116.54, 174.61, 130.81]                     # Re, Si bemol, Fa, Do
    chords = [[293.66, 349.23, 440.0], [233.08, 293.66, 349.23], [349.23, 440.0, 523.25], [261.63, 329.63, 392.0]]
    bar = beat * 4
    ci = (np.floor(t / (bar * 2)) % 4).astype(int)
    # nivel de cada sección (intro suave, corte antes de la caída, resumen sin bombo)
    def sec(lo, hi): return ((t >= lo) & (t < hi)).astype(float)
    brk0 = T["sin"] - 1.6
    drums = sec(TR[0], brk0) + sec(T["soldar"], TR[5])
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
        g = 0.6 + 0.4 * (1 if (TR[0] <= ta < brk0) or (T["soldar"] <= ta) else 0.5)
        place(out, lp(b, 4000), ta, g, pan=0.45 if k % 2 else -0.45)
    # batería
    kick_n = int(0.3 * SR); kt = np.arange(kick_n) / SR
    kick = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-kt / 0.035)) / SR) * np.exp(-kt / 0.16)
    kick[:200] += np.linspace(1, 0, 200) * 0.6
    hat = hp(rng.standard_normal(int(0.06 * SR)), 7000) * np.exp(-np.arange(int(0.06 * SR)) / SR / 0.012)
    clap = bp(rng.standard_normal(int(0.2 * SR)), 900, 4000) * np.exp(-np.arange(int(0.2 * SR)) / SR / 0.05)
    for k, bt in enumerate(np.arange(0, END, beat)):
        on = (TR[0] <= bt < brk0) or (T["soldar"] <= bt < TR[5])
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
