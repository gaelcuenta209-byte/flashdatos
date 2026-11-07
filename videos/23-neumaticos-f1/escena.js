// Flash Datos · video 23 · Neumáticos de F1: blandos, medios y duros
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

// =====================================================================
// Video 23 · escenas
// =====================================================================
const SOFT = '#ff3b3b', MEDC = '#ffd23f', HARD = '#f4f6fb', PUR = '#b67cff', GREY = '#8b93a7';
const TCOL = { S: SOFT, M: MEDC, H: HARD };
const at = (p, f) => p[0] + (p[1] - p[0]) * f;
const P = id => SEG[id].parts;
const [G0, G1] = P('gancho'), [T0, T1] = P('tipos');
const [B0, B1, B2, B3, B4] = P('blandos'), [M0, M1, M2, M3] = P('medios'), [D0, D1, D2] = P('duros');
const [C0, C1, C2, C3] = P('compuestos'), [E0, E1, E2] = P('estrategia'), [F0, F1, F2, F3] = P('final');
const FLASHES = [T0[0] - 0.3, B0[0] - 0.3, M0[0] - 0.3, D0[0] - 0.3, C0[0] - 0.3, E0[0] - 0.3, F0[0] - 0.3, F3[1] + 0.1];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
}
function glow(x, y, r, col, a = 1) {
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a;
  const gr = g.createRadialGradient(x, y, 0, x, y, r);
  gr.addColorStop(0, col); gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr; g.globalCompositeOperation = 'lighter'; g.globalAlpha *= 0.35; g.fillRect(x - r, y - r, 2 * r, 2 * r);
  g.restore();
}
function hash(i, j, k) { let h = (i * 374761393 + j * 668265263 + k * 2246822519) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295; }
function rgba(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }

// ---------------- neumático en 3D (cilindro con perspectiva) ----------------
function tyre(cx, cy, R, col, rot = 0, yaw = 0.5, o = {}) {
  const cs = Math.cos(yaw), sn = Math.sin(yaw);
  const tw = R * (o.width ?? 0.66), dx = tw * sn;
  g.save(); g.globalAlpha *= (o.alpha ?? 1);
  if (o.shadow !== false) {
    g.save(); g.fillStyle = 'rgba(0,0,0,0.5)'; g.beginPath();
    g.ellipse(cx - dx / 2, cy + R * 1.03, R * cs + dx * 0.7, R * 0.09, 0, 0, Math.PI * 2); g.fill(); g.restore();
  }
  if (o.glowCol) glow(cx - dx / 2, cy, R * 1.9, o.glowCol, o.glowA ?? 0.8);
  // banda de rodadura (cara lateral visible del cilindro)
  const tg = g.createLinearGradient(0, cy - R, 0, cy + R);
  tg.addColorStop(0, '#050608'); tg.addColorStop(0.22, '#24272e'); tg.addColorStop(0.42, '#454a55');
  tg.addColorStop(0.55, '#2b2f37'); tg.addColorStop(0.85, '#121419'); tg.addColorStop(1, '#040506');
  g.fillStyle = tg;
  g.beginPath(); g.ellipse(cx - dx, cy, R * cs, R, 0, 0, Math.PI * 2); g.fill();
  g.fillRect(cx - dx, cy - R, dx, 2 * R);
  if (o.wear) { // goma gastada: rayas claras
    g.save(); g.globalAlpha *= o.wear; g.strokeStyle = 'rgba(160,140,120,0.5)'; g.lineWidth = R * 0.02;
    for (let k = 0; k < 9; k++) { const yy = cy - R * 0.8 + k * R * 0.2; line(cx - dx - R * cs * 0.6, yy, cx, yy + R * 0.03); }
    g.restore();
  }
  // marcas que giran sobre la banda
  g.save(); g.strokeStyle = 'rgba(255,255,255,0.07)'; g.lineWidth = Math.max(2, R * 0.025);
  for (let k = 0; k < 18; k++) {
    const ph = rot + k * Math.PI * 2 / 18, c = Math.cos(ph), s = Math.sin(ph);
    if (c > -0.05) continue;
    line(cx - dx + R * c * cs, cy + R * s, cx + R * c * cs, cy + R * s);
  }
  g.restore();
  // costado frontal
  g.translate(cx, cy); g.scale(cs, 1);
  const sg = g.createRadialGradient(-R * 0.2, -R * 0.25, R * 0.3, 0, 0, R);
  sg.addColorStop(0, '#2c3038'); sg.addColorStop(0.7, '#181a20'); sg.addColorStop(1, '#08090c');
  g.fillStyle = sg; circle(0, 0, R); g.fill();
  g.lineWidth = R * 0.018; g.strokeStyle = 'rgba(255,255,255,0.10)'; circle(0, 0, R * 0.985); g.stroke();
  // franja de color
  const bc = col || '#4a4f5b';
  g.save();
  if (col && (o.bandGlow ?? 0) > 0) { g.shadowColor = col; g.shadowBlur = R * 0.25 * o.bandGlow; }
  g.lineWidth = R * 0.07; g.strokeStyle = bc; circle(0, 0, R * 0.835); g.stroke();
  g.restore();
  // "letras" del costado que giran (genéricas)
  g.save(); g.rotate(rot); g.lineWidth = R * 0.05; g.strokeStyle = 'rgba(225,230,240,0.55)';
  for (let k = 0; k < 2; k++) { g.beginPath(); g.arc(0, 0, R * 0.74, k * Math.PI - 0.55, k * Math.PI + 0.55); g.stroke(); }
  g.strokeStyle = col ? rgba(bc, 0.9) : 'rgba(150,155,170,0.6)'; g.lineWidth = R * 0.035;
  for (let k = 0; k < 2; k++) { g.beginPath(); g.arc(0, 0, R * 0.74, k * Math.PI + Math.PI / 2 - 0.25, k * Math.PI + Math.PI / 2 + 0.25); g.stroke(); }
  g.restore();
  // rin de 18"
  const rr = R * 0.6;
  const rg = g.createRadialGradient(-rr * 0.3, -rr * 0.3, rr * 0.1, 0, 0, rr);
  rg.addColorStop(0, '#5a606c'); rg.addColorStop(0.6, '#2a2e36'); rg.addColorStop(1, '#14171c');
  g.fillStyle = rg; circle(0, 0, rr); g.fill();
  g.save(); g.rotate(rot);
  for (let k = 0; k < 10; k++) {
    const a = k * Math.PI / 5;
    g.strokeStyle = '#0c0e12'; g.lineWidth = R * 0.075; line(Math.cos(a) * rr * 0.25, Math.sin(a) * rr * 0.25, Math.cos(a + 0.12) * rr * 0.93, Math.sin(a + 0.12) * rr * 0.93);
    g.strokeStyle = '#6a7180'; g.lineWidth = R * 0.03; line(Math.cos(a) * rr * 0.25, Math.sin(a) * rr * 0.25, Math.cos(a + 0.12) * rr * 0.9, Math.sin(a + 0.12) * rr * 0.9);
  }
  g.restore();
  g.lineWidth = R * 0.03; g.strokeStyle = '#7a8190'; circle(0, 0, rr); g.stroke();
  g.fillStyle = '#1b1e24'; circle(0, 0, rr * 0.25); g.fill();
  g.fillStyle = col || '#9aa3b5'; circle(0, 0, rr * 0.11); g.fill();
  g.restore();
}

