"""Filma escena.html cuadro por cuadro.
  python3 film.py test 1.5 30 ...        -> frames_test/tXXX.jpg
  python3 film.py chunk <ini> <fin> <out.mp4>
  python3 film.py info
"""
import base64, os, subprocess, sys
from playwright.sync_api import sync_playwright
BASE = os.path.dirname(os.path.abspath(__file__)); FPS = 30

def page(p):
    b = p.chromium.launch(args=["--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file://" + os.path.join(BASE, "escena.html"))
    pg.evaluate("window.READY")
    if errs: print("ERRORES:", errs, flush=True)
    return b, pg, errs

def grab(pg, t):
    s = pg.evaluate(f"grab({t}, 0.93)")
    return base64.b64decode(s.split(",", 1)[1])

if __name__ == "__main__":
    mode = sys.argv[1]
    with sync_playwright() as p:
        b, pg, errs = page(p)
        if mode == "info":
            print(pg.evaluate("INFO"))
        elif mode == "test":
            os.makedirs(os.path.join(BASE, "frames_test"), exist_ok=True)
            for ts in sys.argv[2:]:
                open(os.path.join(BASE, "frames_test", f"t{float(ts):06.2f}.jpg"), "wb").write(grab(pg, float(ts)))
            if errs: print("ERRORES:", errs)
        elif mode == "chunk":
            a, z, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
            tmp = out[:-4] + ".part.mp4"
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(FPS), "-i", "-",
                                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
            for f in range(a, z):
                ff.stdin.write(grab(pg, f / FPS))
                if f % 150 == 0: print(f"{out}: {f}/{z}", flush=True)
            ff.stdin.close(); rc = ff.wait()
            if rc == 0: os.replace(tmp, out); print("listo", out, flush=True)
            if errs: print("ERRORES:", errs[:5])
        b.close()
