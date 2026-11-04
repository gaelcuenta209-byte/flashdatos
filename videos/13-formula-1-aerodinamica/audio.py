"""Flash Datos · video 13 (Fórmula 1): efectos y música originales sintetizados según timing.json."""
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
rng = np.random.default_rng(13)

FLASHES = [SEG["leyendas"]["t0"] - 0.35, SEG["secreto"]["t0"] - 0.3, PT("secreto", 2)[0] - 0.15, 142.65, SEG["final"]["t1"] + 0.1]
D0 = PT("secreto", 2)[0] - 0.15
EX0 = D0 + 1.35
RE0 = SEG["final"]["t0"] + 0.05
FOC = ["alerondel", "halo", "pontones", "motor", "piso", "difusor", "alerontras", "llantas"]


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
    # progresión original en Re menor: Dm - Bb - F - C
    chords = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [174.61, 220.0, 261.63], [130.81, 164.81, 196.0]]
    seg = 60 / 104 * 8
    out = np.zeros((N, 2))
    for ci in range(int(END / seg) + 2):
        notes = chords[ci % 4]; a = ci * seg; b = a + seg + 1.2
        i0 = int(a * SR); i1 = min(N, int(b * SR))
        if i0 >= N:
            break
        tt = t[i0:i1] - a
        env = np.clip(tt / 0.8, 0, 1) * np.clip((seg + 1.2 - tt) / 1.2, 0, 1)
        for fq in notes:
            for det, side in ((-0.15, 0), (0.15, 1)):
                f = fq * 2 ** (det / 12)
                out[i0:i1, side] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env * 0.11
        out[i0:i1] += (np.sin(2 * np.pi * notes[0] / 2 * tt) * env * 0.25)[:, None]
    beat = 60 / 104
    for k, bt in enumerate(np.arange(0, END, beat)):
        n = int(0.22 * SR); tt = np.arange(n) / SR
        place(out, np.sin(2 * np.pi * (52 + 70 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.08) * 0.38, bt)
        if k % 2 == 1:
            hh = sosfilt(butter(2, 7000, "highpass", fs=SR, output="sos"), rng.standard_normal(int(0.05 * SR))) * np.exp(-np.arange(int(0.05 * SR)) / SR / 0.012) * 0.12
            place(out, hh, bt)
    out *= (0.88 + 0.12 * np.sin(2 * np.pi * 0.1 * t))[:, None]
    out = sosfilt(butter(2, 3200, "lowpass", fs=SR, output="sos"), out, axis=0)
    fade = np.clip((END - t) / 2.0, 0, 1)
    return out * fade[:, None] / np.max(np.abs(out))


sfx = np.zeros((N, 2))
# dato extra: auto que pasa, giro del túnel y golpe
place(sfx, engine(2.6, 170, 430, 250, 0.45), 0.0, 0.55)
place(sfx, whoosh(2.2, 110, 2200, 300), 3.0, 0.5)
place(sfx, boom(1.4), 5.0, 0.35)
a = PT("dato", 1)[0]
place(sfx, engine(3.6, 120, 470, 440, 0.85, lambda u: np.clip(u / 0.2, 0, 1) * np.clip((1 - u) / 0.15, 0, 1) * 0.9 + 0.1), a + 0.1, 0.42)
place(sfx, ding(1318.5, 0.9), a + 3.2, 0.3)
# destellos
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.5)
# leyendas
i0 = PT("leyendas", 0)[0]
for i in range(4):
    place(sfx, tick(1800 + i * 300, 0.08), i0 - 0.2 + i * 0.22, 0.35)
for k, (wins, a) in enumerate([(None, PT("leyendas", 1)[0]), (15, PT("leyendas", 2)[0]), (15, PT("leyendas", 3)[0]), (21, PT("leyendas", 4)[0])]):
    place(sfx, whoosh(0.8, 300, 3000, 500), a - 0.35, 0.35)
    if wins:
        for i in range(wins):
            place(sfx, tick(2000 + 40 * i, 0.05), a + 0.7 + i * 0.13, 0.12)
    else:
        place(sfx, ding(1046.5, 0.8), a + 0.8, 0.25)
place(sfx, boom(1.0), PT("leyendas", 4)[0] + 0.75 + 21 * 0.13, 0.3)
# el secreto
a0 = PT("secreto", 0)[0]
place(sfx, whoosh(1.3, 150, 1800, 250), a0 + 2.8, 0.4)
place(sfx, whoosh(0.9, 400, 2600, 600), PT("secreto", 1)[0] - 0.2, 0.3)
place(sfx, whoosh(0.9, 400, 2600, 600), PT("secreto", 1)[0] + 2.0, 0.3)
# desarmado: cada pieza cae en su celda
place(sfx, whoosh(1.5, 120, 2600, 300), EX0 - 0.1, 0.5)
for i in range(12):
    place(sfx, clank(0.3, 420 + 37 * i), EX0 + i * 0.07 + 0.92, 0.16, pan=-0.5 + i / 11)
for k, sid in enumerate(FOC):
    place(sfx, whoosh(0.9, 250, 2800, 400), SEG[sid]["t0"] - 0.55, 0.32)
    place(sfx, ding([1046.5, 1174.7, 1318.5, 1396.9, 1568.0, 1760.0, 1975.5, 2093.0][k], 0.7), SEG[sid]["t0"] - 0.05, 0.12)
place(sfx, boom(1.2), SEG["halo"]["t0"] + 1.9, 0.45)
place(sfx, engine(4.0, 140, 360, 330, 0.5, lambda u: 0.5 + 0.5 * np.sin(np.pi * u)), SEG["motor"]["t0"] + 0.8, 0.18)
# armado otra vez y final
place(sfx, whoosh(1.4, 120, 2400, 300), RE0 + 0.4, 0.45)
for i in range(12):
    place(sfx, clank(0.3, 640 - 25 * i), RE0 + 1.32 + i * 0.06, 0.13, pan=0.5 - i / 11)
place(sfx, whoosh(1.0, 200, 2200, 300), PT("final", 1)[0] - 0.5, 0.35)
place(sfx, engine(5.5, 200, 400, 300, 0.5), PT("final", 1)[0] + 0.3, 0.28)
place(sfx, ding(1568.0, 1.2), FLASHES[4] + 0.1, 0.3)

mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
