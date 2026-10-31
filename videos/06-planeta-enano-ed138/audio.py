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
rng = np.random.default_rng(11)

P = lambda sid, k: SEG[sid]["parts"][k]
NOM0 = SEG["nombre"]["t0"]; TAM0 = SEG["tamano"]["t0"]; CLUB0 = SEG["club"]["t0"]; CLUB_P2 = P("club", 1)[0]
PRE0 = SEG["pregunta"]["t0"]; RUB0 = SEG["rubin"]["t0"]; RUB_P2 = P("rubin", 1)[0]
MIS0 = SEG["misterio"]["t0"]; CIE0 = SEG["cierre"]["t0"]
FL = [NOM0 - 0.2, TAM0 - 0.2, CLUB0 - 0.15, PRE0 - 0.25, RUB0 - 0.2, MIS0 - 0.2, END - 0.32]
NB = np.random.default_rng(9)
_ = [(NB.uniform(-5.0, 5.0), NB.uniform(-7.0, 4.0), NB.uniform(-40, -16)) for _ in range(16)]
NEIGH_T = np.sort(NB.uniform(CIE0 + 0.3, CIE0 + 3.2, 16))


def ring_times():
    return TM["rings"]


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
    # progresión original en La menor: Am - F - C - G (raíces en Hz)
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]]
    seg = 4.5
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
    # pulso suave a 96 BPM
    beat = 60 / 96
    for bt in np.arange(0, END, beat):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        k = np.sin(2 * np.pi * (55 + 60 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.09) * 0.35
        place(out, k, bt)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    out *= lfo[:, None]
    sos = butter(2, 2200, "lowpass", fs=SR, output="sos")
    out = sosfilt(sos, out, axis=0)
    return out / np.max(np.abs(out))


def tick(dur=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.008)
    return y / np.max(np.abs(y))


def ice(dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n) * (rng.random(n) < 0.15) * np.exp(-t / 0.12)
    sos = butter(2, [2500, 12000], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, nz) * 3 + np.sin(2 * np.pi * 3100 * t) * np.exp(-t / 0.2) * 0.3
    return y / (np.max(np.abs(y)) + 1e-9)


def alarm(dur=0.5, f=440.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * 1.5 * t) * 0.3
    sos = butter(2, 1800, "lowpass", fs=SR, output="sos")
    y = sosfilt(sos, y) * np.clip(t / 0.01, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)


def shutter():
    n = int(0.25 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    sos = butter(2, [1500, 7000], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, nz) * (np.exp(-t / 0.015) + 0.7 * np.exp(-np.maximum(t - 0.09, 0) / 0.02) * (t > 0.09))
    return y / (np.max(np.abs(y)) + 1e-9)


sfx = np.zeros((N, 2))
place(sfx, boom(2.0), 0.0, 0.30)
place(sfx, whoosh(2.4, 90, 1400, 200), 0.0, 0.30)
place(sfx, ding(1318.5, 1.2), 1.2, 0.22, pan=0.4)
place(sfx, ding(1760.0, 1.0), 2.4, 0.14, pan=0.4)
for tf in FL:
    place(sfx, zap(), tf - 0.06, 0.55)
for k, (dt, f) in enumerate([(0.1, 523.25), (0.5, 659.25), (1.2, 987.77)]):
    place(sfx, whoosh(0.8, 300, 2400, 500), NOM0 + dt, 0.15, pan=-0.4 + 0.4 * k)
    place(sfx, ding(f, 1.0), NOM0 + dt, 0.20, pan=-0.4 + 0.4 * k)
place(sfx, whoosh(1.6), TAM0 + 0.05, 0.35)
place(sfx, boom(1.4), TAM0 + 0.35, 0.30)
for i, f in enumerate([523.25, 587.33, 659.25, 783.99, 880.0]):
    place(sfx, ding(f, 0.8), CLUB0 + 0.3 + 0.45 * i, 0.18, pan=-0.6 + 0.3 * i)
place(sfx, ding(1046.5, 1.4), CLUB_P2, 0.26)
place(sfx, ding(1318.5, 1.4), CLUB_P2 + 0.06, 0.18)
place(sfx, boom(2.4), PRE0 - 0.2, 0.40)
place(sfx, whoosh(2.4, 90, 1600, 200), RUB0 - 0.2, 0.38)
place(sfx, ding(880.0, 0.9), RUB0 + 2.1, 0.22)
place(sfx, shutter(), RUB_P2 + 0.15, 0.45)
place(sfx, ding(1760.0, 0.7), RUB_P2 + 0.35, 0.14)
for k in range(3):
    place(sfx, whoosh(1.3, 120, 900, 150), MIS0 + 0.4 + 1.3 * k, 0.16, pan=-0.3 if k % 2 else 0.3)
place(sfx, ding(1046.5, 1.6), P("cierre", 1)[1] + 0.15, 0.22)
place(sfx, ding(1318.5, 1.6), P("cierre", 1)[1] + 0.2, 0.18)
place(sfx, ding(1568.0, 1.6), P("cierre", 1)[1] + 0.25, 0.14)
for k, tt in enumerate(NEIGH_T):
    place(sfx, ding(1000 + 90 * (k % 7), 0.6), tt, 0.10, pan=-0.7 + 0.09 * k)

music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
