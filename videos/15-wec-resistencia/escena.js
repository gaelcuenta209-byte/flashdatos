// Flash Datos · video 15 · El Mundial de Resistencia (WEC): leyendas, circuitos y el Hypercar desarmado
// Escena dibujada en canvas 2D (1080x1920). render(t) dibuja el cuadro del segundo t.
'use strict';
const W = 1080, H = 1920;
const C = document.getElementById('c'), g = C.getContext('2d');
const SEG = {}; TM.segments.forEach(s => SEG[s.id] = s);
const PT = (id, k) => SEG[id].parts[k];
const END = TM.end;
const YEL = '#FFD84D', CYA = '#4FD8FF', WHT = '#FFFFFF', INK = '#080a14';
const BODY_D = '#0e1936', BODY = '#1a2c5c', BODY_L = '#2f4d92', TI = '#c8d1e2', TYRE = '#0b0c11', ORA = '#ff8a3d', RED = '#ff4d5e';
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
  ...['gt40.jpg', 'p917.jpg', 'r10.jpg', 'ts050.jpg', 'gr010.jpg', 'mulsanne.png', 'spa.png', 'fuji.png', 'monza.png'].map(f => loadImg(f.split('.')[0], 'img/' + f)),
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
  if (/^KM\/H$/i.test(c)) return 17;
  if (/^KM$/i.test(c)) return 9;
  if (/^KG$/i.test(c)) return 5;
  if (c === 'GT40') return 11;
  if (c === 'R10') return 6;
  if (c === 'WEC') return 3;
  if (c === '917') return 22;
  if (c === '5,335') return 36;
  if (c === '13.6') return 15;
  if (c === '1.5') return 9;
  if (c === '1,030') return 11;
  if (c === '405') return 26;
  if (c === '500') return 10;
  if (c === '670') return 22;
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

// ---------------- tiempos de sección ----------------
const S = id => SEG[id].t0, E = id => SEG[id].t1;
const L0 = S('gt40') - 0.3;                 // leyendas
const C0 = S('lemans') - 0.3;               // circuitos
const H0 = S('intro') - 0.3;                // hypercar
const F0 = S('final') - 0.3;                // final
const E0 = E('final') + 0.15;               // tarjeta final
const FLASHES = [L0, C0, H0, F0, E0];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
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
function credit(s, y = 1152) { txt(s, 540, y, 24, 'rgba(255,255,255,0.9)', { font: 'IX', stroke: 4 }); }
function badge(text, x, y, e, bg = YEL, fg = INK, size = 60, rot = 0) {
  if (e <= 0) return;
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(e, e);
  g.font = `${size}px IB`; const w = g.measureText(text).width + size * 1.1, h = size * 1.75;
  g.beginPath(); g.roundRect(-w / 2, -h / 2, w, h, h / 2); g.fillStyle = bg; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  txt(text, 0, 3, size, fg, { stroke: 0 }); g.restore();
}

