// Flash Datos · video 21 · Cómo funciona un celular por dentro (con el iPhone Duo)
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
  if (c === 'A20') return 8;
  if (c === '5.4' || c === '7.6' || c === '5.2') return 15;
  if (c === '48') return 14;
  if (c === '20') return 6;
  if (c === 'OLED') return 5;
  if (c === 'iPHONE') return 6;
  if (/^\d{4}$/.test(c)) return 24;
  if (/^\d+$/.test(c)) return c.length === 1 ? 4 : 8;
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


// ---------------- tiempos ----------------
const G0 = PT('gancho', 0), G1 = PT('gancho', 1);
const B0 = PT('bateria', 0), B1 = PT('bateria', 1), C0 = PT('chip', 0), C1 = PT('chip', 1);
const S0 = PT('pantalla', 0), S1 = PT('pantalla', 1), K0 = PT('camaras', 0), K1 = PT('camaras', 1);
const Q0 = PT('carga', 0), Q1 = PT('carga', 1), F0 = PT('final', 0), F1 = PT('final', 1);
const at = (p, f) => p[0] + (p[1] - p[0]) * f;
const FLASHES = [G1[0] - 0.25, B0[0] - 0.3, C0[0] - 0.15, S0[0] - 0.3, K0[0] - 0.3, Q0[0] - 0.3, F0[0] - 0.3, F1[1] + 0.1];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
}
function hash(i, j, k) { let h = (i * 374761393 + j * 668265263 + k * 2246822519) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295; }

// ---------------- motor 3D sencillo (ortográfico) ----------------
const CAM = { yaw: 0, pitch: 0, cx: 540, cy: 960, s: 300 };
function P3(x, y, z) {
  const cy = Math.cos(CAM.yaw), sy = Math.sin(CAM.yaw), cp = Math.cos(CAM.pitch), sp = Math.sin(CAM.pitch);
  const x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
  const y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
  return [CAM.cx + CAM.s * x1, CAM.cy - CAM.s * y2, z2];
}
const v3 = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k];
// Cara plana: centro O, ejes U y V (unitarios); coordenadas locales en centésimas (y local hacia abajo = -V)
function setFace(O, U, V) {
  const p0 = P3(...O), pu = P3(...v3(O, U, 0.01)), pv = P3(...v3(O, V, 0.01));
  const ax = pu[0] - p0[0], ay = pu[1] - p0[1], bx = -(pv[0] - p0[0]), by = -(pv[1] - p0[1]);
  g.setTransform(ax, ay, bx, by, p0[0], p0[1]);
  return ax * by - ay * bx;
}
function facing(O, U, V) { const p0 = P3(...O), pu = P3(...v3(O, U, 0.01)), pv = P3(...v3(O, V, 0.01)); return (pu[0] - p0[0]) * (-(pv[1] - p0[1])) - (pu[1] - p0[1]) * (-(pv[0] - p0[0])); }
function screenPoly(pts) { const q = pts.map(p => P3(...p)); g.beginPath(); g.moveTo(q[0][0], q[0][1]); for (let i = 1; i < q.length; i++) g.lineTo(q[i][0], q[i][1]); g.closePath(); }
// Losa: cara superior en Ci con normal N; ejes A, B; medio ancho a, medio alto b, grosor t (hacia -N)
function slab(Ci, A, B, N, a, b, t, topFn, botFn, side = TI, alpha = 1, glow = 0) {
  g.save(); g.globalAlpha *= alpha;
  const Co = v3(Ci, N, -t);
  const cor = (C, sa, sb) => v3(v3(C, A, sa * a), B, sb * b);
  const topVis = facing(Ci, A, B) > 0;
  const drawFace = (C, isTop) => {
    g.save(); setFace(C, A, B);
    const fn = isTop ? topFn : botFn;
    if (fn) fn(a * 100, b * 100); else { g.beginPath(); g.roundRect(-a * 100, -b * 100, a * 200, b * 200, 8); g.fillStyle = TI_D; g.fill(); }
    g.restore();
  };
  g.setTransform(1, 0, 0, 1, 0, 0);
  drawFace(topVis ? Co : Ci, !topVis);
  g.setTransform(1, 0, 0, 1, 0, 0);
  const sides = [[[-1, -1], [1, -1]], [[1, -1], [1, 1]], [[1, 1], [-1, 1]], [[-1, 1], [-1, -1]]];
  for (const [p, q] of sides) {
    screenPoly([cor(Ci, ...p), cor(Ci, ...q), cor(Co, ...q), cor(Co, ...p)]);
    g.fillStyle = side; g.fill(); g.lineWidth = 1.5; g.strokeStyle = 'rgba(10,14,30,0.6)'; g.stroke();
  }
  drawFace(topVis ? Ci : Co, topVis);
  if (glow > 0) {
    g.setTransform(1, 0, 0, 1, 0, 0);
    screenPoly([cor(Ci, -1, -1), cor(Ci, 1, -1), cor(Ci, 1, 1), cor(Ci, -1, 1)]);
    g.globalAlpha = alpha * glow; g.shadowColor = YEL; g.shadowBlur = 30; g.lineWidth = 6; g.strokeStyle = YEL; g.stroke(); g.shadowBlur = 0;
  }
  g.restore(); g.setTransform(1, 0, 0, 1, 0, 0);
}
const X3 = [1, 0, 0], Y3 = [0, 1, 0], Z3 = [0, 0, 1];
const TAGS = [];
function flushTags() { for (const tg of TAGS) tag(tg.text, tg.x, tg.y, tg.col, tg.size || 38, tg.a); TAGS.length = 0; }
function tag3(p, text, col, a, size = 38, dx = 0, dy = 0) { if (a <= 0) return; const q = P3(...p); TAGS.push({ text, x: q[0] + dx, y: q[1] + dy, col, a, size }); }

