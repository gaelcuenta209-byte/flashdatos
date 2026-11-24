"""Efectos de sonido y música de fondo originales, sintetizados para la línea de tiempo del video."""
import json, math, os
import numpy as np
from scipy.signal import stft, istft, butter, sosfilt
from scipy.io import wavfile

BASE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
END = TM["end"]
N = int(END * SR)
rng = np.random.default_rng(42)
# video 42: tiempos iguales a escena.py
S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
SPLIT = lambda k, f: S0[k] + (S1[k] - S0[k]) * f
ORDER = ["gancho", "distancia", "enana", "pareja", "docena", "llamaradas", "cierre"]
FLASHES = [S0[k] - 0.22 for k in ORDER[1:]]
CARD = S1["cierre"] + 0.25

def place(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    if sig.ndim == 1:
        l = sig * math.sqrt((1 - pan) / 2) * 1.414; r = sig * math.sqrt((1 + pan) / 2) * 1.414
        sig = np.stack([l, r], -1)
    j = min(len(buf), i + len(sig))
    s0 = max(0, -i)
    buf[max(i, 0):j] += sig[s0:j - i] * gain


def whoosh(dur, f0=180, f1=2400, f2=300):
    n = int(dur * SR)
    noise = rng.standard_normal(n + 2048)
    f, tt, Z = stft(noise, SR, nperseg=1024)
    tt = tt / dur
    peak = 0.62
    fc = np.where(tt < peak, f0 * (f1 / f0) ** (tt / peak), f1 * (f2 / f1) ** ((tt - peak) / (1 - peak)))
    lf = np.log(np.maximum(f, 20))[:, None]
    shape = np.exp(-((lf - np.log(fc)[None, :]) ** 2) / (2 * 0.55 ** 2))
    env = np.clip(tt / peak, 0, 1) ** 1.6 * np.clip((1 - tt) / (1 - peak), 0, 1) ** 1.2
    Z = Z * shape * env[None, :]
    _, y = istft(Z, SR, nperseg=1024)
    y = y[:n]
    y /= np.max(np.abs(y)) + 1e-9
    l = y; r = np.roll(y, 240)
    pan = np.linspace(-0.6, 0.6, n)
    return np.stack([l * (1 - pan) * 0.8, r * (1 + pan) * 0.8], -1)


def zap(dur=0.32):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 2600 * (180 / 2600) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.tanh(3 * np.sin(ph)) * np.exp(-t / 0.10)
    crack = rng.standard_normal(n) * (rng.random(n) < 0.08) * np.exp(-t / 0.05)
    sos = butter(2, [1500, 9000], "bandpass", fs=SR, output="sos")
    crack = sosfilt(sos, crack) * 3
    sub = np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.12)
    y = tone * 0.5 + crack * 0.6 + sub * 0.6
    return y / (np.max(np.abs(y)) + 1e-9)


def boom(dur=2.6):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 30 + 40 * np.exp(-t / 0.25)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.9)
    nz = rng.standard_normal(n) * np.exp(-t / 0.35)
    sos = butter(2, 260, "lowpass", fs=SR, output="sos")
    y = body + sosfilt(sos, nz) * 0.9
    att = np.clip(t / 0.01, 0, 1)
    return y * att / (np.max(np.abs(y)) + 1e-9)


def ding(freq, dur=1.1):
    n = int(dur * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.45)
         + 0.35 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t / 0.18)
         + 0.15 * np.sin(2 * np.pi * freq * 5.40 * t) * np.exp(-t / 0.08))
    y *= np.clip(t / 0.004, 0, 1)
    return y / np.max(np.abs(y))


