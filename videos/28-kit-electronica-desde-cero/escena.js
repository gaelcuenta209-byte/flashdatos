// Flash Datos · video 28 · Lo que compraría si empezara en la electrónica desde cero
// Canvas 2D 1080x1920. render(t) dibuja el cuadro del segundo t.
// Mismo motor de animación del video 27 (subtítulos palabra por palabra, cámara viva, glitch, capítulos),
// con escenas nuevas: kit de componentes, microcontrolador, protoboard con rayos X, osciloscopio y cautín.
// Todos los aparatos están dibujados como esquemas originales (sin logos ni réplicas exactas de productos).
'use strict';
const W = 1080, H = 1920;
const C = document.getElementById('c'), g = C.getContext('2d');
const YEL = '#FFD84D', CYA = '#4FD8FF', WHT = '#FFFFFF', INK = '#070a16', PUR = '#B46BFF', RED = '#FF4D5E', GRN = '#46E08A', PINK = '#FF5FA2', GRY = '#8a94ad';
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, s) => a + (b - a) * s;
const ease = s => { s = clamp(s); return s * s * s * (s * (6 * s - 15) + 10); };
const easeOut = s => { s = clamp(s); return 1 - Math.pow(1 - s, 3); };
const backOut = s => { s = clamp(s); const c = 1.7; return 1 + (c + 1) * Math.pow(s - 1, 3) + c * Math.pow(s - 1, 2); };
const prog = (t, a, b) => clamp((t - a) / (b - a));
function fade(t, a, b, f = 0.25) { if (t < a || t > b) return 0; return Math.min(1, (t - a) / f, (b - t) / f); }
function hash(i, j = 0, k = 0) { let h = (i * 374761393 + j * 668265263 + k * 2246822519) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295; }
function rgb(hex) { const n = parseInt(hex.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
const rgba = (hex, a) => { const [r, gg, b] = rgb(hex); return `rgba(${r},${gg},${b},${a})`; };


// ---------------- tiempos ----------------
const SG = {}; TM.segments.forEach(s => SG[s.id] = s);
const PP = (id, k) => SG[id].parts[k];
const END = TM.end;
const norm = s => s.toLowerCase().replace(/[^0-9a-záéíóúñü$]/g, '');
function WT(id, needle, exact = false, n = 0) {
  let c = 0;
  for (const p of SG[id].parts) for (const [t, w] of p[3]) {
    const x = norm(w);
    if (exact ? x === needle : x.includes(needle)) { if (c === n) return t; c++; }
  }
  console.error('WT sin palabra: ' + id + ' ' + needle); return SG[id].t0;
}
const G0 = PP('gancho', 0), K0 = PP('kit', 0), K1 = PP('kit', 1), M0 = PP('micro', 0), M1 = PP('micro', 1);
const B0 = PP('proto', 0), B1 = PP('proto', 1), O0 = PP('osci', 0), O1 = PP('osci', 1), S0 = PP('cautin', 0), S1 = PP('cautin', 1), C0 = PP('cierre', 0);
const TR = [K0[0] - 0.22, M0[0] - 0.22, B0[0] - 0.22, O0[0] - 0.22, S0[0] - 0.22, C0[0] - 0.22, C0[1] + 0.22];
const ENDC = TR[6];
const SUB = { box: K1[0] - 0.1, esp: M1[0] - 0.1, xray: B1[0] - 0.1, hand: O1[0] - 0.1, pen: S1[0] - 0.1 };

// palabras clave
const T = {
  empezara: WT('gancho', 'empezara'), electronica: WT('gancho', 'electrónica'), cero: WT('gancho', 'cero'), cinco: WT('gancho', '5', true), cosas: WT('gancho', 'cosas'), funciona: WT('gancho', 'funciona'),
  kit: WT('kit', 'kit'), resist: WT('kit', 'resistencias'), frenan: WT('kit', 'frenan'), leds: WT('kit', 'leds'), luz: WT('kit', 'luz'), capa: WT('kit', 'capacitores'), carga: WT('kit', 'carga'),
  trans: WT('kit', 'transistores'), interr: WT('kit', 'interruptores'), elec: WT('kit', 'electricidad'),
  super: WT('kit', 'súper'), elegoo: WT('kit', 'elegoo'), arduino: WT('kit', 'arduino'), sensores: WT('kit', 'sensores'), motores: WT('kit', 'motores'), tutorial: WT('kit', 'tutorial'),
  micro: WT('micro', 'microcontrolador'), compu: WT('micro', 'computadora'), chip: WT('micro', 'chip'), lee: WT('micro', 'lee', true), ejecuta: WT('micro', 'ejecuta'), controla: WT('micro', 'controla', true),
  uno: WT('micro', 'uno', true), internet: WT('micro', 'internet'), esp: WT('micro', 'esp32'), nucleos: WT('micro', 'núcleos'), mhz: WT('micro', '240'), wifi: WT('micro', 'wifi'), bt: WT('micro', 'bluetooth'),
  proto: WT('proto', 'protoboard'), p830: WT('proto', '830'), puntos: WT('proto', 'puntos'),
  fila: WT('proto', 'fila'), cinco2: WT('proto', '5', true), lamina: WT('proto', 'lámina'), metal: WT('proto', 'metal'), rieles: WT('proto', 'rieles'), positivo: WT('proto', 'positivo'), negativo: WT('proto', 'negativo'),
  sin: WT('proto', 'sin', true), soldar: WT('proto', 'soldar'),
  osci: WT('osci', 'osciloscopio'), multi: WT('osci', 'multímetro'), numero: WT('osci', 'número'), dibuja: WT('osci', 'dibuja'), voltaje: WT('osci', 'voltaje'), tiempo: WT('osci', 'tiempo'), moverse: WT('osci', 'moverse'),
  bolsillo: WT('osci', 'bolsillo'), tres: WT('osci', '3', true), fnirsi: WT('osci', 'fnirsi'), canales: WT('osci', 'canales'), multi2: WT('osci', 'multímetro', false, 1), generador: WT('osci', 'generador'),
  cautin: WT('cautin', 'cautín'), caliente: WT('cautin', 'caliente'), estano: WT('cautin', 'estaño'), c200: WT('cautin', '200'), enfria: WT('cautin', 'enfriarse'), electricamente: WT('cautin', 'eléctricamente'),
  pinecil: WT('cautin', 'pinecil'), usbc: WT('cautin', 'usbc'), doce: WT('cautin', '12'), segundos: WT('cautin', 'segundos'), c400: WT('cautin', '400'), toques: WT('cautin', 'toques'),
  ccosas: WT('cierre', 'cosas'), armar: WT('cierre', 'armar'), programar: WT('cierre', 'programar'), medir: WT('cierre', 'medir'), soldar2: WT('cierre', 'soldar'), proyecto: WT('cierre', 'proyecto'),
  links: WT('cierre', 'links'), descripcion: WT('cierre', 'descripción'),
};
const at = (p, f) => p[0] + (p[1] - p[0]) * f;

// ---------------- recursos ----------------
window.READY = Promise.all([
  new FontFace('IB', 'url(fonts/Inter-Black.otf)').load().then(f => document.fonts.add(f)),
  new FontFace('IX', 'url(fonts/Inter-ExtraBold.otf)').load().then(f => document.fonts.add(f)),
]).then(() => true);

// ---------------- dibujo básico ----------------
function txt(s, x, y, size, fill, o = {}) {
  const font = o.font || 'IB';
  g.save();
  g.font = `${size}px ${font}`;
  if (o.maxW) { const w = g.measureText(s).width; if (w > o.maxW) { size *= o.maxW / w; g.font = `${size}px ${font}`; } }
  g.textAlign = o.align || 'center'; g.textBaseline = 'middle';
  g.globalAlpha *= (o.alpha ?? 1);
  const sw = o.stroke ?? Math.round(size * 0.1);
  if (o.glow) { g.shadowColor = o.glow; g.shadowBlur = o.glowR || 30; }
  if (sw > 0) { g.lineJoin = 'round'; g.strokeStyle = o.strokeCol || INK; g.lineWidth = sw * 2; g.strokeText(s, x, y); }
  g.shadowBlur = 0;
  g.fillStyle = fill; g.fillText(s, x, y);
  const w = g.measureText(s).width;
  g.restore();
  return { size, w };
}
function measure(s, size, font = 'IB') { g.save(); g.font = `${size}px ${font}`; const w = g.measureText(s).width; g.restore(); return w; }
function poly(pts, closed = true) { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); if (closed) g.closePath(); }
function line(x0, y0, x1, y1) { g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); }
function circle(x, y, r) { g.beginPath(); g.arc(x, y, Math.max(0.01, r), 0, Math.PI * 2); }
function rr(x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function bolt(cx, cy, s) {
  const p = [[0.58, 0.0], [0.12, 0.56], [0.44, 0.56], [0.30, 1.0], [0.88, 0.38], [0.55, 0.38], [0.74, 0.0]];
  poly(p.map(([x, y]) => [cx + (x - 0.5) * s, cy + (y - 0.5) * s]));
}
function check(x, y, s, col, w = 0.18) { g.save(); g.lineCap = 'round'; g.lineJoin = 'round'; g.strokeStyle = col; g.lineWidth = s * w; poly([[x - s * 0.45, y], [x - s * 0.12, y + s * 0.32], [x + s * 0.48, y - s * 0.36]], false); g.stroke(); g.restore(); }
function cross(x, y, s, col, w = 0.18) { g.save(); g.lineCap = 'round'; g.strokeStyle = col; g.lineWidth = s * w; line(x - s * 0.38, y - s * 0.38, x + s * 0.38, y + s * 0.38); line(x + s * 0.38, y - s * 0.38, x - s * 0.38, y + s * 0.38); g.restore(); }
// píldora con texto: aparece con rebote en t0
function pill(text, x, y, col, size, t, t0, o = {}) {
  if (t < t0 - 0.02) return;
  const e = backOut(prog(t, t0 - 0.02, t0 + 0.3)), a = prog(t, t0 - 0.02, t0 + 0.1) * (o.alpha ?? 1);
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a; g.translate(x, y); g.rotate(o.rot || 0); g.scale(e, e);
  g.font = `${size}px ${o.font || 'IB'}`;
  const tw = g.measureText(text).width, ic = o.icon ? size * 1.05 : 0;
  const w = tw + size * 1.1 + ic, h = size * 1.55;
  rr(-w / 2, -h / 2, w, h, h / 2);
  if (o.solid) { g.shadowColor = col; g.shadowBlur = 30; g.fillStyle = col; g.fill(); g.shadowBlur = 0; g.lineWidth = 5; g.strokeStyle = INK; g.stroke(); }
  else { g.fillStyle = 'rgba(5,8,22,0.86)'; g.fill(); g.lineWidth = 5; g.strokeStyle = col; g.shadowColor = col; g.shadowBlur = 24; g.stroke(); g.shadowBlur = 0; }
  const fc = o.solid ? INK : col;
  if (o.icon === 'check') check(-w / 2 + size * 0.55 + ic * 0.45, 0, size * 0.8, fc, 0.2);
  if (o.icon === 'cross') cross(-w / 2 + size * 0.55 + ic * 0.45, 0, size * 0.75, fc, 0.2);
  if (o.icon === 'dot') { circle(-w / 2 + size * 0.55 + ic * 0.4, 0, size * 0.26); g.fillStyle = (Math.floor(t * 3) % 2) ? fc : rgba(fc, 0.3); g.fill(); }
  g.fillStyle = fc; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, ic / 2, size * 0.04);
  g.restore();
}
// sello de goma que se estampa
function stamp(text, x, y, size, col, t, t0, rot = -0.2, alpha = 1) {
  if (t < t0 - 0.12) return;
  const s = prog(t, t0 - 0.12, t0);
  const sc = lerp(2.6, 1, easeOut(s)) + (t > t0 ? 0.06 * Math.exp(-(t - t0) / 0.08) : 0);
  g.save(); g.globalAlpha *= s * alpha; g.translate(x, y); g.rotate(rot); g.scale(sc, sc);
  g.font = `${size}px IB`; const w = g.measureText(text).width + size * 0.8, h = size * 1.45;
  g.shadowColor = col; g.shadowBlur = 30;
  rr(-w / 2, -h / 2, w, h, 16); g.lineWidth = 12; g.strokeStyle = col; g.stroke(); g.shadowBlur = 0;
  rr(-w / 2 + 14, -h / 2 + 14, w - 28, h - 28, 8); g.lineWidth = 4; g.stroke();
  g.fillStyle = 'rgba(40,0,8,0.55)'; rr(-w / 2, -h / 2, w, h, 16); g.fill();
  g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 0, size * 0.05);
  g.restore();
}
// contador que sube
function counter(t, t0, t1, v0, v1) { const s = easeOut(prog(t, t0, t1)); return Math.round(lerp(v0, v1, s)); }
const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