// ---------------- hypercar de perfil (metros; x=0 nariz, y=0 piso; hacia arriba +) ----------------
const HC_BODY = [[0.02, 0.17], [0.10, 0.30], [0.45, 0.42], [0.85, 0.60], [1.25, 0.71], [1.62, 0.70], [1.92, 0.78], [2.22, 1.00], [2.62, 1.08], [3.05, 1.04], [3.45, 0.90], [3.95, 0.80], [4.45, 0.80], [4.86, 0.83], [4.97, 0.62], [4.93, 0.30], [4.55, 0.17], [3.3, 0.12], [1.5, 0.12], [0.4, 0.13]];
const WF = 1.18, WR = 3.98, WRAD = 0.36;
function hcWheel(cx, rot, hl = 0) {
  g.save(); g.translate(cx, WRAD); g.rotate(-rot);
  circle(0, 0, WRAD); g.fillStyle = TYRE; g.fill();
  g.lineWidth = 0.035; g.strokeStyle = hl > 0 ? `rgba(255,216,77,${0.4 + 0.6 * hl})` : '#2b3142'; g.stroke();
  circle(0, 0, 0.25); g.fillStyle = '#1b2233'; g.fill();
  g.strokeStyle = '#8b97b5'; g.lineWidth = 0.025;
  for (let i = 0; i < 5; i++) { const a = i * Math.PI * 2 / 5; line(Math.cos(a) * 0.05, Math.sin(a) * 0.05, Math.cos(a) * 0.23, Math.sin(a) * 0.23); }
  circle(0, 0, 0.05); g.fillStyle = YEL; g.fill();
  g.restore();
}
// o: {lift: separación del cascarón, ghost: transparencia del cascarón, hl: {motor,hib,peso,aero,llantas}, rot, lights}
function hypercar(o = {}) {
  const lift = o.lift || 0, hl = o.hl || {}, rot = o.rot || 0;
  // piso
  g.fillStyle = '#0a1024'; g.fillRect(0.25, 0.10, 4.6, 0.05);
  // interior (motor, híbrido, batería, piloto)
  const inner = lift > 0.01 || (o.ghost ?? 1) < 1;
  if (inner) {
    // tanque/estructura
    g.beginPath(); g.roundRect(1.55, 0.16, 1.55, 0.30, 0.05); g.fillStyle = '#16244a'; g.fill(); g.lineWidth = 0.01; g.strokeStyle = 'rgba(140,200,255,0.5)'; g.stroke();
    // piloto
    g.save(); g.translate(2.35, 0.55); circle(0, 0, 0.13); g.fillStyle = '#f2f4fa'; g.fill(); g.fillStyle = '#0a0f1e'; g.fillRect(-0.13, -0.04, 0.11, 0.06); g.restore();
    g.beginPath(); g.moveTo(2.2, 0.45); g.lineTo(1.75, 0.30); g.lineTo(1.75, 0.22); g.lineTo(2.45, 0.25); g.closePath(); g.fillStyle = '#c8d1e2'; g.fill();
    // motor de combustión
    const m = hl.motor || 0;
    g.save(); if (m > 0) { g.shadowColor = ORA; g.shadowBlur = 0.4 * 80 * m; }
    g.beginPath(); g.roundRect(3.05, 0.18, 0.95, 0.45, 0.06); g.fillStyle = m > 0 ? `rgb(${lerp(70, 255, m)},${lerp(80, 138, m)},${lerp(110, 61, m)})` : '#4b5878'; g.fill();
    g.restore(); g.lineWidth = 0.012; g.strokeStyle = INK; g.beginPath(); g.roundRect(3.05, 0.18, 0.95, 0.45, 0.06); g.stroke();
    for (let i = 0; i < 4; i++) { g.fillStyle = 'rgba(8,10,20,0.45)'; g.fillRect(3.15 + i * 0.21, 0.52, 0.14, 0.08); }
    // caja de cambios
    g.fillStyle = '#39445f'; g.fillRect(4.0, 0.24, 0.42, 0.24);
    // batería (cian)
    const h2 = hl.hib || 0;
    g.save(); if (h2 > 0) { g.shadowColor = CYA; g.shadowBlur = 60 * h2; }
    g.beginPath(); g.roundRect(1.62, 0.20, 0.55, 0.22, 0.04); g.fillStyle = h2 > 0 ? `rgba(79,216,255,${0.45 + 0.55 * h2})` : '#2b5070'; g.fill(); g.restore();
    for (let i = 0; i < 4; i++) { g.fillStyle = 'rgba(8,10,20,0.5)'; g.fillRect(1.68 + i * 0.12, 0.26, 0.07, 0.10); }
    // motor eléctrico delantero
    g.save(); if (h2 > 0) { g.shadowColor = CYA; g.shadowBlur = 60 * h2; }
    circle(WF, WRAD + 0.02, 0.17); g.fillStyle = h2 > 0 ? `rgba(79,216,255,${0.5 + 0.5 * h2})` : '#2b5070'; g.fill(); g.restore();
    // ejes
    g.strokeStyle = '#6a7898'; g.lineWidth = 0.03; line(4.0, 0.36, WR, WRAD); line(1.62, 0.31, WF + 0.17, WRAD);
  }
  // ruedas
  hcWheel(WF, rot, hl.llantas || 0); hcWheel(WR, rot, hl.llantas || 0);
  // cascarón (carrocería)
  g.save(); g.translate(0, lift);
  g.globalAlpha *= (o.ghost ?? 1);
  smooth(HC_BODY);
  const gr = g.createLinearGradient(0, 1.1, 0, 0.1); gr.addColorStop(0, BODY_L); gr.addColorStop(0.55, BODY); gr.addColorStop(1, BODY_D);
  g.fillStyle = gr; g.fill(); g.lineWidth = 0.014; g.strokeStyle = 'rgba(140,200,255,0.75)'; g.stroke();
  // pasos de rueda
  for (const cx of [WF, WR]) { g.beginPath(); g.arc(cx, WRAD, WRAD + 0.06, 0, Math.PI); g.fillStyle = '#050814'; g.fill(); }
  // cabina
  g.beginPath(); g.moveTo(1.98, 0.80); g.quadraticCurveTo(2.3, 1.06, 2.75, 1.04); g.lineTo(3.0, 0.92); g.lineTo(2.05, 0.80); g.closePath(); g.fillStyle = '#03060e'; g.fill(); g.lineWidth = 0.012; g.strokeStyle = 'rgba(79,216,255,0.6)'; g.stroke();
  // franja amarilla
  g.strokeStyle = YEL; g.lineWidth = 0.03; g.beginPath(); g.moveTo(0.2, 0.33); g.quadraticCurveTo(1.5, 0.52, 3.3, 0.55); g.lineTo(4.8, 0.55); g.stroke();
  // número
  g.save(); g.translate(2.85, 0.70); g.scale(-1, -1); g.font = '0.26px IB'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = WHT; g.fillText('15', 0, 0); g.restore();
  // aleta de tiburón
  const a = hl.aero || 0;
  g.beginPath(); g.moveTo(3.0, 1.03); g.quadraticCurveTo(3.9, 1.05, 4.62, 1.12); g.lineTo(4.62, 0.82); g.lineTo(3.9, 0.82); g.closePath();
  g.fillStyle = a > 0 ? `rgba(255,216,77,${0.25 + 0.6 * a})` : 'rgba(47,77,146,0.85)'; g.fill(); g.lineWidth = 0.01; g.strokeStyle = 'rgba(140,200,255,0.7)'; g.stroke();
  // alerón trasero
  g.fillStyle = '#2a3348'; g.fillRect(4.55, 0.83, 0.05, 0.27);
  g.save(); if (a > 0) { g.shadowColor = YEL; g.shadowBlur = 60 * a; }
  g.beginPath(); g.moveTo(4.40, 1.17); g.quadraticCurveTo(4.75, 1.10, 5.08, 1.20); g.lineTo(5.08, 1.12); g.quadraticCurveTo(4.75, 1.05, 4.40, 1.10); g.closePath();
  g.fillStyle = a > 0 ? YEL : BODY_L; g.fill(); g.restore();
  // faros
  const li = o.lights || 0;
  g.save(); g.shadowColor = '#fff6c8'; g.shadowBlur = 30 + 60 * li;
  g.beginPath(); g.ellipse(0.40, 0.40, 0.14, 0.035, -0.35, 0, Math.PI * 2); g.fillStyle = li > 0 ? '#fffbe6' : '#cfe8ff'; g.fill(); g.restore();
  if (li > 0) {
    const gr2 = g.createLinearGradient(0.3, 0, -2.5, 0); gr2.addColorStop(0, `rgba(255,246,200,${0.55 * li})`); gr2.addColorStop(1, 'rgba(255,246,200,0)');
    g.beginPath(); g.moveTo(0.35, 0.42); g.lineTo(-2.6, 0.95); g.lineTo(-2.6, -0.05); g.closePath(); g.fillStyle = gr2; g.fill();
  }
  // luz trasera
  g.fillStyle = RED; g.fillRect(4.86, 0.62, 0.07, 0.16);
  g.restore();
}
// dibuja el hypercar con escala k (px/m) con la nariz a la izquierda en (x0, piso gy)
function drawHC(x0, gy, k, o) { g.save(); g.translate(x0 + 5 * k, gy); g.scale(-k, -k); hypercar(o); g.restore(); }   // nariz a la derecha
const HC2S = (x0, gy, k, xm, ym) => [x0 + (5 - xm) * k, gy - ym * k];

