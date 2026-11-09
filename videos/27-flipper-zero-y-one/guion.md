# Video 27 · Flipper Zero y Flipper One: cómo funcionan y por qué todos hablan del One

Pedido directo del dueño en el chat el 8 de noviembre de 2026 a las 21:33 ("sube un video explicando el funcionamiento del Flipper Zero y el One y por qué la gente está hablando del One; mejora la animación para que sea más enganchadora; en cuanto lo tengas, súbelo").
Voz: Carlos Garza (eleven_v4), toma 1 (88.1 s). Se acortaron las pausas de más de 0.3 s y se aceleró 7 % (`voz/narracion_editada.mp3`, 78.9 s). Video: 80.7 s.

## Guion

- Gancho: el aparato hacker que Canadá quiso prohibir ya tiene hermano mayor… y no es lo que todos esperaban.
- Flipper Zero: cabe en la mano, cuesta 169 dólares y, según su creador, hay cerca de un millón en el mundo.
- Cómo funciona: escucha señales, las guarda y las repite. Radio para controles de portones, NFC y RFID para tarjetas de acceso, infrarrojo para teles y aires. Un delfín virtual que sube de nivel.
- Polémica: en 2024 Canadá quiso prohibirlo por los robos de autos; las llaves modernas cambian su código en cada clic (código rodante) y al final no lo prohibió. Aviso en pantalla: usarlo en lo ajeno es ilegal.
- Flipper One: no es un Zero 2, es una computadora con Linux de bolsillo. 8 núcleos (Rockchip RK3576), 8 GB de RAM, chip de IA (NPU), potencia parecida a una Raspberry Pi 5. Dos puertos de red, wifi, HDMI y ranura M.2 para 5G o un disco. Router, VPN o laboratorio de redes.
- Por qué se habla ahora: acaban de abrir las reservas: 20 dólares para apartarlo y desde 379 dólares en Kickstarter.
- Cierre: el Zero habla con lo que tienes cerca y el One con redes enteras. Hermanos sí, gemelos no.

## Fuentes (cada dato con al menos dos)

- Precio del Zero (169 USD): tienda oficial flipper.net y 1c3d.com ("Flipper Zero vs Flipper One").
- Cerca de un millón de Flipper Zero: Pavel Zhovner, fundador, en X (21 may 2026) y pasqualepillitteri.it (anuncio del Flipper One). Se dice "según su creador".
- Radio sub-GHz, NFC 13.56 MHz, RFID 125 kHz, infrarrojo, mascota virtual (delfín): Wikipedia (Flipper Zero), flipper.net y 1c3d.com.
- Canadá 2024: Wikipedia (ISED anunció la intención de prohibirlo en febrero de 2024 y el 20 de marzo de 2024 dijo que restringiría el uso ilegítimo en lugar de prohibir el aparato) y Malwarebytes ("Canada revisits decision to ban Flipper Zero").
- Códigos rodantes: BleepingComputer (9 feb 2024) y Jalopnik (12 feb 2024), con la declaración de Flipper Devices.
- Flipper One (anunciado el 21 may 2026; RK3576 de 8 núcleos, 8 GB, NPU, 2 Ethernet gigabit, wifi, HDMI, M.2 para 5G/SSD, Linux; "no reemplaza al Zero"): CNX Software (21 may 2026), Tom's Hardware (21 may 2026) e iXBT (5 nov 2026).
- Potencia parecida a una Raspberry Pi 5: Tom's Hardware ("roughly comparable") e iXBT (la empresa dice que la supera).
- Router y VPN: iXBT (5 nov 2026) y CNX Software ("networking multi-tool").
- Reservas (20 USD) y precio desde 379 USD en Kickstarter: Habr (3 nov 2026) e iXBT (5 nov 2026).

## Animación (más enganchadora)

Canvas 2D filmado con Playwright (`film.py`). Novedades frente a los videos anteriores:
- Subtítulos palabra por palabra sincronizados con la voz (`palabras.py` reparte cada frase saltando las pausas reales); la palabra clave que se está diciendo se marca con una píldora amarilla.
- Cámara viva: zoom de golpe en cada palabra clave y sacudidas en los impactos (sellos, "ONE", "un millón").
- Transiciones glitch con separación RGB y cortes de franjas, además del destello con rayo de marca.
- Barra de progreso arriba, capítulos numerados (1 Zero · 2 Cómo funciona · 3 Polémica · 4 One · 5 Por qué ahora · Resumen), contadores animados ($169, 1 000 000, 2024, $379) y piso de rejilla en perspectiva.
- Aparatos dibujados como esquemas originales (sin logos ni réplicas del diseño real, sin la mascota).

## Efectos y música

Sintetizados con código (`audio.py`): glitch digital, zaps, golpes de sello, pings de radio, chirridos FSK, pitido NFC, alarma, error, tecleo, arpegios de "sube de nivel", caja registradora. Música original synthwave en La menor a 124 bpm con caída fuerte cuando aparece el Flipper One. En la mezcla, la música va a 0.24 (en vez de 0.18 de `motor/mix.sh`) porque es más rítmica.