// ---------------- fondo ----------------
const BG = document.createElement('canvas'); BG.width = W; BG.height = H;
{ const b = BG.getContext('2d'); const gr = b.createRadialGradient(540, 820, 40, 540, 900, 1400);
  gr.addColorStop(0, '#162a6c'); gr.addColorStop(0.45, '#0a1642'); gr.addColorStop(1, '#02050f'); b.fillStyle = gr; b.fillRect(0, 0, W, H); }
const VIG = document.createElement('canvas'); VIG.width = W; VIG.height = H;
{ const b = VIG.getContext('2d'); const gr = b.createRadialGradient(540, 900, 500, 540, 900, 1250);
  gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,0.6)'); b.fillStyle = gr; b.fillRect(0, 0, W, H);
  b.fillStyle = 'rgba(0,0,0,0.07)'; for (let y = 0; y < H; y += 4) b.fillRect(0, y, W, 1.5); }
function drawBG(t, acc = CYA, tint = null) {
  g.drawImage(BG, 0, 0);
  if (tint) { g.fillStyle = tint; g.fillRect(0, 0, W, H); }
  const hz = 1210;
  // resplandor del horizonte
  const hg = g.createLinearGradient(0, hz - 160, 0, hz + 60);
  hg.addColorStop(0, rgba(acc, 0)); hg.addColorStop(0.75, rgba(acc, 0.16)); hg.addColorStop(1, rgba(acc, 0));
  g.fillStyle = hg; g.fillRect(0, hz - 160, W, 220);
  g.save(); g.lineWidth = 2;
  for (let i = -16; i <= 16; i++) { g.strokeStyle = rgba(acc, 0.13); line(540 + i * 16, hz, 540 + i * 230, H); }
  for (let k = 0; k < 16; k++) {
    const f = ((k + t * 1.4) % 16) / 16, y = hz + (H - hz) * f * f;
    g.strokeStyle = rgba(acc, 0.03 + 0.24 * f); g.lineWidth = 1 + 2 * f; line(0, y, W, y);
  }
  g.restore();
  // partículas que suben
  for (let i = 0; i < 70; i++) {
    const sp = 25 + 70 * hash(i, 2), x = hash(i, 1) * W + 30 * Math.sin(t * 0.6 + i);
    const y = ((hash(i, 3) * H - t * sp) % H + H) % H;
    const a = (0.25 + 0.5 * hash(i, 4)) * (0.6 + 0.4 * Math.sin(t * 3 + i * 1.7));
    circle(x, y, 1.2 + 2.6 * hash(i, 5)); g.fillStyle = rgba(i % 3 ? acc : WHT, a * 0.7); g.fill();
  }
}

// ---------------- cámara viva ----------------
const PUNCH = [], SHAKE = [], GLITCH = [];
for (const s of TM.segments) for (const p of s.parts) for (const [t, w] of p[3]) if (isHL(w)) PUNCH.push([t, 0.022]);
function camera(t) {
  let z = 1 + 0.014 * Math.sin(t * 0.8) + 0.006 * Math.sin(t * 2.1);
  for (const [tp, a] of PUNCH) { const d = t - tp; if (d > -0.04 && d < 0.8) z += a * (d < 0 ? (d + 0.04) / 0.04 : Math.exp(-d / 0.16)); }
  let sx = 0, sy = 0;
  for (const [ts, a] of SHAKE) { const d = t - ts; if (d >= 0 && d < 0.6) { const k = a * Math.exp(-d / 0.12); const f = Math.floor(t * 60); sx += k * (hash(f, 7) - 0.5) * 2; sy += k * (hash(f, 9) - 0.5) * 2; } }
  return { z, sx, sy };
}
function addShake(t, a) { SHAKE.push([t, a]); }

// ---------------- glitch RGB y destello de marca ----------------
const OFF = document.createElement('canvas'); OFF.width = W; OFF.height = H; const og = OFF.getContext('2d');
const CR = document.createElement('canvas'); CR.width = W; CR.height = H; const cr = CR.getContext('2d');
const CB = document.createElement('canvas'); CB.width = W; CB.height = H; const cb = CB.getContext('2d');
function glitchAmount(t) {
  let a = 0;
  for (const [tg, s] of GLITCH) { const d = t - tg; if (d > -0.16 && d < 0.26) a = Math.max(a, s * (d < 0 ? 1 + d / 0.16 : 1 - d / 0.26)); }
  return a;
}
function applyGlitch(t, amt) {
  og.setTransform(1, 0, 0, 1, 0, 0); og.globalCompositeOperation = 'copy'; og.drawImage(C, 0, 0); og.globalCompositeOperation = 'source-over';
  for (const [cx, col] of [[cr, '#ff0000'], [cb, '#00ffff']]) { cx.globalCompositeOperation = 'copy'; cx.drawImage(OFF, 0, 0); cx.globalCompositeOperation = 'multiply'; cx.fillStyle = col; cx.fillRect(0, 0, W, H); cx.globalCompositeOperation = 'source-over'; }
  const dx = 34 * amt, f = Math.floor(t * 30);
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0);
  g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
  g.drawImage(CR, -dx, 0); g.globalCompositeOperation = 'lighter'; g.drawImage(CB, dx, dx * 0.3); g.globalCompositeOperation = 'source-over';
  const n = Math.round(4 + 10 * amt);
  for (let k = 0; k < n; k++) {
    const y = hash(f, k, 1) * H, h = 12 + hash(f, k, 2) * 150 * amt, o = (hash(f, k, 3) - 0.5) * 260 * amt;
    g.drawImage(OFF, 0, y, W, h, o, y, W, h);
    if (hash(f, k, 4) < 0.3) { g.fillStyle = rgba(hash(f, k, 5) < 0.5 ? CYA : PINK, 0.25 * amt); g.fillRect(0, y, W, Math.min(h, 8)); }
  }
  g.restore();
}
function flashAlpha(t) {
  let a = 0;
  for (const tf of TR) { const d = t - tf; if (d >= -0.05 && d < 0) a = Math.max(a, (d + 0.05) / 0.05); else if (d >= 0 && d < 0.4) a = Math.max(a, Math.exp(-d / 0.075)); }
  return a;
}
TR.forEach((tt, i) => GLITCH.push([tt, 1]));
GLITCH.push([T.cero, 0.5], [T.cinco, 0.6], [T.toques, 0.5]);
addShake(T.cero, 22); addShake(T.cinco, 26); addShake(T.p830, 14); addShake(T.soldar, 18); addShake(T.c400, 14); addShake(T.toques, 26); addShake(T.links, 14);

