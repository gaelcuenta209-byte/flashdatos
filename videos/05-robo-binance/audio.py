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
BIN0 = SEG["binance"]["t0"]; BIN_P2 = P("binance", 1)[0]
REC0 = SEG["record"]["t0"]; GIRO0 = SEG["giro"]["t0"]
COR0 = SEG["corea"]["t0"]; COR_P2 = P("corea", 1)[0]
CAR0 = SEG["carrera"]["t0"]; CIE0 = SEG["cierre"]["t0"]
FL = [BIN0 - 0.2, REC0 - 0.2, COR0 - 0.2, CAR0 - 0.2, END - 0.32]


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


sfx = np.zeros((N, 2))
place(sfx, boom(1.6), 0.0, 0.32)
# reloj que corre mientras desaparece el dinero
for k, tt in enumerate(np.arange(0.6, 6.2, 0.25)):
    place(sfx, tick(), tt, 0.10 + 0.08 * (k % 4 == 0), pan=0.25 if k % 2 else -0.25)
for tt in np.linspace(0.9, 5.8, 9):
    place(sfx, ding(1200 + 300 * rng.random(), 0.5), tt, 0.10, pan=rng.uniform(-0.7, 0.7))
place(sfx, whoosh(1.4, 200, 2600, 300), 3.4, 0.30)
place(sfx, boom(1.2), SEG["hook2"]["t0"] - 0.05, 0.30)
for tf in FL:
    place(sfx, zap(), tf - 0.06, 0.55)
place(sfx, whoosh(2.0), BIN0, 0.40)
for k in range(10):
    place(sfx, whoosh(0.9, 300, 3200, 600), BIN_P2 + 0.1 + 0.2 * k, 0.12, pan=-0.8 + 0.16 * k)
    place(sfx, ding(660 * 2 ** (k / 12), 0.5), BIN_P2 + 0.1 + 0.2 * k, 0.10, pan=-0.8 + 0.16 * k)
place(sfx, boom(2.0), REC0 + 0.5, 0.45)
place(sfx, ding(1318.5, 1.0), REC0 + 0.7, 0.20)
place(sfx, boom(2.6), GIRO0 + 0.05, 0.40)
place(sfx, whoosh(2.4, 90, 1200, 200), COR0, 0.40)
for k in range(5):
    place(sfx, alarm(0.35, 520 if k % 2 == 0 else 440), COR0 + 2.4 + 0.45 * k, 0.10)
for k in range(10):
    place(sfx, ding(900 + 80 * k, 0.4), COR_P2 + 0.3 + 0.38 * k, 0.07)
for k in range(8):
    place(sfx, ice(), CAR0 + 0.15 + 0.17 * k, 0.16, pan=rng.uniform(-0.6, 0.6))
place(sfx, whoosh(3.0, 120, 2400, 250), CIE0 + 0.4, 0.40)
for tt in np.arange(CIE0 + 0.6, END - 0.6, 0.25):
    place(sfx, tick(), tt, 0.09)

music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
