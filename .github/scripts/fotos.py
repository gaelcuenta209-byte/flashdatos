"""Descarga las fotos de cada video que tenga fotos/pedido.json y todavía no tenga fotos/creditos.json.

pedido.json: {"fotos": [{"nombre": "lotus79", "wiki": "Lotus_79"},            -> foto principal libre del artículo de Wikipedia
                        {"nombre": "x", "archivo": "File:Algo.jpg"},           -> archivo concreto de Wikimedia Commons
                        {"nombre": "y", "url": "https://..."}],                -> enlace directo (por ejemplo, una imagen de ElevenLabs)
              "ancho": 1600}
Escribe fotos/<nombre>.<ext> y fotos/creditos.json (autor y licencia de cada foto de Commons).
"""
import glob, html, json, os, re, sys, urllib.parse, urllib.request

UA = "FlashDatosBot/1.0 (https://github.com/gaelcuenta209-byte/flashdatos)"


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def api(base, **params):
    params.update(format="json", formatversion="2")
    return json.loads(get(base + "?" + urllib.parse.urlencode(params)))


def limpiar(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def archivo_de_articulo(titulo, lang="en"):
    d = api(f"https://{lang}.wikipedia.org/w/api.php", action="query", prop="pageimages", piprop="name",
            pilicense="free", titles=titulo, redirects=1)
    p = d["query"]["pages"][0]
    if not p.get("pageimage"):
        raise RuntimeError(f"el artículo {titulo} no tiene foto libre")
    return "File:" + p["pageimage"]


def info_commons(archivo, ancho):
    d = api("https://commons.wikimedia.org/w/api.php", action="query", titles=archivo, prop="imageinfo",
            iiprop="url|extmetadata|size", iiurlwidth=ancho)
    p = d["query"]["pages"][0]
    ii = p["imageinfo"][0]
    md = ii.get("extmetadata", {})
    v = lambda k: limpiar(md.get(k, {}).get("value", ""))
    return {"url": ii.get("thumburl") or ii["url"], "pagina": ii.get("descriptionurl"), "autor": v("Artist"),
            "licencia": v("LicenseShortName"), "licencia_url": v("LicenseUrl"), "atribucion": v("Attribution"),
            "ancho_original": ii.get("width"), "alto_original": ii.get("height")}


def main():
    for ped in sorted(glob.glob("videos/*/fotos/pedido.json")):
        carpeta = os.path.dirname(ped)
        destino = os.path.join(carpeta, "creditos.json")
        if os.path.exists(destino):
            continue
        p = json.load(open(ped, encoding="utf-8"))
        ancho = p.get("ancho", 1600)
        creditos = []
        for f in p["fotos"]:
            c = {"nombre": f["nombre"]}
            try:
                if f.get("url"):
                    url = f["url"]
                    c["fuente"] = "url"
                else:
                    archivo = f.get("archivo") or archivo_de_articulo(f["wiki"], f.get("lang", "en"))
                    c.update(info_commons(archivo, ancho), archivo=archivo, fuente="commons")
                    url = c["url"]
                datos = get(url, 120)
                ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".jpg"
                if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                    ext = ".jpg"
                ruta = os.path.join(carpeta, f["nombre"] + ext)
                open(ruta, "wb").write(datos)
                c.update(ok=True, ruta=ruta, bytes=len(datos))
                print("listo", ruta, len(datos))
            except Exception as e:
                c.update(ok=False, error=str(e))
                print("ERROR", f, e, file=sys.stderr)
            creditos.append(c)
        json.dump(creditos, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()  # nunca falla el job: el resultado queda en creditos.json