// ---------------- subtítulos palabra por palabra ----------------
function isHL(w) { const core = w.replace(/[.,:;…?!¡¿()"]/g, ''); return /\d/.test(core) || (core.length >= 2 && /[A-ZÁÉÍÓÚÑ]/.test(core) && core === core.toUpperCase()); }
const CHUNKS = [];
for (const s of TM.segments) for (const p of s.parts) {
  const ws = p[3]; let cur = [];
  const flush = () => { if (cur.length) CHUNKS.push({ words: cur, pend: p[1] }); cur = []; };
  ws.forEach(([t, w]) => {
    cur.push({ t, w, hl: isHL(w) });
    const len = cur.map(x => x.w).join(' ').length;
    if (cur.length === 3 || /[.,:…?!]$/.test(w) || len > 15) flush();
  });
  flush();
}
CHUNKS.forEach((c, i) => {
  c.t0 = c.words[0].t - 0.06;
  const nx = CHUNKS[i + 1];
  const last = c.words[c.words.length - 1].t;
  c.t1 = nx && nx.words[0].t - 0.06 - last < 1.0 ? nx.words[0].t - 0.06 : Math.min(last + 0.9, c.pend + 0.25);
});
const CAP_Y = 1470;
function drawCaption(t) {
  const c = CHUNKS.find(c => t >= c.t0 && t < c.t1); if (!c) return;
  let size = 90;
  const sp = () => size * 0.34;
  let wsz = c.words.map(x => measure(x.w, size)); let tot = wsz.reduce((a, b) => a + b, 0) + sp() * (c.words.length - 1);
  if (tot > 900) { const k = 900 / tot; size *= k; wsz = wsz.map(v => v * k); tot = 900; }
  let x = W / 2 - tot / 2; const s2 = sp();
  let active = -1; c.words.forEach((wd, i) => { if (t >= wd.t - 0.04) active = i; });
  const entry = backOut(prog(t, c.t0, c.t0 + 0.2));
  c.words.forEach((wd, i) => {
    const cxw = x + wsz[i] / 2; x += wsz[i] + s2;
    if (t < wd.t - 0.04) return;
    const k = prog(t, wd.t - 0.04, wd.t + 0.12);
    const sc = lerp(1.45, 1, easeOut(k)) * (i === active ? 1.06 : 1) * lerp(0.9, 1, entry);
    const yy = CAP_Y - (1 - easeOut(k)) * 26;
    g.save(); g.translate(cxw, yy); g.scale(sc, sc); g.globalAlpha = clamp(k * 3);
    if (wd.hl && i === active) {
      g.rotate(-0.035);
      rr(-wsz[i] / 2 - 16, -size * 0.62, wsz[i] + 32, size * 1.2, 18);
      g.fillStyle = YEL; g.shadowColor = YEL; g.shadowBlur = 30; g.fill(); g.shadowBlur = 0;
      g.lineWidth = 7; g.strokeStyle = INK; g.stroke();
      txt(wd.w, 0, size * 0.03, size, INK, { stroke: 0 });
    } else txt(wd.w, 0, 0, size, wd.hl ? YEL : WHT, { stroke: 10 });
    g.restore();
  });
}

// ---------------- marca, progreso y capítulos ----------------
function drawWatermark() {
  g.save();
  const tw = measure('FLASH DATOS', 38); const x = W / 2 - (tw + 40) / 2;
  bolt(x + 14, 212, 40); g.fillStyle = 'rgba(255,216,77,0.95)'; g.fill();
  g.globalAlpha = 0.88; txt('FLASH DATOS', x + 40, 212, 38, WHT, { align: 'left', stroke: 4 });
  g.restore();
}
function drawProgress(t) {
  const f = clamp(t / ENDC);
  g.fillStyle = 'rgba(255,255,255,0.14)'; g.fillRect(0, 0, W, 10);
  g.save(); g.shadowColor = YEL; g.shadowBlur = 18; g.fillStyle = YEL; g.fillRect(0, 0, W * f, 10); g.restore();
  circle(W * f, 5, 9); g.fillStyle = WHT; g.fill();
}
const CHAPTERS = [
  [TR[0], TR[1], '1', 'KIT DE COMPONENTES', CYA], [TR[1], TR[2], '2', 'MICROCONTROLADOR', PUR], [TR[2], TR[3], '3', 'PROTOBOARD', GRN],
  [TR[3], TR[4], '4', 'OSCILOSCOPIO', YEL], [TR[4], TR[5], '5', 'CAUTÍN', '#FF9A3D'], [TR[5], TR[6], 'ok', 'TU PRIMER PROYECTO', GRN]];
function drawChapter(t) {
  for (const [a, b, n, title, col] of CHAPTERS) {
    if (t < a + 0.05 || t >= b) continue;
    const e = backOut(prog(t, a + 0.08, a + 0.45)), al = Math.min(1, (b - t) / 0.15);
    g.save(); g.globalAlpha = al;
    const size = 40; const tw = measure(title, size, 'IX'); const w = tw + 120, h = 70;
    const x0 = lerp(-w - 40, W / 2 - w / 2, e), y = 300;
    rr(x0, y - h / 2, w, h, h / 2); g.fillStyle = 'rgba(5,8,22,0.85)'; g.fill(); g.lineWidth = 4; g.strokeStyle = col; g.stroke();
    circle(x0 + 38, y, 26); g.fillStyle = col; g.fill();
    if (n === 'ok') check(x0 + 38, y + 1, 30, INK, 0.22); else txt(n, x0 + 38, y + 2, 34, INK, { stroke: 0 });
    txt(title, x0 + 76, y + 2, size, WHT, { font: 'IX', align: 'left', stroke: 0 });
    g.restore();
  }
}

// ---------------- aparatos (esquemas originales) ----------------
function device(x, y, s, o, w, h, r, depth, cols, faceFn) {
  const yaw = o.yaw || 0, cx = Math.cos(yaw);
  g.save(); g.globalAlpha *= (o.alpha ?? 1); g.translate(x, y); g.rotate(o.rot || 0); g.scale(s, s);
  if (!o.noShadow) { g.save(); g.globalAlpha *= 0.4; const sg = g.createRadialGradient(0, h / 2 + depth + 40, 10, 0, h / 2 + depth + 40, w * 0.55); sg.addColorStop(0, 'rgba(0,0,0,0.9)'); sg.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = sg; g.fillRect(-w, h / 2, 2 * w, depth + 120); g.restore(); }
  const dx = -Math.sin(yaw) * depth, dy = depth * 0.85, N = 12;
  for (let k = N; k >= 1; k--) { g.save(); g.translate(dx * k / N, dy * k / N); g.scale(cx, 1); rr(-w / 2, -h / 2, w, h, r); g.fillStyle = k === N ? cols.edgeDark : cols.edge; g.fill(); g.restore(); }
  g.save(); g.translate(dx, dy); g.scale(cx, 1); rr(-w / 2, -h / 2, w, h, r); g.strokeStyle = rgba(cols.rim, 0.5); g.lineWidth = 3; g.stroke(); g.restore();
  g.save(); g.scale(cx, 1);
  if (o.glow) { g.shadowColor = cols.rim; g.shadowBlur = 50 * o.glow; }
  rr(-w / 2, -h / 2, w, h, r);
  const gr = g.createLinearGradient(0, -h / 2, 0, h / 2); gr.addColorStop(0, cols.faceTop); gr.addColorStop(1, cols.faceBot); g.fillStyle = gr; g.fill(); g.shadowBlur = 0;
  g.lineWidth = 5; g.strokeStyle = cols.rim; g.stroke();
  faceFn();
  // brillo que barre la cara
  const sh = o.shine ?? ((T_NOW * 0.35) % 1.6);
  if (sh >= 0 && sh <= 1) { g.save(); rr(-w / 2, -h / 2, w, h, r); g.clip(); g.rotate(-0.5); const sx = lerp(-w, w, sh); const lg = g.createLinearGradient(sx - 90, 0, sx + 90, 0); lg.addColorStop(0, 'rgba(255,255,255,0)'); lg.addColorStop(0.5, 'rgba(255,255,255,0.16)'); lg.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = lg; g.fillRect(-w * 2, -h * 2, w * 4, h * 4); g.restore(); }
  g.restore(); g.restore();
}
function screenArea(x, y, w, h, r, bg, fn) {
  g.save(); rr(x, y, w, h, r); g.clip(); g.fillStyle = bg; g.fillRect(x, y, w, h); g.translate(x, y);
  if (fn) fn(w, h);
  g.fillStyle = 'rgba(0,0,0,0.2)'; for (let yy = 0; yy < h; yy += 4) g.fillRect(0, yy, w, 1.5);
  const gl = g.createLinearGradient(0, 0, w, h); gl.addColorStop(0, 'rgba(255,255,255,0.12)'); gl.addColorStop(0.5, 'rgba(255,255,255,0)'); g.fillStyle = gl; g.fillRect(0, 0, w, h);
  g.restore();
}
let T_NOW = 0;

function waveRings(x, y, col, t, t0, n = 3, maxR = 520, period = 0.55, a0 = 0.8, thick = 6) {
  if (t < t0) return;
  g.save(); g.lineWidth = thick;
  for (let k = 0; k < 12; k++) {
    const tk = t0 + k * period; if (t < tk) break;
    const f = (t - tk) / (period * n); if (f > 1) continue;
    circle(x, y, 40 + f * maxR); g.strokeStyle = rgba(col, a0 * (1 - f)); g.stroke();
  }
  g.restore();
}
function sparkle(x, y, s, col, a) { g.save(); g.translate(x, y); g.globalAlpha *= a; g.fillStyle = col; g.beginPath(); for (let k = 0; k < 8; k++) { const r = k % 2 ? s * 0.25 : s; const an = k * Math.PI / 4; g.lineTo(Math.cos(an) * r, Math.sin(an) * r); } g.closePath(); g.fill(); g.restore(); }
function burst(x, y, t, t0, col, n = 10, R = 220) {
  const f = prog(t, t0, t0 + 0.6); if (f <= 0 || f >= 1) return;
  for (let k = 0; k < n; k++) { const an = k / n * Math.PI * 2 + hash(k, Math.floor(t0 * 10)) * 0.5; const r = easeOut(f) * R * (0.7 + 0.5 * hash(k, 3)); sparkle(x + Math.cos(an) * r, y + Math.sin(an) * r, 18 * (1 - f) + 6, k % 2 ? col : WHT, 1 - f); }
}
function packet(x0, y0, x1, y1, t, speed, col, n = 3, size = 9) {
  for (let k = 0; k < n; k++) { const f = ((t * speed + k / n) % 1); circle(lerp(x0, x1, f), lerp(y0, y1, f), size); g.fillStyle = col; g.shadowColor = col; g.shadowBlur = 14; g.fill(); g.shadowBlur = 0; }
}
// texto de señal que viaja (código)
function codeTag(text, x, y, col, a = 1, s = 1) {
  g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s); g.font = '46px IX';
  const w = g.measureText(text).width + 40;
  rr(-w / 2, -34, w, 68, 14); g.fillStyle = 'rgba(5,8,22,0.9)'; g.fill(); g.lineWidth = 4; g.strokeStyle = col; g.stroke();
  g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 0, 2); g.restore();
}


// ---------------- ayudas ----------------
const ORA = '#FF9A3D', SLV = '#cfd6e2', COP = '#d4893a';
function pathPoint(pts, f) {
  let L = 0; const seg = [];
  for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); L += d; }
  let r = clamp(f) * L;
  for (let i = 0; i < seg.length; i++) { if (r <= seg[i]) { const u = seg[i] ? r / seg[i] : 0; return [lerp(pts[i][0], pts[i + 1][0], u), lerp(pts[i][1], pts[i + 1][1], u)]; } r -= seg[i]; }
  return pts[pts.length - 1];
}
function flow(pts, t, speed, col, n = 8, size = 9, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a; g.fillStyle = col; g.shadowColor = col; g.shadowBlur = 16;
  for (let k = 0; k < n; k++) { const f = ((t * speed + k / n) % 1 + 1) % 1; const [x, y] = pathPoint(pts, f); circle(x, y, size); g.fill(); }
  g.restore();
}
function pop(t, t0, d = 0.35) { return backOut(prog(t, t0 - 0.05, t0 + d)); }
function panel(x, y, w, h, col, a = 1, title = null, tsize = 40) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  rr(x - w / 2, y - h / 2, w, h, 30); g.fillStyle = 'rgba(6,10,28,0.82)'; g.fill();
  g.lineWidth = 5; g.strokeStyle = col; g.shadowColor = col; g.shadowBlur = 22; g.stroke(); g.shadowBlur = 0;
  if (title) txt(title, x, y - h / 2 + tsize * 0.95, tsize, col, { font: 'IX', stroke: 0 });
  g.restore();
}
function arrow(x0, y0, x1, y1, col, a = 1, w = 10) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a; g.strokeStyle = col; g.fillStyle = col; g.lineWidth = w; g.lineCap = 'round';
  const an = Math.atan2(y1 - y0, x1 - x0); line(x0, y0, x1 - Math.cos(an) * w * 2, y1 - Math.sin(an) * w * 2);
  g.translate(x1, y1); g.rotate(an); poly([[0, 0], [-w * 3.2, -w * 2.2], [-w * 3.2, w * 2.2]]); g.fill();
  g.restore();
}

