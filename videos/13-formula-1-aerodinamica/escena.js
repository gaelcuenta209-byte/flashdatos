// Flash Datos · video 13 · Por qué un Fórmula 1 es tan aerodinámico
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
  loadImg('lotus', 'img/lotus79.jpg'), loadImg('mp44', 'img/mp44.jpg'), loadImg('f2004', 'img/f2004.jpg'),
  loadImg('rb19', 'img/rb19.jpg'), loadImg('render', 'img/render1.png'),
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
  if (/^F1$/i.test(c)) return 10;
  if (/^KM\/H$/i.test(c)) return 17;
  if (/^V6$/i.test(c)) return 8;
  if (c === '1.6') return 13;
  if (c === '1,000') return 4;
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

// ---------------- auto de F1: vista superior (metros; nariz en y=0, hacia abajo) ----------------
function bodyGrad(x0, x1) { const gr = g.createLinearGradient(x0, 0, x1, 0); gr.addColorStop(0, BODY_D); gr.addColorStop(0.5, BODY_L); gr.addColorStop(1, BODY_D); return gr; }
function edge(w = 0.012, col = 'rgba(140,200,255,0.65)') { g.lineWidth = w; g.strokeStyle = col; g.stroke(); }
function topFrontWing() {
  g.beginPath(); g.moveTo(-0.80, 0.20); g.quadraticCurveTo(0, 0.0, 0.80, 0.20); g.lineTo(0.80, 0.40); g.quadraticCurveTo(0, 0.22, -0.80, 0.40); g.closePath();
  g.fillStyle = bodyGrad(-0.8, 0.8); g.fill(); edge();
  g.lineWidth = 0.008; g.strokeStyle = 'rgba(120,170,255,0.55)';
  for (const d of [0.065, 0.13]) { g.beginPath(); g.moveTo(-0.78, 0.20 + d); g.quadraticCurveTo(0, 0.02 + d, 0.78, 0.20 + d); g.stroke(); }
  g.beginPath(); g.moveTo(-0.80, 0.20); g.quadraticCurveTo(0, 0.0, 0.80, 0.20); g.lineWidth = 0.02; g.strokeStyle = YEL; g.stroke();
  g.fillStyle = YEL; for (const s of [-1, 1]) g.fillRect(s * 0.80 - 0.02, 0.13, 0.04, 0.31);
}
const CH_L = [[0, 0.04], [-0.07, 0.09], [-0.15, 1.25], [-0.29, 1.80], [-0.31, 2.65], [-0.27, 3.25], [-0.19, 4.0], [-0.10, 4.6]];
function topChassis(susp = 1) {
  if (susp > 0) {
    g.save(); g.globalAlpha *= susp; g.strokeStyle = '#6a7898'; g.lineWidth = 0.028; g.lineCap = 'round';
    for (const s of [-1, 1]) { line(s * 0.13, 0.82, s * 0.66, 0.95); line(s * 0.17, 1.20, s * 0.66, 1.02); line(s * 0.22, 4.10, s * 0.60, 4.30); line(s * 0.18, 4.52, s * 0.60, 4.38); }
    g.restore();
  }
  const all = CH_L.concat([[0.10, 4.6], [0.19, 4.0], [0.27, 3.25], [0.31, 2.65], [0.29, 1.80], [0.15, 1.25], [0.07, 0.09]]);
  smooth(all); g.fillStyle = bodyGrad(-0.31, 0.31); g.fill(); edge();
  g.strokeStyle = YEL; g.lineWidth = 0.018; g.lineCap = 'round'; line(0, 0.25, 0, 1.70); line(0, 2.98, 0, 4.42);
  // espejos
  for (const s of [-1, 1]) { g.strokeStyle = '#3b5798'; g.lineWidth = 0.02; line(s * 0.27, 1.88, s * 0.36, 1.85); g.fillStyle = BODY_L; g.fillRect(s * 0.36 - 0.05, 1.81, 0.10, 0.06); }
  // cabina, casco y toma de aire
  g.beginPath(); g.ellipse(0, 2.20, 0.19, 0.36, 0, 0, Math.PI * 2); g.fillStyle = '#03060e'; g.fill(); edge(0.01, 'rgba(79,216,255,0.5)');
  const hg = g.createRadialGradient(-0.03, 2.30, 0.01, 0, 2.33, 0.12); hg.addColorStop(0, '#ffffff'); hg.addColorStop(1, '#aeb9d2');
  circle(0, 2.33, 0.115); g.fillStyle = hg; g.fill();
  g.save(); circle(0, 2.33, 0.115); g.clip(); g.fillStyle = YEL; g.fillRect(-0.13, 2.30, 0.26, 0.035); g.restore();
  g.beginPath(); g.ellipse(0, 2.72, 0.11, 0.075, 0, 0, Math.PI * 2); g.fillStyle = '#03060e'; g.fill();
}
function topHalo() {
  g.lineCap = 'round';
  g.beginPath(); g.moveTo(-0.24, 2.62); g.bezierCurveTo(-0.27, 2.05, -0.14, 1.92, 0, 1.90); g.bezierCurveTo(0.14, 1.92, 0.27, 2.05, 0.24, 2.62);
  g.lineWidth = 0.075; g.strokeStyle = INK; g.stroke(); g.lineWidth = 0.055; g.strokeStyle = TI; g.stroke();
  g.lineWidth = 0.02; g.strokeStyle = 'rgba(255,255,255,0.8)'; g.stroke();
  g.lineWidth = 0.055; g.strokeStyle = TI; line(0, 1.90, 0, 1.80);
  g.fillStyle = '#7f8aa3'; for (const s of [-1, 1]) g.fillRect(s * 0.24 - 0.04, 2.58, 0.08, 0.06);
}
const POD_L = [[-0.30, 1.98], [-0.60, 2.02], [-0.69, 2.28], [-0.68, 2.75], [-0.61, 3.35], [-0.47, 3.86], [-0.29, 4.12], [-0.29, 2.6]];
function topSidepods() {
  for (const s of [-1, 1]) {
    smooth(POD_L.map(([x, y]) => [x * s, y]));
    g.fillStyle = bodyGrad(s * -0.69, s * -0.29); g.fill(); edge();
    g.beginPath(); g.roundRect(Math.min(s * -0.58, s * -0.33), 1.99, 0.25, 0.07, 0.03); g.fillStyle = '#02050c'; g.fill();
    g.beginPath(); g.moveTo(s * -0.56, 2.16); g.quadraticCurveTo(s * -0.58, 3.25, s * -0.33, 3.98); g.lineWidth = 0.016; g.strokeStyle = YEL; g.stroke();
  }
}
function topMotor() {
  g.beginPath(); g.roundRect(-0.20, 2.70, 0.40, 0.17, 0.03); g.fillStyle = '#0b2b3d'; g.fill(); edge(0.014, CYA);
  bolt(0, 2.785, 0.13); g.fillStyle = CYA; g.fill();
  const bg = g.createLinearGradient(-0.24, 0, 0.24, 0); bg.addColorStop(0, '#2a3247'); bg.addColorStop(0.5, '#556079'); bg.addColorStop(1, '#2a3247');
  g.beginPath(); g.roundRect(-0.24, 2.95, 0.48, 0.80, 0.06); g.fillStyle = bg; g.fill(); edge(0.012, 'rgba(200,215,240,0.6)');
  for (const s of [-1, 1]) {
    g.beginPath(); g.roundRect(s > 0 ? 0.05 : -0.21, 3.0, 0.16, 0.70, 0.03); g.fillStyle = '#3c4660'; g.fill();
    [3.12, 3.35, 3.58].forEach((y, i) => {
      const idx = s > 0 ? i * 2 + 1 : i * 2;
      const fire = Math.max(0, Math.cos((T * 9 - idx * Math.PI / 3)));
      circle(s * 0.13, y, 0.052); g.fillStyle = `rgb(${154 + 101 * fire ** 6},${166 - 30 * fire ** 6},${192 - 130 * fire ** 6})`; g.fill();
    });
  }
  g.beginPath(); g.roundRect(0.27, 3.05, 0.13, 0.22, 0.03); g.fillStyle = '#0b2b3d'; g.fill(); edge(0.014, CYA);
  bolt(0.335, 3.16, 0.12); g.fillStyle = CYA; g.fill();
  circle(0, 3.90, 0.11); g.fillStyle = '#5b667f'; g.fill(); edge(0.012, 'rgba(220,230,250,0.7)');
  g.save(); g.translate(0, 3.90); g.rotate(T * 14); g.strokeStyle = '#c9d2e6'; g.lineWidth = 0.014;
  for (let i = 0; i < 7; i++) { g.rotate(Math.PI * 2 / 7); g.beginPath(); g.moveTo(0.02, 0); g.quadraticCurveTo(0.06, 0.03, 0.095, 0.01); g.stroke(); }
  g.restore();
  circle(0, 4.08, 0.045); g.fillStyle = '#141925'; g.fill(); edge(0.012, ORA);
}
const FLOOR = [[-0.30, 1.60], [0.30, 1.60], [0.72, 2.15], [0.74, 3.9], [0.66, 4.35], [0.55, 4.55], [-0.55, 4.55], [-0.66, 4.35], [-0.74, 3.9], [-0.72, 2.15]];
function topFloor() {
  poly(FLOOR); g.fillStyle = '#121a30'; g.fill(); edge(0.016, 'rgba(79,216,255,0.7)');
  g.save(); g.setLineDash([0.06, 0.04]); g.lineWidth = 0.014; g.strokeStyle = 'rgba(79,216,255,0.75)';
  for (const s of [-1, 1]) for (const k of [0, 1]) {
    const xo = k ? 0.56 : 0.18;
    g.beginPath(); g.moveTo(s * (xo + (k ? 0.08 : -0.02)), 1.95); g.bezierCurveTo(s * (xo - (k ? 0.10 : -0.10)), 2.9, s * (xo - (k ? 0.12 : -0.12)), 3.6, s * (xo + (k ? 0.0 : -0.05)), 4.5); g.stroke();
  }
  g.restore();
  g.fillStyle = 'rgba(255,216,77,0.28)'; g.fillRect(-0.05, 1.7, 0.10, 2.8);
}
function topDiffuser() {
  const gr = g.createLinearGradient(0, 4.55, 0, 4.95); gr.addColorStop(0, '#121a30'); gr.addColorStop(1, '#2a3a66');
  poly([[-0.45, 4.55], [0.45, 4.55], [0.52, 4.95], [-0.52, 4.95]]); g.fillStyle = gr; g.fill(); edge(0.014, 'rgba(79,216,255,0.75)');
  g.strokeStyle = YEL; g.lineWidth = 0.014; for (const x of [-0.34, -0.17, 0, 0.17, 0.34]) line(x, 4.58, x * 1.1, 4.93);
}
function topRearWing() {
  g.fillStyle = BODY_L; g.fillRect(-0.47, 5.02, 0.94, 0.11); g.fillStyle = BODY; g.fillRect(-0.47, 5.15, 0.94, 0.08);
  g.strokeStyle = 'rgba(140,200,255,0.7)'; g.lineWidth = 0.01; g.strokeRect(-0.47, 5.02, 0.94, 0.11); g.strokeRect(-0.47, 5.15, 0.94, 0.08);
  g.fillStyle = YEL; for (const s of [-1, 1]) g.fillRect(s * 0.495 - 0.02, 4.95, 0.04, 0.33);
  g.fillStyle = '#3b4a70'; g.fillRect(-0.03, 4.98, 0.06, 0.06);
}
function topWheel(cx, cy, w) {
  const l = 0.72;
  const gr = g.createLinearGradient(cx - w / 2, 0, cx + w / 2, 0); gr.addColorStop(0, '#050608'); gr.addColorStop(0.5, '#2b2e38'); gr.addColorStop(1, '#050608');
  g.beginPath(); g.roundRect(cx - w / 2, cy - l / 2, w, l, 0.09); g.fillStyle = gr; g.fill(); edge(0.01, 'rgba(160,170,200,0.5)');
  g.strokeStyle = YEL; g.lineWidth = 0.012; for (const s of [-1, 1]) line(cx + s * (w / 2 - 0.03), cy - l / 2 + 0.12, cx + s * (w / 2 - 0.03), cy + l / 2 - 0.12);
}

