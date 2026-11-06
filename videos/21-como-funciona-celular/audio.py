"""Flash Datos · video 21 (cómo funciona un celular): efectos y música originales sintetizados según timing.json."""
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
rng = np.random.default_rng(21)



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
G0, G1 = PT("gancho", 0), PT("gancho", 1)
B0, B1, C0, C1 = PT("bateria", 0), PT("bateria", 1), PT("chip", 0), PT("chip", 1)
S0, S1, K0, K1 = PT("pantalla", 0), PT("pantalla", 1), PT("camaras", 0), PT("camaras", 1)
Q0, Q1, F0, F1 = PT("carga", 0), PT("carga", 1), PT("final", 0), PT("final", 1)
FLASHES = [G1[0] - 0.25, B0[0] - 0.3, C0[0] - 0.15, S0[0] - 0.3, K0[0] - 0.3, Q0[0] - 0.3, F0[0] - 0.3, F1[1] + 0.1]
UNF0, UNF1, EXP0 = G1[0] + 0.7, G1[0] + 2.0, G1[0] + 2.4

sfx = np.zeros((N, 2))
# gancho: interruptores que se prenden y apagan
for i, tt in enumerate(np.arange(0.3, G0[1], 1 / 9)):
    place(sfx, tick(1600 + 500 * ((i * 7) % 3), 0.05), tt, 0.13 * (1 - 0.6 * tt / G0[1]), pan=((i * 5) % 7 - 3) / 4)
place(sfx, whoosh(3.5, 2400, 300, 150), 1.6, 0.35)
place(sfx, ding(1318.5, 0.9), G0[1] - 1.5, 0.22)
# destellos
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.5)
# se abre y se desarma
place(sfx, whoosh(1.4, 200, 1800, 300), UNF0, 0.4)
place(sfx, clank(0.3, 700), UNF1 - 0.05, 0.3)
place(sfx, whoosh(1.6, 120, 2600, 300), EXP0, 0.45)
for i in range(7):
    place(sfx, clank(0.3, 420 + 45 * i), EXP0 + 0.9 + i * 0.08, 0.13, pan=-0.6 + i / 5)
# capítulos
for k, p in enumerate([B0, C0, S0, K0, Q0]):
    place(sfx, ding([1046.5, 1174.7, 1318.5, 1568.0, 1760.0][k], 0.8), p[0] + 0.05, 0.16)
# batería
place(sfx, hum(at(B1, 0.58) - B1[0], 110), B1[0] + 0.1, 0.10)
place(sfx, rise(B1[1] - at(B1, 0.6), 180, 700), at(B1, 0.6), 0.06)
# chip: el transistor cambia 2.4 veces por segundo
for tt in np.arange(np.ceil(C1[0] * 2.4) / 2.4, C1[1], 1 / 2.4):
    place(sfx, tick(2400, 0.05), tt, 0.16)
place(sfx, whoosh(0.9, 300, 2600, 500), C0[0] + 1.3, 0.3)
# pantallas
place(sfx, whoosh(1.3, 200, 1800, 300), at(S0, 0.52), 0.38)
place(sfx, clank(0.3, 760), at(S0, 0.52) + 1.3, 0.25)
place(sfx, whoosh(0.8, 300, 2200, 400), at(S1, 0.56), 0.3)
# cámaras
place(sfx, shutter(), at(K0, 0.2), 0.45)
place(sfx, shutter(), at(K0, 0.26), 0.35)
for i, tt in enumerate(np.arange(at(K0, 0.42), at(K0, 0.7), 0.09)):
    place(sfx, tick(2000 + 30 * i, 0.04), tt, 0.08)
place(sfx, whoosh(1.2, 250, 2000, 300), K1[0] + 0.4, 0.3)
place(sfx, ding(1568.0, 0.8), at(K1, 0.55), 0.2)
# carga
place(sfx, clank(0.35, 520), at(Q0, 0.3), 0.4)
place(sfx, rise(Q0[1] - at(Q0, 0.45), 220, 880), at(Q0, 0.45), 0.08)
place(sfx, hum(Q1[1] - Q1[0], 90), Q1[0] + 0.1, 0.09)
place(sfx, ding(1760.0, 0.9), at(Q1, 0.72), 0.2)
# final
place(sfx, whoosh(1.2, 150, 2000, 300), F1[0] + 0.3, 0.35)
place(sfx, ding(1568.0, 1.2), FLASHES[7] + 0.1, 0.3)

mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