// ---------------- componentes ----------------
function resistor(x, y, s, o = {}) {
  g.save(); g.translate(x, y); g.rotate(o.rot || 0); g.scale(s, s); g.globalAlpha *= (o.alpha ?? 1);
  g.strokeStyle = '#b9c1cf'; g.lineWidth = 9; g.lineCap = 'round'; line(-210, 0, 210, 0);
  if (o.glow) { g.shadowColor = YEL; g.shadowBlur = 40 * o.glow; }
  rr(-120, -44, 240, 88, 44); const gr = g.createLinearGradient(0, -44, 0, 44); gr.addColorStop(0, '#f2d7a6'); gr.addColorStop(1, '#b78b52'); g.fillStyle = gr; g.fill(); g.shadowBlur = 0;
  g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
  g.save(); rr(-120, -44, 240, 88, 44); g.clip();
  [['#7a4a1e', -72], ['#141414', -38], ['#e0362c', -4], ['#d9b24a', 70]].forEach(([c, bx]) => { g.fillStyle = c; g.fillRect(bx - 10, -50, 20, 100); });
  g.fillStyle = 'rgba(255,255,255,0.25)'; g.fillRect(-110, -32, 220, 10);
  g.restore(); g.restore();
}
function led(x, y, s, col, on = 0, o = {}) {
  g.save(); g.translate(x, y); g.scale(s, s); g.globalAlpha *= (o.alpha ?? 1);
  g.strokeStyle = '#b9c1cf'; g.lineWidth = 9; g.lineCap = 'round'; line(-24, 40, -24, 175); line(24, 40, 24, 145);
  if (on > 0) { const rg = g.createRadialGradient(0, -30, 10, 0, -30, 300); rg.addColorStop(0, rgba(col, 0.6 * on)); rg.addColorStop(1, rgba(col, 0)); g.fillStyle = rg; g.fillRect(-300, -330, 600, 600); }
  rr(-68, 26, 136, 24, 8); g.fillStyle = rgba(col, 0.55 + 0.45 * on); g.fill();
  g.beginPath(); g.moveTo(-56, 30); g.lineTo(-56, -40); g.arc(0, -40, 56, Math.PI, 0); g.lineTo(56, 30); g.closePath();
  if (on > 0) { g.shadowColor = col; g.shadowBlur = 50 * on; }
  g.fillStyle = rgba(col, 0.35 + 0.65 * on); g.fill(); g.shadowBlur = 0; g.lineWidth = 4; g.strokeStyle = col; g.stroke();
  g.beginPath(); g.ellipse(-22, -50, 10, 26, -0.2, 0, Math.PI * 2); g.fillStyle = 'rgba(255,255,255,0.55)'; g.fill();
  g.restore();
}
function capacitor(x, y, s, charge) {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = '#b9c1cf'; g.lineWidth = 9; g.lineCap = 'round'; line(-24, 110, -24, 200); line(24, 110, 24, 180);
  const gr = g.createLinearGradient(-62, 0, 62, 0); gr.addColorStop(0, '#173a7c'); gr.addColorStop(0.5, '#3a6fd0'); gr.addColorStop(1, '#173a7c');
  rr(-62, -120, 124, 236, 24); g.fillStyle = gr; g.fill();
  g.fillStyle = 'rgba(220,226,236,0.85)'; g.fillRect(28, -112, 22, 220);
  for (let i = 0; i < 4; i++) { g.fillStyle = '#173a7c'; g.fillRect(33, -90 + i * 50, 12, 6); }
  g.beginPath(); g.ellipse(0, -118, 60, 14, 0, 0, Math.PI * 2); g.fillStyle = '#c7ccd6'; g.fill();
  rr(96, -120, 36, 236, 12); g.lineWidth = 4; g.strokeStyle = rgba(YEL, 0.6); g.stroke();
  if (charge > 0) { const hh = 228 * charge; rr(100, 112 - hh, 28, hh, 8); g.fillStyle = YEL; g.shadowColor = YEL; g.shadowBlur = 20; g.fill(); g.shadowBlur = 0; }
  g.restore();
}
function transistor(x, y, s) {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = '#b9c1cf'; g.lineWidth = 9; g.lineCap = 'round'; for (const lx of [-34, 0, 34]) line(lx, 50, lx, 190);
  g.beginPath(); g.moveTo(-70, 60); g.lineTo(-70, -20); g.arc(0, -20, 70, Math.PI, 0); g.lineTo(70, 60); g.closePath();
  g.fillStyle = '#1d2029'; g.fill(); g.lineWidth = 4; g.strokeStyle = '#59607a'; g.stroke();
  txt('NPN', 0, 10, 32, '#8a94ad', { font: 'IX', stroke: 0 });
  g.restore();
}
function switchIcon(x, y, s, col, closed) {
  g.save(); g.translate(x, y); g.scale(s, s); g.lineCap = 'round';
  g.strokeStyle = col; g.lineWidth = 10; line(-120, 0, -60, 0); line(60, 0, 120, 0);
  circle(-60, 0, 13); g.fillStyle = col; g.fill(); circle(60, 0, 13); g.fill();
  g.save(); g.translate(-60, 0); g.rotate(lerp(-0.62, 0, closed)); g.lineWidth = 13; g.strokeStyle = closed > 0.9 ? YEL : col; if (closed > 0.9) { g.shadowColor = YEL; g.shadowBlur = 24; } line(0, 0, 122, 0); g.restore();
  g.restore();
}
function ultrasonic(x, y, s) {
  g.save(); g.translate(x, y); g.scale(s, s);
  rr(-130, -60, 260, 120, 10); g.fillStyle = '#1a6fb0'; g.fill();
  for (const cx of [-62, 62]) { circle(cx, 0, 50); g.fillStyle = '#c7ccd6'; g.fill(); circle(cx, 0, 38); g.fillStyle = '#2a2f3a'; g.fill(); g.strokeStyle = 'rgba(200,206,214,0.35)'; g.lineWidth = 2; for (let i = -30; i <= 30; i += 10) line(cx + i, -30, cx + i, 30); }
  g.restore();
}
function servo(x, y, s, a) {
  g.save(); g.translate(x, y); g.scale(s, s);
  rr(-112, -14, 224, 28, 6); g.fillStyle = '#2a63c9'; g.fill(); rr(-80, -55, 160, 110, 12); g.fill();
  circle(-38, -55, 28); g.fillStyle = '#e9ecf2'; g.fill();
  g.save(); g.translate(-38, -55); g.rotate(a); rr(-15, -88, 30, 106, 15); g.fillStyle = '#ffffff'; g.fill(); g.restore();
  g.restore();
}
function dcMotor(x, y, s, a) {
  g.save(); g.translate(x, y); g.scale(s, s);
  rr(-80, -52, 130, 104, 44); g.fillStyle = '#c7ccd6'; g.fill(); rr(46, -30, 30, 60, 8); g.fillStyle = '#9aa2b1'; g.fill();
  g.strokeStyle = '#e8eaee'; g.lineWidth = 8; line(76, 0, 112, 0);
  g.save(); g.translate(122, 0); g.rotate(a); for (let k = 0; k < 3; k++) { g.rotate(Math.PI * 2 / 3); g.fillStyle = rgba(CYA, 0.9); g.beginPath(); g.ellipse(0, -44, 15, 40, 0, 0, Math.PI * 2); g.fill(); } g.restore();
  g.restore();
}
function book(x, y, s, col) {
  g.save(); g.translate(x, y); g.scale(s, s); g.fillStyle = '#0b1026'; g.lineWidth = 6; g.strokeStyle = col; g.lineJoin = 'round';
  poly([[0, -60], [-112, -82], [-112, 70], [0, 92]]); g.fill(); g.stroke(); poly([[0, -60], [112, -82], [112, 70], [0, 92]]); g.fill(); g.stroke();
  g.lineWidth = 4; for (let i = 0; i < 4; i++) { line(-92, -46 + i * 28, -18, -34 + i * 28); line(18, -34 + i * 28, 92, -46 + i * 28); }
  g.restore();
}
function sunIcon(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); circle(0, 0, 34); g.fillStyle = col; g.fill(); g.strokeStyle = col; g.lineWidth = 9; g.lineCap = 'round'; for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4; line(Math.cos(a) * 50, Math.sin(a) * 50, Math.cos(a) * 68, Math.sin(a) * 68); } g.restore(); }
function thermoIcon(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); rr(-16, -64, 32, 96, 16); g.lineWidth = 7; g.strokeStyle = col; g.stroke(); circle(0, 44, 24); g.fillStyle = col; g.fill(); g.fillRect(-6, -30, 12, 64); g.restore(); }
function buttonIcon(x, y, s, col, press) { g.save(); g.translate(x, y); g.scale(s, s); rr(-56, -10, 112, 42, 8); g.fillStyle = '#3a3f4c'; g.fill(); circle(0, -12 + press * 10, 32); g.fillStyle = col; g.fill(); g.restore(); }
function motorIcon(x, y, s, col, a) { g.save(); g.translate(x, y); g.scale(s, s); circle(0, 0, 72); g.fillStyle = '#0b1026'; g.fill(); g.lineWidth = 7; g.strokeStyle = col; g.stroke(); g.rotate(a); for (let k = 0; k < 3; k++) { g.rotate(Math.PI * 2 / 3); rr(-11, -62, 22, 54, 9); g.fillStyle = col; g.fill(); } circle(0, 0, 15); g.fillStyle = WHT; g.fill(); g.restore(); }
function qfp(x, y, s, col, glow = 0) {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = '#c9ced8'; g.lineWidth = 8; for (let i = -5; i <= 5; i++) { line(i * 25, -150, i * 25, -184); line(i * 25, 150, i * 25, 184); line(-150, i * 25, -184, i * 25); line(150, i * 25, 184, i * 25); }
  if (glow) { g.shadowColor = col; g.shadowBlur = 70 * glow; }
  rr(-150, -150, 300, 300, 18); g.fillStyle = '#16182a'; g.fill(); g.shadowBlur = 0; g.lineWidth = 6; g.strokeStyle = col; g.stroke();
  circle(-112, -112, 13); g.fillStyle = '#2a2e45'; g.fill();
  txt('MCU', 0, 4, 70, rgba(col, 0.95), { font: 'IX', stroke: 0 });
  g.restore();
}
function wifiIcon(x, y, s, col, t, a = 1) {
  if (a <= 0) return;
  g.save(); g.translate(x, y); g.scale(s, s); const A = g.globalAlpha * a; g.lineCap = 'round'; g.strokeStyle = col; g.lineWidth = 13; g.shadowColor = col; g.shadowBlur = 16;
  for (let k = 1; k <= 3; k++) { g.globalAlpha = A * ((Math.floor(t * 4) % 4) >= k ? 1 : 0.35); g.beginPath(); g.arc(0, 0, k * 38, -Math.PI * 0.78, -Math.PI * 0.22); g.stroke(); }
  g.globalAlpha = A; circle(0, 0, 11); g.fillStyle = col; g.fill(); g.restore();
}
function btIcon(x, y, s, col, a = 1) {
  if (a <= 0) return;
  g.save(); g.translate(x, y); g.scale(s, s); g.globalAlpha *= a; circle(0, 0, 58); g.fillStyle = col; g.shadowColor = col; g.shadowBlur = 24; g.fill(); g.shadowBlur = 0;
  g.strokeStyle = INK; g.lineWidth = 9; g.lineJoin = 'round'; g.lineCap = 'round'; poly([[-20, -18], [22, 20], [0, 40], [0, -40], [22, -20], [-20, 18]], false); g.stroke(); g.restore();
}

// ---------------- placas (esquemas originales, sin logos) ----------------
const UNOC = { faceTop: '#1a7fb8', faceBot: '#0d5a8a', edge: '#0a3e60', edgeDark: '#062a42', rim: '#6cc6f2' };
const ESPC = { faceTop: '#262d3a', faceBot: '#141922', edge: '#0e1218', edgeDark: '#07090d', rim: '#9aa6bd' };
function headerStrip(x, y, n, step) {
  g.fillStyle = '#0b0d12'; rr(x - 15, y - 15, step * (n - 1) + 30, 30, 4); g.fill();
  for (let i = 0; i < n; i++) { g.fillStyle = '#3d4352'; g.fillRect(x + i * step - 5, y - 5, 10, 10); }
}
function boardUno(x, y, s, o = {}) {
  device(x, y, s, o, 520, 380, 24, 16, UNOC, () => {
    headerStrip(-150, -158, 14, 26); headerStrip(-70, 158, 6, 26); headerStrip(110, 158, 6, 26);
    g.fillStyle = '#c7ccd6'; rr(-296, -150, 104, 92, 6); g.fill(); g.fillStyle = '#8f97a6'; rr(-284, -138, 80, 68, 4); g.fill();
    g.fillStyle = '#111317'; rr(-290, 56, 92, 84, 10); g.fill();
    g.fillStyle = '#b9c1cf'; for (let i = 0; i < 14; i++) { g.fillRect(-58 + i * 17.5, 32, 8, 14); g.fillRect(-58 + i * 17.5, 112, 8, 14); }
    g.fillStyle = '#16181e'; rr(-70, 42, 262, 74, 6); g.fill(); circle(-50, 79, 7); g.fillStyle = '#2b2f38'; g.fill();
    g.fillStyle = '#c7ccd6'; rr(-150, -6, 48, 24, 12); g.fill();
    const blink = o.blink ? (Math.floor(T_NOW * 4) % 2) : 0;
    circle(30, -92, 9); g.fillStyle = blink ? YEL : '#5a4a1a'; g.fill(); circle(62, -92, 9); g.fillStyle = GRN; g.fill();
    txt('UNO', 150, -76, 58, WHT, { font: 'IX', stroke: 0, alpha: 0.92 });
  });
}
function boardESP(x, y, s, o = {}) {
  device(x, y, s, o, 260, 560, 20, 14, ESPC, () => {
    g.save(); g.strokeStyle = '#d9b24a'; g.lineWidth = 6; g.beginPath(); g.moveTo(-90, -250);
    for (let i = 0; i < 6; i++) { const x0 = -90 + i * 30; g.lineTo(x0 + 15, -250); g.lineTo(x0 + 15, -226); g.lineTo(x0 + 30, -226); g.lineTo(x0 + 30, -250); }
    g.stroke(); g.restore();
    const sg = g.createLinearGradient(-95, -212, 95, -20); sg.addColorStop(0, '#eef1f5'); sg.addColorStop(1, '#9aa2b1'); g.fillStyle = sg; rr(-96, -212, 192, 192, 8); g.fill();
    txt('ESP32', 0, -162, 44, '#3a4150', { font: 'IX', stroke: 0 });
    const cores = o.cores ?? 0;
    for (let k = 0; k < 2; k++) {
      const on = clamp(cores - k); rr(-72 + k * 82, -112, 62, 62, 8);
      g.fillStyle = on > 0 ? rgba(YEL, 0.3 + 0.7 * on) : 'rgba(60,66,80,0.5)'; if (on > 0) { g.shadowColor = YEL; g.shadowBlur = 26 * on; } g.fill(); g.shadowBlur = 0;
      txt(String(k + 1), -41 + k * 82, -80, 34, on > 0 ? INK : '#6b7385', { stroke: 0 });
    }
    for (let i = 0; i < 15; i++) for (const px of [-112, 112]) { circle(px, -6 + i * 17.5, 6.5); g.fillStyle = '#d9b24a'; g.fill(); circle(px, -6 + i * 17.5, 2.8); g.fillStyle = '#111'; g.fill(); }
    g.fillStyle = '#0b0d12'; rr(-46, 60, 92, 72, 6); g.fill();
    g.fillStyle = '#c7ccd6'; rr(-82, 196, 38, 28, 5); g.fill(); rr(44, 196, 38, 28, 5); g.fill();
    rr(-38, 252, 76, 24, 12); g.fill();
  });
}

