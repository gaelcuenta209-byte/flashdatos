"""Publica (o programa) un video en YouTube, Instagram y TikTok con la API gratuita de Buffer.

Claude sube videos/NN-tema/publicar.json, solo después de que el dueño apruebe el video en el chat:
  {"numero": "31", "video_url": "<enlace del release>", "texto": "<descripción con hashtags>",
   "titulo_youtube": "...", "titulo_tiktok": "...", "fecha": "2026-11-13T23:00:00Z"}   (fecha en UTC; vacía = publicar ya)
La acción escribe videos/NN-tema/publicar_estado.json con lo que respondió Buffer.
Con buffer/consulta.json (cualquier contenido) solo lista los canales y el esquema, en buffer/consulta_estado.json.
Necesita el secreto BUFFER_API_KEY (publish.buffer.com/settings/api).
"""
import datetime, glob, json, os, subprocess, sys, urllib.request, urllib.error

API = "https://api.buffer.com"
KEY = os.environ.get("BUFFER_API_KEY", "").strip()


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode(errors="replace")[:2000]}


def final_url(url):
    # los enlaces de los releases redirigen a una URL firmada; Buffer pide un enlace directo
    try:
        out = subprocess.run(["curl", "-sSIL", "-o", "/dev/null", "-w", "%{url_effective}", url], capture_output=True, text=True, timeout=60)
        return out.stdout.strip() or url
    except Exception:
        return url


def channels():
    orgs = gql("query { account { organizations { id name } } }")
    res = []
    for o in (orgs.get("data") or {}).get("account", {}).get("organizations", []) or []:
        ch = gql("query Ch($o: OrganizationId!) { channels(input: { organizationId: $o }) { id name displayName service isQueuePaused } }", {"o": o["id"]})
        for c in (ch.get("data") or {}).get("channels", []) or []:
            c["organizationId"] = o["id"]; res.append(c)
        if "errors" in ch or "http_error" in ch:
            res.append({"error": ch})
    return res, orgs


def type_fields(name):
    r = gql("query T($n: String!) { __type(name: $n) { name inputFields { name type { name kind ofType { name kind } } } } }", {"n": name})
    t = (r.get("data") or {}).get("__type") or {}
    return {f["name"]: (f["type"].get("name") or (f["type"].get("ofType") or {}).get("name")) for f in t.get("inputFields") or []}


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)


def now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    pend = [p for p in glob.glob("videos/*/publicar.json") if not os.path.exists(p.replace("publicar.json", "publicar_estado.json"))]
    consulta = os.path.exists("buffer/consulta.json") and not os.path.exists("buffer/consulta_estado.json")
    if not KEY:
        for p in pend:
            write(p.replace("publicar.json", "publicar_estado.json"), {"ok": False, "fecha_utc": now(), "error": "Falta el secreto BUFFER_API_KEY en GitHub"})
        if consulta:
            write("buffer/consulta_estado.json", {"ok": False, "fecha_utc": now(), "error": "Falta el secreto BUFFER_API_KEY en GitHub"})
        return
    chs, orgs = channels()
    if consulta:
        cpi = type_fields("CreatePostInput")
        meta_t = cpi.get("metadata")
        write("buffer/consulta_estado.json", {"ok": bool(chs) and not any("error" in c for c in chs), "fecha_utc": now(), "organizaciones": orgs,
                                              "canales": chs, "CreatePostInput": cpi, "metadata_tipo": meta_t,
                                              "metadata_campos": type_fields(meta_t) if meta_t else None})
    if not pend:
        return
    cpi = type_fields("CreatePostInput"); meta_t = cpi.get("metadata"); meta_f = type_fields(meta_t) if meta_t else {}
    key_for = {}
    for svc in ("youtube", "instagram", "tiktok"):
        k = next((f for f in meta_f if f.lower() == svc), None) or next((f for f in meta_f if svc in f.lower()), None)
        key_for[svc] = k
    mutation = """mutation C($input: CreatePostInput!) { createPost(input: $input) {
      __typename ... on PostActionSuccess { post { id status dueAt assets { __typename } } } ... on MutationError { message } } }"""
    for p in pend:
        job = json.load(open(p))
        url = final_url(job["video_url"])
        fecha = (job.get("fecha") or "").strip()
        out = {"ok": True, "fecha_utc": now(), "video_url_directa": url[:120] + "…", "metadata_claves": key_for, "redes": {}}
        for svc in ("youtube", "instagram", "tiktok"):
            ch = next((c for c in chs if c.get("service") == svc and not c.get("error")), None)
            if not ch:
                out["redes"][svc] = {"ok": False, "error": "No hay canal de " + svc + " conectado en Buffer"}; out["ok"] = False; continue
            inp = {"channelId": ch["id"], "text": job["texto"], "schedulingType": "automatic", "needsApproval": False,
                   "mode": "customScheduled" if fecha else "shareNow", "assets": [{"video": {"url": url}}]}
            if fecha:
                inp["dueAt"] = fecha
            md = {"youtube": {"title": job["titulo_youtube"][:100], "categoryId": "28", "privacy": "public", "madeForKids": False},
                  "instagram": {"type": "reel", "shouldShareToFeed": True},
                  "tiktok": {"title": job.get("titulo_tiktok", "")}}[svc]
            if key_for[svc]:
                inp["metadata"] = {key_for[svc]: md}
            r = gql(mutation, {"input": inp})
            cp = (r.get("data") or {}).get("createPost") or {}
            ok = cp.get("__typename") == "PostActionSuccess"
            if not ok and svc == "tiktok" and "title" in json.dumps(r):   # el título de TikTok solo está documentado para fotos
                inp.pop("metadata", None); r = gql(mutation, {"input": inp}); cp = (r.get("data") or {}).get("createPost") or {}
                ok = cp.get("__typename") == "PostActionSuccess"
            out["redes"][svc] = {"ok": ok, "canal": ch.get("name"), "respuesta": r}
            out["ok"] = out["ok"] and ok
        write(p.replace("publicar.json", "publicar_estado.json"), out)


if __name__ == "__main__":
    main()