// =====================================================================
// DATO EXTRA: 24 horas y 11 segundos
// =====================================================================
function sceneHook(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('dato', 0);
  // reloj de 24 horas
  const cx = 540, cy = 860, R = 330;
  const fill = ease(prog(t, a + 0.2, a + 4.8));
  g.save();
  circle(cx, cy, R + 26); g.fillStyle = 'rgba(6,10,24,0.85)'; g.fill(); g.lineWidth = 8; g.strokeStyle = 'rgba(79,216,255,0.6)'; g.stroke();
  g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + fill * Math.PI * 2); g.closePath(); g.fillStyle = 'rgba(255,216,77,0.22)'; g.fill();
  g.lineWidth = 26; g.strokeStyle = YEL; g.lineCap = 'round'; g.beginPath(); g.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + Math.max(0.001, fill) * Math.PI * 2); g.stroke();
  for (let i = 0; i < 24; i++) { const an = -Math.PI / 2 + i * Math.PI / 12; g.lineWidth = i % 6 ? 4 : 9; g.strokeStyle = WHT; line(cx + Math.cos(an) * (R - 50), cy + Math.sin(an) * (R - 50), cx + Math.cos(an) * (R - (i % 6 ? 70 : 90)), cy + Math.sin(an) * (R - (i % 6 ? 70 : 90))); }
  const hrs = Math.floor(fill * 24), mins = Math.floor((fill * 24 * 60) % 60);
  txt(`${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}`, cx, cy - 10, 150, WHT, { stroke: 10 });
  txt('HORAS DE CARRERA', cx, cy + 105, 40, CYA, { font: 'IX', stroke: 5 });
  g.restore();
  label(t, a - 0.2, a + 4.9, 'LE MANS 2026', ['24 horas sin parar'], WHT, 104);
  // meta: 2 autos, diferencia < 11 s
  const m = prog(t, a + 4.6, a + 5.2);
  if (m > 0) {
    g.save(); g.globalAlpha = ease(m);
    g.fillStyle = 'rgba(3,8,20,0.75)'; g.fillRect(0, 520, W, 900);
    // línea de meta a cuadros
    for (let i = 0; i < 16; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? WHT : INK; g.fillRect(820 + j * 30, 600 + i * 45, 30, 45); }
    const u = ease(prog(t, a + 4.9, b - 0.4));
    drawHC(lerp(-500, 330, u), 860, 92, { rot: t * 14, lights: 1 });
    drawHC(lerp(-1200, -380, u), 1180, 92, { rot: t * 14, lights: 1 });
    // brecha
    const gx0 = lerp(-1200, -380, u) + 4.97 * 92, gx1 = lerp(-500, 330, u);
    if (u > 0.85) {
      const e = backOut(prog(t, a + 4.9 + (b - 0.4 - a - 4.9) * 0.85, b));
      g.strokeStyle = YEL; g.lineWidth = 6; g.setLineDash([14, 10]); line(gx0, 1060, gx0, 1240); line(gx1, 780, gx1, 1240); g.setLineDash([]);
      badge('< 11 SEGUNDOS', 540, 1340, e, YEL, INK, 62);
    }
    label(t, a + 4.8, b + 0.3, 'GANÓ POR', ['menos de 11 segundos'], YEL, 110);
    g.restore();
  }
}
function sceneWEC(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('dato', 1);
  label(t, a - 0.25, b + 0.6, 'WEC', ['Mundial de Resistencia'], YEL, 150);
  const e = backOut(prog(t, a + 0.1, a + 0.7));
  g.save(); g.translate(540, 900); g.scale(e, e);
  photo(IMG.monza, -480, -250, 960, 490, 1.0, 0.5, 0.5, 26, CYA);
  g.restore();
  credit('Mapa: Will Pittenger · CC BY-SA 3.0 · Wikimedia Commons', 1178);
  badge('FINAL · MONZA · 6–8 NOV', 540, 1300, backOut(prog(t, a + 1.6, a + 2.2)), YEL, INK, 52);
}
function sceneQue(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('que', 0), [c, d] = PT('que', 1);
  if (t < c - 0.25) {
    label(t, a - 0.3, c - 0.2, '6 A 24 HORAS', ['3 pilotos, 1 auto'], WHT, 108);
    // 3 cascos en relevo alrededor del auto
    drawHC(540 - 2.5 * 150, 1150, 150, { rot: t * 10 });
    const who = Math.floor(((t - a) / 1.4) % 3 + 3) % 3;
    for (let i = 0; i < 3; i++) {
      const e = backOut(prog(t, a + 0.2 + i * 0.25, a + 0.7 + i * 0.25)); if (e <= 0) continue;
      const x = 240 + i * 300, y = 700, on = i === who;
      g.save(); g.translate(x, y); g.scale(e * (on ? 1.12 : 1), e * (on ? 1.12 : 1));
      circle(0, 0, 95); g.fillStyle = on ? YEL : 'rgba(255,255,255,0.14)'; g.fill(); g.lineWidth = 7; g.strokeStyle = on ? INK : 'rgba(255,255,255,0.5)'; g.stroke();
      g.beginPath(); g.arc(0, 8, 56, Math.PI * 1.05, Math.PI * 1.95); g.lineTo(52, 30); g.lineTo(-52, 30); g.closePath(); g.fillStyle = on ? INK : '#c8d1e2'; g.fill();
      g.fillStyle = on ? YEL : '#0a1024'; g.fillRect(-10, -14, 58, 22);
      g.restore();
      txt(`PILOTO ${i + 1}`, x, y + 140, 40, on ? YEL : WHT, { font: 'IX', stroke: 5, alpha: e });
    }
    if (t > a + 1) { const [hx, hy] = [240 + who * 300, 800]; arrow(hx, hy + 70, lerp(hx, 540, 0.5), 960, 22, YEL); }
    return;
  }
  // gana el que aguanta: gráfica
  label(t, c - 0.25, d + 0.4, 'GANA EL QUE', ['AGUANTA rápido más tiempo'], YEL, 108);
  const x0 = 120, y0 = 1260, w = 860, h = 560, u = prog(t, c, d - 0.2);
  g.save();
  g.strokeStyle = 'rgba(255,255,255,0.5)'; g.lineWidth = 4; line(x0, y0, x0 + w, y0); line(x0, y0, x0, y0 - h);
  txt('TIEMPO →', x0 + w - 110, y0 + 40, 32, WHT, { font: 'IX', stroke: 4 });
  txt('VELOCIDAD', x0 + 10, y0 - h - 30, 32, WHT, { font: 'IX', stroke: 4, align: 'left' });
  // velocista
  const n = 60;
  g.lineWidth = 12; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath(); for (let i = 0; i <= n * Math.min(u, 0.42) / 0.42 * 0.42 / 1; i++) { const s = i / n; const v = s < 0.3 ? 0.95 : 0.95 * Math.exp(-(s - 0.3) * 14); const X = x0 + s * w, Y = y0 - v * h * 0.9; i ? g.lineTo(X, Y) : g.moveTo(X, Y); } g.strokeStyle = RED; g.stroke();
  if (u > 0.36) { const e = backOut(prog(u, 0.36, 0.5)); g.save(); g.translate(x0 + 0.33 * w, y0 - 0.88 * h * 0.9 - 70); g.scale(e, e); txt('¡SE ROMPE!', 0, 0, 44, RED, { stroke: 6 }); g.restore(); }
  // resistencia
  g.beginPath(); for (let i = 0; i <= n * u; i++) { const s = i / n; const v = 0.78 + 0.03 * Math.sin(s * 40); const X = x0 + s * w, Y = y0 - v * h * 0.9; i ? g.lineTo(X, Y) : g.moveTo(X, Y); } g.strokeStyle = YEL; g.stroke();
  if (u > 0.05) { const X = x0 + u * w, Y = y0 - (0.78 + 0.03 * Math.sin(u * 40)) * h * 0.9; circle(X, Y, 18); g.fillStyle = YEL; g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke(); }
  txt('RESISTENCIA', x0 + w - 170, y0 - 0.78 * h * 0.9 + 60, 38, YEL, { stroke: 5, alpha: ease(prog(u, 0.6, 0.8)) });
  g.restore();
}