// Piezas: centro en coordenadas del auto, semiancho/semialto, celda de la cuadrícula
const COLX = [190, 540, 890], ROWY = [580, 930, 1280], CS = 330;
const PARTS = {
  floor: { num: 5, c: [0, 3.08], h: [0.75, 1.48], cell: [2, 1], draw: topFloor },
  diff: { num: 6, c: [0, 4.75], h: [0.52, 0.20], cell: [2, 0], draw: topDiffuser },
  wFL: { num: 8, c: [-0.80, 0.98], h: [0.15, 0.36], cell: [0, 0], off: [-62, -72], draw: () => topWheel(-0.80, 0.98, 0.30) },
  wFR: { num: 8, c: [0.80, 0.98], h: [0.15, 0.36], cell: [0, 0], off: [62, -72], draw: () => topWheel(0.80, 0.98, 0.30) },
  wRL: { num: 8, c: [-0.78, 4.33], h: [0.19, 0.36], cell: [0, 0], off: [-62, 72], draw: () => topWheel(-0.78, 4.33, 0.38) },
  wRR: { num: 8, c: [0.78, 4.33], h: [0.19, 0.36], cell: [0, 0], off: [62, 72], draw: () => topWheel(0.78, 4.33, 0.38) },
  motor: { num: 4, c: [0, 3.41], h: [0.40, 0.71], cell: [2, 2], draw: topMotor, hidden: true },
  pods: { num: 3, c: [0, 3.05], h: [0.70, 1.07], cell: [1, 2], draw: topSidepods },
  chassis: { num: 0, c: [0, 2.35], h: [0.39, 2.30], cell: [1, 1], draw: topChassis },
  halo: { num: 2, c: [0, 2.22], h: [0.28, 0.42], cell: [0, 2], draw: topHalo },
  fw: { num: 1, c: [0, 0.22], h: [0.82, 0.22], cell: [0, 1], draw: topFrontWing },
  rw: { num: 7, c: [0, 5.12], h: [0.52, 0.18], cell: [1, 0], draw: topRearWing },
};
const ORDER = ['floor', 'diff', 'wFL', 'wFR', 'wRL', 'wRR', 'motor', 'pods', 'chassis', 'halo', 'fw', 'rw'];
for (const k of ORDER) {
  const p = PARTS[k];
  p.s = k[0] === 'w' && k.length === 3 ? 150 : Math.min(330, 0.80 * CS / (2 * p.h[0]), 0.80 * CS / (2 * p.h[1]));
}
const NUM_PART = { 1: 'fw', 2: 'halo', 3: 'pods', 4: 'motor', 5: 'floor', 6: 'diff', 7: 'rw', 8: 'wheels' };
const NUM_CELL = { 1: [0, 1], 2: [0, 2], 3: [1, 2], 4: [2, 2], 5: [2, 1], 6: [2, 0], 7: [1, 0], 8: [0, 0] };
const FOCUS_SEG = { 1: 'alerondel', 2: 'halo', 3: 'pontones', 4: 'motor', 5: 'piso', 6: 'difusor', 7: 'alerontras', 8: 'llantas' };
const A_SCALE = 200, A_CY = 2.68, A_Y = 930;
function drawCarTopAt(x, y, s, rot = 0, cy = A_CY, susp = 1) {
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s); g.translate(0, -cy);
  for (const k of ORDER) { if (PARTS[k].hidden) continue; if (k === 'chassis') topChassis(susp); else PARTS[k].draw(); }
  g.restore();
}

