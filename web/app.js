/* ติว TGAT — เว็บนิ่ง ไม่มีเซิร์ฟเวอร์
 * ข้อมูลทั้งหมดอยู่ใน data/ (สร้างด้วย scripts/build_site.py)
 * ความคืบหน้าของผู้ใช้เก็บในเบราว์เซอร์ของผู้ใช้เอง (localStorage)
 */
"use strict";

const $app = document.getElementById("app");
const LETTERS = ["1", "2", "3", "4", "5"];
const SUBJECT_INFO = {
  tgat1: { short: "TGAT1", blurb: "ภาษาอังกฤษเพื่อการสื่อสาร · พูด 30 ข้อ อ่าน 30 ข้อ", time: "60 ข้อ · 60 นาที" },
  tgat2: { short: "TGAT2", blurb: "ภาษา ตัวเลข มิติสัมพันธ์ และเหตุผล", time: "4 ส่วน · 100 คะแนน" },
  tgat3: { short: "TGAT3", blurb: "โจทย์สถานการณ์การทำงาน ให้คะแนนแบบขั้นบันได", time: "60 ข้อ · 60 นาที" },
  tpat3: { short: "TPAT3", blurb: "ความถนัดวิทยาศาสตร์ เทคโนโลยี และวิศวกรรมศาสตร์", time: "70 ข้อ · 180 นาที" },
};
const DIFF_TXT = ["", "ง่ายมาก", "ง่าย", "ปานกลาง", "ยาก", "ยากมาก"];

/* โครงข้อสอบจริง — ตัวเลขมาจากผังสอบ mytcas.com ที่บันทึกไว้ใน spec/02-exam-map.md
 * ใช้เพื่อจำลองสัดส่วนข้อและเวลาเท่านั้น โจทย์ทุกข้อในเว็บนี้แต่งขึ้นใหม่ ไม่ใช่ข้อสอบจริง */
const EXAM_BLUEPRINT = {
  tgat1: {
    items: 60, minutes: 60,
    sections: [{ id: "tgat1.speaking", n: 30 }, { id: "tgat1.reading", n: 30 }],
  },
  tgat2: {
    items: 80, minutes: 60,
    sections: [{ id: "tgat2.language", n: 20 }, { id: "tgat2.numerical", n: 20 },
      { id: "tgat2.reasoning", n: 20 }, { id: "tgat2.spatial", n: 20 }],
  },
  tgat3: {
    items: 60, minutes: 60,
    sections: [{ id: "tgat3.value_innovation", n: 15 }, { id: "tgat3.complex_problem", n: 15 },
      { id: "tgat3.emotion", n: 15 }, { id: "tgat3.civic", n: 15 }],
  },
  tpat3: {
    items: 70, minutes: 180,
    sections: [{ id: "tpat3.aptitude.numerical", n: 15 }, { id: "tpat3.aptitude.spatial", n: 15 },
      { id: "tpat3.aptitude.mechanical", n: 15 }, { id: "tpat3.thinking.sci_engineering", n: 15 },
      { id: "tpat3.thinking.current_awareness", n: 10 }],
  },
};

/* ======================================================== utilities */

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function shuffle(a, rnd = Math.random) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const cache = new Map();
async function getJSON(path) {
  if (!cache.has(path)) {
    cache.set(path, fetch(path).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${path}`);
      return r.json();
    }).catch((e) => { cache.delete(path); throw e; }));
  }
  return cache.get(path);
}

/* ---------- ตัวเรนเดอร์สูตรคณิตศาสตร์
 * หน้าส่วนใหญ่ของเว็บไม่มีสูตรเลย (ภาษา เหตุผล มิติสัมพันธ์) จึงไม่โหลด KaTeX ตั้งแต่เปิดเว็บ
 * ประหยัดการโหลดราว 300 KB ต่อคนที่ไม่ได้เข้าหัวข้อคำนวณ */
const KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min";
let katexPromise = null;
function loadKatex() {
  if (window.katex) return Promise.resolve();
  if (!katexPromise) {
    katexPromise = new Promise((done) => {
      const css = document.createElement("link");
      css.rel = "stylesheet"; css.href = `${KATEX}.css`;
      document.head.appendChild(css);
      const js = document.createElement("script");
      js.src = `${KATEX}.js`;
      js.onload = () => done();
      js.onerror = () => done();        // โหลดไม่ได้ก็ยังอ่านสูตรเป็นข้อความได้
      document.head.appendChild(js);
    }).then(renderPendingMath);
  }
  return katexPromise;
}

function renderPendingMath() {
  if (!window.katex) return;
  document.querySelectorAll(".math-pending").forEach((el) => {
    try {
      el.outerHTML = katex.renderToString(el.dataset.tex, {
        displayMode: el.dataset.display === "1", throwOnError: false,
      });
    } catch { /* ปล่อยให้แสดงเป็นข้อความเหมือนเดิม */ }
  });
}

/* ---------- markdown + คณิต + รูป
 * ต้องดึงสูตรออกก่อนส่งให้ marked เพราะ marked จะกิน \ และ _ ในสูตร */
function md(text, figs = {}, inline = false) {
  if (text == null || text === "") return "";
  const math = [];
  let s = String(text)
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, t) => `%%M${math.push([t, true]) - 1}%%`)
    .replace(/(^|[^\\])\$([^$\n]+?)\$/g, (_, pre, t) => `${pre}%%M${math.push([t, false]) - 1}%%`)
    .replace(/\[\[(fig\d+)\]\]/g, (_, id) => `%%F${id}%%`);

  let html;
  if (window.marked) {
    html = inline ? marked.parseInline(s) : marked.parse(s, { breaks: true });
  } else {
    html = esc(s).split(/\n{2,}/).map((p) => inline ? p : `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
  }
  html = html.replace(/%%M(\d+)%%/g, (_, i) => {
    const [t, display] = math[+i];
    if (!window.katex) {
      // ยังไม่ได้โหลดตัวเรนเดอร์สูตร จองที่ไว้ก่อน แล้วสั่งโหลด พอโหลดเสร็จจะมาแทนที่ให้เอง
      loadKatex();
      return `<span class="math-pending" data-tex="${esc(t)}" data-display="${display ? 1 : 0}"><code>${esc(t)}</code></span>`;
    }
    try { return katex.renderToString(t, { displayMode: display, throwOnError: false }); }
    catch { return `<code>${esc(t)}</code>`; }
  });
  html = html.replace(/%%F(fig\d+)%%/g, (_, id) => figHTML(figs[id]));
  return html;
}
const mdi = (t, figs) => md(t, figs, true);

function figHTML(f) {
  if (!f) return "";
  // svg มาจาก provider ของเราเอง (สร้างตอน build) ไม่ใช่ข้อมูลจากผู้ใช้
  return `<figure class="fig" role="img" aria-label="${esc(f.alt || "")}">${f.svg || ""}` +
    (f.caption ? `<figcaption>${esc(f.caption)}</figcaption>` : "") + `</figure>`;
}

/* ---------- ความคืบหน้า (เก็บในเบราว์เซอร์) */
const STORE_KEY = "tgat-tutor.v1";
const store = (() => {
  let s = { topics: {}, items: {}, lessons: {}, exams: [] };
  try { const raw = localStorage.getItem(STORE_KEY); if (raw) s = { ...s, ...JSON.parse(raw) }; } catch { /* โหมดส่วนตัว */ }
  const save = () => { try { localStorage.setItem(STORE_KEY, JSON.stringify(s)); } catch { /* ไม่เป็นไร */ } };
  return {
    get: () => s,
    record(topicId, baseId, score) {
      const t = (s.topics[topicId] ||= { tries: 0, score: 0 });
      t.tries += 1; t.score += score;
      const it = (s.items[baseId] ||= { tries: 0, best: 0 });
      it.tries += 1; it.best = Math.max(it.best, score);
      save();
    },
    lessonDone(id) { s.lessons[id] = Date.now(); save(); },
    recordExam(row) {
      (s.exams ||= []).unshift(row);
      s.exams = s.exams.slice(0, 20);      // เก็บย้อนหลัง 20 ครั้งพอ
      save();
    },
    reset() { s = { topics: {}, items: {}, lessons: {}, exams: [] }; save(); },
  };
})();

/* ---------- ธีม */
(function theme() {
  const btn = document.getElementById("themeBtn");
  let saved = null;
  try { saved = localStorage.getItem("tgat-theme"); } catch { /* */ }
  if (saved) document.documentElement.dataset.theme = saved;
  btn.addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("tgat-theme", next); } catch { /* */ }
  });
})();