// ---------------- gráfica de degradación (ilustrativa) ----------------
const CURVE = {
  S: L => 0.02 * L + 0.003 * L * L,
  M: L => 0.35 + 0.02 * L + 0.0012 * L * L,
  H: L => 0.7 + 0.85 * Math.exp(-L / 1.6) + 0.012 * L + 0.0005 * L * L,
};
function graph(t, a, curves, o = {}) {
  const x0 = 140, y0 = 1330, w = 820, h = 640;
  const al = ease(prog(t, a, a + 0.4));
  g.save(); g.globalAlpha *= al;
  g.fillStyle = 'rgba(6,10,24,0.72)'; g.beginPath(); g.roundRect(x0 - 70, y0 - h - 60, w + 110, h + 150, 28); g.fill();
  g.strokeStyle = 'rgba(79,216,255,0.35)'; g.lineWidth = 2; g.stroke();
  g.strokeStyle = 'rgba(255,255,255,0.12)'; g.lineWidth = 2;
  for (let i = 1; i <= 4; i++) line(x0, y0 - h * i / 4, x0 + w, y0 - h * i / 4);
  g.strokeStyle = WHT; g.lineWidth = 5; line(x0, y0, x0 + w + 10, y0); line(x0, y0, x0, y0 - h - 10);
  txt('VUELTAS →', x0 + w - 110, y0 + 46, 38, CYA, { font: 'IX', stroke: 5 });
  g.save(); g.translate(x0 - 38, y0 - h / 2); g.rotate(-Math.PI / 2); txt('MÁS LENTO →', 0, 0, 36, CYA, { font: 'IX', stroke: 5 }); g.restore();
  txt('gráfica ilustrativa', x0 + w - 120, y0 - h - 30, 28, 'rgba(255,255,255,0.6)', { font: 'IX', stroke: 0 });
  const maxL = 30, maxY = 3.4;
  for (const c of curves) {
    const k = c.k;
    if (k <= 0) continue;
    const n = Math.max(2, Math.floor(60 * k));
    g.save(); g.globalAlpha *= (c.dim ? 0.35 : 1);
    g.shadowColor = TCOL[c.id]; g.shadowBlur = c.dim ? 0 : 18;
    g.strokeStyle = TCOL[c.id]; g.lineWidth = 11; g.lineJoin = 'round'; g.lineCap = 'round';
    g.beginPath();
    for (let i = 0; i <= n; i++) {
      const L = maxL * k * i / n, v = Math.min(maxY, CURVE[c.id](L));
      const x = x0 + w * L / maxL, y = y0 - h * v / maxY;
      i ? g.lineTo(x, y) : g.moveTo(x, y);
    }
    g.stroke(); g.restore();
    if (!c.dim) {
      const L = maxL * k, v = Math.min(maxY, CURVE[c.id](L));
      const x = x0 + w * L / maxL, y = y0 - h * v / maxY;
      g.fillStyle = TCOL[c.id]; circle(x, y, 14); g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
    }
  }
  g.restore();
  return { x0, y0, w, h, X: L => x0 + w * L / 30, Y: v => y0 - h * v / 3.4 };
}

// ---------------- barra de estrategia ----------------
function stintBar(x, y, w, hgt, laps, stints, k, o = {}) {
  g.save();
  g.fillStyle = 'rgba(255,255,255,0.08)'; g.beginPath(); g.roundRect(x, y - hgt / 2, w, hgt, hgt / 2); g.fill();
  g.beginPath(); g.roundRect(x, y - hgt / 2, w, hgt, hgt / 2); g.clip();
  const shown = laps * k;
  for (const s of stints) {
    const a = Math.min(s.a, shown), b = Math.min(s.b, shown);
    if (b <= a) continue;
    g.fillStyle = s.col; g.fillRect(x + w * a / laps, y - hgt / 2, w * (b - a) / laps, hgt);
    if (s.label && b - a > 4) txt(s.label, x + w * (a + b) / 2 / laps, y + 2, hgt * 0.5, INK, { font: 'IX', stroke: 0, alpha: clamp((b - a - 4) / 3) });
  }
  g.restore();
  for (const s of stints.slice(1)) {
    if (s.a > shown) continue;
    const px = x + w * s.a / laps;
    g.fillStyle = WHT; g.fillRect(px - 4, y - hgt / 2 - 16, 8, hgt + 32);
    if (o.pitTags !== false) tag('BOX · V' + s.a, px, y - hgt / 2 - 46, CYA, 30, clamp((shown - s.a) / 2));
  }
}

// ---------------- iconos ----------------
function thermo(x, y, s, level, col) {
  g.save(); g.lineWidth = s * 0.09; g.strokeStyle = WHT;
  g.beginPath(); g.roundRect(x - s * 0.16, y - s, s * 0.32, s * 1.2, s * 0.16); g.stroke();
  circle(x, y + s * 0.32, s * 0.3); g.stroke();
  g.fillStyle = col; circle(x, y + s * 0.32, s * 0.2); g.fill();
  const hh = s * 1.05 * level; g.fillRect(x - s * 0.07, y + s * 0.15 - hh, s * 0.14, hh);
  g.restore();
}

// =====================================================================
// GANCHO
// =====================================================================
const TRIO = [[SOFT, 'BLANDO'], [MEDC, 'MEDIO'], [HARD, 'DURO']];
function sceneHook(t) {
  drawBG(t, 1);
  const lit = [at(G0, 0.6), at(G0, 0.76), at(G0, 0.9)];
  TRIO.forEach(([col], i) => {
    const on = ease(prog(t, lit[i], lit[i] + 0.25));
    const bounce = on > 0 && on < 1 ? -Math.sin(on * Math.PI) * 40 : 0;
    const x = 220 + i * 320, y = 980 + bounce + Math.sin(t * 2 + i) * 8;
    tyre(x, y, 140, on > 0.02 ? col : null, -t * (3 + i * 0.6), 0.55, { bandGlow: on, glowCol: on > 0 ? col : null, glowA: on * 0.9 });
  });
  // tres signos de pregunta
  const qa = 1 - ease(prog(t, lit[0], lit[0] + 0.4));
  txt('?', 540, 690, 150, YEL, { stroke: 10, alpha: qa });
  label(t, -1, 1e9, '¿POR QUÉ 3 COLORES?', ['rojo, amarillo y blanco'], YEL, 104);
}
function sceneRace(t) {
  drawBG(t, 0.7);
  const cx = 540, cy = 1000, rx = 380, ry = 330;
  g.save();
  g.lineWidth = 92; g.strokeStyle = '#2a2d35'; g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); g.stroke();
  g.lineWidth = 5; g.strokeStyle = 'rgba(255,255,255,0.8)';
  g.beginPath(); g.ellipse(cx, cy, rx + 46, ry + 46, 0, 0, Math.PI * 2); g.stroke();
  g.beginPath(); g.ellipse(cx, cy, rx - 46, ry - 46, 0, 0, Math.PI * 2); g.stroke();
  g.setLineDash([26, 22]); g.strokeStyle = 'rgba(255,255,255,0.25)'; g.lineWidth = 3;
  g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); g.stroke(); g.setLineDash([]);
  // meta (cuadros)
  for (let i = 0; i < 8; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? '#fff' : '#111'; g.fillRect(cx - 8 + j * 12 - 6, cy + ry - 46 + i * 11.5, 12, 11.5); }
  g.restore();
  const u = prog(t, G1[0] - 0.3, G1[1] - 0.4);
  const cars = [
    { col: SOFT, s: 0.1 + 0.9 * u - 0.24 * u },
    { col: MEDC, s: 0.9 * u },
    { col: HARD, s: -0.1 + 0.9 * u + 0.2 * u },
  ];
  const order = cars.map((c, i) => [c.s, i]).sort((a, b) => b[0] - a[0]).map(v => v[1]);
  cars.forEach((c, i) => {
    const th = Math.PI / 2 - 2 * Math.PI * c.s;
    const x = cx + rx * Math.cos(th), y = cy + ry * Math.sin(th);
    g.save(); g.shadowColor = c.col; g.shadowBlur = 24; g.fillStyle = INK; circle(x, y, 26); g.fill();
    g.lineWidth = 10; g.strokeStyle = c.col; circle(x, y, 22); g.stroke(); g.restore();
    const pos = order.indexOf(i) + 1;
    const out = Math.cos(th), outy = Math.sin(th);
    tag('P' + pos, x + out * 80, y + outy * 70, pos === 1 ? YEL : WHT, 34);
  });
  const fin = ease(prog(t, at(G1, 0.82), at(G1, 0.92)));
  if (fin > 0) { tag('¡GANA CON DUROS!', cx, cy, HARD, 46, fin); }
  label(t, G1[0] - 0.3, 1e9, 'CAMBIA EL RESULTADO', ['elegir bien es ganar'], WHT, 100);
}