// ---------------- contenidos de las caras ----------------
// fondo de pantalla genérico (sin marcas): degradado con ondas y el rayo del canal
function wallpaper(w, h, t, crease = false) {
  g.beginPath(); g.roundRect(-w, -h, 2 * w, 2 * h, 9); g.fillStyle = '#05060c'; g.fill();
  g.save(); g.beginPath(); g.roundRect(-w + 2.5, -h + 2.5, 2 * w - 5, 2 * h - 5, 7); g.clip();
  const gr = g.createLinearGradient(-w, -h, w, h);
  gr.addColorStop(0, '#2b1a6e'); gr.addColorStop(0.45, '#0f3d8c'); gr.addColorStop(1, '#0a7c8c');
  g.fillStyle = gr; g.fillRect(-w, -h, 2 * w, 2 * h);
  for (let i = 0; i < 4; i++) {
    g.beginPath();
    for (let x = -w; x <= w; x += 4) { const y = -h * 0.2 + i * h * 0.28 + Math.sin(x * 0.03 + t * 1.3 + i) * h * 0.12; x === -w ? g.moveTo(x, y) : g.lineTo(x, y); }
    g.lineWidth = 6 + i * 2; g.strokeStyle = `rgba(${i % 2 ? '79,216,255' : '255,216,77'},${0.18 + 0.05 * i})`; g.stroke();
  }
  const ic = Math.min(w, h) * 0.13, cols = Math.max(2, Math.floor(w * 2 / (ic * 2.2)));
  for (let r = 0; r < 2; r++) for (let c = 0; c < cols; c++) {
    const x = -w + (c + 0.5) * (2 * w / cols), y = h * 0.42 + r * ic * 1.35 - ic * 0.6;
    g.beginPath(); g.roundRect(x - ic / 2, y - ic / 2, ic, ic, ic * 0.24); g.fillStyle = `hsla(${(c * 47 + r * 90) % 360},70%,60%,0.85)`; g.fill();
  }
  g.restore();
  if (crease) { const cg = g.createLinearGradient(-6, 0, 6, 0); cg.addColorStop(0, 'rgba(255,255,255,0)'); cg.addColorStop(0.5, 'rgba(255,255,255,0.14)'); cg.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = cg; g.fillRect(-6, -h, 12, 2 * h); }
}
function shellTop(w, h) {
  g.beginPath(); g.roundRect(-w, -h, 2 * w, 2 * h, 9);
  const gr = g.createLinearGradient(-w, -h, w, h); gr.addColorStop(0, '#9aa6bd'); gr.addColorStop(0.5, '#e8eef8'); gr.addColorStop(1, '#7d899f');
  g.fillStyle = gr; g.fill();
  g.beginPath(); g.roundRect(-w + 4, -h + 4, 2 * w - 8, 2 * h - 8, 6); g.fillStyle = '#141a2c'; g.fill();
  g.strokeStyle = 'rgba(79,216,255,0.18)'; g.lineWidth = 0.8;
  for (let x = -w + 12; x < w - 8; x += 10) { g.beginPath(); g.moveTo(x, -h + 6); g.lineTo(x, h - 6); g.stroke(); }
  g.fillStyle = '#20283f'; g.fillRect(-3, -h + 4, 6, 2 * h - 8);
}
function batteryTop(w, h) {
  g.beginPath(); g.roundRect(-w, -h, 2 * w, 2 * h, 5);
  const gr = g.createLinearGradient(-w, 0, w, 0); gr.addColorStop(0, '#173b2a'); gr.addColorStop(0.5, '#2b6e4c'); gr.addColorStop(1, '#173b2a');
  g.fillStyle = gr; g.fill(); g.lineWidth = 1.2; g.strokeStyle = 'rgba(70,224,138,0.8)'; g.stroke();
  g.save(); g.translate(0, 0); bolt(0, 0, Math.min(w, h) * 0.9); g.fillStyle = YEL; g.fill(); g.restore();
  g.font = `${Math.min(w, h) * 0.32}px IB`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = 'rgba(255,255,255,0.75)';
  g.fillText('Li-ion', 0, h * 0.68);
}
function boardTop(w, h) {
  g.beginPath(); g.roundRect(-w, -h, 2 * w, 2 * h, 4); g.fillStyle = '#0d4a3e'; g.fill(); g.lineWidth = 1; g.strokeStyle = 'rgba(120,255,200,0.5)'; g.stroke();
  g.strokeStyle = 'rgba(255,216,77,0.45)'; g.lineWidth = 0.7;
  for (let i = 0; i < 12; i++) { const y = -h + 3 + i * (2 * h - 6) / 11; g.beginPath(); g.moveTo(-w + 3, y); g.lineTo(-w * 0.2, y); g.lineTo(-w * 0.1, y * 0.5); g.lineTo(w - 3, y * 0.5); g.stroke(); }
  for (let i = 0; i < 5; i++) { g.fillStyle = '#1b2234'; g.fillRect(w * 0.35 + (i % 3) * 7, -h * 0.6 + Math.floor(i / 3) * 9, 5, 6); }
}
function chipTop(w, h) {
  g.beginPath(); g.roundRect(-w, -h, 2 * w, 2 * h, 2); g.fillStyle = '#1a1f2e'; g.fill();
  g.beginPath(); g.roundRect(-w * 0.78, -h * 0.78, w * 1.56, h * 1.56, 1.5);
  const gr = g.createLinearGradient(-w, -h, w, h); gr.addColorStop(0, '#8a7a4a'); gr.addColorStop(0.5, '#f2d98a'); gr.addColorStop(1, '#8a7a4a'); g.fillStyle = gr; g.fill();
  g.font = `${w * 0.55}px IB`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#2a2414'; g.fillText('A20', 0, -h * 0.12);
  g.font = `${w * 0.32}px IB`; g.fillText('PRO', 0, h * 0.42);
}
function camTop(w, h) {
  g.beginPath(); g.arc(0, 0, w, 0, Math.PI * 2); g.fillStyle = '#2a3046'; g.fill();
  g.beginPath(); g.arc(0, 0, w * 0.72, 0, Math.PI * 2); const gr = g.createRadialGradient(-w * 0.2, -w * 0.2, 0, 0, 0, w * 0.72); gr.addColorStop(0, '#5b7cff'); gr.addColorStop(0.35, '#151a3a'); gr.addColorStop(1, '#05060c'); g.fillStyle = gr; g.fill();
  g.beginPath(); g.arc(-w * 0.22, -w * 0.22, w * 0.14, 0, Math.PI * 2); g.fillStyle = 'rgba(255,255,255,0.7)'; g.fill();
}
const dispTop = (w, h) => wallpaper(w, h, T, true);

// Teléfono abierto en capas (vista de despiece). e: separación 0..1; focus: pieza resaltada
const PARTS3 = [
  { k: 'shell', c: [0, 0, -0.035], a: 1.0, b: 0.707, t: 0.03, top: shellTop, lvl: 0 },
  { k: 'bat', c: [-0.5, -0.15, -0.005], a: 0.43, b: 0.47, t: 0.025, top: batteryTop, lvl: 1 },
  { k: 'bat', c: [0.5, -0.05, -0.005], a: 0.43, b: 0.57, t: 0.025, top: batteryTop, lvl: 1 },
  { k: 'board', c: [-0.5, 0.52, -0.005], a: 0.45, b: 0.14, t: 0.012, top: boardTop, lvl: 2 },
  { k: 'chip', c: [-0.42, 0.52, 0.004], a: 0.07, b: 0.07, t: 0.01, top: chipTop, lvl: 2 },
  { k: 'cam', c: [-0.82, 0.52, 0.005], a: 0.055, b: 0.055, t: 0.015, top: camTop, lvl: 2 },
  { k: 'cam', c: [-0.68, 0.52, 0.005], a: 0.055, b: 0.055, t: 0.015, top: camTop, lvl: 2 },
  { k: 'disp', c: [0, 0, 0.012], a: 1.0, b: 0.707, t: 0.012, top: dispTop, lvl: 3 },
];
const GAP = 0.42;
function partPos(p, e, focus, fa) {
  let z = p.c[2] + e * GAP * p.lvl;
  const isF = focus && (p.k === focus || (focus === 'board' && p.k === 'chip') || (focus === 'chip' && p.k === 'board'));
  if (isF) z += fa * 0.22;
  return { pos: [p.c[0], p.c[1], z], isF };
}
function exploded(e, focus = null, fa = 0) {
  const list = PARTS3.map(p => { const r = partPos(p, e, focus, fa); return { p, ...r, d: P3(...r.pos)[2] + p.lvl * 1e-3 }; });
  list.sort((u, v) => (u.p.lvl - v.p.lvl) || (u.d - v.d));
  for (const it of list) {
    const al = focus ? (it.isF ? 1 : 1 - 0.72 * fa) : 1;
    const side = it.p.k === 'bat' ? '#173b2a' : it.p.k === 'board' ? '#0a3a30' : it.p.k === 'disp' ? '#202638' : it.p.k === 'chip' ? '#3a3a3a' : it.p.k === 'cam' ? '#2a3046' : '#9aa6bd';
    slab(it.pos, X3, Y3, Z3, it.p.a, it.p.b, it.p.t, it.p.top, null, side, al, it.isF ? fa : 0);
  }
}
function partAnchor(k, e, focus, fa) { const p = PARTS3.find(q => q.k === k); return partPos(p, e, focus, fa).pos; }

