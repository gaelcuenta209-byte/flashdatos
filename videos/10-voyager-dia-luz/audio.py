"""Efectos de sonido y música de fondo originales, sintetizados para la línea de tiempo del video 10 (Voyager 1)."""
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
rng = np.random.default_rng(10)

HK1 = SEG["hook1"]["t1"]
VO0 = SEG["voyager"]["t0"]; VO_P2 = SEG["voyager"]["parts"][1][0]
VE0 = SEG["velocidad"]["t0"]; DL0 = SEG["dialuz"]["t0"]
LU0 = SEG["luz"]["t0"]; LU1 = SEG["luz"]["t1"]
RE0 = SEG["respuesta"]["t0"]; RE1 = SEG["respuesta"]["t1"]
SI0 = SEG["silencio"]["t0"]; SI1 = SEG["silencio"]["t1"]; SI_BACK = SI0 + (SI1 - SI0) * 0.60
DI0 = SEG["disco"]["t0"]; CI0 = SEG["cierre"]["t0"]
CARD = SEG["cierre"]["t1"] + 0.15
FL = [VO0 - 0.2, VE0 - 0.2, DL0 - 0.2, SI0 - 0.2, DI0 - 0.2, CI0 - 0.2]


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
    # progresión original en Re menor (raíces en Hz)
    chords = [[293.66, 349.23, 440.0], [233.08, 293.66, 349.23], [349.23, 440.0, 523.25], [261.63, 329.63, 392.0]]  # Rem - Sib - Fa - Do
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




def beep(freq=1400, dur=0.09):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.clip(t / 0.005, 0, 1) * np.clip((dur - t) / 0.01, 0, 1)
    return y


def static(dur):
    n = int(dur * SR)
    nz = rng.standard_normal(n)
    sos = butter(2, [800, 5000], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, nz) * (0.6 + 0.4 * (rng.random(n) < 0.3))
    return y / (np.max(np.abs(y)) + 1e-9)


def riser(dur, f0, f1):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.clip(t / 0.3, 0, 1) * np.clip((dur - t) / 0.15, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)


sfx = np.zeros((N, 2))
place(sfx, riser(HK1 - 0.4, 300, 1400), 0.4, 0.10)               # pulso de luz del gancho
place(sfx, whoosh(HK1 - 0.4, 120, 2400, 600), 0.4, 0.25)
for tf in FL:
    place(sfx, zap(), tf - 0.06, 0.5)
place(sfx, ding(659.25), VO_P2, 0.22)                           # 1977
place(sfx, whoosh(1.6, 300, 4800, 900), VE0 - 0.3, 0.45)        # velocidad
place(sfx, whoosh(3.4, 80, 900, 120), DL0 - 0.1, 0.35)          # el mapa se aleja
place(sfx, ding(880.0), DL0 + 3.2, 0.18)                        # aparece la Voyager
place(sfx, riser(LU1 - LU0, 400, 1600), LU0 - 0.1, 0.09)        # la luz viaja
place(sfx, ding(1318.51, 0.9), LU1 - 0.25, 0.25)                # llega en 24 h
half = (RE1 - RE0 - 0.2) / 2
place(sfx, riser(half, 400, 1600), RE0 - 0.15, 0.08)
place(sfx, ding(1318.51, 0.6), RE0 - 0.15 + half, 0.18)
place(sfx, riser(half, 1600, 400), RE0 - 0.15 + half, 0.08)
place(sfx, ding(783.99, 0.9), RE1 - 0.3, 0.25)                  # respuesta de regreso
st = static(SI_BACK - SI0 + 0.3)
st *= np.linspace(1, 0, len(st)) ** 2
place(sfx, st, SI0 - 0.1, 0.07)                                  # se apaga la señal
for k in range(3):
    place(sfx, beep(1400 if k < 2 else 1870), SI_BACK + 0.05 + k * 0.17, 0.18)
for k, fq in enumerate([523.25, 659.25, 783.99, 1046.5]):        # brillo del disco de oro
    place(sfx, ding(fq, 1.2), DI0 + 0.1 + k * 0.22, 0.12, pan=-0.4 + 0.27 * k)
place(sfx, whoosh(3.0, 600, 200, 80), CI0, 0.25)                # la nave se aleja
place(sfx, ding(1760.0, 0.9), CARD, 0.25)

music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