// =====================================================================
// TIPOS
// =====================================================================
function sceneTypes(t) {
  drawBG(t, 0.8);
  const ap = [at(T0, 0.58), at(T0, 0.74), at(T0, 0.88)];
  TRIO.forEach(([col, name], i) => {
    const e = backOut(prog(t, T0[0] - 0.2 + i * 0.25, T0[0] + 0.3 + i * 0.25));
    const nm = ease(prog(t, ap[i] - 0.2, ap[i] + 0.1));
    if (e <= 0) return;
    const x = 220 + i * 320, y = 980;
    g.save(); g.translate(x, y); g.scale(e, e); g.translate(-x, -y);
    tyre(x, y - nm * 30, 135, col, -t * 2.5, 0.5, { bandGlow: 0.3 + nm, glowCol: col, glowA: 0.3 + 0.5 * nm });
    g.restore();
    txt(name, x, 1210, 64 + 10 * nm, col, { alpha: 0.25 + 0.75 * nm });
  });
  label(t, T0[0] - 0.3, 1e9, 'EN SECO: 3 TIPOS', ['blandos · medios · duros'], WHT, 104);
}
function sceneBars(t) {
  drawBG(t, 0.8);
  const vals = [[0.96, 0.32], [0.72, 0.64], [0.5, 0.95]];
  const k = ease(prog(t, T1[0] + 0.3, at(T1, 0.7)));
  TRIO.forEach(([col, name], i) => {
    const x = 220 + i * 320;
    tyre(x, 760, 95, col, -t * 2, 0.5, { shadow: false });
    txt(name, x, 900, 46, col);
    [['AGARRE', CYA], ['DURACIÓN', GRN]].forEach(([lab, bc], j) => {
      const bx = x - 70 + j * 90, h = 360 * vals[i][j] * k;
      g.fillStyle = 'rgba(255,255,255,0.08)'; g.fillRect(bx, 1350 - 360, 52, 360);
      g.save(); g.shadowColor = bc; g.shadowBlur = 16; g.fillStyle = bc; g.fillRect(bx, 1350 - h, 52, h); g.restore();
    });
  });
  // leyenda
  g.fillStyle = CYA; g.fillRect(250, 1395, 34, 34); txt('AGARRE', 380, 1413, 40, CYA, { font: 'IX', stroke: 5 });
  g.fillStyle = GRN; g.fillRect(580, 1395, 34, 34); txt('DURACIÓN', 725, 1413, 40, GRN, { font: 'IX', stroke: 5 });
  label(t, T1[0] - 0.25, 1e9, 'CADA UNO TRABAJA DISTINTO', ['no solo rápido o lento'], YEL, 84);
}

// =====================================================================
// PRESENTACIÓN DE CADA NEUMÁTICO
// =====================================================================
function sceneHero(t, p, col, name, sub) {
  drawBG(t, 0.6);
  const e = easeOut(prog(t, p[0] - 0.3, p[0] + 0.6));
  const yaw = lerp(1.1, 0.42, e) + 0.05 * Math.sin(t * 0.8);
  const R = lerp(200, 300, e);
  glow(540, 1000, 700, col, 0.9);
  tyre(540 + lerp(260, 40, e), 1000, R, col, -t * 1.6, yaw, { bandGlow: 1.2, glowCol: col, glowA: 0.6 });
  const tg = ease(prog(t, at(p, 0.55), at(p, 0.7)));
  if (tg > 0) {
    const bx = 540 + 40 + Math.cos(-0.9) * R * 0.835 * Math.cos(yaw), by = 1000 + Math.sin(-0.9) * R * 0.835;
    g.save(); g.globalAlpha = tg; g.strokeStyle = col; g.lineWidth = 5; line(bx, by, 860, 640); g.restore();
    tag(sub.toUpperCase(), 820, 610, col, 42, tg);
  }
  label(t, p[0] - 0.3, 1e9, name, [], col, 150);
}

