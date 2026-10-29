#!/bin/bash
# Une el render, la voz de ElevenLabs, los efectos y la música, y normaliza a -14 LUFS para redes sociales.
# Uso: ./mix.sh <nombre_salida_sin_extension>   (por defecto FlashDatos_video)
set -e
cd "$(dirname "$0")"
NAME="${1:-FlashDatos_video}"
END_T=$(python3 -c "import json; print(json.load(open('timing.json'))['end'])")
printf "file 'chunk_a.mp4'\nfile 'chunk_b.mp4'\n" > out/list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i out/list.txt -c copy out/video_mudo.mp4

ffmpeg -y -loglevel error \
  -i voz/narracion.mp3 -i out/music.wav -i out/sfx.wav \
  -filter_complex "\
[0:a]aresample=48000,adelay=100|100,apad,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,volume=1.0,asplit=3[voz][voz_sc][voz_sc2];\
[1:a]volume=0.18[mus];\
[mus][voz_sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[mus_d];\
[2:a]volume=0.8[sfx0];\
[sfx0][voz_sc2]sidechaincompress=threshold=0.05:ratio=3:attack=10:release=250[sfx];\
[voz][mus_d][sfx]amix=inputs=3:normalize=0:duration=longest,atrim=0:${END_T},loudnorm=I=-14:TP=-1.0:LRA=9[out]" \
  -map "[out]" -ar 48000 -ac 2 out/audio_final.wav

ffmpeg -y -loglevel error -i out/video_mudo.mp4 -i out/audio_final.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  "out/${NAME}.mp4"
ffmpeg -y -loglevel error -ss 2.0 -i "out/${NAME}.mp4" -frames:v 1 "out/${NAME}_portada.jpg"
echo "video final listo: out/${NAME}.mp4"
