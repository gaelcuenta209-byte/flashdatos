// Flash Datos · video 26 · Las mejores vueltas de clasificación de la F1
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
  if (c === '→' || c === '·') return 0;
  if (/^\d+:\d+\.\d+$/.test(c)) return 55;
  if (/^\d+\.\d+$/.test(c)) return 26;
  if (/^#\d$/.test(c)) return 9;
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
// Video 26 · recursos (fotos y mapas libres de Wikimedia Commons; ninguna foto de pilotos)
// =====================================================================
function loadImg2(k, src) { return new Promise(r => { const i = new Image(); i.onload = () => { IMG[k] = i; r(); }; i.onerror = () => r(); i.src = src; }); }
const CRED = {
  cronometro: 'Foto: Lesselich · CC BY-SA 3.0 · Wikimedia Commons',
  rb19: 'Foto: Lukas Raich · CC BY-SA 4.0 · Wikimedia Commons',
  rb21: 'Foto: Lukas Raich · CC BY-SA 4.0 · Wikimedia Commons',
  w09: 'Foto: Lukas Raich · CC BY-SA 4.0 · Wikimedia Commons',
  fw10: 'Foto: Lothar Spurzem · CC BY-SA 2.0 DE · Wikimedia Commons',
  mp44: 'Foto: Morio · CC BY-SA 3.0 · Wikimedia Commons',
  montecarlo: 'Foto: Tobi 87 · CC BY-SA 3.0 · Wikimedia Commons',
  monaco: 'Mapa: Will Pittenger · CC BY-SA 3.0 · Wikimedia Commons',
  monza: 'Mapa: Will Pittenger · CC BY-SA 3.0 · Wikimedia Commons',
  marinabay: 'Mapa: Cherkash · CC BY-SA 4.0 · Wikimedia Commons',
  silverstone: 'Mapa: AlexJ · CC0 · Wikimedia Commons',
};
window.READY = Promise.all([window.READY,
  ...['cronometro', 'rb19', 'rb21', 'w09', 'fw10', 'mp44', 'montecarlo'].map(k => loadImg2(k, `img/${k}.jpg`)),
  ...['monaco', 'monza', 'marinabay', 'silverstone'].map(k => loadImg2(k, `img/${k}.png`))]).then(() => true);

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
// mapa de circuito (PNG transparente) sobre tarjeta clara
function mapCard(img, x, y, w, h, a = 1, border = CYA, bg = '#eef3fb') {
  if (!img || a <= 0) return;
  g.save(); g.globalAlpha *= a;
  g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 40;
  g.beginPath(); g.roundRect(x, y, w, h, 26); g.fillStyle = bg; g.fill(); g.shadowBlur = 0;
  const ir = img.width / img.height, pad = 26;
  let dw = w - 2 * pad, dh = dw / ir; if (dh > h - 2 * pad) { dh = h - 2 * pad; dw = dh * ir; }
  g.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
  g.beginPath(); g.roundRect(x, y, w, h, 26); g.lineWidth = 6; g.strokeStyle = border; g.stroke();
  g.restore();
}
function credit(k, y, a = 1) { if (a > 0 && CRED[k]) txt(CRED[k], 540, y, 23, 'rgba(255,255,255,0.92)', { font: 'IX', stroke: 4, alpha: a }); }
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
function panel(x, y, w, h, col = CYA, fill = 'rgba(6,10,24,0.86)') {
  g.beginPath(); g.roundRect(x, y, w, h, 22); g.fillStyle = fill; g.fill(); g.lineWidth = 5; g.strokeStyle = col; g.stroke();
}
// reloj de vuelta tipo transmisión (dibujo propio)
function fmtLap(s) { const m = Math.floor(s / 60), r = s - m * 60; return `${m}:${r.toFixed(3).padStart(6, '0')}`; }
function lapClock(x, y, val, col = WHT, size = 120, lbl = null, lc = YEL) {
  const s = typeof val === 'number' ? fmtLap(val) : val;
  g.save(); g.font = `${size}px IB`; const w = Math.max(g.measureText('0:00.000').width, g.measureText(s).width) + 70; g.restore();
  panel(x - w / 2, y - size * 0.72, w, size * 1.44, col);
  txt(s, x, y + 4, size, col, { stroke: 0 });
  if (lbl) tag(lbl, x, y - size * 0.72 - 6, lc, 34);
}
// barra horizontal de comparación
function hbar(x, y, w, h, frac, col, name, val, a = 1) {
  withA(a, () => {
    g.beginPath(); g.roundRect(x, y, w, h, h / 2); g.fillStyle = 'rgba(255,255,255,0.08)'; g.fill();
    if (frac > 0.001) { g.beginPath(); g.roundRect(x, y, Math.max(h, w * frac), h, h / 2); g.fillStyle = col; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke(); }
    txt(name, x + 20, y + h / 2, h * 0.52, INK, { align: 'left', stroke: 0, font: 'IB' });
    txt(val, x + w, y - 30, 44, col, { align: 'right', stroke: 6 });
  });
}
// velocímetro (dibujo propio)
function gauge(cx, cy, r, v, vmax, col, unit = 'KM/H', a = 1) {
  withA(a, () => {
    const a0 = Math.PI * 0.8, a1 = Math.PI * 2.2;
    g.lineCap = 'round';
    g.lineWidth = 34; g.strokeStyle = 'rgba(255,255,255,0.1)'; g.beginPath(); g.arc(cx, cy, r, a0, a1); g.stroke();
    const f = clamp(v / vmax); const gr = g.createLinearGradient(cx - r, cy, cx + r, cy); gr.addColorStop(0, CYA); gr.addColorStop(1, col);
    g.strokeStyle = gr; g.beginPath(); g.arc(cx, cy, r, a0, a0 + (a1 - a0) * f); g.stroke();
    for (let i = 0; i <= 10; i++) { const an = a0 + (a1 - a0) * i / 10; g.lineWidth = 5; g.strokeStyle = 'rgba(255,255,255,0.6)'; line(cx + Math.cos(an) * (r - 40), cy + Math.sin(an) * (r - 40), cx + Math.cos(an) * (r - 62), cy + Math.sin(an) * (r - 62)); }
    const an = a0 + (a1 - a0) * f; g.lineWidth = 12; g.strokeStyle = col; line(cx, cy, cx + Math.cos(an) * (r - 50), cy + Math.sin(an) * (r - 50));
    circle(cx, cy, 22); g.fillStyle = col; g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
    g.lineCap = 'butt';
    txt(v.toFixed(v % 1 ? 1 : 0), cx, cy + r * 0.5, 120, WHT, { stroke: 9 });
    txt(unit, cx, cy + r * 0.5 + 84, 46, col, { font: 'IX', stroke: 6 });
  });
}
function sparks(x, y, t, t0, n = 26, col = YEL) {
  const dt = t - t0; if (dt < 0 || dt > 0.9) return;
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) {
    const an = -Math.PI * (0.15 + 0.7 * hash(i, 1, Math.floor(t0 * 10))), sp = 300 + 700 * hash(i, 2, 3);
    const px = x + Math.cos(an) * sp * dt, py = y + Math.sin(an) * sp * dt + 900 * dt * dt;
    g.strokeStyle = col; g.globalAlpha = 1 - dt / 0.9; g.lineWidth = 4;
    line(px, py, px - Math.cos(an) * 26, py - Math.sin(an) * 26);
  }
  g.restore();
}
// insignia grande de número de ranking
function rankBadge(x, y, n, s = 1, col = YEL) {
  if (s <= 0) return;
  g.save(); g.translate(x, y); g.scale(s, s);
  g.shadowColor = col; g.shadowBlur = 50;
  circle(0, 0, 120); g.fillStyle = col; g.fill(); g.shadowBlur = 0; g.lineWidth = 12; g.strokeStyle = INK; g.stroke();
  txt('#' + n, 0, 8, 130, INK, { stroke: 0 });
  g.restore();
}