// ---------------- auto de F1: vista lateral (metros; x=0 nariz, y hacia arriba) ----------------
function airfoil(lx, ly, chord, angDeg, thick, camber, inverted, fill, stroke, lw) {
  const N = 28, up = [], lo = [];
  for (let i = 0; i <= N; i++) {
    const x = (1 - Math.cos(Math.PI * i / N)) / 2;
    const yt = 5 * thick * (0.2969 * Math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4);
    const yc = 4 * camber * x * (1 - x);
    up.push([x, yc + yt]); lo.push([x, yc - yt]);
  }
  const pts = up.concat(lo.reverse()).map(([x, y]) => [x * chord, (inverted ? -y : y) * chord]);
  const a = angDeg * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a);
  poly(pts.map(([x, y]) => [lx + x * ca - y * sa, ly + x * sa + y * ca]));
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.lineWidth = lw; g.strokeStyle = stroke; g.stroke(); }
}
function wheelSide(cx, cy, rot, r = 0.36) {
  circle(cx, cy, r); g.fillStyle = TYRE; g.fill(); g.lineWidth = 0.012; g.strokeStyle = 'rgba(120,130,160,0.6)'; g.stroke();
  circle(cx, cy, r * 0.85); g.lineWidth = r * 0.035; g.strokeStyle = YEL; g.stroke();
  const rg = g.createRadialGradient(cx, cy, 0, cx, cy, r * 0.66); rg.addColorStop(0, '#4a5470'); rg.addColorStop(1, '#151a26');
  circle(cx, cy, r * 0.64); g.fillStyle = rg; g.fill();
  g.save(); g.translate(cx, cy); g.rotate(rot); g.strokeStyle = '#8c97b2'; g.lineWidth = r * 0.06; g.lineCap = 'round';
  for (let i = 0; i < 10; i++) { const a = i * Math.PI / 5; line(Math.cos(a) * r * 0.16, Math.sin(a) * r * 0.16, Math.cos(a) * r * 0.58, Math.sin(a) * r * 0.58); }
  g.restore();
  circle(cx, cy, r * 0.14); g.fillStyle = YEL; g.fill();
}
// o: wheelRot, rwOpen (0 cerrado..1 abierto), fwOpen, lift, floorPlate
function carSide(o = {}) {
  const lift = o.lift || 0, rwO = o.rwOpen || 0, fwO = o.fwOpen || 0;
  g.save(); g.fillStyle = 'rgba(0,0,0,0.45)'; g.beginPath(); g.ellipse(2.67, 0.005, 2.7, 0.045, 0, 0, Math.PI * 2); g.fill(); g.restore();
  g.save(); g.translate(0, lift);
  // suspensión
  g.strokeStyle = '#5f6d8e'; g.lineWidth = 0.025; line(0.98, 0.36 - lift, 1.45, 0.42); line(0.98, 0.36 - lift, 1.45, 0.25); line(4.33, 0.36 - lift, 3.95, 0.40); line(4.33, 0.36 - lift, 3.95, 0.24);
  if (!o.noFloor) { poly([[1.30, 0.035], [4.0, 0.035], [4.75, 0.20], [4.75, 0.235], [4.0, 0.07], [1.30, 0.07]]); g.fillStyle = '#101727'; g.fill(); }
  // carrocería
  g.beginPath();
  g.moveTo(0.10, 0.17); g.quadraticCurveTo(0.06, 0.25, 0.24, 0.28); g.lineTo(1.20, 0.46); g.lineTo(1.86, 0.57); g.lineTo(1.95, 0.63); g.lineTo(2.62, 0.63);
  g.lineTo(2.66, 0.68); g.quadraticCurveTo(2.68, 0.94, 2.96, 0.95); g.quadraticCurveTo(3.45, 0.93, 4.02, 0.68); g.lineTo(4.55, 0.45); g.lineTo(4.63, 0.30); g.lineTo(4.56, 0.13);
  g.lineTo(1.62, 0.09); g.lineTo(1.25, 0.16); g.lineTo(0.30, 0.15); g.closePath();
  const bg = g.createLinearGradient(0, 0.08, 0, 0.95); bg.addColorStop(0, BODY_D); bg.addColorStop(0.55, BODY); bg.addColorStop(1, BODY_L);
  g.fillStyle = bg; g.fill(); g.lineWidth = 0.012; g.strokeStyle = 'rgba(140,200,255,0.65)'; g.stroke();
  // pontón
  g.beginPath(); g.moveTo(1.78, 0.15); g.lineTo(1.78, 0.46); g.quadraticCurveTo(1.80, 0.52, 1.93, 0.52); g.lineTo(2.9, 0.50); g.quadraticCurveTo(3.6, 0.44, 4.22, 0.22); g.lineTo(4.26, 0.13); g.closePath();
  g.fillStyle = 'rgba(70,110,200,0.35)'; g.fill(); g.lineWidth = 0.01; g.strokeStyle = 'rgba(140,200,255,0.5)'; g.stroke();
  g.fillStyle = '#02050c'; g.fillRect(1.78, 0.20, 0.06, 0.26);
  g.strokeStyle = YEL; g.lineWidth = 0.018; g.beginPath(); g.moveTo(0.26, 0.255); g.lineTo(1.84, 0.53); g.stroke();
  g.beginPath(); g.moveTo(1.95, 0.47); g.quadraticCurveTo(3.4, 0.43, 4.15, 0.20); g.stroke();
  // casco y halo
  circle(2.30, 0.72, 0.115); { const hg = g.createRadialGradient(2.27, 0.76, 0.01, 2.30, 0.72, 0.12); hg.addColorStop(0, '#fff'); hg.addColorStop(1, '#a9b4cc'); g.fillStyle = hg; } g.fill();
  g.save(); circle(2.30, 0.72, 0.115); g.clip(); g.fillStyle = YEL; g.fillRect(2.18, 0.77, 0.26, 0.05); g.fillStyle = '#0a0f1e'; g.fillRect(2.17, 0.70, 0.12, 0.045); g.restore();
  g.lineCap = 'round'; g.beginPath(); g.moveTo(1.94, 0.63); g.quadraticCurveTo(1.98, 0.83, 2.24, 0.855); g.lineTo(2.60, 0.82); g.lineTo(2.63, 0.66);
  g.lineWidth = 0.05; g.strokeStyle = INK; g.stroke(); g.lineWidth = 0.034; g.strokeStyle = TI; g.stroke();
  // alerón delantero (activo)
  g.fillStyle = 'rgba(255,216,77,0.10)'; poly([[0.0, 0.04], [0.62, 0.04], [0.64, 0.28], [0.03, 0.25]]); g.fill(); g.lineWidth = 0.01; g.strokeStyle = 'rgba(255,216,77,0.45)'; g.stroke();
  airfoil(0.0, 0.085, 0.42, 4, 0.10, 0.05, true, BODY_L, 'rgba(160,210,255,0.8)', 0.008);
  airfoil(0.36, 0.10, 0.22, lerp(26, 8, fwO), 0.10, 0.05, true, BODY_L, YEL, 0.009);
  airfoil(0.50, 0.15, 0.15, lerp(42, 16, fwO), 0.10, 0.05, true, BODY_L, YEL, 0.009);
  // alerón trasero (activo)
  g.fillStyle = 'rgba(255,216,77,0.10)'; poly([[4.62, 0.36], [5.30, 0.36], [5.33, 1.00], [4.68, 0.98]]); g.fill(); g.lineWidth = 0.01; g.strokeStyle = 'rgba(255,216,77,0.45)'; g.stroke();
  g.strokeStyle = '#4a5a82'; g.lineWidth = 0.05; line(4.80, 0.42, 4.92, 0.80);
  airfoil(4.72, 0.80, 0.40, 8, 0.11, 0.05, true, BODY_L, 'rgba(160,210,255,0.8)', 0.009);
  airfoil(5.08, 0.88, 0.22, lerp(42, 8, rwO), 0.11, 0.05, true, BODY_L, YEL, 0.01);
  g.restore();
  wheelSide(0.98, 0.36, o.wheelRot || 0); wheelSide(4.33, 0.36, o.wheelRot || 0);
}
// Contorno superior del auto (para líneas de flujo) y piso esquemático (alto exagerado)
function interp(keys, x) {
  if (x <= keys[0][0]) return keys[0][1];
  for (let i = 0; i < keys.length - 1; i++) if (x <= keys[i + 1][0]) { const s = (x - keys[i][0]) / (keys[i + 1][0] - keys[i][0]); return lerp(keys[i][1], keys[i + 1][1], ease(s)); }
  return keys[keys.length - 1][1];
}
const TOPK = [[-0.6, 0.22], [0.1, 0.28], [1.2, 0.48], [1.9, 0.64], [2.3, 0.90], [2.96, 0.98], [3.9, 0.76], [4.6, 1.02], [5.3, 1.04], [6.2, 0.95]];
const FLK = [[0.6, 0.20], [1.3, 0.19], [1.9, 0.15], [2.8, 0.11], [3.85, 0.13], [4.75, 0.34], [5.6, 0.42]];
function floorSchem(alpha = 1, hl = 0) {
  // placa del piso (vista lateral exagerada): parte de abajo = FLK
  g.beginPath(); g.moveTo(1.30, interp(FLK, 1.30));
  for (let x = 1.30; x <= 4.75; x += 0.05) g.lineTo(x, interp(FLK, x));
  for (let x = 4.75; x >= 1.30; x -= 0.05) g.lineTo(x, interp(FLK, x) + 0.05);
  g.closePath(); g.fillStyle = '#0d1424'; g.fill(); g.lineWidth = 0.014; g.strokeStyle = `rgba(79,216,255,${0.9 * alpha})`; g.stroke();
  if (hl > 0) {
    g.save(); g.globalAlpha *= hl; g.beginPath(); g.moveTo(3.85, interp(FLK, 3.85)); for (let x = 3.85; x <= 4.75; x += 0.03) g.lineTo(x, interp(FLK, x));
    g.lineWidth = 0.045; g.strokeStyle = YEL; g.shadowColor = YEL; g.shadowBlur = 25; g.stroke(); g.restore();
  }
}
function makeLine(x0, x1, yf, vf, step = 0.04) {
  const pts = [], cum = [0];
  for (let x = x0; x <= x1 + 1e-9; x += step) pts.push([x, yf(x)]);
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) / vf((pts[i][0] + pts[i - 1][0]) / 2));
  return { pts, cum, T: cum[cum.length - 1] };
}
function posAt(L, tm) {
  tm = clamp(tm, 0, L.T); let lo = 0, hi = L.cum.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (L.cum[m] <= tm) lo = m; else hi = m; }
  const s = (tm - L.cum[lo]) / Math.max(1e-9, L.cum[hi] - L.cum[lo]);
  return [lerp(L.pts[lo][0], L.pts[hi][0], s), lerp(L.pts[lo][1], L.pts[hi][1], s)];
}
function particles(L, t, n, period, col, w, trail = 0.07, colFn = null) {
  g.lineCap = 'round';
  for (let k = 0; k < n; k++) {
    const u = ((t / period + k / n) % 1 + 1) % 1, tm = u * L.T;
    const a = posAt(L, tm), b = posAt(L, tm - trail * L.T);
    const al = Math.min(1, u * 8, (1 - u) * 8);
    g.globalAlpha = al; g.strokeStyle = colFn ? colFn(a) : col; g.lineWidth = w; line(b[0], b[1], a[0], a[1]);
  }
  g.globalAlpha = 1;
}
const UNDER = [0.28, 0.52, 0.76].map(fr => makeLine(0.4, 6.0, x => fr * interp(FLK, x), x => 1 / interp(FLK, x)));
const OVER = [0.16, 0.38, 0.62].map(off => makeLine(-0.6, 6.2, x => interp(TOPK, x) + off, x => 1.0));
// Esquema lateral completo: auto + piso + flujo. Coordenadas: metros, origen en el suelo.
function sideSchematic(t, o = {}) {
  const lp = o.lowP ?? 0;
  carSide({ lift: 0.10, wheelRot: -t * 9, noFloor: true, rwOpen: o.rwOpen || 0, fwOpen: o.fwOpen || 0 });
  floorSchem(1, o.hlDiff || 0);
  if (lp > 0) {
    g.save(); g.globalAlpha = lp * (0.75 + 0.25 * Math.sin(t * 5));
    g.beginPath(); g.moveTo(1.30, 0); for (let x = 1.30; x <= 4.75; x += 0.05) g.lineTo(x, interp(FLK, x)); g.lineTo(4.75, 0); g.closePath();
    const gr = g.createLinearGradient(0, 0, 0, 0.34); gr.addColorStop(0, 'rgba(40,120,255,0.55)'); gr.addColorStop(1, 'rgba(79,216,255,0.15)'); g.fillStyle = gr; g.fill(); g.restore();
  }
  if (o.flow) {
    for (const L of OVER) particles(L, t, 7, 2.6, 'rgba(255,255,255,0.75)', 0.022, 0.05);
    for (const L of UNDER) particles(L, t, 9, 1.6, CYA, 0.028, 0.06, ([x, y]) => (x > 1.9 && x < 3.9) ? '#9ff0ff' : CYA);
  }
  g.strokeStyle = 'rgba(200,220,255,0.55)'; g.lineWidth = 0.02; line(-0.8, 0, 6.3, 0);
  g.save(); g.setLineDash([0.25, 0.25]); g.lineDashOffset = t * 6; g.strokeStyle = 'rgba(255,255,255,0.25)'; g.lineWidth = 0.02; line(-0.8, -0.06, 6.3, -0.06); g.restore();
}

// ---------------- destellos de marca ----------------
const FLASHES = [SEG.leyendas.t0 - 0.35, SEG.secreto.t0 - 0.3, PT('secreto', 2)[0] - 0.15, 142.65, SEG.final.t1 + 0.1];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
}