// Teléfono plegable entero: phi = 0 abierto, PI cerrado
function foldPhone(phi, t, outerFn = null) {
  const th = 0.04, b = 0.707;
  const L = { C: [-0.5, 0, 0], A: X3, N: Z3 };
  const Ar = [Math.cos(phi), 0, Math.sin(phi)], Nr = [-Math.sin(phi), 0, Math.cos(phi)];
  const R = { C: v3([0, 0, 0], Ar, 0.5), A: Ar, N: Nr };
  const innerL = (w, h) => { g.save(); g.beginPath(); g.rect(-w, -h, 2 * w, 2 * h); g.clip(); g.translate(w, 0); wallpaper(2 * w, h, t, true); g.restore(); };
  const innerR = (w, h) => { g.save(); g.beginPath(); g.rect(-w, -h, 2 * w, 2 * h); g.clip(); g.translate(-w, 0); wallpaper(2 * w, h, t, true); g.restore(); };
  const backL = (w, h) => { g.beginPath(); g.roundRect(-w, -h, 2 * w, 2 * h, 9); const gr = g.createLinearGradient(-w, -h, w, h); gr.addColorStop(0, '#d9dfe9'); gr.addColorStop(1, '#8e9ab0'); g.fillStyle = gr; g.fill(); };
  const outer = outerFn || ((w, h) => { g.beginPath(); g.roundRect(-w, -h, 2 * w, 2 * h, 10); g.fillStyle = '#c4ccda'; g.fill(); g.save(); g.translate(0, 0); g.scale(-1, 1); wallpaper(w - 4, h - 4, t, false); g.restore(); });
  const halves = [{ ...L, top: innerL, bot: backL }, { ...R, top: innerR, bot: outer }];
  halves.sort((u, v) => P3(...u.C)[2] - P3(...v.C)[2]);
  if (phi > Math.PI / 2) halves.sort((u, v) => (u === halves.find(h => h.A === X3) ? -1 : 1));
  for (const hf of halves) slab(hf.C, hf.A, Y3, hf.N, 0.5, b, th, hf.top, hf.bot, '#b7c0d0');
}

// =====================================================================
// GANCHO A: miles de millones de interruptores (zoom hacia afuera)
// =====================================================================
function sceneSwitches(t) {
  drawBG(t, 0.4);
  const u = ease(prog(t, 0.4, G0[1] + 0.2));
  const cell = 150 * Math.pow(6 / 150, u);           // tamaño de cada interruptor en px
  const cx = 540, cy = 930;
  const n = Math.ceil(560 / cell) + 1;
  const step = Math.floor(t * 9);
  g.save();
  g.beginPath(); g.rect(0, 470, W, 1000); g.clip();
  for (let i = -n; i <= n; i++) for (let j = -n; j <= n; j++) {
    const x = cx + i * cell, y = cy + j * cell;
    if (x < -cell || x > W + cell || y < 440 || y > 1500) continue;
    const on = hash(i, j, step + ((i * 7 + j * 3) & 3)) > 0.5;
    g.fillStyle = on ? YEL : '#1a2850';
    const m = Math.max(0.6, cell * 0.12);
    g.fillRect(x - cell / 2 + m, y - cell / 2 + m, cell - 2 * m, cell - 2 * m);
    if (cell > 50) { g.font = `${cell * 0.5}px IB`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = on ? INK : 'rgba(79,216,255,0.6)'; g.fillText(on ? '1' : '0', x, y + cell * 0.03); }
  }
  g.restore();
  // contorno del chip al final
  const ca = ease(prog(t, G0[1] - 1.6, G0[1] - 0.4));
  if (ca > 0) { g.save(); g.globalAlpha = ca; g.lineWidth = 8; g.strokeStyle = CYA; g.shadowColor = CYA; g.shadowBlur = 30; g.strokeRect(540 - 330, 930 - 330, 660, 660); g.restore(); tag('UN SOLO CHIP', 540, 1330, CYA, 44, ca); }
  label(t, 0.25, G0[1] + 0.15, 'MILES DE MILLONES', ['de interruptores: 1 = prendido · 0 = apagado'], YEL, 96);
}

// =====================================================================
// GANCHO B: el teléfono se abre y se desarma
// =====================================================================
const UNF0 = G1[0] + 0.7, UNF1 = G1[0] + 2.0, EXP0 = G1[0] + 2.4, EXP1 = G1[0] + 3.9;
function viewOpen(t, k) {          // cámara de despiece (vista de mesa)
  CAM.yaw = lerp(0.18 * Math.sin(t * 0.6), -0.32 + 0.1 * Math.sin(t * 0.35), k);
  CAM.pitch = lerp(0.12, -0.95, k);
  CAM.s = lerp(330, 380, k); CAM.cx = 540 - CAM.s * Math.sin(CAM.yaw) * GAP * 1.5 * k; CAM.cy = lerp(960, 1180, k);
}
function scenePhoneIntro(t) {
  drawBG(t, 0.6);
  if (t < EXP0) {
    const f = ease(prog(t, UNF0, UNF1)), phi = Math.PI * (1 - f);
    CAM.yaw = 0.18 * Math.sin(t * 0.6) + 0.35 * (1 - f) * Math.sin(t * 1.1); CAM.pitch = 0.12;
    CAM.s = lerp(440, 330, f); CAM.cx = 540 + 0.5 * CAM.s * (1 - f); CAM.cy = 960;
    const pop = backOut(prog(t, G1[0] - 0.25, G1[0] + 0.35)); CAM.s *= pop;
    foldPhone(phi, t);
    if (f > 0.3) { const c = P3(0, -0.707, 0); tag('SE DESDOBLA', c[0], c[1] + 70, YEL, 40, ease(prog(t, UNF0 + 0.5, UNF0 + 0.9)) * (1 - prog(t, EXP0 - 0.3, EXP0))); }
  } else {
    const k = ease(prog(t, EXP0, EXP1));
    viewOpen(t, k);
    exploded(k);
    const la = ease(prog(t, EXP1 - 0.2, EXP1 + 0.3));
    tag3(partAnchor('disp', k), 'PANTALLA', CYA, la, 34, 300, -40);
    tag3(partAnchor('board', k), 'CHIP', YEL, la, 34, -150, -60);
    tag3(partAnchor('bat', k), 'BATERÍAS', GRN, la, 34, 320, 10);
    tag3(PARTS3[0].c, 'CUERPO DE TITANIO', TI, la, 32, 0, 120);
  }
  flushTags();
  label(t, G1[0] - 0.2, G1[1] + 0.2, 'iPHONE DUO', ['el primer iPhone que se dobla'], WHT, 112);
}

// =====================================================================
// Toma de despiece con una pieza resaltada
// =====================================================================
function sceneFocus(t, a, focus, num, title, subs, tags = []) {
  drawBG(t, 0.6);
  viewOpen(t, 1);
  const fa = ease(prog(t, a, a + 0.6));
  exploded(1, focus, fa);
  for (const tg of tags) tag3(tg.p, tg.text, tg.col, fa * ease(prog(t, a + (tg.d || 0.4), a + (tg.d || 0.4) + 0.4)), tg.size || 36, tg.dx || 0, tg.dy || 0);
  flushTags();
  label(t, a - 0.25, 1e9, title, subs, WHT, 104, num);
}

