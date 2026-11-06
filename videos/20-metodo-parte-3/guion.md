# Video 20 · El método Flash Datos · Parte 3/5: la animación 3D y el sonido

Serie pedida por el dueño el 2026-11-03: cómo hacemos el canal, contado por nosotros. Se publica sola a las 22:00 (ver `serie-metodo.json`).

## Narración

Este planeta no es una foto: lo dibuja un programa, rayo por rayo. Así animamos cada video. Claude programó en Python un motor en tres dimensiones propio, que dibuja planetas y estrellas con trazado de rayos. Por cada pixel lanza un rayo, y calcula dónde choca y cuánta luz recibe. Las texturas también salen del código: por ejemplo, una Tierra con los continentes reales. Y cada video tiene una escena nueva, no una plantilla: la cámara, los cuerpos y las etiquetas cambian según el tema. El sonido también es nuestro: los efectos y la música se sintetizan con código, y son originales. Al final, la mezcla se ajusta al volumen de las redes. Así, cada imagen y cada sonido de este canal salen de código, no de una plantilla. En la parte cuatro, GitHub: el cerebro del canal. Estén atentos para conocer el método.

Voz: ElevenLabs, Carlos Garza - Mexican Narrator (`eleven_v4`), toma 1 de 2 (flow `bB2oJyaD1v7m3mei4k09`). La toma duraba 57 s; para quedar en el formato de la serie se acortaron las pausas largas a 0.26 s y se aceleró 8 % (`atempo=1.08`) antes de `sync_voice.py`. El MP3 original está en `voz/narracion.mp3`.

## Escena

Júpiter que se dibuja en vivo por bloques de 72 px sobre una malla de alambre ("NO ES UNA FOTO · dibujando… %"); el código real de `draw_sphere` escribiéndose en una ventana ("motor 3D · PYTHON" → TRAZADO DE RAYOS); diagrama "1 PIXEL = 1 RAYO" con una cámara de pixeles, rayos que chocan con Júpiter (CHOCA) y la línea de luz al Sol (LUZ); la textura de la Tierra plana (`textures.py → tierra`) que se envuelve en la esfera (CONTINENTES REALES); cuadrícula con portadas reales de los videos 01, 09, 10, 13, 16 y 17 (ESCENA NUEVA · NO ES PLANTILLA); cortes de CÁMARA (Venus con marco REC), CUERPOS (gigante roja) y ETIQUETAS (el Sol con su etiqueta); anillo de barras con el espectro real de la música y los efectos de este video (EFECTOS, MÚSICA, ORIGINALES); consola de mezcla con el medidor a −14 LUFS (YouTube · Instagram · TikTok); carrusel con Tierra, Venus, Júpiter, Sol y gigante roja ("IMAGEN + SONIDO = CÓDIGO"); avance "Parte 4 · GitHub · el cerebro del canal" con un grafo de commits.

Música original: arpegio en La menor (Am–F–C–G) a 108 BPM.

## Fuentes

Es la historia del propio canal: lo que dicen `MANUAL.md` (sección Motor, regla 6 y Flujo B, pasos 6 y 7; `mix.sh` normaliza a −14 LUFS), `config.json` y `serie-metodo.json` de este repositorio.