/* ======================================================== catalog */

let CATALOG = null;
async function catalog() {
  if (CATALOG) return CATALOG;
  const c = await getJSON("data/catalog.json");
  const byId = {};
  for (const s of c.subjects) {
    s.children = {};
    for (const t of s.topics) {
      t.subject = s.id;
      byId[t.id] = t;
      (s.children[t.parent] ||= []).push(t);
    }
    for (const k in s.children) s.children[k].sort((a, b) => a.order - b.order);
    s.leaves = s.topics.filter((t) => t.kind === "leaf");
    s.ready = s.leaves.filter((t) => t.lesson || t.problems);
  }
  c.byId = byId;
  CATALOG = c;
  return c;
}

function crumbs(c, id) {
  const out = [];
  let t = c.byId[id];
  while (t) { out.unshift(t); t = c.byId[t.parent]; }
  return `<p class="crumbs"><a href="#/">หน้าแรก</a>` + out.map((x, i) =>
    i === out.length - 1 ? ` › <span>${esc(x.name_th)}</span>`
      : ` › <a href="#/s/${x.subject}">${esc(x.kind === "subject" ? SUBJECT_INFO[x.id].short : x.name_th)}</a>`).join("") + `</p>`;
}

function topicStat(id) {
  const t = store.get().topics[id];
  if (!t || !t.tries) return null;
  return Math.round((t.score / t.tries) * 100);
}

/* ======================================================== pages */

async function pageHome() {
  const c = await catalog();
  const s = store.get();
  const tries = Object.values(s.topics).reduce((a, t) => a + t.tries, 0);
  const totalProblems = c.subjects.reduce((a, x) => a + x.leaves.reduce((b, t) => b + (t.problems || 0), 0), 0);
  const totalLeaves = c.subjects.reduce((a, x) => a + x.leaves.length, 0);

  $app.innerHTML = `
  <section class="hero">
    <h1>เตรียมสอบ TGAT ตั้งแต่ศูนย์</h1>
    <p>บทเรียนสั้น ๆ ต่อด้วยโจทย์ฝึกที่มีคำใบ้ 3 ระดับและเฉลยทีละขั้น
       โจทย์หลายหัวข้อสร้างด้วยโปรแกรม กด "ชุดใหม่" ได้ตัวเลขและรูปใหม่ทุกครั้ง ทำซ้ำได้ไม่มีจำกัด</p>
    <div class="stats">
      <div class="stat"><b>${totalLeaves}</b><span>หัวข้อย่อยในผังสอบ</span></div>
      <div class="stat"><b>${totalProblems}</b><span>โจทย์ต้นแบบ</span></div>
      <div class="stat"><b>${tries}</b><span>ข้อที่คุณทำไปแล้ว</span></div>
    </div>
  </section>
  <h2>เลือกวิชา</h2>
  <div class="grid">
    ${c.subjects.map((x) => {
      const info = SUBJECT_INFO[x.id];
      const pct = Math.round((x.ready.length / x.leaves.length) * 100);
      return `<a class="card subject-card" href="#/s/${x.id}">
        <span class="code">${info.short}</span>
        <span class="name">${esc(x.name_th.replace(info.short + " ", ""))}</span>
        <span class="muted">${esc(info.blurb)}</span>
        <span class="muted" style="font-size:.88rem">${esc(info.time)}</span>
        <div class="bar" title="หัวข้อที่มีเนื้อหาแล้ว"><i style="width:${pct}%"></i></div>
        <span class="muted" style="font-size:.85rem">มีเนื้อหาแล้ว ${x.ready.length} จาก ${x.leaves.length} หัวข้อ</span>
      </a>`;
    }).join("")}
  </div>
  <h2>เริ่มตรงไหนดี</h2>
  <div class="grid">
    ${pickStarters(c).map((t) => `<a class="card subject-card" href="#/t/${t.id}">
        <span class="code">${SUBJECT_INFO[t.subject].short}</span>
        <span class="name">${esc(t.name_th)}</span>
        <span class="muted">${t.lesson ? "มีบทเรียน · " : ""}${t.problems ? `โจทย์ ${t.problems} ข้อ` : ""}</span>
      </a>`).join("")}
  </div>`;
}

function pickStarters(c) {
  const all = c.subjects.flatMap((x) => x.ready);
  return all.filter((t) => t.lesson).concat(all.filter((t) => !t.lesson)).slice(0, 4);
}

async function pageSubject(sid, onlyReady) {
  const c = await catalog();
  const s = c.subjects.find((x) => x.id === sid);
  if (!s) return notFound();
  const info = SUBJECT_INFO[sid];
  const kids = (id) => s.children[id] || [];

  const leafRow = (t) => {
    const ready = t.lesson || t.problems;
    const pct = topicStat(t.id);
    const badges = [
      t.lesson ? `<span class="badge acc">บทเรียน</span>` : "",
      t.problems ? `<span class="badge acc">โจทย์ ${t.problems}${t.templated ? " · สุ่มได้" : ""}</span>` : "",
      pct != null ? `<span class="badge ok">ได้ ${pct}%</span>` : "",
      !ready ? `<span class="badge">กำลังเตรียม</span>` : "",
    ].join("");
    return `<a class="leaf${ready ? "" : " soon"}" href="#/t/${t.id}">
      <span class="t">${esc(t.name_th)}</span><span class="badges">${badges}</span></a>`;
  };

  const section = (b, depth) => {
    const leaves = kids(b.id).filter((t) => t.kind === "leaf" && (!onlyReady || t.lesson || t.problems));
    const subs = kids(b.id).filter((t) => t.kind !== "leaf").map((x) => section(x, depth + 1)).join("");
    if (!leaves.length && !subs) return "";
    const H = depth === 0 ? "h2" : "h3";
    return `<section class="${depth === 0 ? "branch" : "group"}">
      <${H}>${esc(b.name_th)}${b.weight ? ` <span class="badge">${esc(b.weight)}</span>` : ""}</${H}>
      ${leaves.map(leafRow).join("")}${subs}</section>`;
  };

  const hasMix = s.leaves.some((t) => t.problems);
  $app.innerHTML = `${crumbs(c, sid)}
    <h1>${esc(s.name_th)}</h1>
    <p class="muted">${esc(info.blurb)} · ${esc(info.time)}</p>
    <div class="row">
      ${hasMix ? `<a class="btn primary" href="#/exam/${sid}">สอบเสมือน (จับเวลา)</a>` : ""}
      <span class="muted">มีเนื้อหาแล้ว ${s.ready.length} จาก ${s.leaves.length} หัวข้อ</span>
    </div>
    <div class="filter">
      <a class="btn${onlyReady ? "" : " primary"}" href="#/s/${sid}">ทุกหัวข้อ</a>
      <a class="btn${onlyReady ? " primary" : ""}" href="#/s/${sid}/ready">เฉพาะที่มีเนื้อหา</a>
    </div>
    ${kids(sid).map((b) => b.kind === "leaf" ? leafRow(b) : section(b, 0)).join("") ||
      `<div class="empty card">ยังไม่มีหัวข้อที่มีเนื้อหาในวิชานี้ กำลังทยอยเพิ่ม</div>`}`;
}

async function pageTopic(id, tab) {
  const c = await catalog();
  const t = c.byId[id];
  if (!t) return notFound();
  if (t.kind !== "leaf") { location.hash = `#/s/${t.subject}`; return; }
  if (!tab) tab = t.lesson ? "learn" : "practice";

  const head = `${crumbs(c, id)}
    <h1>${esc(t.name_th)}</h1>
    <nav class="tabs">
      <a href="#/t/${id}/learn" class="${tab === "learn" ? "on" : ""}">เรียน</a>
      <a href="#/t/${id}/practice" class="${tab === "practice" ? "on" : ""}">ฝึกโจทย์${t.problems ? ` (${t.problems})` : ""}</a>
    </nav><div id="tabBody"></div>`;
  $app.innerHTML = head;
  const body = document.getElementById("tabBody");

  if (tab === "learn") {
    if (!t.lesson) return comingSoon(body, t, "บทเรียน", t.problems ? `<a class="btn primary" href="#/t/${id}/practice">ไปฝึกโจทย์หัวข้อนี้</a>` : "");
    const lesson = await getJSON(`data/lessons/${id}.json`);
    renderLesson(body, lesson, c, t);
  } else {
    if (!t.problems) return comingSoon(body, t, "โจทย์ฝึก", t.lesson ? `<a class="btn primary" href="#/t/${id}/learn">อ่านบทเรียนหัวข้อนี้</a>` : "");
    const data = await getJSON(`data/problems/${id}.json`);
    const items = data.items.slice().sort((a, b) => a.difficulty - b.difficulty)
      .map((p) => ({ base: p, topic: id }));
    startSession(body, items, { mode: "learn", title: t.name_th, onRestart: () => pageTopic(id, "practice") });
  }
}