// --- BLANDOS ---
function sceneGauge(t) {
  drawBG(t, 0.7);
  const cx = 540, cy = 1080, R = 330;
  const k = ease(prog(t, B1[0] + 0.2, at(B1, 0.55)));
  g.save(); g.lineCap = 'butt';
  for (let i = 0; i < 40; i++) {
    const a0 = Math.PI + i * Math.PI / 40, a1 = a0 + Math.PI / 40 - 0.015;
    const on = i / 40 < k * 0.97;
    g.strokeStyle = on ? (i > 30 ? SOFT : i > 18 ? MEDC : GRN) : 'rgba(255,255,255,0.10)';
    g.lineWidth = 58; g.beginPath(); g.arc(cx, cy, R, a0, a1); g.stroke();
  }
  g.restore();
  const ang = Math.PI + Math.PI * k * 0.97 + Math.sin(t * 30) * 0.01 * k;
  g.save(); g.strokeStyle = WHT; g.lineWidth = 12; g.lineCap = 'round'; line(cx, cy, cx + Math.cos(ang) * (R - 60), cy + Math.sin(ang) * (R - 60)); g.restore();
  g.fillStyle = WHT; circle(cx, cy, 26); g.fill();
  txt('AGARRE', cx, cy + 90, 64, CYA);
  txt(Math.round(k * 97) + '%', cx, cy - 120, 110, k > 0.8 ? SOFT : WHT);
  // cronómetro de vuelta rápida
  const s = prog(t, at(B1, 0.5), B1[1]);
  if (s > 0) {
    const lt = 74.0 + 0.832 * ease(s);
    const mm = Math.floor(lt / 60), ss = (lt - 60 * mm).toFixed(3).padStart(6, '0');
    g.save(); g.globalAlpha = ease(prog(t, at(B1, 0.5), at(B1, 0.55)));
    g.fillStyle = 'rgba(6,10,24,0.85)'; g.beginPath(); g.roundRect(240, 1240, 600, 130, 24); g.fill();
    g.strokeStyle = PUR; g.lineWidth = 4; g.stroke();
    txt(`${mm}:${ss}`, 540, 1306, 84, PUR, { stroke: 0 });
    g.restore();
  }
  label(t, B1[0] - 0.3, 1e9, 'MÁXIMO AGARRE', ['vueltas más rápidas'], SOFT, 110);
}
function asphaltProfile(x) { // perfil rugoso del asfalto (piedritas)
  return 32 * Math.sin(x * 0.045) * Math.sin(x * 0.011 + 1) + 18 * Math.sin(x * 0.13 + 2) + 10 * Math.sin(x * 0.31);
}
function sceneGrip(t) {
  drawBG(t, 0.5);
  const k = ease(prog(t, B2[0] + 0.3, at(B2, 0.45)));
  const cx = 540, cy = 1000, R = 400;
  g.save(); circle(cx, cy, R); g.clip();
  g.fillStyle = '#0c1020'; g.fillRect(cx - R, cy - R, 2 * R, 2 * R);
  const base = cy + 60;
  // asfalto
  g.beginPath(); g.moveTo(cx - R, cy + R);
  for (let x = cx - R; x <= cx + R; x += 4) g.lineTo(x, base + asphaltProfile(x));
  g.lineTo(cx + R, cy + R); g.closePath();
  const ag = g.createLinearGradient(0, base - 40, 0, cy + R); ag.addColorStop(0, '#5a5e68'); ag.addColorStop(1, '#22252c');
  g.fillStyle = ag; g.fill();
  for (let i = 0; i < 70; i++) { const px = cx - R + hash(i, 1, 2) * 2 * R, py = base + 50 + hash(i, 3, 4) * 300; g.fillStyle = `rgba(200,200,210,${0.15 + 0.2 * hash(i, 5, 6)})`; circle(px, py, 4 + 10 * hash(i, 7, 8)); g.fill(); }
  // goma: baja y se mete en las grietas
  const top = cy - R;
  g.beginPath(); g.moveTo(cx - R, top);
  for (let x = cx - R; x <= cx + R; x += 4) {
    const prof = base + asphaltProfile(x);
    const flat = base - 52 + 30 * (1 - k);
    g.lineTo(x, Math.min(prof, lerp(flat, Math.max(flat, prof - 3), k * 0.9)));
  }
  g.lineTo(cx + R, top); g.closePath();
  const rg = g.createLinearGradient(0, top, 0, base); rg.addColorStop(0, '#16181e'); rg.addColorStop(1, '#30343d');
  g.fillStyle = rg; g.fill();
  g.strokeStyle = SOFT; g.lineWidth = 16; line(cx - R, top + 70, cx + R, top + 70);
  g.restore();
  g.lineWidth = 10; g.strokeStyle = WHT; circle(cx, cy, R); g.stroke();
  tag('GOMA BLANDA', cx - 120, cy - 230, SOFT, 44, ease(prog(t, B2[0] + 0.4, B2[0] + 0.8)));
  tag('ASFALTO', cx + 170, cy + 260, WHT, 44, ease(prog(t, B2[0] + 0.8, B2[0] + 1.2)));
  const ga = ease(prog(t, at(B2, 0.45), at(B2, 0.55)));
  if (ga > 0) { tag('¡SE PEGA!', cx, cy - 40, YEL, 60, ga); }
  const ca = ease(prog(t, at(B2, 0.62), at(B2, 0.72)));
  if (ca > 0) {
    g.save(); g.globalAlpha = ca; g.strokeStyle = YEL; g.lineWidth = 16; g.lineCap = 'round';
    g.beginPath(); g.arc(540, 1480, 300, Math.PI * 1.15, Math.PI * 1.85); g.stroke();
    arrow(540 + 300 * Math.cos(Math.PI * 1.8), 1480 + 300 * Math.sin(Math.PI * 1.8), 540 + 300 * Math.cos(Math.PI * 1.9), 1480 + 300 * Math.sin(Math.PI * 1.9), 26, YEL);
    g.restore();
    tag('CURVAS MÁS RÁPIDAS', 540, 1435, YEL, 40, ca);
  }
  label(t, B2[0] - 0.3, 1e9, 'SE PEGA AL ASFALTO', ['más adherencia'], SOFT, 100);
}
function sceneDegSoft(t) {
  drawBG(t, 0.5);
  const k = prog(t, B3[0] + 0.3, at(B3, 0.85));
  const G = graph(t, B3[0] - 0.3, [{ id: 'S', k }]);
  const lap = Math.max(1, Math.round(30 * k));
  tag('VUELTA ' + lap, 540, 585, WHT, 40, 1);
  const pa = ease(prog(t, at(B3, 0.6), at(B3, 0.7)));
  if (pa > 0) tag('PIERDE RENDIMIENTO', G.X(21) - 60, G.Y(CURVE.S(21)) - 70, SOFT, 40, pa);
  label(t, B3[0] - 0.3, 1e9, 'SE DEGRADAN RÁPIDO', ['pierden ritmo vuelta tras vuelta'], SOFT, 96);
}
function sceneQuali(t) {
  drawBG(t, 0.7);
  const rows = [['P1', SOFT], ['P2', SOFT], ['P3', SOFT]];
  const s = prog(t, B4[0] + 0.3, at(B4, 0.7));
  const times = [74.832, 74.919, 75.044];
  g.save(); g.fillStyle = 'rgba(6,10,24,0.85)'; g.beginPath(); g.roundRect(120, 640, 840, 640, 30); g.fill(); g.strokeStyle = 'rgba(79,216,255,0.4)'; g.lineWidth = 3; g.stroke(); g.restore();
  txt('CLASIFICACIÓN', 540, 715, 56, CYA, { font: 'IX', stroke: 0 });
  rows.forEach(([p, col], i) => {
    const y = 840 + i * 150;
    const shown = s > 0.25 + i * 0.2;
    const a = ease(prog(t, at(B4, 0.12 + i * 0.12), at(B4, 0.18 + i * 0.12)));
    g.save(); g.globalAlpha = a;
    txt(p, 220, y, 64, i === 0 ? PUR : WHT, { stroke: 0 });
    tyre(370, y, 48, col, -t * 6, 0.5, { shadow: false });
    const lt = shown ? times[i] : 72 + (t * 7.3 + i) % 3;
    const mm = Math.floor(lt / 60), ss = (lt - 60 * mm).toFixed(3).padStart(6, '0');
    txt(`${mm}:${ss}`, 700, y, 78, i === 0 && shown ? PUR : WHT, { stroke: 0 });
    g.restore();
  });
  const pa = ease(prog(t, at(B4, 0.72), at(B4, 0.8)));
  tag('MEJOR TIEMPO CON BLANDOS', 540, 1360, PUR, 42, pa);
  label(t, B4[0] - 0.3, 1e9, 'REYES DE LA CLASIFICACIÓN', ['una vuelta, máximo agarre'], SOFT, 84);
}