// =====================================================================
// BATERÍA por dentro: iones de litio
// =====================================================================
function sceneBattery(t) {
  drawBG(t, 0.5);
  const a = B1[0], b = B1[1];
  const use = t < at(B1, 0.6);   // primero se usa, luego se carga
  const cx = 540, cy = 1010, w = 820, h = 470;
  const x0 = cx - w / 2, y0 = cy - h / 2;
  // cuerpo de la celda
  g.save();
  g.beginPath(); g.roundRect(x0 - 14, y0 - 14, w + 28, h + 28, 34); g.fillStyle = '#1d2a44'; g.fill(); g.lineWidth = 5; g.strokeStyle = 'rgba(200,215,240,0.7)'; g.stroke();
  g.beginPath(); g.roundRect(x0, y0, w, h, 24); g.fillStyle = 'rgba(79,216,255,0.14)'; g.fill();
  // ánodo (grafito) y cátodo
  const ew = 150;
  for (let i = 0; i < 9; i++) { g.fillStyle = i % 2 ? '#3b4256' : '#2a3042'; g.fillRect(x0 + 10, y0 + 12 + i * (h - 24) / 9, ew, (h - 24) / 9 - 4); }
  for (let i = 0; i < 9; i++) { g.fillStyle = i % 2 ? '#7a4b2e' : '#5c3a26'; g.fillRect(x0 + w - 10 - ew, y0 + 12 + i * (h - 24) / 9, ew, (h - 24) / 9 - 4); }
  g.setLineDash([16, 12]); g.strokeStyle = 'rgba(255,255,255,0.45)'; g.lineWidth = 4; line(cx, y0 + 16, cx, y0 + h - 16); g.setLineDash([]);
  g.restore();
  txt('−', x0 + 10 + ew / 2, y0 - 70, 90, WHT, { stroke: 7 });
  txt('+', x0 + w - 10 - ew / 2, y0 - 70, 90, WHT, { stroke: 7 });
  txt('GRAFITO', x0 + 10 + ew / 2, y0 + h + 52, 38, TI, { font: 'IX', stroke: 5 });
  txt('ÓXIDO METÁLICO', x0 + w - 10 - ew / 2, y0 + h + 52, 38, TI, { font: 'IX', stroke: 5 });
  // circuito exterior arriba
  const wy = y0 - 150;
  g.save(); g.lineWidth = 12; g.strokeStyle = '#c9d3e6'; g.lineJoin = 'round';
  g.beginPath(); g.moveTo(x0 + 85, y0 - 14); g.lineTo(x0 + 85, wy); g.lineTo(x0 + w - 85, wy); g.lineTo(x0 + w - 85, y0 - 14); g.stroke(); g.restore();
  // foco o enchufe en medio del cable
  if (use) {
    const glow = 0.6 + 0.4 * Math.sin(t * 12);
    g.save(); g.shadowColor = YEL; g.shadowBlur = 50 * glow; circle(cx, wy, 52); g.fillStyle = YEL; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke(); g.restore();
    bolt(cx, wy, 60); g.fillStyle = INK; g.fill();
  } else {
    g.save(); g.beginPath(); g.roundRect(cx - 70, wy - 50, 140, 100, 22); g.fillStyle = '#2a3350'; g.fill(); g.lineWidth = 6; g.strokeStyle = CYA; g.stroke();
    g.fillStyle = CYA; g.fillRect(cx - 30, wy - 18, 14, 36); g.fillRect(cx + 16, wy - 18, 14, 36); g.restore();
  }
  // electrones por el cable
  const dir = use ? 1 : -1;
  const pathLen = (wy < 0 ? 0 : 1) * 0 + (y0 - 14 - wy) * 2 + (w - 170);
  for (let i = 0; i < 12; i++) {
    let s = ((i / 12 + dir * t * 0.35) % 1 + 1) % 1; let d = s * pathLen; let px, py;
    const up = y0 - 14 - wy;
    if (d < up) { px = x0 + 85; py = y0 - 14 - d; } else if (d < up + w - 170) { px = x0 + 85 + (d - up); py = wy; } else { px = x0 + w - 85; py = wy + (d - up - (w - 170)); }
    circle(px, py, 11); g.fillStyle = CYA; g.fill();
  }
  // iones de litio
  const loc = t < at(B1, 0.6) ? ease(prog(t, a + 0.3, at(B1, 0.55))) : 1 - ease(prog(t, at(B1, 0.62), b - 0.3));
  for (let i = 0; i < 16; i++) {
    const ry = y0 + 45 + (i % 8) * (h - 90) / 7 + (i >= 8 ? 18 : 0);
    const xa = x0 + 30 + (i >= 8 ? 70 : 20), xb = x0 + w - 160 + (i >= 8 ? 70 : 20);
    const stag = clamp(loc * 1.5 - (i / 16) * 0.5);
    const x = lerp(xa, xb, ease(stag)) + Math.sin(t * 5 + i) * 4;
    circle(x, ry, 20); g.fillStyle = YEL; g.fill(); g.lineWidth = 3; g.strokeStyle = INK; g.stroke();
    g.font = '20px IB'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = INK; g.fillText('Li', x, ry + 1);
  }
  const ua = fade(t, a + 0.1, at(B1, 0.58), 0.25), ca = fade(t, at(B1, 0.6), b + 0.6, 0.25);
  tag('USANDO → SUELTA ELECTRICIDAD', 540, y0 + h + 140, YEL, 40, ua);
  tag('CARGANDO → LOS IONES REGRESAN', 540, y0 + h + 140, CYA, 40, ca);
  label(t, a - 0.3, 1e9, 'IONES DE LITIO', ['viajan de un lado al otro'], YEL, 104);
}

