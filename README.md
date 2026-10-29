# Flash Datos ⚡

Motor 3D, guiones y publicación automática de Shorts, Reels y TikToks de ciencia, espacio y tecnología.

| Carpeta | Qué hay |
| --- | --- |
| `MANUAL.md` | Lo que siguen las tareas programadas de Claude cada día |
| `motor/` | Trazado de rayos, texturas, sincronía de voz, efectos, música y mezcla |
| `videos/NN-tema/` | Guion (`script.json`), tiempos (`timing.json`), escena 3D, narración y portada de cada video |
| `historial.json` | Videos publicados con sus enlaces |
| `ideas.json` | Ideas del reporte de la mañana |
| `reportes/` | Reporte diario de estadísticas |
| `.github/workflows/` | `voz.yml` trae la narración de ElevenLabs · `medios.yml` publica el MP4 como release para Metricool |

Requisitos para renderizar: Python 3 con numpy, scipy y Pillow, y ffmpeg.
