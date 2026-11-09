// Flash Datos · video 27 · Flipper Zero y Flipper One: cómo funcionan y por qué todos hablan del One
// Canvas 2D 1080x1920. render(t) dibuja el cuadro del segundo t.
// Animación más enganchadora que los videos anteriores: subtítulos palabra por palabra con resaltado,
// cámara viva (zoom de golpe en cada palabra clave, sacudidas en los impactos), transiciones glitch RGB,
// barra de progreso, capítulos, contadores y un piso de rejilla en perspectiva.
// Los aparatos están dibujados como esquemas originales (no son réplicas del diseño real ni usan logos).
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
const G0 = PP('gancho', 0), Z0 = PP('zero', 0), F0 = PP('funciona', 0), F1 = PP('funciona', 1), F2 = PP('funciona', 2);
const P0 = PP('polemica', 0), P1 = PP('polemica', 1), O0 = PP('one', 0), O1 = PP('one', 1), O2 = PP('one', 2);
const R0 = PP('porque', 0), K0 = PP('cierre', 0);
const TR = [Z0[0] - 0.22, F0[0] - 0.22, P0[0] - 0.22, O0[0] - 0.2, R0[0] - 0.22, K0[0] - 0.22, K0[1] + 0.22];
const ENDC = TR[6];
const SUB = { mod: F1[0] - 0.1, pet: F2[0] - 0.1, roll: P1[0] - 0.12, spec: O1[0] - 0.1, port: O2[0] - 0.1 };

// palabras clave
const T = {
  hacker: WT('gancho', 'hacker'), canada: WT('gancho', 'canadá'), prohibir: WT('gancho', 'prohibir'), hermano: WT('gancho', 'hermano'), esperaban: WT('gancho', 'esperaban'),
  zero: WT('zero', 'zero'), mano: WT('zero', 'mano'), p169: WT('zero', '$169'), segun: WT('zero', 'según'), millon: WT('zero', 'millón'),
  escucha: WT('funciona', 'escucha'), guarda: WT('funciona', 'guarda'), repite: WT('funciona', 'repite'),
  radio: WT('funciona', 'radio'), nfc: WT('funciona', 'nfc'), tarjetas: WT('funciona', 'tarjetas'), ir: WT('funciona', 'infrarrojo'), teles: WT('funciona', 'teles'),
  delfin: WT('funciona', 'delfín'), nivel: WT('funciona', 'nivel'),
  y2024: WT('polemica', '2024'), canada2: WT('polemica', 'canadá'), prohibir2: WT('polemica', 'prohibir'), autos: WT('polemica', 'autos'),
  cambian: WT('polemica', 'cambian'), clic: WT('polemica', 'clic'), no: WT('polemica', 'no', true),
  one: WT('one', 'one'), zero2: WT('one', 'zero'), compu: WT('one', 'computadora'), linux: WT('one', 'linux'),
  nucleos: WT('one', 'núcleos'), gb: WT('one', 'gb'), ia: WT('one', 'inteligencia'), rpi: WT('one', 'raspberry'),
  red: WT('one', 'red'), wifi: WT('one', 'wifi'), hdmi: WT('one', 'hdmi'), ranura: WT('one', 'ranura'), g5: WT('one', '5g'), disco: WT('one', 'disco'),
  router: WT('one', 'router'), vpn: WT('one', 'vpn'), lab: WT('one', 'laboratorio'),
  todos: WT('porque', 'todos'), reservas: WT('porque', 'reservas'), p20: WT('porque', '$20'), p379: WT('porque', '$379'), kick: WT('porque', 'kickstarter'),
  czero: WT('cierre', 'zero'), cerca: WT('cierre', 'cerca'), cone: WT('cierre', 'one'), redes: WT('cierre', 'redes'), hermanos: WT('cierre', 'hermanos'), gemelos: WT('cierre', 'gemelos'),
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
TR.forEach((tt, i) => GLITCH.push([tt, i === 3 ? 1.3 : 1]));
GLITCH.push([T.hacker, 0.45], [T.esperaban + 0.1, 0.5], [T.prohibir2, 0.4], [T.one, 0.6]);
addShake(T.prohibir, 26); addShake(T.hermano + 0.55, 18); addShake(T.prohibir2, 28); addShake(T.one, 30); addShake(TR[3], 20);
addShake(T.millon, 10); addShake(T.p379, 12); addShake(T.no, 10);

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
  [TR[0], TR[1], '1', 'EL FLIPPER ZERO', CYA], [TR[1], TR[2], '2', 'CÓMO FUNCIONA', CYA], [TR[2], TR[3], '3', 'LA POLÉMICA', RED],
  [TR[3], TR[4], '4', 'EL FLIPPER ONE', PUR], [TR[4], TR[5], '5', '¿POR QUÉ AHORA?', YEL], [TR[5], TR[6], 'ok', 'EN RESUMEN', GRN]];
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
const ZCOL = { faceTop: '#2b3a5e', faceBot: '#141c35', edge: '#0f1529', edgeDark: '#080c1a', rim: CYA };
const SIL = { faceTop: '#0b0916', faceBot: '#05040b', edge: '#06050d', edgeDark: '#030208', rim: PUR };
function drawZero(x, y, s, o = {}) {
  device(x, y, s, o, 460, 220, 72, 30, o.sil ? SIL : ZCOL, () => {
    g.fillStyle = '#3d1022'; rr(-210, -106, 76, 13, 6); g.fill();
    for (let i = 0; i < 8; i++) { circle(52 + i * 19, -97, 4.2); g.fillStyle = '#080d1c'; g.fill(); }
    circle(-125, -2, 70); g.fillStyle = '#0b1124'; g.fill(); g.lineWidth = 3; g.strokeStyle = rgba(CYA, 0.55); g.stroke();
    for (let k = 0; k < 4; k++) { g.save(); g.translate(-125, -2); g.rotate(k * Math.PI / 2); poly([[0, -59], [-12, -44], [12, -44]]); g.fillStyle = o.press === k ? YEL : '#5f6d8e'; g.fill(); g.restore(); }
    circle(-125, -2, 25); g.fillStyle = o.okCol || YEL; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
    circle(-30, 68, 15); g.fillStyle = '#0b1124'; g.fill(); g.strokeStyle = rgba(CYA, 0.55); g.lineWidth = 3; g.stroke();
    g.fillStyle = '#060a16'; rr(6, -88, 208, 154, 24); g.fill();
    screenArea(18, -76, 184, 130, 14, o.sil ? '#0a0716' : '#0b3743', o.screen);
    txt('ZERO', 165, 88, 24, o.sil ? PUR : CYA, { font: 'IX', stroke: 0 });
  });
}
const OCOL = { faceTop: '#30285a', faceBot: '#15112b', edge: '#100c22', edgeDark: '#090614', rim: PUR };
function drawOne(x, y, s, o = {}) {
  const asm = o.asm ?? 1, off = (1 - easeOut(asm)) * 950, fa = clamp(asm * 1.5);
  const ports = o.ports ?? 0, hl = o.hl || {};
  const cols = o.sil ? SIL : OCOL;
  if (asm < 1) { // piezas volando hacia su lugar
    g.save(); g.globalAlpha *= fa;
    device(x, y + off, s, { ...o, shine: -1 }, 600, 300, 56, 40, cols, () => {});
    g.restore();
    g.save(); g.translate(x, y); g.scale(s, s); g.globalAlpha *= fa;
    g.save(); g.translate(-off, 0); g.fillStyle = '#08060f'; rr(-272, -122, 344, 204, 24); g.fill(); g.lineWidth = 4; g.strokeStyle = PUR; g.stroke(); g.restore();
    g.save(); g.translate(off, -off * 0.3); circle(175, -35, 62); g.fillStyle = '#0d0a1f'; g.fill(); g.lineWidth = 4; g.strokeStyle = PUR; g.stroke(); g.restore();
    g.restore();
    return;
  }
  device(x, y, s, o, 600, 300, 56, 40, cols, () => {
    // ranuras de puertos en el borde de arriba
    const P = [[-215, 'rj'], [-145, 'rj'], [-60, 'hdmi'], [15, 'usbc'], [85, 'usba']];
    for (const [px, k] of P) {
      const on = (k === 'rj' && hl.red) || (k === 'hdmi' && hl.hdmi);
      g.save(); g.translate(px, -132);
      if (on) { g.shadowColor = YEL; g.shadowBlur = 25; }
      g.fillStyle = '#05040a'; g.strokeStyle = on ? YEL : rgba(PUR, 0.7); g.lineWidth = on ? 4 : 2.5;
      if (k === 'rj') { rr(-26, -12, 52, 26, 4); g.fill(); g.stroke(); g.fillStyle = '#c9a646'; for (let i = 0; i < 6; i++) g.fillRect(-17 + i * 6.5, -8, 3, 7); }
      if (k === 'hdmi') { poly([[-32, -9], [32, -9], [26, 9], [-26, 9]]); g.fill(); g.stroke(); }
      if (k === 'usbc') { rr(-19, -7, 38, 14, 7); g.fill(); g.stroke(); }
      if (k === 'usba') { rr(-24, -8, 48, 16, 3); g.fill(); g.stroke(); }
      g.restore();
    }
    // ranura M.2 en el costado
    g.save(); if (hl.m2) { g.shadowColor = YEL; g.shadowBlur = 25; } g.fillStyle = '#05040a'; rr(268, -50, 18, 110, 6); g.fill(); g.lineWidth = hl.m2 ? 4 : 2; g.strokeStyle = hl.m2 ? YEL : rgba(PUR, 0.7); g.stroke(); g.restore();
    // rejilla
    g.save(); g.strokeStyle = rgba(PUR, 0.35); g.lineWidth = 5; g.lineCap = 'round'; for (let i = 0; i < 7; i++) line(-262 + i * 22, 132, -248 + i * 22, 112); g.restore();
    // pantalla
    g.fillStyle = '#07050e'; rr(-272, -112, 344, 210, 24); g.fill();
    screenArea(-260, -100, 320, 186, 14, o.sil ? '#07050f' : '#0e0a20', o.screen);
    // controles
    circle(175, -25, 62); g.fillStyle = '#0d0a1f'; g.fill(); g.lineWidth = 3; g.strokeStyle = rgba(PUR, 0.6); g.stroke();
    for (let k = 0; k < 4; k++) { g.save(); g.translate(175, -25); g.rotate(k * Math.PI / 2); poly([[0, -52], [-11, -38], [11, -38]]); g.fillStyle = '#6f6390'; g.fill(); g.restore(); }
    circle(175, -25, 22); g.fillStyle = PUR; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
    for (const [bx, by] of [[118, 88], [175, 100], [232, 88]]) { circle(bx, by, 15); g.fillStyle = '#0d0a1f'; g.fill(); g.lineWidth = 3; g.strokeStyle = rgba(PUR, 0.6); g.stroke(); }
    txt('ONE', -40, 126, 24, PUR, { font: 'IX', stroke: 0 });
  });
}

