// "Neo" deck style: violet + cyan on black and white, giant gradient numerals,
// grid-and-glow dark slides, lavender cards, hairlines. Same JSON spec as build_deck.js.
// Usage: node build_deck_neo.js spec.json out.pptx
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const md = require("react-icons/md");
const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");

const [, , specPath, outPath] = process.argv;
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));

// palette (fixed, from the reference style)
const K = {
  ink: "0B0B12", ink2: "15151F", violet: "6C4CF5", violet2: "8B78FF", cyan: "22D3EE",
  lav: "F3F1FF", lav2: "E8E4FF", gray: "6B7280", gray2: "9CA3AF", line: "E5E7EB", white: "FFFFFF", text: "111118",
  red: "F0445A", amber: "F5A524", green: "22C55E",
};
const FONT = "Arial";
const THEME = {
  name: (spec.short || "Deck").replace(/&/g, "and"), headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: K.text, lt1: K.white, dk2: K.ink, lt2: K.lav, accent1: K.violet, accent2: K.cyan, accent3: K.violet2,
            accent4: "A78BFA", accent5: "0EA5E9", accent6: K.gray, hlink: K.violet, folHlink: K.violet2 },
};
const W = 13.333, H = 7.5, MX = 0.7;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = spec.title; pres.author = spec.team || "Team";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
const TMP = fs.mkdtempSync(path.join(require("os").tmpdir(), "neo-"));
let imgN = 0;