// --- MEDIOS ---
function sceneBalance(t) {
  drawBG(t, 0.7);
  const s = prog(t, M1[0], M1[1]);
  const ang = 0.35 * Math.exp(-s * 4) * Math.cos(s * 18);
  const cx = 540, cy = 1060, L = 400;
  g.fillStyle = '#c9d3e6'; poly([[cx, cy], [cx - 60, cy + 170], [cx + 60, cy + 170]]); g.fill();
  g.save(); g.translate(cx, cy); g.rotate(ang);
  g.fillStyle = '#e6ebf5'; g.fillRect(-L, -10, 2 * L, 20);
  [[-1, 'VELOCIDAD', CYA], [1, 'DURACIÓN', GRN]].forEach(([sd, lab, col]) => {
    g.save(); g.translate(sd * (L - 60), 0); g.rotate(-ang);
    g.strokeStyle = '#e6ebf5'; g.lineWidth = 4; line(0, 0, -70, 120); line(0, 0, 70, 120);
    g.fillStyle = col; g.fillRect(-100, 120, 200, 18);
    txt(lab, 0, 190, 44, col, { font: 'IX', stroke: 6 });
    g.restore();
  });
  g.restore();
  tyre(cx, cy - 150, 120, MEDC, -t * 2, 0.5, { glowCol: MEDC, glowA: 0.6, bandGlow: 1 });
  label(t, M1[0] - 0.3, 1e9, 'EL EQUILIBRIO', ['velocidad y duración'], MEDC, 116);
}
function sceneDegMed(t) {
  drawBG(t, 0.5);
  const k = prog(t, M2[0] + 0.2, at(M2, 0.8));
  const G = graph(t, M2[0] - 0.3, [{ id: 'S', k: 1, dim: true }, { id: 'M', k }]);
  const pa = ease(prog(t, at(M2, 0.6), at(M2, 0.7)));
  if (pa > 0) tag('RINDE MÁS VUELTAS', G.X(22), G.Y(CURVE.M(22)) - 80, MEDC, 40, pa);
  label(t, M2[0] - 0.3, 1e9, 'AGUANTAN MÁS', ['menos agarre, más vueltas'], MEDC, 110);
}
function sceneStratMed(t) {
  drawBG(t, 0.7);
  const k = ease(prog(t, M3[0] + 0.2, at(M3, 0.85)));
  txt('CARRERA DE 60 VUELTAS', 540, 760, 46, CYA, { font: 'IX' });
  stintBar(90, 900, 900, 90, 60, [{ a: 0, b: 34, col: MEDC, label: 'MEDIO' }, { a: 34, b: 60, col: HARD, label: 'DURO' }], k);
  tyre(330, 1170, 110, MEDC, -t * 3, 0.5, { glowCol: MEDC, glowA: 0.5 });
  tyre(760, 1170, 110, HARD, -t * 3, 0.5, { alpha: clamp(k * 2 - 1) });
  txt('+', 545, 1170, 90, WHT, { alpha: clamp(k * 2 - 1) });
  label(t, M3[0] - 0.3, 1e9, 'CLAVE EN LA ESTRATEGIA', ['ejemplo de una parada'], MEDC, 90);
}

// --- DUROS ---
function sceneTough(t) {
  drawBG(t, 0.6);
  tyre(540, 860, 190, HARD, -t * 2.2, 0.5, { glowCol: '#ff7a2a', glowA: 0.5 + 0.2 * Math.sin(t * 6) });
  // ondas de calor
  g.save(); g.strokeStyle = 'rgba(255,140,60,0.55)'; g.lineWidth = 6;
  for (let i = 0; i < 3; i++) { g.beginPath(); for (let y = 0; y < 160; y += 6) { const x = 380 + i * 160 + 14 * Math.sin(y * 0.08 - t * 8); y ? g.lineTo(x, 620 - y) : g.moveTo(x, 620 - y); } g.stroke(); }
  g.restore();
  const items = [['TEMPERATURA', '#ff8a3d', 0.15], ['DESGASTE', CYA, 0.42], ['ESFUERZO', GRN, 0.62]];
  items.forEach(([lab, col, f], i) => {
    const y = 1150 + i * 105;
    const k = ease(prog(t, at(D1, f), at(D1, f) + 0.7));
    txt(lab, 140, y, 42, col, { align: 'left', font: 'IX' });
    g.fillStyle = 'rgba(255,255,255,0.1)'; g.fillRect(520, y - 22, 380, 44);
    g.save(); g.shadowColor = col; g.shadowBlur = 14; g.fillStyle = col; g.fillRect(520, y - 22, 380 * 0.92 * k, 44); g.restore();
    if (k > 0.95) txt('✓', 950, y, 54, GRN, { stroke: 6 });
  });
  label(t, D1[0] - 0.3, 1e9, 'AGUANTAN MÁS', ['temperatura, desgaste y esfuerzo'], HARD, 116);
}
function sceneWarm(t) {
  drawBG(t, 0.6);
  const s = prog(t, D2[0] + 0.2, at(D2, 0.48));
  const yTop = 680, yBot = 1300, x1 = 340, x2 = 740;
  [[x1, SOFT, 'BLANDO', ease(clamp(s * 2.5)) * 0.82], [x2, HARD, 'DURO', 0.82 * ease(s)]].forEach(([x, col, name, lv]) => {
    g.fillStyle = 'rgba(70,224,138,0.18)'; g.fillRect(x - 90, yBot - (yBot - yTop) * 0.92, 180, (yBot - yTop) * 0.2);
    g.fillStyle = 'rgba(255,255,255,0.08)'; g.beginPath(); g.roundRect(x - 50, yTop, 100, yBot - yTop, 50); g.fill();
    g.save(); g.shadowColor = col; g.shadowBlur = 18; g.fillStyle = col; g.beginPath(); g.roundRect(x - 34, yBot - (yBot - yTop) * lv - 16, 68, (yBot - yTop) * lv, 34); g.fill(); g.restore();
    tyre(x, yBot + 90, 70, col, -t * 3, 0.5, { shadow: false });
    txt(name, x, yTop - 40, 48, col);
  });
  txt('VENTANA IDEAL', 540, yBot - (yBot - yTop) * 0.82, 34, GRN, { font: 'IX', stroke: 6 });
  const late = ease(prog(t, at(D2, 0.25), at(D2, 0.32)));
  if (late > 0 && s < 0.97) tag('TARDA EN CALENTAR', x2, 1060, HARD, 36, late);
  label(t, D2[0] - 0.3, 1e9, 'TARDAN EN CALENTARSE', ['menos agarre al inicio'], HARD, 94);
}
function sceneDegHard(t) {
  drawBG(t, 0.5);
  const k = prog(t, at(D2, 0.5), at(D2, 0.92));
  const G = graph(t, at(D2, 0.48), [{ id: 'S', k: 1, dim: true }, { id: 'M', k: 1, dim: true }, { id: 'H', k }]);
  const pa = ease(prog(t, at(D2, 0.82), at(D2, 0.9)));
  if (pa > 0) tag('TANDAS MÁS LARGAS', G.X(23), G.Y(CURVE.H(23)) - 75, HARD, 42, pa);
  label(t, at(D2, 0.48), 1e9, 'TANDAS MÁS LARGAS', ['el más constante'], HARD, 100);
}