// ---------------- contenido de pantallas ----------------
function scrWave(col, t, rec = 1, speed = 1) {
  return (w, h) => {
    g.save(); g.strokeStyle = col; g.lineWidth = 4; g.shadowColor = col; g.shadowBlur = 12; g.beginPath();
    const n = Math.floor(w * rec);
    for (let x = 0; x <= n; x += 3) { const u = x / w; const y = h / 2 + Math.sin(u * 30 + t * 9 * speed) * h * 0.22 * (Math.sin(u * 7 + t * 2) > 0 ? 1 : 0.25); x ? g.lineTo(x, y) : g.moveTo(x, y); }
    g.stroke(); g.restore();
  };
}
function scrText(lines, col, size = 30, t = 0) {
  return (w, h) => { lines.forEach((s, i) => txt(s, w / 2, h / 2 + (i - (lines.length - 1) / 2) * size * 1.25, size, col, { stroke: 0, maxW: w - 16 })); };
}
function scrRadar(col, t) {
  return (w, h) => {
    const cx = w / 2, cy = h / 2; g.save(); g.strokeStyle = rgba(col, 0.5); g.lineWidth = 2;
    for (let r = 18; r < 90; r += 24) { circle(cx, cy, r); g.stroke(); }
    const a = t * 4; g.fillStyle = rgba(col, 0.35); g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, 90, a - 0.6, a); g.closePath(); g.fill();
    g.restore();
  };
}
function scrQuestion(col, t) { return (w, h) => { txt('?', w / 2, h / 2 + 6, h * 0.8 * (1 + 0.06 * Math.sin(t * 8)), col, { stroke: 0, glow: col }); }; }
function scrLevel(level, xp, t) {
  return (w, h) => {
    txt('NIVEL ' + level, w / 2, h * 0.34, 36, '#7ff0ff', { stroke: 0 });
    rr(18, h * 0.62, w - 36, 26, 8); g.strokeStyle = '#7ff0ff'; g.lineWidth = 3; g.stroke();
    rr(22, h * 0.62 + 4, (w - 44) * clamp(xp), 18, 6); g.fillStyle = YEL; g.fill();
  };
}
function scrTerminal(t, t0) {
  const L = [['$ uname -o', 0], ['GNU/Linux', 0.55], ['$ _', 0.9]];
  return (w, h) => {
    L.forEach(([s, d], i) => {
      const n = Math.floor(clamp((t - t0 - d) / 0.4) * s.length); if (n <= 0) return;
      let shown = s.slice(0, n); if (s === '$ _') shown = Math.floor(t * 3) % 2 ? '$ _' : '$';
      txt(shown, 18, 36 + i * 50, 34, i === 1 ? GRN : '#d9c8ff', { font: 'IX', align: 'left', stroke: 0 });
    });
  };
}