// ---------- generated artwork ----------
async function png(svg, w, h) {
  const f = path.join(TMP, `a${imgN++}.png`);
  await sharp(Buffer.from(svg)).resize(w, h).png().toFile(f);
  return f;
}
async function darkBg() {
  const w = 2666, h = 1500, step = 75;
  let lines = "";
  for (let x = 0; x <= w; x += step) lines += `<line x1="${x}" y1="0" x2="${x}" y2="${h}" stroke="#ffffff" stroke-opacity="0.045"/>`;
  for (let y = 0; y <= h; y += step) lines += `<line x1="0" y1="${y}" x2="${w}" y2="${y}" stroke="#ffffff" stroke-opacity="0.045"/>`;
  return png(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">
    <defs><radialGradient id="g" cx="78%" cy="85%" r="55%"><stop offset="0" stop-color="#6C4CF5" stop-opacity="0.55"/>
    <stop offset="0.45" stop-color="#6C4CF5" stop-opacity="0.12"/><stop offset="1" stop-color="#0B0B12" stop-opacity="0"/></radialGradient>
    <radialGradient id="g2" cx="8%" cy="0%" r="40%"><stop offset="0" stop-color="#22D3EE" stop-opacity="0.18"/><stop offset="1" stop-color="#0B0B12" stop-opacity="0"/></radialGradient></defs>
    <rect width="100%" height="100%" fill="#0B0B12"/>${lines}<rect width="100%" height="100%" fill="url(#g)"/><rect width="100%" height="100%" fill="url(#g2)"/></svg>`, w, h);
}
async function violetBg() {
  const w = 2666, h = 1500;
  return png(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">
    <defs><linearGradient id="v" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7B5CFF"/><stop offset="1" stop-color="#5A3CE6"/></linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#v)"/>
    <circle cx="${w * 0.73}" cy="${h * 0.56}" r="${h * 0.2}" fill="#ffffff" fill-opacity="0.95"/>
    <circle cx="${w * 0.86}" cy="${h * 0.56}" r="${h * 0.2}" fill="#22D3EE" fill-opacity="0.92"/>
    <circle cx="${w * 0.795}" cy="${h * 0.56}" r="${h * 0.2}" fill="none" stroke="#ffffff" stroke-opacity="0.35" stroke-width="3"/></svg>`, w, h);
}
function esc(t) { return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
// gradient (violet -> cyan) or solid numerals as an image, sized to fit a box
async function bigText(text, boxW, boxH, { grad = true, color = K.violet, weight = 800 } = {}) {
  const scale = 300; // px per inch
  const pw = Math.round(boxW * scale), ph = Math.round(boxH * scale);
  const len = [...String(text)].reduce((a, c) => a + (/[　-鿿＀-￯]/.test(c) ? 1.0 : 0.58), 0);
  const fs_ = Math.min(ph * 0.92, pw / Math.max(len, 1));
  const fill = grad ? "url(#tg)" : `#${color}`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${pw}" height="${ph}">
    <defs><linearGradient id="tg" x1="0" y1="0" x2="1" y2="0.4"><stop offset="0" stop-color="#8B78FF"/><stop offset="0.55" stop-color="#6C8BFF"/><stop offset="1" stop-color="#22D3EE"/></linearGradient></defs>
    <text x="0" y="${ph * 0.5}" dominant-baseline="central" font-family="Arial, Helvetica, sans-serif" font-weight="${weight}"
      font-size="${fs_}" letter-spacing="${-fs_ * 0.03}" fill="${fill}">${esc(text)}</text></svg>`;
  return png(svg, pw, ph);
}
const iconCache = {};
async function iconPng(name, color) {
  const key = name + color;
  if (iconCache[key]) return iconCache[key];
  const Comp = fa[name] || md[name] || fa.FaCircle;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: 256 }));
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return (iconCache[key] = "image/png;base64," + buf.toString("base64"));
}

// ---------- layouts ----------
let BG_DARK, BG_VIOLET;
function defineMasters() {
  pres.defineSlideMaster({ title: "NEO_DARK", background: { path: BG_DARK },
    objects: [{ placeholder: { options: { name: "title", type: "title", x: MX, y: 0.55, w: 11.9, h: 1.0, fontSize: 28, bold: true, color: K.white, align: "left", valign: "top", margin: 0 }, text: "" } }],
    slideNumber: { x: 12.15, y: 6.95, w: 0.5, h: 0.3, fontSize: 10, color: K.gray2, align: "right" } });
  pres.defineSlideMaster({ title: "NEO_LIGHT", background: { color: K.white },
    objects: [{ placeholder: { options: { name: "title", type: "title", x: MX, y: 0.55, w: 11.9, h: 1.0, fontSize: 28, bold: true, color: K.text, align: "left", valign: "top", margin: 0 }, text: "" } }],
    slideNumber: { x: 12.15, y: 6.95, w: 0.5, h: 0.3, fontSize: 10, color: K.gray2, align: "right" } });
  pres.defineSlideMaster({ title: "NEO_VIOLET", background: { path: BG_VIOLET }, objects: [] });
}
function overline(s, text, dark) {
  if (!text) return;
  s.addText(String(text).toUpperCase(), { x: MX, y: 0.3, w: 9, h: 0.28, fontSize: 10.5, bold: true, charSpacing: 3,
    color: dark ? K.cyan : K.violet, margin: 0, isTextBox: true });
}
function footer(s, dark) {
  s.addText(spec.short || "", { x: MX, y: 6.95, w: 6, h: 0.3, fontSize: 10, color: dark ? K.gray2 : K.gray2, margin: 0, isTextBox: true });
}
function source(s, text, dark) {
  if (!text) return;
  s.addText(text, { x: MX, y: 6.6, w: 11.4, h: 0.3, fontSize: 8.5, color: dark ? "8B8BA0" : K.gray2, margin: 0, isTextBox: true, valign: "bottom" });
}
function panel(s, x, y, w, h, { fill = K.lav, line = null, radius = 0.14 } = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: radius, fill: { color: fill }, line: line ? { color: line, width: 0.75 } : { color: fill } });
}
function bl(items, o = {}) {
  return items.map((t, i) => ({ text: typeof t === "string" ? t : t.text, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 7, ...o } }));
}
const ACC = [K.violet, "0EA5E9", K.violet2, K.cyan];
const LEVEL = { "UGen300": K.violet, "Host CPU": "0EA5E9", "Edge I/O": "A78BFA", "Cloud (optional)": K.gray2 };

// ---------- renderers ----------
const R = {};
R.title = async (s, d) => {
  // optional cover art: a full-height panel on the right that replaces the abstract circles of the violet background
  if (d.art) s.addImage({ path: d.art, x: 13.333 - 5.6, y: 0, w: 5.6, h: 7.5 });
  s.addText((d.tagline || "").toUpperCase(), { x: MX, y: 0.55, w: 7, h: 0.3, fontSize: 11, bold: true, charSpacing: 3, color: "E9E5FF", margin: 0, isTextBox: true });
  s.addImage({ path: await bigText(d.title, 7.2, 1.5, { grad: false, color: "FFFFFF" }), x: MX, y: 1.55, w: 7.2, h: 1.5 });
  s.addText(d.subtitle || "", { x: MX, y: 3.25, w: 6.2, h: 1.0, fontSize: 20, color: "F4F2FF", margin: 0, isTextBox: true, valign: "top" });
  let x = MX, y = 4.75;
  for (const c of d.chips || []) {
    const w = 0.35 + c.length * 0.1;
    if (x + w > 7.3) { x = MX; y += 0.55; }  // wrap before the circles
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.42, rectRadius: 0.21, fill: { color: "FFFFFF", transparency: 82 }, line: { color: "FFFFFF", transparency: 40, width: 0.75 } });
    s.addText(c, { x, y, w, h: 0.42, fontSize: 12, color: "FFFFFF", bold: true, align: "center", valign: "middle", margin: 0, isTextBox: true });
    x += w + 0.15;
  }
  if (d.footer) s.addText(d.footer, { x: MX, y: 6.75, w: 8, h: 0.35, fontSize: 11, color: "E9E5FF", margin: 0, isTextBox: true });
};
R.section = async (s, d) => {
  if (d.number) s.addImage({ path: await bigText(d.number, 3, 1.6), x: MX, y: 1.7, w: 3, h: 1.6 });
  s.addText(d.title, { x: MX, y: 3.5, w: 11, h: 1.0, fontSize: 40, bold: true, color: K.white, margin: 0, isTextBox: true });
  if (d.subtitle) s.addText(d.subtitle, { x: MX, y: 4.5, w: 10, h: 0.7, fontSize: 18, color: "C9C9D6", margin: 0, isTextBox: true });
};
R.stats = async (s, d) => {
  // first stat is the hero (huge gradient numeral on dark); others are a column of smaller tiles
  const [hero, ...rest] = d.stats;
  s.addImage({ path: await bigText(hero.value, 6.2, 2.2), x: MX, y: 1.75, w: 6.2, h: 2.2 });
  s.addText(hero.label, { x: MX, y: 4.05, w: 5.8, h: 1.0, fontSize: 18, color: "D6D6E2", margin: 0, isTextBox: true, valign: "top" });
  const x = 7.35, w = 5.25, gap = 0.18, h = Math.min(1.45, (4.75 - gap * (rest.length - 1)) / Math.max(rest.length, 1));
  for (let i = 0; i < rest.length; i++) {
    const y = 1.75 + i * (h + gap);
    panel(s, x, y, w, h, { fill: K.ink2, line: "2A2A3A" });
    s.addImage({ path: await bigText(rest[i].value, 1.9, h * 0.6, { grad: i % 2 === 0 }), x: x + 0.25, y: y + h * 0.2, w: 1.9, h: h * 0.6 });
    s.addText(rest[i].label, { x: x + 2.3, y, w: w - 2.5, h, fontSize: 13, color: "D6D6E2", margin: 0, isTextBox: true, valign: "middle" });
  }
  if (d.takeaway) s.addText(d.takeaway, { x: MX, y: 5.35, w: 6.2, h: 1.0, fontSize: 15, bold: true, color: K.white, margin: 0, isTextBox: true, valign: "top" });
};
R.cards = async (s, d) => {
  const n = d.cards.length, cols = d.cols || (n <= 3 ? n : n === 4 ? 2 : 3), rows = Math.ceil(n / cols), gap = 0.25;
  const top = d.lead ? 2.15 : 1.75;
  if (d.lead) s.addText(d.lead, { x: MX, y: 1.5, w: 11.9, h: 0.5, fontSize: 15, color: K.gray, margin: 0, isTextBox: true });
  const w = (11.9 - gap * (cols - 1)) / cols, h = (6.45 - top - gap * (rows - 1)) / rows;
  for (let i = 0; i < n; i++) {
    const c = d.cards[i], x = MX + (i % cols) * (w + gap), y = top + Math.floor(i / cols) * (h + gap);
    panel(s, x, y, w, h, { fill: K.lav });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.28, y: y + 0.28, w: 0.62, h: 0.62, rectRadius: 0.12, fill: { color: K.white }, line: { color: K.lav2, width: 0.75 } });
    s.addImage({ data: await iconPng(c.icon, K.violet), x: x + 0.41, y: y + 0.41, w: 0.36, h: 0.36 });
    s.addText(c.head, { x: x + 1.05, y: y + 0.28, w: w - 1.3, h: 0.62, fontSize: 16, bold: true, color: K.text, margin: 0, isTextBox: true, valign: "middle" });
    s.addText(c.body, { x: x + 0.28, y: y + 1.05, w: w - 0.56, h: h - 1.2, fontSize: 12.5, color: "4B5563", margin: 0, isTextBox: true, valign: "top" });
  }
};
R.twocol = async (s, d) => {
  const top = 1.75, gap = 0.3, w = (11.9 - gap) / 2, h = d.verdict ? 3.9 : 4.7;
  panel(s, MX, top, w, h, { fill: K.lav });
  panel(s, MX + w + gap, top, w, h, { fill: K.ink });
  s.addText(d.left.head, { x: MX + 0.35, y: top + 0.3, w: w - 0.7, h: 0.5, fontSize: 19, bold: true, color: K.text, margin: 0, isTextBox: true });
  s.addText(bl(d.left.bullets), { x: MX + 0.35, y: top + 0.95, w: w - 0.7, h: h - 1.15, fontSize: 14, color: "374151", margin: 0, isTextBox: true, valign: "top" });
  const x2 = MX + w + gap;
  s.addText(d.right.head, { x: x2 + 0.35, y: top + 0.3, w: w - 0.7, h: 0.5, fontSize: 19, bold: true, color: K.cyan, margin: 0, isTextBox: true });
  s.addText(bl(d.right.bullets, { color: "E5E7EB" }), { x: x2 + 0.35, y: top + 0.95, w: w - 0.7, h: h - 1.15, fontSize: 14, color: "E5E7EB", margin: 0, isTextBox: true, valign: "top" });
  if (d.verdict) {
    s.addShape(pres.shapes.LINE, { x: MX, y: 5.95, w: 0, h: 0.5, line: { color: K.violet, width: 3 } });
    s.addText(d.verdict, { x: MX + 0.25, y: 5.9, w: 11.6, h: 0.6, fontSize: 16, bold: true, color: K.text, margin: 0, isTextBox: true, valign: "middle" });
  }
};
R.flow = async (s, d) => {
  const n = d.steps.length, top = d.lead ? 2.3 : 1.95;
  if (d.lead) s.addText(d.lead, { x: MX, y: 1.5, w: 11.9, h: 0.5, fontSize: 15, color: K.gray, margin: 0, isTextBox: true });
  const gap = 0.22, w = (11.9 - gap * (n - 1)) / n, h = d.note ? 2.75 : 3.9;
  s.addShape(pres.shapes.LINE, { x: MX + w / 2, y: top + 0.32, w: (n - 1) * (w + gap), h: 0, line: { color: K.lav2, width: 2 } });
  for (let i = 0; i < n; i++) {
    const st = d.steps[i], x = MX + i * (w + gap);
    s.addShape(pres.shapes.OVAL, { x: x + w / 2 - 0.32, y: top, w: 0.64, h: 0.64, fill: { color: i === n - 1 ? K.violet : K.white }, line: { color: K.violet, width: 1.5 } });
    s.addText(String(i + 1).padStart(2, "0"), { x: x + w / 2 - 0.32, y: top, w: 0.64, h: 0.64, fontSize: 13, bold: true, color: i === n - 1 ? K.white : K.violet, align: "center", valign: "middle", margin: 0, isTextBox: true });
    panel(s, x, top + 0.85, w, h, { fill: K.lav });
    s.addText(st.head, { x: x + 0.2, y: top + 1.0, w: w - 0.4, h: 0.75, fontSize: 15, bold: true, color: K.text, margin: 0, isTextBox: true, valign: "top" });
    s.addText(st.body, { x: x + 0.2, y: top + 1.75, w: w - 0.4, h: h - 1.6, fontSize: 12, color: "4B5563", margin: 0, isTextBox: true, valign: "top" });
    if (st.where) {
      const c = LEVEL[st.where] || K.violet2;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.2, y: top + 0.85 + h - 0.48, w: w - 0.4, h: 0.32, rectRadius: 0.16, fill: { color: c }, line: { color: c } });
      s.addText(st.where, { x: x + 0.2, y: top + 0.85 + h - 0.48, w: w - 0.4, h: 0.32, fontSize: 10.5, bold: true, color: K.white, align: "center", valign: "middle", margin: 0, isTextBox: true });
    }
  }
  if (d.note) { const ny = top + 0.85 + h + 0.18; s.addText(d.note, { x: MX, y: ny, w: 11.9, h: 6.5 - ny, fontSize: 12.5, color: K.gray, margin: 0, isTextBox: true, valign: "top" }); }
};
R.arch = async (s, d) => {
  const top = 1.7, n = d.layers.length, gap = 0.14, sideW = d.side ? 3.4 : 0;
  const totalW = 11.9 - (sideW ? sideW + 0.3 : 0), h = (4.85 - gap * (n - 1)) / n;
  for (let i = 0; i < n; i++) {
    const L = d.layers[i], y = top + i * (h + gap);
    panel(s, MX, y, 2.4, h, { fill: i % 2 ? K.violet2 : K.violet });
    s.addText([{ text: L.name, options: { bold: true, fontSize: 14, breakLine: !!L.where } }, ...(L.where ? [{ text: L.where, options: { fontSize: 10 } }] : [])],
      { x: MX + 0.15, y, w: 2.1, h, color: K.white, margin: 0, valign: "middle", isTextBox: true });
    const cx0 = MX + 2.55, cw = totalW - 2.55, m = L.items.length, cg = 0.12, iw = (cw - cg * (m - 1)) / m;
    L.items.forEach((it, j) => {
      const x = cx0 + j * (iw + cg); const [hd, ...rest] = it.split("|");
      panel(s, x, y, iw, h, { fill: K.lav });
      s.addText([{ text: hd, options: { bold: true, fontSize: 12, color: K.text, breakLine: rest.length > 0 } }, ...(rest.length ? [{ text: rest.join("|"), options: { fontSize: 10, color: K.gray } }] : [])],
        { x: x + 0.08, y, w: iw - 0.16, h, margin: 0, valign: "middle", align: "center", isTextBox: true });
    });
  }
  if (d.side) {
    const x = MX + totalW + 0.3;
    panel(s, x, top, sideW, 4.85, { fill: K.ink });
    s.addText(d.side.head, { x: x + 0.25, y: top + 0.25, w: sideW - 0.5, h: 0.45, fontSize: 15, bold: true, color: K.cyan, margin: 0, isTextBox: true });
    s.addText(bl(d.side.bullets, { color: "E5E7EB" }), { x: x + 0.25, y: top + 0.8, w: sideW - 0.5, h: 3.9, fontSize: 12, color: "E5E7EB", margin: 0, isTextBox: true, valign: "top" });
  }
};
R.table = async (s, d) => {
  const top = d.lead ? 2.15 : 1.75;
  if (d.lead) s.addText(d.lead, { x: MX, y: 1.5, w: 11.9, h: 0.5, fontSize: 15, color: K.gray, margin: 0, isTextBox: true });
  const rows = [d.header.map((t) => ({ text: String(t).replace(/[a-z]/g, (c) => c.toUpperCase()), options: { bold: true, color: K.gray, fontSize: 10, fill: { color: K.white }, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: K.text }, { type: "none" }] } }))];
  d.rows.forEach((r, i) => rows.push(r.map((t, j) => ({ text: String(t), options: {
    fill: { color: d.highlightRow === i ? K.lav : K.white }, bold: (j === 0 && d.boldFirst !== false) || d.highlightRow === i,
    color: d.highlightRow === i ? K.violet : K.text, border: [{ type: "none" }, { type: "none" }, { pt: 0.5, color: K.line }, { type: "none" }] } }))));
  const availH = (d.note ? 5.75 : 6.45) - top, rowH = Math.min(0.6, Math.max(0.36, availH / rows.length));
  s.addTable(rows, { x: MX, y: top, w: 11.9, colW: d.colW.map((c) => c * 11.9 / 12.1), rowH, fontSize: d.fontSize || (rows.length <= 6 ? 13.5 : 12.5), fontFace: d.fontFace || FONT, valign: "middle", margin: [4, 8, 4, 8] });
  if (d.note) {
    s.addShape(pres.shapes.LINE, { x: MX, y: 5.92, w: 0, h: 0.42, line: { color: K.violet, width: 3 } });
    s.addText(d.note, { x: MX + 0.22, y: 5.88, w: 11.6, h: 0.5, fontSize: 13.5, bold: true, color: K.text, margin: 0, isTextBox: true, valign: "middle" });
  }
};
R.timeline = async (s, d) => {
  const n = d.items.length, y0 = 2.55, gap = 0.18, w = (11.9 - gap * (n - 1)) / n;
  const cx = (i) => MX + i * (w + gap) + w / 2;
  s.addShape(pres.shapes.LINE, { x: cx(0), y: y0, w: Math.max(cx(n - 1) - cx(0), 0.01), h: 0, line: { color: K.lav2, width: 2 } });
  for (let i = 0; i < n; i++) {
    const it = d.items[i], bx = MX + i * (w + gap);
    s.addShape(pres.shapes.OVAL, { x: cx(i) - 0.13, y: y0 - 0.13, w: 0.26, h: 0.26, fill: { color: i === n - 1 ? K.cyan : K.violet }, line: { color: K.white, width: 2 } });
    s.addText(it.date, { x: bx, y: 1.75, w, h: 0.55, fontSize: 13, bold: true, color: K.violet, align: "center", valign: "bottom", margin: 0, isTextBox: true });
    panel(s, bx, 2.95, w, 3.35, { fill: K.lav });
    s.addText(it.head, { x: bx + 0.15, y: 3.1, w: w - 0.3, h: 0.75, fontSize: 14, bold: true, color: K.text, margin: 0, isTextBox: true, valign: "top" });
    s.addText(it.body, { x: bx + 0.15, y: 3.85, w: w - 0.3, h: 2.3, fontSize: 11.5, color: "4B5563", margin: 0, isTextBox: true, valign: "top" });
  }
};
R.chart = async (s, d) => {
  const cw = d.commentary ? 7.6 : 11.9;
  s.addChart(pres.charts[d.chartType || "BAR"], d.series.map((se) => ({ name: se.name, labels: d.labels, values: se.values })), {
    x: MX, y: 1.75, w: cw, h: 4.7, barDir: d.barDir || "bar", showTitle: !!d.chartTitle, title: d.chartTitle, titleFontSize: 13, titleColor: "C9C9D6", titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, dataLabelColor: "FFFFFF", dataLabelFontFace: "+mn-lt", dataLabelFormatCode: d.format || "General",
    chartColors: [K.violet2, K.cyan, "A78BFA", "0EA5E9"], catAxisLabelColor: "C9C9D6", valAxisLabelColor: "8B8BA0", catAxisLabelFontSize: 12, valAxisLabelFontSize: 10,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "2A2A3A", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: d.series.length > 1, legendPos: "b", legendFontSize: 11, legendColor: "C9C9D6", valAxisHidden: !!d.hideVal });
  if (d.commentary) {
    const x = MX + cw + 0.3, w = 11.9 - cw - 0.3;
    panel(s, x, 1.75, w, 4.7, { fill: K.ink2, line: "2A2A3A" });
    s.addText(d.commentary.head, { x: x + 0.3, y: 1.95, w: w - 0.6, h: 0.5, fontSize: 17, bold: true, color: K.cyan, margin: 0, isTextBox: true });
    s.addText(bl(d.commentary.bullets, { color: "E5E7EB" }), { x: x + 0.3, y: 2.6, w: w - 0.6, h: 3.7, fontSize: 13, color: "E5E7EB", margin: 0, isTextBox: true, valign: "top" });
  }
};
R.story = async (s, d) => {
  const lw = 4.5;
  s.addImage({ data: await iconPng(d.icon || "FaUser", K.cyan), x: MX, y: 1.8, w: 0.55, h: 0.55 });
  s.addText(d.persona, { x: MX + 0.75, y: 1.8, w: lw - 0.8, h: 0.55, fontSize: 16, bold: true, color: K.white, margin: 0, isTextBox: true, valign: "middle" });
  s.addText(`“${d.quote}”`, { x: MX, y: 2.6, w: lw - 0.2, h: 3.6, fontSize: 22, italic: true, color: "E9E5FF", margin: 0, isTextBox: true, valign: "top" });
  const x = MX + lw + 0.3, w = 11.9 - lw - 0.3, n = d.beats.length, gap = 0.14, h = (4.75 - gap * (n - 1)) / n;
  d.beats.forEach((b, i) => {
    const y = 1.75 + i * (h + gap);
    panel(s, x, y, w, h, { fill: K.ink2, line: "2A2A3A" });
    s.addText(b.time, { x: x + 0.25, y, w: 1.2, h, fontSize: 15, bold: true, color: i === n - 1 ? K.cyan : K.violet2, margin: 0, valign: "middle", isTextBox: true });
    s.addText(b.text, { x: x + 1.5, y, w: w - 1.75, h, fontSize: 13.5, color: "E5E7EB", margin: 0, valign: "middle", isTextBox: true });
  });
};
R.image = async (s, d) => {
  const file = path.isAbsolute(d.image) ? d.image : path.join(path.dirname(path.resolve(specPath)), d.image);
  const meta = await sharp(file).metadata(), ar = meta.width / meta.height;
  const top = d.lead ? 2.15 : 1.7, maxH = (d.caption ? 6.15 : 6.45) - top;
  if (d.lead) s.addText(d.lead, { x: MX, y: 1.5, w: 11.9, h: 0.5, fontSize: 15, color: K.gray, margin: 0, isTextBox: true });
  const maxW = d.side ? 11.9 - 3.7 - 0.3 : 11.9;
  let w = maxW, h = w / ar; if (h > maxH) { h = maxH; w = h * ar; }
  const ix = d.side ? MX : MX + (maxW - w) / 2;
  panel(s, ix - 0.08, top - 0.08, w + 0.16, h + 0.16, { fill: K.lav, radius: 0.12 });
  s.addImage({ path: file, x: ix, y: top, w, h, altText: d.alt || d.title });
  if (d.caption) s.addText(d.caption, { x: ix, y: top + h + 0.12, w, h: 0.3, fontSize: 10.5, color: K.gray, margin: 0, isTextBox: true });
  if (d.side) {
    const x = MX + w + 0.3, sw = 11.9 - w - 0.3;
    panel(s, x, top - 0.08, sw, maxH + 0.16, { fill: K.ink });
    s.addText(d.side.head, { x: x + 0.25, y: top + 0.15, w: sw - 0.5, h: 0.45, fontSize: 16, bold: true, color: K.cyan, margin: 0, isTextBox: true });
    s.addText(bl(d.side.bullets, { color: "E5E7EB" }), { x: x + 0.25, y: top + 0.75, w: sw - 0.5, h: maxH - 0.9, fontSize: 12.5, color: "E5E7EB", margin: 0, isTextBox: true, valign: "top" });
  }
};
// free layout: blocks placed by position (inches from the content origin MX, 1.6), for pages that carry several
// small tables, KPI tiles, a chart and a text panel together
function miniTable(s, b, x, y) {
  const fs = b.fontSize || 10.5;
  const head = b.header.map((t) => ({ text: String(t).replace(/[a-z]/g, (c) => c.toUpperCase()), options: { bold: true, color: K.gray, fontSize: fs - 1.5,
    fill: { color: K.white }, border: [{ type: "none" }, { type: "none" }, { pt: 1, color: K.text }, { type: "none" }] } }));
  const body = b.rows.map((r, i) => r.map((t, j) => ({ text: String(t), options: { fontSize: fs,
    fill: { color: b.highlightRow === i ? K.lav : K.white }, bold: (j === 0 && b.boldFirst !== false) || b.highlightRow === i,
    color: b.highlightRow === i ? K.violet : K.text, align: j > 0 && b.alignRight ? "right" : "left",
    border: [{ type: "none" }, { type: "none" }, { pt: 0.5, color: K.line }, { type: "none" }] } })));
  const all = [head, ...body], rowH = Math.min(b.maxRowH || 0.42, (b.h - (b.head ? 0.4 : 0)) / all.length);
  const sum = b.colW.reduce((a, c) => a + c, 0);
  s.addTable(all, { x, y: y + (b.head ? 0.4 : 0), w: b.w, colW: b.colW.map((c) => c * b.w / sum), rowH, fontFace: b.fontFace || FONT, valign: "middle", margin: [2, 6, 2, 6] });
}
R.blocks = async (s, d) => {
  const ox = MX, oy = d.lead ? 2.05 : 1.6;
  if (d.lead) s.addText(d.lead, { x: MX, y: 1.45, w: 11.9, h: 0.5, fontSize: 14, color: K.gray, margin: 0, isTextBox: true, valign: "middle" });
  for (const b of d.blocks) {
    const x = ox + b.x, y = oy + b.y;
    if (b.head && b.kind !== "text") s.addText(b.head, { x, y, w: b.w, h: 0.35, fontSize: 13, bold: true, color: K.violet, margin: 0, isTextBox: true, valign: "middle" });
    if (b.kind === "table") miniTable(s, b, x, y);
    else if (b.kind === "kpis") {
      const n = b.items.length, gap = 0.15, top = y + (b.head ? 0.4 : 0), hh = b.h - (b.head ? 0.4 : 0);
      const vert = b.vertical, w = vert ? b.w : (b.w - gap * (n - 1)) / n, h = vert ? (hh - gap * (n - 1)) / n : hh;
      for (let i = 0; i < n; i++) {
        const it = b.items[i], bx = vert ? x : x + i * (w + gap), by = vert ? top + i * (h + gap) : top;
        panel(s, bx, by, w, h, { fill: K.lav });
        const vh = Math.min(0.7, h * 0.5);
        s.addImage({ path: await bigText(it.value, Math.min(w - 0.3, 2.6), vh, { grad: true }), x: bx + 0.15, y: by + 0.1, w: Math.min(w - 0.3, 2.6), h: vh });
        s.addText(it.label, { x: bx + 0.15, y: by + 0.12 + vh, w: w - 0.3, h: h - vh - 0.2, fontSize: b.fontSize || 10.5, color: "374151", margin: 0, isTextBox: true, valign: "top" });
      }
    } else if (b.kind === "chart") {
      const top = y + (b.head ? 0.4 : 0);
      s.addChart(pres.charts[b.chartType || "BAR"], b.series.map((se) => ({ name: se.name, labels: b.labels, values: se.values })), {
        x, y: top, w: b.w, h: b.h - (b.head ? 0.4 : 0), barDir: b.barDir || "col", barGrouping: b.grouping || "clustered",
        showValue: b.showValue !== false, dataLabelPosition: b.grouping === "stacked" ? "ctr" : "outEnd", dataLabelFontSize: 9, dataLabelColor: b.grouping === "stacked" ? "FFFFFF" : K.text,
        dataLabelFormatCode: b.format || "General", dataLabelFontFace: "+mn-lt",
        chartColors: b.colors || [K.violet, K.cyan, "A78BFA", "0EA5E9"], catAxisLabelColor: "374151", valAxisLabelColor: K.gray2, catAxisLabelFontSize: 9.5,
        valAxisLabelFontSize: 8.5, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E5E7EB", size: 0.5 },
        catGridLine: { style: "none" }, showLegend: b.series.length > 1, legendPos: "b", legendFontSize: 9, legendFontFace: "+mn-lt",
        valAxisMaxVal: b.max, valAxisMinVal: b.min ?? 0, valAxisHidden: !!b.hideVal });
    } else if (b.kind === "text") {
      panel(s, x, y, b.w, b.h, { fill: b.dark ? K.ink : K.lav });
      const tc = b.dark ? "E5E7EB" : "374151";
      if (b.head) s.addText(b.head, { x: x + 0.2, y: y + 0.15, w: b.w - 0.4, h: 0.4, fontSize: 13.5, bold: true, color: b.dark ? K.cyan : K.violet, margin: 0, isTextBox: true });
      const body = b.bullets ? bl(b.bullets, { color: tc }) : b.text;
      s.addText(body, { x: x + 0.2, y: y + (b.head ? 0.6 : 0.15), w: b.w - 0.4, h: b.h - (b.head ? 0.75 : 0.3), fontSize: b.fontSize || 11, color: tc, margin: 0, isTextBox: true, valign: "top" });
    } else if (b.kind === "image") {
      const meta = await sharp(b.path).metadata(), ar = meta.width / meta.height;
      let w = b.w, h = w / ar; if (h > b.h) { h = b.h; w = h * ar; }
      panel(s, x - 0.06, y - 0.06, w + 0.12, h + 0.12, { fill: K.lav, radius: 0.1 });
      s.addImage({ path: b.path, x, y, w, h });
    }
  }
  if (d.note) {
    s.addShape(pres.shapes.LINE, { x: MX, y: 6.1, w: 0, h: 0.38, line: { color: K.violet, width: 3 } });
    s.addText(d.note, { x: MX + 0.22, y: 6.05, w: 11.6, h: 0.48, fontSize: 12.5, bold: true, color: K.text, margin: 0, isTextBox: true, valign: "middle" });
  }
};
R.closing = async (s, d) => {
  s.addImage({ path: await bigText(d.title, 9.5, 1.5), x: MX, y: 1.6, w: 9.5, h: 1.5 });
  if (d.subtitle) s.addText(d.subtitle, { x: MX, y: 3.25, w: 11, h: 0.6, fontSize: 18, color: "C9C9D6", margin: 0, isTextBox: true });
  if (d.bullets) s.addText(bl(d.bullets, { color: "E5E7EB" }), { x: MX, y: 4.15, w: 11.5, h: 2.2, fontSize: 15, color: "E5E7EB", margin: 0, isTextBox: true, valign: "top" });
};

// which background each slide type gets (dark / light / violet)
const MODE = { title: "violet", section: "dark", stats: "dark", story: "dark", chart: "dark", closing: "dark",
  cards: "light", twocol: "light", flow: "light", arch: "light", table: "light", timeline: "light", image: "light" };

(async () => {
  BG_DARK = await darkBg(); BG_VIOLET = await violetBg();
  defineMasters();
  let section = null;
  for (const d of spec.slides) {
    if (d.section && d.section !== section) { pres.addSection({ title: d.section }); section = d.section; }
    const mode = MODE[d.type] || "light";
    const master = mode === "dark" ? "NEO_DARK" : mode === "violet" ? "NEO_VIOLET" : "NEO_LIGHT";
    const s = pres.addSlide({ masterName: master, sectionTitle: section || undefined });
    const titled = !["title", "section", "closing"].includes(d.type);
    if (titled) { s.addText(d.title, { placeholder: "title" }); overline(s, section, mode === "dark"); footer(s, mode === "dark"); }
    if (!R[d.type]) throw new Error("Unknown slide type " + d.type);
    await R[d.type](s, d);
    source(s, d.source, mode !== "light");
    if (d.notes) s.addNotes(d.notes);
  }
  await pres.writeFile({ fileName: outPath });
  await applyTheme(outPath, THEME);
  fs.rmSync(TMP, { recursive: true, force: true });
  console.log("wrote", outPath, spec.slides.length, "slides");
})().catch((e) => { console.error(e); process.exit(1); });
