"""Video 20 (El método, parte 3: la animación 3D y el sonido). Efectos de sonido y música de fondo originales, sintetizados para la línea de tiempo del video."""
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
rng = np.random.default_rng(20)

MO0 = SEG["motor"]["t0"]; RA0, RA1 = SEG["rayos"]["t0"], SEG["rayos"]["t1"]
TX0 = SEG["texturas"]["t0"]; ES0, ES1 = SEG["escena"]["t0"], SEG["escena"]["t1"]
SO0 = SEG["sonido"]["t0"]; MZ0, MZ1 = SEG["mezcla"]["t0"], SEG["mezcla"]["t1"]
CI1 = SEG["cierre"]["t1"]; CIA = SEG["cierre"]["parts"][0]; CIB = SEG["cierre"]["parts"][1]
CARD = CI1 + 0.3
FL = [MO0 - 0.15, TX0 - 0.15, ES0 - 0.15, SO0 - 0.15, CIA[0] - 0.15, CIB[0] - 0.15, CARD - 0.05]

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
    """Música original: arpegio en La menor (Am - F - C - G) a 108 BPM, distinta a la de las partes 1 y 2."""
    t = np.arange(N) / SR
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    beat = 60 / 108
    out = np.zeros((N, 2))
    bar = 4 * beat
    for ci in range(int(END / bar) + 2):
        notes = chords[ci % 4]
        a = ci * bar
        i0 = int(a * SR); i1 = min(N, int((a + bar + 1.0) * SR))
        if i0 >= N:
            break
        tt = t[i0:i1] - a
        env = np.clip(tt / 0.8, 0, 1) * np.clip((bar + 1.0 - tt) / 1.0, 0, 1)
        for fq in notes:
            for det, side in ((-0.1, 0), (0.1, 1)):
                f = fq / 2 * 2 ** (det / 12)
                out[i0:i1, side] += (np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(4 * np.pi * f * tt)) * env * 0.08
        out[i0:i1] += (np.sin(2 * np.pi * notes[0] / 4 * tt) * env * 0.25)[:, None]
        # arpegio en corcheas
        seq = [0, 1, 2, 1, 2, 0, 1, 2]
        for k, ni in enumerate(seq):
            n = int(0.35 * SR); u = np.arange(n) / SR
            f = notes[ni] * 2
            y = (np.sin(2 * np.pi * f * u) + 0.3 * np.sign(np.sin(2 * np.pi * f * u)) * 0.3) * np.exp(-u / 0.12) * np.clip(u / 0.004, 0, 1) * 0.14
            place(out, y, a + k * beat / 2, pan=-0.4 if k % 2 else 0.4)
    for bt in np.arange(0, END, beat):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        k = np.sin(2 * np.pi * (50 + 70 * np.exp(-tt / 0.025)) * tt) * np.exp(-tt / 0.08) * 0.35
        place(out, k, bt)
    for bt in np.arange(beat, END, 2 * beat):
        n = int(0.12 * SR); tt = np.arange(n) / SR
        h = rng.standard_normal(n) * np.exp(-tt / 0.03)
        sos = butter(2, 6000, "highpass", fs=SR, output="sos")
        place(out, sosfilt(sos, h) * 0.08, bt)
    sos = butter(2, 3000, "lowpass", fs=SR, output="sos")
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



def scan_tick(dur=0.05, f=2400):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012)
    return y / (np.max(np.abs(y)) + 1e-9)


sfx = np.zeros((N, 2))
place(sfx, whoosh(2.0, 160, 2800, 400), 0.0, 0.4)
# render en vivo: un tic por cada fila de bloques
for k, tk in enumerate(np.linspace(0.35, 3.6, 18)):
    place(sfx, scan_tick(0.05, 1800 + 60 * k), tk, 0.10, pan=-0.5 + k / 17)
place(sfx, ding(1318.51, 1.0), 3.7, 0.16)
for tf in FL:
    place(sfx, zap(), tf - 0.06, 0.55)
place(sfx, boom(), MO0 - 0.1, 0.28)
# tecleo del código
for tk in np.arange(MO0 + 0.4, MO0 + 4.8, 0.075):
    if rng.random() < 0.75:
        place(sfx, click(), tk + 0.02 * rng.random(), 0.12, pan=rng.uniform(-0.3, 0.3))
# rayos que salen y chocan
for k, tk in enumerate(np.linspace(RA0 + 0.3, RA0 + 2.4, 9)):
    place(sfx, blip(700 + 90 * k, 0.09), tk, 0.13, pan=0.5 - 0.11 * k)
place(sfx, ding(987.77, 1.0), wtime("rayos", 9), 0.18)
place(sfx, ding(1479.98, 1.1), wtime("rayos", 13), 0.16)
place(sfx, whoosh(1.3, 300, 2600, 500), wtime("texturas", 8) - 0.3, 0.25)
# cortes de escena
for idx in (10, 12, 15):
    place(sfx, whoosh(0.7, 400, 3200, 700), wtime("escena", idx) - 0.25, 0.25)
    place(sfx, blip(520, 0.12), wtime("escena", idx), 0.14)
place(sfx, ding(783.99, 1.0), wtime("sonido", 6), 0.16, -0.3)
place(sfx, ding(1046.5, 1.0), wtime("sonido", 9), 0.16, 0.3)
for fq in (659.25, 783.99, 987.77):
    place(sfx, ding(fq, 1.3), wtime("sonido", 16), 0.12)
place(sfx, ding(1174.66, 1.2), MZ0 + 0.7 * (MZ1 - MZ0), 0.16)
place(sfx, ding(880.0, 1.2), CIA[0] + 0.5 * (CIA[1] - CIA[0]), 0.16)
place(sfx, whoosh(1.6, 150, 2400, 300), CIB[0] - 0.3, 0.32)
for k in range(5):
    place(sfx, blip(600 + 100 * k, 0.1), CIB[0] + 0.5 + 0.22 * k, 0.12)
place(sfx, boom(1.8), CARD, 0.22)

music = pad_music()
mix = sfx * 0.9 + music * 0.16
mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
wavfile.write(os.path.join(BASE, "out", "sfx_music.wav"), SR, (mix * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "sfx.wav"), SR, (np.clip(sfx * 0.9, -1, 1) * 32767).astype(np.int16))
wavfile.write(os.path.join(BASE, "out", "music.wav"), SR, (music * 0.9 * 32767).astype(np.int16))
print("audio listo", END, "s")