// =====================================================================
// ESCENA A: dato extra en el túnel
// =====================================================================
function sceneTunnel(t) {
  drawBG(t, 0.4);
  const th = Math.PI * ease(prog(t, 3.0, 5.0));
  const cx = 540, cy = 930, top = 560, bot = 1300;
  g.save(); g.translate(cx, cy); g.rotate(th); g.translate(-cx, -cy);
  g.fillStyle = '#060a16'; g.fillRect(-1400, -900, 3900, 3800);
  const wg = g.createLinearGradient(0, top, 0, bot); wg.addColorStop(0, '#16224a'); wg.addColorStop(0.5, '#0f1834'); wg.addColorStop(1, '#16224a');
  g.fillStyle = wg; g.fillRect(-1400, top, 3900, bot - top);
  for (let i = -6; i < 16; i++) { const x = ((i * 300 + t * 900) % 4200) - 1400; g.fillStyle = 'rgba(79,216,255,0.06)'; g.fillRect(x, top, 26, bot - top); }
  g.fillStyle = '#1b2440'; g.fillRect(-1400, top - 90, 3900, 90); g.fillStyle = '#121828'; g.fillRect(-1400, bot, 3900, 90);
  for (let i = -6; i < 18; i++) {
    const x = ((i * 260 + t * 1700) % (24 * 260)) - 1400;
    g.save(); g.shadowColor = '#fff6c8'; g.shadowBlur = 30; g.fillStyle = '#fff3c4'; g.fillRect(x, top - 26, 120, 18); g.restore();
    g.fillStyle = 'rgba(255,255,255,0.7)'; g.fillRect(x * 1.0 + 40, bot + 40, 110, 10);
  }
  const k = 165, x0 = cx - 2.67 * k;
  g.save(); g.translate(x0, bot); g.scale(k, -k);
  carSide({ wheelRot: -t * 14 });
  g.restore();
  for (let i = 0; i < 9; i++) { const y = bot - 40 - i * 17, L = 120 + (i * 53) % 160, x = cx + 470 + ((i * 97 + t * 900) % 300); g.strokeStyle = 'rgba(255,255,255,0.35)'; g.lineWidth = 4; line(x, y, x + L, y); }
  const fa = ease(prog(t, 5.0, 6.0));
  if (fa > 0) {
    g.globalAlpha = fa;
    for (const xm of [0.35, 1.9, 3.3, 4.95]) { const X = x0 + xm * k, y1 = bot - 0.98 * k - 10, L = 150 * fa; arrow(X, y1 - L - 20, X, y1, 30, YEL); }
    g.globalAlpha = 1;
  }
  g.restore();
  if (fa > 0) {
    tag('FUERZA DEL AIRE', 540, 940, YEL, 44, fa);
    const ga = ease(prog(t, 6.2, 6.8));
    if (ga > 0) { g.globalAlpha = ga; arrow(250, 700, 250, 830, 28, CYA); g.globalAlpha = 1; tag('PESO', 250, 880, CYA, 40, ga); }
  }
  label(t, 0.1, 9.55, 'DATO EXTRA', ['¿Un F1 en el techo de un túnel?'], YEL, 112);
}

// ESCENA B: velocímetro, peso vs. aire
function sceneSpeed(t) {
  drawBG(t, 0.6);
  const a = PT('dato', 1)[0];
  const v = 200 * easeOut(prog(t, a + 0.2, a + 3.2));
  const gx = 540, gy = 790, R = 250;
  g.save();
  g.lineCap = 'round'; g.lineWidth = 30; g.strokeStyle = 'rgba(79,216,255,0.15)';
  g.beginPath(); g.arc(gx, gy, R, Math.PI * 5 / 6, Math.PI * 13 / 6); g.stroke();
  g.strokeStyle = YEL; g.beginPath(); g.arc(gx, gy, R, Math.PI * 5 / 6, Math.PI * 5 / 6 + (Math.PI * 4 / 3) * v / 300); g.stroke();
  for (let s = 0; s <= 300; s += 50) {
    const an = Math.PI * 5 / 6 + (Math.PI * 4 / 3) * s / 300;
    g.strokeStyle = WHT; g.lineWidth = 6; line(gx + Math.cos(an) * (R - 50), gy + Math.sin(an) * (R - 50), gx + Math.cos(an) * (R - 28), gy + Math.sin(an) * (R - 28));
    txt(String(s), gx + Math.cos(an) * (R - 92), gy + Math.sin(an) * (R - 92), 34, WHT, { font: 'IX', stroke: 4 });
  }
  const an = Math.PI * 5 / 6 + (Math.PI * 4 / 3) * v / 300;
  g.strokeStyle = RED; g.lineWidth = 12; line(gx, gy, gx + Math.cos(an) * (R - 40), gy + Math.sin(an) * (R - 40));
  circle(gx, gy, 22); g.fillStyle = WHT; g.fill();
  g.restore();
  txt(`${Math.round(v)}`, gx, gy + 120, 96, v > 199 ? YEL : WHT, { stroke: 8 });
  txt('KM/H', gx, gy + 190, 40, CYA, { font: 'IX', stroke: 5 });
  const road = 1400, k = 165, x0 = 540 - 2.67 * k;
  g.fillStyle = '#121828'; g.fillRect(0, road, W, 70);
  for (let i = 0; i < 8; i++) { const x = ((i * 220 + t * 1500) % 1760) - 300; g.fillStyle = 'rgba(255,255,255,0.6)'; g.fillRect(x, road + 30, 120, 10); }
  g.save(); g.translate(x0, road); g.scale(k, -k); carSide({ wheelRot: -t * 14 }); g.restore();
  const f = (v / 200) ** 2;
  for (const xm of [0.35, 2.0, 4.95]) { const X = x0 + xm * k, y1 = road - 1.0 * k - 6, L = 40 + 130 * f; g.globalAlpha = Math.min(1, f * 4); arrow(X, y1 - L, X, y1, 26, YEL); g.globalAlpha = 1; }
  const wx = x0 + 2.9 * k; arrow(wx, road - 0.45 * k, wx, road + 40, 26, CYA);
  tag('PESO', wx + 120, road + 10, CYA, 38);
  tag('AIRE', x0 + 1.2 * k, road - 1.0 * k - 120, YEL, 38, Math.min(1, f * 4) * (1 - prog(t, a + 3.0, a + 3.25)));
  if (v > 199) {
    const e = backOut(prog(t, a + 3.2, a + 3.7));
    g.save(); g.translate(540, 1080); g.scale(e, e); tag('AIRE = PESO', 0, 0, YEL, 64); g.restore();
  }
  label(t, a - 0.3, SEG.leyendas.t0 - 0.35, 'A 200 KM/H', ['el aire empuja tanto como pesa'], WHT, 104);
}

// =====================================================================
// LEYENDAS
// =====================================================================
const CARS = [
  { k: 'lotus', name: 'LOTUS 79', sub: '1978 · primer campeón con efecto suelo', wins: null, credit: 'Foto: Martin Lee · CC BY-SA 2.0 · Wikimedia Commons', fx: 0.45, fy: 0.62 },
  { k: 'mp44', name: 'McLAREN MP4/4', sub: '1988 · Senna y Prost', wins: [15, 16], credit: 'Foto: Morio · CC BY-SA 3.0 · Wikimedia Commons', fx: 0.55, fy: 0.55 },
  { k: 'f2004', name: 'FERRARI F2004', sub: '2004 · Michael Schumacher', wins: [15, 18], credit: 'Foto: Rick Dikeman · CC BY-SA 3.0 · Wikimedia Commons', fx: 0.48, fy: 0.55 },
  { k: 'rb19', name: 'RED BULL RB19', sub: '2023 · Max Verstappen', wins: [21, 22], credit: 'Foto: Lukas Raich · CC BY-SA 4.0 · Wikimedia Commons', fx: 0.6, fy: 0.55 },
];
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
function sceneLegends(t) {
  drawBG(t, 0.5);
  const intro = PT('leyendas', 0);
  const slots = [1, 2, 3, 4].map(i => PT('leyendas', i));
  if (t < slots[0][0] - 0.05) {
    label(t, intro[0] - 0.3, slots[0][0] + 0.1, 'LEYENDAS DE LA F1', ['los autos más famosos'], YEL, 100);
    CARS.forEach((c, i) => {
      const e = backOut(prog(t, intro[0] - 0.2 + i * 0.22, intro[0] + 0.35 + i * 0.22));
      if (e <= 0) return;
      const col = i % 2, row = (i / 2) | 0;
      const w = 480, h = 330, x = 50 + col * 500 + w / 2, y = 700 + row * 380 + h / 2;
      g.save(); g.translate(x, y); g.scale(e, e); g.rotate((1 - e) * 0.2 * (col ? 1 : -1));
      photo(IMG[c.k], -w / 2, -h / 2, w, h, 1.15 + 0.03 * (t - intro[0]), c.fx, c.fy, 20, i === 3 ? YEL : 'rgba(255,255,255,0.85)');
      txt(c.name, 0, h / 2 + 44, 40, WHT, { stroke: 5 });
      g.restore();
    });
    return;
  }
  let idx = 0; for (let i = 0; i < 4; i++) if (t >= slots[i][0] - 0.3) idx = i;
  for (let j = Math.max(0, idx - 1); j <= idx; j++) {
    const c = CARS[j], [a, b] = slots[j];
    const inP = easeOut(prog(t, a - 0.3, a + 0.15));
    const outP = j < 3 ? ease(prog(t, slots[j + 1][0] - 0.3, slots[j + 1][0] + 0.15)) : 0;
    const dx = (1 - inP) * 1100 - outP * 1100;
    if (inP <= 0 || outP >= 1) continue;
    g.save(); g.translate(dx, 0);
    const z = 1.06 + 0.05 * prog(t, a - 0.3, b);
    photo(IMG[c.k], 40, 530, 1000, 650, z, c.fx, c.fy);
    txt(c.credit, 540, 1152, 24, 'rgba(255,255,255,0.9)', { font: 'IX', stroke: 4 });
    txt(c.name, 540, 345, 104, YEL, { maxW: 1000, stroke: 8 });
    txt(c.sub, 540, 437, 48, CYA, { font: 'IX', maxW: 1000, stroke: 7 });
    if (c.wins) {
      const [wn, tot] = c.wins, perRow = 11, rows = Math.ceil(tot / perRow);
      for (let i = 0; i < tot; i++) {
        const r = (i / perRow) | 0, inRow = Math.min(perRow, tot - r * perRow), cI = i - r * perRow;
        const x = 540 + (cI - (inRow - 1) / 2) * 86, y = 1270 + r * 86;
        const on = i < wn && t > a + 0.7 + i * 0.13;
        circle(x, y, 32); g.fillStyle = on ? YEL : 'rgba(255,255,255,0.12)'; g.fill(); g.lineWidth = 4; g.strokeStyle = on ? INK : 'rgba(255,255,255,0.4)'; g.stroke();
        if (on) { g.strokeStyle = INK; g.lineWidth = 6; g.lineCap = 'round'; g.beginPath(); g.moveTo(x - 12, y + 1); g.lineTo(x - 3, y + 11); g.lineTo(x + 14, y - 10); g.stroke(); }
      }
      const shown = Math.min(wn, Math.max(0, Math.floor((t - a - 0.7) / 0.13) + 1));
      txt(`${shown} / ${tot} VICTORIAS`, 540, 1270 + rows * 86 + 10, 56, WHT, { stroke: 7 });
      if (j === 3 && shown >= wn) {
        const e = backOut(prog(t, a + 0.75 + wn * 0.13, a + 1.25 + wn * 0.13));
        g.save(); g.translate(860, 640); g.rotate(-0.22); g.scale(e, e);
        g.beginPath(); g.roundRect(-150, -55, 300, 110, 18); g.fillStyle = 'rgba(255,77,94,0.92)'; g.fill(); g.lineWidth = 8; g.strokeStyle = WHT; g.stroke();
        txt('RÉCORD', 0, 4, 66, WHT, { stroke: 0 }); g.restore();
      }
    } else {
      const e = backOut(prog(t, a + 0.8, a + 1.3));
      g.save(); g.translate(540, 1300); g.scale(e, e);
      g.beginPath(); g.roundRect(-330, -62, 660, 124, 62); g.fillStyle = YEL; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
      txt('CAMPEÓN 1978', 0, 4, 64, INK, { stroke: 0 }); g.restore();
      txt('EFECTO SUELO', 540, 1420, 52, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, a + 1.4, a + 1.8)) });
    }
    g.restore();
  }
}

