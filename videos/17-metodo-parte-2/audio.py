"""Video 17 (El método, parte 2: la voz). Efectos de sonido y música de fondo originales, sintetizados para la línea de tiempo del video."""
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
rng = np.random.default_rng(17)

IN0 = SEG["investiga"]["t0"]; GU0, GU1 = SEG["guion"]["t0"], SEG["guion"]["t1"]
VO0 = SEG["voz"]["t0"]; TO0 = SEG["tomas"]["t0"]
GH0, GH1 = SEG["github"]["t0"], SEG["github"]["t1"]; PS0 = SEG["pausas"]["t0"]
CI1 = SEG["cierre"]["t1"]; CIA = SEG["cierre"]["parts"][0]; CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
FL = [IN0 - 0.15, VO0 - 0.15, GH0 - 0.15, CIB[0] - 0.15, CARD - 0.05]

def wtime(seg, idx):
    sg = SEG[seg]; words = sg["say"].split()
    wts = [len(w) + 1 + (3 if w[-1] in ".,:…?" else 0) for w in words]
    return sg["t0"] + (sg["t1"] - sg["t0"]) * sum(wts[:idx]) / sum(wts)


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
    # progresión original en Re menor: Dm - Bb - F - C (raíces en Hz)
    chords = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [174.61, 220.0, 261.63], [130.81, 164.81, 196.0]]
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
    # pulso suave a 100 BPM
    beat = 60 / 100
    for bt in np.arange(0, END, beat):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        k = np.sin(2 * np.pi * (55 + 60 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.09) * 0.35
        place(out, k, bt)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    out *= lfo[:, None]
    sos = butter(2, 2200, "lowpass", fs=SR, output="sos")
    out = sosfilt(sos, out, axis=0)
    return out / np.max(np.abs(out))



def click(dur=0.035):
    n = int(dur * SR); t = np.arange(n) / SR
    y = rng.standard_normal(n) * np.exp(-t / 0.006)
    sos = butter(2, [1800, 7000], "bandpass", fs=SR, output="sos")
    y = sosfilt(sos, y)
    return y / (np.max(np.abs(y)) + 1e-9)


def buzz(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.6 + np.sin(2 * np.pi * 165 * t) * 0.4
    sos = butter(2, 1800, "lowpass", fs=SR, output="sos")
    y = sosfilt(sos, y) * np.exp(-t / 0.22) * np.clip(t / 0.005, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)




def blip(freq, dur=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t * (1 + 0.6 * t / dur)) * np.exp(-t / 0.04) * np.clip(t / 0.003, 0, 1)
    return y / (np.max(np.abs(y)) + 1e-9)


sfx = np.zeros((N, 2))
place(sfx, whoosh(2.4, 140, 3000, 500), 0.0, 0.5)
place(sfx, boom(1.6), 0.0, 0.30)
for tf in FL:
    place(sfx, zap(), tf - 0.06, 0.55)
place(sfx, boom(), VO0 - 0.1, 0.30)
# fuentes verificadas: NASA, ESA, universidades
for i, idx in enumerate((17, 19, 21)):
    place(sfx, ding([783.99, 987.77, 1174.66][i], 0.9), wtime("investiga", idx) - 0.1, 0.22, pan=-0.3 + 0.3 * i)
place(sfx, ding(1567.98, 1.0), wtime("investiga", 12), 0.12)
# tecleo del guion
for tk in np.arange(GU0 + 0.1, GU1 - 0.3, 0.08):
    if rng.random() < 0.8:
        place(sfx, click(), tk + 0.02 * rng.random(), 0.14, pan=rng.uniform(-0.3, 0.3))
place(sfx, ding(1046.5, 0.8), wtime("guion", 5), 0.18)
place(sfx, ding(1318.51, 0.8), wtime("guion", 12), 0.18)
# las dos tomas y la elegida
place(sfx, blip(660), TO0, 0.25, -0.4)
place(sfx, blip(660), TO0 + 0.25, 0.25, 0.4)
for fq in (523.25, 659.25, 783.99):
    place(sfx, ding(fq, 1.3), wtime("tomas", 5), 0.13, -0.3)
# el audio viaja por la acción de GitHub
for k, tk in enumerate(np.arange(GH0 + 0.2, GH1, 0.22)):
    place(sfx, blip(900 + 120 * (k % 4), 0.08), tk, 0.12, pan=-0.6 + 1.2 * ((tk - GH0) / (GH1 - GH0)))
place(sfx, whoosh(1.0, 300, 2600, 600), wtime("github", 5) - 0.3, 0.25)
# marcas de pausa en la línea de tiempo
segs = TM["segments"]
for i, (a, b) in enumerate(zip(segs, segs[1:])):
    place(sfx, click(0.05), PS0 + 1.3 + 0.06 * i, 0.22, pan=-0.5 + i * 0.15)
place(sfx, ding(1174.66, 1.0), PS0 + 2.2, 0.16)
place(sfx, ding(880.0, 1.2), CIA[0] + 0.5 * (CIA[1] - CIA[0]), 0.18)
place(sfx, whoosh(1.6, 150, 2400, 300), CIB[0] - 0.3, 0.35)

music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
