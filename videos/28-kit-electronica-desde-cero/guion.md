# Video 28 · Lo que compraría si empezara en la electrónica desde cero

Pedido directo del dueño en el chat el 9 de noviembre de 2026 a las 22:38 ("sube un video sobre esto es lo que compraría si tuviera que empezar eléctrica desde cero: kits de componentes, microcontroladores, protoboard, osciloscopio, cautín; explica el funcionamiento y pon links de compra de los mejores"), y después "en cuanto lo tengas súbelo" y "ni me preguntes, tú súbelo". Se interpretó "eléctrica" como electrónica, por la lista de cosas que pidió.
Voz: Carlos Garza (eleven_v4), toma 2 (110.9 s; la toma 1 seguía generándose). Se acortaron las pausas de más de 0.3 s y se aceleró 7 % (`voz/narracion.mp3`, 99.6 s). Video: 101.3 s.

## Guion

- Gancho: si hoy empezara en la electrónica desde cero, solo compraría estas cinco cosas, y te explico cómo funciona cada una.
- 1 · Kit de componentes: resistencias que frenan la corriente, LEDs que la vuelven luz, capacitores que guardan carga y transistores (interruptores que se activan con electricidad). El súper kit de Elegoo trae placa compatible con Arduino, sensores, motores y tutorial paso a paso.
- 2 · Microcontrolador: una computadora diminuta en un chip que lee sensores, ejecuta tu código y controla luces o motores. Empezar con el Arduino Uno del kit y pasar al ESP32 (2 núcleos a 240 MHz, wifi y bluetooth) cuando quieras internet.
- 3 · Protoboard de 830 puntos: por dentro cada fila de 5 agujeros está unida por una lámina de metal y los rieles de los lados llevan positivo y negativo; se arman circuitos sin soldar.
- 4 · Osciloscopio: el multímetro da un número, el osciloscopio dibuja el voltaje en el tiempo. Para empezar, uno de bolsillo 3 en 1 como el FNIRSI 2C23T (osciloscopio de 2 canales, multímetro y generador de señales).
- 5 · Cautín: la punta caliente derrite el estaño (funde cerca de los 200 °C) y al enfriarse une las piezas eléctricamente. El Pinecil se conecta por USB-C, llega a su temperatura en unos 12 segundos y sube hasta 400 °C. Nunca tocar la punta.
- Cierre: con estas cinco cosas ya puedes armar, programar, medir y soldar tu primer proyecto; los links de compra están en la descripción.

## Fuentes (cada dato con al menos dos)

- Contenido del ELEGOO UNO R3 Super Starter Kit (placa UNO R3 compatible con Arduino IDE, sensores, servo, motor de pasos y de CD, tutorial en PDF): manuals.plus (ASIN B01D8KOZF4) y shopsavvy.com ("What components are included in the ELEGOO UNO Project Super Starter Kit").
- ESP32: 2 núcleos a 240 MHz, wifi y bluetooth clásico y BLE: esp32.atomic14.com (ESP32 classic) y la hoja de datos de Espressif (ESP32 Dual-core 32-bit MCU, 2.4 GHz Wi-Fi + BT/BLE).
- Protoboard de 830 puntos: ELEGOO (Breadboard 830 Point Solderless Prototype PCB Board Kit). Filas de 5 agujeros unidas por una lámina o clip de metal, mitades separadas por el canal central y rieles de alimentación + y − a los lados: SunFounder (ESP32 Starter Kit · Breadboard) y Adafruit (AdaBox001 · Breadboard).
- FNIRSI 2C23T: osciloscopio de 2 canales a 10 MHz y 50 MS/s, multímetro y generador DDS (3 en 1), pantalla de 2.8 pulgadas: fnirsi.com/es/products/2c23t y elektor.com / proshop (FNIRSI 2C23T 3-in-1 Portable Oscilloscope, Multimeter & Signal Generator).
- Estaño: Sn63/Pb37 funde a unos 183 °C y el estaño sin plomo SAC a unos 217 °C ("cerca de los 200"): guiahardware.es (Aleaciones de estaño para soldar electrónica) y AIM Solder (hoja técnica Sn63/Pb37).
- Pinecil V2: USB-C PD de 12 a 20 V; temperatura de trabajo en unos 12 segundos; hasta 400 °C (puntas de 100 a 400 °C): pine64.org (Pinecil) y CNX Software (29 jul 2022, "Pinecil V2 soldering iron gets BL706…"); arnowelzel.de confirma unos 10 s hasta 350 °C y puntas para 400 °C.

## Links de compra (en la descripción)

1. Kit ELEGOO UNO R3 Super Starter: https://www.amazon.com.mx/s?k=ELEGOO+UNO+R3+Super+Starter+Kit
2. ESP32 (wifi + bluetooth): https://www.amazon.com.mx/s?k=ESP32+DevKit+USB-C
3. Protoboard de 830 puntos: https://www.amazon.com.mx/s?k=protoboard+830+puntos
4. Osciloscopio FNIRSI 2C23T: https://www.amazon.com.mx/s?k=FNIRSI+2C23T (tienda oficial: https://fnirsi.com/es/products/2c23t)
5. Cautín Pinecil V2, tienda oficial de PINE64: https://pine64.com/product-category/pinecil/

Son enlaces de búsqueda y de tiendas oficiales, no de afiliado.

## Animación

Canvas 2D filmado con Playwright (`film.py`), con el motor del video 27 (subtítulos palabra por palabra, cámara viva, glitch, barra de progreso y capítulos). Escenas nuevas: el 0 que se vuelve 5 con los cinco objetos en anillo; tarjetas de resistencia (corriente que se frena), LED que se enciende, capacitor que se carga y transistor con interruptor; la caja del kit que se llena; el chip con entradas, código y salidas; Arduino UNO → ESP32 con sus 2 núcleos encendiéndose; protoboard con contador de 830 y vista de rayos X de las láminas, los rieles y un circuito con LED; multímetro contra osciloscopio que dibuja la señal; osciloscopio de bolsillo con 2 canales; soldadura en macro (punta que se calienta, estaño que se derrite y brilla al enfriarse, corriente que pasa) y cautín de pluma con USB-C, cronómetro de 12 s y termómetro a 400 °C. Todos los aparatos son esquemas originales, sin logos.

## Efectos y música

Sintetizados con código (`audio.py`): whooshes, glitch, golpes, pops, ticks de contadores, tecleo, chispa, zumbido de advertencia. Música original en Re menor a 118 bpm con corte antes de "sin soldar" y caída fuerte ahí.