// =====================================================================
// EL SECRETO: avión al revés
// =====================================================================
function plane(x, y, s, flip) {
  g.save(); g.translate(x, y); g.scale(s, s * flip);
  g.fillStyle = '#d9e2f2';
  g.beginPath(); g.moveTo(-300, 10); g.quadraticCurveTo(-320, -18, -270, -24); g.lineTo(240, -24); g.quadraticCurveTo(300, -20, 310, 4); g.quadraticCurveTo(290, 22, 240, 24); g.lineTo(-260, 24); g.closePath(); g.fill();
  g.fillStyle = CYA; g.beginPath(); g.moveTo(-20, 0); g.lineTo(-120, 160); g.lineTo(-60, 160); g.lineTo(90, 0); g.closePath(); g.fill();
  g.beginPath(); g.moveTo(-230, -20); g.lineTo(-290, -120); g.lineTo(-250, -120); g.lineTo(-170, -20); g.closePath(); g.fill();
  g.fillStyle = '#0b1530'; for (let i = 0; i < 9; i++) { g.beginPath(); g.roundRect(-150 + i * 40, -12, 22, 14, 5); g.fill(); }
  g.beginPath(); g.moveTo(250, -16); g.quadraticCurveTo(285, -12, 292, 0); g.lineTo(250, 0); g.closePath(); g.fill();
  g.restore();
}
function flowAround(cx, cy, t, inverted, speedTop, col) {
  const s = inverted ? -1 : 1;
  for (const y0 of [-190, -130, -80, 80, 130, 190]) {
    const above = (y0 < 0) === !inverted;
    g.beginPath();
    for (let x = -520; x <= 520; x += 10) {
      const bump = Math.exp(-(((x + 30) / 190) ** 2));
      const amp = (above ? 62 : 28) * Math.exp(-(Math.abs(y0) - 80) / 160);
      const wash = 40 * clamp((x - 120) / 360) ** 1.3 * Math.exp(-(Math.abs(y0) - 80) / 260);
      const y = cy + y0 + (y0 < 0 ? -amp : amp) * bump + s * wash;
      if (x === -520) g.moveTo(cx + x, y); else g.lineTo(cx + x, y);
    }
    g.save(); g.setLineDash([26, 18]); g.lineDashOffset = -t * (above ? speedTop : speedTop * 0.6); g.lineWidth = 5; g.strokeStyle = col; g.globalAlpha = 0.8; g.stroke(); g.restore();
  }
}
function sceneSecret(t) {
  drawBG(t, 0.5);
  const [a0, b0] = PT('secreto', 0), [a1, b1] = PT('secreto', 1);
  if (t < a0 + 2.5) {
    const e = easeOut(prog(t, a0 - 0.3, a0 + 0.4)), out = ease(prog(t, a0 + 2.2, a0 + 2.5));
    g.save(); g.globalAlpha = 1 - out; g.translate(540, 860); g.scale(0.9 + 0.1 * e, 0.9 + 0.1 * e);
    photo(IMG.render, -500, -290, 1000, 580, 1.0 + 0.04 * prog(t, a0, a0 + 2.5), 0.5, 0.55);
    txt('Ilustración', 420, 260, 24, 'rgba(255,255,255,0.8)', { font: 'IX', stroke: 3 });
    g.restore();
  } else if (t < a1 - 0.2) {
    const fl = Math.cos(Math.PI * ease(prog(t, a0 + 2.9, a0 + 4.0)));
    const e = easeOut(prog(t, a0 + 2.4, a0 + 2.8));
    plane(540, 880, 1.25 * e, fl);
    const up = fl > 0;
    arrow(540, 880 + (up ? -70 : 70), 540, 880 + (up ? -300 : 300), 40, up ? CYA : YEL);
    tag(up ? 'LO LEVANTA' : 'LO HUNDE', 540, up ? 1130 : 640, up ? CYA : YEL, 52, e * Math.min(1, Math.abs(fl) * 2));
  } else {
    const ea = easeOut(prog(t, a1 - 0.2, a1 + 0.4)), eb = easeOut(prog(t, a1 + 2.0, a1 + 2.6));
    if (ea > 0) {
      g.save(); g.globalAlpha = ea;
      flowAround(540, 700, t, false, 260, 'rgba(79,216,255,0.9)');
      airfoil(330, 700, 420, 4, 0.14, 0.07, true, '#d9e2f2', INK, 6);
      arrow(560, 650, 560, 470, 38, CYA); tag('AVIÓN', 220, 520, CYA, 50);
      g.restore();
    }
    if (eb > 0) {
      g.save(); g.globalAlpha = eb;
      flowAround(540, 1230, t, true, 260, 'rgba(255,216,77,0.9)');
      airfoil(330, 1230, 420, -4, 0.14, 0.07, false, BODY_L, YEL, 6);
      arrow(560, 1280, 560, 1460, 38, YEL); tag('FÓRMULA 1', 230, 1440, YEL, 50);
      g.restore();
    }
  }
  label(t, a0 - 0.3, b0 + 0.2, 'EL SECRETO', ['es un avión... ¡al revés!'], YEL, 112);
  label(t, a1 - 0.1, b1 + 0.25, 'ALAS INVERTIDAS', ['el avión sube · el F1 se pega'], WHT, 100);
}

// =====================================================================
// DESARMADO
// =====================================================================
const D0 = PT('secreto', 2)[0] - 0.15;      // aparece el auto armado
const EX0 = D0 + 1.35;                     // empieza a desarmarse
const RE0 = SEG.final.t0 + 0.05;           // empieza a armarse otra vez
const FOCUS = [1, 2, 3, 4, 5, 6, 7, 8].map(n => ({ n, a: SEG[FOCUS_SEG[n]].t0, b: SEG[FOCUS_SEG[n]].t1, r: NUM_CELL[n][0], c: NUM_CELL[n][1] }));
const OV = { cx: 540, cy: 930, z: 1, sy: 930 };
function focusState(f) { return { cx: COLX[f.c], cy: ROWY[f.r], z: 2.7, sy: f.n === 4 ? 840 : 905 }; }
function mixCam(A, B, s, bump) { const z = lerp(A.z, B.z, s) * (1 - bump * Math.sin(Math.PI * s)); return { cx: lerp(A.cx, B.cx, s), cy: lerp(A.cy, B.cy, s), z, sy: lerp(A.sy, B.sy, s) }; }
function camAt(t) {
  const f0 = FOCUS[0];
  if (t < f0.a - 0.5) return OV;
  if (t < f0.a + 0.25) return mixCam(OV, focusState(f0), ease(prog(t, f0.a - 0.5, f0.a + 0.25)), 0);
  for (let i = 0; i < 8; i++) {
    const f = FOCUS[i], nx = FOCUS[i + 1];
    if (!nx) {
      if (t < f.b - 0.05) return focusState(f);
      return mixCam(focusState(f), OV, ease(prog(t, f.b - 0.05, f.b + 0.55)), 0);
    }
    const t0 = f.b - 0.2, t1 = nx.a + 0.25;
    if (t < t0) return focusState(f);
    if (t < t1) return mixCam(focusState(f), focusState(nx), ease(prog(t, t0, t1)), 0.33);
  }
  return OV;
}
const g2s = (cam, gx, gy) => [540 + (gx - cam.cx) * cam.z, cam.sy + (gy - cam.cy) * cam.z];
function focusAmt(t, n) { const f = FOCUS[n - 1]; return fade(t, f.a - 0.35, f.b + 0.1, 0.4); }
function specAmt(t, n) { const f = FOCUS[n - 1]; return fade(t, f.a + 0.05, f.b - 0.02, 0.4); }
function explodeAmt(t, i) { return ease(prog(t, EX0 + i * 0.07, EX0 + i * 0.07 + 0.95)) - ease(prog(t, RE0 + 0.45 + i * 0.06, RE0 + 1.4 + i * 0.06)); }