function comingSoon(el, t, what, extra) {
  el.innerHTML = `<div class="card empty">
    <p><b>${what}ของหัวข้อนี้กำลังเตรียม</b></p>
    <p class="muted">หัวข้อนี้อยู่ในผังสอบ ${esc(SUBJECT_INFO[t.subject].short)} และจะทยอยเพิ่มเนื้อหา</p>
    <div class="row" style="justify-content:center">${extra}
      <a class="btn" href="#/s/${t.subject}/ready">ดูหัวข้อที่พร้อมแล้ว</a></div></div>`;
}

/* ---------- บทเรียน */
function renderLesson(el, L, c, t) {
  const figs = {};
  for (const b of L.blocks) for (const f of b.figures || []) figs[f.id] = f;
  const link = (id) => c.byId[id] ? `<a href="#/t/${id}">${esc(c.byId[id].name_th)}</a>` : "";

  const blocks = L.blocks.map((b, i) => {
    switch (b.type) {
      case "hook":
        return `<div class="block hook">${md(b.body_md, figs)}</div>`;
      case "concept":
        return `<div class="block concept"><div class="tag">แนวคิด</div>
          ${b.heading ? `<h3 style="margin-top:0">${mdi(b.heading, figs)}</h3>` : ""}${md(b.body_md, figs)}</div>`;
      case "formula":
        return `<div class="block formula"><div class="tag">${b.formula_tex ? "สูตร" : "หลักที่ใช้"}</div>
          <h3 style="margin-top:0">${mdi(b.name, figs)}</h3>
          ${b.formula_tex ? `<div class="formula-main">${md("$$" + b.formula_tex + "$$")}</div>` : ""}
          ${(b.variables || []).length ? `<div class="kv">${b.variables.map((v) =>
            `<span>${mdi(v.symbol.includes("\\") || /[_^]/.test(v.symbol) ? `$${v.symbol}$` : v.symbol)}</span><span>${mdi(v.meaning)}</span>`).join("")}</div>` : ""}
          ${b.use_when ? `<p><b>ใช้เมื่อ</b> ${mdi(b.use_when, figs)}</p>` : ""}
          ${b.avoid_when ? `<p><b>ห้ามใช้เมื่อ</b> ${mdi(b.avoid_when, figs)}</p>` : ""}
          ${b.derivation_md ? `<details class="reveal"><summary>ที่มาของสูตร</summary>${md(b.derivation_md, figs)}</details>` : ""}
          ${b.memory_tip ? `<p class="note">💡 ${mdi(b.memory_tip, figs)}</p>` : ""}</div>`;
      case "example":
        return `<div class="block example"><div class="tag">${esc(b.label || "ตัวอย่าง")}</div>
          ${md(b.stem_md, figs)}
          <details class="reveal"><summary>ลองคิดเองก่อน แล้วกดดูวิธีทำ</summary>
            ${stepsHTML(b.steps, figs)}
            <p><b>คำตอบ</b> ${mdi(b.answer_md, figs)}</p></details></div>`;
      case "pitfall":
        return `<div class="block pitfall"><div class="tag">จุดที่คนพลาดบ่อย</div>
          <h3 style="margin-top:0">${mdi(b.title, figs)}</h3>
          <div class="box-wrong"><b>คิดผิด:</b> ${md(b.wrong_md, figs)}</div>
          ${md(b.why_wrong_md, figs)}
          <div class="box-right"><b>ที่ถูก:</b> ${md(b.correct_md, figs)}</div></div>`;
      case "summary":
        return `<div class="block summary"><div class="tag">สรุป</div>
          <ul>${(b.bullets_md || []).map((x) => `<li>${mdi(x, figs)}</li>`).join("")}</ul></div>`;
      case "check":
        return `<div class="block check" data-check="${i}"><div class="tag">เช็กความเข้าใจ</div>
          ${md(b.question_md, figs)}
          <div class="choices">${b.choices.map((ch, j) => `<button class="choice" data-j="${j}">
            <span class="letter">${LETTERS[j]}</span><span class="body">${mdi(ch, figs)}</span></button>`).join("")}</div>
          <div class="fb"></div></div>`;
      default:
        return b.body_md ? `<div class="block">${md(b.body_md, figs)}</div>` : "";
    }
  }).join("");

  const pre = (L.prereq_topic_ids || []).map(link).filter(Boolean);
  const next = (L.next_topic_ids || []).map(link).filter(Boolean);
  el.innerHTML = `
    <div class="lesson-head">
      ${L.subtitle ? `<p class="muted" style="font-size:1.05rem">${mdi(L.subtitle)}</p>` : ""}
      <p class="muted">ใช้เวลาประมาณ ${L.est_minutes || "-"} นาที${pre.length ? ` · ควรรู้ก่อน: ${pre.join(", ")}` : ""}</p>
      ${(L.objectives || []).length ? `<div class="card"><b>เรียนจบแล้วจะทำได้</b><ul class="obj">${L.objectives.map((o) => `<li>${mdi(o)}</li>`).join("")}</ul></div>` : ""}
    </div>
    ${blocks}
    ${(L.common_exam_patterns || []).length ? `<div class="block concept"><div class="tag">ข้อสอบมักออกแบบไหน</div>
      <ul>${L.common_exam_patterns.map((x) => `<li>${mdi(x)}</li>`).join("")}</ul></div>` : ""}
    ${(L.glossary || []).length ? `<details class="block concept reveal"><summary>คำศัพท์ในบทนี้</summary>
      <div class="kv">${L.glossary.map((g) => `<b>${esc(g.term_th)}${g.term_en ? ` <span class="muted">(${esc(g.term_en)})</span>` : ""}</b><span>${mdi(g.def_md)}</span>`).join("")}</div></details>` : ""}
    <div class="row" style="margin-top:22px">
      ${t.problems ? `<a class="btn primary" href="#/t/${t.id}/practice" id="goPractice">เรียนจบแล้ว ไปฝึกโจทย์</a>` : ""}
      ${next.length ? `<span class="muted">หัวข้อถัดไป: ${next.join(", ")}</span>` : ""}
    </div>`;

  el.querySelectorAll("[data-check]").forEach((box) => {
    const b = L.blocks[+box.dataset.check];
    box.querySelectorAll(".choice").forEach((btn) => btn.addEventListener("click", () => {
      const j = +btn.dataset.j;
      box.querySelectorAll(".choice").forEach((x) => {
        x.disabled = true;
        if (+x.dataset.j === b.answer_index) x.classList.add("right");
      });
      if (j !== b.answer_index) btn.classList.add("wrong");
      box.querySelector(".fb").innerHTML = `<div class="feedback ${j === b.answer_index ? "good" : "bad"}">
        <b>${j === b.answer_index ? "ถูกต้อง" : "ยังไม่ถูก"}</b> ${md(b.explain_md, figs)}</div>`;
    }));
  });
  const gp = document.getElementById("goPractice");
  if (gp) gp.addEventListener("click", () => store.lessonDone(t.id));
}

function stepsHTML(steps, figs) {
  if (!steps || !steps.length) return "";
  return `<ol class="steps">${steps.map((s) => `<li>${md(s.do_md, figs)}${s.why_md ? `<div class="why">ทำไม: ${mdi(s.why_md, figs)}</div>` : ""}</li>`).join("")}</ol>`;
}

/* ======================================================== ฝึกโจทย์
 * mode "learn" : ตอบแล้วเห็นเฉลยทันที ขอคำใบ้ได้
 * mode "exam"  : จับเวลา ไม่มีคำใบ้ เห็นเฉลยตอนส่ง */

function pickVersion(base, fresh) {
  // โจทย์แม่แบบมีหลายแบบที่สุ่มไว้ล่วงหน้า หยิบมาหนึ่งแบบ ครั้งแรกใช้ข้อต้นฉบับ
  const seen = store.get().items[base.id];
  const pool = base.variants || [];
  if (!pool.length || (!seen && !fresh)) return base;
  return pool[Math.floor(Math.random() * pool.length)];
}