// =====================================================================
// CHIP: A20 Pro de 2 nm y transistores
// =====================================================================
function sceneChipZoom(t) {
  drawBG(t, 0.5);
  const a = C0[0];
  const z = backOut(prog(t, a + 1.4, a + 2.1));
  g.save(); g.translate(540, 1000); g.scale(z, z);
  g.save(); g.shadowColor = YEL; g.shadowBlur = 60; g.beginPath(); g.roundRect(-300, -300, 600, 600, 30); g.fillStyle = '#151a28'; g.fill(); g.restore();
  for (let i = 0; i < 24; i++) for (const sgn of [-1, 1]) { g.fillStyle = '#c9a85a'; g.fillRect(-276 + i * 23.5, sgn * 306 - 6, 12, 12); g.fillRect(sgn * 306 - 6, -276 + i * 23.5, 12, 12); }
  const gr = g.createLinearGradient(-230, -230, 230, 230); gr.addColorStop(0, '#7c6a3c'); gr.addColorStop(0.5, '#f4dc90'); gr.addColorStop(1, '#7c6a3c');
  g.beginPath(); g.roundRect(-230, -230, 460, 460, 14); g.fillStyle = gr; g.fill();
  // zonas internas (núcleos) con brillo
  const zones = [[-200, -200, 190, 150, 'CPU'], [10, -200, 190, 150, 'GPU'], [-200, -30, 400, 110, 'MOTOR NEURONAL'], [-200, 100, 190, 100, 'MEMORIA'], [10, 100, 190, 100, 'IMAGEN']];
  zones.forEach(([x, y, w, h, n], i) => {
    const pulse = 0.25 + 0.25 * Math.sin(t * 6 + i * 1.3);
    g.fillStyle = `rgba(20,24,40,${0.55 + pulse * 0.3})`; g.fillRect(x, y, w, h);
    g.font = '30px IX'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = 'rgba(255,216,77,0.9)'; g.fillText(n, x + w / 2, y + h / 2);
  });
  g.restore();
  tag('A20 PRO', 540, 1000 - 380 * z, YEL, 52, ease(prog(t, a + 1.9, a + 2.3)));
  tag('2 NANÓMETROS', 540, 1000 + 380 * z, CYA, 50, ease(prog(t, at(C0, 0.7), at(C0, 0.7) + 0.4)));
  label(t, a - 0.2, 1e9, 'EL CEREBRO', ['el chip A20 Pro'], WHT, 104, 2);
}
function sceneTransistor(t) {
  drawBG(t, 0.5);
  const a = C1[0], b = C1[1];
  const on = Math.floor(t * 2.4) % 2 === 0;
  // transistor: fuente y drenador con canal y compuerta
  const cy = 860;
  g.save();
  g.fillStyle = '#26314f'; g.beginPath(); g.roundRect(150, cy - 40, 780, 220, 26); g.fill();
  g.fillStyle = '#3c4a74'; g.fillRect(170, cy + 20, 170, 140); g.fillRect(740, cy + 20, 170, 140);
  g.fillStyle = on ? 'rgba(79,216,255,0.55)' : 'rgba(79,216,255,0.08)'; g.fillRect(340, cy + 60, 400, 60);
  g.fillStyle = on ? YEL : '#5a5f70'; g.beginPath(); g.roundRect(360, cy - 110, 360, 70, 14); g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
  g.restore();
  txt('COMPUERTA', 540, cy - 75, 34, on ? INK : WHT, { font: 'IX', stroke: on ? 0 : 5 });
  txt('ENTRADA', 255, cy + 210, 30, TI, { font: 'IX', stroke: 4 }); txt('SALIDA', 825, cy + 210, 30, TI, { font: 'IX', stroke: 4 });
  if (on) for (let i = 0; i < 9; i++) { const x = 200 + ((i / 9 + t * 0.9) % 1) * 680; circle(x, cy + 90, 13); g.fillStyle = CYA; g.fill(); }
  else for (let i = 0; i < 4; i++) { circle(215 + i * 32, cy + 90, 13); g.fillStyle = CYA; g.fill(); }
  txt(on ? '1' : '0', 540, cy + 300, 170, on ? YEL : CYA, { stroke: 12 });
  tag(on ? 'PRENDIDO' : 'APAGADO', 540, cy + 410, on ? YEL : CYA, 40, 1);
  // río de unos y ceros abajo / arriba
  const ba = ease(prog(t, at(C1, 0.62), at(C1, 0.72)));
  if (ba > 0) {
    g.save(); g.globalAlpha = ba; g.font = '44px IB'; g.textAlign = 'center'; g.textBaseline = 'middle';
    for (let r = 0; r < 3; r++) for (let c = 0; c < 16; c++) {
      const x = ((c * 72 + t * (180 + r * 60)) % (16 * 72)) - 40, y = 1435 + (r - 1) * 50;
      const v = hash(c, r, Math.floor(t * 6)) > 0.5; g.fillStyle = v ? YEL : 'rgba(79,216,255,0.75)'; g.fillText(v ? '1' : '0', x, y);
    }
    g.restore();
  }
  label(t, a - 0.3, 1e9, 'TRANSISTORES', ['miles de millones de veces por segundo'], WHT, 100);
}

