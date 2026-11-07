"""Flash Datos · video 23 (neumáticos de F1): efectos y música originales sintetizados según timing.json."""
import json, math, os
import numpy as np
from scipy.signal import stft, istft, butter, sosfilt
from scipy.io import wavfile

BASE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
TM = json.load(open(os.path.join(BASE, "timing.json")))
SEG = {s["id"]: s for s in TM["segments"]}
PT = lambda i, k: SEG[i]["parts"][k]
END = TM["end"]
N = int(END * SR)
rng = np.random.default_rng(23)



def place(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    if sig.ndim == 1:
        sig = np.stack([sig * math.sqrt((1 - pan) / 2) * 1.414, sig * math.sqrt((1 + pan) / 2) * 1.414], -1)
    j = min(len(buf), i + len(sig)); s0 = max(0, -i)
    buf[max(i, 0):j] += sig[s0:j - i] * gain


def whoosh(dur, f0=180, f1=2400, f2=300):
    n = int(dur * SR)
    f, tt, Z = stft(rng.standard_normal(n + 2048), SR, nperseg=1024)
    tt = tt / dur; peak = 0.62
    fc = np.where(tt < peak, f0 * (f1 / f0) ** (tt / peak), f1 * (f2 / f1) ** ((tt - peak) / (1 - peak)))
    shape = np.exp(-((np.log(np.maximum(f, 20))[:, None] - np.log(fc)[None, :]) ** 2) / (2 * 0.55 ** 2))
    env = np.clip(tt / peak, 0, 1) ** 1.6 * np.clip((1 - tt) / (1 - peak), 0, 1) ** 1.2
    _, y = istft(Z * shape * env[None, :], SR, nperseg=1024)
    y = y[:n]; y /= np.max(np.abs(y)) + 1e-9
    pan = np.linspace(-0.6, 0.6, n)
    return np.stack([y * (1 - pan) * 0.8, np.roll(y, 240) * (1 + pan) * 0.8], -1)


def zap(dur=0.32):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 2600 * (180 / 2600) ** (t / dur)
    tone = np.tanh(3 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t / 0.10)
    crack = sosfilt(butter(2, [1500, 9000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n) * (rng.random(n) < 0.08) * np.exp(-t / 0.05)) * 3
    y = tone * 0.5 + crack * 0.6 + np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.12) * 0.6
    return y / (np.max(np.abs(y)) + 1e-9)


def boom(dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(30 + 40 * np.exp(-t / 0.25)) / SR) * np.exp(-t / 0.7)
    y = body + sosfilt(butter(2, 260, "lowpass", fs=SR, output="sos"), rng.standard_normal(n) * np.exp(-t / 0.3)) * 0.9
    return y * np.clip(t / 0.01, 0, 1) / (np.max(np.abs(y)) + 1e-9)


def ding(freq, dur=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.45) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t / 0.18)
         + 0.15 * np.sin(2 * np.pi * freq * 5.40 * t) * np.exp(-t / 0.08)) * np.clip(t / 0.004, 0, 1)
    return y / np.max(np.abs(y))


def tick(freq=2400, dur=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.012) + 0.3 * rng.standard_normal(n) * np.exp(-t / 0.004)
    return y / np.max(np.abs(y))


def clank(dur=0.35, base=520):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * base * r * t) * np.exp(-t / d) for a, r, d in [(1, 1, 0.09), (0.7, 2.31, 0.06), (0.5, 3.97, 0.04), (0.35, 5.6, 0.03)])
    y += 0.5 * rng.standard_normal(n) * np.exp(-t / 0.006)
    return y / np.max(np.abs(y))


def engine(dur, f_start, f_peak, f_end, peak_at=0.55, gain_env=None):
    """Motor de carreras sintetizado: tono con armónicos y rugosidad, con efecto Doppler."""
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    f = np.where(u < peak_at, f_start + (f_peak - f_start) * np.clip(u / peak_at, 0, 1) ** 1.5, f_peak + (f_end - f_peak) * np.clip((u - peak_at) / (1 - peak_at), 0, 1) ** 0.7)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum(np.sin(k * ph) / k ** 0.9 for k in range(1, 12))
    y = np.tanh(1.8 * y) + 0.15 * rng.standard_normal(n)
    y = sosfilt(butter(2, [80, 6000], "bandpass", fs=SR, output="sos"), y)
    env = gain_env(u) if gain_env else np.exp(-((u - peak_at) / 0.28) ** 2)
    y = y * env * np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.1, 0, 1)
    y /= np.max(np.abs(y)) + 1e-9
    pan = np.clip((u - peak_at) * 2.2, -0.9, 0.9)
    return np.stack([y * (1 - pan) * 0.75, y * (1 + pan) * 0.75], -1)