// ---------------- íconos ----------------
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
function arcs(x, y, s, col, t, dir = 0, a = 1) { // ondas de wifi / contactless
  g.save(); g.translate(x, y); g.rotate(dir); g.lineCap = 'round';
  for (let k = 0; k < 3; k++) { const ph = (t * 2.2 - k * 0.3) % 1; g.strokeStyle = rgba(col, a * (0.35 + 0.65 * (1 - Math.abs(ph - 0.5) * 2))); g.lineWidth = s * 0.12; g.beginPath(); g.arc(0, 0, s * (0.35 + k * 0.32), -0.8, 0.8); g.stroke(); }
  g.restore();
}
function fob(x, y, s, col, press = 0) {
  g.save(); g.translate(x, y); g.scale(s, s);
  circle(0, -96, 18); g.lineWidth = 7; g.strokeStyle = GRY; g.stroke();
  rr(-55, -80, 110, 175, 44); g.fillStyle = '#1b2440'; g.fill(); g.lineWidth = 5; g.strokeStyle = col; g.stroke();
  for (let k = 0; k < 2; k++) { circle(0, -25 + k * 62, 22); g.fillStyle = (k === 0 && press > 0) ? YEL : '#0c1226'; g.fill(); g.lineWidth = 4; g.strokeStyle = rgba(col, 0.7); g.stroke(); }
  circle(0, -62, 5); g.fillStyle = press > 0 ? RED : '#3a2030'; g.fill();
  g.restore();
}
function gate(x, y, s, open, col) {
  g.save(); g.translate(x, y); g.scale(s, s);
  poly([[-130, -60], [0, -140], [130, -60]], false); g.lineWidth = 8; g.strokeStyle = col; g.lineJoin = 'round'; g.stroke();
  rr(-110, -60, 220, 170, 8); g.fillStyle = '#060a18'; g.fill(); g.lineWidth = 6; g.stroke();
  g.save(); rr(-104, -54, 208, 158, 6); g.clip();
  const oy = -open * 150;
  for (let i = 0; i < 6; i++) { rr(-100, -50 + i * 26 + oy, 200, 22, 4); g.fillStyle = i % 2 ? '#2a3a62' : '#33467a'; g.fill(); }
  if (open > 0.3) { const lg = g.createLinearGradient(0, 100, 0, -50); lg.addColorStop(0, rgba(YEL, 0.5 * open)); lg.addColorStop(1, rgba(YEL, 0)); g.fillStyle = lg; g.fillRect(-104, -54 + 158 * (1 - open), 208, 158 * open); }
  g.restore();
  circle(118, -78, 9); g.fillStyle = open > 0.05 ? GRN : RED; g.shadowColor = g.fillStyle; g.shadowBlur = 16; g.fill();
  g.restore();
}
function cardIcon(x, y, s, col, t, rot = 0) {
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s);
  rr(-115, -72, 230, 144, 18); const gr = g.createLinearGradient(-115, -72, 115, 72); gr.addColorStop(0, rgba(col, 0.95)); gr.addColorStop(1, rgba(col, 0.55)); g.fillStyle = gr; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  rr(-90, -30, 52, 42, 8); g.fillStyle = '#d8b350'; g.fill(); g.lineWidth = 3; g.strokeStyle = '#7a5a12'; g.stroke(); line(-64, -30, -64, 12); line(-90, -9, -38, -9);
  arcs(50, -10, 70, INK, t, 0, 0.9);
  rr(-90, 36, 120, 12, 6); g.fillStyle = rgba(INK, 0.45); g.fill();
  g.restore();
}
function tvIcon(x, y, s, col, on) {
  g.save(); g.translate(x, y); g.scale(s, s);
  line(-40, 92, 40, 92); g.lineWidth = 8; g.strokeStyle = GRY; line(0, 70, 0, 92); g.stroke(); line(-45, 94, 45, 94);
  rr(-120, -80, 240, 150, 14); g.fillStyle = '#05070f'; g.fill(); g.lineWidth = 6; g.strokeStyle = col; g.stroke();
  if (on > 0) { g.save(); rr(-110, -70, 220, 130, 8); g.clip(); const gr = g.createLinearGradient(-110, -70, 110, 60); gr.addColorStop(0, rgba(CYA, on)); gr.addColorStop(1, rgba(PUR, on)); g.fillStyle = gr; g.fillRect(-110, -70 + 65 * (1 - on), 220, 130 * on); g.restore(); }
  g.restore();
}
function carIcon(x, y, s, col, lights = 0, lightCol = RED) {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.beginPath(); g.moveTo(-170, 30); g.lineTo(-165, -10); g.quadraticCurveTo(-150, -30, -110, -34); g.lineTo(-70, -78); g.quadraticCurveTo(-55, -90, -20, -90); g.lineTo(55, -90); g.quadraticCurveTo(80, -88, 100, -60); g.lineTo(122, -34); g.quadraticCurveTo(165, -28, 172, 0); g.lineTo(172, 30); g.closePath();
  g.fillStyle = '#1d2a4c'; g.fill(); g.lineWidth = 6; g.strokeStyle = col; g.lineJoin = 'round'; g.stroke();
  poly([[-58, -40], [-30, -76], [10, -76], [10, -40]]); g.fillStyle = rgba(CYA, 0.35); g.fill();
  poly([[24, -40], [24, -76], [52, -76], [88, -40]]); g.fill();
  for (const wx of [-100, 105]) { circle(wx, 34, 34); g.fillStyle = '#05070f'; g.fill(); g.lineWidth = 6; g.strokeStyle = GRY; g.stroke(); circle(wx, 34, 12); g.fillStyle = GRY; g.fill(); }
  if (lights > 0) { for (const [lx, ly] of [[165, -6], [-162, -6]]) { circle(lx, ly, 12); g.fillStyle = lightCol; g.shadowColor = lightCol; g.shadowBlur = 40 * lights; g.globalAlpha = lights; g.fill(); g.globalAlpha = 1; } g.shadowBlur = 0; }
  g.restore();
}
function sdCard(x, y, s, col) {
  g.save(); g.translate(x, y); g.scale(s, s);
  poly([[-45, -60], [25, -60], [45, -40], [45, 60], [-45, 60]]); g.fillStyle = '#1c2a4f'; g.fill(); g.lineWidth = 5; g.strokeStyle = col; g.stroke();
  for (let i = 0; i < 5; i++) { g.fillStyle = '#d8b350'; g.fillRect(-34 + i * 14, -50, 9, 22); }
  g.restore();
}
function chip(x, y, s, col, cores = 0, t = 0, glow = 0) {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = '#c9a646'; g.lineWidth = 6;
  for (let i = -4; i <= 4; i++) { line(i * 24, -150, i * 24, -175); line(i * 24, 150, i * 24, 175); line(-150, i * 24, -175, i * 24); line(150, i * 24, 175, i * 24); }
  if (glow) { g.shadowColor = col; g.shadowBlur = 60 * glow; }
  rr(-150, -150, 300, 300, 26); g.fillStyle = '#141130'; g.fill(); g.shadowBlur = 0; g.lineWidth = 6; g.strokeStyle = col; g.stroke();
  for (let k = 0; k < 8; k++) {
    const cx = -84 + (k % 4) * 56, cy = -56 + Math.floor(k / 4) * 112;
    const on = clamp(cores - k);
    rr(cx - 24, cy - 44, 48, 88, 8); g.fillStyle = on > 0 ? rgba(YEL, 0.25 + 0.65 * on) : '#221d48'; if (on > 0) { g.shadowColor = YEL; g.shadowBlur = 20 * on; } g.fill(); g.shadowBlur = 0;
    g.lineWidth = 3; g.strokeStyle = on > 0 ? YEL : rgba(col, 0.5); g.stroke();
  }
  g.restore();
}
function laptop(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); rr(-80, -60, 160, 100, 8); g.fillStyle = '#0a0f22'; g.fill(); g.lineWidth = 6; g.strokeStyle = col; g.stroke(); poly([[-105, 50], [105, 50], [90, 66], [-90, 66]]); g.fillStyle = col; g.fill(); g.restore(); }
function phone(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); rr(-42, -78, 84, 156, 16); g.fillStyle = '#0a0f22'; g.fill(); g.lineWidth = 6; g.strokeStyle = col; g.stroke(); circle(0, 60, 6); g.fillStyle = col; g.fill(); g.restore(); }
function cloud(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); g.beginPath(); g.arc(-40, 10, 40, Math.PI * 0.5, Math.PI * 1.5); g.arc(0, -25, 50, Math.PI, 0); g.arc(48, 5, 38, Math.PI * 1.5, Math.PI * 0.5); g.closePath(); g.fillStyle = '#0a0f22'; g.fill(); g.lineWidth = 6; g.strokeStyle = col; g.stroke(); g.restore(); }
function lock(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); g.lineWidth = 10; g.strokeStyle = col; g.beginPath(); g.arc(0, -18, 26, Math.PI, 0); g.stroke(); rr(-40, -18, 80, 62, 10); g.fillStyle = col; g.fill(); circle(0, 10, 9); g.fillStyle = INK; g.fill(); g.restore(); }
function warnTri(x, y, s, col) { g.save(); g.translate(x, y); g.scale(s, s); poly([[0, -26], [28, 22], [-28, 22]]); g.fillStyle = col; g.lineJoin = 'round'; g.fill(); g.fillStyle = INK; g.fillRect(-3.5, -10, 7, 18); circle(0, 14, 4); g.fill(); g.restore(); }
function bubble(x, y, s, col, kind, t) {
  g.save(); g.translate(x, y); g.scale(s, s);
  rr(-70, -48, 140, 96, 30); poly([[-30, 40], [-50, 75], [5, 46]]); g.fillStyle = '#0b1026'; rr(-70, -48, 140, 96, 30); g.fill(); poly([[-30, 40], [-50, 75], [5, 46]]); g.fill();
  rr(-70, -48, 140, 96, 30); g.lineWidth = 5; g.strokeStyle = col; g.stroke();
  if (kind === 0) for (let k = 0; k < 3; k++) { circle(-32 + k * 32, 0, 10 + 3 * Math.sin(t * 8 + k)); g.fillStyle = col; g.fill(); }
  if (kind === 1) txt('!!', 0, 2, 64, col, { stroke: 0 });
  if (kind === 2) txt('?', 0, 4, 66, col, { stroke: 0 });
  if (kind === 3) { g.beginPath(); g.moveTo(0, 26); g.bezierCurveTo(-58, -12, -22, -48, 0, -20); g.bezierCurveTo(22, -48, 58, -12, 0, 26); g.fillStyle = col; g.fill(); }
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
function rays(x, y, col, t, a = 1, n = 12, R = 900) {
  g.save(); g.translate(x, y); g.rotate(t * 0.25); g.globalAlpha *= a;
  for (let k = 0; k < n; k++) { g.rotate(Math.PI * 2 / n); const gr = g.createLinearGradient(0, 0, R, 0); gr.addColorStop(0, rgba(col, 0.35)); gr.addColorStop(1, rgba(col, 0)); g.fillStyle = gr; poly([[0, 0], [R, -R * 0.09], [R, R * 0.09]]); g.fill(); }
  g.restore();
}
// texto de señal que viaja (código)
function codeTag(text, x, y, col, a = 1, s = 1) {
  g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s); g.font = '46px IX';
  const w = g.measureText(text).width + 40;
  rr(-w / 2, -34, w, 68, 14); g.fillStyle = 'rgba(5,8,22,0.9)'; g.fill(); g.lineWidth = 4; g.strokeStyle = col; g.stroke();
  g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 0, 2); g.restore();
}

