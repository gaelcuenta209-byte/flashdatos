// Flash Datos · video 24 · Rosberg y los 80 gramos del casco
// Escena dibujada en canvas 2D (1080x1920). render(t) dibuja el cuadro del segundo t.
'use strict';
const W = 1080, H = 1920;
const C = document.getElementById('c'), g = C.getContext('2d');
const SEG = {}; TM.segments.forEach(s => SEG[s.id] = s);
const PT = (id, k) => SEG[id].parts[k];
const END = TM.end;
const YEL = '#FFD84D', CYA = '#4FD8FF', WHT = '#FFFFFF', INK = '#080a14';
const TI = '#c8d1e2', TI_D = '#56627d', ORA = '#ff8a3d', RED = '#ff4d5e', GRN = '#46e08a', BLU = '#3d8bff', COP = '#e0924f';
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, s) => a + (b - a) * s;
const ease = s => { s = clamp(s); return s * s * s * (s * (6 * s - 15) + 10); };
const easeOut = s => { s = clamp(s); return 1 - Math.pow(1 - s, 3); };
const backOut = s => { s = clamp(s); const c = 1.6; return 1 + (c + 1) * Math.pow(s - 1, 3) + c * Math.pow(s - 1, 2); };
const prog = (t, a, b) => clamp((t - a) / (b - a));
function fade(t, a, b, f = 0.25) { if (t < a || t > b) return 0; return Math.min(1, (t - a) / f, (b - t) / f); }
let T = 0;

// ---------------- recursos ----------------
const IMG = {};
function loadImg(k, src) { return new Promise(r => { const i = new Image(); i.onload = () => { IMG[k] = i; r(); }; i.src = src; }); }
window.READY = Promise.all([
  new FontFace('IB', 'url(fonts/Inter-Black.otf)').load().then(f => document.fonts.add(f)),
  new FontFace('IX', 'url(fonts/Inter-ExtraBold.otf)').load().then(f => document.fonts.add(f)),
]).then(() => true);

// ---------------- utilidades de dibujo ----------------
function txt(s, x, y, size, fill, o = {}) {
  const font = o.font || 'IB';
  g.save();
  g.font = `${size}px ${font}`;
  if (o.maxW) { const w = g.measureText(s).width; if (w > o.maxW) { size *= o.maxW / w; g.font = `${size}px ${font}`; } }
  g.textAlign = o.align || 'center'; g.textBaseline = 'middle';
  g.globalAlpha *= (o.alpha ?? 1);
  const sw = o.stroke ?? Math.round(size * 0.1);
  if (sw > 0) { g.lineJoin = 'round'; g.strokeStyle = o.strokeCol || INK; g.lineWidth = sw * 2; g.strokeText(s, x, y); }
  g.fillStyle = fill; g.fillText(s, x, y);
  const w = g.measureText(s).width;
  g.restore();
  return { size, w };
}
function measure(s, size, font = 'IB') { g.save(); g.font = `${size}px ${font}`; const w = g.measureText(s).width; g.restore(); return w; }
function smooth(pts, closed = true) {
  const n = pts.length; g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
  const P = i => closed ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))];
  const lim = closed ? n : n - 1;
  for (let i = 0; i < lim; i++) {
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    g.bezierCurveTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6, p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]);
  }
  if (closed) g.closePath();
}
function poly(pts, closed = true) { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); if (closed) g.closePath(); }
function mirror(pts) { return pts.map(([x, y]) => [-x, y]).reverse(); }
function line(x0, y0, x1, y1) { g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); }
function circle(x, y, r) { g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); }
function arrow(x0, y0, x1, y1, w, col, head = 2.1) {
  const a = Math.atan2(y1 - y0, x1 - x0), L = Math.hypot(x1 - x0, y1 - y0);
  if (L < 1e-6) return;
  const hl = Math.min(L * 0.55, w * head * 1.25), hw = w * head * 0.95;
  g.save(); g.translate(x0, y0); g.rotate(a);
  g.beginPath(); g.moveTo(0, -w / 2); g.lineTo(L - hl, -w / 2); g.lineTo(L - hl, -hw); g.lineTo(L, 0); g.lineTo(L - hl, hw); g.lineTo(L - hl, w / 2); g.lineTo(0, w / 2); g.closePath();
  g.lineJoin = 'round'; g.lineWidth = w * 0.32; g.strokeStyle = INK; g.stroke();
  g.fillStyle = col; g.fill(); g.restore();
}
function bolt(cx, cy, s) {
  const p = [[0.58, 0.0], [0.12, 0.56], [0.44, 0.56], [0.30, 1.0], [0.88, 0.38], [0.55, 0.38], [0.74, 0.0]];
  poly(p.map(([x, y]) => [cx + (x - 0.5) * s, cy + (y - 0.5) * s]));
}
function tag(text, x, y, col, size = 38, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  g.font = `${size}px IX`;
  const w = g.measureText(text).width + size * 0.9, h = size * 1.45;
  g.beginPath(); g.roundRect(x - w / 2, y - h / 2, w, h, h / 2);
  g.fillStyle = 'rgba(6,10,24,0.82)'; g.fill(); g.lineWidth = 3; g.strokeStyle = col; g.stroke();
  g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, x, y + size * 0.03);
  g.restore();
}

// ---------------- fondo ----------------
const BG = document.createElement('canvas'); BG.width = W; BG.height = H;
{
  const b = BG.getContext('2d');
  const gr = b.createRadialGradient(540, 880, 60, 540, 960, 1300);
  gr.addColorStop(0, '#142a62'); gr.addColorStop(0.5, '#0a1738'); gr.addColorStop(1, '#030814');
  b.fillStyle = gr; b.fillRect(0, 0, W, H);
}
function drawBG(t, gridA = 1) {
  g.drawImage(BG, 0, 0);
  if (gridA <= 0) return;
  const sp = 54, off = (t * 9) % sp;
  g.save();
  for (let i = -1; i < W / sp + 2; i++) {
    const x = i * sp + off;
    g.strokeStyle = `rgba(79,216,255,${(i % 4 === 0 ? 0.075 : 0.035) * gridA})`; g.lineWidth = 1.5; line(x, 0, x, H);
  }
  for (let j = -1; j < H / sp + 2; j++) {
    const y = j * sp + off * 0.5;
    g.strokeStyle = `rgba(79,216,255,${(j % 4 === 0 ? 0.075 : 0.035) * gridA})`; g.lineWidth = 1.5; line(0, y, W, y);
  }
  g.restore();
}

