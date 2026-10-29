"""Sincroniza el guion con la narración: detecta las pausas reales de la voz y calcula cuándo empieza
y termina cada frase. Escribe timing.json para render.py y audio.py.

Uso: python3 sync_voice.py <script.json> <narracion.mp3> [timing.json]
"""
import json, re, subprocess, sys

OFFSET = 0.10   # la voz entra 0.10 s después del primer cuadro
TAIL = 0.83     # cuadros finales después de la última palabra


def merge(gaps, tol=0.06):
    out = []
    for a, b in sorted(gaps):
        if out and a - out[-1][1] < tol:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def detect_gaps(path, noise="-35dB", d="0.12"):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()[2]) + 60 * float(re.search(r"Duration: (\d+):(\d+)", out).groups()[1])
    gaps = list(zip(starts, ends + [dur] * (len(starts) - len(ends))))
    first = gaps[0][1] if gaps and gaps[0][0] < 0.05 else 0.0
    gaps = [g for g in gaps if g[0] > 0.05]
    last = gaps[-1][0] if gaps and gaps[-1][1] >= dur - 0.05 else dur
    gaps = [g for g in gaps if g[1] < dur - 0.05]
    return first, last, merge(gaps), dur


def weight(text):
    return len(re.sub(r"[^\wáéíóúñü]", "", text.lower())) + 2


def main(script_path, voice_path, out_path="timing.json"):
    sc = json.load(open(script_path))
    first, last, gaps, dur = detect_gaps(voice_path)
    fine = detect_gaps(voice_path, "-30dB", "0.08")[2]
    parts = [(si, pi, p) for si, s in enumerate(sc["segments"]) for pi, p in enumerate(s["parts"])]
    w = [weight(p["say"]) for _, _, p in parts]
    total = sum(w)
    speech = (last - first) - sum(b - a for a, b in gaps)

    def real_time(speech_t):
        t = first
        rem = speech_t
        for a, b in gaps:
            if t + rem <= a:
                return t + rem
            rem -= max(0.0, a - t)
            t = b
        return t + rem

    bounds = []  # límite entre la parte k y la k+1
    cum = 0
    prev_end = first
    for k in range(len(parts) - 1):
        cum += w[k]
        exp = real_time(speech * cum / total)
        seg_break = parts[k + 1][0] != parts[k][0]
        best = None
        for cand, tol in ((gaps, 1.4), (fine, 1.2)):
            best_score = 9e9
            for a, b in cand:
                if a <= prev_end + 0.15:
                    continue
                c = (a + b) / 2
                score = abs(c - exp) - (0.9 if seg_break else 0.5) * min(b - a, 0.8)
                if abs(c - exp) < tol and score < best_score:
                    best, best_score = (a, b), score
            if best is not None:
                break
        if best is None:
            x = max(exp, prev_end + 0.3)
            best = (x, x)
        bounds.append(best)
        prev_end = best[1]

    times = []
    start = first
    for k in range(len(parts)):
        end = bounds[k][0] if k < len(bounds) else last
        times.append((start, end))
        if k < len(bounds):
            start = bounds[k][1]

    segs = []
    for si, s in enumerate(sc["segments"]):
        pts = [(times[k], parts[k][2]) for k in range(len(parts)) if parts[k][0] == si]
        segs.append({
            "id": s["id"],
            "t0": round(pts[0][0][0] + OFFSET, 2), "t1": round(pts[-1][0][1] + OFFSET, 2),
            "say": " ".join(p["say"] for _, p in pts),
            "parts": [[round(a + OFFSET, 2), round(b + OFFSET, 2), p["cap"]] for (a, b), p in pts],
        })

    def word_time(seg_id, word):
        for k, (si, pi, p) in enumerate(parts):
            if sc["segments"][si]["id"] != seg_id:
                continue
            words = p["say"].split()
            ws = [weight(x) for x in words]
            acc = 0
            for x, wt in zip(words, ws):
                if re.sub(r"[^\wáéíóúñü]", "", x.lower()) == word:
                    a, b = times[k]
                    return a + (b - a) * (acc + 0.15 * wt) / sum(ws) + OFFSET
                acc += wt
        raise KeyError(word)

    rings = [round(word_time(sid, wd), 2) for sid, wd in sc.get("ring_words", [])]
    if rings:
        orb = next(s for s in segs if s["id"] == "orbitas")
        rings.append(round(orb["t1"] + 0.15, 2))
    timing = {"voice_offset": OFFSET, "voice_duration": round(dur, 3), "segments": segs, "rings": rings,
              "end": round(last + OFFSET + TAIL, 2)}
    json.dump(timing, open(out_path, "w"), ensure_ascii=False, indent=1)
    for s in segs:
        print(f"{s['id']:8s} {s['t0']:6.2f}-{s['t1']:6.2f}  " + " | ".join(f"{a:.2f}-{b:.2f}" for a, b, _ in s["parts"]))
    print("rings", rings, "end", timing["end"])


if __name__ == "__main__":
    main(*sys.argv[1:])