function startSession(el, entries, opts) {
  const S = {
    q: entries.map((e) => ({ ...e, p: pickVersion(e.base, opts.fresh), picked: null, hints: 0 })),
    i: 0, mode: opts.mode, done: false, t0: Date.now(), limit: opts.limitSec || 0, timer: null,
  };
  const figsOf = (p) => Object.fromEntries((p.figures || []).map((f) => [f.id, f]));
  const scoreOf = (q) => q.picked == null ? 0 : q.p.scores ? q.p.scores[q.picked] : (q.picked === q.p.answer_index ? 1 : 0);
  const fmtT = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  function tick() {
    const tEl = el.querySelector(".timer");
    if (!tEl || S.done) return;
    const used = Math.floor((Date.now() - S.t0) / 1000);
    if (S.limit) {
      const left = Math.max(0, S.limit - used);
      tEl.textContent = `เหลือ ${fmtT(left)}`;
      if (left === 0) finish();
    } else tEl.textContent = fmtT(used);
  }

  function render() {
    const q = S.q[S.i];
    const p = q.p;
    const figs = figsOf(p);
    const answered = q.picked != null;
    const reveal = S.mode === "learn" ? answered : S.done;
    const picsOnly = p.choices.every((ch) => /^\[\[fig\d+\]\]$/.test(ch.trim()));
    const n = S.q.length;

    let fb = "";
    if (reveal && answered) {
      const sc = scoreOf(q);
      const cls = sc === 1 ? "good" : sc > 0 ? "mid" : "bad";
      const head = p.scores ? (sc === 1 ? "ดีที่สุด ได้เต็ม" : `ได้ ${sc} คะแนน จาก 1`)
        : (sc === 1 ? "ถูกต้อง" : `ยังไม่ถูก คำตอบคือข้อ ${LETTERS[p.answer_index]}`);
      const why = sc < 1 && p.why_wrong[String(q.picked)] ? `<p><b>ทำไมข้อ ${LETTERS[q.picked]} ไม่ใช่:</b> ${mdi(p.why_wrong[String(q.picked)], figs)}</p>` : "";
      const allWhy = p.scores ? `<ul>${p.choices.map((_, j) => p.why_wrong[String(j)] && j !== q.picked
        ? `<li><b>${LETTERS[j]} (${p.scores[j]}):</b> ${mdi(p.why_wrong[String(j)], figs)}</li>` : "").join("")}</ul>` : "";
      fb = `<div class="feedback ${cls}" role="status"><b>${head}</b>${why}${allWhy ? `<details class="reveal"><summary>ทำไมตัวเลือกอื่นได้คะแนนน้อยกว่า</summary>${allWhy}</details>` : ""}</div>
        <div class="solution">
          ${md(p.explanation_md, figs)}
          <details class="reveal"${sc < 1 ? " open" : ""}><summary>วิธีคิดทีละขั้น</summary>${stepsHTML(p.steps, figs)}</details>
        </div>`;
    } else if (reveal && !answered) {
      fb = `<div class="feedback bad" role="status"><b>ไม่ได้ตอบ</b> คำตอบคือข้อ ${LETTERS[p.answer_index]}</div>
        <div class="solution">${md(p.explanation_md, figs)}${stepsHTML(p.steps, figs)}</div>`;
    }

    const hintBox = S.mode === "learn" && q.hints > 0
      ? `<div class="hintbox"><b>คำใบ้</b><ol>${p.hints.slice(0, q.hints).map((h) => `<li>${mdi(h, figs)}</li>`).join("")}</ol></div>` : "";

    el.innerHTML = `
      <div class="qhead">
        <span>ข้อ ${S.i + 1} / ${n} · ระดับ${DIFF_TXT[p.difficulty] || ""}${p.est_seconds ? ` · ควรใช้ราว ${p.est_seconds} วินาที` : ""}</span>
        <span class="timer" aria-label="เวลาที่ใช้หรือเวลาที่เหลือ"></span>
      </div>
      <div class="qcard">
        <div class="stem">${md(p.stem_md, figs)}</div>
        <div class="choices${picsOnly ? " pics" : ""}">
          ${p.choices.map((ch, j) => {
            let cls = "";
            if (reveal) { if (j === p.answer_index) cls = "right"; else if (j === q.picked) cls = "wrong"; }
            else if (j === q.picked) cls = "picked";
            if (reveal && p.scores && j === q.picked && p.scores[j] > 0 && p.scores[j] < 1) cls = "picked";
            return `<button class="choice ${cls}" data-j="${j}" ${reveal ? "disabled" : ""}>
              <span class="letter">${LETTERS[j]}</span><span class="body">${mdi(ch, figs)}${reveal && p.scores
                ? ` <span class="badge ${p.scores[j] === 1 ? "ok" : ""}">${p.scores[j]} คะแนน</span>` : ""}</span></button>`;
          }).join("")}
        </div>
        ${hintBox}${fb}
        <div class="row" style="margin-top:16px">
          ${S.mode === "learn" && !answered && q.hints < p.hints.length ? `<button class="btn" id="hintBtn">ขอคำใบ้ (${q.hints + 1}/${p.hints.length})</button>` : ""}
          ${S.i > 0 ? `<button class="btn" id="prevBtn">← ก่อนหน้า</button>` : ""}
          ${S.i < n - 1 ? `<button class="btn ${answered || S.mode === "exam" ? "primary" : ""}" id="nextBtn">ข้อถัดไป →</button>` : ""}
          ${S.i === n - 1 && !S.done ? `<button class="btn primary" id="endBtn">${S.mode === "exam" ? "ส่งคำตอบ" : "ดูสรุปผล"}</button>` : ""}
          ${S.done && S.i === n - 1 ? `<button class="btn primary" id="sumBtn">กลับไปหน้าสรุป</button>` : ""}
        </div>
      </div>
      <div class="pager">${S.q.map((x, k) => {
        let c = k === S.i ? "cur" : "";
        if (x.picked != null && (S.mode === "learn" || S.done)) c += scoreOf(x) === 1 ? " r" : scoreOf(x) === 0 ? " w" : "";
        else if (x.picked != null) c += " cur";
        return `<button class="dot ${k === S.i ? "cur" : ""} ${c}" data-k="${k}" aria-label="ข้อ ${k + 1}">${k + 1}</button>`;
      }).join("")}</div>`;
    tick();

    el.querySelectorAll(".choice").forEach((b) => b.addEventListener("click", () => {
      if (reveal) return;
      q.picked = +b.dataset.j;
      if (S.mode === "learn") store.record(q.topic, q.base.id, scoreOf(q));
      render();
    }));
    const on = (id, fn) => { const x = document.getElementById(id); if (x) x.addEventListener("click", fn); };
    on("hintBtn", () => { q.hints += 1; render(); });
    on("prevBtn", () => { S.i -= 1; render(); scrollTop(); });
    on("nextBtn", () => { S.i += 1; render(); scrollTop(); });
    on("endBtn", finish);
    on("sumBtn", summary);
    el.querySelectorAll(".dot").forEach((d) => d.addEventListener("click", () => { S.i = +d.dataset.k; render(); }));
  }

  function finish() {
    if (S.mode === "exam" && !S.done) {
      const blank = S.q.filter((x) => x.picked == null).length;
      if (blank && !S.limit && !confirm(`ยังไม่ได้ตอบ ${blank} ข้อ ส่งเลยไหม`)) return;
      if (blank && S.limit && Date.now() - S.t0 < S.limit * 1000 && !confirm(`ยังไม่ได้ตอบ ${blank} ข้อ ส่งเลยไหม`)) return;
      for (const x of S.q) store.record(x.topic, x.base.id, scoreOf(x));
    }
    S.done = true;
    S.used = Math.floor((Date.now() - S.t0) / 1000);
    clearInterval(S.timer);
    if (S.mode === "exam" && opts.examMeta) {
      const total = S.q.reduce((a, x) => a + scoreOf(x), 0);
      store.recordExam({ ...opts.examMeta, at: Date.now(), n: S.q.length, score: +total.toFixed(2), used: S.used });
    }
    summary();
  }

  function summary() {
    const total = S.q.reduce((a, x) => a + scoreOf(x), 0);
    const n = S.q.length;
    const pct = Math.round((total / n) * 100);
    const byTopic = {};
    for (const x of S.q) { const b = (byTopic[x.topic] ||= [0, 0]); b[0] += scoreOf(x); b[1] += 1; }
    const weak = Object.entries(byTopic).filter(([, [a, b]]) => a / b < 0.7);
    // ตารางคะแนนรายส่วน (เฉพาะโหมดสอบเสมือนที่ส่ง sections มา)
    let secTable = "";
    if (opts.sections && opts.sections.length) {
      const rows = opts.sections.map((sec) => {
        const mine = S.q.filter((x) => x.topic.startsWith(sec.id + "."));
        if (!mine.length) return "";
        const got = mine.reduce((a, x) => a + scoreOf(x), 0);
        const p = Math.round((got / mine.length) * 100);
        return `<tr><td>${esc(sec.name)}</td><td>${Number.isInteger(got) ? got : got.toFixed(2)} / ${mine.length}</td>
          <td><span class="badge ${p >= 70 ? "ok" : p >= 50 ? "acc" : "warn"}">${p}%</span></td></tr>`;
      }).join("");
      secTable = `<h3>คะแนนรายส่วน</h3><table><thead><tr><th scope="col">ส่วน</th><th scope="col">คะแนน</th><th scope="col">สัดส่วน</th></tr></thead><tbody>${rows}</tbody></table>`;
    }
    el.innerHTML = `<div class="card" style="text-align:center">
        <p class="muted" style="margin:0">${esc(opts.title)}</p>
        <div class="result-big">${Number.isInteger(total) ? total : total.toFixed(2)} / ${n}</div>
        <p>${pct >= 80 ? "ยอดเยี่ยม พร้อมไปหัวข้อถัดไป" : pct >= 50 ? "ใช้ได้ ลองทำชุดใหม่อีกรอบเพื่อให้แม่นขึ้น" : "ลองอ่านบทเรียนอีกครั้ง แล้วกลับมาทำชุดใหม่"}
          ${S.used ? ` · ใช้เวลา ${fmtT(S.used)}` : ""}</p>
        <div class="row" style="justify-content:center">
          <button class="btn primary" id="again">ทำชุดใหม่ (ตัวเลข/รูปใหม่)</button>
          <button class="btn" id="review">ดูเฉลยทีละข้อ</button>
        </div></div>
      ${secTable}
      ${weak.length && opts.showTopics ? `<h3>หัวข้อที่ควรทบทวน</h3>${weak.map(([id]) =>
        `<a class="leaf" href="#/t/${id}"><span class="t">${esc(CATALOG.byId[id].name_th)}</span><span class="badge warn">ได้ ${Math.round(byTopic[id][0] / byTopic[id][1] * 100)}%</span></a>`).join("")}` : ""}`;
    document.getElementById("again").addEventListener("click", () => opts.onRestart());
    document.getElementById("review").addEventListener("click", () => { S.done = true; S.i = 0; render(); });
    scrollTop();
  }

  // สอบจำลองใช้แบบที่สุ่มใหม่เสมอ (fresh) เพื่อไม่ให้เจอข้อที่เคยเห็นเฉลยแล้ว
  S.timer = setInterval(tick, 1000);
  const stop = () => { clearInterval(S.timer); window.removeEventListener("hashchange", stop); };
  window.addEventListener("hashchange", stop);
  render();
}