// ---------------- protoboard ----------------
const BBX = c => c < 5 ? -150 + 30 * c : 30 + 30 * (c - 5);
const BBY = r => -425 + 34 * r;
const RX = { lp: -245, ln: -215, rn: 215, rp: 245 };
const BB_PATH = [[RX.lp, BBY(3)], [BBX(0), BBY(3)], [BBX(2), BBY(3)], [BBX(2), BBY(9)], [BBX(4), BBY(9)], [BBX(4), BBY(11)], [BBX(0), BBY(11)], [RX.ln, BBY(11)]];
function breadboard(x, y, s, o = {}) {
  const xr = o.xray || 0;
  g.save(); g.translate(x, y); g.scale(s, s); g.globalAlpha *= (o.alpha ?? 1); const A = g.globalAlpha;
  g.globalAlpha = A * lerp(1, 0.5, xr); g.fillStyle = '#8e95a2'; rr(-270, -484, 560, 1000, 22); g.fill();
  g.globalAlpha = A * lerp(1, 0.24, xr);
  const gr = g.createLinearGradient(-280, 0, 280, 0); gr.addColorStop(0, '#f5f6f9'); gr.addColorStop(1, '#dde1e8'); g.fillStyle = gr; rr(-280, -500, 560, 1000, 22); g.fill();
  g.fillStyle = '#c3c8d1'; rr(-13, -480, 26, 960, 8); g.fill();
  g.globalAlpha = A;
  rr(-280, -500, 560, 1000, 22); g.lineWidth = 4; g.strokeStyle = xr > 0.5 ? rgba(CYA, 0.7) : '#aab0bc'; g.stroke();
  // líneas de los rieles
  g.lineWidth = 5; for (const [lx, col] of [[-268, '#e0363f'], [-192, '#2f6fe0'], [192, '#2f6fe0'], [268, '#e0363f']]) { g.strokeStyle = col; line(lx, -470, lx, 470); }
  txt('+', -268, -486, 30, '#e0363f', { stroke: 0 }); txt('−', -192, -486, 30, '#2f6fe0', { stroke: 0 }); txt('−', 192, -486, 30, '#2f6fe0', { stroke: 0 }); txt('+', 268, -486, 30, '#e0363f', { stroke: 0 });
  // láminas de metal (rayos X)
  if (xr > 0) {
    g.save(); g.globalAlpha = A * xr;
    const mg = g.createLinearGradient(0, -9, 0, 9); mg.addColorStop(0, '#f2f5fa'); mg.addColorStop(1, '#8d96a6');
    for (let r = 0; r < 26; r++) { g.fillStyle = mg; g.save(); g.translate(0, BBY(r)); rr(-164, -10, 148, 20, 8); g.fill(); rr(16, -10, 148, 20, 8); g.fill(); g.restore(); }
    for (const rx of [RX.lp, RX.ln, RX.rn, RX.rp]) { const rg = g.createLinearGradient(rx - 10, 0, rx + 10, 0); rg.addColorStop(0, '#f2f5fa'); rg.addColorStop(1, '#8d96a6'); g.fillStyle = rg; rr(rx - 10, -440, 20, 880, 8); g.fill(); }
    g.restore();
  }
  if (o.hlRow != null && o.hl > 0) {
    g.save(); g.globalAlpha = A * o.hl; g.shadowColor = YEL; g.shadowBlur = 30; g.fillStyle = YEL;
    rr(-168, BBY(o.hlRow) - 13, 156, 26, 10); g.fill(); g.restore();
  }
  if (o.rail > 0) {
    g.save(); g.globalAlpha = A * o.rail; g.shadowBlur = 30;
    for (const [rx, col, k] of [[RX.lp, '#ff4d5e', o.railP ?? 1], [RX.rp, '#ff4d5e', o.railP ?? 1], [RX.ln, '#4f8dff', o.railN ?? 1], [RX.rn, '#4f8dff', o.railN ?? 1]]) {
      if (k <= 0) continue; g.globalAlpha = A * o.rail * k; g.shadowColor = col; g.fillStyle = col; rr(rx - 12, -444, 24, 888, 10); g.fill();
    }
    g.restore();
  }
  // agujeros
  const N = 26 * 14, lit = o.count ?? -1; let idx = 0;
  const holeA = lerp(1, 0.75, xr);
  for (let r = 0; r < 26; r++) {
    const xs = [RX.lp, RX.ln]; for (let c = 0; c < 10; c++) xs.push(BBX(c)); xs.push(RX.rn, RX.rp);
    for (const hx of xs) {
      const on = lit >= 0 && idx < lit * N; idx++;
      g.globalAlpha = A * holeA;
      if (on) { g.fillStyle = CYA; g.shadowColor = CYA; g.shadowBlur = 10; } else g.fillStyle = '#2c313b';
      g.fillRect(hx - 6, BBY(r) - 6, 12, 12); g.shadowBlur = 0;
    }
  }
  g.globalAlpha = A;
  if (!o.noLetters) 'abcde'.split('').concat('fghij'.split('')).forEach((L, c) => txt(L, BBX(c), -458, 20, '#7d8494', { font: 'IX', stroke: 0, alpha: lerp(1, 0.5, xr) }));
  // piezas
  const p = o.parts || 0;
  if (p > 0) {
    g.save(); g.globalAlpha = A * clamp(p * 2); g.translate(0, -(1 - easeOut(p)) * 80);
    const wire = (x0, y0, x1, y1, col) => { g.strokeStyle = col; g.lineWidth = 13; g.lineCap = 'round'; g.beginPath(); g.moveTo(x0, y0); g.quadraticCurveTo((x0 + x1) / 2, y0 - 46, x1, y1); g.stroke(); circle(x0, y0, 7); g.fillStyle = SLV; g.fill(); circle(x1, y1, 7); g.fill(); };
    wire(RX.lp, BBY(3), BBX(0), BBY(3), '#e8424f');
    wire(BBX(0), BBY(11), RX.ln, BBY(11), '#22252d');
    g.save(); g.translate(BBX(2), (BBY(3) + BBY(9)) / 2); g.rotate(Math.PI / 2); resistor(0, 0, 0.486); g.restore();
    g.strokeStyle = '#b9c1cf'; g.lineWidth = 6; line(BBX(4), BBY(9), BBX(4), BBY(10) - 20); line(BBX(4), BBY(11), BBX(4), BBY(10) + 20);
    const on = o.on || 0;
    if (on > 0) { const rg = g.createRadialGradient(BBX(4), BBY(10), 5, BBX(4), BBY(10), 170); rg.addColorStop(0, rgba(RED, 0.7 * on)); rg.addColorStop(1, rgba(RED, 0)); g.fillStyle = rg; g.fillRect(BBX(4) - 170, BBY(10) - 170, 340, 340); }
    circle(BBX(4), BBY(10), 30); g.fillStyle = rgba(RED, 0.45 + 0.55 * on); if (on > 0) { g.shadowColor = RED; g.shadowBlur = 40 * on; } g.fill(); g.shadowBlur = 0; g.lineWidth = 4; g.strokeStyle = '#ff9aa4'; g.stroke();
    circle(BBX(4) - 9, BBY(10) - 9, 8); g.fillStyle = 'rgba(255,255,255,0.6)'; g.fill();
    g.restore();
    if (o.flowA > 0) flow(BB_PATH, T_NOW, 0.55, YEL, 12, 8, o.flowA);
  }
  g.restore();
}

// ---------------- instrumentos ----------------
const HSC = { faceTop: '#363c4a', faceBot: '#1c2029', edge: '#12151c', edgeDark: '#0a0c10', rim: CYA };
const MMC = { faceTop: '#ffd34d', faceBot: '#e0a41c', edge: '#a87610', edgeDark: '#6e4c08', rim: '#fff0b0' };
function scrScope(t, o = {}) {
  return (w, h) => {
    g.save(); g.strokeStyle = 'rgba(79,216,255,0.16)'; g.lineWidth = 1.5;
    for (let i = 1; i < 10; i++) line(w * i / 10, 0, w * i / 10, h);
    for (let j = 1; j < 8; j++) line(0, h * j / 8, w, h * j / 8);
    g.strokeStyle = 'rgba(79,216,255,0.4)'; g.lineWidth = 2; line(w / 2, 0, w / 2, h); line(0, h / 2, w, h / 2);
    const rec = o.rec ?? 1, ph = o.phase || 0, lw = Math.max(3, w / 110);
    const tr = (col, fn) => {
      if (rec <= 0) return;
      g.strokeStyle = col; g.lineWidth = lw; g.shadowColor = col; g.shadowBlur = 14; g.beginPath();
      const n = w * rec; for (let x = 0; x <= n; x += 2) { const y = fn(x / w); x ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke(); g.shadowBlur = 0;
      if (rec < 1) { circle(n, fn(rec), lw * 1.8); g.fillStyle = WHT; g.fill(); }
    };
    if (o.ch2) {
      tr(YEL, u => h * 0.32 - Math.sin(u * Math.PI * 4 + ph) * h * 0.16);
      tr(CYA, u => h * 0.72 - (Math.sin(u * Math.PI * 6 + ph * 1.5) > 0 ? 1 : -1) * h * 0.11);
    } else tr(YEL, u => h * 0.5 - Math.sin(u * Math.PI * 4 + ph) * h * 0.3);
    g.restore();
  };
}
function scopePanel(x, y, w, h, t, o = {}) {
  g.save(); g.globalAlpha *= (o.alpha ?? 1);
  rr(x - w / 2, y - h / 2, w, h, 28); g.fillStyle = '#10141c'; g.fill(); g.lineWidth = 6; g.strokeStyle = YEL; g.shadowColor = YEL; g.shadowBlur = 30 * (o.glow ?? 0.6); g.stroke(); g.shadowBlur = 0;
  screenArea(x - w / 2 + 22, y - h / 2 + 22, w - 44, h - 44, 14, '#06121a', scrScope(t, o));
  g.restore();
}
function multimeter(x, y, s, val, o = {}) {
  device(x, y, s, o, 300, 520, 46, 24, MMC, () => {
    g.fillStyle = '#20232b'; rr(-125, -235, 250, 470, 30); g.fill();
    g.fillStyle = '#a9bd93'; rr(-106, -216, 212, 112, 10); g.fill();
    txt(val, 0, -158, 62, '#16200f', { stroke: 0, maxW: 190 });
    circle(0, 24, 86); g.fillStyle = '#3a3f4c'; g.fill(); g.lineWidth = 4; g.strokeStyle = '#7b849a'; g.stroke();
    g.save(); g.translate(0, 24); g.rotate(-0.6); g.fillStyle = '#d9dde5'; rr(-14, -80, 28, 160, 10); g.fill(); g.restore();
    for (const [jx, col] of [[-72, '#111'], [0, '#111'], [72, RED]]) { circle(jx, 176, 20); g.fillStyle = col; g.fill(); g.lineWidth = 4; g.strokeStyle = '#7b849a'; g.stroke(); }
  });
}
function handScope(x, y, s, o = {}) {
  device(x, y, s, o, 420, 700, 44, 26, HSC, () => {
    g.fillStyle = '#07090e'; rr(-186, -318, 372, 296, 18); g.fill();
    screenArea(-170, -302, 340, 264, 10, '#06121a', o.screen);
    for (let i = 0; i < 4; i++) { rr(-170 + i * 88, 4, 72, 40, 12); g.fillStyle = '#4b5263'; g.fill(); }
    circle(0, 164, 80); g.fillStyle = '#272c37'; g.fill(); g.lineWidth = 3; g.strokeStyle = rgba(CYA, 0.5); g.stroke();
    for (let k = 0; k < 4; k++) { g.save(); g.translate(0, 164); g.rotate(k * Math.PI / 2); poly([[0, -66], [-12, -50], [12, -50]]); g.fillStyle = '#7b849a'; g.fill(); g.restore(); }
    circle(0, 164, 28); g.fillStyle = CYA; g.fill();
    for (const bx of [-152, 152]) { circle(bx, 110, 26); g.fillStyle = '#4b5263'; g.fill(); circle(bx, 200, 26); g.fill(); }
    txt('2C23T', 0, 300, 30, rgba(CYA, 0.9), { font: 'IX', stroke: 0 });
  });
}

// ---------------- cautín ----------------
function penIron(x, y, s, rot, heat, o = {}) {
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s); g.globalAlpha *= (o.alpha ?? 1);
  // cable USB-C
  g.strokeStyle = '#1b1e25'; g.lineWidth = 24; g.lineCap = 'round'; g.beginPath(); g.moveTo(-520, 0); g.bezierCurveTo(-680, 0, -700, 280, -980, 320); g.stroke();
  g.strokeStyle = '#2c313c'; g.lineWidth = 6; g.beginPath(); g.moveTo(-520, -6); g.bezierCurveTo(-670, -6, -700, 268, -980, 306); g.stroke();
  if (o.usb) { g.shadowColor = YEL; g.shadowBlur = 40 * o.usb; }
  g.fillStyle = o.usb ? YEL : '#c7ccd6'; rr(-530, -26, 70, 52, 12); g.fill(); g.shadowBlur = 0;
  g.fillStyle = '#1b1e25'; rr(-560, -34, 40, 68, 10); g.fill();
  // mango
  const mg = g.createLinearGradient(0, -46, 0, 46); mg.addColorStop(0, '#3a3f4c'); mg.addColorStop(1, '#16181e');
  rr(-462, -46, 430, 92, 40); g.fillStyle = mg; g.fill(); g.lineWidth = 3; g.strokeStyle = '#59607a'; g.stroke();
  g.strokeStyle = '#272b34'; g.lineWidth = 8; for (let i = 0; i < 7; i++) line(-150 + i * 16, -40, -150 + i * 16, 40);
  g.fillStyle = '#05070c'; rr(-380, -26, 170, 52, 8); g.fill();
  txt((o.temp ?? 0) + '°', -295, 2, 34, heat > 0.05 ? ORA : CYA, { font: 'IX', stroke: 0 });
  // vástago
  const sg = g.createLinearGradient(0, -22, 0, 22); sg.addColorStop(0, '#f0f3f8'); sg.addColorStop(1, '#8d96a6');
  poly([[-40, -24], [300, -14], [300, 14], [-40, 24]]); g.fillStyle = sg; g.fill();
  // punta
  const hc = heat > 0 ? `rgb(${Math.round(lerp(190, 255, heat))},${Math.round(lerp(196, 140, heat))},${Math.round(lerp(206, 60, heat))})` : '#bfc5ce';
  if (heat > 0) { const rg = g.createRadialGradient(400, 0, 5, 400, 0, 220); rg.addColorStop(0, rgba(ORA, 0.7 * heat)); rg.addColorStop(1, rgba(ORA, 0)); g.fillStyle = rg; g.fillRect(180, -220, 440, 440); }
  poly([[300, -15], [416, -4], [426, 0], [416, 4], [300, 15]]); g.fillStyle = hc; if (heat > 0) { g.shadowColor = ORA; g.shadowBlur = 40 * heat; } g.fill(); g.shadowBlur = 0;
  g.restore();
}
function timerRing(x, y, r, f, label, col, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  circle(x, y, r); g.fillStyle = 'rgba(6,10,28,0.85)'; g.fill(); g.lineWidth = 16; g.strokeStyle = 'rgba(255,255,255,0.12)'; g.stroke();
  g.beginPath(); g.arc(x, y, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * f); g.strokeStyle = col; g.shadowColor = col; g.shadowBlur = 20; g.lineCap = 'round'; g.stroke(); g.shadowBlur = 0;
  txt(label, x, y + 4, r * 0.62, WHT, { stroke: 0 });
  g.restore();
}
function thermo(x, y, f, col, label, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  rr(x - 30, y - 180, 60, 320, 30); g.fillStyle = 'rgba(6,10,28,0.85)'; g.fill(); g.lineWidth = 6; g.strokeStyle = 'rgba(255,255,255,0.35)'; g.stroke();
  circle(x, y + 150, 50); g.fill(); g.stroke();
  circle(x, y + 150, 36); g.fillStyle = col; g.shadowColor = col; g.shadowBlur = 24; g.fill();
  const hh = 280 * f; rr(x - 16, y + 120 - hh, 32, hh + 20, 16); g.fill(); g.shadowBlur = 0;
  txt(label, x + 60, y - 150 + (1 - f) * 200, 52, col, { align: 'left', stroke: 6 });
  g.restore();
}

