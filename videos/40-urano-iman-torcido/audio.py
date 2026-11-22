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
rng = np.random.default_rng(40)
# video 40: tiempos iguales a escena.py
S0 = {k: v["t0"] for k, v in SEG.items()}
S1 = {k: v["t1"] for k, v in SEG.items()}
SPLIT = lambda k, f: S0[k] + (S1[k] - S0[k]) * f
ORDER = ["gancho", "oposicion", "acostado", "iman", "tierra", "agua", "resultado", "cierre"]
FLASHES = [S0[k] - 0.22 for k in ORDER[1:]]
CARD = S1["cierre"] + 0.25

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
    # progresión original en Mi menor: Em - C - G - D (raíces en Hz), más tensa y espacial
    chords = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [174.61, 220.0, 261.63], [130.81, 164.81, 196.0]]
    seg = 4.3
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
    # pulso suave a 92 BPM
    beat = 60 / 84
    for bt in np.arange(0, END, beat):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        k = np.sin(2 * np.pi * (55 + 60 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.09) * 0.35
        place(out, k, bt)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    out *= lfo[:, None]
    sos = butter(2, 2200, "lowpass", fs=SR, output="sos")
    out = sosfilt(sos, out, axis=0)
    return out / np.max(np.abs(out))


def rumble(dur, lo=40, hi=260, att=0.4, rel=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    sos = butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, nz)
    crackle = sosfilt(butter(2, [600, 3000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n) * (rng.random(n) < 0.02)) * 0.6
    y = y / (np.max(np.abs(y)) + 1e-9) + crackle
    env = np.clip(t / att, 0, 1) * np.clip((dur - t) / rel, 0, 1)
    y = y * env
    return y / (np.max(np.abs(y)) + 1e-9)


def clank(dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for f, d, g in ((180, 0.5, 1.0), (433, 0.35, 0.6), (911, 0.2, 0.4), (1530, 0.12, 0.25)):
        y += g * np.sin(2 * np.pi * f * t) * np.exp(-t / d)
    hit = rng.standard_normal(n) * np.exp(-t / 0.02)
    y = y + 0.8 * sosfilt(butter(2, 1800, "lowpass", fs=SR, output="sos"), hit)
    return y * np.clip(t / 0.002, 0, 1) / (np.max(np.abs(y)) + 1e-9)


def hiss(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sosfilt(butter(2, [900, 6000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    y *= (0.7 + 0.3 * np.sin(2 * np.pi * 3.1 * t)) * np.clip(t / 0.5, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)

def bubbles(dur, n=26):
    out = np.zeros(int(dur * SR))
    for _ in range(n):
        st = rng.uniform(0, dur - 0.1); f0 = rng.uniform(500, 1400); d = rng.uniform(0.03, 0.08)
        m = int(d * SR); tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * f0 * (1 + 2.5 * tt / d) * tt) * np.exp(-tt / (d / 3))
        i = int(st * SR); out[i:i + m] += y[:len(out) - i] * rng.uniform(0.3, 1)
    return out / (np.max(np.abs(out)) + 1e-9)


def sonar(freq=1250, dur=1.8):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.35) + 0.3 * np.sin(2 * np.pi * freq * 1.5 * t) * np.exp(-t / 0.2)
    echo = np.zeros(n); k = int(0.32 * SR); echo[k:] = y[:n - k] * 0.35
    return (y + echo) * np.clip(t / 0.005, 0, 1) / 1.4


sfx = np.zeros((N, 2))

def tick(freq=2400, dur=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.012)


def chime_ok():
    out = np.zeros(int(1.4 * SR))
    for i, f in enumerate((659.25, 987.77, 1318.5)):
        y = ding(f, 1.0); j = int(i * 0.09 * SR); out[j:j + len(y)] += y[:len(out) - j] * (0.8 - 0.15 * i)
    return out / np.max(np.abs(out))




def hum(dur, f=62.0, wob=0.6):
    """Zumbido magnético: tono grave con batido y armónicos que suben y bajan."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * (f * 2 + wob) * t) + 0.25 * np.sin(2 * np.pi * (f * 3.01) * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t))
    env = np.clip(t / 0.6, 0, 1) * np.clip((dur - t) / 0.8, 0, 1)
    return y * env / 1.8


def sparkle(dur, n=40):
    out = np.zeros(int(dur * SR))
    for _ in range(n):
        st = rng.uniform(0, dur - 0.1); f0 = rng.uniform(2500, 6000); d = rng.uniform(0.02, 0.06)
        m = int(d * SR); tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt / (d / 4))
        i = int(st * SR); out[i:i + m] += y[:len(out) - i] * rng.uniform(0.2, 1)
    return out / (np.max(np.abs(out)) + 1e-9)


sfx = np.zeros((N, 2))
place(sfx, whoosh(2.6, 80, 1300, 180), 0.1, 0.15)
place(sfx, rumble(5.0, 30, 120, 1.0, 1.5), 0.0, 0.08)
place(sfx, hum(3.0, 58, 0.7), S0["gancho"] + 3.0, 0.10)                         # aparece el campo torcido
for tf in FLASHES:
    place(sfx, zap(), tf - 0.06, 0.34)
place(sfx, ding(1318.5, 0.9), S0["oposicion"] + 0.15, 0.07, pan=0.2)            # calendario 25 nov
place(sfx, whoosh(3.0, 100, 900, 200), S0["oposicion"] + 0.3, 0.10)            # la Tierra se alinea
place(sfx, chime_ok(), S0["oposicion"] + 3.3, 0.08)                             # Sol, Tierra y Urano en línea
place(sfx, whoosh(2.0, 120, 1600, 260), S0["acostado"] + 0.3, 0.10)
place(sfx, ding(987.77, 0.8), S0["acostado"] + 1.2, 0.06, pan=-0.2)             # 97°
place(sfx, hum(6.2, 55, 1.1), S0["iman"] + 0.1, 0.11)                           # líneas de campo
place(sfx, ding(880.0, 0.8), S0["iman"] + 1.6, 0.06, pan=0.25)                  # 59°
place(sfx, sonar(740.0, 1.4), S0["iman"] + 3.4, 0.06, pan=-0.2)                 # ni siquiera está centrado
place(sfx, ding(1174.66, 0.7), S0["tierra"] + 0.3, 0.06, pan=-0.4)              # Tierra 11°
place(sfx, ding(1396.91, 0.7), S0["tierra"] + 1.7, 0.06, pan=0.4)               # Neptuno 47°
place(sfx, rumble(8.4, 40, 220, 0.6, 1.5), S0["agua"] + 0.1, 0.05)              # presión enorme
place(sfx, sparkle(6.0, 50), S0["agua"] + 2.2, 0.035)                           # iones
place(sfx, hum(5.0, 70, 1.6), S0["agua"] + 3.0, 0.06)
place(sfx, whoosh(4.0, 90, 1300, 200), S0["resultado"] - 0.05, 0.12)            # pasa la Voyager 2
place(sfx, chime_ok(), S0["resultado"] + 1.0, 0.07)
place(sfx, hiss(5.0), S0["cierre"] + 0.3, 0.02)                                 # cielo nocturno
place(sfx, ding(1975.53, 1.0), S0["cierre"] + 1.2, 0.05, pan=0.3)               # marcador de Urano
place(sfx, ding(1760.0, 0.8), CARD, 0.18)
music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