function scrollTop() { window.scrollTo({ top: 0, behavior: "smooth" }); }

/* ---------- สอบเสมือน (เต็มฉบับหรือครึ่งฉบับ ตามสัดส่วนของผังสอบ) */
function examSections(c, sid) {
  return EXAM_BLUEPRINT[sid].sections.map((sec) => ({ ...sec, name: c.byId[sec.id].name_th }));
}

async function pageExam(sid, size) {
  const c = await catalog();
  const s = c.subjects.find((x) => x.id === sid);
  if (!s) return notFound();
  const bp = EXAM_BLUEPRINT[sid];
  const secs = examSections(c, sid);

  if (!size) {
    $app.innerHTML = `${crumbs(c, sid)}<h1>สอบเสมือน ${SUBJECT_INFO[sid].short}</h1>
      <p class="muted">จำลองสัดส่วนข้อและเวลาตามผังสอบ ${bp.items} ข้อ ${bp.minutes} นาที
        ระหว่างทำจะไม่มีคำใบ้และไม่เฉลย ส่งแล้วจึงเห็นคะแนนรายส่วนและเฉลยทุกข้อ</p>
      <div class="note"><b>โจทย์ทุกข้อแต่งขึ้นใหม่ ไม่ใช่ข้อสอบจริง</b> ที่จำลองคือจำนวนข้อ สัดส่วนของแต่ละส่วน และเวลาเท่านั้น
        (สัดส่วนอ้างจากผังสอบใน mytcas.com) · อยากเห็นว่าโจทย์จริงหน้าตาเป็นอย่างไร ดูได้ที่
        <a href="#/official">ข้อสอบตัวอย่างทางการ</a></div>
      <h3>สัดส่วนข้อของชุดเต็ม</h3>
      <table><thead><tr><th scope="col">ส่วน</th><th scope="col">จำนวนข้อ</th></tr></thead><tbody>
        ${secs.map((x) => `<tr><td>${esc(x.name)}</td><td>${x.n} ข้อ</td></tr>`).join("")}
      </tbody></table>
      <div class="row" style="margin-top:16px">
        <a class="btn primary" href="#/exam/${sid}/full">ชุดเต็ม ${bp.items} ข้อ · ${bp.minutes} นาที</a>
        <a class="btn" href="#/exam/${sid}/half">ครึ่งชุด ${Math.round(bp.items / 2)} ข้อ · ${Math.round(bp.minutes / 2)} นาที</a>
        <a class="btn" href="#/exam/${sid}/quick">ชุดสั้น ${Math.round(bp.items / 4)} ข้อ · ${Math.round(bp.minutes / 4)} นาที</a>
      </div>`;
    return;
  }

  const frac = size === "full" ? 1 : size === "half" ? 0.5 : 0.25;
  const label = size === "full" ? "ชุดเต็ม" : size === "half" ? "ครึ่งชุด" : "ชุดสั้น";
  $app.innerHTML = `${crumbs(c, sid)}<h1>สอบเสมือน ${SUBJECT_INFO[sid].short} · ${label}</h1>
    <div id="tabBody"><p class="muted">กำลังเตรียมข้อสอบ…</p></div>`;

  // โหลดคลังข้อสอบของวิชานี้ไฟล์เดียว (ไม่มีแบบสุ่มติดมา จึงเล็กกว่าการดึงรายหัวข้อหลายสิบไฟล์มาก)
  const bank = await getJSON(`data/exam/${sid}.json`);
  const entries = [];
  const short = [];
  for (const sec of secs) {
    const pool = shuffle(bank.items.filter((p) => p.topic.startsWith(sec.id + "."))
      .map((p) => ({ base: p, topic: p.topic })));
    const want = Math.max(1, Math.round(sec.n * frac));
    if (pool.length < want) short.push(`${sec.name} (มี ${pool.length} จาก ${want} ข้อ)`);
    entries.push(...pool.slice(0, want));
  }
  const items = shuffle(entries).sort((a, b) => a.base.difficulty - b.base.difficulty);
  const limitSec = Math.round(bp.minutes * 60 * frac);

  startSession(document.getElementById("tabBody"), items, {
    mode: "exam", fresh: true, limitSec, showTopics: true, sections: secs,
    title: `สอบเสมือน ${SUBJECT_INFO[sid].short} ${label} ${items.length} ข้อ`,
    examMeta: { subject: sid, size, label },
    onRestart: () => pageExam(sid, size),
  });
  if (short.length) {
    document.getElementById("tabBody").insertAdjacentHTML("beforebegin",
      `<div class="note">ส่วนที่โจทย์ยังไม่พอจึงได้น้อยกว่าสัดส่วนจริง: ${esc(short.join(" · "))}</div>`);
  }
}

/* ---------- ความคืบหน้า */
/* กราฟแท่งเล็ก ๆ วาดเป็น SVG เอง ไม่ต้องโหลดไลบรารีกราฟ
 * ใช้สีจากธีมปัจจุบัน และมีตารางข้อความกำกับอยู่แล้วด้านล่าง จึงไม่ใช่ข้อมูลที่เข้าถึงไม่ได้ */