// =====================================================================
// ESCENAS
// =====================================================================
function sceneHook(t) {
  const tint = t > T.prohibir ? `rgba(255,30,60,${0.12 * Math.min(1, (t - T.prohibir) / 0.2) * (t > T.hermano ? Math.max(0, 1 - (t - T.hermano) / 0.4) : 1)})` : null;
  drawBG(t, t > T.hermano ? PUR : CYA, tint);
  // hermano mayor que sube detrás
  if (t > T.hermano - 0.1) {
    const e = easeOut(prog(t, T.hermano - 0.1, T.hermano + 0.6));
    rays(600, 780, PUR, t, e * 0.8);
    const fl = t > T.esperaban ? (hash(Math.floor(t * 24), 3) < 0.25 ? 0.4 : 1) : 1;
    drawOne(600, lerp(2300, 800, e), 1.28, { sil: true, glow: 1, alpha: fl, shine: -1, screen: scrQuestion(PUR, t) });
  }
  const m = ease(prog(t, T.hermano, T.hermano + 0.6));
  const zx = lerp(540, 330, m), zy = lerp(830, 1050, m), zs = lerp(1.3, 0.78, m);
  waveRings(zx, zy, CYA, t, 0, 3, 560, 0.5, 0.7 * (1 - m * 0.6));
  drawZero(zx, zy, zs, { yaw: 0.25 * Math.sin(t * 1.4), rot: -0.06, glow: 0.8, screen: scrRadar('#7ff0ff', t) });
  // CANADÁ y sello
  if (t > T.canada - 0.05) {
    const a = 1 - prog(t, T.hermano, T.hermano + 0.3);
    const e = backOut(prog(t, T.canada - 0.05, T.canada + 0.3));
    g.save(); g.globalAlpha = a; txt('CANADÁ', lerp(-300, 540, e), 520, 120, RED, { stroke: 10, glow: RED }); g.restore();
  }
  stamp('¿PROHIBIDO?', zx, zy, 92 * zs / 1.3, RED, t, T.prohibir, -0.18, 1 - prog(t, T.hermano + 0.1, T.hermano + 0.4));
  if (t > T.hermano + 0.25) pill('HERMANO MAYOR', 540, 470, PUR, 60, t, T.hermano + 0.35, { solid: true });
}
function sceneZero(t) {
  drawBG(t, CYA);
  const a0 = Z0[0] - 0.22;
  const ent = backOut(prog(t, a0, a0 + 0.6));
  const m = ease(prog(t, T.segun - 0.1, T.segun + 0.5));
  const x = 540, y = lerp(800, 590, m) + 10 * Math.sin(t * 2.2), s = lerp(0.2, 1.35, ent) * lerp(1, 0.55, m);
  rays(540, y, CYA, t, 0.5 * (1 - m));
  drawZero(x, y, s, { yaw: lerp(-1.1, 0, ent) + 0.2 * Math.sin(t * 1.1), glow: 1, screen: t < T.zero + 0.4 ? scrText(['¡HOLA!'], '#7ff0ff', 46) : scrWave('#7ff0ff', t) });
  pill('CABE EN LA MANO', 400, 450, CYA, 54, t, T.mano, { alpha: 1 - m });
  // etiqueta de precio
  if (t > T.p169 - 0.1) {
    const e = backOut(prog(t, T.p169 - 0.1, T.p169 + 0.35)), a = 1 - prog(t, T.segun - 0.1, T.segun + 0.2);
    const sw = Math.sin((t - T.p169) * 6) * 0.25 * Math.exp(-(t - T.p169) * 1.5);
    const px = 850, py = lerp(150, 610, e);
    g.save(); g.globalAlpha = a; g.strokeStyle = GRY; g.lineWidth = 4; line(px, 0, px, py - 80);
    g.translate(px, py); g.rotate(0.12 + sw);
    poly([[-115, -62], [80, -62], [125, 0], [80, 62], [-115, 62]]); g.fillStyle = YEL; g.shadowColor = YEL; g.shadowBlur = 30; g.fill(); g.shadowBlur = 0; g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
    circle(88, 0, 11); g.fillStyle = INK; g.fill();
    txt('$' + counter(t, T.p169 - 0.05, T.p169 + 0.45, 0, 169), -24, 4, 76, INK, { stroke: 0 });
    g.restore();
  }
  // un millón de aparatos
  if (t > T.segun - 0.1) {
    pill('SEGÚN SU CREADOR', 540, 1295, CYA, 40, t, T.segun, { font: 'IX' });
    const cols = 11, rows = 6, cx0 = 540, cy0 = 960;
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
      const dx = (i - (cols - 1) / 2), dy = (j - (rows - 1) / 2);
      const d = Math.hypot(dx, dy * 1.4); const ta = T.segun + 0.1 + d * 0.09;
      if (t < ta) continue;
      const e = backOut(prog(t, ta, ta + 0.25));
      g.save(); g.translate(cx0 + dx * 88, cy0 + dy * 62); g.scale(e, e);
      rr(-34, -16, 68, 32, 11); g.fillStyle = hash(i, j) < 0.15 ? rgba(YEL, 0.8) : rgba(CYA, 0.55); g.fill();
      rr(2, -9, 24, 18, 4); g.fillStyle = '#0b3743'; g.fill(); circle(-16, 0, 7); g.fillStyle = INK; g.fill();
      g.restore();
    }
    const v = counter(t, T.segun + 0.1, T.millon + 0.3, 0, 1000000);
    const e = backOut(prog(t, T.segun, T.segun + 0.3));
    g.save(); g.translate(540, 1185); g.scale(e, e); txt('≈ ' + fmt(v), 0, 0, 118, YEL, { stroke: 11, glow: YEL }); g.restore();
  }
}
function sceneListen(t) {
  drawBG(t, CYA);
  const a0 = F0[0] - 0.22;
  const steps = [['1', 'ESCUCHA', T.escucha], ['2', 'GUARDA', T.guarda], ['3', 'REPITE', T.repite]];
  steps.forEach(([n, s, ts], i) => {
    const x = 200 + i * 340, on = t > ts - 0.05, e = backOut(prog(t, ts - 0.05, ts + 0.3));
    const ap = backOut(prog(t, a0 + 0.1 + i * 0.1, a0 + 0.4 + i * 0.1));
    g.save(); g.translate(x, 470); g.scale(ap * (on ? lerp(1, 1.1, e) : 0.92), ap * (on ? lerp(1, 1.1, e) : 0.92));
    rr(-150, -50, 300, 100, 50); g.fillStyle = on ? YEL : 'rgba(5,8,22,0.85)'; if (on) { g.shadowColor = YEL; g.shadowBlur = 30; } g.fill(); g.shadowBlur = 0; g.lineWidth = 5; g.strokeStyle = on ? INK : rgba(CYA, 0.5); g.stroke();
    txt(n + ' ' + s, 0, 3, 44, on ? INK : rgba(WHT, 0.6), { stroke: 0, maxW: 270 });
    g.restore();
  });
  // control → Flipper → portón
  const fx = 180, fy = 760, zx = 540, zy = 1020, gx = 890, gy = 790;
  fob(fx, fy, 0.95, CYA, t > T.escucha - 0.1 && t < T.escucha + 0.5 ? 1 : 0);
  const op = easeOut(prog(t, T.repite + 0.35, T.repite + 1.1));
  gate(gx, gy, 0.95, op, op > 0.5 ? GRN : CYA);
  // ondas de ida
  if (t > T.escucha - 0.05 && t < T.guarda + 0.3) {
    g.save(); g.strokeStyle = YEL; g.lineWidth = 7; g.shadowColor = YEL; g.shadowBlur = 16; g.lineCap = 'round';
    for (let k = 0; k < 4; k++) { const f = ((t - T.escucha) * 1.3 - k * 0.22); if (f < 0 || f > 1) continue; const px = lerp(fx + 40, zx - 120, f), py = lerp(fy + 40, zy - 60, f); g.save(); g.translate(px, py); g.rotate(Math.atan2(zy - fy, zx - fx)); g.beginPath(); for (let u = -40; u <= 40; u += 4) { const yy = Math.sin(u * 0.25) * 14; u === -40 ? g.moveTo(u, yy) : g.lineTo(u, yy); } g.stroke(); g.restore(); }
    g.restore();
  }
  if (t > T.repite) {
    g.save(); g.strokeStyle = YEL; g.lineWidth = 7; g.shadowColor = YEL; g.shadowBlur = 16; g.lineCap = 'round';
    for (let k = 0; k < 5; k++) { const f = ((t - T.repite) * 1.4 - k * 0.2); if (f < 0 || f > 1) continue; const px = lerp(zx + 130, gx - 90, f), py = lerp(zy - 60, gy + 20, f); g.save(); g.translate(px, py); g.rotate(Math.atan2(gy - zy, gx - zx)); g.beginPath(); for (let u = -40; u <= 40; u += 4) { const yy = Math.sin(u * 0.25) * 14; u === -40 ? g.moveTo(u, yy) : g.lineTo(u, yy); } g.stroke(); g.restore(); }
    g.restore();
  }
  const rec = prog(t, T.escucha + 0.3, T.guarda);
  let scr;
  if (t < T.escucha) scr = scrQuestion('#7ff0ff', t);
  else if (t < T.guarda) scr = (w, h) => { scrWave(YEL, t, rec, 0)(w, h); circle(w - 22, 20, 9); g.fillStyle = Math.floor(t * 4) % 2 ? RED : 'rgba(255,77,94,0.3)'; g.fill(); txt('REC', w - 58, 21, 22, RED, { stroke: 0 }); };
  else if (t < T.repite) scr = (w, h) => { txt('GUARDADO', w / 2, h * 0.36, 34, GRN, { stroke: 0 }); check(w / 2, h * 0.72, 44, GRN, 0.2); };
  else scr = scrWave(YEL, t, 1, 1.5);
  drawZero(zx, zy, 1.0, { yaw: 0.15 * Math.sin(t * 1.3), glow: 0.8, screen: scr });
  if (t > T.guarda - 0.05) {
    const e = backOut(prog(t, T.guarda - 0.05, T.guarda + 0.35)), a = 1 - prog(t, T.repite + 0.6, T.repite + 0.9);
    g.save(); g.globalAlpha = a; sdCard(zx, lerp(zy, zy - 250, e), 1.1 * e, GRN); if (e > 0.8) { circle(zx + 55, zy - 300, 30); g.fillStyle = GRN; g.fill(); check(zx + 55, zy - 300, 36, INK, 0.2); } g.restore();
  }
  burst(gx, gy, t, T.repite + 1.0, GRN, 10, 200);
}
function sceneModules(t) {
  drawBG(t, CYA);
  const cards = [
    [T.radio, CYA, 'RADIO', 'controles de portones', 'gate'],
    [T.nfc, YEL, 'NFC · RFID', 'tarjetas de acceso', 'card'],
    [T.ir, PINK, 'INFRARROJO', 'teles y aires', 'tv']];
  const active = cards.reduce((a, c, i) => t > c[0] - 0.1 ? i : a, -1);
  // aparato pequeño arriba emitiendo
  drawZero(540, 480 + 6 * Math.sin(t * 2), 0.5, { glow: 0.6, screen: scrWave(active >= 0 ? cards[active][1] : '#7ff0ff', t) });
  cards.forEach(([ts, col, title, sub, ic], i) => {
    if (t < ts - 0.15) return;
    const e = backOut(prog(t, ts - 0.15, ts + 0.3)), y = 720 + i * 240;
    const on = i === active;
    g.save(); g.translate(lerp(1500, 540, e), y); g.scale(on ? 1.03 : 0.97, on ? 1.03 : 0.97); g.globalAlpha = on ? 1 : 0.6;
    rr(-470, -105, 940, 210, 34); g.fillStyle = 'rgba(6,10,26,0.92)'; g.fill(); g.lineWidth = 6; g.strokeStyle = col; if (on) { g.shadowColor = col; g.shadowBlur = 35; } g.stroke(); g.shadowBlur = 0;
    g.save(); rr(-470, -105, 210, 210, 34); g.clip(); g.fillStyle = rgba(col, 0.16); g.fillRect(-470, -105, 210, 210); g.restore();
    if (ic === 'gate') gate(-365, 15, 0.52, 0.5 + 0.5 * Math.sin((t - ts) * 3), col);
    if (ic === 'card') cardIcon(-365, 0, 0.62, col, t, -0.1);
    if (ic === 'tv') tvIcon(-365, -5, 0.6, col, Math.floor((t - ts) * 2.2) % 2 ? 1 : 0);
    txt(title, -220, -28, 76, col, { align: 'left', stroke: 0, maxW: 660 });
    txt(sub, -220, 46, 44, WHT, { font: 'IX', align: 'left', stroke: 0, maxW: 660 });
    g.restore();
  });
}
function scenePet(t) {
  drawBG(t, CYA);
  const a0 = F2[0] - 0.1, t1 = F2[1];
  const lv = 1 + Math.floor(clamp((t - T.delfin - 0.2) / Math.max(0.5, (t1 - T.delfin - 0.2))) * 3.999);
  const xp = ((t - T.delfin - 0.2) / Math.max(0.5, (t1 - T.delfin - 0.2)) * 4) % 1;
  // íconos que orbitan y entran
  for (let k = 0; k < 6; k++) {
    const an = t * 1.6 + k * Math.PI / 3, f = ((t * 0.9 + k / 6) % 1);
    const r = lerp(420, 120, easeOut(f)), x = 540 + Math.cos(an) * r, y = 900 + Math.sin(an) * r * 0.75;
    g.save(); g.globalAlpha = (1 - f) * prog(t, a0, a0 + 0.3);
    if (k % 3 === 0) arcs(x, y, 60, CYA, t, an); else if (k % 3 === 1) cardIcon(x, y, 0.28, YEL, t); else tvIcon(x, y, 0.28, PINK, 1);
    g.restore();
    if (f > 0.85) txt('+XP', x, y - 40 - (f - 0.85) * 300, 40, YEL, { stroke: 6, alpha: (1 - f) * 6 });
  }
  const e = backOut(prog(t, a0, a0 + 0.4));
  drawZero(540, 900 + 8 * Math.sin(t * 2.5), 1.55 * lerp(0.6, 1, e), { glow: 1, yaw: 0.12 * Math.sin(t), screen: t < T.delfin ? scrText(['MASCOTA', 'VIRTUAL'], '#7ff0ff', 32) : scrLevel(lv, xp, t) });
  pill('MASCOTA VIRTUAL', 540, 520, YEL, 58, t, T.delfin, { solid: true });
  for (let k = 1; k < 4; k++) { const tl = T.delfin + 0.2 + k * (t1 - T.delfin - 0.2) / 4; burst(540, 880, t, tl, YEL, 12, 330); if (t > tl && t < tl + 0.7) txt('¡SUBE DE NIVEL!', 540, 1220 - 30 * easeOut(prog(t, tl, tl + 0.3)), 66, YEL, { stroke: 8, alpha: 1 - prog(t, tl + 0.45, tl + 0.7), glow: YEL }); }
}
function sceneCanada(t) {
  const red = prog(t, T.canada2 - 0.1, T.canada2 + 0.3);
  drawBG(t, red > 0 ? RED : CYA, `rgba(255,20,50,${0.14 * red * (0.75 + 0.25 * Math.sin(t * 9))})`);
  // año con rodillo
  const e = backOut(prog(t, P0[0] - 0.2, P0[0] + 0.25));
  g.save(); g.translate(540, 500); g.scale(e, e);
  const yr = t < T.y2024 ? String(2000 + counter(t, P0[0] - 0.2, T.y2024, 0, 24)).padStart(4, '0') : '2024';
  txt(yr, 0, 0, 170, WHT, { stroke: 12, glow: red > 0 ? RED : CYA });
  g.restore();
  if (t > T.canada2 - 0.1) { const e2 = backOut(prog(t, T.canada2 - 0.1, T.canada2 + 0.25)); g.save(); g.translate(540, 640); g.scale(e2, e2); rr(-230, -50, 460, 100, 20); g.fillStyle = RED; g.shadowColor = RED; g.shadowBlur = 30; g.fill(); g.shadowBlur = 0; txt('CANADÁ', 0, 4, 76, WHT, { stroke: 0 }); g.restore(); }
  const m = ease(prog(t, T.autos - 0.2, T.autos + 0.3));
  const zx = lerp(540, 330, m), zy = lerp(960, 900, m);
  drawZero(zx, zy, lerp(1.2, 0.9, m), { glow: 0.8, okCol: RED, screen: scrWave(t > T.prohibir2 ? RED : '#7ff0ff', t) });
  stamp('PROHIBIDO', zx, zy, 96 * lerp(1, 0.8, m), RED, t, T.prohibir2, -0.16);
  if (t > T.autos - 0.15) {
    const e3 = backOut(prog(t, T.autos - 0.15, T.autos + 0.25));
    const bl = Math.floor(t * 6) % 2 ? 1 : 0.2;
    carIcon(lerp(1400, 790, e3), 1150, 1.05, RED, bl);
    pill('ROBOS DE AUTOS', 790, 1300, RED, 44, t, T.autos + 0.1);
  }
}
function sceneRolling(t) {
  const a0 = P1[0] - 0.12;
  const done = prog(t, T.no - 0.1, T.no + 0.25);
  drawBG(t, done > 0 ? GRN : CYA);
  const fx = 190, fy = 760, cx = 790, cy = 800;
  const codes = ['A7F3', '19C2', 'E04B'];
  const clicks = [a0 + 0.35, T.cambian + 0.1, T.clic - 0.35];
  pill('UN CÓDIGO NUEVO EN CADA CLIC', 540, 470, YEL, 46, t, T.cambian, { solid: true });
  const pressing = clicks.some(c => t > c && t < c + 0.25);
  fob(fx, fy, 1.0, CYA, pressing ? 1 : 0);
  let lights = 0, lcol = GRN;
  clicks.forEach((c, i) => {
    if (t < c) return;
    const f = prog(t, c, c + 0.7);
    if (f < 1) codeTag(codes[i], lerp(fx + 60, cx - 130, easeOut(f)), lerp(fy - 150, cy - 170, easeOut(f)) - Math.sin(f * Math.PI) * 60, YEL, 1 - prog(f, 0.85, 1));
    if (t > c + 0.6 && t < c + 1.0) lights = Math.max(lights, Math.floor((t - c) * 12) % 2 ? 1 : 0.3);
    // historial de códigos usados
    const hx = 270 + i * 210, hy = 1040;
    if (t > c + 0.7) { const ee = backOut(prog(t, c + 0.7, c + 0.95)); codeTag(codes[i], hx + 60, hy, '#c3cbe0', 0.95, ee); if (i === 0) txt('YA USADOS', 540, hy + 60, 34, GRY, { font: 'IX', stroke: 0, alpha: prog(t, c + 0.8, c + 1.0) }); }
  });
  // el Flipper copia el primero y lo repite: el auto lo rechaza
  const zx = 540, zy = 1230;
  const tr = T.clic + 0.15;
  drawZero(zx, zy, 0.55, { glow: 0.6, screen: t > clicks[0] + 0.3 ? scrText(['A7F3'], YEL, 40) : scrRadar('#7ff0ff', t) });
  if (t > tr) {
    const f = prog(t, tr, tr + 0.6);
    if (f < 1) codeTag('A7F3', lerp(zx + 80, cx - 60, easeOut(f)), lerp(zy - 90, cy + 60, easeOut(f)), RED, 1);
    if (t > tr + 0.55) { lights = Math.floor((t - tr) * 10) % 2 ? 1 : 0.2; lcol = RED; }
  }
  carIcon(cx, cy, 1.15, lcol === RED && t > tr + 0.55 ? RED : CYA, lights, lcol);
  if (t > tr + 0.55) pill('CÓDIGO VIEJO', cx, cy - 190, RED, 44, t, tr + 0.6, { icon: 'cross' });
  // ya no se prohibió
  if (done > 0) {
    g.save(); g.globalAlpha = done * 0.6; g.fillStyle = '#02050f'; g.fillRect(0, 380, W, 980); g.restore();
    stamp('PROHIBIDO', 540, 760, 100, RED, t, T.no - 0.25, -0.16, 1 - prog(t, T.no, T.no + 0.25));
    pill('NO LO PROHIBIÓ', 540, 840, GRN, 84, t, T.no + 0.05, { solid: true, icon: 'check' });
  }
  // aviso legal
  const al = prog(t, a0 + 0.3, a0 + 0.6);
  g.save(); g.globalAlpha = al; rr(160, 1312, 760, 66, 33); g.fillStyle = 'rgba(5,8,22,0.88)'; g.fill(); g.lineWidth = 3; g.strokeStyle = rgba(YEL, 0.8); g.stroke();
  warnTri(208, 1346, 0.9, YEL); txt('Usarlo en lo ajeno es ilegal', 560, 1347, 38, WHT, { font: 'IX', stroke: 0 }); g.restore();
}
function sceneOneReveal(t) {
  const a0 = O0[0] - 0.2;
  drawBG(t, PUR, `rgba(120,40,255,${0.10 + 0.08 * Math.exp(-Math.max(0, t - T.one) * 2)})`);
  const asm = prog(t, a0 + 0.05, T.one + 0.05);
  rays(540, 820, PUR, t, asm);
  if (t > T.one - 0.05) burst(540, 820, t, T.one, PUR, 16, 560);
  const lift = ease(prog(t, T.zero2 - 0.2, T.zero2 + 0.3));
  drawOne(540, lerp(840, 800, lift) + 8 * Math.sin(t * 2), 1.4, { asm, glow: 1, screen: t < T.compu ? scrText(['FLIPPER', 'ONE'], '#d9c8ff', 52) : scrTerminal(t, T.compu - 0.05) });
  if (t > T.one - 0.1) { const e = backOut(prog(t, T.one - 0.1, T.one + 0.3)); g.save(); g.translate(540, 470); g.scale(e, e); txt('FLIPPER ONE', 0, 0, 120, WHT, { stroke: 10, glow: PUR, glowR: 50 }); g.restore(); }
  if (t > T.zero2 - 0.1) {
    const a = 1 - prog(t, T.compu - 0.1, T.compu + 0.15);
    const e = backOut(prog(t, T.zero2 - 0.1, T.zero2 + 0.25));
    g.save(); g.globalAlpha = a; g.translate(540, 1170); g.scale(e, e);
    txt('ZERO 2', 0, 0, 120, GRY, { stroke: 10 });
    const sw = easeOut(prog(t, T.zero2 + 0.2, T.zero2 + 0.45)); g.strokeStyle = RED; g.lineWidth = 16; g.lineCap = 'round'; g.shadowColor = RED; g.shadowBlur = 20; line(-230, 10, lerp(-230, 230, sw), 10 - 30 * sw);
    g.restore();
  }
  pill('COMPUTADORA', 330, 1170, YEL, 52, t, T.compu, { solid: true });
  pill('LINUX', 800, 1170, CYA, 52, t, T.linux, { solid: true });
  if (t > T.linux + 0.35) txt('de bolsillo', 540, 1285, 50, WHT, { font: 'IX', stroke: 6, alpha: prog(t, T.linux + 0.35, T.linux + 0.6) });
}
function sceneSpecs(t) {
  drawBG(t, PUR);
  const a0 = O1[0] - 0.1;
  const out = ease(prog(t, T.rpi - 0.25, T.rpi + 0.2));
  if (out < 1) {
    g.save(); g.globalAlpha = 1 - out; g.translate(0, -out * 300);
    const e = backOut(prog(t, a0, a0 + 0.4));
    const cores = clamp((t - a0 - 0.15) / Math.max(0.3, T.nucleos + 0.25 - a0 - 0.15)) * 8;
    chip(540, 690, 0.95 * e, PUR, cores, t, cores >= 8 ? 1 : 0.3);
    if (cores > 0.2) txt(Math.min(8, Math.ceil(cores)) + ' NÚCLEOS', 540, 905, 72, YEL, { stroke: 8, glow: YEL });
    if (t > T.gb - 0.15) {
      const e2 = backOut(prog(t, T.gb - 0.15, T.gb + 0.25));
      g.save(); g.translate(lerp(-600, 540, e2), 1060);
      rr(-330, -48, 660, 96, 10); g.fillStyle = '#123a2c'; g.fill(); g.lineWidth = 5; g.strokeStyle = GRN; g.stroke();
      for (let k = 0; k < 8; k++) { rr(-300 + k * 76, -32, 60, 50, 6); g.fillStyle = '#05070f'; g.fill(); }
      g.fillStyle = '#d8b350'; for (let k = 0; k < 40; k++) g.fillRect(-310 + k * 15.5, 34, 9, 12);
      g.restore();
      txt('8 GB DE RAM', lerp(-600, 540, e2), 1170, 64, GRN, { stroke: 8 });
    }
    if (t > T.ia - 0.15) {
      const e3 = backOut(prog(t, T.ia - 0.15, T.ia + 0.3));
      g.save(); g.translate(860, 560); g.scale(e3, e3);
      circle(0, 0, 120); g.fillStyle = 'rgba(8,6,22,0.92)'; g.fill(); g.lineWidth = 6; g.strokeStyle = CYA; g.shadowColor = CYA; g.shadowBlur = 30; g.stroke(); g.shadowBlur = 0;
      const N = [[-60, -40], [-60, 0], [-60, 40], [0, -55], [0, -18], [0, 18], [0, 55], [60, -25], [60, 25]];
      g.lineWidth = 3; for (let i = 0; i < 3; i++) for (let j = 3; j < 7; j++) { g.strokeStyle = rgba(CYA, 0.3 + 0.5 * (0.5 + 0.5 * Math.sin(t * 6 + i + j))); line(N[i][0], N[i][1], N[j][0], N[j][1]); }
      for (let j = 3; j < 7; j++) for (let k = 7; k < 9; k++) { g.strokeStyle = rgba(CYA, 0.3 + 0.5 * (0.5 + 0.5 * Math.sin(t * 6 + j * k))); line(N[j][0], N[j][1], N[k][0], N[k][1]); }
      N.forEach(([x, y], i) => { circle(x, y, 9); g.fillStyle = (Math.floor(t * 8) + i) % 4 === 0 ? YEL : CYA; g.fill(); });
      g.restore();
      pill('CHIP DE IA', 860, 720, CYA, 40, t, T.ia + 0.1, { solid: true });
    }
    g.restore();
  }
  if (out > 0) {
    const gr = easeOut(prog(t, T.rpi, T.rpi + 0.9));
    const bars = [[330, 'FLIPPER ONE', PUR], [750, 'RASPBERRY PI 5', GRN]];
    bars.forEach(([x, label, col], i) => {
      const h = 470 * gr * (i ? 1 : 0.985), base = 1230;
      g.save(); g.globalAlpha = out;
      rr(x - 110, base - h, 220, h, 18); const lg = g.createLinearGradient(0, base - h, 0, base); lg.addColorStop(0, col); lg.addColorStop(1, rgba(col, 0.35)); g.fillStyle = lg; g.shadowColor = col; g.shadowBlur = 30; g.fill(); g.shadowBlur = 0; g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
      txt(label, x, base + 55, 46, col, { stroke: 6, maxW: 380 });
      g.restore();
    });
    if (gr > 0.6) { const e = backOut(prog(t, T.rpi + 0.55, T.rpi + 0.85)); g.save(); g.translate(540, 900); g.scale(e, e); txt('≈', 0, 0, 200, YEL, { stroke: 12, glow: YEL }); g.restore(); }
    pill('POTENCIA PARECIDA', 540, 520, YEL, 52, t, T.rpi + 0.2, { solid: true });
  }
}
function scenePorts(t) {
  drawBG(t, PUR);
  const zo = ease(prog(t, T.router - 0.35, T.router + 0.15));
  const ox = 540, oy = lerp(800, 870, zo), os = lerp(1.3, 0.62, zo);
  // red alrededor (fase B)
  if (zo > 0) {
    const N = [[220, 600, 'laptop'], [860, 600, 'phone'], [210, 1150, 'tv'], [870, 1150, 'cloud']];
    g.save(); g.globalAlpha = zo;
    N.forEach(([x, y]) => { g.strokeStyle = rgba(CYA, 0.35); g.lineWidth = 4; g.setLineDash([12, 12]); g.lineDashOffset = -t * 40; line(ox, oy, x, y); g.setLineDash([]); packet(ox, oy, x, y, t, 0.8, CYA, 2, 8); packet(x, y, ox, oy, t + 0.3, 0.6, YEL, 1, 7); });
    if (t > T.lab - 0.1) {
      const f = easeOut(prog(t, T.lab - 0.1, T.lab + 0.8));
      for (let k = 0; k < 18; k++) {
        const an = hash(k, 1) * Math.PI * 2, r = 330 + 230 * hash(k, 2), x = ox + Math.cos(an) * r * f, y = oy + Math.sin(an) * r * 0.9 * f;
        g.strokeStyle = rgba(PUR, 0.4); g.lineWidth = 2; const j = (k * 7) % 18; const an2 = hash(j, 1) * Math.PI * 2, r2 = 330 + 230 * hash(j, 2);
        line(x, y, ox + Math.cos(an2) * r2 * f, oy + Math.sin(an2) * r2 * 0.9 * f);
        circle(x, y, 9); g.fillStyle = k % 3 ? PUR : YEL; g.fill();
      }
    }
    laptop(N[0][0], N[0][1], 0.8, CYA); phone(N[1][0], N[1][1], 0.75, CYA); tvIcon(N[2][0], N[2][1], 0.55, CYA, 1); cloud(N[3][0], N[3][1], 0.9, CYA);
    if (t > T.vpn - 0.1) {
      const f = easeOut(prog(t, T.vpn - 0.1, T.vpn + 0.4));
      g.save(); g.lineCap = 'round'; g.strokeStyle = rgba(YEL, 0.35); g.lineWidth = 46; line(ox, oy, lerp(ox, N[3][0], f), lerp(oy, N[3][1], f)); g.strokeStyle = YEL; g.lineWidth = 6; g.shadowColor = YEL; g.shadowBlur = 20; line(ox, oy, lerp(ox, N[3][0], f), lerp(oy, N[3][1], f)); g.restore();
      if (f > 0.5) lock(lerp(ox, N[3][0], 0.5), lerp(oy, N[3][1], 0.5), 0.9 * backOut(prog(t, T.vpn + 0.15, T.vpn + 0.45)), YEL);
    }
    g.restore();
    pill('ROUTER', 540, 470, CYA, 54, t, T.router, { solid: true });
    pill('VPN', 820, 1010, YEL, 50, t, T.vpn + 0.1, { solid: true });
    pill('LABORATORIO DE REDES', 540, 1330, PUR, 46, t, T.lab + 0.1, { solid: true });
  }
  // módulo M.2 que entra
  const modIn = (ts, tsOut, label, col) => {
    if (t < ts - 0.15 || t > tsOut + 0.3) return;
    const ein = easeOut(prog(t, ts - 0.15, ts + 0.25)), eout = ease(prog(t, tsOut, tsOut + 0.3));
    const mx = lerp(1250, 780, ein) + eout * 500;
    g.save(); g.translate(0, oy - 800); g.translate(ox, 800); g.scale(os / 1.3, os / 1.3); g.translate(-ox, -800);
    g.translate(mx, 805); rr(-110, -42, 220, 84, 8); g.fillStyle = '#103026'; g.fill(); g.lineWidth = 5; g.strokeStyle = col; g.shadowColor = col; g.shadowBlur = 25; g.stroke(); g.shadowBlur = 0;
    g.fillStyle = '#d8b350'; for (let k = 0; k < 7; k++) g.fillRect(-106, -34 + k * 10, 10, 6);
    txt(label, 20, 3, 54, col, { stroke: 0 });
    g.restore();
  };
  modIn(T.g5, T.disco - 0.2, '5G', CYA);
  modIn(T.disco, T.router - 0.35, 'SSD', GRN);
  drawOne(ox, oy + 6 * Math.sin(t * 2), os, { glow: 0.9, hl: { red: t > T.red - 0.1 && zo < 1, hdmi: t > T.hdmi - 0.1 && zo < 1, m2: t > T.ranura - 0.1 && zo < 1 }, screen: zo > 0.5 ? scrText(['ROUTER'], CYA, 52) : scrWave('#d9c8ff', t) });
  if (zo < 1) {
    g.save(); g.globalAlpha = 1 - zo;
    const call = (ts, x, y, px, py, label, col) => { if (t < ts - 0.1) return; const e = easeOut(prog(t, ts - 0.1, ts + 0.2)); g.save(); g.strokeStyle = col; g.lineWidth = 4; line(px, py, lerp(px, x, e), lerp(py, y + 40, e)); g.restore(); pill(label, x, y, col, 48, t, ts, { solid: true }); };
    call(T.red, 240, 510, 540 + (-180) * 1.3, 800 - 132 * 1.3, '2× RED', YEL);
    call(T.hdmi, 560, 450, 540 + (-60) * 1.3, 800 - 132 * 1.3, 'HDMI', YEL);
    call(T.ranura, 830, 1100, 540 + 277 * 1.3, 800 + 60 * 1.3, 'RANURA M.2', YEL);
    if (t > T.wifi - 0.1) { arcs(540 + 330, 800 - 240, 120, CYA, t, -0.9, prog(t, T.wifi - 0.1, T.wifi + 0.2)); pill('WIFI', 900, 470, CYA, 48, t, T.wifi, { solid: true }); }
    g.restore();
  }
}
function sceneWhy(t) {
  drawBG(t, YEL);
  const a0 = R0[0] - 0.22;
  const e = backOut(prog(t, a0, a0 + 0.4));
  drawOne(540, 760 + 8 * Math.sin(t * 2), 0.82 * e, { glow: 1, screen: t < T.reservas ? scrQuestion('#d9c8ff', t) : scrText(['RESERVAS', 'ABIERTAS'], GRN, 40) });
  // todos hablan: globos
  const fadeB = 1 - prog(t, T.reservas, T.reservas + 0.3);
  for (let k = 0; k < 9; k++) {
    const tb = T.todos - 0.2 + k * 0.11; if (t < tb) continue;
    const x = [170, 900, 260, 820, 150, 930, 400, 690, 540][k], y = [560, 540, 1010, 1020, 790, 800, 470, 1080, 1130][k];
    const s = backOut(prog(t, tb, tb + 0.25)) * 0.85;
    g.save(); g.globalAlpha = fadeB; bubble(x, y + 6 * Math.sin(t * 3 + k), s, [CYA, YEL, PINK, GRN][k % 4], k % 4, t); g.restore();
  }
  pill('RESERVAS ABIERTAS', 540, 470, GRN, 54, t, T.reservas, { icon: 'dot' });
  // boleto de $20
  if (t > T.p20 - 0.15) {
    const e2 = backOut(prog(t, T.p20 - 0.15, T.p20 + 0.3));
    g.save(); g.translate(lerp(-400, 290, e2), 1140); g.rotate(-0.07);
    g.beginPath(); g.moveTo(-190, -95); g.lineTo(190, -95); g.arc(190, 0, 0.01, 0, 0); g.lineTo(190, -25); g.arc(190, 0, 25, -Math.PI / 2, Math.PI / 2, true); g.lineTo(190, 95); g.lineTo(-190, 95); g.lineTo(-190, 25); g.arc(-190, 0, 25, Math.PI / 2, -Math.PI / 2, true); g.closePath();
    g.fillStyle = GRN; g.shadowColor = GRN; g.shadowBlur = 25; g.fill(); g.shadowBlur = 0; g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
    g.setLineDash([10, 10]); g.lineWidth = 4; line(95, -85, 95, 85); g.setLineDash([]);
    txt('$20', -45, -14, 100, INK, { stroke: 0 }); txt('PARA APARTARLO', -45, 56, 30, INK, { font: 'IX', stroke: 0 });
    check(143, 4, 52, INK, 0.2);
    g.restore();
  }
  if (t > T.p379 - 0.15) {
    const e3 = backOut(prog(t, T.p379 - 0.15, T.p379 + 0.3));
    g.save(); g.translate(lerp(1500, 790, e3), 1140); g.rotate(0.06);
    poly([[-200, -100], [140, -100], [200, 0], [140, 100], [-200, 100]]); g.fillStyle = YEL; g.shadowColor = YEL; g.shadowBlur = 30; g.fill(); g.shadowBlur = 0; g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
    circle(150, 0, 13); g.fillStyle = INK; g.fill();
    txt('DESDE', -30, -58, 32, INK, { font: 'IX', stroke: 0 });
    txt('$' + counter(t, T.p379 - 0.1, T.p379 + 0.5, 20, 379), -30, 16, 108, INK, { stroke: 0 });
    g.restore();
  }
  pill('KICKSTARTER', 790, 1300, GRN, 44, t, T.kick, { solid: true });
}
function sceneClose(t) {
  drawBG(t, GRN);
  const a0 = K0[0] - 0.22;
  const d = easeOut(prog(t, a0, a0 + 0.5));
  g.save(); g.strokeStyle = WHT; g.lineWidth = 5; g.shadowColor = WHT; g.shadowBlur = 20; line(540, 860 - 420 * d, 540, 860 + 420 * d); g.restore();
  // izquierda: Zero y lo que tiene cerca
  const zl = t > T.czero - 0.1 ? 1 : 0.5;
  waveRings(270, 800, CYA, t, T.cerca - 0.1, 2, 190, 0.4, 0.8, 5);
  drawZero(270, 800, 0.62, { glow: zl, alpha: lerp(0.5, 1, zl), screen: scrRadar('#7ff0ff', t) });
  if (t > T.cerca - 0.1) {
    const e = backOut(prog(t, T.cerca - 0.1, T.cerca + 0.3));
    cardIcon(140, 1060, 0.4 * e, YEL, t); tvIcon(400, 1060, 0.4 * e, PINK, 1); gate(270, 610, 0.38 * e, 0.6, CYA);
  }
  pill('CERCA', 270, 470, CYA, 54, t, T.cerca, { solid: true });
  // derecha: One y redes enteras
  const ol = t > T.cone - 0.1 ? 1 : 0.5;
  if (t > T.redes - 0.1) {
    const f = easeOut(prog(t, T.redes - 0.1, T.redes + 0.8));
    for (let k = 0; k < 16; k++) {
      const x = 600 + 420 * hash(k, 11), y = 560 + 560 * hash(k, 12); const j = (k * 5 + 3) % 16; const x2 = 600 + 420 * hash(j, 11), y2 = 560 + 560 * hash(j, 12);
      const xx = lerp(810, x, f), yy = lerp(800, y, f), xx2 = lerp(810, x2, f), yy2 = lerp(800, y2, f);
      g.strokeStyle = rgba(PUR, 0.45); g.lineWidth = 3; line(810, 800, xx, yy); line(xx, yy, xx2, yy2);
      circle(xx, yy, 9); g.fillStyle = k % 3 ? PUR : YEL; g.fill();
      if (k % 4 === 0) packet(810, 800, xx, yy, t, 0.9, YEL, 1, 6);
    }
  }
  drawOne(810, 800, 0.5, { glow: ol, alpha: lerp(0.5, 1, ol), screen: scrWave('#d9c8ff', t) });
  pill('REDES ENTERAS', 810, 470, PUR, 50, t, T.redes, { solid: true });
  pill('HERMANOS', 290, 1240, GRN, 56, t, T.hermanos, { solid: true, icon: 'check' });
  pill('GEMELOS', 790, 1240, RED, 56, t, T.gemelos, { solid: true, icon: 'cross' });
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

// cambio rápido entre escenas dentro de un capítulo (barrido hacia arriba)
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
  else if (t < TR[1]) sceneZero(t);
  else if (t < TR[2]) { if (t < SUB.mod + 0.2) whip(t, SUB.mod, sceneListen, sceneModules); else whip(t, SUB.pet, sceneModules, scenePet); }
  else if (t < TR[3]) whip(t, SUB.roll, sceneCanada, sceneRolling);
  else if (t < TR[4]) { if (t < SUB.spec + 0.2) whip(t, SUB.spec, sceneOneReveal, sceneSpecs); else whip(t, SUB.port, sceneSpecs, scenePorts); }
  else if (t < TR[5]) sceneWhy(t);
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