def pad_music():
    t = np.arange(N) / SR
    # progresión original en Re menor: Dm - Bb - F - C, grave y espacial
    chords = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [87.31, 110.0, 130.81], [130.81, 164.81, 196.0]]
    seg = 4.0
    out = np.zeros((N, 2))
    for ci in range(int(END / seg) + 2):
        notes = chords[ci % 4]
        a = ci * seg; b = a + seg + 1.5
        i0 = int(a * SR); i1 = min(N, int(b * SR))
        if i0 >= N:
            break
        tt = t[i0:i1] - a
        env = np.clip(tt / 1.2, 0, 1) * np.clip((seg + 1.5 - tt) / 1.5, 0, 1)
        for k, fq in enumerate(notes):
            for det, side in ((-0.18, 0), (0.18, 1)):
                f = fq * 2 ** (det / 12)
                v = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt) + 0.08 * np.sin(2 * np.pi * 3 * f * tt))
                out[i0:i1, side] += v * env * 0.12
        bass = np.sin(2 * np.pi * notes[0] / 2 * tt) * env * 0.22
        out[i0:i1] += bass[:, None]
    # pulso suave a 76 BPM
    beat = 60 / 84
    for bt in np.arange(0, END, beat):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        k = np.sin(2 * np.pi * (55 + 60 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.09) * 0.35
        place(out, k, bt)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    out *= lfo[:, None]
    sos = butter(2, 2200, "lowpass", fs=SR, output="sos")
    out = sosfilt(sos, out, axis=0)
    return out / np.max(np.abs(out))


def rumble(dur, lo=40, hi=260, att=0.4, rel=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    sos = butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, nz)
    crackle = sosfilt(butter(2, [600, 3000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n) * (rng.random(n) < 0.02)) * 0.6
    y = y / (np.max(np.abs(y)) + 1e-9) + crackle
    env = np.clip(t / att, 0, 1) * np.clip((dur - t) / rel, 0, 1)
    y = y * env
    return y / (np.max(np.abs(y)) + 1e-9)


def clank(dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for f, d, g in ((180, 0.5, 1.0), (433, 0.35, 0.6), (911, 0.2, 0.4), (1530, 0.12, 0.25)):
        y += g * np.sin(2 * np.pi * f * t) * np.exp(-t / d)
    hit = rng.standard_normal(n) * np.exp(-t / 0.02)
    y = y + 0.8 * sosfilt(butter(2, 1800, "lowpass", fs=SR, output="sos"), hit)
    return y * np.clip(t / 0.002, 0, 1) / (np.max(np.abs(y)) + 1e-9)


def hiss(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sosfilt(butter(2, [900, 6000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    y *= (0.7 + 0.3 * np.sin(2 * np.pi * 3.1 * t)) * np.clip(t / 0.5, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)

def bubbles(dur, n=26):
    out = np.zeros(int(dur * SR))
    for _ in range(n):
        st = rng.uniform(0, dur - 0.1); f0 = rng.uniform(500, 1400); d = rng.uniform(0.03, 0.08)
        m = int(d * SR); tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * f0 * (1 + 2.5 * tt / d) * tt) * np.exp(-tt / (d / 3))
        i = int(st * SR); out[i:i + m] += y[:len(out) - i] * rng.uniform(0.3, 1)
    return out / (np.max(np.abs(out)) + 1e-9)


def sonar(freq=1250, dur=1.8):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.35) + 0.3 * np.sin(2 * np.pi * freq * 1.5 * t) * np.exp(-t / 0.2)
    echo = np.zeros(n); k = int(0.32 * SR); echo[k:] = y[:n - k] * 0.35
    return (y + echo) * np.clip(t / 0.005, 0, 1) / 1.4


sfx = np.zeros((N, 2))

def tick(freq=2400, dur=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.012)


def chime_ok():
    out = np.zeros(int(1.4 * SR))
    for i, f in enumerate((659.25, 987.77, 1318.5)):
        y = ding(f, 1.0); j = int(i * 0.09 * SR); out[j:j + len(y)] += y[:len(out) - j] * (0.8 - 0.15 * i)
    return out / np.max(np.abs(out))




def hum(dur, f=62.0, wob=0.6):
    """Zumbido magnético: tono grave con batido y armónicos que suben y bajan."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * (f * 2 + wob) * t) + 0.25 * np.sin(2 * np.pi * (f * 3.01) * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t))
    env = np.clip(t / 0.6, 0, 1) * np.clip((dur - t) / 0.8, 0, 1)
    return y * env / 1.8


def sparkle(dur, n=40):
    out = np.zeros(int(dur * SR))
    for _ in range(n):
        st = rng.uniform(0, dur - 0.1); f0 = rng.uniform(2500, 6000); d = rng.uniform(0.02, 0.06)
        m = int(d * SR); tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt / (d / 4))
        i = int(st * SR); out[i:i + m] += y[:len(out) - i] * rng.uniform(0.2, 1)
    return out / (np.max(np.abs(out)) + 1e-9)




PV, T_OFF = 2.0, 0.55
FLARE_T = SPLIT("llamaradas", 0.62)


def blip(freq=1500, dur=0.22):
    """Pulso de radio: tono corto con un poco de estática."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.05) + 0.5 * np.sin(2 * np.pi * freq * 1.5 * t) * np.exp(-t / 0.03)
    st = sosfilt(butter(2, [2000, 7000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-t / 0.08) * 0.4
    return (y + st) * np.clip(t / 0.003, 0, 1) / 1.6


def static(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sosfilt(butter(2, [1200, 5000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    y *= np.clip(t / 0.4, 0, 1) * np.clip((dur - t) / 0.6, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)


def pulses_in(a, b):
    out = []; k = math.ceil((a - T_OFF) / PV)
    while T_OFF + k * PV <= b:
        out.append(T_OFF + k * PV); k += 1
    return out


sfx = np.zeros((N, 2))
place(sfx, static(6.8), 0.0, 0.03)
# pulsos audibles solo donde el haz es protagonista (gancho, enana) y bajitos, para no tapar la voz
for tp in pulses_in(0.0, S0["distancia"] - 0.3):
    place(sfx, blip(1500), tp, 0.10, pan=0.15)
for tp in pulses_in(S0["distancia"], S1["distancia"]):
    place(sfx, blip(1100, 0.18), tp, 0.04, pan=0.4)
for tp in pulses_in(SPLIT("enana", 0.5), S1["enana"] + 0.4):
    place(sfx, blip(1500), tp, 0.09, pan=-0.15)
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.30)
place(sfx, whoosh(2.4, 100, 1800, 250), S0["distancia"] - 0.1, 0.10)          # viaje hasta la Tierra
place(sfx, ding(1318.5, 0.8), SPLIT("distancia", 0.45), 0.05, pan=-0.3)        # Australia
place(sfx, hum(6.5, 50, 0.6), S0["enana"] + 0.1, 0.07)                          # la enana de cerca
place(sfx, whoosh(3.0, 80, 1300, 200), S0["pareja"] + 0.2, 0.09)               # se aleja la cámara
place(sfx, chime_ok(), SPLIT("pareja", 0.5), 0.06)                              # primera vez
for i in range(12):                                                             # 12 puntitos
    place(sfx, tick(1600 + 60 * i, 0.05), S0["docena"] + 0.35 + 0.12 * i, 0.08, pan=-0.5 + i / 11)
place(sfx, hum(3.0, 41, 0.4), SPLIT("docena", 0.48) + 0.2, 0.06)               # enana roja
place(sfx, rumble(3.2, 30, 220, 0.05, 2.0), FLARE_T, 0.12)                       # llamarada
place(sfx, boom(2.0), FLARE_T - 0.02, 0.16)
place(sfx, sparkle(1.4, 25), FLARE_T + 0.1, 0.03)
place(sfx, tick(900, 0.08), S0["cierre"] + 0.8, 0.10)                            # tachado
place(sfx, hum(5.5, 46, 0.5), S0["cierre"] + 0.3, 0.05)
place(sfx, ding(1760.0, 0.8), CARD, 0.18)
music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