// =====================================================================
// ESCENAS
// =====================================================================
const RING = [[540, 520], [854, 748], [734, 1118], [346, 1118], [226, 748]];
const RCOL = [CYA, PUR, GRN, YEL, ORA];
function ringItem(k, x, y, s, t) {
  if (k === 0) resistor(x, y, 0.3 * s);
  if (k === 1) boardUno(x, y, 0.3 * s, { shine: -1, noShadow: true });
  if (k === 2) breadboard(x, y, 0.165 * s, { noLetters: true });
  if (k === 3) handScope(x, y, 0.22 * s, { shine: -1, noShadow: true, screen: scrScope(t, { phase: t * 5 }) });
  if (k === 4) penIron(x + 10 * s, y + 10 * s, 0.2 * s, -0.75, 0.6 + 0.4 * Math.sin(t * 5), { temp: 320 });
}
function sceneHook(t) {
  drawBG(t, t > T.cinco ? YEL : CYA);
  const c = [540, 834];
  // "0" que se vuelve "5"
  const flip = prog(t, T.cinco - 0.08, T.cinco + 0.12);
  const big = t < T.cinco ? '0' : '5';
  const sc = (1 + 0.04 * Math.sin(t * 6)) * (t < T.cinco ? 1 : lerp(1.5, 1, easeOut(prog(t, T.cinco, T.cinco + 0.3)))) * (Math.abs(Math.cos(flip * Math.PI)) * 0.85 + 0.15);
  if (t > T.cinco) rays(c[0], c[1], YEL, t, 0.7 * easeOut(prog(t, T.cinco, T.cinco + 0.5)));
  g.save(); g.translate(c[0], c[1]); g.scale(sc, sc);
  txt(big, 0, 10, 380, t < T.cinco ? CYA : YEL, { stroke: 16, glow: t < T.cinco ? CYA : YEL, glowR: 60 });
  g.restore();
  // los 5 objetos salen al anillo
  for (let k = 0; k < 5; k++) {
    const t0 = T.cinco + 0.08 + k * 0.1, e = backOut(prog(t, t0, t0 + 0.45));
    if (e <= 0) continue;
    const [rx, ry] = RING[k]; const x = lerp(c[0], rx, e), y = lerp(c[1], ry, e);
    const pulse = t > T.cosas ? 1 + 0.06 * Math.sin((t - T.cosas) * 8 + k) : 1;
    g.save(); circle(x, y, 118 * e * pulse); g.fillStyle = 'rgba(6,10,28,0.88)'; g.fill(); g.lineWidth = 6; g.strokeStyle = RCOL[k]; g.shadowColor = RCOL[k]; g.shadowBlur = 26; g.stroke(); g.restore();
    ringItem(k, x, y, e * pulse, t);
    circle(x + 82 * e, y - 82 * e, 30 * e); g.fillStyle = RCOL[k]; g.fill(); txt(String(k + 1), x + 82 * e, y - 80 * e, 38 * e, INK, { stroke: 0 });
  }
  if (t < T.cinco + 0.3) pill('ELECTRÓNICA', 540, 470, CYA, 64, t, T.electronica, { solid: true, alpha: 1 - prog(t, T.cinco, T.cinco + 0.25) });
  stamp('DESDE CERO', 540, 1250, 92, RED, t, T.cero, -0.08, 1 - prog(t, T.cinco - 0.1, T.cinco + 0.15));
  pill('¿CÓMO FUNCIONA?', 540, 1300, YEL, 56, t, T.funciona, { solid: true });
  burst(c[0], c[1], t, T.cinco, YEL, 14, 300);
}

// ---- 1. kit de componentes ----
function sceneKit(t) {
  drawBG(t, CYA);
  const a0 = 1 - prog(t, T.resist - 0.2, T.resist + 0.1);
  if (a0 > 0) {
    const e = pop(t, TR[0] + 0.1, 0.4);
    g.save(); g.globalAlpha = a0; g.translate(540, 860); g.scale(e, e); txt('KIT', 0, 0, 300, CYA, { stroke: 14, glow: CYA, glowR: 50 }); g.restore();
  }
  const cards = [
    [290, 690, 'RESISTENCIA', YEL, T.resist], [790, 690, 'LED', RED, T.leds],
    [290, 1090, 'CAPACITOR', CYA, T.capa], [790, 1090, 'TRANSISTOR', PUR, T.trans]];
  cards.forEach(([x, y, title, col, t0], i) => {
    const e = pop(t, t0, 0.35); if (e <= 0) return;
    g.save(); g.translate(x, y); g.scale(e, e); g.translate(-x, -y);
    panel(x, y, 460, 360, col, 1, title, 40);
    if (i === 0) {
      const fa = prog(t, T.frenan - 0.2, T.frenan + 0.2);
      g.strokeStyle = '#b9c1cf'; g.lineWidth = 7; line(x - 200, y + 30, x + 200, y + 30);
      resistor(x, y + 30, 0.55, { glow: fa * (0.6 + 0.4 * Math.sin(t * 10)) });
      flow([[x - 200, y + 30], [x - 115, y + 30]], t, 2.2, YEL, 5, 9, fa);
      flow([[x + 115, y + 30], [x + 200, y + 30]], t, 0.7, YEL, 2, 9, fa);
      if (fa > 0) txt('frena', x, y + 120, 36, YEL, { font: 'IX', stroke: 6, alpha: fa });
    }
    if (i === 1) led(x, y + 10, 0.62, RED, prog(t, T.luz - 0.15, T.luz + 0.2) * (0.85 + 0.15 * Math.sin(t * 12)));
    if (i === 2) capacitor(x - 30, y + 20, 0.62, easeOut(prog(t, T.carga - 0.1, T.carga + 1.2)));
    if (i === 3) {
      transistor(x - 120, y + 10, 0.55);
      const on = t > T.interr ? ((t - T.interr) % 1.0 < 0.5 ? 1 : 0) : 0;
      const sw = t > T.interr ? ease(clamp(((t - T.interr) % 1.0 < 0.5 ? (t - T.interr) % 1.0 : 1 - ((t - T.interr) % 1.0 - 0.5)) / 0.12)) : 0;
      switchIcon(x + 90, y + 30, 0.8, WHT, t > T.interr ? sw : 0);
      circle(x + 90, y - 50, 22); g.fillStyle = on ? YEL : '#3a3f4c'; if (on) { g.shadowColor = YEL; g.shadowBlur = 30; } g.fill(); g.shadowBlur = 0;
      if (t > T.elec) flow([[x - 120, y + 120], [x - 120, y + 150], [x + 10, y + 150], [x + 10, y + 30]], t, 1.4, CYA, 4, 7, prog(t, T.elec - 0.1, T.elec + 0.2));
    }
    g.restore();
  });
}
function sceneKitBox(t) {
  drawBG(t, CYA);
  const t0 = SUB.box;
  // caja abierta (genérica)
  const e = pop(t, t0 + 0.1, 0.4);
  g.save(); g.translate(540, 930); g.scale(e, e);
  poly([[-410, -210], [410, -210], [360, -430], [-360, -430]]); g.fillStyle = '#132552'; g.fill(); g.lineWidth = 5; g.strokeStyle = CYA; g.stroke();
  if (t > T.super - 0.05) txt('SÚPER KIT', 0, -318, 86 * pop(t, T.super, 0.3), YEL, { stroke: 8, glow: YEL });
  rr(-410, -210, 820, 560, 26); g.fillStyle = '#0a1636'; g.fill(); g.lineWidth = 6; g.strokeStyle = CYA; g.stroke();
  g.strokeStyle = rgba(CYA, 0.4); g.lineWidth = 4; line(-410, 70, 410, 70); line(-137, -210, -137, 350); line(137, -210, 137, 350);
  g.restore();
  const cell = (cx, cy) => [540 + cx * 273, 930 + (cy ? 210 : -70)];
  const items = [
    [T.arduino, 0, 0, (x, y, s) => boardUno(x, y, 0.42 * s, { blink: true, noShadow: true, shine: -1 })],
    [T.sensores, 1, 0, (x, y, s) => ultrasonic(x, y, 0.85 * s)],
    [T.sensores + 0.15, -1, 1, (x, y, s) => { thermoIcon(x - 50, y, 0.9 * s, RED); sunIcon(x + 50, y, 0.75 * s, YEL); }],
    [T.motores, 1, 1, (x, y, s) => servo(x, y + 10, 0.8 * s, Math.sin(t * 3) * 0.9)],
    [T.motores + 0.15, 0, 1, (x, y, s) => dcMotor(x - 20, y, 0.75 * s, t * 9)],
    [T.tutorial, -1, 0, (x, y, s) => book(x, y, 0.95 * s, YEL)],
  ];
  for (const [ti, cx, cy, fn] of items) {
    const s = pop(t, ti, 0.35); if (s <= 0) continue;
    const [x, y] = cell(cx, cy); fn(x, y, s * e);
  }
  pill('ELEGOO', 540, 432, CYA, 56, t, T.elegoo, { solid: true });
  if (t > T.tutorial) pill('PASO A PASO', 268, 1360, YEL, 40, t, T.tutorial + 0.2, { icon: 'check' });
}

