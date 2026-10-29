"""Genera o descarga la narración de cada video que tenga voz/pedido.json y todavía no tenga voz/narracion.mp3.

pedido.json acepta dos formas:
  {"url": "<enlace firmado de la generación de ElevenLabs>"}                 -> se descarga tal cual
  {"texto": "...", "voice_id": "...", "model_id": "eleven_multilingual_v2"}  -> se genera con la API (secreto ELEVENLABS_API_KEY)

Escribe voz/estado.json con el resultado, para que Claude lo lea después del push.
"""
import glob, json, os, sys, time, urllib.request, urllib.error

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_192"


def es_mp3(b):
    return len(b) > 8000 and (b[:3] == b"ID3" or (b[0] == 0xFF and (b[1] & 0xE0) == 0xE0))


def descargar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "flashdatos-voz/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def generar(p):
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta el secreto ELEVENLABS_API_KEY en Settings > Secrets and variables > Actions")
    body = {
        "text": p["texto"],
        "model_id": p.get("model_id", "eleven_multilingual_v2"),
        "voice_settings": p.get("voice_settings", {"stability": 0.5, "similarity_boost": 0.75, "style": 0.3, "use_speaker_boost": True}),
    }
    if p.get("language_code"):
        body["language_code"] = p["language_code"]
    req = urllib.request.Request(API.format(voice=p["voice_id"]), data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"ElevenLabs respondió {e.code}: {e.read()[:300].decode(errors='replace')}")


def main():
    fallos = 0
    for ped in sorted(glob.glob("videos/*/voz/pedido.json")):
        carpeta = os.path.dirname(ped)
        destino = os.path.join(carpeta, "narracion.mp3")
        if os.path.exists(destino):
            continue
        p = json.load(open(ped, encoding="utf-8"))
        estado = {"pedido": ped, "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        try:
            if p.get("url"):
                datos, estado["fuente"] = descargar(p["url"]), "url"
            else:
                datos, estado["fuente"] = generar(p), "api"
            if not es_mp3(datos):
                raise RuntimeError(f"lo que llegó no parece un MP3 ({len(datos)} bytes)")
            open(destino, "wb").write(datos)
            estado.update(ok=True, bytes=len(datos))
            print(f"listo {destino} ({len(datos)} bytes, {estado['fuente']})")
        except Exception as e:  # se guarda el error para que Claude avise al dueño
            fallos += 1
            estado.update(ok=False, error=str(e))
            print(f"ERROR {ped}: {e}", file=sys.stderr)
        json.dump(estado, open(os.path.join(carpeta, "estado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return fallos


if __name__ == "__main__":
    main()  # nunca falla el job: el resultado queda en estado.json y se sube igual
