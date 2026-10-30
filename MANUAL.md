# Flash Datos — manual de operación diaria (en la nube)

Este manual lo siguen las tareas programadas de Claude. **Todo funciona sin la computadora del dueño**: el código y los archivos viven en el repositorio de GitHub `gaelcuenta209-byte/flashdatos`, la voz sale del conector de ElevenLabs, y la publicación y las estadísticas pasan por Metricool (YouTube, Instagram y TikTok). Los datos fijos (IDs, voz, métricas) están en `config.json`.

## Reglas que nunca cambian

1. **Nada se publica sin la aprobación explícita del dueño en el chat** ("sí", "aprobado", "publícalo"). Una aprobación vale solo para ese video. Nunca programar en Metricool un video sin aprobar, ni siquiera como borrador para "adelantar".
2. Antes de publicar, el dueño también aprueba el título y la descripción. Si pide cambios, se aplican y se vuelve a pedir aprobación.
3. Nunca escribir contraseñas, datos de tarjeta ni claves. Si algo pide iniciar sesión o reconectar una cuenta, avisarle al dueño qué tiene que hacer.
4. **Si algo falla en cualquier paso**: notificación push (PushNotification, una línea) y mensaje (SendUserMessage) que diga qué paso falló, qué se intentó y qué necesita hacer el dueño. Dos intentos como máximo por paso.
5. Cada dato del video se verifica con al menos dos fuentes confiables (NASA, ESA, universidades, revistas científicas, enciclopedias). Si no se puede verificar, se cambia el dato o el tema.
6. Contenido original: guion propio y escena 3D distinta en cada video. Nunca la misma plantilla con otro tema (política de contenido inauténtico de YouTube).
7. No es contenido para niños (`madeForKids: false`).
8. **ElevenLabs**: nunca repetir `creative_generate_speech` para reintentar (cobra otra vez). Si la descarga falla, pedir de nuevo el enlace con `creative_get_flow_run_status` (no gasta créditos).

## Preparar la sesión (siempre primero)

1. `add_repo(owner="gaelcuenta209-byte", repo="flashdatos", access="push")` y clonar como indique la respuesta (normalmente `git clone --depth 1 https://github.com/gaelcuenta209-byte/flashdatos /home/claude/flashdatos`). Configurar `git config user.name "Claude"` y el correo `noreply@anthropic.com`.
2. Leer `config.json`, `historial.json` e `ideas.json`.
3. Herramientas: Metricool (`createScheduledPost`, `getScheduledPosts`, `getAnalyticsDataByMetrics`, `getBestTimeToPostByNetwork`), ElevenLabs (`creative_generate_speech`, `creative_get_flow_run_status`) y PushNotification se cargan con ToolSearch.
4. El contenedor no puede abrir elevenlabs.io ni storage.googleapis.com. Por eso la voz se baja con la acción `voz.yml` de GitHub. Tampoco puede crear releases por la API, así que los videos se publican con la acción `medios.yml`. Ambas se disparan con `git push`.

## Carpetas del repositorio

| Ruta | Qué hay |
| --- | --- |
| `motor/` | Motor 3D y de audio (ver abajo) y las fuentes Inter |
| `videos/NN-tema/` | `script.json`, `timing.json`, `guion.md`, `escena.py`, `portada.jpg`, `voz/` (pedido, estado, narración), `medios.json` y `medios_estado.json` |
| `historial.json` | Videos con número, tema, título, estado, ID de Metricool y enlaces |
| `ideas.json` | Ideas del reporte de la mañana; `elegida` = número de la idea que pidió el dueño |
| `reportes/AAAA-MM-DD.md` | Reporte de cada mañana |
| `config.json` | IDs de Metricool, voz de ElevenLabs, métricas |

Los MP4 no se guardan en `main`: se suben a la rama `medios` y quedan como release (ver Flujo B, paso 9).

## Motor (`motor/`)

| Archivo | Para qué |
| --- | --- |
| `render.py` | Trazado de rayos de esferas con texturas, cámara, subtítulos, etiquetas, destellos de marca y marca de agua. Es la escena del video 01: se copia como `escena.py` y se adapta por video. |
| `textures.py`, `earth_real.py`, `continents.py`, `noise.py` | Texturas procedurales (Tierra con continentes reales, Júpiter, Sol, gigante roja). Agregar texturas nuevas aquí. |
| `sync_voice.py` | Lee `script.json` y la narración, detecta las pausas y escribe `timing.json`. |
| `audio.py` | Efectos y música originales sintetizados según `timing.json`. Los eventos se ajustan por video. |
| `mix.sh` | Une video, voz, efectos y música; normaliza a −14 LUFS. Uso: `./mix.sh FlashDatos_NN`. |

