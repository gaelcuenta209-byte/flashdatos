// Flash Datos · video 16 · Mazda 787B: el único auto sin pistones que ganó Le Mans (respuesta a @_nachozn_)
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
  ...['m787b.jpg', 'lm1991.jpg', 'wankel.jpg', 'm767.jpg'].map(f => loadImg(f.split('.')[0], 'img/' + f)),
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
  if (/^KG$/i.test(c)) return 5;
  if (/^RPM$/i.test(c)) return 13;
  if (c === '787B') return 20;
  if (c === 'R26B') return 14;
  if (c === 'RX-7') return 8;
  if (c === '654') return 30;
  if (c === '9,000') return 9;
  if (c === '1,000') return 3;
  if (c === '700') return 9;
  if (c === '830') return 16;
  if (/^cc$/i.test(c)) return 20;
  if (c.startsWith('@')) return 6;
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


// ---------------- colores del 787B ----------------
const MGRN = '#16b06a', MORA = '#ff6a2b', SILV = '#b9c2d3';
const S = id => SEG[id].t0, E = id => SEG[id].t1;
const M0 = S('motor') - 0.3;           // el motor
const D0 = S('pbujias') - 0.3;         // desarmado
const K0 = S('chasis') - 0.3;          // chasis
const P0 = S('pilotos') - 0.3;         // pilotos y carrera
const F0 = S('final') - 0.3;           // final
const E0 = E('final') + 0.15;          // tarjeta final
const FLASHES = [M0, D0, K0, P0, F0, E0];
function flashAlpha(t) {
  let a = 0;
  for (const tf of FLASHES) { const dt = t - tf; if (dt >= -0.07 && dt < 0) a = Math.max(a, (dt + 0.07) / 0.07); else if (dt >= 0 && dt < 0.45) a = Math.max(a, Math.exp(-dt / 0.085)); }
  return a;
}