// =====================================================================
// COMPUESTOS
// =====================================================================
function sceneSecret(t) {
  drawBG(t, 0.8);
  const s = prog(t, at(C0, 0.5), at(C0, 0.95));
  const cols = [SOFT, MEDC, HARD];
  for (let i = 0; i < 3; i++) {
    const ph = s * Math.PI * 4 + i * 2.1;
    const x = 540 + 300 * Math.sin(ph) * (s > 0 ? 1 : 0) + (s > 0 ? 0 : (i - 1) * 320);
    const zz = Math.cos(ph);
    const col = s > 0.05 ? (hash(i, Math.floor(s * 12), 3) < 0.5 ? cols[(i + Math.floor(s * 12)) % 3] : null) : cols[i];
    tyre(s > 0 ? x : 220 + i * 320, 1000 + (s > 0 ? zz * 30 : 0), 130 * (s > 0 ? 1 + 0.12 * zz : 1), col, -t * 2, 0.5);
  }
  const qa = ease(prog(t, at(C0, 0.55), at(C0, 0.65)));
  txt('?', 540, 1000, 220, YEL, { stroke: 12, alpha: qa });
  label(t, C0[0] - 0.3, 1e9, 'LO QUE MUCHOS NO SABEN', ['el rojo no siempre es el mismo'], YEL, 84);
}
const XS5 = [130, 335, 540, 745, 950];
function fiveRow(t, y, colsFn, appear = () => 1, hi = -1, hiCol = YEL) {
  for (let i = 0; i < 5; i++) {
    const a = appear(i); if (a <= 0) continue;
    const e = backOut(clamp(a));
    g.save(); g.translate(XS5[i], y); g.scale(e, e); g.translate(-XS5[i], -y);
    tyre(XS5[i], y, 84, colsFn(i), -t * 2, 0.45, { shadow: false, glowCol: i === hi ? hiCol : null, glowA: 0.8, bandGlow: i === hi ? 1 : 0 });
    g.restore();
    txt('C' + (i + 1), XS5[i], y + 135, 58, i === hi ? hiCol : WHT, { alpha: clamp(a) });
  }
}
function sceneFive(t) {
  drawBG(t, 0.8);
  const ap = i => prog(t, at(C1, 0.28 + i * 0.075), at(C1, 0.28 + i * 0.075) + 0.35);
  fiveRow(t, 960, () => null, ap);
  const k = ease(prog(t, at(C1, 0.7), at(C1, 0.85)));
  if (k > 0) {
    const gr = g.createLinearGradient(110, 0, 970, 0); gr.addColorStop(0, HARD); gr.addColorStop(0.5, MEDC); gr.addColorStop(1, SOFT);
    g.save(); g.globalAlpha = k; g.fillStyle = gr; g.fillRect(110, 1210, 860 * k, 22);
    arrow(110 + 860 * k - 10, 1221, 110 + 860 * k + 30, 1221, 22, SOFT);
    g.restore();
    txt('MÁS DURO', 200, 1290, 44, HARD, { font: 'IX', alpha: k });
    txt('MÁS BLANDO', 870, 1290, 44, SOFT, { font: 'IX', alpha: k });
  }
  label(t, C1[0] - 0.3, 1e9, '5 COMPUESTOS', ['de seco: del C1 al C5'], YEL, 120);
}
function windowCols(start) { return i => (i < start || i > start + 2) ? null : [HARD, MEDC, SOFT][i - start]; }
function sceneWindow(t) {
  drawBG(t, 0.8);
  const m1 = at(C2, 0.5), m2 = at(C2, 0.78);
  const pos = t < m1 - 0.4 ? 1 : t < m2 - 0.4 ? lerp(1, 2, ease(prog(t, m1 - 0.4, m1))) : lerp(2, 0, ease(prog(t, m2 - 0.4, m2)));
  const st = Math.round(pos);
  const settled = Math.abs(pos - st) < 0.02;
  const wa = ease(prog(t, C2[0] + 0.2, C2[0] + 0.6));
  const wx = XS5[0] + (XS5[1] - XS5[0]) * pos - 105;
  g.save(); g.globalAlpha = wa; g.fillStyle = 'rgba(255,216,77,0.08)'; g.strokeStyle = YEL; g.lineWidth = 6;
  g.beginPath(); g.roundRect(wx, 820, 2 * (XS5[1] - XS5[0]) + 210, 340, 30); g.fill(); g.stroke();
  txt('ESTE GP', wx + (XS5[1] - XS5[0]) + 105, 790, 40, YEL, { font: 'IX' });
  g.restore();
  fiveRow(t, 960, settled ? windowCols(st) : () => null, () => 1, 2, YEL);
  if (settled && t > m1 - 0.1) {
    const isHard = st === 2;
    tag(isHard ? 'C3 = DURO' : 'C3 = BLANDO', 540, 1330, isHard ? HARD : SOFT, 64, ease(prog(t, (isHard ? m1 : m2) - 0.05, (isHard ? m1 : m2) + 0.25)));
  }
  label(t, C2[0] - 0.3, 1e9, 'CADA GP ELIGE 3', ['los colores cambian de dueño'], YEL, 110);
}
function raceCard(t, y, title, start, a) {
  if (a <= 0) return;
  g.save(); g.globalAlpha = a;
  g.fillStyle = 'rgba(6,10,24,0.85)'; g.beginPath(); g.roundRect(70, y - 190, 940, 380, 30); g.fill();
  g.strokeStyle = 'rgba(79,216,255,0.45)'; g.lineWidth = 3; g.stroke();
  txt(title, 540, y - 135, 56, WHT);
  for (let j = 0; j < 3; j++) {
    const i = start + j, x = 260 + j * 280, isC3 = i === 2;
    tyre(x, y + 15, 78, [HARD, MEDC, SOFT][j], -t * 2, 0.45, { shadow: false, glowCol: isC3 ? YEL : null, glowA: 0.9, bandGlow: isC3 ? 1 : 0 });
    txt('C' + (i + 1), x, y + 152, 50, isC3 ? YEL : WHT);
    if (isC3) { g.strokeStyle = YEL; g.lineWidth = 6; circle(x - 11, y + 15, 98); g.stroke(); }
  }
  g.restore();
}
function sceneExamples(t) {
  drawBG(t, 0.8);
  raceCard(t, 830, 'MÉXICO 2026', 2, ease(prog(t, C3[0] - 0.2, C3[0] + 0.3)));
  raceCard(t, 1260, 'JAPÓN 2026', 0, ease(prog(t, at(C3, 0.5), at(C3, 0.62))));
  label(t, C3[0] - 0.3, 1e9, 'EJEMPLO REAL', ['C3: duro en México, blando en Japón'], YEL, 116);
}

