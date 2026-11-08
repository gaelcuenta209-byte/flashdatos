"""Flash Datos · video 24 (Rosberg y los 80 gramos del casco): efectos y música originales sintetizados según timing.json."""
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
rng = np.random.default_rng(24)



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
P = lambda i: SEG[i]["parts"]
G0, G1 = P("gancho"); O0, O1, O2 = P("objetivo"); K0, K1, K2, K3 = P("casco"); L0, L1 = P("calculo")
B0, B1, B2 = P("cuerpo"); M0, M1 = P("mente"); R0, R1 = P("rivalidad"); S0, S1, S2, S3 = P("temporada")
A0, A1, A2 = P("abudabi"); X0, X1 = P("retiro"); F0, = P("final")
FLASHES = [O0[0] - 0.3, K0[0] - 0.3, L0[0] - 0.3, B0[0] - 0.3, M0[0] - 0.3, R0[0] - 0.3, S0[0] - 0.3, A0[0] - 0.3, X0[0] - 0.3, F0[0] - 0.3, F0[1] + 0.15]


def scrape(dur):
    """Pintura que se raspa: ruido filtrado con textura granular."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = sosfilt(butter(2, [1200, 7000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    y *= (0.5 + 0.5 * (rng.random(n) < 0.3)) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t) ** 2)
    y *= np.clip(t / 0.1, 0, 1) * np.clip((dur - t) / 0.3, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)


def crowd(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sosfilt(butter(2, [300, 3000], "bandpass", fs=SR, output="sos"), rng.standard_normal((n, 2)), axis=0)
    y *= (np.clip(t / 0.4, 0, 1) * np.clip((dur - t) / 1.2, 0, 1))[:, None]
    return y / (np.max(np.abs(y)) + 1e-9)


sfx = np.zeros((N, 2))
# gancho: casco que aparece y la pintura que empieza a ceder
place(sfx, whoosh(1.0, 180, 2200, 300), 0.0, 0.35)
place(sfx, clank(0.4, 520), 0.45, 0.25)
place(sfx, ding(1318.5, 0.9), G1[0] + 0.2, 0.18)
place(sfx, scrape(1.6), at(G1, 0.6), 0.12)
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.5)
# mismo auto: dos motores
place(sfx, engine(2.6, 260, 620, 300), O0[0] + 0.1, 0.25)
place(sfx, engine(2.6, 280, 640, 320), O0[0] + 0.4, 0.2)
place(sfx, ding(1046.5, 0.8), at(O1, 0.32), 0.18)
# búsqueda
for k in range(6):
    place(sfx, tick(2000 + 150 * k, 0.05), O2[0] + 0.3 + 0.3 * k, 0.12)
place(sfx, whoosh(1.0, 200, 1800, 300), at(O2, 0.58) - 0.3, 0.3)
place(sfx, ding(1568.0, 1.0), at(O2, 0.58) + 0.2, 0.2)
# pelado del casco
place(sfx, scrape(K1[0] + 2.0 - K0[0] - 0.3), K0[0] + 0.3, 0.2)
place(sfx, ding(1318.5, 1.0), at(K1, 0.5), 0.18)
# báscula
for k in range(12):
    place(sfx, tick(1800, 0.04), at(K2, 0.55) + k * 0.07, 0.07)
place(sfx, ding(1760.0, 1.1), at(K2, 0.82), 0.25)
place(sfx, boom(1.2), at(K3, 0.55), 0.22)
# cronómetro
for tt in np.arange(L0[0], at(L0, 0.55), 0.5):
    place(sfx, tick(2600, 0.03), tt, 0.08)
place(sfx, clank(0.4, 700), at(L0, 0.55), 0.25)
for k in range(14):
    place(sfx, tick(2400 + 80 * (k % 4), 0.04), L1[0] + 0.3 + k * 0.3, 0.06)
place(sfx, ding(1568.0, 1.0), L1[1] - 0.5, 0.2)
# obsesión
for k in range(3):
    place(sfx, clank(0.3, 480 + 80 * k), B0[0] + 0.3 + k * 0.35, 0.2)
place(sfx, whoosh(0.8, 300, 1600, 400), at(B1, 0.22), 0.3)
place(sfx, boom(1.0), at(B1, 0.6), 0.25)
place(sfx, clank(0.35, 900), at(B2, 0.42), 0.3)
place(sfx, engine(1.8, 200, 700, 500, 0.4), at(B2, 0.7), 0.2)
# mente
place(sfx, hum(M0[1] - M0[0], 110), M0[0], 0.06)
place(sfx, ding(880.0, 1.4), at(M0, 0.42), 0.15); place(sfx, ding(1174.7, 1.4), at(M0, 0.7), 0.15)
place(sfx, whoosh(0.6, 400, 2400, 800), M1[0] + 0.4, 0.3)
place(sfx, clank(0.3, 400), M1[0] + 0.8, 0.35)
# rivalidad
place(sfx, whoosh(1.0, 160, 1800, 300), R0[0] - 0.2, 0.3)
place(sfx, boom(1.4), R0[0] + 0.6, 0.25)
place(sfx, ding(1318.5, 1.0), R1[0] + 0.3, 0.18); place(sfx, ding(1568.0, 1.0), R1[0] + 0.9, 0.18)
# temporada 2016
for k in range(4):
    place(sfx, ding([1046.5, 1174.7, 1318.5, 1568.0][k], 0.8), at(S0, 0.18) + k * 0.45, 0.18)
place(sfx, rise(2.0, 200, 900), at(S0, 0.55), 0.06)
place(sfx, engine(3.0, 300, 700, 420), S1[0] + 0.2, 0.2)
for k in range(5):
    place(sfx, clank(0.25, 600 + 60 * k), at(S3, [0.0, 0.12, 0.32, 0.5, 0.62][k]), 0.2)
place(sfx, boom(1.2), at(S3, 0.8), 0.2)
# Abu Dabi
place(sfx, whoosh(1.4, 150, 2400, 300), A0[0] - 0.2, 0.3)
place(sfx, rise(2.0, 200, 800), at(A1, 0.32), 0.06)
place(sfx, engine(5.0, 300, 720, 420, 0.5, lambda u: 0.6 + 0.4 * np.sin(np.pi * u)), A2[0], 0.22)
place(sfx, crowd(5.0), at(A2, 0.6), 0.12)
place(sfx, boom(1.6), at(A2, 0.6), 0.25)
place(sfx, ding(1760.0, 1.4), at(A2, 0.6) + 0.1, 0.3)
# retiro
place(sfx, boom(1.4), at(X0, 0.55), 0.3)
place(sfx, clank(0.4, 380), X1[0] + 0.2, 0.25)
place(sfx, ding(1568.0, 1.2), at(X1, 0.74), 0.28)
# final
place(sfx, rise(F0[1] - F0[0] - 1.0, 180, 700), F0[0] + 0.3, 0.05)
place(sfx, ding(1568.0, 1.2), FLASHES[10] + 0.1, 0.3)

mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