// ---- 2. microcontrolador ----
function sceneMicro(t) {
  drawBG(t, PUR);
  const e = pop(t, T.micro, 0.45);
  qfp(540, 850, 0.95 * e, PUR, 0.6 + 0.4 * Math.sin(t * 4) * (t > T.ejecuta ? 1 : 0.3));
  pill('COMPUTADORA EN UN CHIP', 540, 470, PUR, 50, t, T.compu, { solid: true, alpha: 1 - prog(t, T.lee - 0.25, T.lee) });
  // entradas
  const li = prog(t, T.lee - 0.1, T.lee + 0.3);
  if (li > 0) {
    const ins = [[150, 650, (x, y) => thermoIcon(x, y, 0.95, RED)], [150, 850, (x, y) => sunIcon(x, y, 0.85, YEL)], [150, 1050, (x, y) => buttonIcon(x, y, 0.9, GRN, (Math.floor(t * 2) % 2))]];
    ins.forEach(([x, y, fn], i) => { const s = pop(t, T.lee + i * 0.08, 0.3); g.save(); g.globalAlpha = clamp(s); fn(x, y); g.restore(); flow([[x + 70, y], [330, lerp(y, 850, 0.6)]], t, 1.6, CYA, 3, 8, li); });
    pill('LEE', 170, 470, CYA, 54, t, T.lee, { solid: true });
  }
  // código
  if (t > T.ejecuta - 0.1) {
    const k = prog(t, T.ejecuta - 0.1, T.ejecuta + 0.2);
    panel(540, 1230, 640, 170, PUR, k);
    const code = ['if (luz < 300) {', '  led = ENCENDIDO;', '}'];
    const nch = Math.floor((t - T.ejecuta) * 34);
    let used = 0;
    code.forEach((ln, i) => { const show = ln.slice(0, clamp(nch - used, 0, ln.length)); used += ln.length; txt(show, 260, 1180 + i * 46, 38, i === 1 ? YEL : '#d9c8ff', { font: 'IX', align: 'left', stroke: 0, alpha: k }); });
    pill('EJECUTA', 540, 1080, PUR, 46, t, T.ejecuta, { solid: true });
  }
  // salidas
  const lo = prog(t, T.controla - 0.1, T.controla + 0.3);
  if (lo > 0) {
    flow([[750, 760], [880, 700]], t, 1.6, YEL, 3, 8, lo); flow([[750, 940], [880, 1000]], t, 1.6, YEL, 3, 8, lo);
    led(930, 650, 0.6, GRN, lo * (0.85 + 0.15 * Math.sin(t * 14)));
    motorIcon(930, 1020, 0.95, YEL, (t - T.controla) * 10 * lo);
    pill('CONTROLA', 880, 470, YEL, 50, t, T.controla, { solid: true });
  }
}
function sceneESP(t) {
  drawBG(t, PUR);
  const m = ease(prog(t, T.internet - 0.2, T.internet + 0.4));
  const ue = pop(t, SUB.esp + 0.05, 0.4);
  boardUno(lerp(540, 240, m), lerp(820, 690, m), lerp(1.2, 0.55, m) * ue, { blink: true, glow: 1 - m, alpha: lerp(1, 0.75, m) });
  pill('ARDUINO UNO', lerp(540, 240, m), lerp(1140, 880, m), CYA, 46, t, T.uno, { solid: true });
  if (m > 0.02) {
    arrow(410, 690, 610, 690, WHT, m, 10);
    pill('INTERNET', 505, 615, CYA, 38, t, T.internet + 0.1);
    const ee = pop(t, T.esp, 0.4);
    if (ee > 0) {
      const cores = 2 * prog(t, T.nucleos - 0.15, T.nucleos + 0.35);
      boardESP(830, 860, 1.0 * ee, { cores, glow: 0.5 + 0.5 * Math.sin(t * 5) * (cores > 0 ? 1 : 0) });
      pill('ESP32', 830, 1220, PUR, 54, t, T.esp, { solid: true });
    }
    pill('2 NÚCLEOS', 250, 1030, YEL, 48, t, T.nucleos, { solid: true });
    if (t > T.mhz - 0.05) { const v = counter(t, T.mhz - 0.05, T.mhz + 0.5, 0, 240); pill(v + ' MHz', 250, 1150, YEL, 48, t, T.mhz); }
    wifiIcon(700, 520, 1.15, CYA, t, prog(t, T.wifi - 0.1, T.wifi + 0.2));
    btIcon(960, 520, 0.9, '#4f8dff', pop(t, T.bt, 0.3));
  }
}

// ---- 3. protoboard ----
function sceneProto(t) {
  drawBG(t, GRN);
  const e = pop(t, T.proto, 0.45);
  const cnt = prog(t, T.p830 - 0.1, T.p830 + 0.9);
  g.save(); g.translate(540, 860); g.rotate(lerp(-0.12, 0, e)); g.translate(-540, -860);
  breadboard(540, 860, 0.8 * e, { count: t > T.p830 - 0.1 ? cnt : -1 });
  g.restore();
  if (t > T.p830 - 0.1) {
    const v = counter(t, T.p830 - 0.1, T.p830 + 0.9, 0, 830);
    g.save(); const s = pop(t, T.p830, 0.3); g.translate(540, 860); g.scale(s, s);
    txt(String(v), 0, -20, 240, YEL, { stroke: 14, glow: YEL, glowR: 50 }); g.restore();
  }
  pill('PUNTOS', 540, 1000, GRN, 54, t, T.puntos, { solid: true });
}
function sceneProtoX(t) {
  drawBG(t, GRN);
  const xr = prog(t, SUB.xray + 0.05, SUB.xray + 0.5);
  const hl = prog(t, T.fila - 0.1, T.fila + 0.2) * (0.7 + 0.3 * Math.sin(t * 8));
  const rail = prog(t, T.rieles - 0.1, T.rieles + 0.25) * (t > T.sin - 0.1 ? 1 - 0.6 * prog(t, T.sin - 0.1, T.sin + 0.3) : 1);
  const parts = prog(t, T.sin - 0.15, T.sin + 0.35);
  const on = prog(t, T.soldar - 0.1, T.soldar + 0.2);
  breadboard(540, 860, 0.8, { xray: xr, hlRow: 15, hl: hl * (1 - prog(t, T.rieles, T.rieles + 0.3) * 0.6), rail, railP: prog(t, T.positivo - 0.1, T.positivo + 0.2) + (t < T.positivo - 0.1 ? 1 : 0), railN: prog(t, T.negativo - 0.1, T.negativo + 0.2) + (t < T.positivo - 0.1 ? 1 : 0), parts, on, flowA: on });
  // etiqueta de la fila de 5
  if (hl > 0) {
    const y = 860 + BBY(15) * 0.8, x = 540 + BBX(2) * 0.8;
    g.save(); g.globalAlpha = clamp(hl * 1.5) * (1 - prog(t, T.rieles, T.rieles + 0.3)); arrow(x - 300, y - 140, x - 120, y - 18, YEL, 1, 8); g.restore();
    pill('5 CONECTADOS', 260, y - 190, YEL, 40, t, T.cinco2, { solid: true, alpha: 1 - prog(t, T.rieles, T.rieles + 0.3) });
  }
  pill('LÁMINA DE METAL', 540, 470, CYA, 50, t, T.lamina, { solid: true, alpha: 1 - prog(t, T.rieles - 0.1, T.rieles + 0.1) });
  pill('+ POSITIVO', 250, 470, RED, 44, t, T.positivo, { solid: true, alpha: 1 - prog(t, T.sin - 0.1, T.sin + 0.2) });
  pill('− NEGATIVO', 830, 470, '#4f8dff', 44, t, T.negativo, { solid: true, alpha: 1 - prog(t, T.sin - 0.1, T.sin + 0.2) });
  stamp('SIN SOLDAR', 540, 1310, 76, GRN, t, T.soldar, -0.06);
  burst(540 + BBX(4) * 0.8, 860 + BBY(10) * 0.8, t, T.soldar, RED, 10, 200);
}

// ---- 4. osciloscopio ----
function sceneScope(t) {
  drawBG(t, YEL);
  const se = pop(t, T.osci, 0.4);
  const rec = t < T.dibuja - 0.05 ? 0 : (t < T.moverse ? easeOut(prog(t, T.dibuja - 0.05, T.tiempo + 0.4)) : 1);
  const ph = t > T.moverse ? (t - T.moverse) * 7 : 0;
  g.save(); g.translate(735, 860); g.scale(se, se); g.translate(-735, -860);
  scopePanel(735, 860, 600, 470, t, { rec, phase: ph, glow: 0.7 });
  g.restore();
  if (t > T.voltaje - 0.1) { const k = pop(t, T.voltaje, 0.3); arrow(462, 1040, 462, 700, YEL, clamp(k), 8); pill('VOLTAJE', 735, 570, YEL, 46, t, T.voltaje, { solid: true }); }
  if (t > T.tiempo - 0.1) { const k = pop(t, T.tiempo, 0.3); arrow(470, 1130, 980, 1130, CYA, clamp(k), 8); pill('TIEMPO', 735, 1200, CYA, 46, t, T.tiempo, { solid: true }); }
  // multímetro: solo un número
  const me = pop(t, T.multi, 0.4);
  if (me > 0) {
    const v = t > T.numero ? '3.30 V' : '- - -';
    multimeter(210, 860, 0.72 * me, v, { glow: t > T.numero ? 0.6 : 0 });
    pill('UN NÚMERO', 210, 1170, WHT, 40, t, T.numero);
  }
  if (t > T.moverse) txt('~', 735, 860, 0, YEL);
}
function sceneHand(t) {
  drawBG(t, YEL);
  const e = pop(t, SUB.hand + 0.05, 0.45);
  const ch2 = t > T.canales - 0.1;
  handScope(380, 900, 0.95 * e, { yaw: 0.12 * Math.sin(t * 1.2), glow: 0.7, screen: scrScope(t, { phase: t * 5, ch2 }) });
  pill('DE BOLSILLO', 540, 470, CYA, 52, t, T.bolsillo, { solid: true });
  stamp('3 EN 1', 850, 600, 80, YEL, t, T.tres, 0.12);
  pill('2 CANALES', 840, 790, YEL, 40, t, T.canales, { solid: true });
  pill('MULTÍMETRO', 840, 920, CYA, 40, t, T.multi2, { solid: true });
  pill('GENERADOR', 840, 1050, GRN, 40, t, T.generador, { solid: true });
  pill('FNIRSI 2C23T', 380, 1330, WHT, 42, t, T.fnirsi);
}

