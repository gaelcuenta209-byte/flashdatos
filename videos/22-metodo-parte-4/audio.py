"""Efectos de sonido y música originales del video 22 (El método, parte 4), sintetizados según timing.json."""
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
rng = np.random.default_rng(22)

HK0 = SEG["hook"]["t0"]; RE0 = SEG["repo"]["t0"]
NU0 = SEG["nube"]["t0"]; AC0 = SEG["acciones"]["t0"]; VO0 = SEG["voz"]["t0"]
ME0 = SEG["medios"]["t0"]; MT0 = SEG["metricool"]["t0"]
CI1 = SEG["cierre"]["t1"]; CIA = SEG["cierre"]["parts"][0]; CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
GH_T = HK0 + 2.45
FL = [NU0 - 0.18, AC0 - 0.18, CIA[0] - 0.18, CIB[0] - 0.15, CARD - 0.05]
FILE_T = [RE0 + 1.75, RE0 + 4.0, RE0 + 5.25, RE0 + 7.35]


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


def click(dur=0.035):
    n = int(dur * SR); t = np.arange(n) / SR
    y = rng.standard_normal(n) * np.exp(-t / 0.006)
    sos = butter(2, [1800, 7000], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, y)
    return y / (np.max(np.abs(y)) + 1e-9)


def buzz(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.6 + np.sin(2 * np.pi * 165 * t) * 0.4
    sos = butter(2, 1800, "lowpass", fs=SR, output="sos")
    y = sosfilt(sos, y) * np.exp(-t / 0.22) * np.clip(t / 0.005, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)




def blip(freq, dur=0.18):
    n = int(dur * SR); t = np.arange(n) / SR
    f = freq * (1 + 0.5 * np.exp(-t / 0.02))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * np.clip(t / 0.003, 0, 1)
    return y / np.max(np.abs(y))


def gear_ticks(dur=1.2, rate=11):
    out = np.zeros(int(dur * SR))
    for k, tk in enumerate(np.arange(0, dur, 1 / rate)):
        c = click(0.03) * (0.7 + 0.3 * (k % 2))
        i = int(tk * SR); j = min(len(out), i + len(c)); out[i:j] += c[:j - i]
    return out / (np.max(np.abs(out)) + 1e-9)


def music():
    t = np.arange(N) / SR
    # progresión original en Re menor: Dm - Bb - F - C, arpegio a 100 BPM
    chords = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [174.61, 220.0, 261.63], [130.81, 164.81, 196.0]]
    beat = 60 / 100
    bar = 4 * beat
    out = np.zeros((N, 2))
    for ci in range(int(END / bar) + 2):
        notes = chords[ci % 4]
        a = ci * bar
        i0 = int(a * SR); i1 = min(N, int((a + bar + 1.0) * SR))
        if i0 >= N:
            break
        tt = t[i0:i1] - a
        env = np.clip(tt / 0.6, 0, 1) * np.clip((bar + 1.0 - tt) / 1.0, 0, 1)
        for fq in notes:
            for det, side in ((-0.12, 0), (0.12, 1)):
                f = fq * 2 ** (det / 12)
                out[i0:i1, side] += (np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(4 * np.pi * f * tt)) * env * 0.09
        out[i0:i1] += (np.sin(2 * np.pi * notes[0] / 2 * tt) * env * 0.22)[:, None]
        # arpegio en corcheas, una octava arriba
        seq = [notes[0], notes[1], notes[2], notes[1] * 2 / 2 * 2, notes[2], notes[1], notes[0] * 2, notes[2]]
        for k, fq in enumerate(seq):
            st = a + k * beat / 2
            n = int(0.28 * SR); ts = np.arange(n) / SR
            y = np.sin(2 * np.pi * fq * 2 * ts) * np.exp(-ts / 0.09) * np.clip(ts / 0.004, 0, 1)
            place(out, y * 0.20, st, pan=-0.35 if k % 2 else 0.35)
    for bt in np.arange(0, END, beat):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        k = np.sin(2 * np.pi * (52 + 70 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.08) * 0.35
        place(out, k, bt)
    for bt in np.arange(beat / 2, END, beat):
        hh = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR / 0.01)
        sos = butter(2, 7000, "highpass", fs=SR, output="sos")
        place(out, sosfilt(sos, hh) * 0.08, bt)
    lfo = 0.88 + 0.12 * np.sin(2 * np.pi * 0.1 * t)
    out *= lfo[:, None]
    sos = butter(2, 3000, "lowpass", fs=SR, output="sos")
    out = sosfilt(sos, out, axis=0)
    return out / np.max(np.abs(out))


sfx = np.zeros((N, 2))
place(sfx, whoosh(2.8, 110, 2600, 380), 0.0, 0.55)
place(sfx, boom(1.6), 0.0, 0.30)
place(sfx, buzz(), 1.45, 0.28)
place(sfx, boom(), GH_T - 0.05, 0.33)
for i, tf in enumerate(FILE_T):
    place(sfx, ding([659.25, 783.99, 880.0, 1046.5][i], 0.9), tf, 0.22, pan=-0.45 + 0.3 * i)
for tf in FL:
    place(sfx, zap(), tf - 0.06, 0.55)
place(sfx, whoosh(2.0, 80, 1400, 200), NU0 - 0.1, 0.40)
place(sfx, gear_ticks(1.4, 12), AC0 + 0.2, 0.12, pan=-0.2)
for i in range(2):
    place(sfx, blip(880 + 220 * i), AC0 + 0.6 + 0.9 * i, 0.22, pan=-0.5 + i)
for k in range(3):
    place(sfx, blip(660 + 110 * k, 0.14), VO0 + 0.5 * k, 0.15)
place(sfx, whoosh(1.0, 300, 2600, 800), VO0 + 1.3, 0.22)
for k in range(3):
    place(sfx, blip(523.25 + 130 * k, 0.14), ME0 + 0.6 * k, 0.15)
place(sfx, whoosh(1.1, 300, 2600, 800), ME0 + 0.9, 0.22)
place(sfx, ding(1318.51, 0.8), ME0 + 1.6, 0.18)
place(sfx, ding(987.77, 0.8), MT0 + 0.35, 0.18)
for i in range(3):
    place(sfx, ding([784.0, 987.77, 1174.66][i], 0.8), MT0 + 1.0 + 0.3 * i, 0.18, pan=-0.5 + 0.5 * i)
t0 = CIA[0] + 1.2; dt = (CIA[1] - CIA[0] - 1.4) / 6
for i in range(6):
    place(sfx, blip(523.25 * 2 ** (i / 6), 0.16), t0 + dt * i, 0.17)
place(sfx, whoosh(1.6, 150, 2400, 300), CIB[0] - 0.3, 0.35)
span = CIB[1] - CIB[0]
for j in range(4):
    place(sfx, ding([523.25, 659.25, 783.99, 1046.5][j], 1.0), CIB[0] + 0.6 + j * 0.22 * span, 0.15)

mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