let TAGS = [];
function sceneDisassembly(t) {
  drawBG(t, 1);
  const cam = camAt(t);
  const appear = easeOut(prog(t, D0 - 0.1, D0 + 0.5));
  const anyFocus = Math.max(...FOCUS.map(f => focusAmt(t, f.n)));
  const tilesA = Math.min(explodeAmt(t, 0), 1);
  // celdas
  if (tilesA > 0) {
    for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
      const [x, y] = g2s(cam, COLX[c], ROWY[r]); const s = CS * cam.z;
      g.save(); g.globalAlpha = tilesA * (1 - 0.6 * anyFocus);
      g.beginPath(); g.roundRect(x - s / 2, y - s / 2, s, s, 22 * cam.z); g.fillStyle = 'rgba(79,216,255,0.05)'; g.fill(); g.lineWidth = 2 * cam.z; g.strokeStyle = 'rgba(79,216,255,0.28)'; g.stroke();
      g.restore();
    }
  }
  // piezas
  ORDER.forEach((k, i) => {
    const p = PARTS[k];
    const e = explodeAmt(t, i);
    const Xa = 540 + p.c[0] * A_SCALE, Ya = A_Y + (p.c[1] - A_CY) * A_SCALE;
    const gx = COLX[p.cell[1]] + (p.off ? p.off[0] : 0), gy = ROWY[p.cell[0]] + (p.off ? p.off[1] : 0);
    const [Xg, Yg] = g2s(cam, gx, gy);
    const X = lerp(Xa, Xg, e), Y = lerp(Ya, Yg, e) - 70 * Math.sin(Math.PI * e) * (p.c[1] < 2.5 ? 1 : -1) * 0.5;
    const S = lerp(A_SCALE, p.s * cam.z, e) * (1 + 0.1 * Math.sin(Math.PI * e)) * (0.85 + 0.15 * appear);
    const n = p.num; const fa = n ? focusAmt(t, n) : 0;
    let al = appear * (p.hidden ? clamp(e * 2.5) : 1);
    al *= 1 - 0.78 * Math.max(0, anyFocus - fa);
    const sideSwitch = { 2: 1, 5: 1, 6: 1, 7: 1, 8: 1 }[n] ? specAmt(t, n) : 0;
    al *= 1 - sideSwitch;
    if (al <= 0.003) return;
    g.save(); g.globalAlpha = al; g.translate(X, Y); g.scale(S, S); g.translate(-p.c[0], -p.c[1]);
    if (fa > 0) { g.shadowColor = YEL; g.shadowBlur = 34 * fa; }
    if (k === 'chassis') topChassis(1 - clamp(e * 3)); else p.draw();
    g.restore();
  });
  // números en cada celda
  if (tilesA > 0) {
    for (let n = 1; n <= 8; n++) {
      const [r, c] = NUM_CELL[n]; const [x, y] = g2s(cam, COLX[c] - 134, ROWY[r] - 134);
      const e = backOut(prog(t, EX0 + 0.8 + n * 0.08, EX0 + 1.2 + n * 0.08)) * clamp(explodeAmt(t, 11) * 1.2);
      if (e <= 0) continue;
      g.save(); g.globalAlpha = (1 - 0.7 * Math.max(0, anyFocus - focusAmt(t, n))) * (1 - focusAmt(t, n)); g.translate(x, y); g.scale(e * Math.min(cam.z, 1.6), e * Math.min(cam.z, 1.6));
      circle(0, 0, 25); g.fillStyle = YEL; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke(); txt(String(n), 0, 2, 32, INK, { stroke: 0 }); g.restore();
    }
  }
  // contenido especial de cada pieza
  TAGS = [];
  for (const f of FOCUS) {
    const sv = specAmt(t, f.n); if (sv <= 0) continue;
    const [x, y] = g2s(cam, COLX[f.c], ROWY[f.r]);
    g.save(); g.translate(x, y); g.scale(cam.z, cam.z); g.globalAlpha = sv;
    g.beginPath(); g.roundRect(-197, -160, 394, 345, 24); g.clip();
    SPEC[f.n](t, sv, f);
    g.restore();
    for (const tg of TAGS) { const [X, Y] = [x + tg.u[0] * cam.z, y + tg.u[1] * cam.z]; tag(tg.text, X, Y, tg.col, tg.size || 40, sv * (tg.a ?? 1)); }
    TAGS = [];
    if (SCREEN[f.n]) SCREEN[f.n](t, sv, f);
  }
  // títulos
  label(t, D0 - 0.1, EX0 + 0.6, 'VAMOS A DESARMARLO', ['pieza por pieza'], YEL, 100);
  label(t, EX0 + 0.9, FOCUS[0].a - 0.35, '8 PIEZAS CLAVE', [], WHT, 96);
  const TITLES = {
    1: ['ALERÓN DELANTERO', 'aleja el aire de las llantas'], 2: ['HALO', 'titanio · ~7 kg · aguanta ~12 t'], 3: ['PONTONES', 'radiadores + guían el aire'],
    4: ['UNIDAD DE POTENCIA', 'V6 turbo 1.6 L + motor eléctrico'], 5: ['PISO', 'túneles que aceleran el aire'], 6: ['DIFUSOR', 'la salida del piso'],
    7: ['ALERÓN TRASERO', 'cerrado en curvas · abierto en rectas'], 8: ['LLANTAS', '18 pulgadas · único contacto con la pista'],
  };
  for (const f of FOCUS) {
    let sub = TITLES[f.n][1];
    if (f.n === 4 && t > PT('motor', 1)[0] - 0.2) sub = 'más de 1,000 caballos';
    if (f.n === 5 && t > PT('piso', 1)[0] - 0.2) sub = '¡esto es el efecto suelo!';
    if (f.n === 7 && t > PT('alerontras', 1)[0] - 0.2) sub = '2026: aerodinámica activa';
    label(t, f.a - 0.25, f.b + 0.05, TITLES[f.n][0], [sub], WHT, 92, f.n);
  }
}