// =====================================================================
// PANTALLAS: 5.4" afuera y 7.6" adentro
// =====================================================================
const SC_IN = at(S0, 0.52);   // empieza a abrirse
function diagonal(p0, p1, text, col, a) {
  if (a <= 0) return;
  const q0 = P3(...p0), q1 = P3(...p1);
  const qx = lerp(q0[0], q1[0], a), qy = lerp(q0[1], q1[1], a);
  g.save(); g.lineWidth = 7; g.strokeStyle = col; g.setLineDash([22, 14]); line(q0[0], q0[1], qx, qy); g.setLineDash([]);
  circle(q0[0], q0[1], 12); g.fillStyle = col; g.fill(); if (a > 0.98) { circle(q1[0], q1[1], 12); g.fill(); } g.restore();
  if (a > 0.6) tag(text, (q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2, col, 56, ease((a - 0.6) / 0.4));
}
function sceneScreens(t) {
  drawBG(t, 0.6);
  const f = ease(prog(t, SC_IN, SC_IN + 1.3));
  const wob = 0.35 * Math.sin(Math.PI * prog(t, at(S0, 0.86), at(S0, 0.99)));
  const phi = Math.PI * (1 - f) + wob;
  CAM.yaw = 0.16 * Math.sin(t * 0.5) + 0.1; CAM.pitch = 0.1;
  CAM.s = lerp(450, 345, f); CAM.cx = 540 + 0.5 * CAM.s * (1 - f) * Math.cos(CAM.yaw); CAM.cy = 990;
  foldPhone(phi, t);
  if (f < 0.05) diagonal([-0.95, -0.66, 0.045], [-0.05, 0.66, 0.045], '5.4″', YEL, ease(prog(t, at(S0, 0.22), at(S0, 0.36))) * (1 - prog(t, SC_IN - 0.2, SC_IN)));
  if (f > 0.97) diagonal([-0.95, -0.66, 0.01], [0.95, 0.66, 0.01], '7.6″', CYA, ease(prog(t, SC_IN + 1.35, SC_IN + 2.0)));
  label(t, S0[0] - 0.25, 1e9, 'LAS PANTALLAS', [f < 0.5 ? 'una por fuera…' : '…y otra por dentro, que se dobla'], WHT, 104, 3);
}
function scenePixels(t) {
  drawBG(t, 0.4);
  const a = S1[0], b = S1[1], mid = at(S1, 0.56);
  if (t < mid + 0.3) {
    const al = 1 - prog(t, mid, mid + 0.3);
    g.save(); g.globalAlpha = al;
    const z = lerp(1, 1.25, prog(t, a, mid));
    const P = 92 * z, cols = Math.ceil(W / P) + 1;
    for (let i = 0; i < cols; i++) for (let j = 0; j < 11; j++) {
      const x = 540 + (i - cols / 2) * P, y = 980 + (j - 5) * P;
      if (y < 500 || y > 1470) continue;
      const hue = (i * 18 + j * 11 + t * 70) % 360;
      const r = 0.5 + 0.5 * Math.sin(hue * Math.PI / 180), gg = 0.5 + 0.5 * Math.sin((hue + 120) * Math.PI / 180), bb = 0.5 + 0.5 * Math.sin((hue + 240) * Math.PI / 180);
      g.fillStyle = '#05060c'; g.fillRect(x - P / 2, y - P / 2, P, P);
      const sw = P * 0.26;
      [[r, '255,60,70'], [gg, '60,255,120'], [bb, '70,130,255']].forEach(([v, c], k) => {
        g.save(); g.shadowColor = `rgba(${c},${v})`; g.shadowBlur = 18 * v;
        g.fillStyle = `rgba(${c},${0.15 + 0.85 * v})`; g.beginPath(); g.roundRect(x - P / 2 + P * 0.08 + k * (sw + P * 0.04), y - P * 0.4, sw, P * 0.8, sw * 0.4); g.fill(); g.restore();
      });
    }
    g.restore();
    const ta = ease(prog(t, at(S1, 0.18), at(S1, 0.26))) * al;
    tag('ROJO', 300, 1430, '#ff5a64', 40, ta); tag('VERDE', 540, 1430, GRN, 40, ta); tag('AZUL', 780, 1430, '#6aa5ff', 40, ta);
    tag('BRILLAN SOLAS', 540, 560, YEL, 46, ease(prog(t, at(S1, 0.36), at(S1, 0.44))) * al);
  }
  if (t > mid) {
    const al = ease(prog(t, mid, mid + 0.35));
    g.save(); g.globalAlpha = al; g.translate(540, 1010); g.scale(1.32, 1.32); g.translate(-540, -820);
    // LCD: con lámpara detrás (gruesa, no se dobla)
    const ly = 720;
    const layers = [['FILTROS DE COLOR', '#3a4870'], ['CRISTAL LÍQUIDO', '#2c5a7a'], ['LÁMPARA', '#c9b25a']];
    layers.forEach(([n, c], i) => { g.fillStyle = c; g.beginPath(); g.roundRect(120, ly + i * 62, 380, 52, 10); g.fill(); g.font = '24px IX'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = WHT; g.fillText(n, 310, ly + i * 62 + 27); });
    txt('LCD', 310, ly - 60, 64, TI, { stroke: 6 });
    const xa = ease(prog(t, mid + 0.6, mid + 1.0));
    if (xa > 0) { g.save(); g.globalAlpha = al * xa; g.lineWidth = 16; g.strokeStyle = RED; g.lineCap = 'round'; line(140, ly - 10, 480, ly + 190); line(480, ly - 10, 140, ly + 190); g.restore(); }
    // OLED: una sola lámina delgada que se dobla
    const bend = ease(prog(t, at(S1, 0.78), b - 0.2));
    txt('OLED', 770, ly - 60, 64, YEL, { stroke: 6 });
    g.save(); g.translate(770, ly + 90);
    const L = 380, R = L / (Math.PI * Math.max(bend, 0.001));
    g.lineWidth = 26; g.lineCap = 'round';
    const grad = g.createLinearGradient(-190, 0, 190, 0); grad.addColorStop(0, '#ff5a64'); grad.addColorStop(0.5, GRN); grad.addColorStop(1, '#6aa5ff');
    g.strokeStyle = grad; g.shadowColor = YEL; g.shadowBlur = 25;
    g.beginPath();
    if (bend < 0.01) { g.moveTo(-190, 0); g.lineTo(190, 0); }
    else { const ang = Math.PI * bend; g.arc(0, -R, R, Math.PI / 2 + ang / 2, Math.PI / 2 - ang / 2, true); }
    g.stroke(); g.restore();
    tag('SIN LÁMPARA', 770, ly + 240, CYA, 40, ease(prog(t, mid + 0.5, mid + 0.9)));
    tag('¡SE DOBLA!', 770, ly + 330, YEL, 48, ease(prog(t, at(S1, 0.82), at(S1, 0.9))));
    g.restore();
  }
  label(t, a - 0.3, 1e9, 'PANTALLA OLED', [t < mid ? 'cada punto: rojo, verde y azul' : 'por eso se puede doblar'], WHT, 104);
}

// =====================================================================
// CÁMARAS: 48 MP y la cámara bajo la pantalla
// =====================================================================
function sceneSensor(t) {
  drawBG(t, 0.5);
  const a = K0[0], b = K0[1], m = at(K0, 0.36);
  if (t < m + 0.3) {
    const al = 1 - prog(t, m, m + 0.3);
    const z = backOut(prog(t, a - 0.1, a + 0.5));
    g.save(); g.globalAlpha = al; g.translate(540, 990); g.scale(z, z);
    g.beginPath(); g.roundRect(-300, -420, 600, 840, 70); const gr = g.createLinearGradient(-300, -420, 300, 420); gr.addColorStop(0, '#dde3ee'); gr.addColorStop(1, '#8d98ad'); g.fillStyle = gr; g.fill();
    g.beginPath(); g.roundRect(-260, -380, 260, 380, 60); g.fillStyle = 'rgba(40,48,70,0.25)'; g.fill();
    for (const [x, y] of [[-130, -280], [-130, -100]]) { g.save(); g.translate(x, y); g.scale(1.25, 1.25); camTop(62, 62); g.restore(); }
    g.restore();
    tag('48 MP', 540 + 40 * z, 990 - 300 * z, YEL, 44, ease(prog(t, at(K0, 0.18), at(K0, 0.24))) * al);
    tag('48 MP', 540 + 40 * z, 990 - 120 * z, YEL, 44, ease(prog(t, at(K0, 0.22), at(K0, 0.28))) * al);
    tag('PRINCIPAL', 540 + 60 * z, 990 - 240 * z, WHT, 28, ease(prog(t, at(K0, 0.24), at(K0, 0.3))) * al);
    tag('ULTRA GRAN ANGULAR', 540 + 120 * z, 990 - 60 * z, WHT, 28, ease(prog(t, at(K0, 0.26), at(K0, 0.32))) * al);
  }
  if (t > m) {
    const al = ease(prog(t, m, m + 0.35));
    g.save(); g.globalAlpha = al;
    // lente arriba, sensor abajo
    const lx = 540, ly = 640, sy = 1170;
    g.save(); g.beginPath(); g.ellipse(lx, ly, 230, 46, 0, 0, Math.PI * 2); const lg = g.createLinearGradient(lx - 230, 0, lx + 230, 0); lg.addColorStop(0, 'rgba(120,170,255,0.4)'); lg.addColorStop(0.5, 'rgba(200,230,255,0.85)'); lg.addColorStop(1, 'rgba(120,170,255,0.4)'); g.fillStyle = lg; g.fill(); g.lineWidth = 4; g.strokeStyle = WHT; g.stroke(); g.restore();
    txt('LENTE', lx + 330, ly, 36, TI, { font: 'IX', stroke: 5 });
    // rayos de luz
    for (let i = 0; i < 7; i++) {
      const x0 = lx - 210 + i * 70, xs = lx + (i - 3) * 95;
      g.strokeStyle = 'rgba(255,216,77,0.35)'; g.lineWidth = 5; line(x0, 470, x0, ly); line(x0, ly, xs, sy - 70);
      const ph = (t * 0.9 + i * 0.13) % 1;
      const px = ph < 0.4 ? x0 : lerp(x0, xs, (ph - 0.4) / 0.6), py = ph < 0.4 ? lerp(470, ly, ph / 0.4) : lerp(ly, sy - 70, (ph - 0.4) / 0.6);
      circle(px, py, 12); g.fillStyle = YEL; g.fill();
    }
    // sensor: cuadrícula de fotodiodos
    const cols = 14, rows = 5, cw = 54, x0 = 540 - cols * cw / 2, y0 = sy - 60;
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
      const hit = hash(i, j, Math.floor(t * 5)) > 0.62;
      g.fillStyle = hit ? YEL : '#223055'; g.fillRect(x0 + i * cw + 3, y0 + j * cw * 0.55 + 3, cw - 6, cw * 0.55 - 6);
    }
    txt('SENSOR', 540, y0 + rows * cw * 0.55 + 46, 36, TI, { font: 'IX', stroke: 5 });
    // electrones que salen
    for (let i = 0; i < 10; i++) { const ph = (t * 1.2 + i / 10) % 1; const x = x0 + ((i * 97) % (cols * cw)); circle(x, y0 + rows * cw * 0.55 + 90 + ph * 140, 10); g.fillStyle = CYA; g.globalAlpha = al * (1 - ph); g.fill(); g.globalAlpha = al; }
    g.restore();
    const cnt = Math.round(48e6 * ease(prog(t, at(K0, 0.42), at(K0, 0.7))));
    const ca = ease(prog(t, at(K0, 0.4), at(K0, 0.46)));
    if (ca > 0) txt(cnt.toLocaleString('en-US') + ' PUNTITOS', 540, 1520 - 75, 56, YEL, { stroke: 7, alpha: ca, maxW: 960 });
    tag('LUZ → ELECTRICIDAD', 540, 520, CYA, 44, ease(prog(t, at(K0, 0.8), at(K0, 0.86))));
  }
  label(t, a - 0.25, 1e9, 'LAS CÁMARAS', [t < m ? 'atrás hay dos' : '48 millones de puntitos'], WHT, 104, 4);
}
function sceneHiddenCam(t) {
  drawBG(t, 0.6);
  const a = K1[0], b = K1[1];
  CAM.yaw = 0.12 * Math.sin(t * 0.5); CAM.pitch = 0.08; CAM.s = 470; CAM.cx = 540; CAM.cy = 1000;
  foldPhone(0, t);
  // lupa de "rayos X" que descubre la cámara
  const tgt = P3(0.5, 0.56, 0.01);
  const u = ease(prog(t, a + 0.4, at(K1, 0.55)));
  const mx = lerp(220, tgt[0], u), my = lerp(1250, tgt[1], u), R = 120;
  g.save(); circle(mx, my, R); g.clip();
  g.fillStyle = '#0b1328'; g.fillRect(mx - R, my - R, 2 * R, 2 * R);
  g.strokeStyle = 'rgba(79,216,255,0.35)'; g.lineWidth = 2; for (let k = -R; k < R; k += 16) { line(mx + k, my - R, mx + k, my + R); line(mx - R, my + k, mx + R, my + k); }
  g.translate(tgt[0], tgt[1]); camTop(34, 34);
  g.restore();
  g.save(); circle(mx, my, R); g.lineWidth = 10; g.strokeStyle = CYA; g.shadowColor = CYA; g.shadowBlur = 30; g.stroke(); g.restore();
  g.save(); g.lineWidth = 16; g.lineCap = 'round'; g.strokeStyle = CYA; line(mx + R * 0.72, my + R * 0.72, mx + R * 1.25, my + R * 1.25); g.restore();
  tag('CÁMARA ESCONDIDA', tgt[0], tgt[1] - 175, YEL, 42, ease(prog(t, at(K1, 0.55), at(K1, 0.65))));
  tag('DEBAJO DE LA PANTALLA', 540, 1440, CYA, 40, ease(prog(t, at(K1, 0.62), at(K1, 0.72))));
  label(t, a - 0.2, 1e9, 'CÁMARA OCULTA', ['por dentro, bajo la pantalla'], WHT, 104);
}