// ---- 5. cautín ----
function sceneSolder(t) {
  drawBG(t, ORA);
  const pa = ease(prog(t, TR[4], TR[4] + 0.45));
  const heat = prog(t, T.caliente - 0.3, T.caliente + 0.5) * (1 - prog(t, T.enfria, T.enfria + 0.8));
  g.save(); g.globalAlpha = pa;
  // placa
  rr(-40, 640, 1160, 720, 30); const pg = g.createLinearGradient(0, 640, 0, 1360); pg.addColorStop(0, '#12744c'); pg.addColorStop(1, '#0a4a30'); g.fillStyle = pg; g.fill();
  g.strokeStyle = '#1f9a66'; g.lineWidth = 26; g.lineCap = 'round'; line(540, 1010, 1080, 1010); line(200, 1250, 540, 1250);
  circle(200, 1250, 40); g.fillStyle = COP; g.fill();
  // pata del componente
  resistor(540, 520, 0.62, { rot: Math.PI / 2 });
  g.strokeStyle = '#d5dbe4'; g.lineWidth = 15; line(540, 640, 540, 1020);
  circle(540, 1010, 74); g.fillStyle = COP; g.fill(); circle(540, 1010, 24); g.fillStyle = '#1a1208'; g.fill();
  g.strokeStyle = '#d5dbe4'; g.lineWidth = 15; line(540, 990, 540, 1030);
  // estaño
  const m = easeOut(prog(t, T.estano - 0.05, T.estano + 1.0));
  const shine = prog(t, T.enfria + 0.2, T.enfria + 0.6);
  if (m > 0) {
    g.beginPath(); g.moveTo(540 - 86 * m, 1012); g.quadraticCurveTo(540 - 36 * m, 1004 - 12 * m, 540 - 14, 1010 - 78 * m); g.lineTo(540 + 14, 1010 - 78 * m); g.quadraticCurveTo(540 + 36 * m, 1004 - 12 * m, 540 + 86 * m, 1012); g.closePath();
    const bg2 = g.createLinearGradient(460, 0, 620, 0); bg2.addColorStop(0, '#8d96a6'); bg2.addColorStop(0.35, shine > 0 ? '#ffffff' : '#dfe4ec'); bg2.addColorStop(1, '#7c8596');
    g.fillStyle = bg2; if (heat > 0.2) { g.shadowColor = ORA; g.shadowBlur = 20 * heat; } g.fill(); g.shadowBlur = 0;
  }
  // hilo de estaño
  const wi = ease(prog(t, T.estano - 0.6, T.estano - 0.05)), melt = prog(t, T.estano, T.estano + 1.0), wo = ease(prog(t, T.enfria - 0.2, T.enfria + 0.3));
  if (wi > 0) {
    const ex = lerp(-80, 490, wi) - melt * 70 - wo * 400, ey = lerp(690, 975, wi) - melt * 35 - wo * 200;
    g.strokeStyle = '#c9d0db'; g.lineWidth = 16; g.lineCap = 'round'; line(-80, 690 - (ey - 690) * 0, ex, ey);
    g.strokeStyle = 'rgba(255,255,255,0.55)'; g.lineWidth = 4; line(-80, 684, ex, ey - 6);
  }
  // punta del cautín
  const ent = ease(prog(t, TR[4] + 0.2, TR[4] + 0.8)), ret = ease(prog(t, T.enfria - 0.1, T.enfria + 0.5));
  const tx = 600 + (1 - ent) * 600 + ret * 330, ty = 970 - (1 - ent) * 600 - ret * 330;
  if (heat > 0) { const rg = g.createRadialGradient(tx, ty, 5, tx, ty, 260); rg.addColorStop(0, rgba(ORA, 0.55 * heat)); rg.addColorStop(1, rgba(ORA, 0)); g.fillStyle = rg; g.fillRect(tx - 260, ty - 260, 520, 520); }
  g.save(); g.translate(tx, ty); g.rotate(-Math.PI / 4);
  const hc = `rgb(${Math.round(lerp(190, 255, heat))},${Math.round(lerp(196, 140, heat))},${Math.round(lerp(206, 60, heat))})`;
  poly([[0, 0], [150, -30], [150, 30]]); g.fillStyle = hc; if (heat > 0) { g.shadowColor = ORA; g.shadowBlur = 40 * heat; } g.fill(); g.shadowBlur = 0;
  const sg = g.createLinearGradient(0, -34, 0, 34); sg.addColorStop(0, '#f0f3f8'); sg.addColorStop(1, '#8d96a6'); g.fillStyle = sg; rr(146, -34, 560, 68, 10); g.fill();
  g.fillStyle = '#23262e'; rr(700, -56, 600, 112, 40); g.fill();
  g.restore();
  // humo
  if (heat > 0.3 && m > 0) for (let k = 0; k < 6; k++) { const f = ((t * 0.6 + k / 6) % 1); circle(540 + Math.sin(f * 6 + k) * 30, 980 - f * 320, 14 + f * 30); g.fillStyle = `rgba(220,226,236,${0.18 * (1 - f) * heat})`; g.fill(); }
  g.restore();
  // temperatura
  if (t > T.caliente - 0.3) {
    const v = counter(t, T.caliente - 0.3, T.c200, 25, 200);
    panel(300, 500, 400, 150, ORA, prog(t, T.caliente - 0.3, T.caliente));
    txt(v + ' °C', 300, 505, 88, ORA, { stroke: 0, alpha: prog(t, T.caliente - 0.3, T.caliente) });
  }
  if (t > T.c200) pill('EL ESTAÑO SE DERRITE', 760, 640, ORA, 38, t, T.c200 + 0.05, { solid: true, alpha: 1 - prog(t, T.enfria - 0.2, T.enfria) });
  if (t > T.enfria) { burst(540, 970, t, T.enfria + 0.3, WHT, 10, 170); sparkle(520, 960, 30 * shine, WHT, shine * (0.6 + 0.4 * Math.sin(t * 10))); }
  if (t > T.electricamente - 0.2) {
    const fa = prog(t, T.electricamente - 0.2, T.electricamente + 0.2);
    flow([[540, 380], [540, 1010], [1080, 1010]], t, 0.8, YEL, 9, 9, fa);
    pill('UNIÓN ELÉCTRICA', 760, 1180, YEL, 44, t, T.electricamente, { solid: true, icon: 'check' });
  }
}
function scenePen(t) {
  const warn = prog(t, T.toques - 0.1, T.toques + 0.2);
  drawBG(t, warn > 0 ? RED : ORA, warn > 0 ? `rgba(255,30,60,${0.12 * warn})` : null);
  const e = pop(t, SUB.pen + 0.05, 0.45);
  const heat = prog(t, T.doce - 0.2, T.doce + 1.0);
  const temp = Math.round(lerp(25, t < T.c400 - 0.1 ? 350 : 400, easeOut(prog(t, T.doce - 0.2, t < T.c400 - 0.1 ? T.doce + 1.0 : T.c400 + 0.4))));
  const usb = t > T.usbc - 0.1 ? prog(t, T.usbc - 0.1, T.usbc + 0.2) * (1 - prog(t, T.doce, T.doce + 0.3)) : 0;
  penIron(lerp(1400, 540, e), 820, 0.95, -0.32, heat, { usb, temp });
  pill('PINECIL', 540, 470, ORA, 60, t, T.pinecil, { solid: true, alpha: 1 - prog(t, T.toques - 0.2, T.toques) });
  pill('USB-C', 230, 1080, YEL, 46, t, T.usbc, { solid: true, alpha: 1 - prog(t, T.doce - 0.3, T.doce - 0.1) });
  if (t > T.doce - 0.2) {
    const f = easeOut(prog(t, T.doce - 0.2, T.doce + 0.9));
    timerRing(320, 1210, 110, f, Math.round(12 * f) + ' s', CYA, prog(t, T.doce - 0.2, T.doce));
  }
  if (t > T.c400 - 0.2) {
    const f = easeOut(prog(t, T.c400 - 0.2, T.c400 + 0.5));
    thermo(760, 1150, f, ORA, Math.round(400 * f) + ' °C', prog(t, T.c400 - 0.2, T.c400));
  }
  if (warn > 0) { g.save(); g.globalAlpha = warn; warnTri(910, 560, 3.2 * pop(t, T.toques, 0.3), RED); g.restore(); }
  stamp('¡NO TOQUES LA PUNTA!', 540, 470, 62, RED, t, T.toques, -0.05);
}
function warnTri(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); poly([[0, -26], [28, 22], [-28, 22]]); g.fillStyle = col; g.lineJoin = 'round'; g.fill(); g.fillStyle = INK; g.fillRect(-3.5, -10, 7, 18); circle(0, 14, 4); g.fill(); g.restore(); }

// ---- cierre ----
function sceneClose(t) {
  drawBG(t, GRN);
  const fadeL = 1 - 0.65 * prog(t, T.links - 0.2, T.links + 0.2);
  const tiles = [
    [290, 690, 'ARMAR', GRN, T.armar, (x, y) => breadboard(x, y, 0.2, { noLetters: true, parts: 1, on: 1 })],
    [790, 690, 'PROGRAMAR', PUR, T.programar, (x, y) => boardUno(x, y, 0.62 * 0.6, { blink: true, noShadow: true, shine: -1 })],
    [290, 1080, 'MEDIR', YEL, T.medir, (x, y) => handScope(x, y, 0.27, { noShadow: true, shine: -1, screen: scrScope(t, { phase: t * 5 }) })],
    [790, 1080, 'SOLDAR', ORA, T.soldar2, (x, y) => penIron(x + 20, y + 10, 0.27, -0.6, 0.8, { temp: 320 })],
  ];
  tiles.forEach(([x, y, lab, col, tk, fn], i) => {
    const e = pop(t, C0[0] + i * 0.08, 0.4); if (e <= 0) return;
    const on = t > tk - 0.05;
    g.save(); g.globalAlpha = fadeL; g.translate(x, y); g.scale(e * (on ? 1 + 0.05 * Math.exp(-(t - tk) / 0.2) : 0.94), e * (on ? 1 + 0.05 * Math.exp(-(t - tk) / 0.2) : 0.94)); g.translate(-x, -y);
    panel(x, y, 450, 350, on ? col : rgba(col, 0.35), 1);
    g.save(); if (!on) g.globalAlpha *= 0.45; fn(x, y - 20); g.restore();
    txt(lab, x, y + 140, 50, on ? col : rgba(WHT, 0.5), { stroke: 6 });
    if (on) { const k = backOut(prog(t, tk - 0.05, tk + 0.25)); circle(x + 180, y - 140, 40 * k); g.fillStyle = col; g.fill(); check(x + 180, y - 138, 44 * k, INK, 0.2); }
    g.restore();
  });
  if (t > T.links - 0.1) {
    const e = pop(t, T.links, 0.35);
    g.save(); g.translate(540, 880); g.scale(e, e);
    rr(-420, -110, 840, 220, 60); g.fillStyle = YEL; g.shadowColor = YEL; g.shadowBlur = 50; g.fill(); g.shadowBlur = 0; g.lineWidth = 8; g.strokeStyle = INK; g.stroke();
    txt('LINKS DE COMPRA', 0, -36, 74, INK, { stroke: 0 });
    txt('en la descripción', 0, 46, 54, INK, { font: 'IX', stroke: 0 });
    g.restore();
    const b = Math.abs(Math.sin((t - T.links) * 5)) * 30;
    if (t > T.descripcion - 0.2) arrow(540, 1040 + b, 540, 1200 + b, YEL, prog(t, T.descripcion - 0.2, T.descripcion + 0.1), 14);
  }
}
function sceneEnd(t) {
  drawBG(t, YEL);
  const E = ENDC;
  const e = backOut(prog(t, E, E + 0.5));
  rays(540, 830, YEL, t, e * 0.6);
  g.save(); g.translate(540, 830); g.scale(e, e);
  g.shadowColor = YEL; g.shadowBlur = 60; bolt(0, 0, 330); g.fillStyle = YEL; g.fill(); g.lineWidth = 10; g.strokeStyle = INK; g.stroke(); g.restore();
  txt('FLASH DATOS', 540, 1090, 112, WHT, { stroke: 9, alpha: ease(prog(t, E + 0.15, E + 0.5)) });
  txt('Síguenos para más datos', 540, 1200, 54, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, E + 0.3, E + 0.7)) });
}
function rays(x, y, col, t, a = 1, n = 12, R = 900) {
  if (a <= 0) return;
  g.save(); g.translate(x, y); g.rotate(t * 0.25); g.globalAlpha *= a;
  for (let k = 0; k < n; k++) { g.rotate(Math.PI * 2 / n); const gr = g.createLinearGradient(0, 0, R, 0); gr.addColorStop(0, rgba(col, 0.35)); gr.addColorStop(1, rgba(col, 0)); g.fillStyle = gr; poly([[0, 0], [R, -R * 0.09], [R, R * 0.09]]); g.fill(); }
  g.restore();
}
function whip(t, ts, A, B) {
  const s = prog(t, ts - 0.12, ts + 0.14);
  if (s <= 0) return A(t);
  if (s >= 1) return B(t);
  const e = ease(s);
  g.save(); g.translate(0, -e * 700); g.globalAlpha = 1 - e; A(t); g.restore();
  g.save(); g.translate(0, (1 - e) * 700); g.globalAlpha = e; B(t); g.restore();
  g.save(); g.globalAlpha = Math.sin(s * Math.PI) * 0.5;
  for (let k = 0; k < 14; k++) { g.fillStyle = k % 2 ? rgba(CYA, 0.6) : rgba(WHT, 0.6); g.fillRect(hash(k, 1) * W, 0, 4 + hash(k, 2) * 10, H); }
  g.restore();
}

function render(t) {
  T_NOW = t;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]); g.globalCompositeOperation = 'source-over';
  g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
  const cam = camera(t);
  g.setTransform(cam.z, 0, 0, cam.z, 540 * (1 - cam.z) + cam.sx, 880 * (1 - cam.z) + cam.sy);
  if (t < TR[0]) sceneHook(t);
  else if (t < TR[1]) whip(t, SUB.box, sceneKit, sceneKitBox);
  else if (t < TR[2]) whip(t, SUB.esp, sceneMicro, sceneESP);
  else if (t < TR[3]) whip(t, SUB.xray, sceneProto, sceneProtoX);
  else if (t < TR[4]) whip(t, SUB.hand, sceneScope, sceneHand);
  else if (t < TR[5]) whip(t, SUB.pen, sceneSolder, scenePen);
  else if (t < TR[6]) sceneClose(t);
  else sceneEnd(t);
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  g.drawImage(VIG, 0, 0);
  const ga = glitchAmount(t);
  if (ga > 0.02) applyGlitch(t, ga);
  if (t < ENDC) { drawChapter(t); drawCaption(t); }
  drawWatermark();
  drawProgress(t);
  const fa = flashAlpha(t);
  if (fa > 0) {
    g.fillStyle = `rgba(225,248,255,${0.85 * fa})`; g.fillRect(0, 0, W, H);
    if (fa > 0.35) { g.globalAlpha = Math.min(1, (fa - 0.35) / 0.4); bolt(W / 2, H / 2, 420); g.fillStyle = YEL; g.fill(); g.globalAlpha = 1; }
  }
}
window.render = render;
window.grab = (t, q) => { render(t); return C.toDataURL('image/jpeg', q); };
window.INFO = { END, ENDC, TR, T };