// =====================================================================
// ESTRATEGIA
// =====================================================================
function sceneWall(t) {
  drawBG(t, 0.8);
  const x0 = 110, y0 = 680, w = 860, h = 560;
  g.save(); g.fillStyle = '#0a0f1f'; g.beginPath(); g.roundRect(x0 - 20, y0 - 20, w + 40, h + 40, 26); g.fill();
  g.strokeStyle = '#5a6582'; g.lineWidth = 8; g.stroke(); g.restore();
  g.fillStyle = '#5a6582'; g.fillRect(500, y0 + h + 20, 80, 120); g.fillRect(380, y0 + h + 130, 320, 24);
  // líneas de ritmo en vivo
  const s = t - E0[0];
  const lines = [[SOFT, 0.02, 0.003], [MEDC, 0.35, 0.0012], [HARD, 0.7, 0.0005]];
  lines.forEach(([col, b, q], j) => {
    g.save(); g.strokeStyle = col; g.lineWidth = 6; g.beginPath();
    for (let i = 0; i <= 80; i++) {
      const L = i * 30 / 80, v = b + 0.02 * L + q * L * L + 0.08 * Math.sin(L * 2 + s * 3 + j);
      const x = x0 + 30 + (w - 60) * i / 80, y = y0 + h - 60 - (h - 140) * v / 3.4;
      if (i / 80 > clamp(s / 2.5)) break;
      i ? g.lineTo(x, y) : g.moveTo(x, y);
    }
    g.stroke(); g.restore();
  });
  txt('RITMO POR VUELTA', 540, y0 + 40, 36, CYA, { font: 'IX', stroke: 0 });
  // cursor que parpadea
  if (Math.floor(t * 2) % 2) { g.fillStyle = GRN; circle(x0 + w - 30, y0 + 40, 10); g.fill(); }
  label(t, E0[0] - 0.3, 1e9, 'LOS ESTRATEGAS', ['aquí empieza su trabajo'], CYA, 116);
}
function factorIcon(k, x, y, s) {
  g.save(); g.lineWidth = 8; g.strokeStyle = WHT; g.lineCap = 'round'; g.lineJoin = 'round';
  if (k === 0) thermo(x, y - 10, s, 0.75, '#ff8a3d');
  if (k === 1) { // asfalto abrasivo
    g.fillStyle = '#3a3f4a'; g.fillRect(x - s, y - s * 0.2, 2 * s, s * 0.8);
    g.fillStyle = '#9aa0ad'; for (let i = 0; i < 9; i++) { poly([[x - s + i * s * 0.22, y - s * 0.2], [x - s + i * s * 0.22 + s * 0.11, y - s * 0.55], [x - s + i * s * 0.22 + s * 0.22, y - s * 0.2]]); g.fill(); }
  }
  if (k === 2) { g.beginPath(); g.moveTo(x - s, y + s * 0.6); g.bezierCurveTo(x - s * 0.2, y + s * 0.6, x - s * 0.8, y - s * 0.7, x + s, y - s * 0.6); g.lineWidth = 22; g.strokeStyle = '#3a3f4a'; g.stroke(); g.lineWidth = 4; g.strokeStyle = WHT; g.setLineDash([16, 14]); g.stroke(); g.setLineDash([]); }
  if (k === 3) { tyre(x, y, s * 0.75, SOFT, 0, 0.4, { shadow: false, wear: 1 }); }
  g.restore();
}
function sceneFactors(t) {
  drawBG(t, 0.7);
  const f = [['TEMPERATURA', '#ff8a3d', 0.05], ['ABRASIVIDAD', GREY, 0.2], ['CURVAS', CYA, 0.42], ['DEGRADACIÓN', SOFT, 0.55]];
  f.forEach(([lab, col, fr], i) => {
    const a = backOut(prog(t, at(E1, fr), at(E1, fr) + 0.4));
    if (a <= 0) return;
    const x = i % 2 ? 790 : 290, y = i < 2 ? 820 : 1220;
    g.save(); g.translate(x, y); g.scale(a, a); g.translate(-x, -y);
    g.fillStyle = 'rgba(6,10,24,0.85)'; g.beginPath(); g.roundRect(x - 230, y - 180, 460, 360, 28); g.fill();
    g.strokeStyle = col; g.lineWidth = 5; g.stroke();
    factorIcon(i, x, y - 30, 110);
    txt(lab, x, y + 130, 44, col, { font: 'IX', maxW: 420 });
    g.restore();
  });
  label(t, E1[0] - 0.3, 1e9, '¿CUÁL ELEGIR?', ['depende de la pista'], CYA, 120);
}
function sceneRule(t) {
  drawBG(t, 0.7);
  const k = ease(prog(t, E2[0] + 0.3, at(E2, 0.8)));
  txt('CARRERA EN SECO', 540, 720, 48, CYA, { font: 'IX' });
  stintBar(90, 860, 900, 90, 57, [{ a: 0, b: 22, col: MEDC, label: 'MEDIO' }, { a: 22, b: 57, col: HARD, label: 'DURO' }], k);
  // auto entrando a boxes
  const pitA = ease(prog(t, at(E2, 0.55), at(E2, 0.68)));
  if (pitA > 0) {
    g.save(); g.globalAlpha = pitA;
    g.fillStyle = 'rgba(6,10,24,0.85)'; g.beginPath(); g.roundRect(240, 1020, 600, 300, 28); g.fill(); g.strokeStyle = CYA; g.lineWidth = 4; g.stroke();
    txt('PARADA EN BOXES', 540, 1080, 50, WHT);
    tyre(400, 1215, 70, MEDC, 0, 0.45, { shadow: false, wear: 0.8 });
    arrow(490, 1215, 590, 1215, 22, YEL);
    tyre(690, 1215, 70, HARD, -t * 3, 0.45, { shadow: false });
    g.restore();
  }
  const ca = ease(prog(t, at(E2, 0.35), at(E2, 0.45)));
  tag('MÍNIMO 2 COMPUESTOS ✓', 540, 1420, GRN, 46, ca);
  label(t, E2[0] - 0.3, 1e9, 'LA REGLA', ['al menos 2 compuestos en seco'], YEL, 130);
}