// =====================================================================
// LEYENDAS (fotos reales)
// =====================================================================
const CR = {
  gt40: 'Foto: edvvc · CC BY 2.0 · Wikimedia Commons', p917: 'Foto: MrWalkr · CC BY-SA 4.0 · Wikimedia Commons',
  r10: 'Foto: Joachim Köhler · CC BY 3.0 · Wikimedia Commons', ts050: 'Foto: Matti Blume · CC BY-SA 4.0 · Wikimedia Commons',
  gr010: 'Foto: MarcelX42 · CC BY-SA 4.0 · Wikimedia Commons',
};
const LEG = [
  { id: 'gt40', k: 'gt40', fx: 0.45, fy: 0.62 }, { id: 'p917', k: 'p917', fx: 0.5, fy: 0.55 },
  { id: 'audi', k: 'r10', fx: 0.56, fy: 0.62 }, { id: 'toyota', k: 'ts050', fx: 0.55, fy: 0.58 },
];
function mexFlag(x, y, w, h) { const c = ['#0b8f4c', '#ffffff', '#d3202f']; for (let i = 0; i < 3; i++) { g.fillStyle = c[i]; g.fillRect(x + i * w / 3, y, w / 3 + 1, h); } g.lineWidth = 4; g.strokeStyle = INK; g.strokeRect(x, y, w, h); circle(x + w / 2, y + h / 2, h * 0.16); g.fillStyle = '#8a6b2a'; g.fill(); }
function sceneLegends(t) {
  drawBG(t, 0.5);
  let idx = 0; for (let i = 0; i < 4; i++) if (t >= S(LEG[i].id) - 0.3) idx = i;
  for (let j = Math.max(0, idx - 1); j <= idx; j++) {
    const L = LEG[j], a = S(L.id), b = E(L.id);
    const inP = easeOut(prog(t, a - 0.3, a + 0.15));
    const outP = j < 3 ? ease(prog(t, S(LEG[j + 1].id) - 0.3, S(LEG[j + 1].id) + 0.15)) : 0;
    if (inP <= 0 || outP >= 1) continue;
    g.save(); g.translate((1 - inP) * 1100 - outP * 1100, 0);
    const z = 1.06 + 0.05 * prog(t, a - 0.3, b);
    let key = L.k;
    if (L.id === 'toyota' && t > lerp(a, b, 0.62)) key = 'gr010';
    photo(IMG[key], 40, 530, 1000, 650, key === 'gr010' ? 1.12 + 0.04 * prog(t, lerp(a, b, 0.62), b) : z, key === 'gr010' ? 0.45 : L.fx, key === 'gr010' ? 0.6 : L.fy);
    credit(CR[key]);
    if (L.id === 'gt40') {
      const p1 = PT('gt40', 1)[0];
      if (t < p1 - 0.2) {
        txt('FORD GT40', 540, 345, 110, YEL, { stroke: 8 }); txt('1966–1969 · 4 victorias en Le Mans', 540, 437, 46, CYA, { font: 'IX', stroke: 7, maxW: 1000 });
        // regla de 40 pulgadas
        const e = ease(prog(t, a + 1.2, a + 2.0));
        const x = 960, yb = 1060, ht = 330 * e;
        g.strokeStyle = YEL; g.lineWidth = 8; line(x, yb, x, yb - ht); line(x - 26, yb, x + 26, yb); if (e > 0.98) line(x - 26, yb - ht, x + 26, yb - ht);
        badge('40 PULGADAS = 1.02 M', 540, 1290, backOut(prog(t, a + 1.6, a + 2.2)), YEL, INK, 54);
        txt('menos altura = corta menos aire', 540, 1405, 46, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, a + 2.4, a + 2.9)) });
      } else {
        txt('PEDRO RODRÍGUEZ', 540, 345, 100, YEL, { stroke: 8, maxW: 1000 }); txt('Le Mans 1968 · con Lucien Bianchi', 540, 437, 46, CYA, { font: 'IX', stroke: 7, maxW: 1000 });
        const e = backOut(prog(t, p1 + 0.2, p1 + 0.8));
        g.save(); g.translate(540, 1300); g.scale(e, e); mexFlag(-90, -60, 180, 120); g.restore();
        badge('ÚNICO MEXICANO GANADOR', 540, 1430, backOut(prog(t, p1 + 2.0, p1 + 2.6)), YEL, INK, 50);
      }
    } else if (L.id === 'p917') {
      txt('PORSCHE 917', 540, 345, 110, YEL, { stroke: 8 }); txt('chasis de magnesio · 12 cilindros', 540, 437, 46, CYA, { font: 'IX', stroke: 7, maxW: 1000 });
      const km = Math.round(5335 * ease(prog(t, a + 3.0, a + 6.0)));
      const e = ease(prog(t, a + 2.8, a + 3.2));
      txt(`${km.toLocaleString('en-US')} KM`, 540, 1290, 120, WHT, { stroke: 10, alpha: e });
      txt('en 24 horas · 1971', 540, 1385, 46, CYA, { font: 'IX', stroke: 6, alpha: e });
      badge('RÉCORD HASTA 2010', 770, 640, backOut(prog(t, a + 6.4, a + 7.0)), RED, WHT, 46, -0.18);
    } else if (L.id === 'audi') {
      const p1 = PT('audi', 1)[0];
      if (t < p1 - 0.2) {
        txt('AUDI R10 TDI', 540, 345, 110, YEL, { stroke: 8 }); txt('2006 · primer DIÉSEL campeón', 540, 437, 46, CYA, { font: 'IX', stroke: 7, maxW: 1000 });
        // bomba de combustible: menos paradas
        const e = ease(prog(t, a + 1.6, a + 2.2));
        g.save(); g.globalAlpha *= e;
        g.beginPath(); g.roundRect(150, 1235, 780, 120, 60); g.fillStyle = 'rgba(6,10,24,0.85)'; g.fill(); g.lineWidth = 5; g.strokeStyle = CYA; g.stroke();
        const lev = 1 - 0.45 * prog(t, a + 2.2, b);
        g.beginPath(); g.roundRect(170, 1255, 740 * lev, 80, 40); g.fillStyle = YEL; g.fill();
        txt('MENOS CONSUMO = MENOS PARADAS', 540, 1296, 34, INK, { stroke: 0, maxW: 700 });
        g.restore();
      } else {
        txt('TOM KRISTENSEN', 540, 345, 104, YEL, { stroke: 8, maxW: 1000 }); txt('"Mr. Le Mans" · Dinamarca', 540, 437, 46, CYA, { font: 'IX', stroke: 7 });
        for (let i = 0; i < 9; i++) {
          const x = 540 + (i - 4) * 108, y = 1290, on = t > p1 + 0.5 + i * 0.22;
          const e = on ? backOut(prog(t, p1 + 0.5 + i * 0.22, p1 + 0.8 + i * 0.22)) : 0.6;
          g.save(); g.translate(x, y); g.scale(e, e);
          g.beginPath(); g.moveTo(-34, -46); g.lineTo(34, -46); g.quadraticCurveTo(34, 10, 0, 16); g.quadraticCurveTo(-34, 10, -34, -46); g.fillStyle = on ? YEL : 'rgba(255,255,255,0.15)'; g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
          g.fillStyle = on ? YEL : 'rgba(255,255,255,0.15)'; g.fillRect(-7, 14, 14, 20); g.fillRect(-26, 34, 52, 12);
          g.restore();
        }
        const shown = Math.min(9, Math.max(0, Math.floor((t - p1 - 0.5) / 0.22) + 1));
        txt(`${shown} VICTORIAS`, 540, 1410, 60, WHT, { stroke: 7 });
        badge('RÉCORD', 860, 640, backOut(prog(t, p1 + 2.6, p1 + 3.1)), RED, WHT, 62, -0.22);
      }
    } else {
      const sw = lerp(a, b, 0.62);
      if (t < sw) {
        txt('KAMUI KOBAYASHI', 540, 345, 100, YEL, { stroke: 8, maxW: 1000 }); txt('2017 · Toyota híbrido', 540, 437, 46, CYA, { font: 'IX', stroke: 7 });
        const e = backOut(prog(t, a + 1.2, a + 1.8));
        badge('3:14.791', 540, 1290, e, YEL, INK, 84);
        txt('la vuelta más rápida de Le Mans', 540, 1410, 46, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, a + 1.8, a + 2.3)) });
      } else {
        txt('LE MANS 2026', 540, 345, 110, YEL, { stroke: 8 }); txt('Kobayashi · Conway · De Vries', 540, 437, 46, CYA, { font: 'IX', stroke: 7, maxW: 1000 });
        badge('¡GANA OTRA VEZ!', 540, 1300, backOut(prog(t, sw + 0.2, sw + 0.8)), YEL, INK, 70);
      }
    }
    g.restore();
  }
}