// ---------------- subtítulos ----------------
function cleanCap(s) { return s.replace(/(\d)️?⃣/gu, '$1.').replace(/[⚡\u{1F527}️]/gu, '').replace(/\s+/g, ' ').trim(); }
// peso de cada palabra según cuánto tarda en decirse (los números se dicen con palabras)
function spokenLen(w) {
  const c = w.replace(/[.,:;…?!¡¿()"]/g, '');
  if (c === '→') return 0;
  if (/^C\d$/.test(c)) return 6;
  if (c === 'F1') return 11;
  if (c === 'GP') return 11;
  if (/^\d{4}$/.test(c)) return 24;
  if (/^\d+$/.test(c)) return c.length === 1 ? 5 : 9;
  return c.length;
}
const CAPS = [];
for (const s of TM.segments) for (const [t0, t1, raw] of s.parts) {
  const words = cleanCap(raw).split(' ');
  const groups = []; let cur = [];
  for (const w of words) { cur.push(w); if (cur.length === 3 || /[.,:…?!]$/.test(w) || cur.join(' ').length > 17) { groups.push(cur); cur = []; } }
  if (cur.length) groups.push(cur);
  const wts = groups.map(gr => gr.reduce((a, w) => a + spokenLen(w), 0) + 2), tot = wts.reduce((a, b) => a + b, 0);
  let t = t0;
  groups.forEach((gr, i) => { const d = (t1 - t0) * wts[i] / tot; CAPS.push([t, t + d, gr]); t += d; });
}
for (let i = 0; i < CAPS.length - 1; i++) if (CAPS[i + 1][0] - CAPS[i][1] < 0.7) CAPS[i][1] = CAPS[i + 1][0];
function isHL(w) { const core = w.replace(/[.,:…?!¡¿()"]/g, ''); return /\d/.test(core) || (core.length >= 2 && /[A-ZÁÉÍÓÚÑ]/.test(core) && core === core.toUpperCase()); }
const CAP_Y = 1590;
function drawCaption(t) {
  for (const [t0, t1, gr] of CAPS) {
    if (t >= t0 && t < t1) {
      const k = Math.min(1, (t - t0) / 0.09);
      let size = 80 * (1.12 - 0.12 * k);
      const sp = measure(' ', size);
      let ws = gr.map(w => measure(w, size)); let tot = ws.reduce((a, b) => a + b, 0) + sp * (gr.length - 1);
      if (tot > 1000) { size *= 1000 / tot; ws = ws.map(w => w * 1000 / tot); tot = 1000; }
      let x = W / 2 - tot / 2;
      const sp2 = measure(' ', size);
      gr.forEach((w, i) => { txt(w, x, CAP_Y, size, isHL(w) ? YEL : WHT, { align: 'left', stroke: 9 }); x += ws[i] + sp2; });
      return;
    }
  }
}
function drawWatermark() {
  g.save();
  const tw = measure('FLASH DATOS', 38); const x = W / 2 - (tw + 40) / 2;
  bolt(x + 14, 212, 40); g.fillStyle = 'rgba(255,216,77,0.92)'; g.fill();
  g.globalAlpha = 0.85; txt('FLASH DATOS', x + 40, 212, 38, WHT, { align: 'left', stroke: 4 });
  g.restore();
}
// Título grande arriba con subtítulos cian
function label(t, a, b, title, subs = [], col = WHT, size = 104, num = null) {
  const al = fade(t, a, b, 0.25); if (al <= 0) return;
  g.save(); g.globalAlpha = al;
  const rise = (1 - Math.min(1, (t - a) / 0.3)) * 24;
  const y = 345 + rise;
  let maxW = 1000;
  if (num !== null) {
    const r = 46; const tw = Math.min(measure(title, size), 1000 - 2 * r - 24);
    const tot = 2 * r + 24 + tw; const x0 = W / 2 - tot / 2;
    circle(x0 + r, y, r); g.fillStyle = YEL; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
    txt(String(num), x0 + r, y + 3, 62, INK, { stroke: 0 });
    txt(title, x0 + 2 * r + 24 + tw / 2, y, size, col, { maxW: tw, stroke: 8 });
  } else txt(title, W / 2, y, size, col, { maxW, stroke: 8 });
  let yy = y + size * 0.5 + 40;
  for (const s of subs) { txt(s, W / 2, yy, 50, CYA, { font: 'IX', maxW: 1000, stroke: 7 }); yy += 64; }
  g.restore();
}
function car(x, y, ang, k, col, num = null, o = {}) {
  g.save(); g.translate(x, y); g.rotate(ang); g.scale(k, k);
  if (o.shadow !== false) { g.save(); g.shadowColor = 'rgba(0,0,0,0.55)'; g.shadowBlur = 18 / k; g.fillStyle = 'rgba(0,0,0,0.01)'; g.fillRect(-45, -24, 95, 48); g.restore(); }
  const dark = o.dark || '#141a2b';
  // llantas
  const tyre = (x0, y0, w, h, band) => { g.fillStyle = '#0b0c11'; g.beginPath(); g.roundRect(x0, y0, w, h, 3); g.fill(); if (band) { g.fillStyle = band; g.fillRect(x0 + 2, y0 + (y0 < 0 ? 1 : h - 3), w - 4, 2); } };
  tyre(-42, -31, 19, 12, o.band); tyre(-42, 19, 19, 12, o.band);
  tyre(23, -28, 15, 10, o.band); tyre(23, 18, 15, 10, o.band);
  // suspensión
  g.strokeStyle = dark; g.lineWidth = 2.2; line(-32, -20, -18, -8); line(-32, 20, -18, 8); line(30, -19, 18, -5); line(30, 19, 18, 5);
  // piso
  poly([[-40, -16], [-12, -21], [14, -17], [28, -9], [28, 9], [14, 17], [-12, 21], [-40, 16]]); g.fillStyle = dark; g.fill();
  // carrocería
  g.beginPath();
  g.moveTo(-44, -7); g.lineTo(-22, -9); g.quadraticCurveTo(-12, -18, 4, -16); g.lineTo(12, -9); g.lineTo(44, -4); g.quadraticCurveTo(52, 0, 44, 4); g.lineTo(12, 9); g.lineTo(4, 16); g.quadraticCurveTo(-12, 18, -22, 9); g.lineTo(-44, 7); g.closePath();
  g.fillStyle = col; g.fill(); g.lineWidth = 2.5; g.strokeStyle = INK; g.stroke();
  // franja central
  g.fillStyle = 'rgba(255,255,255,0.22)'; g.fillRect(-40, -2, 80, 4);
  // cabina y halo
  g.beginPath(); g.ellipse(2, 0, 9, 5.5, 0, 0, Math.PI * 2); g.fillStyle = '#0a0d16'; g.fill();
  g.strokeStyle = '#d6dbe6'; g.lineWidth = 2.2; g.beginPath(); g.ellipse(3, 0, 10, 6.5, 0, -1.9, 1.9); g.stroke();
  circle(0, 0, 3.6); g.fillStyle = o.helmet || WHT; g.fill();
  // alerones
  g.fillStyle = col; g.strokeStyle = INK; g.lineWidth = 2;
  g.beginPath(); g.roundRect(44, -25, 7, 50, 2); g.fill(); g.stroke();
  g.fillStyle = dark; g.beginPath(); g.roundRect(-52, -21, 9, 42, 2); g.fill(); g.strokeStyle = col; g.stroke();
  // número
  if (num !== null) {
    g.save(); g.translate(-28, 0); g.rotate(-ang);
    circle(0, 0, 9.5); g.fillStyle = WHT; g.fill(); g.lineWidth = 1.5; g.strokeStyle = INK; g.stroke();
    g.fillStyle = INK; g.font = `${num.length > 1 ? 10 : 12}px IB`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(num, 0, 0.6);
    g.restore();
  }
  g.restore();
}
// marcador con nombre sobre un auto
function nameTag(x, y, s, col, size = 30, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  g.font = `${size}px IB`; const w = g.measureText(s).width + size * 0.7, h = size * 1.3;
  g.beginPath(); g.roundRect(x - w / 2, y - h / 2, w, h, 8); g.fillStyle = col; g.fill(); g.lineWidth = 3; g.strokeStyle = INK; g.stroke();
  g.fillStyle = INK; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s, x, y + 1);
  g.restore();
}

// =====================================================================
// PISTA (esquema de Yas Marina, dibujo propio)
// =====================================================================
// Recorrido trazado sobre el mapa de Yas Marina (Anthony Alessio Tralongo, CC BY-SA 4.0), sentido de carrera
const TRK = [[548, 262], [548, 340], [548, 410], [552, 458], [585, 478], [650, 470], [700, 452], [724, 408], [748, 372], [795, 352], [880, 350], [980, 351], [1060, 352], [1105, 352], [1124, 340],
  [1108, 326], [1040, 302], [940, 262], [840, 220], [740, 178], [640, 136], [540, 98], [462, 66], [446, 92], [400, 112], [348, 140], [290, 190], [228, 255], [170, 330], [118, 415], [86, 490], [80, 540],
  [98, 568], [140, 576], [180, 560], [190, 512], [188, 450], [196, 390], [218, 336], [258, 306], [302, 298], [318, 322], [322, 364], [344, 386], [392, 380], [402, 336], [398, 266], [402, 204], [436, 160], [478, 136], [512, 132], [520, 168], [522, 214], [532, 246]];
const TS = (() => { // muestreo Catmull-Rom cerrado
  const n = TRK.length, out = [];
  for (let i = 0; i < n; i++) {
    const p0 = TRK[(i - 1 + n) % n], p1 = TRK[i], p2 = TRK[(i + 1) % n], p3 = TRK[(i + 2) % n];
    for (let j = 0; j < 40; j++) {
      const s = j / 40, s2 = s * s, s3 = s2 * s;
      out.push([0, 1].map(k => 0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * s + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * s2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * s3)));
    }
  }
  const L = [0]; for (let i = 1; i <= out.length; i++) L.push(L[i - 1] + Math.hypot(out[i % out.length][0] - out[i - 1][0], out[i % out.length][1] - out[i - 1][1]));
  return { pts: out, L, total: L[L.length - 1] };
})();
function uAt(px, py) { let best = 0, bd = 1e9; TS.pts.forEach((p, i) => { const d = Math.hypot(p[0] - px, p[1] - py); if (d < bd) { bd = d; best = i; } }); return TS.L[best] / TS.total; }
const U_T1 = uAt(552, 458), U_T5 = uAt(1124, 340), U_REC = uAt(800, 203), U_T14 = uAt(396, 300), U_CHI = uAt(462, 66);
function tpos(u, off = 0) { // posición en coordenadas de pista y ángulo
  u = ((u % 1) + 1) % 1; const d = u * TS.total;
  let lo = 0, hi = TS.L.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (TS.L[m] <= d) lo = m; else hi = m; }
  const n = TS.pts.length, a = TS.pts[lo % n], b = TS.pts[(lo + 1) % n], s = (d - TS.L[lo]) / Math.max(1e-6, TS.L[lo + 1] - TS.L[lo]);
  const x = lerp(a[0], b[0], s), y = lerp(a[1], b[1], s), ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
  return [x - Math.sin(ang) * off, y + Math.cos(ang) * off, ang];
}
// cámara de la pista: escala y centro en pantalla
const MAPD = { s: 0.93, cx: 601, cy: 318, ox: 540, oy: 1000 };
let MAP = MAPD;
const MX = x => MAP.ox + (x - MAP.cx) * MAP.s, MY = y => MAP.oy + (y - MAP.cy) * MAP.s;
function drawTrack(a = 1, o = {}) {
  g.save(); g.globalAlpha *= a;
  const path = () => { g.beginPath(); TS.pts.forEach(([x, y], i) => i ? g.lineTo(MX(x), MY(y)) : g.moveTo(MX(x), MY(y))); g.closePath(); };
  g.lineJoin = 'round'; g.lineCap = 'round';
  path(); g.strokeStyle = 'rgba(0,0,0,0.45)'; g.lineWidth = 56 * MAP.s; g.stroke();
  path(); g.strokeStyle = '#e8ecf4'; g.lineWidth = 46 * MAP.s; g.stroke();
  path(); g.strokeStyle = '#2b3245'; g.lineWidth = 38 * MAP.s; g.stroke();
  if (o.sc) { path(); g.strokeStyle = `rgba(255,216,77,${0.25 + 0.2 * Math.sin(T * 10)})`; g.lineWidth = 38 * MAP.s; g.stroke(); }
  // línea de meta a cuadros
  const [x0, y0, an] = tpos(0);
  g.save(); g.translate(MX(x0), MY(y0)); g.rotate(an + Math.PI / 2);
  const w = 38 * MAP.s, c = w / 6; for (let i = 0; i < 6; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? WHT : INK; g.fillRect(-w / 2 + i * c, -c + j * c, c, c); }
  g.restore();
  g.restore();
}
function trackLabel(u, s, col, dx, dy, a = 1, size = 32) {
  const [x, y] = tpos(u); tag(s, MX(x) + dx, MY(y) + dy, col, size, a);
}
function carOn(u, off, col, num, k = 0.7, o = {}) {
  const [x, y, an] = tpos(u, off); car(MX(x), MY(y), an, k * MAP.s, col, num, o);
  return [MX(x), MY(y)];
}

// =====================================================================
// Video 24 · recursos (fotos libres de Wikimedia Commons; ninguna foto de pilotos)
// =====================================================================
function loadImg2(k, src) { return new Promise(r => { const i = new Image(); i.onload = () => { IMG[k] = i; r(); }; i.onerror = () => r(); i.src = src; }); }
const PHOTO_CREDIT = {
  carbono: 'Foto: Acheolg · CC BY-SA 4.0 · Wikimedia Commons',
  bascula: 'Foto: Poussin jean · CC BY-SA 3.0 · Wikimedia Commons',
  cronometro: 'Foto: Lesselich · CC BY-SA 3.0 · Wikimedia Commons',
  yasaerea: 'Foto: Dapaan · CC BY-SA 3.0 · Wikimedia Commons',
  bici: 'Ilustración: Road bike · CC BY-SA 4.0 · Wikimedia Commons',
};
window.READY = Promise.all([window.READY,
  loadImg2('carbono', 'img/carbono.jpg'), loadImg2('bascula', 'img/bascula.jpg'), loadImg2('cronometro', 'img/cronometro.jpg'),
  loadImg2('yasaerea', 'img/yasaerea.jpg'), loadImg2('bici', 'img/bici.png')]).then(() => true);

function photo(img, x, y, w, h, zoom, fx, fy, r = 26, border = YEL) {
  if (!img) return;
  g.save();
  g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 40; g.beginPath(); g.roundRect(x, y, w, h, r); g.fillStyle = '#000'; g.fill(); g.shadowBlur = 0;
  g.clip();
  const ir = img.width / img.height, br = w / h;
  let sw, sh; if (ir > br) { sh = img.height / zoom; sw = sh * br; } else { sw = img.width / zoom; sh = sw / br; }
  const sx = clamp(fx * img.width - sw / 2, 0, img.width - sw), sy = clamp(fy * img.height - sh / 2, 0, img.height - sh);
  g.drawImage(img, sx, sy, sw, sh, x, y, w, h);
  g.restore();
  g.beginPath(); g.roundRect(x, y, w, h, r); g.lineWidth = 6; g.strokeStyle = border; g.stroke();
}
function credit(s, y, a = 1) { if (a > 0) txt(s, 540, y, 24, 'rgba(255,255,255,0.92)', { font: 'IX', stroke: 4, alpha: a }); }
function popIn(t, a, d = 0.45) { return backOut(prog(t, a, a + d)); }
function hash(i, j, k) { let h = (i * 374761393 + j * 668265263 + k * 2246822519) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295; }
function glow(x, y, r, col, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  const gr = g.createRadialGradient(x, y, 0, x, y, r);
  gr.addColorStop(0, col); gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr; g.globalCompositeOperation = 'lighter'; g.globalAlpha *= 0.35; g.fillRect(x - r, y - r, 2 * r, 2 * r);
  g.restore();
}
function withA(a, fn) { if (a <= 0) return; g.save(); g.globalAlpha *= a; fn(); g.restore(); }

// =====================================================================
// Video 24 · tiempos
// =====================================================================
const SIL = '#c3ccd6', TEAL = '#00d2be', PUR = '#b67cff', GREY = '#8b93a7';
const at = (p, f) => p[0] + (p[1] - p[0]) * f;
const P = id => SEG[id].parts;
const [G0, G1] = P('gancho'), [O0, O1, O2] = P('objetivo'), [K0, K1, K2, K3] = P('casco'), [L0, L1] = P('calculo');
const [B0, B1, B2] = P('cuerpo'), [M0, M1] = P('mente'), [R0, R1] = P('rivalidad'), [S0, S1, S2, S3] = P('temporada');
const [A0, A1, A2] = P('abudabi'), [X0, X1] = P('retiro'), [F0] = P('final');
const FLASHES = [O0[0] - 0.3, K0[0] - 0.3, L0[0] - 0.3, B0[0] - 0.3, M0[0] - 0.3, R0[0] - 0.3, S0[0] - 0.3, A0[0] - 0.3, X0[0] - 0.3, F0[0] - 0.3, F0[1] + 0.15];
const ENDF = FLASHES[10];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
}

// =====================================================================
// CASCO de perfil (dibujo original): pintura encima, fibra de carbono debajo
// =====================================================================
const CW = document.createElement('canvas'); CW.width = 48; CW.height = 48;
{
  const c = CW.getContext('2d'); const q = 12;
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
    const x = i * q, y = j * q, hor = ((i + j) % 4) < 2;
    const gr = hor ? c.createLinearGradient(x, y, x, y + q) : c.createLinearGradient(x, y, x + q, y);
    gr.addColorStop(0, '#08090c'); gr.addColorStop(0.5, '#3b404b'); gr.addColorStop(1, '#08090c');
    c.fillStyle = gr; c.fillRect(x, y, q, q);
  }
}
let CPAT = null;
function cpat() { if (!CPAT) CPAT = g.createPattern(CW, 'repeat'); return CPAT; }
function helmetPath() {
  g.beginPath(); g.moveTo(-170, 140);
  g.bezierCurveTo(-218, 60, -212, -110, -60, -165);
  g.bezierCurveTo(60, -205, 182, -140, 206, -30);
  g.lineTo(214, 70); g.quadraticCurveTo(212, 142, 150, 146); g.closePath();
}
function visorPath() {
  g.beginPath(); g.moveTo(30, -66); g.quadraticCurveTo(120, -102, 206, -46);
  g.lineTo(212, 16); g.quadraticCurveTo(120, 30, 38, 8); g.quadraticCurveTo(20, -30, 30, -66); g.closePath();
}
const peelX = (xe, yy) => xe + 14 * Math.sin(yy * 0.045 + T * 2.2) + (yy + 230) * 0.12;
function helmet(x, y, s, paint = 1, o = {}) {
  if (s <= 0) return;
  g.save(); g.translate(x, y); g.rotate(o.rot || 0); g.scale(s * (o.flip ? -1 : 1), s);
  if (o.glow) glow(0, 0, 340, o.glow, o.glowA ?? 1);
  g.save(); g.shadowColor = 'rgba(0,0,0,0.7)'; g.shadowBlur = 50; g.shadowOffsetY = 20; helmetPath(); g.fillStyle = '#0d0f14'; g.fill(); g.restore();
  g.save(); helmetPath(); g.clip();
  g.save(); g.scale(1.5, 1.5); g.fillStyle = cpat(); g.fillRect(-200, -200, 400, 320); g.restore();
  if (paint > 0) {
    const xe = lerp(-245, 245, paint);
    g.save();
    g.beginPath(); g.moveTo(-270, -230);
    for (let yy = -230; yy <= 170; yy += 20) g.lineTo(peelX(xe, yy), yy);
    g.lineTo(-270, 170); g.closePath(); g.clip();
    g.fillStyle = o.base || '#e8ecf3'; g.fillRect(-270, -230, 540, 400);
    g.beginPath(); g.moveTo(-230, 30); g.bezierCurveTo(-80, -20, 80, 0, 240, -30); g.lineTo(240, 40); g.bezierCurveTo(80, 64, -80, 46, -230, 104); g.closePath(); g.fillStyle = o.band || YEL; g.fill();
    g.lineWidth = 14; g.strokeStyle = o.line || CYA; g.beginPath(); g.moveTo(-230, -20); g.bezierCurveTo(-80, -70, 80, -50, 240, -82); g.stroke();
    g.restore();
    if (paint < 0.999 && o.peelEdge !== false) {
      g.save(); g.lineWidth = 7; g.strokeStyle = 'rgba(255,216,77,0.95)'; g.shadowColor = YEL; g.shadowBlur = 25; g.beginPath();
      for (let yy = -230; yy <= 170; yy += 20) { const xx = peelX(xe, yy); yy === -230 ? g.moveTo(xx, yy) : g.lineTo(xx, yy); }
      g.stroke(); g.restore();
    }
  }
  const sh = g.createLinearGradient(0, -210, 0, 150); sh.addColorStop(0, 'rgba(255,255,255,0.22)'); sh.addColorStop(0.45, 'rgba(255,255,255,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.55)');
  g.fillStyle = sh; g.fillRect(-270, -230, 540, 400);
  g.fillStyle = '#07080b'; g.fillRect(-270, 124, 540, 40);
  g.restore();
  visorPath(); const vg = g.createLinearGradient(30, -90, 210, 20); vg.addColorStop(0, '#0a1626'); vg.addColorStop(0.6, '#1d4670'); vg.addColorStop(1, '#0a1626');
  g.fillStyle = vg; g.fill(); g.lineWidth = 7; g.strokeStyle = INK; g.stroke();
  g.save(); visorPath(); g.clip(); g.fillStyle = 'rgba(255,255,255,0.22)'; g.beginPath(); g.moveTo(70, -90); g.lineTo(120, -96); g.lineTo(80, 24); g.lineTo(40, 24); g.closePath(); g.fill(); g.restore();
  helmetPath(); g.lineWidth = 8; g.strokeStyle = INK; g.stroke();
  g.save(); g.globalAlpha = 0.35; g.strokeStyle = WHT; g.lineWidth = 10; g.lineCap = 'round'; g.beginPath(); g.arc(-30, 10, 150, -2.6, -1.7); g.stroke(); g.restore();
  g.restore();
}
function cup(x, y, s, year, a = 1) {
  if (s <= 0 || a <= 0) return;
  g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s);
  g.shadowColor = YEL; g.shadowBlur = 50;
  g.beginPath(); g.moveTo(-90, -120); g.lineTo(90, -120); g.quadraticCurveTo(90, 30, 0, 50); g.quadraticCurveTo(-90, 30, -90, -120); g.closePath();
  g.fillStyle = YEL; g.fill(); g.shadowBlur = 0; g.lineWidth = 8; g.strokeStyle = INK; g.stroke();
  g.lineWidth = 16; g.strokeStyle = YEL; g.beginPath(); g.arc(-95, -70, 40, Math.PI * 0.5, Math.PI * 1.5); g.stroke(); g.beginPath(); g.arc(95, -70, 40, -Math.PI * 0.5, Math.PI * 0.5); g.stroke();
  g.fillStyle = YEL; g.fillRect(-18, 48, 36, 60); g.beginPath(); g.roundRect(-75, 105, 150, 40, 8); g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  txt(year, 0, -50, 46, INK, { stroke: 0 });
  g.restore();
}
function wheel(x, y, s, hot) {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.save(); if (hot > 0) { g.shadowColor = YEL; g.shadowBlur = 40 * hot; }
  g.fillStyle = hot > 0 ? YEL : '#3a4258'; g.beginPath(); g.roundRect(-235, 70, 150, 64, 22); g.fill(); g.restore();
  g.fillStyle = '#3a4258'; g.beginPath(); g.roundRect(85, 70, 150, 64, 22); g.fill();
  g.beginPath(); g.moveTo(-260, -80); g.quadraticCurveTo(-300, 0, -260, 130); g.quadraticCurveTo(-230, 170, -170, 150); g.lineTo(170, 150); g.quadraticCurveTo(230, 170, 260, 130); g.quadraticCurveTo(300, 0, 260, -80); g.quadraticCurveTo(200, -140, 0, -140); g.quadraticCurveTo(-200, -140, -260, -80); g.closePath();
  g.fillStyle = '#1a1f2e'; g.fill(); g.lineWidth = 8; g.strokeStyle = INK; g.stroke();
  g.fillStyle = '#0d0f15'; g.beginPath(); g.roundRect(-300, -60, 70, 200, 30); g.fill(); g.beginPath(); g.roundRect(230, -60, 70, 200, 30); g.fill();
  g.beginPath(); g.roundRect(-110, -105, 220, 110, 14); g.fillStyle = '#061a2a'; g.fill(); g.lineWidth = 4; g.strokeStyle = CYA; g.stroke();
  for (let i = 0; i < 10; i++) { circle(-90 + i * 20, -122, 6); g.fillStyle = i < 4 ? GRN : i < 8 ? RED : BLU; g.fill(); }
  txt('N', 0, -50, 64, CYA, { stroke: 0 });
  [[-175, -50, RED], [-175, 30, GRN], [175, -50, BLU], [175, 30, YEL]].forEach(([bx, by, c]) => { circle(bx, by, 22); g.fillStyle = c; g.fill(); });
  g.restore();
}