// =====================================================================
// CARGA: con cable y sin cable
// =====================================================================
function battIcon(x, y, w, h, level, col) {
  g.save(); g.beginPath(); g.roundRect(x - w / 2, y - h / 2, w, h, h * 0.22); g.lineWidth = 10; g.strokeStyle = WHT; g.stroke();
  g.fillStyle = WHT; g.fillRect(x + w / 2 + 4, y - h * 0.2, 16, h * 0.4);
  g.fillStyle = col; g.beginPath(); g.roundRect(x - w / 2 + 14, y - h / 2 + 14, (w - 28) * clamp(level), h - 28, h * 0.12); g.fill(); g.restore();
}
function sceneCable(t) {
  drawBG(t, 0.6);
  const a = Q0[0], b = Q0[1];
  // teléfono cerrado de frente
  g.save(); g.translate(540, 900);
  g.beginPath(); g.roundRect(-230, -330, 460, 660, 56); const gr = g.createLinearGradient(-230, 0, 230, 0); gr.addColorStop(0, '#8e9ab0'); gr.addColorStop(0.5, '#e6ebf3'); gr.addColorStop(1, '#8e9ab0'); g.fillStyle = gr; g.fill();
  g.beginPath(); g.roundRect(-212, -312, 424, 624, 44); g.fillStyle = '#05060c'; g.fill();
  g.restore();
  const lvl = 0.5 * ease(prog(t, at(Q0, 0.45), b - 0.1));
  battIcon(540, 860, 260, 120, Math.max(0.04, lvl), lvl > 0.2 ? GRN : RED);
  txt(Math.round(lvl * 100) + ' %', 540, 1010, 96, WHT, { stroke: 7 });
  // cable USB-C que sube
  const pin = ease(prog(t, a + 0.3, at(Q0, 0.3)));
  const py = lerp(1600, 1262, pin);
  g.save(); g.fillStyle = '#d9dfe9'; g.beginPath(); g.roundRect(500, py, 80, 120, 14); g.fill(); g.fillStyle = '#9aa3b5'; g.fillRect(515, py - 30, 50, 34); g.fillStyle = '#2a3046'; g.fillRect(530, py + 120, 20, 260); g.restore();
  if (pin > 0.99) { const pz = 0.5 + 0.5 * Math.sin(t * 10); g.save(); g.globalAlpha = pz; bolt(540, 760, 90); g.fillStyle = YEL; g.fill(); g.restore(); }
  // reloj de minutos
  const mins = Math.round(20 * ease(prog(t, at(Q0, 0.45), b - 0.1)));
  const ca = ease(prog(t, at(Q0, 0.45), at(Q0, 0.55)));
  if (ca > 0) {
    g.save(); g.globalAlpha = ca; g.translate(880, 640);
    circle(0, 0, 92); g.fillStyle = '#16213f'; g.fill(); g.lineWidth = 8; g.strokeStyle = CYA; g.stroke();
    g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, 80, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * mins / 60); g.closePath(); g.fillStyle = 'rgba(79,216,255,0.45)'; g.fill();
    g.restore();
    txt(mins + ' MIN', 880, 770, 50, CYA, { stroke: 6, alpha: ca });
  }
  tag('≈ 50 % EN 20 MINUTOS', 540, 1460, YEL, 44, ease(prog(t, b - 0.9, b - 0.5)));
  label(t, a - 0.25, 1e9, 'LA CARGA', ['con cable'], WHT, 104, 5);
}
function coil(cx, cy, rx, ry, n, t, dir, col) {
  for (let i = 0; i < n; i++) {
    const k = 1 - i * 0.16;
    g.save(); g.beginPath(); g.ellipse(cx, cy, rx * k, ry * k, 0, 0, Math.PI * 2); g.lineWidth = 12; g.strokeStyle = COP; g.stroke(); g.lineWidth = 3; g.strokeStyle = 'rgba(255,230,190,0.6)'; g.stroke(); g.restore();
    for (let j = 0; j < 3; j++) { const ang = dir * t * 2.2 + j * 2.09 + i; circle(cx + Math.cos(ang) * rx * k, cy + Math.sin(ang) * ry * k, 9); g.fillStyle = col; g.fill(); }
  }
}
function sceneWireless(t) {
  drawBG(t, 0.5);
  const a = Q1[0], b = Q1[1];
  const by = 1260, py = 760;
  // base del cargador
  g.save(); g.beginPath(); g.ellipse(540, by + 40, 330, 80, 0, 0, Math.PI * 2); g.fillStyle = '#1b2236'; g.fill();
  g.beginPath(); g.ellipse(540, by, 330, 80, 0, 0, Math.PI * 2); g.fillStyle = '#d9dfe9'; g.fill(); g.restore();
  coil(540, by, 230, 54, 4, t, 1, CYA);
  // campo magnético
  const fa = ease(prog(t, at(Q1, 0.25), at(Q1, 0.35)));
  if (fa > 0) {
    g.save(); g.globalAlpha = fa; g.setLineDash([26, 18]); g.lineDashOffset = -t * 120; g.lineWidth = 6; g.strokeStyle = 'rgba(79,216,255,0.8)';
    for (const k of [0.35, 0.6, 0.85]) { for (const sg of [-1, 1]) { g.beginPath(); g.ellipse(540 + sg * 250 * k, (by + py) / 2, 250 * k * 0.55, (by - py) / 2 + 60, 0, 0, Math.PI * 2); g.stroke(); } }
    g.setLineDash([]); g.restore();
  }
  // teléfono con su bobina, flotando un poco
  const fl = 8 * Math.sin(t * 2);
  g.save(); g.translate(540, py + fl); g.scale(1, 0.3);
  g.beginPath(); g.roundRect(-380, -250 + 70, 760, 500, 70); g.fillStyle = '#6f7a90'; g.fill();
  g.beginPath(); g.roundRect(-380, -250, 760, 500, 70); g.fillStyle = 'rgba(30,38,60,0.82)'; g.fill(); g.lineWidth = 8; g.strokeStyle = TI; g.stroke();
  g.restore();
  const ra = ease(prog(t, at(Q1, 0.5), at(Q1, 0.6)));
  g.save(); g.globalAlpha = 0.35 + 0.65 * ra; coil(540, py + fl, 200, 40, 3, t, 1, ra > 0.5 ? YEL : 'rgba(255,216,77,0.3)'); g.restore();
  const ea = ease(prog(t, at(Q1, 0.72), at(Q1, 0.8)));
  if (ea > 0) { g.save(); g.globalAlpha = ea; g.shadowColor = YEL; g.shadowBlur = 40; bolt(540, py + fl - 150, 120); g.fillStyle = YEL; g.fill(); g.restore(); }
  tag('BOBINA DEL CARGADOR', 540, by + 150, CYA, 38, ease(prog(t, at(Q1, 0.08), at(Q1, 0.16))));
  tag('CAMPO MAGNÉTICO', 860, (by + py) / 2, CYA, 36, fa);
  tag('BOBINA DEL CELULAR', 540, py - 105, YEL, 38, ra * (1 - ea));
  tag('¡ELECTRICIDAD!', 540, py + fl - 250, YEL, 46, ea);
  label(t, a - 0.25, 1e9, 'SIN CABLE', ['por inducción magnética'], WHT, 104);
}