// =====================================================================
// CIRCUITOS
// =====================================================================
function gauge(cx, cy, R, v, vmax, unit, col = YEL) {
  g.save();
  g.lineWidth = 30; g.strokeStyle = 'rgba(255,255,255,0.12)'; g.beginPath(); g.arc(cx, cy, R, Math.PI * 0.8, Math.PI * 2.2); g.stroke();
  g.strokeStyle = col; g.lineCap = 'round'; g.beginPath(); g.arc(cx, cy, R, Math.PI * 0.8, Math.PI * 0.8 + Math.PI * 1.4 * clamp(v / vmax)); g.stroke();
  const an = Math.PI * 0.8 + Math.PI * 1.4 * clamp(v / vmax);
  g.strokeStyle = WHT; g.lineWidth = 10; line(cx, cy, cx + Math.cos(an) * (R - 40), cy + Math.sin(an) * (R - 40));
  circle(cx, cy, 22); g.fillStyle = WHT; g.fill();
  txt(String(Math.round(v)), cx, cy + R * 0.55, 120, WHT, { stroke: 9 });
  txt(unit, cx, cy + R * 0.55 + 85, 44, CYA, { font: 'IX', stroke: 5 });
  g.restore();
}
function sceneLeMans(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('lemans', 0), [c, d] = PT('lemans', 1);
  if (t < c - 0.2) {
    label(t, a - 0.3, c - 0.1, 'LE MANS', ['Francia · 13.6 km'], YEL, 120);
    const e = backOut(prog(t, a - 0.1, a + 0.5));
    g.save(); g.translate(540, 870); g.scale(e, e);
    photo(IMG.mulsanne, -500, -340, 1000, 690, 1.02 + 0.06 * prog(t, a, c), 0.5, 0.5, 26, YEL);
    g.restore();
    credit('Mapa: Will Pittenger · CC BY-SA 3.0 · Wikimedia Commons', 1240);
    badge('RECTA MULSANNE = CARRETERA', 540, 1360, backOut(prog(t, a + 3.4, a + 4.0)), CYA, INK, 46);
    return;
  }
  label(t, c - 0.2, d + 0.3, 'RECTA MULSANNE', ['1988 · récord de velocidad'], YEL, 104);
  const v = 405 * ease(prog(t, c + 0.2, c + 2.4));
  gauge(540, 820, 250, v, 420, 'KM/H', v > 400 ? RED : YEL);
  // recta con chicanas
  const e = ease(prog(t, c + 3.0, c + 3.6));
  g.save(); g.globalAlpha *= e;
  const y = 1300;
  g.lineWidth = 70; g.strokeStyle = '#1d2333'; g.lineJoin = 'round';
  g.beginPath(); g.moveTo(60, y); g.lineTo(330, y); g.lineTo(380, y - 60); g.lineTo(430, y); g.lineTo(650, y); g.lineTo(700, y + 60); g.lineTo(750, y); g.lineTo(1020, y); g.stroke();
  g.lineWidth = 4; g.strokeStyle = 'rgba(255,255,255,0.6)'; g.setLineDash([20, 18]);
  g.beginPath(); g.moveTo(60, y); g.lineTo(330, y); g.lineTo(380, y - 60); g.lineTo(430, y); g.lineTo(650, y); g.lineTo(700, y + 60); g.lineTo(750, y); g.lineTo(1020, y); g.stroke(); g.setLineDash([]);
  tag('CHICANA', 380, y - 120, YEL, 34); tag('CHICANA', 700, y + 120, YEL, 34);
  g.restore();
  badge('1990: 2 CHICANAS', 540, 1460, backOut(prog(t, c + 3.6, c + 4.2)), YEL, INK, 52);
}
function sceneSpa(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('spa', 0);
  label(t, a - 0.3, b + 0.3, 'SPA · EAU ROUGE', ['Bélgica · 7 km'], YEL, 104);
  // mapa chico
  const e0 = backOut(prog(t, a - 0.1, a + 0.4));
  g.save(); g.translate(540, 640); g.scale(e0, e0); photo(IMG.spa, -300, -150, 600, 300, 1.0, 0.5, 0.5, 20, CYA); g.restore();
  credit('Mapa: Will Pittenger · CC BY-SA 3.0 · Wikimedia Commons', 815);
  // perfil de la curva: baja y sube
  const prof = x => 1250 + 160 * Math.tanh((x - 360) / 120) * -1 + (x > 360 ? -(x - 360) * 0.55 : 0) * 0 ;
  const P = []; for (let x = 40; x <= 1040; x += 10) { const yb = x < 420 ? 1080 + (x - 40) * 0.42 : 1080 + 380 * 0.42 - (x - 420) * 0.62; P.push([x, yb]); }
  g.save();
  g.lineWidth = 48; g.strokeStyle = '#1d2333'; g.lineJoin = 'round'; g.beginPath(); P.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke();
  g.lineWidth = 6; g.strokeStyle = 'rgba(255,255,255,0.7)'; g.beginPath(); P.forEach(([x, y], i) => i ? g.lineTo(x, y + 26) : g.moveTo(x, y + 26)); g.stroke();
  // auto bajando y subiendo
  const u = prog(t, a + 1.0, b - 0.6), xi = 40 + u * 900;
  const yb = xi < 420 ? 1080 + (xi - 40) * 0.42 : 1080 + 380 * 0.42 - (xi - 420) * 0.62;
  const ang = xi < 420 ? Math.atan(0.42) : -Math.atan(0.62);
  const comp = Math.exp(-Math.pow((xi - 420) / 70, 2));   // compresión en el fondo
  g.translate(xi, yb - 24); g.rotate(ang);
  g.scale(1, 1 - 0.12 * comp);
  drawHC(-2.5 * 70, 0, 70, { rot: t * 16 });
  g.restore();
  if (comp > 0.2) { for (const dx of [-120, 0, 120]) arrow(xi + dx, 880, xi + dx, yb - 110, 30, RED); }
  badge('COMPRESIÓN', 540, 1440, backOut(prog(t, lerp(a + 1.0, b - 0.6, 0.38), lerp(a + 1.0, b - 0.6, 0.45))), RED, WHT, 56);
}
function sceneFuji(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('fuji', 0);
  label(t, a - 0.3, b + 0.3, 'FUJI', ['Japón · al pie del volcán'], YEL, 120);
  // volcán
  g.save(); g.globalAlpha = 0.9;
  g.beginPath(); g.moveTo(80, 1000); g.lineTo(440, 560); g.lineTo(640, 560); g.lineTo(1000, 1000); g.closePath(); g.fillStyle = '#26365f'; g.fill();
  g.beginPath(); g.moveTo(440, 560); g.lineTo(640, 560); g.lineTo(700, 640); g.lineTo(620, 610); g.lineTo(560, 650); g.lineTo(500, 610); g.lineTo(390, 625); g.closePath(); g.fillStyle = '#e8f0ff'; g.fill();
  g.restore();
  const e = backOut(prog(t, a + 0.2, a + 0.8));
  g.save(); g.translate(540, 1080); g.scale(e, e); photo(IMG.fuji, -480, -165, 960, 330, 1.0, 0.5, 0.5, 20, CYA); g.restore();
  credit('Mapa: Will Pittenger · CC BY-SA 3.0 · Wikimedia Commons', 1270);
  // barra de la recta
  const u = ease(prog(t, a + 0.4, a + 2.2));
  g.save(); g.beginPath(); g.roundRect(90, 1340, 900, 70, 35); g.fillStyle = 'rgba(6,10,24,0.85)'; g.fill(); g.lineWidth = 4; g.strokeStyle = YEL; g.stroke();
  g.beginPath(); g.roundRect(100, 1350, 880 * u, 50, 25); g.fillStyle = YEL; g.fill(); g.restore();
  txt(`RECTA: ${(1.5 * u).toFixed(1)} KM`, 540, 1460, 58, WHT, { stroke: 7 });
}
function sceneMonza(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('monza', 0);
  label(t, a - 0.3, b + 0.6, 'MONZA', ['el templo de la velocidad'], YEL, 120);
  const e = backOut(prog(t, a - 0.1, a + 0.4));
  g.save(); g.translate(540, 700); g.scale(e, e); photo(IMG.monza, -440, -225, 880, 450, 1.0, 0.5, 0.5, 20, CYA); g.restore();
  credit('Mapa: Will Pittenger · CC BY-SA 3.0 · Wikimedia Commons', 945);
  // disco de freno al rojo vivo
  const heat = ease(prog(t, a + 1.0, b - 0.2));
  const cx = 540, cy = 1200, R = 170;
  g.save(); g.translate(cx, cy); g.rotate(t * 6);
  g.shadowColor = `rgba(255,${120 - 60 * heat},40,${heat})`; g.shadowBlur = 90 * heat;
  circle(0, 0, R); g.fillStyle = `rgb(${lerp(70, 255, heat)},${lerp(80, 90, heat)},${lerp(100, 40, heat)})`; g.fill();
  g.shadowBlur = 0; circle(0, 0, R * 0.42); g.fillStyle = '#1b2233'; g.fill();
  for (let i = 0; i < 18; i++) { const an = i * Math.PI * 2 / 18; g.strokeStyle = 'rgba(8,10,20,0.55)'; g.lineWidth = 6; line(Math.cos(an) * R * 0.5, Math.sin(an) * R * 0.5, Math.cos(an + 0.3) * R * 0.95, Math.sin(an + 0.3) * R * 0.95); }
  g.restore();
  g.beginPath(); g.roundRect(cx + 90, cy - 120, 90, 240, 22); g.fillStyle = YEL; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  tag('FRENOS AL LÍMITE', 540, 1440, RED, 44, ease(prog(t, a + 1.6, a + 2.0)));
}

