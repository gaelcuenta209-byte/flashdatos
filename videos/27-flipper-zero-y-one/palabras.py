"""Tiempo de cada palabra del subtítulo (para los subtítulos palabra por palabra).
Reparte cada frase según lo que tarda en decirse cada palabra y salta las pausas reales de la voz.
Uso: python3 palabras.py timing.json voz/narracion.mp3 timing.js"""
import json, re, subprocess, sys
SPOKEN = {"$169": 26, "2024": 18, "$20": 13, "$379": 24, "NFC": 8, "RFID": 10, "HDMI": 11, "VPN": 7, "5G": 7,
          "GB": 5, "1": 2, "2": 3, "8": 4, "5": 5}

def spoken(w):
    c = re.sub(r"[.,:;…?!¡¿()\"]", "", w)
    if c in SPOKEN: return SPOKEN[c]
    return len(re.sub(r"[^\wáéíóúñü]", "", c.lower())) or 1

def gaps(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "silencedetect=noise=-32dB:d=0.07", "-f", "null", "-"], capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]; e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(s, e))

tm = json.load(open(sys.argv[1])); off = tm["voice_offset"]; G = gaps(sys.argv[2])
for seg in tm["segments"]:
    for p in seg["parts"]:
        a, b, cap = p[0] - off, p[1] - off, p[2]
        inner = [(max(x, a), min(y, b)) for x, y in G if y > a + 0.05 and x < b - 0.05]
        speech = (b - a) - sum(y - x for x, y in inner)
        def real(st):
            t, rem = a, st
            for x, y in inner:
                if t + rem <= x: return t + rem
                rem -= max(0.0, x - t); t = y
            return t + rem
        words = cap.split(); wts = [spoken(w) + 2 for w in words]; tot = sum(wts); acc = 0; out = []
        for w, wt in zip(words, wts):
            out.append([round(real(speech * (acc + 0.6) / tot) + off, 3), w]); acc += wt
        p.append(out)
tm["end"] = round(tm["segments"][-1]["t1"] + 1.9, 2)
open(sys.argv[3], "w").write("const TM = " + json.dumps(tm, ensure_ascii=False) + ";\n")
json.dump(tm, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print("end", tm["end"]); [print(seg["id"], [(w, t) for p in seg["parts"] for t, w in p[3]][:6]) for seg in tm["segments"]]
