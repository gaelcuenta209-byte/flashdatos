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

S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
ORDER = ["hook1", "lanzamiento", "orden", "gemma", "svalbard", "poema", "plan", "cierre"]
FL = [S0[k] - 0.2 for k in ORDER[1:]]
CARD = S1["cierre"] + 0.15
SPLIT = lambda k, f: S0[k] + (S1[k] - S0[k]) * f


def rumble(dur, gain_curve=None):
    """Retumbo de plasma: ruido grave filtrado con crepitar."""
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    sos = butter(2, 180, "lowpass", fs=SR, output="sos")
    low = sosfilt(sos, nz) * 4
    cr = rng.standard_normal(n) * (rng.random(n) < 0.01)
    sos2 = butter(2, [900, 5000], "bandpass", fs=SR, output="sos")
    cr = sosfilt(sos2, cr) * 2.5
    env = np.clip(t / 0.6, 0, 1) * np.clip((dur - t) / 0.8, 0, 1)
    y = (low + cr) * env
    return y / (np.max(np.abs(y)) + 1e-9)


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
    # progresión original en Mi menor: Em - C - G - D (raíces en Hz)
    chords = [[164.81, 196.0, 246.94], [130.81, 164.81, 196.0], [196.0, 246.94, 293.66], [146.83, 185.0, 220.0]]
    seg = 5.0
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
    # pulso suave a 84 BPM
    beat = 60 / 92
    for bt in np.arange(0, END, beat):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        k = np.sin(2 * np.pi * (55 + 60 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.09) * 0.35
        place(out, k, bt)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    out *= lfo[:, None]
    sos = butter(2, 2200, "lowpass", fs=SR, output="sos")
    out = sosfilt(sos, out, axis=0)
    return out / np.max(np.abs(out))


def tick(dur=0.03):
    """Tecla: clic corto filtrado."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = rng.standard_normal(n) * np.exp(-t / 0.006)
    sos = butter(2, [1500, 6000], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, y)
    return y / (np.max(np.abs(y)) + 1e-9)


def blip(f0, f1, dur=0.12):
    """Pulso de datos: seno con barrido corto."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 + (f1 - f0) * t / dur
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.35)) * np.clip(t / 0.005, 0, 1)
    return y


def hum(dur, f=110.0):
    """Zumbido del láser entre satélites."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2.01 * f * t) + 0.25 * np.sin(2 * np.pi * 3.02 * f * t))
    env = np.clip(t / 0.3, 0, 1) * np.clip((dur - t) / 0.5, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 6 * t))
    return y * env / 1.75


TPL3 = SPLIT("plan", 0.66)
sfx = np.zeros((N, 2))
place(sfx, whoosh(2.4, 120, 1800, 300), 0.0, 0.30)
place(sfx, ding(1318.51, 1.0), 1.0, 0.18)
for tf in FL + [TPL3 - 0.2]:
    place(sfx, zap(), tf - 0.06, 0.45)
tsl = SPLIT("lanzamiento", 0.50)
place(sfx, boom(1.4), FL[0] + 0.8, 0.18)                               # separación de la etapa
place(sfx, whoosh(1.8, 200, 2200, 400), FL[0] + 0.9, 0.22)
for i in range(6):
    place(sfx, blip(900 + 120 * i, 1400 + 120 * i, 0.09), tsl + 0.25 + 0.12 * i, 0.10, pan=-0.3 + 0.12 * i)   # el chip se enciende
text = "escribe un haiku sobre estar en el espacio"
for i, ch in enumerate(text):                                          # se teclea la orden
    if ch != " ":
        place(sfx, tick(), FL[1] + 0.3 + 2.2 * i / len(text), 0.10, pan=0.2 * math.sin(i))
tb = SPLIT("orden", 0.25)
for i in range(10):
    place(sfx, blip(600, 1200, 0.12), tb + 0.35 * i, 0.045)              # pulsos de subida
for i in range(8):
    place(sfx, blip(700 + 90 * (i % 4), 1100 + 90 * (i % 4), 0.08), FL[2] + 0.4 + 0.4 * i, 0.04, pan=0.3 * math.sin(i))   # pensando
for i in range(9):
    place(sfx, blip(1400, 700, 0.12), SPLIT("svalbard", 0.35) + 0.3 * i, 0.045)   # pulsos de bajada
for f_, fr in zip([0.14, 0.40, 0.66, 0.78], [659.25, 783.99, 987.77, 1174.66]):
    place(sfx, ding(fr, 1.2), SPLIT("poema", f_), 0.06)                 # cada verso
place(sfx, whoosh(2.2, 90, 1200, 200), SPLIT("plan", 0.36), 0.09)       # constelación
place(sfx, hum(S1["plan"] - TPL3 - 0.3, 110.0), TPL3 + 0.5, 0.05)       # láser 2027
place(sfx, ding(1760.0, 0.9), CARD, 0.25)


music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