// =====================================================================
// Video 26 · tiempos
// =====================================================================
const MCL = '#f2f2f2', MCR = '#e5322d', MER = '#00d2be', PUR = '#b67cff';
const at = (p, f) => p[0] + (p[1] - p[0]) * f;
const P = id => SEG[id].parts;
const [G0, G1] = P('gancho'), [A0, A1] = P('n5'), [B0, B1] = P('n4'), [C0, C1, C2] = P('n3');
const [D0, D1, D2] = P('n2'), [E0, E1, E2] = P('n1'), [F0] = P('cierre');
const FLASHES = [A0[0] - 0.3, B0[0] - 0.3, C0[0] - 0.3, D0[0] - 0.3, E0[0] - 0.3, F0[0] - 0.3, F0[1] + 0.15];
const ENDF = FLASHES[6];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
}
// líneas de velocidad
function speedLines(t, a = 1, col = 'rgba(255,255,255,0.5)') {
  withA(a, () => {
    for (let i = 0; i < 34; i++) {
      const y = 480 + hash(i, 7, 1) * 1000, len = 120 + 260 * hash(i, 3, 2), sp = 1600 + 1400 * hash(i, 5, 5);
      const x = W + 300 - ((t * sp + hash(i, 9, 9) * 3000) % (W + 700));
      g.strokeStyle = col; g.lineWidth = 3 + 3 * hash(i, 1, 1); line(x, y, x + len, y);
    }
  });
}

