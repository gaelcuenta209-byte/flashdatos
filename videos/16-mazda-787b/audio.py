"""Flash Datos · video 16 (Mazda 787B, respuesta a @_nachozn_): efectos y música originales sintetizados según timing.json."""
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
rng = np.random.default_rng(16)

S = lambda i: SEG[i]["t0"]
E = lambda i: SEG[i]["t1"]
FLASHES = [S("motor") - 0.3, S("pbujias") - 0.3, S("chasis") - 0.3, S("pilotos") - 0.3, S("final") - 0.3, E("final") + 0.15]
PARTS = ["pbujias", "padmision", "ppuertos", "psellos", "psonido"]


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
    chords = [[110.0, 130.81, 164.81], [87.31, 110.0, 130.81], [130.81, 164.81, 196.0], [98.0, 123.47, 146.83]]
    seg = 60 / 112 * 8
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
    beat = 60 / 112
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
# gancho: respuesta, foto del 787B y "sin pistones"
a, b = PT("dato", 0)[:2]
place(sfx, ding(1318.5, 0.8), a + 0.05, 0.22)
place(sfx, whoosh(0.9, 300, 2600, 500), a + 0.15, 0.3)
place(sfx, engine(3.0, 300, 900, 700, 0.6), a + 1.0, 0.18)
place(sfx, boom(1.0), a + 3.6, 0.3)
place(sfx, ding(1046.5, 0.8), a + 5.4, 0.2)
c, d = PT("dato", 1)[:2]
place(sfx, boom(1.2), c, 0.32)
place(sfx, ding(1568.0, 1.0), c + 2.4, 0.22)
# destellos
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.5)
# el motor: 4 rotores que entran
a = PT("motor", 0)[0]
for i in range(4):
    place(sfx, clank(0.3, 420 + 60 * i), a + 1.2 + i * 0.35, 0.18, pan=-0.6 + i * 0.4)
place(sfx, ding(1174.7, 0.8), a + 3.0, 0.2)
# pistón contra rotor
a, b = PT("rotor", 0)[:2]
place(sfx, whoosh(1.0, 250, 2400, 400), a + 2.3, 0.3)
place(sfx, clank(0.4, 300), a + 3.0, 0.25)
c = PT("rotor", 1)[0]
for i in range(4):
    place(sfx, tick(1500 + 250 * i, 0.08), c + 0.9 + i * 0.9, 0.3)
e = PT("rotor", 2)[0]
place(sfx, ding(1318.5, 0.9), e + 0.4, 0.22)
# R26B: 4 x 654 cc, RX-7 y tacómetro
a = PT("r26b", 0)[0]
for i in range(4):
    place(sfx, tick(1800 + 200 * i, 0.07), a + 0.6 + i * 0.4, 0.3)
place(sfx, ding(1046.5, 0.8), a + 5.0, 0.22)
c, d = PT("r26b", 1)[:2]
place(sfx, engine(3.6, 180, 1100, 1050, 0.8, lambda u: np.clip(u / 0.15, 0, 1) * np.clip((1 - u) / 0.15, 0, 1)), c + 0.2, 0.32)
place(sfx, whoosh(1.2, 120, 2400, 300), d - 1.6, 0.35)
for i in range(5):
    place(sfx, clank(0.3, 430 + 40 * i), d - 1.2 + i * 0.05, 0.12, pan=-0.5 + i / 4)
# desarmado
for k, sid in enumerate(PARTS):
    place(sfx, whoosh(0.9, 250, 2800, 400), S(sid) - 0.55, 0.3)
    place(sfx, ding([1046.5, 1174.7, 1318.5, 1396.9, 1568.0][k], 0.7), S(sid) - 0.05, 0.12)
a = S("pbujias")
for i in range(10):
    place(sfx, zap(0.12), a + 0.6 + i * 0.3, 0.06)
place(sfx, ding(880.0, 0.8), a + 1.2, 0.18)
place(sfx, whoosh(2.5, 200, 900, 200), S("padmision") + 1.5, 0.18)
place(sfx, whoosh(1.4, 400, 3000, 600), S("ppuertos") + 0.8, 0.22)
place(sfx, ding(1318.5, 0.8), S("ppuertos") + 2.5, 0.18)
place(sfx, boom(0.9), S("psellos") + 2.0, 0.25)
# el grito del rotativo
a, b = PT("psonido", 0)[:2]
place(sfx, engine(4.6, 400, 1500, 1350, 0.55, lambda u: np.clip(u / 0.1, 0, 1) * np.clip((1 - u) / 0.12, 0, 1)), a + 0.4, 0.42)
# chasis: barras de peso
a = S("chasis")
place(sfx, whoosh(1.2, 200, 2000, 400), a + 2.0, 0.25)
place(sfx, clank(0.45, 300), a + 3.6, 0.28)
# pilotos
a = S("pilotos")
for i in range(3):
    place(sfx, tick(1600 + 300 * i, 0.08), a + 0.5 + i * 0.9, 0.3)
c, d = PT("pilotos", 1)[:2]
place(sfx, ding(1046.5, 0.8), c + 0.6, 0.2)
place(sfx, engine(4.0, 300, 700, 650, 0.5, lambda u: 0.5 + 0.5 * np.sin(np.pi * u)), c + 2.5, 0.14)
# carrera
a, b = PT("carrera", 0)[:2]
place(sfx, engine(2.6, 500, 260, 120, 0.15), a + 1.6, 0.25)
place(sfx, boom(1.2), a + 2.3, 0.32)
place(sfx, engine(4.0, 600, 1400, 1100, 0.7), a + 2.8, 0.35)
place(sfx, ding(1568.0, 1.0), a + 0.7 * (b - 0.2 - a - 3.4) + a + 3.4, 0.25)
c, d = PT("carrera", 1)[:2]
place(sfx, engine(3.0, 1300, 1400, 600, 0.3), c, 0.3)
place(sfx, boom(1.2), c + 2.0, 0.28)
place(sfx, ding(880.0, 0.9), c + 2.6, 0.2)
# final
a = S("final")
place(sfx, boom(1.0), a + 2.2, 0.3)
place(sfx, clank(0.4, 260), a + 2.4, 0.25)
c = PT("final", 1)[0]
place(sfx, whoosh(1.0, 300, 2600, 500), c - 0.4, 0.3)
place(sfx, engine(4.0, 600, 1500, 1300, 0.6), c + 0.8, 0.22)
place(sfx, ding(1318.5, 1.0), c + 4.2, 0.25)
place(sfx, ding(1568.0, 1.2), FLASHES[-1] + 0.1, 0.3)

mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
