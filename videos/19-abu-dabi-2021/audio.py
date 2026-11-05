"""Flash Datos · video 19 (Abu Dabi 2021): efectos y música originales sintetizados según timing.json."""
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
rng = np.random.default_rng(19)

S = lambda i: SEG[i]["t0"]
E = lambda i: SEG[i]["t1"]
FLASHES = [S("empate") - 0.3, S("salida") - 0.3, S("checo") - 0.3, S("latifi") - 0.25, S("masi") - 0.3, S("ultima") - 0.25, S("final") - 0.3, E("final") + 0.15]


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
    seg = 60 / 124 * 8
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
    beat = 60 / 124
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




def beep(freq, dur=0.18):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + np.sin(2 * np.pi * freq * t) * 0.5
    y = sosfilt(butter(2, 4000, "lowpass", fs=SR, output="sos"), y)
    return y * np.clip(t / 0.005, 0, 1) * np.clip((dur - t) / 0.02, 0, 1)


def radio(dur=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sosfilt(butter(2, [900, 3200], "bandpass", fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-t / 0.12)
    return y / (np.max(np.abs(y)) + 1e-9)


def wrench(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sign(np.sin(2 * np.pi * 38 * t)) * sosfilt(butter(2, [1200, 6000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    y = y * np.clip(t / 0.01, 0, 1) * np.clip((dur - t) / 0.05, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)


def thump():
    n = int(0.35 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * (45 + 40 * np.exp(-t / 0.04)) * t) * np.exp(-t / 0.09)
    return y / np.max(np.abs(y))


def pass_by(t0, dur, f0, f1, f2, g, pan_dir=1):
    e = engine(dur, f0, f1, f2, 0.5)
    if pan_dir < 0:
        e = e[:, ::-1]
    place(sfx, e, t0, g)


sfx = np.zeros((N, 2))
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.5)

# gancho: dos autos y lo que está en juego
a, b = PT("gancho", 0)[:2]
place(sfx, boom(1.4), a, 0.32)
pass_by(a + 0.1, 2.2, 300, 1100, 800, 0.22)
pass_by(a + 0.4, 2.2, 320, 1000, 760, 0.18, -1)
place(sfx, ding(1318.5, 0.9), a + 1.6, 0.22)
place(sfx, ding(1568.0, 0.9), a + 3.3, 0.22)

# empate en puntos
a, b = PT("empate", 0)[:2]
place(sfx, whoosh(0.9, 300, 2600, 500), a, 0.28)
for i in range(10):
    place(sfx, tick(1800 + 60 * i, 0.05), a + 1.3 + i * 0.13, 0.22)
place(sfx, boom(1.0), a + 2.7, 0.28)
place(sfx, ding(1046.5, 0.9), a + 2.7, 0.22)

# salida: semáforo y arrancada
a, b = PT("salida", 0)[:2]
for i in range(5):
    place(sfx, beep(880, 0.07), a - 0.3 + i * 0.09, 0.12)
pass_by(a + 0.15, 3.4, 250, 1250, 1050, 0.34)
pass_by(a + 0.25, 3.3, 240, 1180, 1000, 0.28, -1)
place(sfx, ding(1318.5, 0.8), a + 1.9, 0.18)

# Checo defiende
a, b = PT("checo", 0)[:2]
c, d = PT("checo", 1)[:2]
place(sfx, engine(d - a + 0.6, 700, 760, 720, 0.5, lambda u: np.clip(u / 0.05, 0, 1) * np.clip((1 - u) / 0.05, 0, 1)), a - 0.3, 0.12)
period = 2 * np.pi / 2.2
k = 0
while a + 0.35 + k * period / 2 < c - 0.4:
    place(sfx, whoosh(0.6, 300, 2000, 400), a + 0.35 + k * period / 2, 0.14)
    k += 1
for i in range(8):
    place(sfx, tick(1500 - 50 * i, 0.05), a + 5.6 + i * 0.4, 0.18)
place(sfx, radio(0.35), c - 0.25, 0.25)
place(sfx, beep(1400, 0.12), c - 0.2, 0.08)
place(sfx, ding(1568.0, 1.0), c + 0.2, 0.25)

# Hamilton se escapa
a, b = PT("escape", 0)[:2]
pass_by(a, 2.5, 500, 1100, 900, 0.16)
for i in range(9):
    place(sfx, tick(1200 + 80 * i, 0.05), a + 0.5 + i * 0.45, 0.16)
place(sfx, ding(880.0, 0.9), b - 1.0, 0.2)

# Latifi choca y sale el auto de seguridad
a, b = PT("latifi", 0)[:2]
place(sfx, engine(0.9, 900, 600, 200, 0.2), a - 0.3, 0.25)
place(sfx, boom(1.6), a + 0.5, 0.45)
place(sfx, clank(0.5, 260), a + 0.52, 0.3)
place(sfx, clank(0.4, 380), a + 0.62, 0.2)
for i in range(6):
    place(sfx, beep(740 if i % 2 else 980, 0.16), a + 1.6 + i * 0.22, 0.09)

# llantas: Max entra a pits
a, b = PT("llantas", 0)[:2]
place(sfx, whoosh(0.8, 300, 2400, 500), a, 0.25)
for i in range(4):
    place(sfx, wrench(0.32), a + 0.6 + i * 0.36, 0.14, pan=-0.5)
mid = a + (b - a) * 0.42
place(sfx, ding(1046.5, 0.8), mid + 0.6, 0.2)

# Masi: mensajes de dirección de carrera
a, b = PT("masi", 0)[:2]
m2 = a + 5.1
place(sfx, engine(b - a + 0.5, 420, 450, 430, 0.5, lambda u: np.clip(u / 0.05, 0, 1) * np.clip((1 - u) / 0.05, 0, 1)), a - 0.3, 0.08)
place(sfx, beep(330, 0.25), a + 2.2, 0.14)
place(sfx, beep(330, 0.25), a + 2.5, 0.14)
place(sfx, ding(1318.5, 0.8), m2 - 0.1, 0.22)
place(sfx, ding(1568.0, 0.8), m2 + 0.05, 0.16)
for i in range(5):
    pass_by(m2 + 0.6 + i * 0.25, 1.4, 400, 950, 700, 0.1, 1 if i % 2 else -1)

# última vuelta: latido
a, b = PT("ultima", 0)[:2]
for i in range(5):
    place(sfx, thump(), a - 0.2 + i * 0.6, 0.4)
    place(sfx, thump(), a - 0.2 + i * 0.6 + 0.16, 0.25)
place(sfx, boom(1.2), a + 0.35, 0.3)
place(sfx, ding(1568.0, 0.9), a + 0.9, 0.22)

# el rebase
a, b = PT("rebase", 0)[:2]
t5 = a + (b - a) * 0.22; ps = a + (b - a) * 0.42; att = a + (b - a) * 0.62
pass_by(a - 0.2, b - a + 0.8, 500, 1300, 1150, 0.3)
pass_by(a - 0.1, b - a + 0.8, 480, 1250, 1100, 0.24, -1)
place(sfx, boom(1.2), ps, 0.32)
place(sfx, whoosh(1.0, 300, 2800, 500), att, 0.3)
place(sfx, ding(880.0, 0.9), b - 0.5, 0.22)

# final: informe, resultado, campeón y Checo
a, b = PT("final", 0)[:2]
c, d = PT("final", 1)[:2]
place(sfx, clank(0.45, 220), a + 1.0, 0.35)
place(sfx, boom(1.0), a + 1.0, 0.25)
place(sfx, ding(1046.5, 0.8), a + 3.1, 0.2)
champ = a + 5.2
for k, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]):
    place(sfx, ding(f, 1.4), champ - 0.1 + k * 0.08, 0.16)
place(sfx, boom(1.4), champ - 0.1, 0.3)
place(sfx, whoosh(1.0, 300, 2600, 500), c - 0.4, 0.3)
pass_by(c - 0.2, 2.2, 300, 1100, 800, 0.18)
place(sfx, ding(1318.5, 1.0), c + 1.1, 0.24)
place(sfx, ding(1568.0, 1.2), FLASHES[-1] + 0.1, 0.3)

mus = music()
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (mus * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s", "pico sfx", float(np.max(np.abs(sfx))))
