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
H1 = SEG["hook1"]; H2 = SEG["hook2"]
COR0 = SEG["cornell"]["t0"]; CIU0 = SEG["ciudades"]["t0"]; CIU_P2 = P("ciudades", 1)[0]
MX0 = SEG["mx" if "mx" in SEG else "cdmx"]["t0"]; HUI0 = SEG["huir"]["t0"]; OTT0 = SEG["ottawa"]["t0"]
HON0 = SEG["hongo"]["t0"]; CIE0 = SEG["cierre"]["t0"]; CIE_P2 = P("cierre", 1)[0]
FL = [COR0 - 0.2, CIU_P2 - 0.15, MX0 - 0.2, HUI0 - 0.2, OTT0 - 0.2, HON0 - 0.2, CIE0 - 0.2, CIE_P2 - 0.15]
BREAK = OTT0 + 2.2


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
    """Ambiente de terror original: zumbido grave disonante, latido y cuerdas tensas (sintetizado)."""
    t = np.arange(N) / SR
    out = np.zeros((N, 2))
    for f, g in ((41.2, 0.5), (43.65, 0.35), (61.7, 0.25), (87.3, 0.12)):   # Mi y Fa graves: semitono disonante
        for side, det in ((0, -0.3), (1, 0.3)):
            ff = f * 2 ** (det / 12)
            saw = 2 * ((t * ff) % 1.0) - 1
            out[:, side] += saw * g
    sos = butter(2, 220, "lowpass", fs=SR, output="sos")
    out = sosfilt(sos, out, axis=0)
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t) ** 2
    out *= swell[:, None]
    # cuerdas tensas agudas que crecen en los momentos de tensión
    tens = np.zeros(N)
    for a0, b0 in ((COR0, CIU_P2 + 3.0), (OTT0, HON0 + 7.0)):
        i0, i1 = int(a0 * SR), min(N, int(b0 * SR))
        env = np.linspace(0, 1, i1 - i0) ** 2
        tens[i0:i1] = env
    hi = (np.sin(2 * np.pi * 1318.5 * t + 3 * np.sin(2 * np.pi * 5.5 * t)) + np.sin(2 * np.pi * 1396.9 * t)) * 0.08 * tens
    out += hi[:, None]
    # latido que se acelera
    tt = 0.3
    while tt < END - 3.5:
        calm = tt > CIE_P2 - 0.2
        bpm = 58 if (tt < COR0 or calm) else (84 if tt < HUI0 else 104 if tt < CIE0 else 70)
        for dt, gain in ((0.0, 1.0), (0.24, 0.7)):
            n = int(0.25 * SR); x = np.arange(n) / SR
            k = np.sin(2 * np.pi * (48 + 30 * np.exp(-x / 0.02)) * x) * np.exp(-x / 0.08) * gain * (0.5 if calm else 1.0)
            place(out, k, tt + dt)
        tt += 60 / bpm
    return out / np.max(np.abs(out))


def growl(dur=1.4, f0=70):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (1 + 0.15 * np.sin(2 * np.pi * 6 * t)) * (1 + 0.3 * rng.standard_normal(n).cumsum() / np.sqrt(np.arange(1, n + 1)) * 0.02)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.tanh(4 * np.sin(ph)) + 0.6 * rng.standard_normal(n)
    sos = butter(2, [180, 900], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, y) * np.clip(t / 0.15, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)


def sting(dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * t) for f in (311.1, 329.6, 466.2, 493.9)) * np.exp(-t / 0.5)
    y += rng.standard_normal(n) * np.exp(-t / 0.05) * 0.8
    return y / np.max(np.abs(y))


def hiss(dur=2.0):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    sos = butter(2, [4000, 12000], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, nz) * np.sin(np.pi * t / dur)
    return y / (np.max(np.abs(y)) + 1e-9)


def tick(dur=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.008)
    return y / np.max(np.abs(y))


sfx = np.zeros((N, 2))
for k, tt in enumerate(np.arange(0.4, H2["t0"] - 0.2, 1.0)):            # reloj de la madrugada
    place(sfx, tick(), tt, 0.16, pan=-0.2 if k % 2 else 0.2)
place(sfx, whoosh(2.4, 60, 600, 80), 1.0, 0.25)                         # viento
place(sfx, sting(), H2["t0"] - 0.05, 0.40)                               # paciente cero
place(sfx, boom(2.6), H2["t0"] - 0.05, 0.45)
place(sfx, growl(1.6, 65), H2["t0"] + 0.4, 0.30, pan=0.3)
for tf in FL:
    place(sfx, zap(), tf - 0.06, 0.45)
for k in range(10):                                                       # contagio que se expande
    place(sfx, growl(0.9, 60 + 8 * k), COR0 + 0.4 + 0.75 * k, 0.12, pan=rng.uniform(-0.8, 0.8))
place(sfx, boom(2.0), CIU0 + 0.05, 0.38)
place(sfx, sting(1.6), CIU_P2, 0.25)
place(sfx, whoosh(2.2, 90, 1400, 200), MX0 - 0.2, 0.35)
place(sfx, boom(2.4), MX0 + 1.6, 0.35)
for k in range(14):                                                       # pasos de la huida
    place(sfx, boom(0.25), HUI0 + 0.2 + 0.32 * k, 0.12, pan=-0.2 if k % 2 else 0.2)
for k in range(5):
    place(sfx, growl(1.2, 55 + 10 * k), HUI0 + 0.5 + 1.1 * k, 0.16, pan=rng.uniform(-0.6, 0.6))
place(sfx, boom(2.6), BREAK, 0.45)                                        # se rompe la cuarentena
place(sfx, sting(), BREAK + 0.02, 0.30)
place(sfx, growl(2.0, 58), BREAK + 0.3, 0.30)
place(sfx, hiss(3.5), HON0 + 2.0, 0.18)                                   # esporas
place(sfx, hiss(3.0), HON0 + 4.5, 0.14)
place(sfx, ding(392.0, 1.6), CIE0 + 0.4, 0.18)                            # el calor gana
place(sfx, ding(523.25, 1.6), CIE0 + 1.0, 0.16)
place(sfx, ding(659.25, 2.0), CIE_P2, 0.18)                               # calma
for f, d0 in ((1046.5, 0.15), (1318.5, 0.2), (1568.0, 0.25)):
    place(sfx, ding(f, 1.6), P("cierre", 1)[1] + d0, 0.18)

music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