// =====================================================================
// FINAL: resumen y grosor
// =====================================================================
function sceneSummary(t) {
  drawBG(t, 0.6);
  const a = F0[0], b = F0[1];
  viewOpen(t, 1);
  const steps = [['bat', 'ENERGÍA', GRN, 0.14], ['board', 'PIENSA', YEL, 0.33], ['disp', 'MUESTRA', CYA, 0.55], ['cam', 'VEN POR TI', WHT, 0.75]];
  let cur = null, fa = 0;
  for (const [k, , , f] of steps) if (t >= at(F0, f)) { cur = k; fa = ease(prog(t, at(F0, f), at(F0, f) + 0.4)); }
  exploded(1, cur, fa);
  for (const [k, txtS, col, f] of steps) {
    const al = ease(prog(t, at(F0, f), at(F0, f) + 0.4));
    const p = partAnchor(k, 1, cur, k === cur ? fa : 0);
    const off = { bat: [330, 30], board: [-40, -120], disp: [300, -60], cam: [-260, 40] }[k];
    tag3(p, txtS, col, al, 44, off[0], off[1]);
  }
  flushTags();
  label(t, a - 0.25, 1e9, 'ASÍ FUNCIONA', ['cada pieza hace su trabajo'], YEL, 108);
}
function sceneThin(t) {
  drawBG(t, 0.6);
  const a = F1[0], b = F1[1];
  const r = ease(prog(t, a + 0.3, at(F1, 0.5)));
  CAM.yaw = 0; CAM.pitch = lerp(0.15, Math.PI / 2 - 0.02, r); CAM.s = 440; CAM.cx = 540; CAM.cy = 960;
  foldPhone(0, t);
  const ca = ease(prog(t, at(F1, 0.5), at(F1, 0.62)));
  if (ca > 0) {
    // calibrador
    const top = P3(1, 0, 0.0)[1], bot = P3(1, 0, -0.04)[1], xR = 540 + 440 + 40;
    const yc = (top + bot) / 2;
    g.save(); g.globalAlpha = ca; g.fillStyle = '#c9d3e6';
    g.fillRect(xR - 20, yc - 230, 18, 460);
    g.fillRect(xR - 120, yc - 230 - 0, 120, 18 + 0); g.fillRect(xR - 120, yc + 212, 120, 18);
    g.strokeStyle = YEL; g.lineWidth = 5; line(xR - 160, top - 4, xR - 60, top - 4); line(xR - 160, bot + 4, xR - 60, bot + 4);
    g.restore();
    tag('5.2 mm', 540, yc - 170, YEL, 76, ca);
    tag('abierto', 540, yc + 150, CYA, 44, ca);
  }
  label(t, a - 0.25, 1e9, 'TODO ESO CABE EN', ['apenas 5.2 milímetros'], WHT, 100);
}
function sceneEnd(t) {
  drawBG(t, 0.7);
  const E = FLASHES[7];
  const e = backOut(prog(t, E, E + 0.5));
  g.save(); g.translate(540, 830); g.scale(e, e);
  g.shadowColor = YEL; g.shadowBlur = 60; bolt(0, 0, 330); g.fillStyle = YEL; g.fill(); g.lineWidth = 10; g.strokeStyle = INK; g.stroke(); g.restore();
  txt('FLASH DATOS', 540, 1090, 112, WHT, { stroke: 9, alpha: ease(prog(t, E + 0.15, E + 0.5)) });
  txt('Síguenos para más datos', 540, 1200, 54, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, E + 0.3, E + 0.7)) });
}

// =====================================================================
function crossfade(t, a, b, sceneA, sceneB) {
  const s = prog(t, a, b);
  if (s <= 0) return sceneA(t);
  if (s >= 1) return sceneB(t);
  sceneA(t); g.save(); g.globalAlpha = s; sceneB(t); g.restore();
}
const batFocus = t => sceneFocus(t, B0[0], 'bat', 1, 'LA BATERÍA', ['en el Duo son dos'], [
  { p: [-0.5, -0.15, GAP], text: 'MITAD 1', col: GRN, d: 1.6, dy: 40 }, { p: [0.5, -0.05, GAP], text: 'MITAD 2', col: GRN, d: 2.6, dy: 40 },
  { p: [0, -0.8, GAP + 0.2], text: 'TRABAJAN COMO UNA', col: YEL, d: 4.2, dy: 170, size: 42 }]);
const chipFocus = t => sceneFocus(t, C0[0], 'board', 2, 'EL CEREBRO', ['el chip A20 Pro'], [{ p: [-0.42, 0.52, 2 * GAP + 0.2], text: 'A20 PRO', col: YEL, d: 0.6, dy: -60 }]);
function render(t) {
  T = t;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  if (t < FLASHES[0]) sceneSwitches(t);
  else if (t < FLASHES[1]) scenePhoneIntro(t);
  else if (t < FLASHES[2]) crossfade(t, B1[0] - 0.45, B1[0] - 0.05, batFocus, sceneBattery);
  else if (t < FLASHES[3]) { if (t < C1[0] - 0.4) crossfade(t, C0[0] + 1.2, C0[0] + 1.6, chipFocus, sceneChipZoom); else crossfade(t, C1[0] - 0.4, C1[0], sceneChipZoom, sceneTransistor); }
  else if (t < FLASHES[4]) crossfade(t, S1[0] - 0.4, S1[0], sceneScreens, scenePixels);
  else if (t < FLASHES[5]) crossfade(t, K1[0] - 0.35, K1[0] + 0.05, sceneSensor, sceneHiddenCam);
  else if (t < FLASHES[6]) crossfade(t, Q1[0] - 0.4, Q1[0], sceneCable, sceneWireless);
  else if (t < FLASHES[7]) crossfade(t, F1[0] - 0.4, F1[0], sceneSummary, sceneThin);
  else sceneEnd(t);
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.shadowBlur = 0; g.setLineDash([]);
  if (t < FLASHES[7]) drawCaption(t);
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