// =====================================================================
// ESCENAS
// =====================================================================
function sceneHook(t) {
  drawBG(t, 0.8);
  const e = popIn(t, 0.0, 0.6);
  const crack = prog(t, at(G1, 0.55), G1[1]);
  const y = 960 + Math.sin(t * 1.6) * 12;
  helmet(540, y, 1.55 * e, 1 - 0.22 * ease(crack), { glow: crack > 0 ? RED : CYA, glowA: 0.8, rot: -0.05 + 0.03 * Math.sin(t) });
  label(t, -1, G1[0] - 0.1, '¿HASTA DÓNDE?', ['para ganar un campeonato'], WHT, 118);
  label(t, G1[0] - 0.1, 1e9, 'NICO ROSBERG', ['campeón de la F1 en 2016'], YEL, 118);
  tag('LA PINTURA: SU ENEMIGO', 540, 1330, RED, 50, ease(prog(t, at(G1, 0.62), at(G1, 0.75))));
}
function sceneTwins(t) {
  drawBG(t, 0.7);
  const a = O0[0] - 0.3;
  const same = ease(prog(t, O1[0], O1[0] + 0.6));
  const yb = 1000;
  const xs = [lerp(290, 340, same), lerp(790, 740, same)];
  [['6', 'ROSBERG', YEL, '#14161b'], ['44', 'HAMILTON', CYA, WHT]].forEach(([num, name, col, hc], i) => {
    const e = popIn(t, a + 0.1 + i * 0.25, 0.5); if (e <= 0) return;
    const x = xs[i];
    g.save(); g.translate(x, yb); g.scale(e, e); g.translate(-x, -yb);
    car(x + Math.sin(t * 40 + i) * 1.2, yb, -Math.PI / 2, 4.8, SIL, num, { helmet: hc, dark: '#151a26' });
    g.restore();
    nameTag(x, yb - 330, name, col, 40, Math.min(1, e));
  });
  label(t, a, O1[0] - 0.1, 'EL OBJETIVO', ['vencer a Lewis Hamilton'], WHT, 118);
  label(t, O1[0] - 0.1, 1e9, 'EL MISMO AUTO', ['los dos, en Mercedes'], WHT, 112);
  const ea = ease(prog(t, at(O1, 0.3), at(O1, 0.45)));
  if (ea > 0) txt('=', 540, yb, 110, YEL, { alpha: ea, stroke: 8 });
  tag('LA DIFERENCIA: DETALLES', 540, 1400, YEL, 46, ease(prog(t, at(O1, 0.6), at(O1, 0.75))));
}
function sceneSearch(t) {
  drawBG(t, 0.7);
  const a = O2[0] - 0.3, mid = at(O2, 0.58);
  label(t, a, 1e9, 'BUSCÓ EN TODO', ['cualquier rendimiento extra'], WHT, 118);
  const items = ['AUTO', 'PESO', 'SALIDAS', 'SUEÑO', 'CUERPO', 'MENTE'];
  const off = ease(prog(t, mid - 0.2, mid + 0.3));
  items.forEach((s, i) => {
    const x = 290 + (i % 2) * 500, y = 700 + Math.floor(i / 2) * 190;
    tag(s, x, y, i % 2 ? CYA : WHT, 52, Math.min(1, popIn(t, a + 0.3 + i * 0.3, 0.4)) * (1 - off));
  });
  const sa = fade(t, a + 0.8, mid + 0.2, 0.3);
  withA(sa, () => {
    const mx = 540 + 280 * Math.sin(t * 1.7), my = 880 + 170 * Math.sin(t * 2.3);
    g.lineWidth = 18; g.strokeStyle = YEL; circle(mx, my, 90); g.stroke();
    g.fillStyle = 'rgba(255,216,77,0.08)'; g.fill();
    g.lineCap = 'round'; g.lineWidth = 26; line(mx + 64, my + 64, mx + 150, my + 150);
  });
  const e = popIn(t, mid, 0.5);
  if (e > 0) {
    helmet(540, 1050, 1.2 * e, 1, { glow: YEL });
    withA(ease(prog(t, mid + 0.3, mid + 0.7)), () => arrow(540, 640, 540, 790 + 12 * Math.sin(t * 6), 34, YEL));
    tag('ENCIMA DE SU CABEZA', 540, 1360, YEL, 50, ease(prog(t, mid + 0.4, mid + 0.8)));
  }
}
function scenePeel(t) {
  drawBG(t, 0.6);
  const a = K0[0] - 0.3;
  const peel = ease(prog(t, K0[0] + 0.3, K1[0] + 2.0));
  const sp = ease(prog(t, at(K1, 0.5), at(K1, 0.62)));
  const hy = lerp(1000, 770, sp), hs = lerp(1.6, 0.95, sp);
  helmet(540, hy, hs, 1 - peel, { glow: peel > 0.95 ? '#8d95a8' : YEL, glowA: 0.7, rot: Math.sin(t * 0.8) * 0.03 });
  if (peel > 0 && peel < 1) for (let i = 0; i < 26; i++) {
    const tt = (t * 0.9 + hash(i, 3, 7)) % 1;
    const xe = 540 + lerp(-245, 245, 1 - peel) * hs;
    const x = xe + tt * 260 * (hash(i, 1, 1) + 0.3), y = hy - 200 * hs + hash(i, 2, 2) * 380 * hs + tt * tt * 300;
    g.save(); g.globalAlpha = (1 - tt) * 0.9; g.translate(x, y); g.rotate(tt * 8 + i);
    g.fillStyle = i % 3 === 0 ? YEL : i % 3 === 1 ? CYA : '#e8ecf3'; g.fillRect(-11, -6, 22, 12); g.restore();
  }
  label(t, a, K1[0] - 0.1, 'ADIÓS, PINTURA', ['se la quitó a su casco'], WHT, 112);
  label(t, K1[0] - 0.1, 1e9, 'FIBRA DE CARBONO', ['casi negro: así quedó'], YEL, 100);
  withA(sp, () => photo(IMG.carbono, 130, 1000, 820, 400, 1.1 + 0.08 * prog(t, K1[0], K1[1]), 0.5, 0.5, 24, CYA));
  credit(PHOTO_CREDIT.carbono, 1438, sp);
}
function sceneGrams(t) {
  drawBG(t, 0.6);
  const a = K2[0] - 0.3;
  const sy = 1180;
  g.save();
  g.beginPath(); g.roundRect(240, sy, 600, 60, 18); g.fillStyle = '#2a3150'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  g.beginPath(); g.roundRect(200, sy + 60, 680, 140, 26); g.fillStyle = '#151a2a'; g.fill(); g.stroke();
  g.beginPath(); g.roundRect(370, sy + 88, 340, 84, 14); g.fillStyle = '#062014'; g.fill(); g.lineWidth = 4; g.strokeStyle = GRN; g.stroke();
  g.restore();
  helmet(540, sy - 175, 1.0, 0, { glow: CYA, glowA: 0.6 });
  const c = ease(prog(t, at(K2, 0.55), at(K2, 0.85)));
  txt(`−${Math.round(80 * c)} g`, 540, sy + 132, 64, GRN, { stroke: 0 });
  label(t, a, 1e9, '¿CUÁNTO AHORRÓ?', [], WHT, 110);
  const big = popIn(t, at(K2, 0.8), 0.5);
  if (big > 0) txt('80 GRAMOS', 540, 560, 120 * big, YEL, { stroke: 10 });
}
function sceneMatters(t) {
  drawBG(t, 0.6);
  const a = K3[0] - 0.3;
  label(t, a, 1e9, '¿RIDÍCULO?', ['para Rosberg, no'], WHT, 118);
  const pa = ease(prog(t, a, a + 0.5));
  withA(pa, () => photo(IMG.bascula, 120, 590, 840, 790, 1.0 + 0.06 * prog(t, a, K3[1]), 0.5, 0.55, 26, YEL));
  credit(PHOTO_CREDIT.bascula, 1415, pa);
  const s = popIn(t, at(K3, 0.55), 0.5);
  if (s > 0) { g.save(); g.translate(540, 990); g.rotate(-0.1); g.scale(s, s); g.beginPath(); g.roundRect(-320, -90, 640, 180, 24); g.fillStyle = 'rgba(6,10,24,0.88)'; g.fill(); g.lineWidth = 10; g.strokeStyle = YEL; g.stroke(); txt('80 g IMPORTAN', 0, 4, 76, YEL, { stroke: 0 }); g.restore(); }
}
function sceneLap(t) {
  drawBG(t, 0.6);
  const a = L0[0] - 0.3;
  label(t, a, 1e9, '1 KILO EXTRA', ['según sus cálculos'], WHT, 118);
  const pa = ease(prog(t, a, a + 0.5));
  withA(pa, () => photo(IMG.cronometro, 240, 590, 600, 720, 1.0, 0.5, 0.42, 26, CYA));
  credit(PHOTO_CREDIT.cronometro, 1340, pa);
  const e = popIn(t, at(L0, 0.55), 0.5);
  if (e > 0) { g.save(); g.translate(540, 1150); g.scale(e, e); g.beginPath(); g.roundRect(-380, -100, 760, 200, 28); g.fillStyle = 'rgba(6,10,24,0.92)'; g.fill(); g.lineWidth = 8; g.strokeStyle = RED; g.stroke(); txt('+0.03 s', 0, -20, 100, RED, { stroke: 0 }); txt('POR VUELTA', 0, 58, 42, WHT, { font: 'IX', stroke: 0 }); g.restore(); }
}
function sceneEveryGram(t) {
  drawBG(t, 0.6);
  const a = L1[0] - 0.3;
  label(t, a, 1e9, 'CADA GRAMO', ['empezó a importar'], YEL, 124);
  const x0 = 140, x1 = 940, y = 1050;
  const f = ease(prog(t, L1[0] + 0.2, L1[1] - 0.5));
  if (t > L1[0]) for (let i = 0; i < 16; i++) {
    const tt = ((t - L1[0]) * 0.8 + hash(i, 5, 9)) % 1;
    const x = x0 + 70 + hash(i, 6, 1) * (x1 - x0 - 140), yy = 640 + tt * 330;
    tag('1 g', x, yy, WHT, 30, Math.sin(Math.PI * tt));
  }
  g.beginPath(); g.roundRect(x0, y - 50, x1 - x0, 100, 50); g.fillStyle = '#141b30'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  g.save(); g.beginPath(); g.roundRect(x0, y - 50, x1 - x0, 100, 50); g.clip(); g.fillStyle = YEL; g.fillRect(x0, y - 50, (x1 - x0) * f, 100); g.restore();
  txt(`${Math.round(1000 * f)} g`, 540, y, 62, f > 0.55 ? INK : WHT, { stroke: f > 0.55 ? 0 : 6 });
  txt('1 kg = 0.03 s por vuelta', 540, y + 130, 50, CYA, { font: 'IX', stroke: 6 });
}
function sceneObsession(t) {
  drawBG(t, 0.6);
  const a = B0[0] - 0.3;
  label(t, a, 1e9, 'LA OBSESIÓN', ['el casco era solo una parte'], WHT, 118);
  helmet(290, 930, 0.72 * popIn(t, a + 0.1, 0.5), 0, { glow: CYA, glowA: 0.6 });
  [['PIERNAS', 780, 760, YEL], ['GUANTES', 780, 930, CYA], ['MENTE', 780, 1100, PUR]].forEach(([s, x, y, c], i) => tag(s, x, y, c, 56, Math.min(1, popIn(t, a + 0.6 + i * 0.35, 0.4))));
  withA(ease(prog(t, a + 0.4, a + 0.8)), () => arrow(470, 930, 600, 930, 26, YEL));
}
function sceneBike(t) {
  drawBG(t, 0.6);
  const a = B1[0] - 0.3;
  label(t, a, 1e9, 'ADIÓS, BICICLETA', ['en 2016, para perder músculo'], WHT, 104);
  const pa = ease(prog(t, a, a + 0.5));
  withA(pa, () => photo(IMG.bici, 90, 600, 900, 490, 1.0, 0.5, 0.5, 26, CYA));
  credit(PHOTO_CREDIT.bici, 1118, pa);
  const x = ease(prog(t, at(B1, 0.22), at(B1, 0.42)));
  if (x > 0) {
    g.save(); g.lineCap = 'round'; g.lineWidth = 34; g.strokeStyle = RED; g.shadowColor = RED; g.shadowBlur = 30;
    const u = Math.min(1, x * 2); line(210, 660, lerp(210, 870, u), lerp(660, 1030, u));
    if (x > 0.5) { const v = (x - 0.5) * 2; line(870, 660, lerp(870, 210, v), lerp(660, 1030, v)); }
    g.restore();
  }
  const k = popIn(t, at(B1, 0.6), 0.5);
  if (k > 0) { g.save(); g.translate(540, 1290); g.scale(k, k); txt('−1 KG', 0, 0, 150, YEL, { stroke: 12 }); g.restore(); txt('de músculo en las piernas', 540, 1415, 46, CYA, { font: 'IX', stroke: 6, alpha: Math.min(1, k) }); }
}
function sceneGlove(t) {
  drawBG(t, 0.6);
  const a = B2[0] - 0.3;
  label(t, a, 1e9, 'GUANTES A MEDIDA', ['sin costuras en los dedos'], WHT, 104);
  const e = popIn(t, a + 0.1, 0.5);
  const hot = prog(t, at(B2, 0.4), at(B2, 0.45)) * (0.6 + 0.4 * Math.sin(t * 8));
  const wx = 540, wy = 880, ws = 1.4;
  g.save(); g.translate(wx, wy); g.scale(e, e); g.translate(-wx, -wy); wheel(wx, wy, ws, hot); g.restore();
  const fa = ease(prog(t, at(B2, 0.22), at(B2, 0.42)));
  const fx = wx - ws * 160, fy = wy + ws * 102;
  if (fa > 0) {
    g.save(); g.translate(fx, lerp(fy + 420, fy + 20, fa));
    g.beginPath(); g.roundRect(-46, 0, 92, 380, 46); g.fillStyle = '#2b2f3a'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
    g.strokeStyle = 'rgba(79,216,255,0.7)'; g.setLineDash([10, 10]); g.lineWidth = 3; g.beginPath(); g.roundRect(-30, 14, 60, 350, 30); g.stroke(); g.setLineDash([]);
    g.restore();
  }
  const ta = ease(prog(t, at(B2, 0.45), at(B2, 0.55)));
  tag('EMBRAGUE', 760, 1180, YEL, 48, ta);
  withA(ta, () => arrow(630, 1170, fx + 70, fy + 40, 20, YEL));
  tag('SALIDAS MÁS PRECISAS', 540, 1420, CYA, 46, ease(prog(t, at(B2, 0.68), at(B2, 0.78))));
}
function sceneMind(t) {
  drawBG(t, 0.5);
  const a = M0[0] - 0.3, sw = M1[0] - 0.2;
  label(t, a, sw + 0.1, 'LA MENTE', ['también se entrena'], WHT, 124);
  label(t, sw + 0.1, 1e9, 'CUALQUIER VENTAJA', ['para vencer a Hamilton'], YEL, 100);
  const ha = 1 - ease(prog(t, sw, sw + 0.4));
  const cx = 540, cy = 920;
  withA(ha, () => {
    for (let i = 0; i < 4; i++) { const ph = ((t * 0.5 + i / 4) % 1); withA((1 - ph) * 0.6, () => { g.lineWidth = 6; g.strokeStyle = PUR; circle(cx, cy, 170 + ph * 320); g.stroke(); }); }
    g.save(); g.translate(cx, cy); g.scale(1.15, 1.15);
    g.beginPath(); g.moveTo(-120, 220); g.lineTo(-110, 120); g.bezierCurveTo(-200, 60, -190, -160, -20, -190); g.bezierCurveTo(140, -200, 200, -80, 170, 10); g.lineTo(205, 70); g.lineTo(165, 85); g.lineTo(170, 140); g.quadraticCurveTo(160, 170, 100, 160); g.lineTo(90, 220); g.closePath();
    g.fillStyle = '#1b2240'; g.fill(); g.lineWidth = 8; g.strokeStyle = PUR; g.stroke();
    glow(0, -60, 220, PUR, 0.9 + 0.1 * Math.sin(t * 4));
    g.strokeStyle = 'rgba(182,124,255,0.9)'; g.lineWidth = 6; g.lineCap = 'round';
    for (let k = 0; k < 3; k++) { g.beginPath(); for (let xx = -110; xx <= 110; xx += 6) { const yy = -110 + k * 45 + 14 * Math.sin(xx * 0.06 + t * 5 + k); xx === -110 ? g.moveTo(xx, yy) : g.lineTo(xx, yy); } g.stroke(); }
    g.restore();
    tag('PSICÓLOGO: HASTA 2 HORAS', 540, 1290, CYA, 46, Math.min(1, popIn(t, at(M0, 0.42), 0.4)));
    tag('MEDITACIÓN DIARIA', 540, 1390, YEL, 46, Math.min(1, popIn(t, at(M0, 0.7), 0.4)));
  });
  const tg = popIn(t, sw + 0.2, 0.5);
  if (tg > 0) {
    g.save(); g.translate(540, 950); g.scale(tg, tg);
    [[300, RED], [240, WHT], [180, RED], [120, WHT], [60, RED]].forEach(([r, c]) => { circle(0, 0, r); g.fillStyle = c; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke(); });
    g.restore();
    const hit = ease(prog(t, sw + 0.6, sw + 1.0));
    if (hit > 0) withA(1, () => arrow(lerp(1100, 560, hit), lerp(500, 935, hit), lerp(1240, 700, hit), lerp(390, 820, hit), 22, YEL));
    tag('+ VENTAJA', 540, 1340, YEL, 56, ease(prog(t, sw + 1.0, sw + 1.4)));
  }
}
function sceneRivalry(t) {
  drawBG(t, 0.6);
  const a = R0[0] - 0.3;
  if (t < R1[0] - 0.1) {
    label(t, a, R1[0] - 0.1, 'RIVALIDAD BRUTAL', ['dentro de Mercedes'], RED, 100);
    const sl = ease(prog(t, a, a + 0.8));
    helmet(lerp(-220, 290, sl), 960, 0.85, 0, { glow: YEL });
    helmet(lerp(1300, 790, sl), 960, 0.85, 1, { flip: true, glow: CYA, base: '#f2f4f8', band: PUR, line: CYA, peelEdge: false });
    nameTag(290, 1230, 'ROSBERG', YEL, 40, sl); nameTag(790, 1230, 'HAMILTON', CYA, 40, sl);
    if (sl >= 1) { const fr = Math.floor(t * 12); for (let i = 0; i < 14; i++) { const ang = hash(i, 1, fr) * Math.PI * 2, r = 30 + hash(i, 2, fr) * 120; g.save(); g.strokeStyle = i % 2 ? YEL : WHT; g.lineWidth = 5; g.lineCap = 'round'; line(540, 930, 540 + Math.cos(ang) * r, 930 + Math.sin(ang) * r); g.restore(); } }
  } else {
    label(t, R1[0] - 0.1, 1e9, 'HAMILTON, CAMPEÓN', ['2014 y 2015, con Mercedes'], CYA, 100);
    ['2014', '2015'].forEach((yr, i) => {
      const e = popIn(t, R1[0] + 0.3 + i * 0.6, 0.5); if (e <= 0) return;
      const x = 310 + i * 460;
      cup(x, 860, 1.2 * e, yr);
      nameTag(x, 1110, 'HAMILTON 1.º', CYA, 38, Math.min(1, e));
      const r2 = at(R1, 0.62) + i * 0.4;
      nameTag(x, 1190, 'ROSBERG 2.º', '#9aa3b8', 34, ease(prog(t, r2, r2 + 0.4)));
    });
  }
}
function bars(t, rv, hv, a = 1, max = 110, y0 = 1010, nums = true) {
  withA(a, () => {
    const x0 = 180, w = 720;
    [['ROSBERG', rv, YEL], ['HAMILTON', hv, CYA]].forEach(([n, v, col], i) => {
      const y = y0 + i * 160, bw = Math.max(70, w * v / max);
      txt(n, x0, y - 58, 40, col, { align: 'left', font: 'IX', stroke: 5 });
      g.beginPath(); g.roundRect(x0, y - 32, w, 64, 32); g.fillStyle = '#141b30'; g.fill();
      g.beginPath(); g.roundRect(x0, y - 32, bw, 64, 32); g.fillStyle = col; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
      if (nums) txt(String(Math.round(v)), x0 + bw - 20, y + 2, 42, INK, { align: 'right', stroke: 0 });
    });
  });
}
const RACES = ['AUSTRALIA', 'BARÉIN', 'CHINA', 'RUSIA'];
function sceneSeason(t) {
  drawBG(t, 0.6);
  const a = S0[0] - 0.3;
  if (t < S2[0] - 0.2) {
    label(t, a, S1[0] - 0.1, '2016: ARRANQUE PERFECTO', ['4 victorias en 4 carreras'], YEL, 88);
    label(t, S1[0] - 0.1, S2[0] - 0.2, 'HAMILTON REACCIONÓ', ['y la pelea se abrió'], CYA, 100);
    const vanish = ease(prog(t, S1[0] - 0.2, S1[0] + 0.3));
    RACES.forEach((r, i) => {
      const x = 300 + (i % 2) * 480, y = 640 + Math.floor(i / 2) * 120;
      tag(`${r} · 1.º`, x, y, YEL, 44, Math.min(1, popIn(t, at(S0, 0.18) + i * 0.45, 0.4)) * (1 - vanish));
    });
    const gr = ease(prog(t, at(S0, 0.55), at(S0, 0.8)));
    const conv = ease(prog(t, S1[0] + 0.2, S1[1] - 0.6));
    const rv = 100 * gr, hv = 57 * gr + (100 - 57) * 0.95 * conv;
    bars(t, rv, hv, Math.min(1, gr * 3), 110, lerp(1010, 900, vanish), conv <= 0);
    tag('+43 PUNTOS', 540, lerp(1330, 1220, vanish), YEL, 60, ease(prog(t, at(S0, 0.8), at(S0, 0.88))) * (1 - vanish));
    tag('PELEA ABIERTA', 540, 1250, RED, 60, ease(prog(t, at(S1, 0.55), at(S1, 0.7))));
  } else {
    label(t, S2[0] - 0.2, 1e9, 'CERO DESPERDICIOS', ['cada oportunidad contaba'], WHT, 104);
    const items = [['SALIDA', at(S3, 0.0)], ['CLASIFICACIÓN', at(S3, 0.12)], ['ENTRENAMIENTO', at(S3, 0.32)], ['CUERPO', at(S3, 0.5)], ['MENTE', at(S3, 0.62)]];
    items.forEach(([s, ti], i) => {
      const e = Math.min(1, popIn(t, ti, 0.4)); if (e <= 0) return;
      const y = 640 + i * 150;
      withA(e, () => {
        g.beginPath(); g.roundRect(170, y - 55, 740, 110, 26); g.fillStyle = 'rgba(6,10,24,0.85)'; g.fill(); g.lineWidth = 4; g.strokeStyle = i % 2 ? CYA : YEL; g.stroke();
        txt(s, 230, y, 54, WHT, { align: 'left', stroke: 0 });
        circle(850, y, 32); g.fillStyle = GRN; g.fill();
        g.strokeStyle = INK; g.lineWidth = 8; g.lineCap = 'round'; g.beginPath(); g.moveTo(834, y); g.lineTo(846, y + 13); g.lineTo(868, y - 13); g.stroke();
      });
    });
    const ca = ease(prog(t, at(S3, 0.8), at(S3, 0.9)));
    tag('CONSECUENCIAS', 540, 1420, RED, 56, ca);
  }
}
function sceneAbu(t) {
  drawBG(t, 0.5);
  const a = A0[0] - 0.3, ph = at(A1, 0.32);
  if (t < ph) {
    label(t, a, 1e9, 'ABU DABI', ['la última carrera de 2016'], YEL, 130);
    const pa = ease(prog(t, a, a + 0.5)), out = 1 - ease(prog(t, ph - 0.4, ph));
    withA(pa * out, () => photo(IMG.yasaerea, 140, 580, 800, 820, 1.05 + 0.12 * prog(t, a, ph), 0.5, 0.42, 26, YEL));
    credit(PHOTO_CREDIT.yasaerea, 1430, pa * out);
    return;
  }
  if (t < A2[0] - 0.2) {
    label(t, ph, A2[0] - 0.2, '12 PUNTOS DE VENTAJA', ['antes de la última carrera'], YEL, 96);
    const gr = ease(prog(t, ph, ph + 0.8));
    bars(t, 367 * gr, 355 * gr, Math.min(1, gr * 3), 380, 760);
    tag('NO NECESITABA GANAR', 540, 1180, CYA, 52, ease(prog(t, at(A1, 0.55), at(A1, 0.65))));
    tag('SOLO TERMINAR CERCA', 540, 1300, YEL, 52, ease(prog(t, at(A1, 0.72), at(A1, 0.82))));
    return;
  }
  // carrera: la pista (trazado propio calcado del mapa de Yas Marina) y el final
  const champ = at(A2, 0.6);
  const ta = 1 - ease(prog(t, champ - 0.2, champ + 0.3));
  withA(ta, () => {
    MAP = { s: 0.88, cx: 601, cy: 318, ox: 540, oy: 940 };
    drawTrack(1);
    const u = (t - A2[0]) * 0.11;
    carOn(u + 0.03, 0, SIL, '44', 0.85, { helmet: WHT });
    carOn(u, 0, SIL, '6', 0.85, { helmet: '#14161b' });
    MAP = MAPD;
    tag('1.º HAMILTON', 300, 1300, CYA, 44, ease(prog(t, at(A2, 0.05), at(A2, 0.15))));
    tag('2.º ROSBERG', 780, 1300, YEL, 44, ease(prog(t, at(A2, 0.2), at(A2, 0.3))));
  });
  label(t, A2[0] - 0.2, champ - 0.1, 'HAMILTON GANÓ…', ['pero Rosberg fue segundo'], CYA, 104);
  if (t > champ - 0.2) {
    label(t, champ - 0.1, 1e9, '¡CAMPEÓN DEL MUNDO!', ['Nico Rosberg · 2016'], YEL, 94);
    const e = popIn(t, champ, 0.6);
    cup(540, 900, 1.9 * e, '2016');
    for (let i = 0; i < 40; i++) { const tt = (t - champ) * 0.5 + hash(i, 9, 9); const y = 560 + ((tt * 420) % 900), x = 80 + hash(i, 4, 4) * 920 + 20 * Math.sin(t * 3 + i); g.save(); g.translate(x, y); g.rotate(t * 3 + i); g.fillStyle = [YEL, CYA, WHT, PUR][i % 4]; g.globalAlpha = Math.min(1, (t - champ) * 2); g.fillRect(-8, -4, 16, 8); g.restore(); }
    tag('385 vs 380 PUNTOS', 540, 1330, WHT, 50, ease(prog(t, champ + 0.8, champ + 1.2)));
  }
}
function sceneRetire(t) {
  drawBG(t, 0.5);
  const a = X0[0] - 0.3;
  if (t < X1[0] - 0.1) {
    label(t, a, 1e9, 'SE RETIRÓ', ['5 días después del título'], WHT, 124);
    helmet(540, 930, 1.2, 0, { glow: YEL, glowA: 0.5 });
    g.save(); g.beginPath(); g.roundRect(330, 1090, 420, 90, 16); g.fillStyle = '#20263a'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke(); g.restore();
    const s = popIn(t, at(X0, 0.55), 0.35);
    if (s > 0) { g.save(); g.translate(540, 930); g.rotate(-0.16); g.scale(1.8 - 0.8 * Math.min(1, s), 1.8 - 0.8 * Math.min(1, s)); g.globalAlpha = Math.min(1, s);
      g.lineWidth = 14; g.strokeStyle = RED; g.beginPath(); g.roundRect(-300, -85, 600, 170, 20); g.stroke(); txt('RETIRO', 0, 6, 110, RED, { stroke: 0 }); g.restore(); }
    return;
  }
  label(t, X1[0] - 0.1, at(X1, 0.72), 'EL OTRO LADO DEL GARAJE', ['años buscando vencerlo'], WHT, 80);
  // garaje dividido
  const ga = ease(prog(t, X1[0] - 0.1, X1[0] + 0.4)) * (1 - ease(prog(t, at(X1, 0.7), at(X1, 0.78))));
  withA(ga, () => {
    [[290, '6', YEL], [790, '44', CYA]].forEach(([x, n, c]) => {
      g.beginPath(); g.roundRect(x - 230, 640, 460, 620, 18); g.fillStyle = '#121a30'; g.fill(); g.lineWidth = 6; g.strokeStyle = c; g.stroke();
      for (let k = 0; k < 8; k++) { g.fillStyle = 'rgba(255,255,255,0.05)'; g.fillRect(x - 220, 660 + k * 75, 440, 40); }
      car(x, 1000, -Math.PI / 2, 3.6, SIL, n, { helmet: n === '6' ? '#14161b' : WHT });
      txt(n, x, 700, 70, c, { stroke: 6 });
    });
    g.fillStyle = WHT; g.fillRect(536, 620, 8, 660);
    tag('FÍSICO AL LÍMITE', 540, 1340, YEL, 44, ease(prog(t, at(X1, 0.42), at(X1, 0.5))));
  });
  const fin = at(X1, 0.74);
  if (t > fin - 0.2) {
    label(t, fin, 1e9, 'Y LO LOGRÓ', ['campeón del mundo 2016'], YEL, 120);
    cup(540, 930, 1.7 * popIn(t, fin, 0.6), '2016');
  }
}
function sceneFinal(t) {
  drawBG(t, 0.6);
  const a = F0[0] - 0.3;
  label(t, a, at(F0, 0.5), 'LOS 80 GRAMOS', ['más que una curiosidad'], YEL, 118);
  label(t, at(F0, 0.5), 1e9, 'MISMAS HERRAMIENTAS', ['ganan los detalles'], WHT, 96);
  const sc = 1.25 + 0.05 * Math.sin(t * 1.3);
  helmet(540, 930, sc * popIn(t, a, 0.6), 0, { glow: YEL, glowA: 0.8, rot: 0.04 * Math.sin(t * 0.9) });
  const r = 330;
  [['80 g', YEL], ['0.03 s', RED], ['1 KG', CYA]].forEach(([s, c], i) => {
    const ang = t * 0.7 + i * Math.PI * 2 / 3;
    tag(s, 540 + Math.cos(ang) * r * 1.2, 930 + Math.sin(ang) * r * 0.75, c, 46, Math.min(1, popIn(t, a + 0.3 + i * 0.3, 0.4)));
  });
  tag('MISMO AUTO · MISMAS ARMAS', 540, 1400, CYA, 44, ease(prog(t, at(F0, 0.55), at(F0, 0.65))));
}
function sceneEnd(t) {
  drawBG(t, 0.7);
  const E = ENDF;
  const e = backOut(prog(t, E, E + 0.5));
  g.save(); g.translate(540, 830); g.scale(e, e);
  g.shadowColor = YEL; g.shadowBlur = 60; bolt(0, 0, 330); g.fillStyle = YEL; g.fill(); g.lineWidth = 10; g.strokeStyle = INK; g.stroke(); g.restore();
  txt('FLASH DATOS', 540, 1090, 112, WHT, { stroke: 9, alpha: ease(prog(t, E + 0.15, E + 0.5)) });
  txt('Síguenos para más datos', 540, 1200, 54, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, E + 0.3, E + 0.7)) });
}

