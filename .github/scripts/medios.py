"""Publica como release los archivos que cada videos/*/medios.json pide y que están en la rama "medios" (_medios/NN/).
Escribe videos/NN-tema/medios_estado.json con los enlaces públicos y si responden."""
import glob, json, os, subprocess, time, urllib.request

REPO = os.environ["GITHUB_REPOSITORY"]


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True)


def revisar(url):
    try:
        req = urllib.request.Request(url, headers={"Range": "bytes=0-1023", "User-Agent": "flashdatos-medios/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return {"http": r.status, "tipo": r.headers.get("Content-Type"), "total": r.headers.get("Content-Range")}
    except Exception as e:
        return {"error": str(e)}


for ped in sorted(glob.glob("videos/*/medios.json")):
    carpeta = os.path.dirname(ped)
    destino = os.path.join(carpeta, "medios_estado.json")
    p = json.load(open(ped, encoding="utf-8"))
    n = str(p["numero"]).zfill(2)
    archivos = [os.path.join("_medios", n, a) for a in p["archivos"]]
    faltan = [a for a in archivos if not os.path.exists(a)]
    if not os.path.isdir(os.path.join("_medios", n)):
        continue  # ya publicado antes (la rama medios ya no tiene esta carpeta)
    estado = {"numero": n, "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "enlaces": {}}
    if faltan:
        estado.update(ok=False, error="faltan en la rama medios: " + ", ".join(faltan))
    else:
        tag = f"video-{n}"
        if sh("gh", "release", "view", tag).returncode == 0:
            r = sh("gh", "release", "upload", tag, *archivos, "--clobber")
        else:
            r = sh("gh", "release", "create", tag, *archivos, "--target", "main", "--title", f"Video {n}",
                   "--notes", f"Archivos del video {n} de Flash Datos, listos para publicar.")
        if r.returncode != 0:
            estado.update(ok=False, error=(r.stderr or r.stdout)[-500:])
        else:
            time.sleep(3)
            for a in p["archivos"]:
                url = f"https://github.com/{REPO}/releases/download/{tag}/{a}"
                estado["enlaces"][a] = {"url": url, **revisar(url)}
            estado["ok"] = all(v.get("http") in (200, 206) for v in estado["enlaces"].values())
    json.dump(estado, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(estado, ensure_ascii=False, indent=1))