// =====================================================================
// ESCENAS
// =====================================================================
// GANCHO: dos McLaren idénticos, uno se despega 1.4 s
function sceneHook(t) {
  drawBG(t, 0.8);
  if (t < G1[0] - 0.15) {
    speedLines(t, 0.6);
    label(t, -1, 1e9, 'MISMO AUTO', ['casi 1.5 s de diferencia'], WHT, 120);
    const k = ease(prog(t, 0.6, G0[1]));
    const xa = 300 + 520 * k, xb = 300 + 520 * k * 0.42;
    g.strokeStyle = 'rgba(255,255,255,0.25)'; g.lineWidth = 4; g.setLineDash([30, 26]); line(0, 980, W, 980); g.setLineDash([]);
    car(xa, 880, 0, 3.6, MCL, '12', { dark: MCR, helmet: YEL });
    car(xb, 1080, 0, 3.6, MCL, '11', { dark: MCR, helmet: WHT });
    nameTag(xa, 760, 'A', YEL, 40, ease(prog(t, 0.3, 0.6)));
    nameTag(xb, 1200, 'B', CYA, 40, ease(prog(t, 0.3, 0.6)));
    const gp = (1.427 * k).toFixed(3);
    tag(`+${gp} s`, 540, 1330, YEL, 64, ease(prog(t, 0.8, 1.2)));
    return;
  }
  // TOP 5
  label(t, G1[0] - 0.15, 1e9, 'TOP 5', ['vueltas de clasificación'], YEL, 150);
  const ys = [640, 800, 960, 1120, 1280];
  for (let i = 0; i < 5; i++) {
    const n = 5 - i, e = popIn(t, G1[0] + 0.25 + i * 0.35, 0.4);
    if (e <= 0) continue;
    g.save(); g.translate(540, ys[i]); g.scale(e, e);
    panel(-420, -62, 840, 124, n === 1 ? YEL : CYA);
    circle(-340, 0, 46); g.fillStyle = n === 1 ? YEL : CYA; g.fill();
    txt(String(n), -340, 4, 64, INK, { stroke: 0 });
    txt('? ? ?', 60, 4, 64, n === 1 ? YEL : WHT, { stroke: 6 });
    g.restore();
  }
}
// encabezado de cada puesto
function intro(t, p, n, name, place, year, img, fx, fy, col, credY = 1455) {
  const a = p[0] - 0.3;
  rankBadge(540, 700, n, popIn(t, a + 0.05, 0.5), col);
  withA(ease(prog(t, a + 0.25, a + 0.6)), () => {
    txt(name, 540, 920, 112, WHT, { maxW: 1000, stroke: 9 });
    txt(`${place} · ${year}`, 540, 1030, 64, col, { font: 'IX', stroke: 7 });
  });
  const e = ease(prog(t, a + 0.5, a + 1.0));
  if (e > 0) {
    const z = 1.05 + 0.08 * prog(t, a, p[1] + 0.3);
    withA(e, () => { photo(IMG[img], 90, 1100 + (1 - e) * 60, 900, 330, z, fx, fy, 24, col); credit(img, credY, 1); });
  }
}
// #5 VERSTAPPEN MÓNACO 2023
function scene5(t) {
  drawBG(t, 0.6);
  if (t < A1[0] - 0.15) { intro(t, A0, 5, 'MAX VERSTAPPEN', 'MÓNACO', '2023', 'rb19', 0.45, 0.52, YEL); return; }
  label(t, A1[0] - 0.15, 1e9, 'ÚLTIMO SECTOR', ['contra Fernando Alonso'], WHT, 110);
  // mapa de Mónaco
  mapCard(IMG.monaco, 90, 540, 900, 560, ease(prog(t, A1[0] - 0.1, A1[0] + 0.3)), CYA);
  credit('monaco', 1125, ease(prog(t, A1[0], A1[0] + 0.4)));
  // barras de sectores
  const s = A1;
  const rows = [['ALO', GRN], ['VER', YEL]];
  const sec = (i) => prog(t, at(s, 0.08 + i * 0.16), at(s, 0.2 + i * 0.16));
  const yb = 1200;
  withA(ease(prog(t, at(s, 0.04), at(s, 0.1))), () => {
    rows.forEach(([nm, c], r) => {
      const y = yb + r * 100;
      txt(nm, 150, y + 30, 50, c, { stroke: 6 });
      for (let i = 0; i < 3; i++) {
        const x = 240 + i * 260, f = sec(i);
        g.beginPath(); g.roundRect(x, y, 240, 60, 14); g.fillStyle = 'rgba(255,255,255,0.08)'; g.fill();
        let fc = c;
        if (nm === 'VER') fc = i < 2 ? RED : PUR; else fc = i < 2 ? GRN : '#f0c040';
        if (f > 0) { g.beginPath(); g.roundRect(x, y, 240 * f, 60, 14); g.fillStyle = fc; g.fill(); }
        if (r === 0 && f > 0.5) txt(`S${i + 1}`, x + 120, yb - 34, 36, WHT, { font: 'IX', stroke: 5 });
      }
    });
  });
  // roce con el muro: chispas
  [at(s, 0.5), at(s, 0.56)].forEach(tt => sparks(760, 820, t, tt, 30));
  const wall = at(s, 0.48);
  if (t > wall && t < wall + 1.3) tag('¡ROZA EL MURO!', 540, 600, RED, 52, fade(t, wall, wall + 1.3, 0.15));
  const fin = at(s, 0.74);
  if (t > fin) {
    const e = popIn(t, fin, 0.5);
    g.save(); g.translate(540, 1460); g.scale(e, e); tag('POLE POR 0.084 s', 0, 0, YEL, 66); g.restore();
  }
}
// #4 HAMILTON SINGAPUR 2018
function scene4(t) {
  drawBG(t, 0.6);
  if (t < B1[0] - 0.15) { intro(t, B0, 4, 'LEWIS HAMILTON', 'SINGAPUR', '2018', 'w09', 0.5, 0.55, CYA); return; }
  const s = B1;
  label(t, s[0] - 0.15, at(s, 0.6), 'POLE SORPRESA', ['de noche, entre muros'], CYA, 116);
  label(t, at(s, 0.6), 1e9, '"SE SINTIÓ COMO MAGIA"', ['Lewis Hamilton'], YEL, 80);
  // mapa nocturno: tarjeta oscura con contorno brillante
  const ma = ease(prog(t, s[0] - 0.1, s[0] + 0.3));
  withA(ma, () => {
    mapCard(IMG.marinabay, 90, 560, 900, 520, 1, PUR, '#dfe6f7');
    for (let i = 0; i < 18; i++) { const x = 120 + hash(i, 4, 1) * 840, y = 590 + hash(i, 2, 8) * 460; glow(x, y, 50 + 30 * Math.sin(t * 3 + i), i % 2 ? YEL : CYA, 0.5); }
  });
  credit('marinabay', 1105, ma);
  const ba = ease(prog(t, at(s, 0.12), at(s, 0.2)));
  const gr = ease(prog(t, at(s, 0.15), at(s, 0.4)));
  hbar(140, 1200, 800, 76, gr, MER, 'HAM', 'POLE', ba);
  hbar(140, 1330, 800, 76, gr * 0.86, '#3d6bff', 'VER', '+0.3 s', ba);
  if (t > at(s, 0.6)) for (let i = 0; i < 26; i++) {
    const ph = (t * 0.6 + hash(i, 5, 5)) % 1, x = 100 + hash(i, 6, 2) * 880, y = 1450 - ph * 950;
    g.save(); g.globalAlpha = Math.sin(ph * Math.PI) * 0.9; g.translate(x, y); g.rotate(t * 2 + i);
    bolt(0, 0, 26 + 18 * hash(i, 1, 9)); g.fillStyle = i % 3 ? YEL : CYA; g.fill(); g.restore();
  }
}
// #3 KEKE ROSBERG SILVERSTONE 1985
function scene3(t) {
  drawBG(t, 0.6);
  if (t < C1[0] - 0.15) { intro(t, C0, 3, 'KEKE ROSBERG', 'SILVERSTONE', '1985', 'fw10', 0.55, 0.45, ORA); tag('EL PAPÁ DE NICO', 540, 580, CYA, 44, ease(prog(t, at(C0, 0.45), at(C0, 0.6)))); return; }
  if (t < C2[0] - 0.15) {
    const s = C1;
    const deflate = t < at(s, 0.42);
    label(t, s[0] - 0.15, at(s, 0.42), '1.er INTENTO', ['llanta perdiendo aire'], RED, 116);
    label(t, at(s, 0.42), 1e9, 'SIGUIENTE VUELTA', ['Williams-Honda FW10'], WHT, 100);
    if (deflate) {
      // llanta que se desinfla (dibujo propio)
      const f = ease(prog(t, s[0] + 0.3, at(s, 0.38)));
      g.save(); g.translate(540, 900);
      g.fillStyle = '#0d0f15'; g.beginPath(); g.ellipse(0, 40 * f, 230, 230 - 60 * f, 0, 0, Math.PI * 2); g.fill();
      g.lineWidth = 8; g.strokeStyle = INK; g.stroke();
      g.fillStyle = '#9aa3b5'; circle(0, 40 * f, 95); g.fill(); g.fillStyle = '#5c6478'; circle(0, 40 * f, 40); g.fill();
      for (let i = 0; i < 6; i++) { const ph = (t * 1.5 + i / 6) % 1; g.globalAlpha = 1 - ph; g.strokeStyle = CYA; g.lineWidth = 6; g.beginPath(); g.arc(230 + ph * 120, -60, 20 + ph * 40, -0.8, 0.8); g.stroke(); }
      g.restore();
      tag(`PRESIÓN ${Math.round(100 - 45 * f)} %`, 540, 1280, RED, 54, ease(prog(t, s[0], s[0] + 0.4)));
    } else {
      gauge(540, 930, 300, 259 * ease(prog(t, at(s, 0.45), at(s, 0.85))), 300, YEL, 'KM/H DE PROMEDIO');
    }
    return;
  }
  // récord 17 años: línea de tiempo
  const s = C2;
  label(t, s[0] - 0.15, 1e9, 'RÉCORD: 17 AÑOS', ['la vuelta más rápida de la F1'], YEL, 106);
  const e = ease(prog(t, s[0], at(s, 0.7)));
  const x0 = 140, x1 = 940, y = 950;
  g.lineCap = 'round'; g.lineWidth = 26; g.strokeStyle = 'rgba(255,255,255,0.12)'; line(x0, y, x1, y);
  g.strokeStyle = YEL; line(x0, y, x0 + (x1 - x0) * e, y); g.lineCap = 'butt';
  for (let k = 0; k <= 17; k++) { const x = x0 + (x1 - x0) * k / 17; if (k / 17 <= e + 1e-3) { circle(x, y, k % 5 === 0 ? 14 : 8); g.fillStyle = WHT; g.fill(); } }
  txt('1985', x0, y + 90, 64, WHT, { stroke: 7 });
  withA(ease(prog(t, at(s, 0.65), at(s, 0.8))), () => txt('2002', x1, y + 90, 64, WHT, { stroke: 7 }));
  const yr = Math.round(17 * e);
  txt(`${yr} ${yr === 1 ? 'AÑO' : 'AÑOS'}`, 540, y - 150, 140, YEL, { stroke: 10 });
  withA(ease(prog(t, s[0] + 0.2, s[0] + 0.6)), () => { photo(IMG.fw10, 190, 1140, 700, 300, 1.1, 0.55, 0.45, 22, ORA); credit('fw10', 1465, 1); });
}
// #2 VERSTAPPEN MONZA 2025
function scene2(t) {
  drawBG(t, 0.6);
  if (t < D1[0] - 0.15) { intro(t, D0, 2, 'MAX VERSTAPPEN', 'MONZA', '2025', 'rb21', 0.5, 0.52, YEL); return; }
  if (t < D2[0] - 0.15) {
    const s = D1;
    speedLines(t, 0.5);
    label(t, s[0] - 0.15, 1e9, 'EL TEMPLO DE LA VELOCIDAD', [], WHT, 76);
    mapCard(IMG.monza, 120, 450, 840, 430, ease(prog(t, s[0] - 0.1, s[0] + 0.3)), CYA);
    credit('monza', 905, ease(prog(t, s[0], s[0] + 0.4)));
    const k = ease(prog(t, s[0] + 0.1, at(s, 0.45)));
    lapClock(540, 1040, 78.792 * k, k >= 1 ? YEL : WHT, 120, 'VUELTA', CYA);
    gauge(540, 1310, 150, 264.7 * ease(prog(t, at(s, 0.5), at(s, 0.85))), 300, YEL, 'KM/H');
    return;
  }
  // tabla de récords (velocidad promedio)
  const s = D2;
  label(t, s[0] - 0.15, 1e9, 'LA MÁS RÁPIDA', ['de toda la historia de la F1'], YEL, 120);
  const rows = [['ROSBERG 1985', 259.0, ORA], ['HAMILTON 2020', 264.4, MER], ['VERSTAPPEN 2025', 264.7, YEL]];
  rows.forEach(([nm, v, c], i) => {
    const a = ease(prog(t, s[0] + 0.2 + i * 0.6, s[0] + 0.6 + i * 0.6));
    const f = (v - 240) / 26 * a;
    hbar(110, 720 + i * 200, 860, 90, f, c, nm, `${v.toFixed(1)} km/h`, a);
  });
  const cr = s[0] + 2.2;
  if (t > cr) { const e = popIn(t, cr, 0.5); g.save(); g.translate(540, 1360); g.scale(e, e); tag('RÉCORD VIGENTE', 0, 0, YEL, 64); g.restore(); }
  glow(540, 1120, 300, YEL, 0.4 * ease(prog(t, cr - 0.5, cr)));
}
// #1 SENNA MÓNACO 1988
function scene1(t) {
  drawBG(t, 0.6);
  if (t < E1[0] - 0.15) { intro(t, E0, 1, 'AYRTON SENNA', 'MÓNACO', '1988', 'mp44', 0.45, 0.55, YEL); return; }
  if (t < E2[0] - 0.1) {
    const s = E1;
    label(t, s[0] - 0.15, 1e9, 'EL MISMO McLAREN', ['Senna contra Prost'], WHT, 104);
    withA(ease(prog(t, s[0], s[0] + 0.4)), () => { photo(IMG.mp44, 140, 540, 800, 400, 1.15, 0.45, 0.6, 22, MCR); credit('mp44', 965, 1); });
    const k = ease(prog(t, s[0] + 0.3, at(s, 0.6)));
    lapClock(540, 1110, 83.998 * k, k >= 1 ? YEL : WHT, 96, 'SENNA', YEL);
    withA(ease(prog(t, at(s, 0.35), at(s, 0.5))), () => lapClock(540, 1300, 85.425 * ease(prog(t, at(s, 0.35), at(s, 0.75))), WHT, 70, 'PROST', CYA));
    const d = at(s, 0.78);
    if (t > d) { const e = popIn(t, d, 0.5); g.save(); g.translate(540, 1455); g.scale(e, e); tag('−1.427 s', 0, 0, YEL, 70); g.restore(); }
    return;
  }
  // el túnel
  const s = E2;
  const tt = t - s[0];
  g.save(); g.beginPath(); g.rect(0, 470, W, 1040); g.clip();
  for (let i = 14; i >= 0; i--) {
    const z = ((i + tt * 2.2) % 15) / 15, sc = Math.pow(z, 2.2);
    const w = 60 + 1500 * sc, h = 100 + 2500 * sc;
    g.globalAlpha = Math.min(1, z * 1.5) * 0.85;
    g.strokeStyle = i % 2 ? YEL : CYA; g.lineWidth = 3 + 12 * sc;
    g.beginPath(); g.roundRect(540 - w / 2, 960 - h / 2, w, h, 30 + 120 * sc); g.stroke();
  }
  g.restore();
  glow(540, 960, 260, WHT, 0.8);
  car(540, 1020, -Math.PI / 2, 3.2 + 0.1 * Math.sin(t * 6), MCL, '12', { dark: MCR, helmet: YEL });
  label(t, s[0] - 0.1, 1e9, '"UN TÚNEL"', ['ya no manejaba de forma consciente'], YEL, 130);
}
// CIERRE
function sceneClose(t) {
  drawBG(t, 0.5);
  const s = F0;
  const z = 1.1 + 0.15 * prog(t, s[0], s[1]);
  withA(ease(prog(t, s[0] - 0.3, s[0] + 0.3)), () => { photo(IMG.montecarlo, 60, 520, 960, 520, z, 0.55, 0.6, 26, YEL); credit('montecarlo', 1065, 1); });
  label(t, s[0] - 0.3, 1e9, 'LA VUELTA PERFECTA', ['Senna · Mónaco 1988'], YEL, 104);
  const e = ease(prog(t, at(s, 0.35), at(s, 0.55)));
  withA(e, () => {
    lapClock(540, 1250, '1:23.998', YEL, 120, 'CASI 40 AÑOS DESPUÉS', CYA);
  });
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
  [FLASHES[0], scene5], [FLASHES[1], scene4], [FLASHES[2], scene3],
  [FLASHES[3], scene2], [FLASHES[4], scene1], [FLASHES[5], sceneClose], [FLASHES[6], sceneEnd],
];
function render(t) {
  T = t;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  let i = 0; while (i + 1 < SCENES.length && SCENES[i + 1][0] <= t) i++;
  SCENES[i][1](t);
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
window.INFO = { END, frames: Math.ceil(END * 30) };