// =====================================================================
// MOTOR ROTATIVO (medidas reales del rotor Mazda: R = 105 mm, e = 15 mm)
// =====================================================================
const RE = 15, RR = 105, TAU = Math.PI * 2;
const hp = a => [RE * Math.cos(3 * a) + RR * Math.cos(a), RE * Math.sin(3 * a) + RR * Math.sin(a)];
const PH = [[Math.PI / 4, [79, 216, 255]], [3 * Math.PI / 4, [150, 160, 180]], [5 * Math.PI / 4, [255, 110, 50]], [7 * Math.PI / 4, [255, 216, 77]]]; // admisión, escape, explosión, compresión
function phaseCol(m, a = 0.75) {
  m = ((m % TAU) + TAU) % TAU;
  for (let i = 0; i < 4; i++) {
    const [a0, c0] = PH[i], [a1r, c1] = PH[(i + 1) % 4]; const a1 = i === 3 ? a1r + TAU : a1r;
    let mm = m; if (mm < a0) mm += TAU;
    if (mm >= a0 && mm <= a1) { const s = ease((mm - a0) / (a1 - a0)); return `rgba(${c0.map((v, j) => Math.round(lerp(v, c1[j], s))).join(',')},${a})`; }
  }
  return `rgba(255,255,255,${a})`;
}
// o: {k px/mm, phi ángulo del eje, hl: {bujias, puertos, sellos, chambers}, alpha}
function rotary(cx, cy, k, phi, o = {}) {
  const P = ([x, y]) => [cx + x * k, cy - y * k];
  const th = phi / 3, c = [RE * Math.cos(phi), RE * Math.sin(phi)];
  const apex = i => [c[0] + RR * Math.cos(th + i * TAU / 3), c[1] + RR * Math.sin(th + i * TAU / 3)];
  g.save();
  // carcasa
  const H = []; for (let i = 0; i <= 240; i++) H.push(P(hp(i / 240 * TAU)));
  g.save(); g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 40;
  poly(H); g.lineWidth = 34 * k / 3.4; g.strokeStyle = '#3a4258'; g.stroke(); g.shadowBlur = 0; g.restore();
  poly(H); g.fillStyle = 'rgba(10,14,30,0.92)'; g.fill(); g.lineWidth = 8; g.strokeStyle = '#8b97b3'; g.stroke();
  // cámaras con el color de su tiempo
  for (let i = 0; i < 3; i++) {
    const a0 = th + i * TAU / 3, a1 = a0 + TAU / 3, m = a0 + TAU / 6;
    const pts = []; for (let j = 0; j <= 40; j++) pts.push(P(hp(lerp(a0, a1, j / 40))));
    const A0 = apex(i), A1 = apex(i + 1), dm = RR / 2 + 36;
    const ctrl = [c[0] + dm * Math.cos(m), c[1] + dm * Math.sin(m)];
    for (let j = 40; j >= 0; j--) { const s = j / 40; const x = (1 - s) * (1 - s) * A0[0] + 2 * (1 - s) * s * ctrl[0] + s * s * A1[0], y = (1 - s) * (1 - s) * A0[1] + 2 * (1 - s) * s * ctrl[1] + s * s * A1[1]; pts.push(P([x, y])); }
    poly(pts); g.fillStyle = phaseCol(m, 0.55 * (o.chambers ?? 1)); g.fill();
    // chispa: la cámara pasa por las bujías (abajo)
    const mm = ((m % TAU) + TAU) % TAU, dIg = mm - 3 * Math.PI / 2;
    if (dIg > -0.55 && dIg < 0.08 && (o.chambers ?? 1) > 0) { g.save(); g.globalAlpha = 0.6 * (1 - Math.abs(dIg + 0.25) / 0.35) * (0.7 + 0.3 * Math.sin(T * 60)); poly(pts); g.fillStyle = '#fff1b0'; g.fill(); g.restore(); }
  }
  // rotor
  const R = []; for (let i = 0; i < 3; i++) {
    const A0 = apex(i), A1 = apex(i + 1), m = th + i * TAU / 3 + TAU / 6, dm = RR / 2 + 36;
    const ctrl = [c[0] + dm * Math.cos(m), c[1] + dm * Math.sin(m)];
    for (let j = 0; j < 30; j++) { const s = j / 30; R.push(P([(1 - s) * (1 - s) * A0[0] + 2 * (1 - s) * s * ctrl[0] + s * s * A1[0], (1 - s) * (1 - s) * A0[1] + 2 * (1 - s) * s * ctrl[1] + s * s * A1[1]])); }
  }
  poly(R); const gr = g.createLinearGradient(cx - 300, cy - 300, cx + 300, cy + 300); gr.addColorStop(0, '#dfe5f0'); gr.addColorStop(1, '#7d879c'); g.fillStyle = gr; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
  // engrane interno del rotor, engrane fijo y eje excéntrico
  const C = P(c);
  circle(C[0], C[1], 34 * k); g.fillStyle = '#4a536b'; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
  for (let i = 0; i < 24; i++) { const an = th + i * TAU / 24; g.strokeStyle = '#c8d1e2'; g.lineWidth = 4; line(C[0] + Math.cos(an) * 30 * k, C[1] - Math.sin(an) * 30 * k, C[0] + Math.cos(an) * 34 * k, C[1] - Math.sin(an) * 34 * k); }
  circle(C[0], C[1], 22 * k); g.fillStyle = '#2b3246'; g.fill();
  circle(cx, cy, 15 * k); g.fillStyle = '#8b97b3'; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.stroke();
  g.strokeStyle = YEL; g.lineWidth = 8; line(cx, cy, C[0], C[1]); circle(cx, cy, 7); g.fillStyle = YEL; g.fill();
  // sellos de las puntas
  const sh = o.hl?.sellos ?? 0;
  for (let i = 0; i < 3; i++) {
    const A = P(apex(i)); circle(A[0], A[1], 9 + 9 * sh); g.fillStyle = sh > 0 ? `rgba(255,255,255,${0.7 + 0.3 * sh})` : '#e6ebf5'; g.fill(); g.lineWidth = 3; g.strokeStyle = INK; g.stroke();
    if (sh > 0) { g.save(); g.globalAlpha = sh * (0.5 + 0.3 * Math.sin(T * 8 + i)); circle(A[0], A[1], 34); g.fillStyle = 'rgba(255,216,77,0.45)'; g.fill(); g.restore(); }
  }
  // bujías (abajo, 3 por rotor)
  const bj = o.hl?.bujias ?? 0;
  for (const da of [-0.22, 0, 0.22]) {
    const a = -Math.PI / 2 + da, [x, y] = hp(a), [px, py] = P([x, y]);
    const nx = Math.cos(a), ny = -Math.sin(a), L = (52 + 14 * bj) * k / 3.4;
    g.save(); g.translate(px, py); g.rotate(Math.atan2(ny, nx));
    g.fillStyle = bj > 0 ? '#ffffff' : '#c8d1e2'; g.fillRect(14, -10, L, 20); g.fillStyle = '#5a6380'; g.fillRect(14 + L * 0.35, -15, L * 0.3, 30);
    g.lineWidth = 3; g.strokeStyle = INK; g.strokeRect(14, -10, L, 20);
    g.restore();
  }
  if (bj > 0) for (const da of [-0.22, 0, 0.22]) { const [px, py] = P(hp(-Math.PI / 2 + da)); g.save(); g.globalAlpha = bj; circle(px, py - 4, 18 + 6 * Math.sin(T * 40 + da * 9)); g.fillStyle = 'rgba(79,216,255,0.85)'; g.fill(); g.restore(); }
  // puertos periféricos (arriba): admisión a la derecha, escape a la izquierda
  const pu = o.hl?.puertos ?? 0;
  for (const [da, col, inn] of [[-0.42, CYA, 1], [0.42, '#9aa4ba', -1]]) {
    const a = Math.PI / 2 + da, [px, py] = P(hp(a));
    g.save(); g.translate(px, py); g.fillStyle = '#3a4258'; g.fillRect(-26, -90, 52, 80); g.strokeStyle = INK; g.lineWidth = 4; g.strokeRect(-26, -90, 52, 80);
    g.fillStyle = 'rgba(10,14,30,1)'; g.fillRect(-18, -92, 36, 96);
    g.restore();
    if (pu > 0 || o.flow) {
      const w = Math.max(pu, o.flow ?? 0);
      for (let j = 0; j < 3; j++) { const s = ((T * 1.4 + j / 3) % 1); const y0 = inn > 0 ? lerp(py - 150, py + 10, s) : lerp(py + 10, py - 150, s); g.save(); g.globalAlpha = w * Math.sin(Math.PI * s); arrow(px, y0 - 20 * inn, px, y0 + 20 * inn, 14, col, 1.8); g.restore(); }
    }
  }
  g.restore();
  return { P, apex, c };
}
function rotorLabels(cx, cy, k, a, hl = -1) {
  const L = [['ADMISIÓN', Math.PI / 4, CYA], ['COMPRESIÓN', 7 * Math.PI / 4, YEL], ['EXPLOSIÓN', 5 * Math.PI / 4, ORA], ['ESCAPE', 3 * Math.PI / 4, '#c8d1e2']];
  L.forEach(([s, an, col], i) => {
    const e = backOut(prog(T, a + i * 0.9, a + i * 0.9 + 0.35)); if (e <= 0) return;
    const x = cx + Math.cos(an) * 128 * k * 0.98, y = cy - Math.sin(an) * 104 * k;
    g.save(); g.translate(x, y); g.scale(e, e); tag(s, 0, 0, col, hl === i ? 46 : 40); g.restore();
  });
}
function piston(cx, cy, s, t, cross = 0) {
  const y = Math.sin(t * 7) * 60 * s;
  g.save(); g.lineWidth = 8; g.strokeStyle = '#8b97b3';
  g.strokeRect(cx - 80 * s, cy - 160 * s, 160 * s, 260 * s);
  g.fillStyle = '#c8d1e2'; g.fillRect(cx - 70 * s, cy - 110 * s + y, 140 * s, 70 * s);
  g.strokeStyle = '#c8d1e2'; g.lineWidth = 16 * s; line(cx, cy - 40 * s + y, cx + Math.cos(t * 7) * 30 * s, cy + 150 * s);
  circle(cx, cy + 160 * s, 40 * s); g.lineWidth = 6; g.strokeStyle = '#8b97b3'; g.stroke();
  if (cross > 0) { g.globalAlpha = cross; g.strokeStyle = RED; g.lineWidth = 22; g.lineCap = 'round'; line(cx - 130 * s, cy - 180 * s, cx + 130 * s, cy + 220 * s); line(cx + 130 * s, cy - 180 * s, cx - 130 * s, cy + 220 * s); }
  g.restore();
}