def music():
    t = np.arange(N) / SR
    # progresión original en La menor: Am - F - C - G, 110 bpm
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    bpm = 110; seg = 60 / bpm * 8
    out = np.zeros((N, 2))
    for ci in range(int(END / seg) + 2):
        notes = chords[ci % 4]; a = ci * seg; b = a + seg + 1.0
        i0 = int(a * SR); i1 = min(N, int(b * SR))
        if i0 >= N:
            break
        tt = t[i0:i1] - a
        env = np.clip(tt / 0.6, 0, 1) * np.clip((seg + 1.0 - tt) / 1.0, 0, 1)
        for fq in notes:
            for det, side in ((-0.12, 0), (0.12, 1)):
                f = fq * 2 ** (det / 12)
                out[i0:i1, side] += (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * env * 0.09
        out[i0:i1] += (np.sin(2 * np.pi * notes[0] / 2 * tt) * env * 0.22)[:, None]
        # arpegio brillante (corcheas)
        for k in range(16):
            ta = a + k * 30 / bpm
            if ta >= END: break
            fq = notes[[0, 1, 2, 1][k % 4]] * 2
            n = int(0.25 * SR); tq = np.arange(n) / SR
            place(out, np.sin(2 * np.pi * fq * tq) * np.exp(-tq / 0.09) * 0.07, ta, pan=0.4 if k % 2 else -0.4)
    beat = 60 / bpm
    for k, bt in enumerate(np.arange(0, END, beat)):
        n = int(0.22 * SR); tt = np.arange(n) / SR
        place(out, np.sin(2 * np.pi * (50 + 75 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.08) * 0.36, bt)
        if k % 2 == 1:
            hh = sosfilt(butter(2, 7500, "highpass", fs=SR, output="sos"), rng.standard_normal(int(0.05 * SR))) * np.exp(-np.arange(int(0.05 * SR)) / SR / 0.012) * 0.11
            place(out, hh, bt)
    out *= (0.9 + 0.1 * np.sin(2 * np.pi * 0.08 * t))[:, None]
    out = sosfilt(butter(2, 3400, "lowpass", fs=SR, output="sos"), out, axis=0)
    fade = np.clip((END - t) / 2.0, 0, 1)
    return out * fade[:, None] / np.max(np.abs(out))


def hum(dur, f=120):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) + 0.25 * np.sin(2 * np.pi * 3 * f * t)
    y *= 0.7 + 0.3 * np.sin(2 * np.pi * 4 * t)
    y *= np.clip(t / 0.3, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)
    return y / np.max(np.abs(y))


def rise(dur, f0=200, f1=900):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(t / 0.1, 0, 1) * np.clip((dur - t) / 0.2, 0, 1)
    return y * 0.8


def shutter():
    n = int(0.18 * SR); t = np.arange(n) / SR
    y = sosfilt(butter(2, [800, 6000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n)) * (np.exp(-t / 0.012) + 0.7 * np.exp(-np.clip(t - 0.07, 0, None) / 0.012) * (t > 0.07))
    return y / np.max(np.abs(y))


at = lambda p, f: p[0] + (p[1] - p[0]) * f
G0, G1 = SEG["gancho"]["parts"]; T0, T1 = SEG["tipos"]["parts"]
B0, B1, B2, B3, B4 = SEG["blandos"]["parts"]; M0, M1, M2, M3 = SEG["medios"]["parts"]; D0, D1, D2 = SEG["duros"]["parts"]
C0, C1, C2, C3 = SEG["compuestos"]["parts"]; E0, E1, E2 = SEG["estrategia"]["parts"]; F0, F1, F2, F3 = SEG["final"]["parts"]
FLASHES = [T0[0] - 0.3, B0[0] - 0.3, M0[0] - 0.3, D0[0] - 0.3, C0[0] - 0.3, E0[0] - 0.3, F0[0] - 0.3, F3[1] + 0.1]

sfx = np.zeros((N, 2))
# gancho: un auto pasa y se encienden las franjas
place(sfx, engine(2.6, 260, 620, 300), 0.15, 0.32)
for k, f in enumerate([0.6, 0.76, 0.9]):
    place(sfx, ding([1046.5, 1318.5, 1568.0][k], 0.8), at(G0, f), 0.2)
# carrera en el óvalo
place(sfx, engine(6.5, 300, 700, 420, 0.5, lambda u: 0.6 + 0.4 * np.sin(np.pi * u)), G1[0] - 0.2, 0.22)
place(sfx, ding(1760.0, 1.0), at(G1, 0.85), 0.22)
# destellos entre capítulos
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.5)
# tipos
for k in range(3):
    place(sfx, clank(0.3, 480 + 60 * k), T0[0] - 0.05 + k * 0.25, 0.2)
place(sfx, rise(1.6, 200, 800), T1[0] + 0.3, 0.05)
# presentación de cada neumático
for p in (B0, M0, D0):
    place(sfx, whoosh(1.0, 180, 2200, 300), p[0] - 0.3, 0.35)
    place(sfx, clank(0.35, 560), p[0] + 0.5, 0.25)
# blandos
place(sfx, rise(at(B1, 0.55) - B1[0], 160, 900), B1[0] + 0.2, 0.07)
for tt in np.arange(at(B1, 0.5), B1[1], 0.1):
    place(sfx, tick(2200, 0.04), tt, 0.06)
place(sfx, ding(1568.0, 0.9), B1[1] - 0.1, 0.2)
place(sfx, hum(at(B2, 0.45) - B2[0], 70), B2[0] + 0.3, 0.12)
place(sfx, boom(1.2), at(B2, 0.45), 0.25)
place(sfx, engine(2.4, 280, 640, 380), at(B2, 0.62), 0.2)
for k in range(10):
    place(sfx, tick(1500, 0.04), at(B3, 0.05 + 0.08 * k), 0.06)
place(sfx, ding(880.0, 1.0), at(B4, 0.12), 0.12); place(sfx, ding(988.0, 1.0), at(B4, 0.24), 0.12); place(sfx, ding(1318.5, 1.2), at(B4, 0.72), 0.22)
# medios
place(sfx, clank(0.4, 420), M1[0] + 0.1, 0.3)
place(sfx, whoosh(1.0, 200, 1500, 300), M2[0] + 0.1, 0.2)
place(sfx, clank(0.35, 600), at(M3, 0.55), 0.3)
# duros
place(sfx, hum(D1[1] - D1[0], 95), D1[0], 0.08)
for f in (0.15, 0.42, 0.62):
    place(sfx, rise(0.7, 300, 900), at(D1, f), 0.06)
place(sfx, rise(at(D2, 0.48) - D2[0], 120, 600), D2[0] + 0.2, 0.06)
place(sfx, ding(1318.5, 1.0), at(D2, 0.85), 0.18)
# compuestos
place(sfx, whoosh(1.4, 150, 2400, 300), at(C0, 0.5), 0.3)
for k in range(5):
    place(sfx, clank(0.25, 400 + 70 * k), at(C1, 0.28 + 0.075 * k), 0.18)
place(sfx, whoosh(0.8, 300, 1800, 500), at(C2, 0.5) - 0.4, 0.3); place(sfx, ding(1046.5, 0.9), at(C2, 0.5), 0.2)
place(sfx, whoosh(0.8, 300, 1800, 500), at(C2, 0.78) - 0.4, 0.3); place(sfx, ding(1568.0, 0.9), at(C2, 0.78), 0.2)
place(sfx, ding(1318.5, 1.0), C3[0], 0.18); place(sfx, ding(1760.0, 1.0), at(C3, 0.55), 0.18)
# estrategia
for tt in np.arange(E0[0], E0[1], 0.5):
    place(sfx, tick(2600, 0.03), tt, 0.04)
for f in (0.05, 0.2, 0.42, 0.55):
    place(sfx, clank(0.3, 650), at(E1, f), 0.2)
place(sfx, engine(2.0, 400, 300, 120, 0.3), at(E2, 0.5), 0.2)
for k in range(4):
    place(sfx, clank(0.2, 900), at(E2, 0.6) + 0.12 * k, 0.15)
place(sfx, engine(2.0, 150, 500, 650, 0.7), at(E2, 0.7), 0.2)
place(sfx, ding(1568.0, 1.0), at(E2, 0.4), 0.18)
# final
place(sfx, engine(2.5, 500, 760, 500), F0[0] + 0.1, 0.18)
place(sfx, rise(F1[1] - F1[0] - 1, 200, 700), F1[0] + 0.3, 0.05)
place(sfx, engine(4.0, 300, 700, 400, 0.6), F2[0] + 0.3, 0.15)
place(sfx, ding(1760.0, 1.2), at(F2, 0.8), 0.3)
place(sfx, boom(1.6), at(F3, 0.6), 0.2)
place(sfx, ding(1568.0, 1.2), FLASHES[7] + 0.1, 0.3)

mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