// =====================================================================
// FINAL
// =====================================================================
function sceneNotFastest(t) {
  drawBG(t, 0.7);
  tyre(540, 940, 230, SOFT, -t * 7, 0.5, { glowCol: SOFT, glowA: 0.7, bandGlow: 1, wear: clamp(prog(t, at(F0, 0.5), F0[1])) });
  tag('EL MÁS RÁPIDO', 540, 620, SOFT, 50, ease(prog(t, F0[0], F0[0] + 0.4)));
  const w = 1 - ease(prog(t, at(F0, 0.45), F0[1]));
  g.fillStyle = 'rgba(255,255,255,0.1)'; g.fillRect(290, 1270, 500, 40);
  g.fillStyle = w > 0.4 ? GRN : SOFT; g.fillRect(290, 1270, 500 * w, 40);
  txt('VIDA DEL NEUMÁTICO', 540, 1350, 38, WHT, { font: 'IX' });
  label(t, F0[0] - 0.3, 1e9, 'NO SIEMPRE GANA', ['el neumático más rápido'], WHT, 120);
}
function scenePositions(t) {
  drawBG(t, 0.6);
  const x0 = 150, y0 = 1270, w = 800, h = 560;
  const k = prog(t, F1[0] + 0.2, at(F1, 0.9));
  g.save(); g.fillStyle = 'rgba(6,10,24,0.72)'; g.beginPath(); g.roundRect(x0 - 80, y0 - h - 60, w + 120, h + 140, 28); g.fill(); g.restore();
  for (let p = 1; p <= 6; p++) { const y = y0 - h + (p - 1) * h / 5; g.strokeStyle = 'rgba(255,255,255,0.1)'; g.lineWidth = 2; line(x0, y, x0 + w, y); txt('P' + p, x0 - 40, y, 32, p === 1 ? YEL : 'rgba(255,255,255,0.7)', { stroke: 0 }); }
  const Ppos = (arr, u) => { const n = arr.length - 1, i = Math.min(n - 1, Math.floor(u * n)), f = u * n - i; return lerp(arr[i], arr[i + 1], ease(f)); };
  const A = [5, 2, 2, 3, 4], Bp = [6, 6, 4, 2, 1];
  [[A, SOFT, 'SALE CON BLANDOS'], [Bp, HARD, 'SALE CON MEDIOS/DUROS']].forEach(([arr, col, lab], j) => {
    g.save(); g.strokeStyle = col; g.lineWidth = 12; g.lineCap = 'round'; g.shadowColor = col; g.shadowBlur = 14; g.beginPath();
    for (let i = 0; i <= 60; i++) { const u = k * i / 60, x = x0 + w * u, y = y0 - h + (Ppos(arr, u) - 1) * h / 5; i ? g.lineTo(x, y) : g.moveTo(x, y); }
    g.stroke(); g.restore();
    const xe = x0 + w * k, ye = y0 - h + (Ppos(arr, k) - 1) * h / 5;
    g.fillStyle = col; circle(xe, ye, 16); g.fill();
    tag(lab, 540, j ? 1475 : 1405, col, 34, k > 0.05 ? 1 : 0);
  });
  txt('VUELTAS →', x0 + w - 90, y0 + 40, 34, CYA, { font: 'IX', stroke: 5 });
  txt('gráfica ilustrativa', 760, y0 - h - 30, 28, 'rgba(255,255,255,0.6)', { font: 'IX', stroke: 0 });
  label(t, F1[0] - 0.3, 1e9, 'GANAR AL FINAL', ['blandos al inicio · medios o duros al final'], YEL, 116);
}
function sceneHungary(t) {
  drawBG(t, 0.7);
  const k = ease(prog(t, F2[0] + 0.3, at(F2, 0.75)));
  g.save(); g.fillStyle = 'rgba(6,10,24,0.85)'; g.beginPath(); g.roundRect(50, 640, 980, 730, 30); g.fill(); g.strokeStyle = 'rgba(79,216,255,0.45)'; g.lineWidth = 3; g.stroke(); g.restore();
  txt('GP DE HUNGRÍA 2025 · 70 VUELTAS', 540, 700, 42, CYA, { font: 'IX', stroke: 0 });
  txt('NORRIS', 90, 820, 54, WHT, { align: 'left' }); txt('1 PARADA', 990, 820, 40, GRN, { align: 'right', font: 'IX' });
  stintBar(90, 900, 900, 76, 70, [{ a: 0, b: 32, col: MEDC, label: 'MEDIO' }, { a: 32, b: 70, col: HARD, label: 'DURO' }], k);
  txt('PIASTRI', 90, 1060, 54, WHT, { align: 'left' }); txt('2 PARADAS', 990, 1060, 40, '#ff8a3d', { align: 'right', font: 'IX' });
  stintBar(90, 1140, 900, 76, 70, [{ a: 0, b: 19, col: '#7d879c' }, { a: 19, b: 46, col: '#9aa3b5' }, { a: 46, b: 70, col: '#7d879c' }], k, { pitTags: false });
  const wa = ease(prog(t, at(F2, 0.78), at(F2, 0.88)));
  if (wa > 0) {
    tag('GANA NORRIS', 540, 1260, YEL, 58, wa);
    txt('por solo 0.698 s', 540, 1335, 40, WHT, { font: 'IX', alpha: wa });
  }
  label(t, F2[0] - 0.3, 1e9, 'EJEMPLO REAL', ['Norris vs. Piastri'], YEL, 120);
}
function sceneTools(t) {
  drawBG(t, 0.7);
  // bandera a cuadros que ondea
  const fa = ease(prog(t, F3[0], F3[0] + 0.6));
  g.save(); g.globalAlpha = 0.22 * fa;
  for (let i = 0; i < 14; i++) for (let j = 0; j < 3; j++) {
    const x = i * 80, y = 1300 + j * 60 + 14 * Math.sin(i * 0.6 - t * 4);
    g.fillStyle = (i + j) % 2 ? '#fff' : '#000'; g.fillRect(x, y, 80, 60);
  }
  g.restore();
  TRIO.forEach(([col], i) => {
    const e = backOut(prog(t, F3[0] + i * 0.25, F3[0] + i * 0.25 + 0.5));
    if (e <= 0) return;
    const x = 220 + i * 320, y = 960 + Math.sin(t * 2 + i) * 10;
    g.save(); g.translate(x, y); g.scale(e, e); g.translate(-x, -y);
    tyre(x, y, 135, col, -t * 3, 0.5, { glowCol: col, glowA: 0.7, bandGlow: 1 });
    g.restore();
  });
  const ga = ease(prog(t, at(F3, 0.55), at(F3, 0.7)));
  tag('HERRAMIENTAS PARA GANAR', 540, 1200, YEL, 52, ga);
  label(t, F3[0] - 0.3, 1e9, 'NO SON SOLO GOMA', ['son estrategia pura'], WHT, 116);
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
// MONTAJE
// =====================================================================
const hero = (p, col, name, sub) => t => sceneHero(t, p, col, name, sub);
const SCENES = [
  [-1, sceneHook], [G1[0] - 0.3, sceneRace],
  [FLASHES[0], sceneTypes], [T1[0] - 0.3, sceneBars],
  [FLASHES[1], hero(B0, SOFT, 'BLANDO', 'franja roja')], [B1[0] - 0.3, sceneGauge], [B2[0] - 0.3, sceneGrip], [B3[0] - 0.3, sceneDegSoft], [B4[0] - 0.3, sceneQuali],
  [FLASHES[2], hero(M0, MEDC, 'MEDIO', 'color amarillo')], [M1[0] - 0.3, sceneBalance], [M2[0] - 0.3, sceneDegMed], [M3[0] - 0.3, sceneStratMed],
  [FLASHES[3], hero(D0, HARD, 'DURO', 'franja blanca')], [D1[0] - 0.3, sceneTough], [D2[0] - 0.3, sceneWarm], [at(D2, 0.48), sceneDegHard],
  [FLASHES[4], sceneSecret], [C1[0] - 0.3, sceneFive], [C2[0] - 0.3, sceneWindow], [C3[0] - 0.3, sceneExamples],
  [FLASHES[5], sceneWall], [E1[0] - 0.3, sceneFactors], [E2[0] - 0.3, sceneRule],
  [FLASHES[6], sceneNotFastest], [F1[0] - 0.3, scenePositions], [F2[0] - 0.3, sceneHungary], [F3[0] - 0.3, sceneTools],
  [FLASHES[7], sceneEnd],
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