// =====================================================================
// HYPERCAR DESARMADO
// =====================================================================
const HK = 190, HX0 = 540 - 2.5 * HK, HGY = 1190;
const PARTS = ['pmotor', 'phibrido', 'plimite', 'ppeso', 'paero', 'pllantas'];
function partAmt(t, id) { return fade(t, S(id) - 0.3, E(id) + 0.15, 0.35); }
function sceneHyper(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('intro', 0);
  const drive = easeOut(prog(t, a - 0.3, a + 1.3));
  const lift = ease(prog(t, b - 1.2, b - 0.2)) * 0.95;
  const hl = { motor: partAmt(t, 'pmotor'), hib: partAmt(t, 'phibrido'), aero: partAmt(t, 'paero'), llantas: partAmt(t, 'pllantas') };
  const x0 = lerp(-1100, HX0, drive);
  const ghost = lift > 0 ? 0.55 : 1;
  // líneas de velocidad
  if (drive < 1) for (let i = 0; i < 9; i++) { g.strokeStyle = `rgba(255,255,255,${0.3 * (1 - drive)})`; g.lineWidth = 5; const y = HGY - 40 - i * 26; line(x0 - 400 - (i % 3) * 90, y, x0 - 40, y); }
  // aire sobre la carrocería en "aero"
  if (hl.aero > 0) {
    g.save(); g.globalAlpha *= hl.aero;
    for (let i = 0; i < 4; i++) {
      const off = 0.15 + i * 0.16; g.setLineDash([26, 18]); g.lineDashOffset = -t * 260; g.strokeStyle = CYA; g.lineWidth = 6;
      g.beginPath(); for (let xm = -0.6; xm <= 5.6; xm += 0.1) { const top = xm < 0 ? 0.3 : xm > 5 ? 1.2 : interpTop(xm); const [X, Y] = HC2S(x0, HGY, HK, xm, top + off + lift); xm === -0.6 ? g.moveTo(X, Y) : g.lineTo(X, Y); } g.stroke();
    }
    g.setLineDash([]); g.restore();
  }
  drawHC(x0, HGY, HK, { lift, ghost, hl, rot: t * (drive < 1 ? 14 : 1.2), lights: 0.6 });
  // flujos de energía
  if (hl.motor > 0) { g.save(); g.globalAlpha *= hl.motor; flow(t, [HC2S(x0, HGY, HK, 3.5, 0.4), HC2S(x0, HGY, HK, WR, WRAD)], ORA); g.restore(); }
  if (hl.hib > 0) {
    const [p0, p1] = PT('phibrido', 0); const half = (p0 + p1) / 2;
    g.save(); g.globalAlpha *= hl.hib;
    if (t < half) flow(t, [HC2S(x0, HGY, HK, WR, WRAD), HC2S(x0, HGY, HK, 2.6, 0.3), HC2S(x0, HGY, HK, 1.9, 0.31)], CYA);
    else flow(t, [HC2S(x0, HGY, HK, 1.9, 0.31), HC2S(x0, HGY, HK, WF, WRAD)], CYA);
    g.restore();
  }
  // etiquetas por pieza
  const N = { pmotor: 1, phibrido: 2, plimite: 3, ppeso: 4, paero: 5, pllantas: 6 };
  const TT = { pmotor: ['MOTOR', 'combustión → llantas traseras'], phibrido: ['HÍBRIDO', 'eléctrico → llantas delanteras'], plimite: ['LÍMITE', '500 kW ≈ 670 caballos'], ppeso: ['PESO', 'mínimo 1,030 kg'], paero: ['AERODINÁMICA', '1 solo paquete aprobado'], pllantas: ['LLANTAS', 'Michelin · de día y de noche'] };
  if (t < S('pmotor') - 0.3) label(t, a - 0.3, S('pmotor') - 0.3, 'HYPERCAR', ['el auto más rápido del WEC'], YEL, 120);
  for (const id of PARTS) label(t, S(id) - 0.3, E(id) + 0.12, TT[id][0], [TT[id][1]], WHT, 100, N[id]);
  // tablero de cada pieza
  const pl = partAmt(t, 'plimite');
  if (pl > 0) {
    g.save(); g.globalAlpha *= pl; g.fillStyle = 'rgba(3,8,20,0.7)'; g.fillRect(0, 560, W, 900);
    const v = 500 * ease(prog(t, S('plimite'), S('plimite') + 2.0));
    gauge(540, 930, 270, v, 520, 'KILOVATIOS', v > 495 ? RED : YEL);
    badge('≈ 670 CABALLOS', 540, 1340, backOut(prog(t, S('plimite') + 2.0, S('plimite') + 2.6)), YEL, INK, 56);
    g.restore();
  }
  const pp = partAmt(t, 'ppeso');
  if (pp > 0) {
    g.save(); g.globalAlpha *= pp;
    // báscula
    g.beginPath(); g.roundRect(HX0 - 30, HGY + 8, 5 * HK + 60, 40, 12); g.fillStyle = '#c8d1e2'; g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
    badge('1,030 KG', 540, 640 + 0, backOut(prog(t, S('ppeso') + 0.3, S('ppeso') + 0.9)), YEL, INK, 64);
    // lastre que cae y potencia que baja
    const s2 = lerp(S('ppeso'), E('ppeso'), 0.45);
    const dropE = easeOut(prog(t, s2, s2 + 0.6));
    if (dropE > 0) {
      const [bx, by] = HC2S(x0, HGY, HK, 2.6, 0.20);
      g.beginPath(); g.roundRect(bx - 70, lerp(560, by - 70, dropE), 140, 70, 10); g.fillStyle = '#9aa6c2'; g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
      txt('+ KG', bx, lerp(560, by - 70, dropE) + 36, 40, INK, { stroke: 0 });
      tag('BALANCE DE RENDIMIENTO', 540, 1440, CYA, 40, ease(prog(t, s2 + 0.5, s2 + 0.9)));
    }
    g.restore();
  }
  const pa = partAmt(t, 'paero');
  if (pa > 0) badge('1 KIT AERO', 860, 700, backOut(prog(t, S('paero') + 1.0, S('paero') + 1.6)) * pa, YEL, INK, 52, -0.15);
  const pt = partAmt(t, 'pllantas');
  if (pt > 0) {
    g.save(); g.globalAlpha *= pt;
    const cyc = (t - S('pllantas')) / 3.2;
    const day = 0.5 + 0.5 * Math.cos(cyc * Math.PI * 2);
    const sx = 540 + Math.cos(cyc * Math.PI * 2 + Math.PI) * 300, sy = 760 - Math.abs(Math.sin(cyc * Math.PI * 2)) * 90;
    circle(sx, sy, 60); g.fillStyle = day > 0.5 ? YEL : '#e8f0ff'; g.fill();
    txt(day > 0.5 ? 'DÍA' : 'NOCHE', sx, sy + 105, 40, WHT, { font: 'IX', stroke: 5 });
    tag('MICHELIN', 540, 1440, YEL, 46);
    g.restore();
  }
}
const TOPS = [[0, 0.17], [0.45, 0.42], [0.85, 0.60], [1.25, 0.71], [1.62, 0.70], [2.22, 1.00], [2.62, 1.08], [3.05, 1.04], [3.9, 1.06], [4.6, 1.12], [5.0, 1.2]];
function interpTop(x) { for (let i = 0; i < TOPS.length - 1; i++) if (x <= TOPS[i + 1][0]) { const s = (x - TOPS[i][0]) / (TOPS[i + 1][0] - TOPS[i][0]); return lerp(TOPS[i][1], TOPS[i + 1][1], s); } return TOPS[TOPS.length - 1][1]; }
function flow(t, pts, col) {
  g.save(); g.setLineDash([22, 16]); g.lineDashOffset = -t * 160; g.strokeStyle = col; g.lineWidth = 12; g.lineCap = 'round';
  g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke(); g.setLineDash([]);
  const [xa, ya] = pts[pts.length - 2], [xb, yb] = pts[pts.length - 1]; const L = Math.hypot(xb - xa, yb - ya);
  arrow(xb - (xb - xa) / L * 70, yb - (yb - ya) / L * 70, xb - (xb - xa) / L * 10, yb - (yb - ya) / L * 10, 24, col);
  g.restore();
}