// ----- contenido especial (unidades de celda: 330 = una celda; origen en el centro) -----
function flowPath(pts, t, speed, col, w = 4, dash = [16, 12]) {
  g.save(); g.setLineDash(dash); g.lineDashOffset = -t * speed; g.lineWidth = w; g.strokeStyle = col; g.lineCap = 'round'; smooth(pts, false); g.stroke(); g.restore();
}
const SPEC = {};
const SCREEN = {};
SPEC[1] = (t, a) => {   // alerón delantero (vista superior, escala de la pieza)
  const s = PARTS.fw.s;
  g.save(); g.setLineDash([6, 6]); g.lineWidth = 2.5; g.strokeStyle = 'rgba(255,255,255,0.6)';
  for (const sx of [-1, 1]) { g.beginPath(); g.roundRect(sx * 0.80 * s - 0.15 * s, 0.76 * s - 0.36 * s, 0.30 * s, 0.72 * s, 12); g.stroke(); }
  g.beginPath(); g.moveTo(-0.12 * s, -0.17 * s); g.lineTo(-0.2 * s, 1.1 * s); g.moveTo(0.12 * s, -0.17 * s); g.lineTo(0.2 * s, 1.1 * s); g.stroke();
  g.restore();
  for (const x0 of [-150, -118, -86, -54, 54, 86, 118, 150]) {
    const pts = []; const out = Math.abs(x0) > 70 ? 95 : 55;
    for (let y = -190; y <= 200; y += 20) { const d = Math.sign(x0) * out * ease((y + 10) / 150); pts.push([x0 + d, y]); }
    flowPath(pts, t, 150, 'rgba(79,216,255,0.95)', 4.5);
  }
  TAGS.push({ u: [0, -150], text: 'AIRE', col: CYA }, { u: [-120, 175], text: 'LLANTA', col: WHT, size: 34 }, { u: [120, 175], text: 'LLANTA', col: WHT, size: 34 });
  TAGS.push({ u: [0, 60], text: 'EMPUJA HACIA ABAJO', col: YEL, size: 36, a: ease(prog(t, FOCUS[0].a + 1.2, FOCUS[0].a + 1.6)) });
};
function bus(x, y, w) {
  const h = w * 0.58;
  g.save(); g.translate(x, y);
  g.beginPath(); g.roundRect(-w / 2, -h, w, h * 0.92, 10); g.fillStyle = '#d8394a'; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
  g.fillStyle = '#bfe7ff';
  for (let r = 0; r < 2; r++) for (let i = 0; i < 6; i++) { g.beginPath(); g.roundRect(-w / 2 + 12 + i * (w - 24) / 6, -h + 12 + r * h * 0.42, (w - 24) / 6 - 8, h * 0.26, 4); g.fill(); }
  g.fillStyle = '#111'; for (const s of [-1, 1]) { circle(s * w * 0.3, -h * 0.08, h * 0.13); g.fill(); }
  g.restore();
}
SPEC[2] = (t, a, f) => {   // halo: vista lateral con un autobús encima
  g.save(); g.translate(0, 70); g.scale(0.78, 0.78);
  g.fillStyle = BODY; g.beginPath(); g.moveTo(-170, 80); g.lineTo(-120, 45); g.lineTo(150, 45); g.lineTo(175, 80); g.lineTo(175, 160); g.lineTo(-170, 160); g.closePath(); g.fill();
  g.lineWidth = 2.5; g.strokeStyle = 'rgba(140,200,255,0.6)'; g.stroke();
  const hg = g.createRadialGradient(10, 0, 4, 20, 10, 46); hg.addColorStop(0, '#fff'); hg.addColorStop(1, '#a9b4cc');
  circle(20, 12, 44); g.fillStyle = hg; g.fill(); g.save(); circle(20, 12, 44); g.clip(); g.fillStyle = YEL; g.fillRect(-30, -22, 100, 16); g.fillStyle = '#0a0f1e'; g.fillRect(-30, 6, 46, 15); g.restore();
  g.lineCap = 'round'; g.beginPath(); g.moveTo(-118, 46); g.quadraticCurveTo(-100, -38, -10, -46); g.lineTo(110, -38); g.lineTo(122, 44);
  g.lineWidth = 22; g.strokeStyle = INK; g.stroke(); g.lineWidth = 15; g.strokeStyle = TI; g.stroke(); g.lineWidth = 4; g.strokeStyle = '#fff'; g.stroke();
  const land = f.a + 1.9;
  const yb = lerp(-470, -58, easeOut(prog(t, f.a + 1.0, land)));
  const sq = t > land ? 1 - 0.06 * Math.exp(-(t - land) * 9) * Math.cos((t - land) * 40) : 1;
  g.save(); g.translate(0, yb); g.scale(1, sq); bus(0, 0, 300); g.restore();
  if (t > land) { const k = prog(t, land, land + 0.4); g.strokeStyle = `rgba(255,216,77,${1 - k})`; g.lineWidth = 4; for (const s of [-1, 1]) line(s * 120, -50, s * (150 + 60 * k), -60 - 30 * k); }
  g.restore();
  TAGS.push({ u: [0, -128], text: '≈ 12 TONELADAS', col: YEL, size: 46, a: ease(prog(t, land, land + 0.3)) });
  TAGS.push({ u: [-100, 150], text: 'HALO ≈ 7 KG', col: CYA, size: 38, a: ease(prog(t, f.a + 0.4, f.a + 0.8)) });
};
SPEC[3] = (t, a, f) => {   // pontones: radiadores y flujo
  const s = PARTS.pods.s, cy = PARTS.pods.c[1];
  const Y = y => (y - cy) * s;
  for (const sx of [-1, 1]) {
    const x0 = sx * 0.36 * s, x1 = sx * 0.60 * s;
    const glow = 0.55 + 0.25 * Math.sin(t * 6);
    g.fillStyle = `rgba(255,138,61,${0.35 * glow})`; g.fillRect(Math.min(x0, x1), Y(2.15), Math.abs(x1 - x0), Y(2.85) - Y(2.15));
    g.strokeStyle = ORA; g.lineWidth = 2; g.strokeRect(Math.min(x0, x1), Y(2.15), Math.abs(x1 - x0), Y(2.85) - Y(2.15));
    for (let i = 1; i < 6; i++) { const x = lerp(x0, x1, i / 6); line(x, Y(2.15), x, Y(2.85)); }
    for (let k = 0; k < 7; k++) {
      const u = ((t / 1.6 + k / 7) % 1), yy = lerp(-200, 140, u), xx = sx * lerp(0.47 * s, 0.38 * s, ease((yy - Y(2.9)) / 120));
      const hot = yy > Y(2.3);
      g.strokeStyle = hot ? ORA : CYA; g.lineWidth = 5; g.lineCap = 'round'; g.globalAlpha = a * Math.min(1, u * 6, (1 - u) * 6); line(xx, yy - 22, xx, yy); g.globalAlpha = a;
    }
    const pts = []; for (let yy = -190; yy <= 190; yy += 20) pts.push([sx * (0.78 * s - 50 * ease((yy + 20) / 200)), yy]);
    flowPath(pts, t, 130, 'rgba(79,216,255,0.9)', 4);
  }
  TAGS.push({ u: [0, Y(2.5) - 0], text: 'RADIADORES', col: ORA, size: 34, a: ease(prog(t, f.a + 0.6, f.a + 1.0)) });
  TAGS.push({ u: [0, 175], text: 'EL AIRE SIGUE HACIA ATRÁS', col: CYA, size: 32, a: ease(prog(t, f.a + 3.4, f.a + 3.8)) });
};
SPEC[4] = (t, a, f) => {   // unidad de potencia
  const s = PARTS.motor.s, cy = PARTS.motor.c[1];
  const p2 = PT('motor', 1)[0];
  g.save(); g.scale(s, s); g.translate(0, -cy);
  for (let k = 0; k < 6; k++) {
    const u = ((t / 0.9 + k / 6) % 1); const x = lerp(0.0, 0.33, u), y = lerp(2.80, 3.12, u);
    circle(x, y, 0.02); g.fillStyle = CYA; g.globalAlpha = a * Math.min(1, u * 5, (1 - u) * 5); g.fill();
  }
  g.globalAlpha = a; g.restore();
  const k1 = 1 - ease(prog(t, p2 - 0.3, p2 + 0.2));
  TAGS.push({ u: [-80, 0], text: 'V6 TURBO 1.6 L', col: WHT, size: 34, a: k1 * ease(prog(t, f.a + 1.0, f.a + 1.4)) });
  TAGS.push({ u: [100, -60], text: 'MOTOR ELÉCTRICO', col: CYA, size: 32, a: k1 * ease(prog(t, f.a + 3.6, f.a + 4.0)) });
  TAGS.push({ u: [-120, -116], text: 'BATERÍA', col: CYA, size: 30, a: k1 * ease(prog(t, f.a + 4.0, f.a + 4.4)) });
  TAGS.push({ u: [0, 125], text: 'TURBO', col: WHT, size: 30, a: k1 * ease(prog(t, f.a + 1.6, f.a + 2.0)) });
};
SCREEN[4] = (t, sv, f) => {
  const p2 = PT('motor', 1)[0];
  const e = easeOut(prog(t, p2 - 0.2, p2 + 0.4)) * sv; if (e <= 0) return;
  g.save(); g.globalAlpha = e;
  const y = 1345, w = 920, x0 = 540 - w / 2, fill = ease(prog(t, p2 + 0.2, p2 + 1.6)), split = 0.53;
  txt('MÁS DE 1,000 HP', 540, y - 95, 84, YEL, { stroke: 8 });
  g.beginPath(); g.roundRect(x0, y - 32, w, 64, 32); g.fillStyle = 'rgba(255,255,255,0.12)'; g.fill();
  g.save(); g.beginPath(); g.roundRect(x0, y - 32, w, 64, 32); g.clip();
  g.fillStyle = ORA; g.fillRect(x0, y - 32, w * split * Math.min(1, fill / split), 64);
  if (fill > split) { g.fillStyle = CYA; g.fillRect(x0 + w * split, y - 32, w * (fill - split), 64); }
  g.restore();
  g.lineWidth = 5; g.strokeStyle = INK; g.beginPath(); g.roundRect(x0, y - 32, w, 64, 32); g.stroke();
  txt('COMBUSTIÓN ≈ 540', x0 + w * split / 2, y + 72, 38, ORA, { font: 'IX', stroke: 5, alpha: ease(prog(t, p2 + 0.6, p2 + 1.0)) });
  txt('ELÉCTRICO ≈ 470', x0 + w * split + w * (1 - split) / 2, y + 72, 38, CYA, { font: 'IX', stroke: 5, alpha: ease(prog(t, p2 + 1.4, p2 + 1.8)) });
  g.restore();
};
function schem(t, x0m, k, gy, opts) {   // dibuja el esquema lateral con escala k (unidades por metro)
  g.save(); g.translate(-x0m * k, gy); g.scale(k, -k); sideSchematic(t, opts); g.restore();
}
SPEC[5] = (t, a, f) => {   // piso: efecto suelo
  const p2 = PT('piso', 1)[0];
  const k = 68, gy = 90;
  schem(t, 2.67, k, gy, { flow: true, lowP: ease(prog(t, p2 - 0.4, p2 + 0.4)) });
  const ea = ease(prog(t, p2 + 1.6, p2 + 2.4));
  if (ea > 0) for (const xm of [1.6, 2.8, 4.0]) { const X = (xm - 2.67) * k, yTop = gy - (interp(TOPK, xm) + 0.12) * k; const L = 70 * ea * (0.85 + 0.15 * Math.sin(t * 8 + xm)); arrow(X, yTop - L - 14, X, yTop - 4, 16, YEL); }
  TAGS.push({ u: [0, gy + 38], text: 'AIRE RÁPIDO', col: CYA, size: 36, a: ease(prog(t, f.a + 1.4, f.a + 1.8)) });
  TAGS.push({ u: [-95, gy + 82], text: 'BAJA PRESIÓN', col: '#8fb8ff', size: 34, a: ease(prog(t, p2 - 0.2, p2 + 0.3)) });
  TAGS.push({ u: [0, -150], text: 'SUCCIÓN', col: YEL, size: 44, a: ea });
};
SPEC[6] = (t, a, f) => {   // difusor
  const k = 150, gy = 70;
  schem(t, 4.3, k, gy, { flow: true, lowP: 0.7, hlDiff: ease(prog(t, f.a + 0.6, f.a + 1.2)) });
  const ea = ease(prog(t, f.a + 4.0, f.a + 4.8));
  if (ea > 0) for (const xm of [3.7, 4.4]) { const X = (xm - 4.3) * k, yTop = gy - (interp(TOPK, xm) + 0.12) * k; arrow(X, yTop - 80 * ea - 10, X, yTop, 16, YEL); }
  TAGS.push({ u: [70, gy + 45], text: 'DIFUSOR', col: YEL, size: 38, a: ease(prog(t, f.a + 0.8, f.a + 1.2)) });
  TAGS.push({ u: [-60, -140], text: 'MÁS SUCCIÓN', col: YEL, size: 40, a: ea });
};
SPEC[7] = (t, a, f) => {   // alerón trasero: perfil y aerodinámica activa
  const p2 = PT('alerontras', 1)[0];
  const showA = 1 - ease(prog(t, p2 - 0.35, p2 + 0.1));
  const openA = ease(prog(t, f.a + 4.9, f.a + 5.5));
  if (showA > 0) {
    g.save(); g.globalAlpha = a * showA;
    g.fillStyle = 'rgba(255,216,77,0.10)'; g.strokeStyle = 'rgba(255,216,77,0.5)'; g.lineWidth = 2; g.beginPath(); g.roundRect(-165, -150, 330, 290, 18); g.fill(); g.stroke();
    for (const y0 of [-120, -75, 30, 70, 110]) {
      const pts = []; for (let x = -190; x <= 190; x += 15) { const b = Math.exp(-(((x + 10) / 90) ** 2)); const up = (1 - openA * 0.75) * 45 * clamp((x - 20) / 150); pts.push([x, y0 + (y0 < 0 ? -18 : 14) * b - up]); }
      flowPath(pts, t, lerp(120, 220, openA), 'rgba(79,216,255,0.9)', 4);
    }
    airfoil(-120, -20, 170, -8, 0.12, 0.06, false, BODY_L, 'rgba(160,210,255,0.9)', 3);
    airfoil(40, -40, 95, lerp(-42, -8, openA), 0.12, 0.06, false, BODY_L, YEL, 3.5);
    const L = lerp(120, 40, openA);
    arrow(-20, 30, -20, 30 + L, 20, YEL);
    g.restore();
    TAGS.push({ u: [0, 162], text: openA > 0.5 ? 'RECTA: ABIERTO · MÁS VELOCIDAD' : 'CURVA: CERRADO · MÁS AGARRE', col: openA > 0.5 ? CYA : YEL, size: 32, a: showA * ease(prog(t, f.a + 1.8, f.a + 2.2)) });
  }
  const sb = ease(prog(t, p2 - 0.2, p2 + 0.3));
  if (sb > 0) {
    const cyc = (Math.sin((t - p2) * Math.PI / 1.1) + 1) / 2;
    g.save(); g.globalAlpha = a * sb; g.translate(-2.67 * 62, 70); g.scale(62, -62);
    carSide({ wheelRot: -t * 9, rwOpen: cyc, fwOpen: cyc }); g.restore();
    for (const xm of [0.4, 5.1]) { g.save(); g.globalAlpha = a * sb; g.strokeStyle = YEL; g.lineWidth = 3; circle((xm - 2.67) * 62, 70 - (xm < 1 ? 0.15 : 0.88) * 62, 26 + 4 * Math.sin(t * 6)); g.stroke(); g.restore(); }
    TAGS.push({ u: [0, -110], text: cyc > 0.5 ? 'MODO RECTA' : 'MODO CURVA', col: cyc > 0.5 ? CYA : YEL, size: 40, a: sb });
  }
};
SPEC[8] = (t, a, f) => {   // llantas
  g.save();
  const R = 100, cy = 0;
  g.strokeStyle = 'rgba(200,220,255,0.6)'; g.lineWidth = 3; line(-197, cy + R, 197, cy + R);
  g.save(); g.setLineDash([30, 26]); g.lineDashOffset = t * 260; g.strokeStyle = 'rgba(255,255,255,0.35)'; line(-197, cy + R + 14, 197, cy + R + 14); g.restore();
  g.save(); g.scale(R / 0.36, R / 0.36); wheelSide(0, cy * 0.36 / R, -t * 8); g.restore();
  const pg = 0.7 + 0.3 * Math.sin(t * 7);
  g.fillStyle = `rgba(255,216,77,${0.55 * pg})`; g.beginPath(); g.ellipse(0, cy + R, 70, 10, 0, 0, Math.PI * 2); g.fill();
  const rr = R * 0.2286 / 0.36 * 0.98;
  const ed = ease(prog(t, f.a + 1.0, f.a + 1.6));
  if (ed > 0) { g.globalAlpha = a * ed; g.strokeStyle = WHT; g.lineWidth = 4; line(-rr, cy, rr, cy); arrow(0, cy, -rr, cy, 6, WHT, 2.4); arrow(0, cy, rr, cy, 6, WHT, 2.4); g.globalAlpha = a; }
  const ea = ease(prog(t, f.a + 4.2, f.a + 5.0));
  if (ea > 0) for (const x of [-60, 0, 60]) { const L = 34 * ea; arrow(x, cy - R - L - 12, x, cy - R - 8, 14, YEL); }
  g.restore();
  TAGS.push({ u: [0, cy - 36], text: '18 PULGADAS', col: WHT, size: 36, a: ed });
  TAGS.push({ u: [0, cy + R + 42], text: 'ÚNICO CONTACTO', col: YEL, size: 34, a: ease(prog(t, f.a + 2.2, f.a + 2.6)) });
  TAGS.push({ u: [0, 172], text: 'EL AIRE LAS EMPUJA', col: YEL, size: 36, a: ea });
};