// =====================================================================
// AUTO DE PERFIL (Grupo C, metros; x=0 nariz, y=0 piso)
// =====================================================================
const GC = [[0.0, 0.18], [0.15, 0.36], [0.9, 0.62], [1.55, 0.74], [1.95, 1.0], [2.5, 1.06], [2.95, 1.0], [3.5, 0.86], [4.3, 0.84], [4.62, 0.98], [4.8, 0.98], [4.8, 0.78], [4.7, 0.42], [4.5, 0.16], [0.4, 0.1]];
function gcar(x0, gy, k, body, accent, num, rot) {
  g.save(); g.translate(x0, gy);
  const P = ([x, y]) => [x * k, -y * k];
  g.save(); g.shadowColor = 'rgba(0,0,0,0.5)'; g.shadowBlur = 30; smooth(GC.map(P)); g.fillStyle = body; g.fill(); g.restore();
  smooth(GC.map(P)); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
  // franja y cabina
  poly([[0.5, 0.42], [2.0, 0.6], [3.9, 0.5], [3.9, 0.36], [2.0, 0.44], [0.5, 0.28]].map(P)); g.fillStyle = accent; g.fill();
  smooth([[1.75, 0.92], [2.15, 1.04], [2.75, 1.0], [2.55, 0.84]].map(P)); g.fillStyle = '#1b2235'; g.fill();
  if (num) { circle(...P([3.25, 0.62]), 0.2 * k); g.fillStyle = WHT; g.fill(); txt(num, ...P([3.25, 0.62]), 0.24 * k, INK, { stroke: 0 }); }
  for (const wx of [1.05, 3.85]) {
    const [px, py] = P([wx, 0.33]); circle(px, py, 0.33 * k); g.fillStyle = '#0b0c11'; g.fill();
    circle(px, py, 0.2 * k); g.fillStyle = '#d4af37'; g.fill();
    g.strokeStyle = INK; g.lineWidth = 4; for (let i = 0; i < 6; i++) { const an = rot + i * Math.PI / 3; line(px, py, px + Math.cos(an) * 0.18 * k, py + Math.sin(an) * 0.18 * k); }
  }
  g.restore();
}
function jpFlag(x, y, w, h) { g.fillStyle = WHT; g.fillRect(x, y, w, h); circle(x + w / 2, y + h / 2, h * 0.3); g.fillStyle = '#bc002d'; g.fill(); g.lineWidth = 4; g.strokeStyle = INK; g.strokeRect(x, y, w, h); }