Se trabaja en una carpeta aparte: `mkdir -p /home/claude/trabajo && cp -r motor/* /home/claude/trabajo/` y ahí `python3 textures.py && python3 earth_real.py` (≈1 min, genera `tex/`). El contenedor tiene 2 núcleos: renderizar en 2 mitades en paralelo.

Identidad visual: fondo espacial azul noche, subtítulos en Inter Black blanco con palabras clave en amarillo #FFD84D, secundarios cian #4FD8FF, destello blanco con rayo amarillo en cada cambio de escena, marca de agua "⚡ FLASH DATOS" arriba. 1080×1920, 30 fps, 35–45 s.

## Flujo A — Reporte de la mañana (8:00)

1. Estadísticas con Metricool `getAnalyticsDataByMetrics` (`blogId` 7723504), de los últimos 7 días y de los últimos 28, con las métricas de `config.json`:
   - YouTube: título, vistas, URL, duración media vista, likes, comentarios, compartidos y suscriptores.
   - Instagram Reels: vistas, alcance, tiempo medio, retención, tasa de vista a 3 s, guardados y compartidos.
   - TikTok: vistas, alcance, video completo visto, tiempo medio y "Para ti".
   - Si Metricool todavía no tiene datos (los primeros días tarda en importar), decirlo tal cual y no inventar cifras.
2. Explicar **qué video funcionó mejor y por qué**: comparar gancho, tema, duración y retención entre videos y redes. Ser concreto, por ejemplo: "retuvo 82 % porque abre con un número".
3. Revisar el video de ayer con `getScheduledPosts`: si sigue pendiente después de su hora, es un fallo (regla 4).
4. Investigar tendencias (búsqueda web: noticias de ciencia y espacio de la semana, efemérides, lo que se comparte en Shorts y Reels de ciencia en español) y proponer **8 ideas**. Cada idea lleva gancho, por qué puede ser viral, dato principal y dos fuentes. Ordenarlas por potencial y guardarlas en `ideas.json` con `"elegida": null`.
5. Guardar `reportes/AAAA-MM-DD.md`, hacer commit y push, mandar el reporte con SendUserMessage y avisar con push: "Tu reporte está listo; responde con el número de idea si quieres otra que no sea la 1". Si el dueño responde un número antes de las 9, escribirlo en `elegida` y hacer push.

## Flujo B — Video del día (9:00)

1. `git pull`. **Si `historial.json` ya tiene un video con `fecha_programada` de hoy** (programado o esperando aprobación), no producir otro: avisar al dueño en un mensaje corto y terminar. Si no, usar la idea de `ideas.json` cuyo número diga `elegida`; si no hay, la primera que no repita tema de `historial.json`. Número del video: el siguiente en `historial.json` (dos dígitos).
2. Verificar los datos (regla 5). Escribir `videos/NN-tema/script.json` con el formato del video 01:
   - segmentos → partes con `say` (cómo se dice, con números en palabras) y `cap` (el subtítulo, con cifras);
   - gancho en la primera frase;
   - un final que conecte con el inicio para que el video se repita solo.
   Escribir también `guion.md` con las fuentes. Si el dueño pidió otra hora de publicación, guardarla en `historial.json` (`fecha_programada`) y usarla en lugar de las 17:00.
3. **Voz**: `creative_generate_speech` con `voice_id` y `model_id` de `config.json`. Como `prompt` va todo el texto (`say` de todas las partes) en un solo párrafo, sin saltos de línea. Esperar con `creative_get_flow_run_status`. De las dos tomas, elegir la más clara: en caso de duda, la primera.
4. Escribir `videos/NN-tema/voz/pedido.json` con `{"url": "<content_url de la toma>", "generation_id": "...", "flow_id": "...", "voice_id": "...", "model_id": "..."}`, hacer commit y push. La acción **Voz (ElevenLabs)** baja el MP3 en menos de un minuto. Hacer `git pull` cada 15 s, hasta 5 minutos, hasta que exista `voz/narracion.mp3`, y leer `voz/estado.json`.
   - Si `ok` es false porque el enlace caducó (dura 2 h), pedir un enlace nuevo con `creative_get_flow_run_status`, borrar `estado.json`, actualizar `url` y hacer push otra vez.
   - Si el dueño agregó el secreto `ELEVENLABS_API_KEY`, también sirve `{"texto": "...", "voice_id": "...", "model_id": "eleven_multilingual_v2"}` sin `url`.