// =====================================================================
// FINAL
// =====================================================================
function sceneWing(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('final', 0);
  const k = 185, gy = 1180;
  g.save(); g.translate(540 - 2.67 * k, gy); g.scale(k, -k); sideSchematic(t, { flow: true, lowP: 0.6 }); g.restore();
  const ea = ease(prog(t, 143.6, 144.4));
  for (const xm of [0.4, 1.6, 2.8, 4.0, 5.0]) { const X = 540 + (xm - 2.67) * k, yTop = gy - (interp(TOPK, xm) + 0.14) * k; const L = 160 * ea * (0.85 + 0.15 * Math.sin(t * 7 + xm)); if (ea > 0) arrow(X, yTop - L - 20, X, yTop - 6, 30, YEL); }
  label(t, 142.75, PT('final', 1)[0] - 0.3, 'UN ALA AL REVÉS', ['cada pieza trabaja con el aire'], YEL, 108);
}
function sceneCurve(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('final', 1);
  const cx = 1240, cy = 1000, R = 720, tw = 250;
  g.save();
  g.lineWidth = tw + 40; g.strokeStyle = 'rgba(255,255,255,0.08)'; g.beginPath(); g.arc(cx, cy, R, Math.PI * 0.70, Math.PI * 1.30); g.stroke();
  g.lineWidth = tw; g.strokeStyle = '#1d2333'; g.beginPath(); g.arc(cx, cy, R, Math.PI * 0.69, Math.PI * 1.31); g.stroke();
  g.lineWidth = 6; g.strokeStyle = 'rgba(255,255,255,0.75)'; g.beginPath(); g.arc(cx, cy, R + tw / 2 - 8, Math.PI * 0.69, Math.PI * 1.31); g.stroke();
  const ri = R - tw / 2 + 12;
  for (let i = 0; i < 36; i++) { const a0 = Math.PI * 0.69 + i * (Math.PI * 0.62 / 36); g.lineWidth = 22; g.strokeStyle = i % 2 ? RED : WHT; g.beginPath(); g.arc(cx, cy, ri, a0, a0 + Math.PI * 0.62 / 36); g.stroke(); }
  g.restore();
  const u = prog(t, a - 0.4, b + 0.3);
  const ang = Math.PI * lerp(1.25, 0.75, u);
  const x = cx + Math.cos(ang) * R, y = cy + Math.sin(ang) * R;
  for (let i = 1; i <= 4; i++) {
    const ph = ((t * 1.6 + i / 4) % 1);
    g.strokeStyle = `rgba(255,216,77,${0.85 * (1 - ph)})`; g.lineWidth = 7; circle(x, y, 90 + ph * 240); g.stroke();
  }
  for (let i = 0; i < 6; i++) { const da = 0.035 + i * 0.03; const xa = cx + Math.cos(ang + da) * (R + (i - 2.5) * 22), ya = cy + Math.sin(ang + da) * (R + (i - 2.5) * 22); const xb = cx + Math.cos(ang + da + 0.1) * (R + (i - 2.5) * 22), yb = cy + Math.sin(ang + da + 0.1) * (R + (i - 2.5) * 22); g.strokeStyle = 'rgba(255,255,255,0.4)'; g.lineWidth = 4; line(xa, ya, xb, yb); }
  drawCarTopAt(x, y, 66, ang, A_CY, 1);
  const s1 = PT('final', 1)[0];
  label(t, s1 - 0.2, s1 + 4.7, 'EN CADA CURVA', ['el aire lo pega a la pista'], WHT, 104);
  label(t, s1 + 4.8, b + 0.12, 'NO ES MAGIA', ['¡es el AIRE!'], YEL, 120);
}
function sceneEnd(t) {
  drawBG(t, 0.7);
  const e = backOut(prog(t, FLASHES[4], FLASHES[4] + 0.5));
  g.save(); g.translate(540, 830); g.scale(e, e);
  g.shadowColor = YEL; g.shadowBlur = 60; bolt(0, 0, 330); g.fillStyle = YEL; g.fill(); g.lineWidth = 10; g.strokeStyle = INK; g.stroke(); g.restore();
  txt('FLASH DATOS', 540, 1090, 112, WHT, { stroke: 9, alpha: ease(prog(t, FLASHES[4] + 0.15, FLASHES[4] + 0.5)) });
  txt('Síguenos para más datos', 540, 1200, 54, CYA, { font: 'IX', stroke: 6, alpha: ease(prog(t, FLASHES[4] + 0.3, FLASHES[4] + 0.7)) });
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
  const L0 = FLASHES[0], S0 = FLASHES[1], E0 = FLASHES[4];
  if (t < L0) crossfade(t, PT('dato', 1)[0] - 0.55, PT('dato', 1)[0] - 0.1, sceneTunnel, sceneSpeed);
  else if (t < S0) sceneLegends(t);
  else if (t < D0) sceneSecret(t);
  else if (t < 142.65) sceneDisassembly(t);
  else if (t < E0) crossfade(t, PT('final', 1)[0] - 0.45, PT('final', 1)[0] + 0.05, sceneWing, sceneCurve);
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