// =====================================================================
// ESCENAS
// =====================================================================
function sceneHook(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('dato', 0), [c, d] = PT('dato', 1);
  // burbuja de respuesta
  const eb = backOut(prog(t, a, a + 0.45));
  if (eb > 0 && t < c - 0.2) {
    g.save(); g.translate(540, 330); g.scale(eb, eb);
    g.beginPath(); g.roundRect(-380, -62, 760, 124, 30); g.fillStyle = 'rgba(255,255,255,0.96)'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke();
    poly([[-300, 58], [-250, 58], [-310, 108]]); g.fillStyle = 'rgba(255,255,255,0.96)'; g.fill();
    circle(-310, 0, 38); g.fillStyle = CYA; g.fill(); txt('N', -310, 3, 44, INK, { stroke: 0 });
    txt('Respuesta a', -250, -18, 34, '#5a6380', { align: 'left', font: 'IX', stroke: 0 });
    txt('@_nachozn_', -250, 24, 50, INK, { align: 'left', stroke: 0 });
    g.restore();
  }
  // foto del 787B
  const z = 1.0 + 0.12 * prog(t, a, d);
  const ep = easeOut(prog(t, a + 0.2, a + 0.8));
  g.save(); g.globalAlpha = ep; g.translate(0, (1 - ep) * 80);
  photo(IMG.m787b, 60, 470, 960, 640, z, 0.42, 0.62, 26, MORA);
  credit('Foto: 韋駄天狗 · CC BY-SA 3.0 · Wikimedia Commons', 1140);
  g.restore();
  if (t < c - 0.2) {
    badge('SIN PISTONES', 540, 1280, backOut(prog(t, a + 3.6, a + 4.2)), YEL, INK, 64, -0.04);
    badge('24 HORAS DE LE MANS', 540, 1420, backOut(prog(t, a + 5.4, a + 6.0)), CYA, INK, 46, 0.03);
  } else {
    const e = backOut(prog(t, c, c + 0.45));
    g.save(); g.translate(540, 1300); g.scale(e, e); txt('1991', 0, 0, 170, YEL, { stroke: 12 }); g.restore();
    const e2 = backOut(prog(t, c + 2.4, c + 2.9));
    if (e2 > 0) { g.save(); g.translate(540, 1460); g.scale(e2, e2); const tw = measure('1.ª VICTORIA JAPONESA', 52), x0 = -(tw + 140) / 2; jpFlag(x0, -40, 110, 74); txt('1.ª VICTORIA JAPONESA', x0 + 140, -3, 52, WHT, { stroke: 7, align: 'left' }); g.restore(); }
    label(t, c - 0.2, d + 0.6, 'MAZDA 787B', ['ganador de Le Mans'], WHT, 110);
  }
}
function sceneMotor(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('motor', 0);
  label(t, a - 0.3, b + 0.6, 'MOTOR R26B', ['rotativo · 4 rotores'], YEL, 120);
  // 4 rotores en fila que entran uno por uno
  for (let i = 0; i < 4; i++) {
    const e = backOut(prog(t, a + 1.2 + i * 0.35, a + 1.6 + i * 0.35)); if (e <= 0) continue;
    const cx = 540 + (i - 1.5) * 255, cy = 900 + (i % 2 ? 40 : -40);
    g.save(); g.translate(cx, cy); g.scale(e, e); rotary(0, 0, 1.0, -t * 5 - i * Math.PI / 2, {}); g.restore();
    txt(String(i + 1), cx, cy + 135, 52, YEL, { stroke: 6, alpha: e });
  }
  badge('SIN PISTONES · SIN VÁLVULAS', 540, 1260, backOut(prog(t, a + 3.0, a + 3.5)), CYA, INK, 46);
}
const RK = 3.3, RCY = 960;
function sceneRotor(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('rotor', 0), [c, d] = PT('rotor', 1), [e, f] = PT('rotor', 2);
  if (t < c - 0.25) {
    label(t, a - 0.3, c - 0.2, 'PISTÓN VS ROTOR', ['sube y baja · gira'], WHT, 104);
    const sw = ease(prog(t, a + 2.4, a + 3.4));
    piston(lerp(540, 230, sw), 940, 1.1 - 0.35 * sw, t, ease(prog(t, a + 3.0, a + 3.5)));
    if (sw > 0) { g.save(); g.globalAlpha = sw; rotary(lerp(1100, 680, sw), RCY, 1.75, -t * 2.6, { chambers: 0.6 }); g.restore(); }
    if (sw > 0.8) { tag('TRIÁNGULO', 680, 1240, YEL, 42, (sw - 0.8) * 5); tag('cámara OVALADA', 680, 680, CYA, 40, (sw - 0.8) * 5); }
  } else {
    rotary(540, RCY, RK, -t * 1.6, { chambers: 1 });
    if (t < e - 0.25) {
      label(t, c - 0.2, e - 0.2, '4 TIEMPOS', ['en cada cara del rotor'], YEL, 116);
      rotorLabels(540, RCY, RK, c + 0.9);
    } else {
      label(t, e - 0.2, f + 0.6, 'SIN VÁLVULAS', ['menos piezas · muy suave'], CYA, 116);
      badge('0 VÁLVULAS', 540, 1390, backOut(prog(t, e + 0.4, e + 0.9)), YEL, INK, 60, -0.03);
    }
  }
}
function sceneR26B(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('r26b', 0), [c, d] = PT('r26b', 1);
  if (t < c - 0.25) {
    label(t, a - 0.3, c - 0.2, '4 × 654 cc', ['= 2,616 cc'], YEL, 130);
    for (let i = 0; i < 4; i++) {
      const e = backOut(prog(t, a + 0.6 + i * 0.4, a + 1.0 + i * 0.4)); if (e <= 0) continue;
      const cx = 160 + i * 253, cy = 900;
      g.save(); g.translate(cx, cy); g.scale(e, e);
      g.beginPath(); g.roundRect(-115, -230, 230, 460, 30); g.fillStyle = 'rgba(6,10,24,0.85)'; g.fill(); g.lineWidth = 5; g.strokeStyle = 'rgba(79,216,255,0.6)'; g.stroke();
      g.save(); g.rotate(Math.PI / 2); rotary(0, 0, 0.9, -t * 6 - i * Math.PI / 2, {}); g.restore();
      txt('654 cc', 0, 185, 42, WHT, { stroke: 5 });
      g.restore();
    }
    // RX-7 de calle
    const r = backOut(prog(t, a + 5.0, a + 5.5));
    if (r > 0) { g.save(); g.translate(540, 1300); g.scale(r, r); tag('MISMA FORMA QUE EL RX-7', 0, 0, YEL, 50); g.restore(); }
  } else {
    label(t, c - 0.2, d + 0.6, '700 CABALLOS', ['a 9,000 RPM'], YEL, 120);
    // tacómetro
    const cx = 540, cy = 990, R = 330, v = ease(prog(t, c + 0.3, c + 3.2)) * 9000 + (t > c + 3.2 ? Math.sin(t * 30) * 60 : 0);
    circle(cx, cy, R + 30); g.fillStyle = 'rgba(6,10,24,0.88)'; g.fill(); g.lineWidth = 8; g.strokeStyle = 'rgba(79,216,255,0.6)'; g.stroke();
    const a0 = Math.PI * 0.75, span = Math.PI * 1.5;
    g.lineWidth = 28; g.lineCap = 'butt'; g.strokeStyle = 'rgba(255,77,94,0.85)'; g.beginPath(); g.arc(cx, cy, R - 20, a0 + span * 9000 / 10000, a0 + span); g.stroke();
    for (let i = 0; i <= 10; i++) { const an = a0 + span * i / 10; g.strokeStyle = WHT; g.lineWidth = 6; line(cx + Math.cos(an) * (R - 50), cy + Math.sin(an) * (R - 50), cx + Math.cos(an) * (R - 90), cy + Math.sin(an) * (R - 90)); txt(String(i), cx + Math.cos(an) * (R - 130), cy + Math.sin(an) * (R - 130), 40, WHT, { stroke: 4 }); }
    const an = a0 + span * v / 10000; g.strokeStyle = MORA; g.lineWidth = 14; g.lineCap = 'round'; line(cx, cy, cx + Math.cos(an) * (R - 60), cy + Math.sin(an) * (R - 60));
    circle(cx, cy, 30); g.fillStyle = MORA; g.fill();
    txt(Math.round(v).toLocaleString('en-US'), cx, cy + 262, 70, WHT, { stroke: 7 }); txt('RPM × 1000', cx, cy - 120, 34, CYA, { font: 'IX', stroke: 4 });
    const w = backOut(prog(t, d - 1.6, d - 1.1));
    if (w > 0) badge('¡VAMOS A DESARMARLO!', 540, 1420, w, YEL, INK, 52, -0.03);
  }
}
// ---------------- desarmado ----------------
const PARTS = ['pbujias', 'padmision', 'ppuertos', 'psellos', 'psonido'];
function partAmt(t, id) { return fade(t, S(id) - 0.3, E(id) + 0.15, 0.35); }
function sceneParts(t) {
  drawBG(t, 0.5);
  const idx = PARTS.findIndex(id => t < E(id) + 0.45);
  const id = PARTS[Math.max(0, idx)], amt = partAmt(t, id), [a, b] = PT(id, 0);
  const rpm = id === 'padmision' ? 0.5 + 0.5 * Math.sin((t - a) * 1.1) : 0.6;
  const speed = id === 'psonido' ? 7 : 2.2;
  const cy = id === 'padmision' ? 1130 : RCY + 20;
  // trompetas de admisión variable
  if (id === 'padmision') {
    const len = lerp(200, 70, ease(0.5 + 0.5 * Math.sin((t - a) * 1.3)));
    const [px, py] = [540 + hp(Math.PI / 2 - 0.42)[0] * RK, cy - hp(Math.PI / 2 - 0.42)[1] * RK - 92];
    g.save(); g.globalAlpha = amt;
    g.fillStyle = '#c8d1e2'; g.beginPath(); g.moveTo(px - 26, py); g.lineTo(px - 26, py - len); g.lineTo(px - 52, py - len - 40); g.lineTo(px + 52, py - len - 40); g.lineTo(px + 26, py - len); g.lineTo(px + 26, py); g.closePath(); g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke();
    const long = len > 135;
    tag(long ? 'LARGA = FUERZA ABAJO' : 'CORTA = POTENCIA ARRIBA', 330, 640, long ? CYA : YEL, 36);
    g.restore();
  }
  rotary(540, cy, RK, -t * speed, { chambers: 0.8, flow: id === 'padmision' ? 0.6 : 0, hl: { bujias: id === 'pbujias' ? amt : 0, puertos: id === 'ppuertos' ? amt : 0, sellos: id === 'psellos' ? amt : 0 } });
  const titles = { pbujias: ['3 BUJÍAS', 'por rotor'], padmision: ['ADMISIÓN VARIABLE', 'las trompetas cambian de largo'], ppuertos: ['PUERTOS PERIFÉRICOS', 'el aire entra por la orilla'], psellos: ['SELLOS DE CERÁMICA', 'en las 3 puntas del rotor'], psonido: ['EL SONIDO', 'un grito agudo'] };
  const [ti, su] = titles[id];
  label(t, S(id) - 0.3, E(id) + 0.15, ti, [su], id === 'psonido' ? YEL : WHT, ti.length > 14 ? 84 : 104, PARTS.indexOf(id) + 1);
  if (id === 'pbujias') { const e = backOut(prog(t, a + 1.2, a + 1.7)); if (e > 0) badge('QUEMA MEJOR LA GASOLINA', 540, 1420, e, YEL, INK, 46); }
  if (id === 'ppuertos') { const e = backOut(prog(t, a + 2.5, a + 3.0)); if (e > 0) badge('RESPIRA A ALTAS RPM', 540, 1420, e, CYA, INK, 50); }
  if (id === 'psellos') {
    const e = easeOut(prog(t, a + 3.4, a + 4.0));
    if (e > 0) { g.save(); g.globalAlpha = e * amt; photo(IMG.wankel, 40, 1250, 230, 294, 1.0, 0.5, 0.5, 18, YEL); txt('Foto: Softeis · CC BY-SA 3.0', 155, 1228, 20, 'rgba(255,255,255,0.9)', { font: 'IX', stroke: 4 }); g.restore(); }
    const e2 = backOut(prog(t, a + 2.0, a + 2.5)); if (e2 > 0) badge('PUNTO DÉBIL', 790, 1420, e2, RED, WHT, 54, -0.05);
  }
  if (id === 'psonido') {
    // ondas de sonido
    for (let i = 0; i < 6; i++) { const s = ((t * 1.3 + i / 6) % 1); g.save(); g.globalAlpha = amt * (1 - s) * 0.8; g.lineWidth = 10; g.strokeStyle = i % 2 ? YEL : CYA; g.beginPath(); g.arc(540, RCY + 20, 360 + s * 380, -0.5, 0.5); g.stroke(); g.beginPath(); g.arc(540, RCY + 20, 360 + s * 380, Math.PI - 0.5, Math.PI + 0.5); g.stroke(); g.restore(); }
    const e = backOut(prog(t, a + 2.2, a + 2.7)); if (e > 0) badge('¡LEYENDA!', 540, 1420, e, YEL, INK, 70, -0.05);
  }
}
function sceneChasis(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('chasis', 0);
  label(t, a - 0.3, b + 0.6, 'CARBONO + KEVLAR', ['un chasis ligerísimo'], WHT, 100);
  photo(IMG.m787b, 60, 520, 960, 520, 1.15 + 0.06 * prog(t, a, b), 0.38, 0.6, 26, MGRN);
  credit('Foto: 韋駄天狗 · CC BY-SA 3.0 · Wikimedia Commons', 1066);
  // barras de peso
  const s = ease(prog(t, a + 2.0, a + 3.6)), y0 = 1450, H1 = 300;
  const bars = [['MAZDA', 830, MGRN], ['JAGUAR / MERCEDES', 1000, SILV]];
  bars.forEach(([n, v, col], i) => {
    const x = 300 + i * 480, h = H1 * v / 1000 * s;
    g.fillStyle = col; g.fillRect(x - 90, y0 - h, 180, h); g.lineWidth = 5; g.strokeStyle = INK; g.strokeRect(x - 90, y0 - h, 180, h);
    if (s > 0.05) { txt(`${Math.round(v * s).toLocaleString('en-US')} KG`, x, y0 - h - 40, 52, i ? WHT : YEL, { stroke: 6 }); txt(n, x, y0 + 40, i ? 34 : 40, CYA, { font: 'IX', stroke: 5 }); }
  });
}
function scenePilotos(t) {
  drawBG(t, 0.6);
  const [a, b] = PT('pilotos', 0), [c, d] = PT('pilotos', 1);
  if (t < c - 0.25) {
    label(t, a - 0.3, c - 0.2, 'LOS PILOTOS', ['sus manos en Le Mans'], WHT, 110);
    photo(IMG.lm1991, 90, 520, 900, 666, 1.05 + 0.08 * prog(t, a, c), 0.5, 0.5, 26, YEL);
    credit('Foto: OldLion · CC BY-SA 4.0 · Wikimedia Commons', 1212);
    ['VOLKER WEIDLER', 'JOHNNY HERBERT', 'BERTRAND GACHOT'].forEach((n, i) => { const e = backOut(prog(t, a + 0.5 + i * 0.9, a + 0.9 + i * 0.9)); if (e > 0) { g.save(); g.translate(540, 1300 + i * 82); g.scale(e, e); tag(n, 0, 0, i === 1 ? YEL : CYA, 44); g.restore(); } });
  } else {
    label(t, c - 0.2, d + 0.6, 'SALIERON 19.°', ['rápido y gastando poco'], YEL, 110);
    // parrilla de salida: el 55 en el lugar 19
    for (let i = 0; i < 6; i++) {
      const y = 620 + i * 100, x = 540 + (i % 2 ? 140 : -140), p19 = i === 5;
      g.fillStyle = p19 ? 'rgba(255,216,77,0.22)' : 'rgba(255,255,255,0.10)'; g.fillRect(x - 160, y - 40, 320, 80);
      g.lineWidth = 4; g.strokeStyle = p19 ? YEL : 'rgba(255,255,255,0.35)'; g.strokeRect(x - 160, y - 40, 320, 80);
      txt(`${14 + i}`, x - 210, y, 44, p19 ? YEL : 'rgba(255,255,255,0.6)', { stroke: 5 });
      if (!p19) gcar(x - 130, y + 30, 54, 'rgba(185,194,211,0.55)', '#2b3246', null, 0);
    }
    gcar(540 + 140 - 130, 620 + 5 * 100 + 30, 54, MGRN, MORA, '55', 0);
    badge('LUGAR 19', 830, 1080, backOut(prog(t, c + 0.6, c + 1.1)), YEL, INK, 44, -0.05);
    // medidor de gasolina
    const fu = 1 - 0.65 * ease(prog(t, c + 2.5, d - 0.5));
    const gx = 540, gy = 1330;
    g.beginPath(); g.roundRect(gx - 300, gy - 40, 600, 80, 40); g.fillStyle = 'rgba(6,10,24,0.85)'; g.fill(); g.lineWidth = 5; g.strokeStyle = CYA; g.stroke();
    g.beginPath(); g.roundRect(gx - 290, gy - 30, 580 * fu, 60, 30); g.fillStyle = fu > 0.5 ? MGRN : YEL; g.fill();
    txt('GASOLINA', gx, gy, 40, WHT, { stroke: 5 });
  }
}
function sceneCarrera(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('carrera', 0), [c, d] = PT('carrera', 1);
  const y = 1180;
  g.fillStyle = '#1d2333'; g.fillRect(0, y - 10, W, 190); g.fillStyle = 'rgba(255,255,255,0.75)'; g.fillRect(0, y - 10, W, 6);
  for (let i = 0; i < 9; i++) { const x = ((i * 160 - t * 900) % 1440 + 1440) % 1440 - 180; g.fillStyle = 'rgba(255,255,255,0.55)'; g.fillRect(x, y + 80, 90, 10); }
  if (t < c - 0.25) {
    label(t, a - 0.3, c - 0.2, 'HORA 22', ['quedan poco más de 2 horas'], WHT, 110);
    const brk = prog(t, a + 2.2, a + 2.6), pass = ease(prog(t, a + 3.4, b - 0.2));
    // Mercedes adelante que se rompe
    gcar(lerp(470, 470 - 900 * pass, 1) - 0, y + 50, 90, SILV, '#2b3246', '1', t * (16 - 14 * brk));
    if (brk > 0) for (let i = 0; i < 8; i++) { const s = ((t * 0.9 + i / 8) % 1); g.save(); g.globalAlpha = brk * (1 - s) * 0.7; circle(470 - 900 * pass + 4.1 * 90 + s * 120, y - 20 - s * 260, 30 + s * 60); g.fillStyle = '#9aa4ba'; g.fill(); g.restore(); }
    if (brk > 0) badge('¡SE ROMPIÓ!', 400 - 900 * pass, 860, backOut(prog(t, a + 2.3, a + 2.8)), RED, WHT, 56, -0.06);
    // Mazda 55 que pasa
    gcar(lerp(-460, 520, pass), y + 50, 90, MGRN, MORA, '55', t * 16);
    if (pass > 0.7) badge('P1 · MAZDA 55', 760, 860, backOut(prog(t, lerp(a + 3.4, b - 0.2, 0.7), lerp(a + 3.4, b - 0.2, 0.85))), YEL, INK, 56, 0.04);
  } else {
    label(t, c - 0.2, d + 0.6, '¡META!', ['Herbert, deshidratado'], YEL, 130);
    const fx = 830, fy = 600;
    g.strokeStyle = WHT; g.lineWidth = 10; line(fx - 140, fy - 40, fx - 140, fy + 360);
    for (let i = 0; i < 6; i++) for (let j = 0; j < 4; j++) { g.fillStyle = (i + j) % 2 ? WHT : INK; g.fillRect(fx - 135 + i * 45, fy - 40 + j * 45 + Math.sin(t * 8 + i) * 6, 45, 45); }
    for (let i = 0; i < 12; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? WHT : INK; g.fillRect(i * 90, y - 4 + j * 45, 90, 45); }
    const u = ease(prog(t, c, c + 2.2));
    gcar(lerp(-450, 300, u), y + 50, 90, MGRN, MORA, '55', t * 16 * (1 - 0.6 * u));
    const e = backOut(prog(t, c + 2.6, c + 3.1));
    if (e > 0) { g.save(); g.translate(300, 820); g.scale(e, e); g.beginPath(); g.moveTo(0, -80); g.bezierCurveTo(60, 0, 60, 60, 0, 60); g.bezierCurveTo(-60, 60, -60, 0, 0, -80); g.fillStyle = CYA; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke(); g.restore(); tag('SIN PODIO', 300, 950, CYA, 42, e); }
  }
}
function sceneFinal(t) {
  drawBG(t, 0.5);
  const [a, b] = PT('final', 0), [c, d] = PT('final', 1);
  if (t < c - 0.25) {
    label(t, a - 0.3, c - 0.2, 'DESDE 1992', ['el rotativo quedó fuera'], WHT, 110);
    rotary(540, 960, 2.4, -t * 1.2, { chambers: 0.5 });
    const e = ease(prog(t, a + 2.2, a + 2.9));
    if (e > 0) { g.save(); g.globalAlpha = e; g.lineWidth = 34; g.strokeStyle = RED; circle(540, 960, 360); g.stroke(); line(540 - 255, 960 + 255, 540 + 255, 960 - 255); g.restore(); }
  } else {
    label(t, c - 0.2, d + 0.6, 'ÚNICO', ['el único triunfo sin pistones'], YEL, 150);
    photo(IMG.m787b, 60, 560, 960, 640, 1.0 + 0.1 * prog(t, c, d), 0.42, 0.62, 26, YEL);
    credit('Foto: 韋駄天狗 · CC BY-SA 3.0 · Wikimedia Commons', 1226);
    const e = backOut(prog(t, c + 4.2, c + 4.7));
    if (e > 0) badge('SU ÚLTIMA OPORTUNIDAD', 540, 1380, e, YEL, INK, 54, -0.03);
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
  const r0 = S('rotor'), r2 = S('r26b'), ca = S('carrera');
  if (t < M0) sceneHook(t);
  else if (t < r0 - 0.3) sceneMotor(t);
  else if (t < r2 - 0.3) crossfade(t, r0 - 0.3, r0 + 0.1, sceneMotor, sceneRotor);
  else if (t < D0) crossfade(t, r2 - 0.3, r2 + 0.1, sceneRotor, sceneR26B);
  else if (t < K0) sceneParts(t);
  else if (t < P0) sceneChasis(t);
  else if (t < ca - 0.3) scenePilotos(t);
  else if (t < F0) crossfade(t, ca - 0.3, ca + 0.1, scenePilotos, sceneCarrera);
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