// =====================================================================
// MONTAJE
// =====================================================================
const SCENES = [
  [-1, sceneHook],
  [FLASHES[0], sceneTwins], [O2[0] - 0.3, sceneSearch],
  [FLASHES[1], scenePeel], [K2[0] - 0.3, sceneGrams], [K3[0] - 0.3, sceneMatters],
  [FLASHES[2], sceneLap], [L1[0] - 0.3, sceneEveryGram],
  [FLASHES[3], sceneObsession], [B1[0] - 0.3, sceneBike], [B2[0] - 0.3, sceneGlove],
  [FLASHES[4], sceneMind],
  [FLASHES[5], sceneRivalry],
  [FLASHES[6], sceneSeason],
  [FLASHES[7], sceneAbu],
  [FLASHES[8], sceneRetire],
  [FLASHES[9], sceneFinal],
  [FLASHES[10], sceneEnd],
];
const CUTS = new Set(FLASHES);
function render(t) {
  T = t;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  let i = 0; while (i + 1 < SCENES.length && SCENES[i + 1][0] <= t) i++;
  const [st, fn] = SCENES[i];
  const XF = 0.4;
  if (i > 0 && !CUTS.has(st) && t - st < XF) {
    SCENES[i - 1][1](t);
    g.setTransform(1, 0, 0, 1, 0, 0); g.save(); g.globalAlpha = ease((t - st) / XF); fn(t); g.restore();
  } else fn(t);
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  if (t < ENDF) drawCaption(t);
  drawWatermark();
  const fa = flashAlpha(t);
  if (fa > 0) {
    g.fillStyle = `rgba(225,248,255,${0.92 * fa})`; g.fillRect(0, 0, W, H);
    if (fa > 0.35) { g.globalAlpha = Math.min(1, (fa - 0.35) / 0.4); bolt(W / 2, H / 2, 420); g.fillStyle = YEL; g.fill(); g.globalAlpha = 1; }
  }
}
window.render = render;
window.grab = (t, q) => { render(t); return C.toDataURL('image/jpeg', q); };
window.INFO = { END };