// =====================================================================
// FINAL
// =====================================================================
function sceneFinal(t) {
  const [a, b] = PT('final', 0), [c, d] = PT('final', 1);
  // cielo día → noche
  const night = ease(prog(t, a, b));
  drawBG(t, 0.4);
  g.fillStyle = `rgba(0,0,8,${0.45 * night})`; g.fillRect(0, 0, W, H);
  // pista que pasa
  const y = 1240;
  g.fillStyle = '#1d2333'; g.fillRect(0, y - 10, W, 170); g.fillStyle = 'rgba(255,255,255,0.75)'; g.fillRect(0, y - 10, W, 6);
  for (let i = 0; i < 9; i++) { const x = ((i * 160 - t * 900) % 1440 + 1440) % 1440 - 180; g.fillStyle = 'rgba(255,255,255,0.55)'; g.fillRect(x, y + 70, 90, 10); }
  // horas que pasan
  const hrs = Math.min(24, Math.floor(24 * prog(t, a, d - 0.5)));
  if (t < c - 0.2) {
    label(t, a - 0.3, c - 0.2, 'SIN ROMPERSE', ['rápido durante horas'], YEL, 110);
    txt(`HORA ${hrs}`, 540, 760, 90, WHT, { stroke: 8 });
    drawHC(540 - 2.5 * 130, y + 20, 130, { rot: t * 20, lights: night });
  } else {
    label(t, c - 0.2, d + 0.3, 'LLEGAR PRIMERO', ['a la META'], YEL, 110);
    // bandera a cuadros
    const fx = 830, fy = 620, wv = Math.sin(t * 8) * 8;
    g.strokeStyle = WHT; g.lineWidth = 10; line(fx - 140, fy - 40, fx - 140, fy + 360);
    for (let i = 0; i < 6; i++) for (let j = 0; j < 4; j++) { g.fillStyle = (i + j) % 2 ? WHT : INK; g.fillRect(fx - 135 + i * 45, fy - 40 + j * 45 + Math.sin(t * 8 + i) * 6, 45, 45); }
    for (let i = 0; i < 12; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? WHT : INK; g.fillRect(i * 90, y - 4 + j * 45, 90, 45); }
    const u = ease(prog(t, c, d - 0.3));
    drawHC(lerp(-700, 700, u), y + 20, 120, { rot: t * 20, lights: 1 });
    if (u > 0.55) badge('¡META!', 300, 1000, backOut(prog(t, lerp(c, d - 0.3, 0.55), lerp(c, d - 0.3, 0.7))), YEL, INK, 80, -0.12);
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
  const w1 = PT('dato', 1)[0], q0 = S('que'), sp = S('spa'), fu = S('fuji'), mo = S('monza');
  if (t < q0 - 0.3) crossfade(t, w1 - 0.5, w1 - 0.1, sceneHook, sceneWEC);
  else if (t < L0) crossfade(t, q0 - 0.3, q0 + 0.1, sceneWEC, sceneQue);
  else if (t < C0) sceneLegends(t);
  else if (t < sp - 0.3) sceneLeMans(t);
  else if (t < fu - 0.3) crossfade(t, sp - 0.3, sp + 0.1, sceneLeMans, sceneSpa);
  else if (t < mo - 0.3) crossfade(t, fu - 0.3, fu + 0.1, sceneSpa, sceneFuji);
  else if (t < H0) crossfade(t, mo - 0.3, mo + 0.1, sceneFuji, sceneMonza);
  else if (t < F0) sceneHyper(t);
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
