// Flash Datos · video 19 · Abu Dabi 2021: el campeonato que se decidió en una vuelta
// Escena dibujada en canvas 2D (1080x1920). render(t) dibuja el cuadro del segundo t.
// Autos, pista y gráficos son dibujos originales (sin logotipos ni libreas reales).
'use strict';
const W = 1080, H = 1920;
const C = document.getElementById('c'), g = C.getContext('2d');
const SEG = {}; TM.segments.forEach(s => SEG[s.id] = s);
const PT = (id, k) => SEG[id].parts[k];
const END = TM.end;
const YEL = '#FFD84D', CYA = '#4FD8FF', WHT = '#FFFFFF', INK = '#080a14';
const HAMC = '#2fe0c0', VERC = '#ff4d6a', PERC = '#ff9a3c', GRY = '#8b97b3', RED = '#ff3b4e', GRN = '#3ddc84';
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, s) => a + (b - a) * s;
const ease = s => { s = clamp(s); return s * s * s * (s * (6 * s - 15) + 10); };
const easeOut = s => { s = clamp(s); return 1 - Math.pow(1 - s, 3); };
const easeIn = s => { s = clamp(s); return s * s; };
const backOut = s => { s = clamp(s); const c = 1.6; return 1 + (c + 1) * Math.pow(s - 1, 3) + c * Math.pow(s - 1, 2); };
const prog = (t, a, b) => clamp((t - a) / (b - a));
function fade(t, a, b, f = 0.25) { if (t < a || t > b) return 0; return Math.min(1, (t - a) / f, (b - t) / f); }
let T = 0;

// ---------------- recursos ----------------
const IMG = {};
const PHOTOS = [['yas', 'yas.jpg']];
const PHOTO_FOCUS = { yas: [0.5, 0.5] }, PHOTO_CREDIT = { yas: 'Mapa: Anthony Alessio Tralongo · CC BY-SA 4.0 · Wikimedia Commons' };
function loadImg(k, src) { return new Promise(r => { const i = new Image(); i.onload = () => { IMG[k] = i; r(); }; i.onerror = () => r(); i.src = src; }); }
window.READY = Promise.all([
  new FontFace('IB', 'url(fonts/Inter-Black.otf)').load().then(f => document.fonts.add(f)),
  new FontFace('IX', 'url(fonts/Inter-ExtraBold.otf)').load().then(f => document.fonts.add(f)),
  ...PHOTOS.map(([k, f]) => loadImg(k, 'img/' + f)),
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
function poly(pts, closed = true) { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); if (closed) g.closePath(); }
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
  g.fillStyle = 'rgba(6,10,24,0.85)'; g.fill(); g.lineWidth = 3; g.strokeStyle = col; g.stroke();
  g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, x, y + size * 0.03);
  g.restore();
}
function badge(text, x, y, e, bg = YEL, fg = INK, size = 60, rot = 0) {
  if (e <= 0) return;
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(e, e);
  g.font = `${size}px IB`; const w = g.measureText(text).width + size * 1.1, h = size * 1.75;
  g.beginPath(); g.roundRect(-w / 2, -h / 2, w, h, h / 2); g.fillStyle = bg; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  txt(text, 0, 3, size, fg, { stroke: 0 }); g.restore();
}
function popIn(t, a, d = 0.45) { return backOut(prog(t, a, a + d)); }