5. En la carpeta de trabajo, copiar `script.json` y `voz/narracion.mp3` (a `voz/`) y correr `python3 sync_voice.py script.json voz/narracion.mp3 timing.json`. Revisar que ninguna parte termine antes de empezar.
6. Crear `escena.py` a partir de `render.py`: cuerpos y texturas del tema, movimientos de cámara por segmento, etiquetas grandes con el dato de cada momento. Renderizar cuadros de prueba (`python3 escena.py test 1 5 12 ...`), revisarlos con Read y corregir antes del render completo.
7. Render completo en dos mitades en paralelo (`python3 escena.py chunk 0 N/2 out/chunk_a.mp4` y `chunk N/2 N out/chunk_b.mp4`, con N = cuadros totales, de `python3 escena.py info`). Después `python3 audio.py` y `./mix.sh FlashDatos_NN`. Revisar cuadros clave y que los efectos no tapen la voz.
8. Copiar al repositorio `escena.py`, `timing.json` y la portada (`out/FlashDatos_NN_portada.jpg` como `portada.jpg`), hacer commit y push a `main`.
9. **Enlace público para Metricool**:
   - Clonar la rama `medios` (`git clone --depth 1 -b medios ...` en una carpeta aparte).
   - Agregar `NN/FlashDatos_NN.mp4` y `NN/FlashDatos_NN_portada.jpg`, y hacer commit y push a `medios`.
   - Después escribir en `main` el archivo `videos/NN-tema/medios.json` con `{"numero": "NN", "archivos": ["FlashDatos_NN.mp4", "FlashDatos_NN_portada.jpg"]}` y hacer push.
   - La acción **Medios para publicar** crea el release `video-NN` y escribe `medios_estado.json`. Esperar con `git pull` hasta que exista y diga `"ok": true`. El enlace queda así: `https://github.com/gaelcuenta209-byte/flashdatos/releases/download/video-NN/FlashDatos_NN.mp4`.
10. Agregar el video a `historial.json` con `"estado": "esperando aprobación"` y hacer push.
11. Mandar el video al dueño (SendUserFile) con los textos siguientes. **El rayo ⚡ es el símbolo del canal:** el título de YouTube, la descripción y el título de TikTok empiezan con ⚡ (ver `perfiles.md`).
    Textos:
    - el título de YouTube (máximo 100 caracteres, con #shorts);
    - la descripción (2–3 líneas, la fuente y 4–6 hashtags);
    - el texto para Instagram y TikTok.
    Avisar con push: "Tu video de hoy está listo para aprobar". Pedir aprobación y esperar la respuesta.

## Al recibir la aprobación

1. Programar con Metricool `createScheduledPost`:
   - `blogId` 7723504.
   - Fecha: hoy a las **17:00** (`AAAA-MM-DDT17:00:00-06:00`). Si ya pasaron las 16:45, ahora más 15 minutos.
   - `info`, con los textos aprobados:
     ```json
     {"autoPublish": true, "draft": false, "descendants": [], "firstCommentText": "", "hasNotReadNotes": false,
      "media": ["<enlace del release>"], "mediaAltText": [], "shortener": false, "smartLinkData": {"ids": []},
      "providers": [{"network": "youtube"}, {"network": "instagram"}, {"network": "tiktok"}],
      "publicationDate": {"dateTime": "AAAA-MM-DDT17:00:00", "timezone": "America/Mexico_City"},
      "text": "<descripción aprobada con hashtags>",
      "youtubeData": {"title": "<título aprobado>", "type": "short", "privacy": "public", "madeForKids": false, "category": "SCIENCE_TECHNOLOGY", "isAiGeneratedContent": false},
      "instagramData": {"type": "REEL", "showReelOnFeed": true, "isAiGenerated": false},
      "tiktokData": {"privacyOption": "PUBLIC_TO_EVERYONE", "title": "<título corto>", "isAigc": false}}
     ```
2. Confirmar con `getScheduledPosts` que quedó en la fecha correcta, con las tres redes.
3. Actualizar `historial.json`: estado `"programado"`, fecha, `metricool` (id, uuid, plannerUrl) y enlace del release. Hacer push.
4. Avisar al dueño en un mensaje corto con la hora y el enlace del planificador.

## Flujo C — Verificación de la tarde (17:30)

1. `git pull` y buscar en `historial.json` el video de hoy.
   - Si sigue `"esperando aprobación"`, mandar push: "El video de hoy sigue esperando tu sí". No es un error del sistema.
   - Si no hubo video hoy, avisar por qué, si se sabe.
2. Si estaba programado: `getScheduledPosts` de hoy.
   - Si ya no aparece como pendiente, salió.
   - Si aparece pendiente después de las 17:10, o alguna red dice error, es un fallo (regla 4).
3. Buscar los enlaces publicados:
   - En las métricas de Metricool: `YTVV05`, `IGRE06` y `TKPO03` del día.
   - Si todavía no aparecen, decir que se agregarán en el reporte de mañana.
   - Actualizar `historial.json` (estado `"publicado"` y enlaces) y hacer push.
4. Mensaje corto al dueño con lo que salió.