function barChart(rows, alt) {
  if (!rows.length) return "";
  const W = 320, H = rows.length * 30 + 8, LBL = 96, BAR = W - LBL - 44;
  const bars = rows.map((r, i) => {
    const y = i * 30 + 6;
    const w = Math.max(2, Math.round((r.pct / 100) * BAR));
    const col = r.pct >= 70 ? "var(--good)" : r.pct >= 50 ? "var(--accent)" : "var(--warn)";
    return `<text x="0" y="${y + 14}" font-size="12" fill="currentColor">${esc(r.label)}</text>
      <rect x="${LBL}" y="${y + 3}" width="${BAR}" height="14" rx="7" fill="currentColor" opacity="0.12"/>
      <rect x="${LBL}" y="${y + 3}" width="${w}" height="14" rx="7" fill="${col}"/>
      <text x="${LBL + BAR + 6}" y="${y + 14}" font-size="12" fill="currentColor">${r.pct}%</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(alt)}" style="width:100%;max-width:420px">${bars}</svg>`;
}

async function pageProgress() {
  const c = await catalog();
  const s = store.get();
  const rows = c.subjects.map((x) => {
    const done = x.leaves.filter((t) => s.topics[t.id]);
    const list = done.map((t) => {
      const pct = topicStat(t.id);
      return `<a class="leaf" href="#/t/${t.id}"><span class="t">${esc(t.name_th)}</span>
        <span class="badges"><span class="badge">${s.topics[t.id].tries} ข้อ</span>
        <span class="badge ${pct >= 70 ? "ok" : "warn"}">${pct}%</span></span></a>`;
    }).join("");
    return `<section class="branch"><h2>${esc(x.name_th)}</h2>${list || `<p class="muted">ยังไม่ได้เริ่ม</p>`}</section>`;
  }).join("");
  const exams = (s.exams || []).slice(0, 8);
  const examRows = exams.length ? `<h2>ประวัติสอบเสมือน</h2>
    <table><thead><tr><th scope="col">เมื่อ</th><th scope="col">ชุด</th><th scope="col">คะแนน</th><th scope="col">เวลาที่ใช้</th></tr></thead><tbody>
    ${exams.map((e) => {
      const d = new Date(e.at);
      const pct = Math.round((e.score / e.n) * 100);
      return `<tr><td>${d.toLocaleDateString("th-TH", { day: "numeric", month: "short" })} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}</td>
        <td>${esc(SUBJECT_INFO[e.subject].short)} ${esc(e.label || "")}</td>
        <td>${e.score} / ${e.n} <span class="badge ${pct >= 70 ? "ok" : pct >= 50 ? "acc" : "warn"}">${pct}%</span></td>
        <td>${Math.floor(e.used / 60)}:${String(e.used % 60).padStart(2, "0")} นาที</td></tr>`;
    }).join("")}</tbody></table>` : "";

  // สรุปความแม่นยำรายวิชา จากจำนวนข้อที่ทำและคะแนนที่ได้
  const subjPct = c.subjects.map((x) => {
    let tries = 0, score = 0;
    for (const t of x.leaves) { const r = s.topics[t.id]; if (r) { tries += r.tries; score += r.score; } }
    return tries ? { label: SUBJECT_INFO[x.id].short, pct: Math.round((score / tries) * 100), tries } : null;
  }).filter(Boolean);
  const chart = subjPct.length
    ? `<div class="card"><h2 style="margin-top:0">ความแม่นยำรายวิชา</h2>
        ${barChart(subjPct, "กราฟแท่งแสดงเปอร์เซ็นต์ความถูกต้องของแต่ละวิชา: "
          + subjPct.map((r) => `${r.label} ${r.pct} เปอร์เซ็นต์`).join(" · "))}
        <p class="muted" style="margin-bottom:0">นับจากทุกข้อที่เคยทำ ${subjPct.reduce((a, r) => a + r.tries, 0)} ข้อ</p></div>`
    : "";
  const missed = missedItemIds().length;
  $app.innerHTML = `<h1>ความคืบหน้าของฉัน</h1>
    <p class="muted">ข้อมูลเก็บในเบราว์เซอร์นี้เท่านั้น ไม่ได้ส่งไปที่ไหน ถ้าล้างข้อมูลเว็บหรือเปลี่ยนเครื่อง ความคืบหน้าจะหายไป</p>
    ${missed ? `<p><a class="btn primary" href="#/redo">ฝึกเฉพาะข้อที่เคยผิด (${missed} ข้อ)</a></p>` : ""}
    ${chart}
    ${examRows}
    ${rows}
    <p style="margin-top:24px"><button class="btn" id="resetBtn">ล้างความคืบหน้าทั้งหมด</button></p>`;
  document.getElementById("resetBtn").addEventListener("click", () => {
    if (confirm("ล้างความคืบหน้าทั้งหมดในเครื่องนี้?")) { store.reset(); pageProgress(); }
  });
}

/* ---------- ฝึกเฉพาะข้อที่เคยทำไม่เต็ม */
function missedItemIds() {
  const items = store.get().items || {};
  return Object.keys(items).filter((id) => items[id].tries > 0 && items[id].best < 1);
}

function topicOfItemId(id) {
  // รูปแบบ id คือ prob.<topic_id>.0001 จึงตัดหัวและท้ายออก
  const m = /^prob\.(.+)\.\d+$/.exec(id);
  return m ? m[1] : null;
}

async function pageRedo() {
  const c = await catalog();
  const ids = missedItemIds();
  if (!ids.length) {
    $app.innerHTML = `<h1>ฝึกข้อที่เคยผิด</h1>
      <div class="card empty"><p>ยังไม่มีข้อที่ทำไม่เต็มคะแนน</p>
      <p class="muted">เมื่อฝึกโจทย์แล้วมีข้อที่ตอบผิดหรือได้คะแนนไม่เต็ม ข้อเหล่านั้นจะมารออยู่ที่นี่</p>
      <a class="btn primary" href="#/">เลือกหัวข้อไปฝึก</a></div>`;
    return;
  }
  $app.innerHTML = `<h1>ฝึกข้อที่เคยผิด</h1><div id="tabBody"><p class="muted">กำลังเตรียมโจทย์…</p></div>`;

  const byTopic = {};
  for (const id of ids) {
    const t = topicOfItemId(id);
    if (t && c.byId[t]) (byTopic[t] ||= []).push(id);
  }
  const files = await Promise.all(Object.keys(byTopic).map((t) =>
    getJSON(`data/problems/${t}.json`).catch(() => null)));
  const entries = [];
  files.forEach((f) => {
    if (!f) return;
    const want = new Set(byTopic[f.topic_id]);
    f.items.filter((p) => want.has(p.id)).forEach((p) => entries.push({ base: p, topic: f.topic_id }));
  });
  const picked = shuffle(entries).slice(0, 20);

  startSession(document.getElementById("tabBody"), picked, {
    mode: "learn", fresh: true, showTopics: true,
    title: `ฝึกซ้ำข้อที่เคยผิด ${picked.length} ข้อ`,
    onRestart: () => pageRedo(),
  });
  document.getElementById("tabBody").insertAdjacentHTML("beforebegin",
    `<p class="muted">หยิบมาจากข้อที่เคยทำไม่เต็มคะแนน ${ids.length} ข้อ ครั้งละไม่เกิน 20 ข้อ
     · ตัวเลขและรูปจะสุ่มใหม่ ไม่ใช่ข้อเดิมเป๊ะ ๆ</p>`);
}

/* ---------- ข้อสอบตัวอย่างทางการ (ลิงก์ออก ไม่ได้คัดลอกมาเก็บไว้) */
const OFFICIAL = [
  { id: "tgat1", code: "91", url: "https://www.mytcas.com/blueprint/tgat1-91/",
    note: "โครงสร้างข้อสอบ + ตัวอย่างข้อสอบทั้งส่วนการพูดและการอ่าน พร้อมเฉลย" },
  { id: "tgat2", code: "92", url: "https://www.mytcas.com/blueprint/tgat2-92/",
    note: "ตัวอย่างข้อสอบครบทั้ง 4 ด้าน พร้อมเฉลยและเหตุผลประกอบ" },
  { id: "tgat3", code: "93", url: "https://www.mytcas.com/blueprint/tgat3-93/",
    note: "ตัวอย่างสถานการณ์พร้อมคำอธิบายว่าตัวเลือกใดได้คะแนนมากน้อยเพียงใด" },
  { id: "tpat3", code: "30", url: "https://www.mytcas.com/blueprint/tpat3-30/",
    note: "ตัวอย่างข้อสอบทั้งด้านตัวเลข มิติสัมพันธ์ เชิงกล และความคิดเชิงวิทยาศาสตร์ พร้อมเฉลย" },
];

function pageOfficial() {
  $app.innerHTML = `<h1>ข้อสอบตัวอย่างทางการ</h1>
  <p class="muted">เว็บนี้ไม่ได้เก็บข้อสอบเก่าไว้ให้ดาวน์โหลด แต่รวมทางเข้าไปยังของทางการไว้ให้ครบในหน้าเดียว</p>

  <div class="note"><b>ทำไมถึงไม่มีข้อสอบเก่าในเว็บนี้</b><br>
    ข้อสอบ TGAT ฉบับเต็มของแต่ละปี <b>ไม่ได้ถูกเผยแพร่เป็นทางการ</b> ไฟล์ที่หมุนเวียนกันตามอินเทอร์เน็ต
    ส่วนใหญ่เป็นการถอดความกันเองซึ่งอาจคลาดเคลื่อน และการนำมาเผยแพร่ซ้ำก็ละเมิดลิขสิทธิ์
    เว็บนี้จึงเลือกแต่งโจทย์ขึ้นใหม่ทั้งหมด แล้วชี้ทางไปยังตัวอย่างข้อสอบทางการแทน</div>

  <h2>ลิงก์ทางการจาก ทปอ. (mytcas.com)</h2>
  <div class="grid">
    ${OFFICIAL.map((o) => `<a class="card subject-card" href="${o.url}" target="_blank" rel="noopener noreferrer">
      <span class="code">${SUBJECT_INFO[o.id].short} · รหัส ${o.code}</span>
      <span class="name">โครงสร้างข้อสอบและตัวอย่างข้อสอบ</span>
      <span class="muted">${esc(o.note)}</span>
      <span class="badge acc" style="align-self:flex-start">เปิดเว็บ mytcas.com</span>
    </a>`).join("")}
  </div>

  <h2>ใช้ร่วมกับเว็บนี้อย่างไรให้คุ้มที่สุด</h2>
  <div class="card">
    <ol>
      <li><b>อ่านโครงสร้างข้อสอบก่อน</b> จะได้รู้ว่าแต่ละพาร์ตมีกี่ข้อ กี่นาที และวัดอะไรบ้าง</li>
      <li><b>ลองทำตัวอย่างข้อสอบทางการ</b> ทีละข้อโดยยังไม่เปิดเฉลย เพื่อดูว่าโจทย์จริงหน้าตาเป็นอย่างไร</li>
      <li><b>กลับมาเรียนหัวข้อที่ยังไม่แม่นในเว็บนี้</b> แล้วฝึกโจทย์จนคล่อง เพราะที่นี่มีโจทย์ให้ทำซ้ำได้ไม่จำกัด</li>
      <li><b>ปิดท้ายด้วยโหมดสอบเสมือน</b> ที่จับเวลาและใช้สัดส่วนข้อตามผังสอบจริง</li>
    </ol>
    <p class="muted" style="margin-bottom:0">หมายเหตุ: หน้าเว็บของ ทปอ. ระบุว่าโครงสร้างและตัวอย่างข้อสอบเป็นแนวทางเตรียมตัวเท่านั้น
      ข้อสอบปีปัจจุบันอาจไม่เหมือนกันทุกประการ</p>
  </div>

  <h2>ถ้ามีไฟล์ข้อสอบเก่าอยู่แล้ว</h2>
  <div class="card">
    <p>ใช้อ่านเองเพื่อเตรียมสอบได้ แต่ <b>อย่านำขึ้นเว็บสาธารณะ</b> ไม่ว่าจะเว็บนี้หรือที่อื่น เพราะเป็นงานมีลิขสิทธิ์
      และหลายไฟล์ก็ไม่ใช่ฉบับทางการ จึงอาจมีข้อผิดพลาดที่ทำให้เข้าใจผิดได้</p>
  </div>`;
}

/* ---------- เบื้องหลังการสร้าง (หน้าสำหรับพอร์ตโฟลิโอ) */
async function pageBuild() {
  const c = await catalog();
  const st = c.stats || { lessons: 0, problems: 0, variants: 0, topics: 0 };
  const pipe = `<svg viewBox="0 0 640 96" role="img" aria-label="ขั้นตอนการสร้างข้อมูล: เขียนเนื้อหาเป็นโค้ด แล้วตรวจอัตโนมัติ แล้วแปลงเป็นไฟล์ของเว็บ แล้วเปิดในเบราว์เซอร์">
    ${[["content/*.py", "เขียนเนื้อหาเป็นโค้ด"], ["validate + stress", "ตรวจอัตโนมัติ"],
       ["web/data/*.json", "แปลงเป็นไฟล์เว็บ"], ["เบราว์เซอร์", "ผู้ใช้เปิดอ่าน"]].map(([a, b], i) => `
      <g transform="translate(${i * 160} 0)">
        <rect x="6" y="14" width="140" height="44" rx="10" fill="none" stroke="currentColor" stroke-width="1.5"/>
        <text x="76" y="36" text-anchor="middle" font-size="13" fill="currentColor">${a}</text>
        <text x="76" y="74" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.65">${b}</text>
        ${i < 3 ? `<path d="M150 36 L 162 36" stroke="currentColor" stroke-width="1.5"/>
          <polygon points="166,36 158,32 158,40" fill="currentColor"/>` : ""}
      </g>`).join("")}
  </svg>`;

  $app.innerHTML = `<h1>เบื้องหลังการสร้างเว็บนี้</h1>
  <p class="muted">อ่านประมาณ 3 นาที · เขียนไว้สำหรับคนที่อยากรู้ว่าเว็บนี้ทำงานอย่างไรและตัดสินใจอะไรไปบ้าง</p>

  <div class="stats">
    <div class="stat"><b>${st.topics}</b><span>หัวข้อในผังสอบ</span></div>
    <div class="stat"><b>${st.lessons}</b><span>บทเรียน</span></div>
    <div class="stat"><b>${st.problems}</b><span>โจทย์ต้นแบบ</span></div>
    <div class="stat"><b>${st.variants}</b><span>โจทย์ที่สุ่มไว้ล่วงหน้า</span></div>
  </div>

  <h2>ปัญหาที่อยากแก้</h2>
  <div class="card">
    <p>คนที่เริ่มติว TGAT จากศูนย์มักเจอสองอย่าง: แหล่งฝึกที่ดีต้องเสียเงิน และข้อสอบที่หาได้ฟรีมักมีแต่เฉลยว่า
      "ตอบข้อไหน" แต่ไม่บอกว่า <b>ทำไมข้ออื่นถึงผิด</b> พอทำผิดซ้ำก็ไม่รู้ว่าตัวเองเข้าใจผิดตรงไหน</p>
    <p>เว็บนี้จึงตั้งเงื่อนไขไว้สามข้อตั้งแต่ต้น: ใช้ฟรีทั้งหมด · ทุกตัวเลือกที่ผิดต้องมีเหตุผลกำกับว่าคิดผิดแบบไหนจึงได้ค่านั้น ·
      และโจทย์ต้องทำซ้ำได้เรื่อย ๆ โดยไม่เจอข้อเดิม</p>
  </div>

  <h2>เนื้อหาเป็นโค้ด ไม่ใช่เอกสาร</h2>
  <div class="card">
    <p>บทเรียนและโจทย์ทุกข้อเขียนเป็นโปรแกรมภาษา Python แล้วให้เครื่องแปลงเป็นไฟล์ข้อมูลของเว็บอีกที
      ข้อดีคือกฎคุณภาพถูกบังคับด้วยเครื่อง ไม่ใช่ความจำของคนเขียน</p>
    <figure class="fig wide">${pipe}</figure>
    <p>ทุกครั้งที่แก้เนื้อหา ตัวตรวจจะรันซ้ำทั้งคลัง ถ้าข้อไหนผิดกฎ ไฟล์จะไม่ถูกสร้างเลย</p>
  </div>

  <h2>โจทย์ที่คำนวณคำตอบเองได้</h2>
  <div class="card">
    <p>โจทย์บางกลุ่มไม่ได้พิมพ์คำตอบไว้ล่วงหน้า แต่ให้โปรแกรมคิดคำตอบจากกฎ แล้วสร้างตัวลวงจากความผิดพลาดที่พบบ่อย ตัวอย่าง</p>
    <ul>
      <li><b>พับกล่อง</b> — โปรแกรมพับแผ่นคลี่จริงในสามมิติ จึงรู้ว่าหน้าไหนอยู่ตรงข้ามกัน และลูกศรบนหน้าหนึ่งชี้ไปทางหน้าใด
        ตรวจกับแผ่นคลี่ทั้ง 16 แบบแล้วตรงกันทุกกรณี</li>
      <li><b>หมุนภาพสามมิติ</b> — เก็บทรงเป็นพิกัดของลูกบาศก์แต่ละก้อน การหมุนคือการแปลงพิกัด ภาพที่เห็นวาดจากพิกัดนั้นอีกที
        และคัดเฉพาะทรงที่ไม่สมมาตร เพื่อให้ตัวลวงแบบภาพสะท้อนเป็นตัวลวงจริง ๆ</li>
      <li><b>ปริศนาเงื่อนไข</b> (ใครนั่งตรงไหน ใครเลี้ยงสัตว์อะไร) — โปรแกรมไล่ทุกความเป็นไปได้
        แล้วยืนยันว่าคำตอบมีแบบเดียวจริง และตัวเลือกอื่นเป็นไปไม่ได้จริง</li>
      <li><b>ประกอบชิ้นส่วน</b> — ไล่วางชิ้นส่วนทุกตำแหน่งและทุกมุมหมุน เพื่อพิสูจน์ว่ารูปที่เป็นตัวลวงประกอบไม่ได้แน่นอน</li>
    </ul>
    <p>โจทย์กลุ่มตัวเลขใช้แม่แบบที่สุ่มค่าใหม่ได้ ก่อนนำขึ้นเว็บจะถูกสุ่มทดสอบข้อละ 200 ครั้ง
      ถ้ามีแม้แต่ครั้งเดียวที่ได้โจทย์กำกวม ตัวเลือกซ้ำ หรือคำใบ้เผยคำตอบ ถือว่าแม่แบบนั้นไม่ผ่าน</p>
  </div>

  <h2>สิ่งที่เลือกไม่ทำ</h2>
  <div class="card">
    <ul>
      <li><b>ไม่ใช้ข้อสอบจริง</b> แม้จะมีไฟล์อยู่ในเครื่อง เพราะติดเรื่องลิขสิทธิ์ โจทย์ทุกข้อจึงแต่งขึ้นใหม่ทั้งหมด</li>
      <li><b>ไม่มีระบบสมาชิกและไม่มีฐานข้อมูล</b> ความคืบหน้าเก็บในเบราว์เซอร์ของผู้ใช้เอง ทำให้ไม่มีค่าใช้จ่ายรายเดือน
        และไม่ต้องเก็บข้อมูลส่วนตัวของใคร</li>
      <li><b>ไม่เดาโครงสอบเอง</b> จำนวนข้อและเวลาที่ใช้ในโหมดสอบเสมือนอ้างจากผังสอบของ mytcas.com เท่านั้น</li>
    </ul>
  </div>

  <h2>ข้อจำกัดที่ยังมีอยู่</h2>
  <div class="card">
    <ul>
      <li>เนื้อหาเขียนโดยใช้ AI ช่วยและ <b>ยังอยู่ระหว่างการตรวจทานโดยคน</b> จึงยังอาจมีจุดผิด</li>
      <li>เกณฑ์คะแนนย่อยของ TGAT3 ในเว็บนี้เป็นเกณฑ์ที่เรากำหนดขึ้นเพื่อฝึก ไม่ใช่เกณฑ์ทางการ</li>
      <li>ยังมีเฉพาะ TGAT ทั้งสามพาร์ต ยังไม่มี TPAT และ A-Level</li>
    </ul>
  </div>

  <h2>สิ่งที่อยากทำต่อ</h2>
  <div class="card">
    <ul>
      <li>ระบบทวนซ้ำตามช่วงเวลา เพื่อให้กลับมาทำข้อที่เคยผิดในจังหวะที่ใกล้ลืมพอดี</li>
      <li>ให้ครูหรือผู้เชี่ยวชาญตรวจเนื้อหาแล้วเปลี่ยนสถานะจากฉบับร่างเป็นฉบับตรวจแล้ว</li>
      <li>ขยายไปวิชาอื่นโดยใช้โครงเดิม เพราะผังหัวข้อของทุกวิชาวางไว้แล้ว</li>
    </ul>
  </div>

  <p class="muted" style="margin-top:22px">เว็บนี้เป็นเว็บนิ่งล้วน ไม่มีเซิร์ฟเวอร์ ไม่มีการเก็บข้อมูลผู้ใช้
    และเปิดได้จากมือถือ · <a href="#/about">อ่านข้อมูลเกี่ยวกับเว็บ</a></p>`;
}

function pageAbout() {
  $app.innerHTML = `<h1>เกี่ยวกับเว็บนี้</h1>
  <div class="card">
    <p>เว็บนี้ทำขึ้นเพื่อช่วยนักเรียนเตรียมสอบ TGAT ได้ฟรี โดยเน้นคนที่เริ่มจากศูนย์</p>
    <ul>
      <li><b>ทุกหัวข้ออิงผังสอบทางการ</b> จาก mytcas.com ส่วนการแบ่งหัวข้อย่อยเป็นการแบ่งเองเพื่อให้เรียนทีละเรื่องได้</li>
      <li><b>โจทย์ทุกข้อแต่งขึ้นใหม่</b> ไม่ใช่ข้อสอบจริง และไม่ได้คัดลอกจากข้อสอบจริง</li>
      <li><b>โจทย์แบบสุ่มได้</b> สร้างด้วยโปรแกรมที่คำนวณคำตอบเอง เช่น การหมุนรูป การพับกล่อง
        ทุกข้อถูกตรวจอัตโนมัติว่าคำตอบถูก ตัวเลือกไม่ซ้ำ และคำใบ้ไม่เผยคำตอบ</li>
      <li><b>ทุกตัวเลือกผิดมีเหตุผล</b> ว่าคิดผิดแบบไหนจึงได้ค่านั้น เพื่อให้รู้ว่าตัวเองพลาดตรงไหน</li>
      <li>เนื้อหาจัดทำโดยใช้ AI ช่วยและอยู่ระหว่างตรวจทาน หากพบข้อผิดพลาดโปรดแจ้งผู้จัดทำ</li>
    </ul>
    <p class="muted">ความคืบหน้าเก็บในเบราว์เซอร์ของคุณเอง ไม่มีการเก็บข้อมูลส่วนตัว</p>
  </div>`;
}

function notFound() {
  $app.innerHTML = `<div class="empty"><h1>ไม่พบหน้านี้</h1><a class="btn primary" href="#/">กลับหน้าแรก</a></div>`;
}

/* ======================================================== router */

async function route() {
  const h = location.hash.replace(/^#\/?/, "");
  const [a, b, c2] = h.split("/");
  // ทำเครื่องหมายเมนูที่กำลังเปิด — เรียกสองครั้ง เพราะรอบแรก catalog อาจยังโหลดไม่เสร็จ
  const markNav = () => {
    document.querySelectorAll(".nav a").forEach((x) => {
      const on = x.getAttribute("href") === `#/s/${b}` && (a === "s" || a === "exam" || a === "mix") ||
      (a === "t" && CATALOG && CATALOG.byId[b] && x.getAttribute("href") === `#/s/${CATALOG.byId[b].subject}`) ||
        x.getAttribute("href") === `#/${a}`;
      x.classList.toggle("on", on);
      if (on) x.setAttribute("aria-current", "page"); else x.removeAttribute("aria-current");
    });

  };
  markNav();
  try {
    if (!a) await pageHome();
    else if (a === "s") await pageSubject(b, c2 === "ready");
    else if (a === "t") await pageTopic(decodeURIComponent(b), c2);
    else if (a === "exam") await pageExam(b, c2 || "");
    else if (a === "mix") location.hash = `#/exam/${b}`;   // เส้นทางเดิม ให้ไปหน้าใหม่แทน
    else if (a === "progress") await pageProgress();
    else if (a === "redo") await pageRedo();
    else if (a === "official") pageOfficial();
    else if (a === "how") await pageBuild();
    else if (a === "about") pageAbout();
    else notFound();
  } catch (e) {
    console.error(e);
    $app.innerHTML = `<div class="card empty"><p><b>โหลดข้อมูลไม่สำเร็จ</b></p>
      <p class="muted">${esc(e.message)}</p>
      <p class="muted">ถ้าเปิดไฟล์ตรงจากเครื่อง ต้องเปิดผ่านเซิร์ฟเวอร์ เช่น <code>python -m http.server</code> ในโฟลเดอร์ web</p></div>`;
  }
  markNav();
  if (a !== "t" || !c2) window.scrollTo(0, 0);
}

window.addEventListener("hashchange", route);
route();