// ---------------- fondo ----------------
const BG = document.createElement('canvas'); BG.width = W; BG.height = H;
{
  const b = BG.getContext('2d');
  const gr = b.createRadialGradient(540, 880, 60, 540, 960, 1300);
  gr.addColorStop(0, '#142a62'); gr.addColorStop(0.5, '#0a1738'); gr.addColorStop(1, '#030814');
  b.fillStyle = gr; b.fillRect(0, 0, W, H);
}
function drawBG(t, gridA = 1, tint = null) {
  g.drawImage(BG, 0, 0);
  if (tint) { g.fillStyle = tint; g.fillRect(0, 0, W, H); }
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
function cleanCap(s) { return s.replace(/[⚡]/gu, '').replace(/\s+/g, ' ').trim(); }
function spokenLen(w) {
  const c = w.replace(/[.,:;…?!¡¿()"]/g, '');
  if (c === '8º') return 6;
  if (c === 'FIA') return 6;
  if (/^\d{4}$/.test(c)) return 18;
  if (/^\d+$/.test(c)) return c.length === 1 ? 5 : 4;
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
function label(t, a, b, title, subs = [], col = WHT, size = 104) {
  const al = fade(t, a, b, 0.25); if (al <= 0) return;
  g.save(); g.globalAlpha = al;
  const rise = (1 - Math.min(1, (t - a) / 0.3)) * 24;
  const y = 345 + rise;
  txt(title, W / 2, y, size, col, { maxW: 1000, stroke: 8 });
  let yy = y + size * 0.5 + 40;
  for (const s of subs) { txt(s, W / 2, yy, 50, CYA, { font: 'IX', maxW: 1000, stroke: 7 }); yy += 64; }
  g.restore();
}
function photo(img, x, y, w, h, zoom, fx, fy, r = 26, border = YEL) {
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
function credit(s, y) { txt(s, 540, y, 24, 'rgba(255,255,255,0.9)', { font: 'IX', stroke: 4 }); }

// =====================================================================
// AUTO DE F1 VISTO DESDE ARRIBA (dibujo original; apunta hacia +x)
// =====================================================================
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
// ---------------- semáforo de salida ----------------
function lights(x, y, lit, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  g.beginPath(); g.roundRect(x - 330, y - 70, 660, 140, 30); g.fillStyle = 'rgba(6,10,24,0.92)'; g.fill(); g.lineWidth = 5; g.strokeStyle = '#3a4258'; g.stroke();
  for (let i = 0; i < 5; i++) {
    const cx = x - 248 + i * 124; circle(cx, y, 46); g.fillStyle = '#1c2133'; g.fill();
    if (i < lit) { g.save(); g.shadowColor = RED; g.shadowBlur = 40; circle(cx, y, 40); g.fillStyle = RED; g.fill(); g.restore(); }
  }
  g.restore();
}

// ---------------- carretera vertical (vista de cámara de persecución) ----------------
const RX0 = 250, RX1 = 830;
function road(t, speed, a = 1, scTint = 0) {
  g.save(); g.globalAlpha *= a; g.beginPath(); g.rect(0, 520, W, 1000); g.clip();
  g.fillStyle = '#0e1a14'; g.fillRect(0, 520, W, 1000);
  for (let i = -1; i < 14; i++) { const y = 520 + ((i * 80 + t * speed) % 1040 + 1040) % 1040 - 40; for (const xx of [RX0 - 24, RX1]) { g.fillStyle = (i % 2) ? RED : WHT; g.fillRect(xx, y, 24, 40); g.fillStyle = (i % 2) ? WHT : RED; g.fillRect(xx, y + 40, 24, 40); } }
  g.fillStyle = '#2b3245'; g.fillRect(RX0, 520, RX1 - RX0, 1000);
  if (scTint > 0) { g.fillStyle = `rgba(255,216,77,${scTint * (0.08 + 0.06 * Math.sin(T * 10))})`; g.fillRect(RX0, 520, RX1 - RX0, 1000); }
  for (let i = -1; i < 12; i++) { const y = 520 + ((i * 120 + t * speed) % 1080 + 1080) % 1080 - 60; g.fillStyle = 'rgba(255,255,255,0.55)'; g.fillRect(538, y, 8, 60); }
  // bordes del cuadro de carretera
  const gr = g.createLinearGradient(0, 520, 0, 640); gr.addColorStop(0, 'rgba(3,8,20,1)'); gr.addColorStop(1, 'rgba(3,8,20,0)'); g.fillStyle = gr; g.fillRect(0, 520, W, 120);
  const gr2 = g.createLinearGradient(0, 1400, 0, 1520); gr2.addColorStop(0, 'rgba(3,8,20,0)'); gr2.addColorStop(1, 'rgba(3,8,20,1)'); g.fillStyle = gr2; g.fillRect(0, 1400, W, 120);
  g.restore();
}

// =====================================================================
// TIEMPOS
// =====================================================================
const S = id => SEG[id].t0, E = id => SEG[id].t1;
const F_EMP = S('empate') - 0.3, F_SAL = S('salida') - 0.3, F_CHE = S('checo') - 0.3, F_ESC = S('escape') - 0.3, F_LAT = S('latifi') - 0.25,
  F_LLA = S('llantas') - 0.3, F_MAS = S('masi') - 0.3, F_ULT = S('ultima') - 0.25, F_REB = S('rebase') - 0.3, F_FIN = S('final') - 0.3, E0 = E('final') + 0.15;
const FLASHES = [F_EMP, F_SAL, F_CHE, F_LAT, F_MAS, F_ULT, F_FIN, E0];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
}

// =====================================================================
// ESCENAS
// =====================================================================
function versus(t, a, cxL, cxR, y, k, sway = 1) {
  car(cxL, y + Math.sin(t * 2.1) * 8 * sway, -Math.PI / 2, k, HAMC, '44');
  car(cxR, y + Math.sin(t * 2.1 + 1.4) * 8 * sway, -Math.PI / 2, k, VERC, '33');
}
function sceneHook(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('gancho', 0);
  // mitades de color
  const sp = easeOut(prog(t, a, a + 0.6));
  g.save(); g.globalAlpha = 0.18 * sp; g.fillStyle = HAMC; g.fillRect(0, 0, W / 2, H); g.fillStyle = VERC; g.fillRect(W / 2, 0, W / 2, H); g.restore();
  g.save(); g.globalAlpha = sp; g.strokeStyle = 'rgba(255,255,255,0.35)'; g.lineWidth = 4; g.setLineDash([18, 16]); line(540, 520, 540, 1480); g.restore();
  const ent = easeOut(prog(t, a, a + 0.7));
  versus(t, a, 290, 790, lerp(1700, 1080, ent), 3.2);
  // nombres
  const e1 = popIn(t, a + 0.5), e2 = popIn(t, a + 0.9);
  if (e1 > 0) { g.save(); g.translate(290, 760); g.scale(e1, e1); txt('HAMILTON', 0, 0, 74, HAMC, { stroke: 8 }); g.restore(); }
  if (e2 > 0) { g.save(); g.translate(790, 760); g.scale(e2, e2); txt('VERSTAPPEN', 0, 0, 66, VERC, { stroke: 8 }); g.restore(); }
  // títulos en juego
  const e3 = popIn(t, a + 1.6), e4 = popIn(t, a + 3.3);
  badge('8º TÍTULO', 290, 1380, e3, HAMC, INK, 50, -0.04);
  badge('1er TÍTULO', 790, 1380, e4, VERC, INK, 50, 0.04);
  // "1 VUELTA"
  const e5 = popIn(t, a, 0.5);
  if (e5 > 0) { g.save(); g.translate(540, 470); g.scale(e5, e5); txt('1 VUELTA', 0, 0, 150, YEL, { stroke: 12 }); g.restore(); }
  txt('VS', 540, 1080, 90, WHT, { stroke: 9, alpha: ease(prog(t, a + 0.4, a + 0.8)) });
}
function sceneEmpate(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('empate', 0);
  label(t, a - 0.3, b + 0.6, 'ABU DABI 2021', ['última carrera del año'], WHT, 118);
  if (IMG.yas) {
    const ep = easeOut(prog(t, a, a + 0.6));
    g.save(); g.globalAlpha = ep; g.translate(0, (1 - ep) * 60);
    photo(IMG.yas, 60, 560, 960, 560, 1.0 + 0.1 * prog(t, a, b + 0.6), PHOTO_FOCUS.yas[0], PHOTO_FOCUS.yas[1], 26, CYA);
    credit(PHOTO_CREDIT.yas, 1150);
    g.restore();
  } else {
    MAP = { s: 0.9, cx: 525, cy: 520, ox: 540, oy: 850 };
    drawTrack(easeOut(prog(t, a, a + 0.6)));
    trackLabel(0.0, 'YAS MARINA', CYA, -180, 0, ease(prog(t, a + 0.4, a + 0.8)), 34);
  }
  // marcador de puntos
  const e = easeOut(prog(t, a + 1.2, a + 1.8));
  if (e > 0) {
    g.save(); g.globalAlpha = e; g.translate(0, (1 - e) * 40);
    g.beginPath(); g.roundRect(70, 1210, 940, 180, 30); g.fillStyle = 'rgba(6,10,24,0.9)'; g.fill(); g.lineWidth = 5; g.strokeStyle = YEL; g.stroke();
    txt('HAM', 190, 1265, 46, HAMC, { stroke: 5 }); txt('VER', 890, 1265, 46, VERC, { stroke: 5 });
    const v = Math.round(369.5 * ease(prog(t, a + 1.3, a + 2.6)) * 2) / 2;
    txt(v.toFixed(1), 260, 1335, 76, WHT, { stroke: 7 }); txt(v.toFixed(1), 820, 1335, 76, WHT, { stroke: 7 });
    txt('PUNTOS', 540, 1265, 34, CYA, { font: 'IX', stroke: 4 });
    g.restore();
    badge('EMPATE', 540, 1335, popIn(t, a + 2.7), YEL, INK, 58, -0.04);
  }
}
function towerRow(x, y, pos, name, col, gapS, a = 1, w = 330) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  g.beginPath(); g.roundRect(x, y - 30, w, 60, 12); g.fillStyle = 'rgba(6,10,24,0.9)'; g.fill();
  g.fillStyle = col; g.fillRect(x, y - 30, 12, 60);
  txt(String(pos), x + 42, y, 36, WHT, { stroke: 0 });
  txt(name, x + 80, y, 36, WHT, { align: 'left', stroke: 0 });
  if (gapS) txt(gapS, x + w - 16, y, 30, YEL, { align: 'right', font: 'IX', stroke: 0 });
  g.restore();
}
function sceneSalida(t) {
  drawBG(t, 0.4);
  const [a, b] = PT('salida', 0);
  MAP = MAPD;
  drawTrack(1);
  // semáforo: se encienden y se apagan
  const lit = t < a + 0.15 ? Math.floor(clamp((t - (a - 0.3)) / 0.09, 0, 5)) : 0;
  lights(540, 470, lit, 1 - prog(t, a + 1.0, a + 1.3));
  const go = t >= a + 0.15;
  if (go) badge('¡ARRANCAN!', 540, 470, popIn(t, a + 0.15) * (1 - prog(t, a + 1.0, a + 1.2)), YEL, INK, 64, -0.03);
  // autos: Max sale primero, Lewis lo pasa
  const s = ease(prog(t, a + 0.15, b + 0.3));
  const uV = -0.012 + 0.16 * s, uH = -0.024 + 0.19 * s;
  const ham = carOn(uH, lerp(-10, 0, s), HAMC, '44'), ver = carOn(uV, lerp(10, 0, s), VERC, '33');
  nameTag(ham[0] - 70, ham[1], 'HAM', HAMC, 28); nameTag(ver[0] - 70, ver[1] - 50, 'VER', VERC, 28);
  // torre de posiciones
  const swap = uH > uV;
  const ta = ease(prog(t, a + 1.2, a + 1.5));
  towerRow(375, 560, 1, swap ? 'HAMILTON' : 'VERSTAPPEN', swap ? HAMC : VERC, '', ta);
  towerRow(375, 630, 2, swap ? 'VERSTAPPEN' : 'HAMILTON', swap ? VERC : HAMC, '', ta);
  if (swap) badge('P1 HAMILTON', 540, 1450, popIn(t, a + 1.9), HAMC, INK, 50, 0.03);
}
function sceneCheco(t) {
  drawBG(t, 0.3);
  const [a, b] = PT('checo', 0), [c, d] = PT('checo', 1);
  road(t, 900);
  label(t, a - 0.3, d + 0.6, 'CHECO PÉREZ', ['el muro de Red Bull'], PERC, 120);
  // Pérez adelante defendiendo; Hamilton atrás buscando por dónde pasar
  const att = Math.sin((t - a) * 2.2);
  const hx = 540 + att * 140, px = 540 + Math.sin((t - a) * 2.2 - 0.55) * 135;
  const pe = easeOut(prog(t, a, a + 0.6));
  g.save(); g.beginPath(); g.rect(0, 520, W, 1000); g.clip();
  car(px, lerp(560, 820, pe), -Math.PI / 2, 2.6, PERC, '11', { helmet: '#ffe066' });
  car(hx, 1180 + Math.cos(t * 3) * 10, -Math.PI / 2, 2.6, HAMC, '44');
  // Max se acerca desde abajo
  const close = ease(prog(t, a + 5.0, b));
  if (close > 0.05) { car(540, lerp(1660, 1430, close), -Math.PI / 2, 2.1, VERC, '33'); }
  g.restore();
  nameTag(px + (px < 540 ? 190 : -190), lerp(560, 820, pe), 'PÉREZ', PERC, 34); nameTag(hx, 1180 + 165, 'HAMILTON', HAMC, 30);
  // panel de diferencia con Max
  const gap = lerp(9.0, 1.9, ease(prog(t, a + 5.6, b - 0.3)));
  g.beginPath(); g.roundRect(60, 560, 330, 150, 24); g.fillStyle = 'rgba(6,10,24,0.9)'; g.fill(); g.lineWidth = 5; g.strokeStyle = VERC; g.stroke();
  txt('MAX A', 225, 600, 32, VERC, { font: 'IX', stroke: 0 });
  txt(`${gap.toFixed(1)} s`, 225, 660, 66, WHT, { stroke: 0 });
  g.beginPath(); g.roundRect(690, 560, 330, 150, 24); g.fillStyle = 'rgba(6,10,24,0.9)'; g.fill(); g.lineWidth = 5; g.strokeStyle = PERC; g.stroke();
  txt('DEFENSA', 855, 600, 32, PERC, { font: 'IX', stroke: 0 });
  txt('VUELTAS 20-21', 855, 660, 44, WHT, { stroke: 0, maxW: 300 });
  // radio de Max
  if (t > c - 0.3) {
    const e = popIn(t, c - 0.2);
    g.save(); g.translate(540, 1000); g.scale(e, e);
    g.beginPath(); g.roundRect(-330, -95, 660, 190, 34); g.fillStyle = 'rgba(255,255,255,0.97)'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
    for (let i = 0; i < 3; i++) { g.strokeStyle = VERC; g.lineWidth = 8; g.beginPath(); g.arc(-250, 0, 22 + i * 18, -0.8, 0.8); g.stroke(); }
    txt('RADIO DE MAX', 40, -42, 34, '#5a6380', { font: 'IX', stroke: 0 });
    txt('¡LEYENDA!', 40, 22, 84, INK, { stroke: 0 });
    g.restore();
  }
}
function sceneEscape(t) {
  drawBG(t, 0.4);
  const [a, b] = PT('escape', 0);
  MAP = MAPD;
  drawTrack(1);
  label(t, a - 0.3, b + 0.3, 'VUELTA 53 / 58', ['faltan 5 vueltas'], WHT, 110);
  const s = (t - a) * 0.09;
  const ham = carOn(0.55 + s, 0, HAMC, '44'), ver = carOn(0.55 + s - 0.13 * ease(prog(t, a, a + 2)) - 0.02, 0, VERC, '33');
  nameTag(ham[0], ham[1] - 48, 'HAM', HAMC, 28); nameTag(ver[0], ver[1] - 48, 'VER', VERC, 28);
  const gap = lerp(2, 11, ease(prog(t, a + 0.3, b - 0.5)));
  badge(`HAMILTON +${gap.toFixed(0)} s`, 540, 1330, popIn(t, a + 0.3), HAMC, INK, 52, -0.03);
  const e = popIn(t, b - 1.0);
  if (e > 0) { g.save(); g.translate(540, 1450); g.scale(e, e); g.rotate(-0.04); txt('8º TÍTULO… CASI', 0, 0, 76, YEL, { stroke: 9 }); g.restore(); }
}
function sceneLatifi(t) {
  drawBG(t, 0.3);
  const [a, b] = PT('latifi', 0);
  MAP = MAPD;
  const crash = a + 0.5, sc = a + 1.6;
  drawTrack(1, { sc: t > sc });
  // Latifi pierde el control en la curva 14
  const [lx, ly, la] = tpos(U_T14 - 0.02);
  const sl = ease(prog(t, a - 0.25, crash));
  const cx = MX(lx) + Math.cos(la) * 70 * sl + Math.sin(la) * 70 * sl, cy = MY(ly) + Math.sin(la) * 70 * sl - Math.cos(la) * 70 * sl * -1;
  car(cx, cy, la + 1.8 * sl, 0.75 * MAP.s, GRY, '6', { shadow: false });
  if (t > crash) {
    const k = prog(t, crash, crash + 0.8);
    for (let i = 0; i < 14; i++) { const an = i * 0.9 + 0.3, r = 20 + 140 * k * (0.5 + 0.5 * ((i * 37) % 10) / 10); g.save(); g.globalAlpha = (1 - k); circle(cx + Math.cos(an) * r, cy + Math.sin(an) * r, 7); g.fillStyle = i % 2 ? YEL : ORA; g.fill(); g.restore(); }
    tag('CURVA 14', cx + 10, cy + 70, WHT, 32, ease(prog(t, crash, crash + 0.3)));
    nameTag(cx, cy - 60, 'LATIFI', GRY, 30, ease(prog(t, crash, crash + 0.3)));
  }
  // los punteros en pista
  const s = (t - a) * (t > sc ? 0.03 : 0.09);
  const ham = carOn(0.86 + Math.min(s, 0.2), 0, HAMC, '44'); carOn(0.73 + Math.min(s, 0.2), 0, VERC, '33');
  label(t, a - 0.25, b + 0.6, '¡CHOQUE!', ['vuelta 53'], RED, 130);
  if (t > sc) {
    const e = popIn(t, sc, 0.4);
    g.save(); g.translate(540, 1440); g.scale(e, e); g.rotate(-0.03);
    g.beginPath(); g.roundRect(-460, -70, 920, 140, 26); g.fillStyle = YEL; g.fill(); g.lineWidth = 7; g.strokeStyle = INK; g.stroke();
    const blink = Math.sin(T * 14) > 0;
    circle(-400, 0, 26); g.fillStyle = blink ? '#ff9f1c' : '#5a3a10'; g.fill(); circle(400, 0, 26); g.fillStyle = blink ? '#5a3a10' : '#ff9f1c'; g.fill();
    txt('AUTO DE SEGURIDAD', 0, 4, 58, INK, { stroke: 0 });
    g.restore();
  }
}
const ORA = '#ff9f1c';
function tyre(x, y, r, band, label1, label2, wear, col, e) {
  if (e <= 0) return;
  g.save(); g.translate(x, y); g.scale(e, e); g.rotate(T * (wear > 0.5 ? 0.6 : 1.4));
  circle(0, 0, r); g.fillStyle = '#121418'; g.fill(); g.lineWidth = 8; g.strokeStyle = INK; g.stroke();
  // dibujo de desgaste
  for (let i = 0; i < 24; i++) { const an = i * Math.PI / 12; g.strokeStyle = `rgba(255,255,255,${0.05 + 0.1 * wear})`; g.lineWidth = 3; line(Math.cos(an) * r * 0.93, Math.sin(an) * r * 0.93, Math.cos(an + 0.1) * r * 0.82, Math.sin(an + 0.1) * r * 0.82); }
  g.lineWidth = r * 0.07; g.strokeStyle = band; circle(0, 0, r * 0.72); g.stroke();
  circle(0, 0, r * 0.5); g.fillStyle = '#2b3245'; g.fill(); g.lineWidth = 6; g.strokeStyle = '#8b97b3'; g.stroke();
  for (let i = 0; i < 5; i++) { const an = i * Math.PI * 2 / 5; g.strokeStyle = '#8b97b3'; g.lineWidth = 10; line(Math.cos(an) * r * 0.12, Math.sin(an) * r * 0.12, Math.cos(an) * r * 0.45, Math.sin(an) * r * 0.45); }
  circle(0, 0, r * 0.12); g.fillStyle = col; g.fill();
  g.restore();
  txt(label1, x, y + r + 60, 54, band === WHT ? WHT : band, { stroke: 7, alpha: e });
  txt(label2, x, y + r + 122, 40, CYA, { font: 'IX', stroke: 6, alpha: e });
}
function sceneLlantas(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('llantas', 0);
  label(t, a - 0.3, b + 0.6, 'LLANTAS', ['¿parar o no parar?'], WHT, 120);
  const mid = a + (b - a) * 0.42;
  nameTag(290, 640, 'VERSTAPPEN', VERC, 40, ease(prog(t, a, a + 0.3)));
  tyre(290, 900, 200, RED, 'BLANDAS', 'NUEVAS', 0.1, VERC, popIn(t, a + 0.1));
  nameTag(790, 640, 'HAMILTON', HAMC, 40, ease(prog(t, mid - 0.3, mid)));
  tyre(790, 900, 200, WHT, 'DURAS', '+40 VUELTAS', 1, HAMC, popIn(t, mid - 0.2));
  badge('ENTRA A PITS', 290, 1390, popIn(t, a + 0.6), VERC, INK, 44, -0.04);
  badge('SE QUEDA EN PISTA', 790, 1390, popIn(t, mid + 0.6), HAMC, INK, 40, 0.04);
}
function sceneMasi(t) {
  drawBG(t, 0.3);
  const [a, b] = PT('masi', 0);
  const m2 = a + 5.1;   // "y luego dejó pasar solo a los cinco..."
  road(t, 260, 1, 1);
  label(t, a - 0.3, b + 0.6, 'MICHAEL MASI', ['director de carrera'], WHT, 116);
  // fila detrás del auto de seguridad: SC, HAM, 5 rezagados, VER
  const go = ease(prog(t, m2 + 0.6, b - 0.2));
  const Y0 = 700, step = 108;
  const lapped = [0, 1, 2, 3, 4];
  // auto de seguridad
  car(540, Y0, -Math.PI / 2, 1.25, YEL, null, { dark: '#3a3215' });
  txt('SC', 540, Y0 + 2, 30, INK, { stroke: 0 });
  car(540, Y0 + step, -Math.PI / 2, 1.25, HAMC, '44');
  nameTag(720, Y0 + step, 'HAM', HAMC, 30);
  lapped.forEach(i => {
    const y = Y0 + step * (2 + i) - go * (step * (2 + i) + 420 + i * 60);
    const x = 540 + Math.sin(prog(t, m2 + 0.6 + i * 0.08, m2 + 1.2 + i * 0.08) * Math.PI) * 150 * (i % 2 ? 1 : -1) + (go > 0.3 ? 0 : 0);
    if (y > 470) car(x, y, -Math.PI / 2, 1.1, GRY, null, { helmet: '#c8d1e2' });
  });
  const vy = lerp(Y0 + step * 7, Y0 + step * 2, go);
  car(540, vy, -Math.PI / 2, 1.25, VERC, '33'); nameTag(720, vy, 'VER', VERC, 30);
  if (go < 0.2) tag('5 REZAGADOS', 820, Y0 + step * 4, GRY, 34, 1 - go * 5);
  // mensajes de dirección de carrera
  const msg = (y, head, body, col, mark, e) => {
    if (e <= 0) return;
    g.save(); g.translate(540, y); g.scale(e, e);
    g.beginPath(); g.roundRect(-480, -78, 960, 156, 22); g.fillStyle = 'rgba(6,10,24,0.94)'; g.fill(); g.lineWidth = 5; g.strokeStyle = col; g.stroke();
    txt(head, -440, -36, 28, CYA, { align: 'left', font: 'IX', stroke: 0 });
    txt(body, -440, 24, 46, WHT, { align: 'left', maxW: 760, stroke: 0 });
    circle(410, 0, 46); g.fillStyle = col; g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
    txt(mark, 410, 4, 54, INK, { stroke: 0 });
    g.restore();
  };
  const e1 = popIn(t, a + 2.2), e2 = popIn(t, m2 - 0.1);
  if (t < m2 - 0.1) msg(1440, 'DIRECCIÓN DE CARRERA', 'Los rezagados NO pueden pasar', RED, '✕', e1);
  else msg(1440, 'DIRECCIÓN DE CARRERA', 'Pasan SOLO los 5 entre HAM y VER', GRN, '✓', e2);
}
function sceneUltima(t) {
  drawBG(t, 0.6, 'rgba(255,59,78,0.06)');
  const [a, b] = PT('ultima', 0);
  const flip = t > a + 0.35;
  const e = popIn(t, a - 0.2, 0.4);
  g.save(); g.translate(540, 760); g.scale(e, e);
  txt('VUELTA', 0, -120, 70, CYA, { font: 'IX', stroke: 7 });
  txt(flip ? '58 / 58' : '57 / 58', 0, 20, 190, flip ? YEL : WHT, { stroke: 14 });
  g.restore();
  // latido
  g.save(); g.strokeStyle = RED; g.lineWidth = 9; g.lineJoin = 'round'; g.beginPath();
  for (let x = 60; x <= 1020; x += 6) { const ph = ((x - 60) / 960 * 3 - (t - a) * 1.6) % 1; const yb = 1010; const k = ph > 0.42 && ph < 0.58 ? Math.sin((ph - 0.42) / 0.16 * Math.PI * 2) * 90 : 0; if (x === 60) g.moveTo(x, yb - k); else g.lineTo(x, yb - k); }
  g.stroke(); g.restore();
  // los dos, uno detrás del otro
  car(540, 1200, -Math.PI / 2, 2.0, HAMC, '44');
  car(540, 1390, -Math.PI / 2, 2.0, VERC, '33');
  badge('TODO O NADA', 540, 1080, popIn(t, a + 0.9), YEL, INK, 62, -0.04);
}
function sceneRebase(t) {
  drawBG(t, 0.4);
  const [a, b] = PT('rebase', 0);
  MAP = MAPD;
  drawTrack(1);
  // avance de la vuelta: rápido hasta la curva 5, rebase, ataque en la recta y meta
  const t5 = a + (b - a) * 0.22, pass = a + (b - a) * 0.42, att = a + (b - a) * 0.62, fin = b + 0.2;
  let u;
  if (t < t5) u = lerp(0, U_T5 - 0.015, ease(prog(t, a - 0.3, t5)));
  else if (t < att) u = lerp(U_T5 - 0.015, U_REC + 0.02, prog(t, t5, att));
  else u = lerp(U_REC + 0.02, 1.0, easeIn(prog(t, att, fin)));
  const p = prog(t, t5, pass);               // Max se tira por dentro y queda adelante
  const dV = lerp(-0.012, 0.012, ease(p)), offV = Math.sin(Math.PI * clamp(p * 1.1)) * 16;
  const q = prog(t, pass + 0.2, att + 0.4);  // Lewis ataca en la recta
  const dH = -0.012 + Math.sin(Math.PI * q) * 0.008 * (t < att + 0.4 ? 1 : 0), offH = -Math.sin(Math.PI * q) * 16;
  const ham = carOn(u + (t > t5 ? dH : 0.012), t > t5 ? offH : 0, HAMC, '44', 0.75);
  const ver = carOn(u + (t > t5 ? dV : 0), t > t5 ? offV : 0, VERC, '33', 0.75);
  nameTag(ver[0], ver[1] - 52, 'VER', VERC, 28); nameTag(ham[0], ham[1] + 52, 'HAM', HAMC, 28);
  trackLabel(U_T5, 'CURVA 5', YEL, -60, -80, fade(t, a, att + 0.3), 34);
  trackLabel(0, 'META', WHT, -110, 0, fade(t, fin - 1.2, fin + 1), 34);
  trackLabel(U_REC, 'RECTA', CYA, 40, -75, fade(t, pass, b), 34);
  label(t, a - 0.3, b + 0.3, 'ÚLTIMA VUELTA', [], YEL, 116);
  if (t > pass) badge('¡LO PASA!', 540, 520, popIn(t, pass) * (1 - prog(t, att - 0.2, att)), VERC, INK, 60, -0.04);
  if (t > att) badge('¡ATAQUE!', 540, 520, popIn(t, att) * (1 - prog(t, b - 0.7, b - 0.5)), HAMC, INK, 60, 0.04);
  if (t > b - 0.5) badge('NO ALCANZÓ', 540, 520, popIn(t, b - 0.5), WHT, INK, 60, -0.03);
}
function trophy(x, y, s, a = 1) {
  g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s);
  g.shadowColor = YEL; g.shadowBlur = 50;
  g.beginPath(); g.moveTo(-90, -120); g.lineTo(90, -120); g.quadraticCurveTo(90, 30, 0, 50); g.quadraticCurveTo(-90, 30, -90, -120); g.closePath();
  g.fillStyle = YEL; g.fill(); g.shadowBlur = 0; g.lineWidth = 8; g.strokeStyle = INK; g.stroke();
  g.lineWidth = 16; g.strokeStyle = YEL; g.beginPath(); g.arc(-95, -70, 40, Math.PI * 0.5, Math.PI * 1.5); g.stroke(); g.beginPath(); g.arc(95, -70, 40, -Math.PI * 0.5, Math.PI * 0.5); g.stroke();
  g.fillStyle = YEL; g.fillRect(-18, 48, 36, 60); g.beginPath(); g.roundRect(-75, 105, 150, 40, 8); g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  txt('2021', 0, -50, 46, INK, { stroke: 0 });
  g.restore();
}
function sceneFinal(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('final', 0), [c, d] = PT('final', 1);
  if (t < c - 0.25) {
    const fiaEnd = a + 2.9, champ = a + 5.2;   // "pero el resultado no cambió" / "Verstappen fue campeón"
    if (t < fiaEnd + 0.3) {
      label(t, a - 0.3, fiaEnd + 0.3, 'LA FIA', ['investigó lo que pasó'], WHT, 120);
      // hoja de informe con sello
      g.save(); g.globalAlpha = fade(t, a - 0.3, fiaEnd + 0.3);
      g.beginPath(); g.roundRect(240, 600, 600, 720, 20); g.fillStyle = '#eef1f7'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
      txt('INFORME', 540, 670, 44, INK, { stroke: 0 });
      for (let i = 0; i < 9; i++) { g.fillStyle = '#b9c2d3'; g.fillRect(300, 740 + i * 52, i % 3 === 2 ? 320 : 480, 16); }
      g.restore();
      const e = popIn(t, a + 1.0, 0.35);
      if (e > 0) { g.save(); g.translate(540, 980); g.rotate(-0.18); g.scale(1.6 - 0.6 * e, 1.6 - 0.6 * e); g.globalAlpha = Math.min(1, e) * fade(t, a - 0.3, fiaEnd + 0.3);
        g.lineWidth = 12; g.strokeStyle = RED; g.beginPath(); g.roundRect(-330, -85, 660, 170, 20); g.stroke(); txt('ERROR HUMANO', 0, 6, 82, RED, { stroke: 0 }); g.restore(); }
    } else {
      if (t < champ - 0.1) {
        // el resultado se queda: bandera a cuadros con el 33 adelante
        label(t, fiaEnd + 0.1, champ, 'RESULTADO FINAL', [], WHT, 110);
        for (let i = 0; i < 12; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? WHT : INK; g.fillRect(i * 90, 1050 + j * 45, 90, 45); }
        const e0 = popIn(t, fiaEnd + 0.2);
        towerRow(300, 700, 1, 'VERSTAPPEN', VERC, '', e0 > 0 ? 1 : 0, 480); towerRow(300, 780, 2, 'HAMILTON', HAMC, '+2.256 s', e0 > 0 ? 1 : 0, 480);
        badge('NO CAMBIÓ', 540, 1300, popIn(t, fiaEnd + 0.6), YEL, INK, 70, -0.04);
      } else {
        label(t, champ - 0.1, c - 0.2, 'CAMPEÓN 2021', ['su primer título'], YEL, 120);
        const e = popIn(t, champ - 0.1, 0.55);
        trophy(540, 860, 1.6 * e, e > 0 ? 1 : 0);
        car(540, 1330, -Math.PI / 2, 2.4 * Math.min(1, e), VERC, '33');
        badge('MAX VERSTAPPEN', 540, 1150, popIn(t, champ + 0.4), VERC, INK, 56, -0.03);
      }
    }
  } else {
    label(t, c - 0.2, d + 0.6, 'SIN CHECO…', ['no lo habría logrado'], PERC, 128);
    const e = easeOut(prog(t, c - 0.2, c + 0.5));
    car(lerp(-200, 540, e), 940, -Math.PI / 2 + (1 - e) * 1.2, 3.4, PERC, '11', { helmet: '#ffe066' });
    nameTag(540, 690, 'CHECO PÉREZ', PERC, 44, e);
    badge('MINISTRO DE DEFENSA', 540, 1230, popIn(t, c + 1.1), YEL, INK, 50, -0.04);
    car(380, 1400, -Math.PI / 2, 1.6, VERC, '33'); car(700, 1400, -Math.PI / 2, 1.6, PERC, '11', { helmet: '#ffe066' });
  }
}
function sceneEnd(t) {
  drawBG(t, 0.7);
  const e = backOut(prog(t, E0, E0 + 0.5));
  g.save(); g.translate(540, 830); g.scale(e, e);
  g.shadowColor = YEL; g.shadowBlur = 60; bolt(0, 0, 330); g.fillStyle = YEL; g.fill(); g.lineWidth = 10; g.strokeStyle = INK; g.stroke(); g.restore();
  txt('FLASH DATOS', 540, 1090, 112, WHT, { stroke: 9, alpha: ease(prog(t, E0 + 0.15, E0 + 0.5)) });
  txt('Síguenos para más datos', 540, 1200, 54, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, E0 + 0.3, E0 + 0.7)) });
}

// =====================================================================
function crossfade(t, a, b, sceneA, sceneB) {
  const s = prog(t, a, b);
  if (s <= 0) return sceneA(t);
  if (s >= 1) return sceneB(t);
  sceneA(t); g.save(); g.globalAlpha = s; sceneB(t); g.restore();
}
function render(t) {
  T = t;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  if (t < F_EMP) sceneHook(t);
  else if (t < F_SAL) sceneEmpate(t);
  else if (t < F_CHE) sceneSalida(t);
  else if (t < F_ESC) sceneCheco(t);
  else if (t < F_LAT) crossfade(t, F_ESC, F_ESC + 0.4, sceneCheco, sceneEscape);
  else if (t < F_LLA) sceneLatifi(t);
  else if (t < F_MAS) crossfade(t, F_LLA, F_LLA + 0.4, sceneLatifi, sceneLlantas);
  else if (t < F_ULT) sceneMasi(t);
  else if (t < F_REB) sceneUltima(t);
  else if (t < F_FIN) crossfade(t, F_REB, F_REB + 0.35, sceneUltima, sceneRebase);
  else if (t < E0) sceneFinal(t);
  else sceneEnd(t);
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  if (t < E0) drawCaption(t);
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
