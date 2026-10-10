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
    // แบ่งส่วนย่อยตามผังสอบ และไม่ดึงหัวข้อพื้นฐาน (foundation) ซึ่งเป็นบทปูพื้น ไม่ใช่รูปแบบข้อสอบ
    sections: [
      { id: "tgat1.speaking.question_response", n: 10, name: "พูด · ถาม-ตอบ" },
      { id: "tgat1.speaking.short_conversation", n: 10, name: "พูด · บทสนทนาสั้น" },
      { id: "tgat1.speaking.long_conversation", n: 10, name: "พูด · บทสนทนายาว" },
      { id: "tgat1.reading.text_completion", n: 15, name: "อ่าน · เติมข้อความ" },
      { id: "tgat1.reading.comprehension", n: 15, name: "อ่าน · จับใจความ" },
    ],
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
/* วันที่ตามเวลาของเครื่องผู้ใช้ รูป YYYY-MM-DD */
function dayKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/* จำนวนวันที่ฝึกติดต่อกันจนถึงวันนี้ (ถ้าวันนี้ยังไม่ได้ทำ นับถึงเมื่อวาน เพื่อไม่ให้ตัวเลขหายก่อนหมดวัน) */
function streakInfo(days) {
  const d = new Date();
  const today = (days || {})[dayKey(d)] || 0;
  if (!today) d.setDate(d.getDate() - 1);
  let n = 0;
  while ((days || {})[dayKey(d)]) { n += 1; d.setDate(d.getDate() - 1); }
  return { streak: n, today };
}

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
      const day = dayKey(new Date());
      (s.days ||= {})[day] = (s.days[day] || 0) + 1;
      save();
    },
    lessonDone(id) { s.lessons[id] = Date.now(); save(); },
    setLast(id, tab) { s.last = { id, tab, at: Date.now() }; save(); },
    flag(name) { if (!s[name]) { s[name] = Date.now(); save(); } },
    recordExam(row) {
      (s.exams ||= []).unshift(row);
      s.exams = s.exams.slice(0, 20);      // เก็บย้อนหลัง 20 ครั้งพอ
      save();
    },
    reset() { s = { topics: {}, items: {}, lessons: {}, exams: [], seenGuide: s.seenGuide }; save(); },
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

/* คำอธิบายวิชาสำหรับคนที่เพิ่งเข้ามา: บอกว่าใครต้องสอบและวัดอะไร ไม่ใช้ศัพท์ของผังสอบ */
const SUBJECT_INTRO = {
  tgat1: { who: "ทุกคนที่สมัคร TCAS", what: "สนทนาและอ่านภาษาอังกฤษในชีวิตประจำวัน" },
  tgat2: { who: "ทุกคนที่สมัคร TCAS", what: "คิดเลข จับใจความ ดูรูปทรง และใช้เหตุผล" },
  tgat3: { who: "ทุกคนที่สมัคร TCAS", what: "เลือกวิธีรับมือสถานการณ์การทำงานและการอยู่ร่วมกัน" },
  tpat3: { who: "คนที่จะเข้าคณะวิศวะและสายวิทย์-เทคโนโลยี", what: "ตัวเลข มิติสัมพันธ์ กลไก และความคิดเชิงวิทยาศาสตร์" },
};

async function pageHome() {
  const c = await catalog();
  const s = store.get();
  const tries = Object.values(s.topics).reduce((a, t) => a + t.tries, 0);
  const score = Object.values(s.topics).reduce((a, t) => a + t.score, 0);
  const st = c.stats || { lessons: 0, problems: 0 };
  const last = s.last && c.byId[s.last.id] ? c.byId[s.last.id] : null;

  // ปุ่มหลักเปลี่ยนตามผู้ใช้: คนใหม่ไปหน้าสอนใช้งาน · คนที่ดูแล้วไปเลือกวิชา · คนที่ฝึกค้างไว้กลับไปหัวข้อเดิม
  // ปุ่มเลื่อนไปส่วนเลือกวิชาใช้ data-scroll เพราะ # ในเว็บนี้ใช้กำหนดหน้า ลิงก์ #subjects จะกลายเป็นหน้าไม่พบ
  const toSubjects = (label, cls) => `<button class="btn big ${cls}" type="button" data-scroll="subjects">${label}</button>`;
  let primary, secondary;
  if (last) {
    primary = `<a class="btn primary big" href="#/t/${last.id}/${s.last.tab || "practice"}">ทำต่อ: ${esc(last.name_th)}</a>`;
    secondary = `<a class="btn big" href="#/progress">ดูความคืบหน้า</a>`;
  } else if (s.seenGuide) {
    primary = toSubjects("เลือกวิชาเริ่มฝึก", "primary");
    secondary = `<a class="btn big" href="#/guide">ดูวิธีใช้อีกครั้ง</a>`;
  } else {
    primary = `<a class="btn primary big" href="#/guide">เริ่มใช้งาน · ลองทำข้อแรก</a>`;
    secondary = toSubjects("เลือกวิชาเอง", "");
  }

  $app.innerHTML = `
  <section class="hero">
    <p class="eyebrow">ฟรีทั้งหมด · ไม่ต้องสมัครสมาชิก</p>
    <h1>ฝึกข้อสอบ TGAT และ TPAT3<br>แบบรู้ว่าตัวเองผิดตรงไหน</h1>
    <p class="lead">เว็บฝึกข้อสอบเข้ามหาวิทยาลัย (TCAS) ทุกข้อมีคำใบ้ เฉลยทีละขั้น
      และบอกเหตุผลว่า <b>ทำไมตัวเลือกที่ผิดถึงผิด</b></p>
    <div class="cta-row">${primary}${secondary}</div>
    ${(() => {
      const k = streakInfo(s.days);
      if (!k.streak && !k.today) return "";
      return `<p class="streak" role="status"><b>ฝึกต่อเนื่อง ${k.streak} วัน</b> · ${k.today
        ? `วันนี้ทำแล้ว ${k.today} ข้อ` : "วันนี้ยังไม่ได้ทำ ทำสักข้อเพื่อไม่ให้ขาดช่วง"}</p>`;
    })()}
    <p class="hero-facts"><span><b>${st.lessons}</b> บทเรียน</span><span><b>${st.problems.toLocaleString("th-TH")}</b> โจทย์</span>
      <span><b>4</b> วิชา</span><span>ใช้บนมือถือได้</span></p>
  </section>

  <h2>ใช้งานอย่างไร</h2>
  <ol class="howto">
    <li><span class="n">1</span><b>เรียน</b>
      <p>บทเรียนสั้น ๆ รายหัวข้อ มีตัวอย่างทีละขั้นและกับดักที่คนมักพลาด</p></li>
    <li><span class="n">2</span><b>ฝึก</b>
      <p>ทำโจทย์พร้อมคำใบ้ 3 ระดับ ตอบแล้วเห็นเฉลยและเหตุผลของทุกตัวเลือก</p></li>
    <li><span class="n">3</span><b>สอบเสมือน</b>
      <p>จับเวลาตามจำนวนข้อและเวลาของข้อสอบจริง แล้วดูว่าควรกลับไปทบทวนเรื่องไหน</p></li>
  </ol>

  <a class="card duel-card" href="#/duel">
    <span class="code">ท้าเพื่อน</span>
    <span class="name">ทำโจทย์ชุดเดียวกัน 10 ข้อ แล้วเทียบคะแนนกัน</span>
    <span class="what">สร้างลิงก์ส่งให้เพื่อน ทุกคนที่เปิดลิงก์ได้โจทย์ชุดเดียวกัน จับเวลา 10 นาที ทำเสร็จแล้วดูเฉลยด้วยกันได้</span>
  </a>

  <h2 id="subjects" tabindex="-1">เลือกวิชา</h2>
  <div class="subjects">
    ${c.subjects.map((x) => {
      const info = SUBJECT_INFO[x.id];
      const intro = SUBJECT_INTRO[x.id] || { who: "", what: info.blurb };
      const bp = EXAM_BLUEPRINT[x.id];
      const done = x.ready.filter((t) => s.topics[t.id]).length;
      return `<a class="card subject-card" href="#/s/${x.id}">
        <span class="code">${info.short}</span>
        <span class="name">${esc(x.name_th.replace(info.short + " ", ""))}</span>
        <span class="what">${esc(intro.what)}</span>
        <span class="meta"><span class="badge acc">${esc(intro.who)}</span>
          ${bp ? `<span class="badge">${bp.items} ข้อ · ${bp.minutes} นาที</span>` : ""}
          <span class="badge">${x.ready.length} หัวข้อ</span></span>
        ${done ? `<span class="muted small">คุณฝึกไปแล้ว ${done} จาก ${x.ready.length} หัวข้อ</span>
          <div class="bar"><i style="width:${Math.round(done / x.ready.length * 100)}%"></i></div>` : ""}
        <span class="go">เข้าดูหัวข้อ →</span>
      </a>`;
    }).join("")}
  </div>

  ${tries ? `<h2>ความคืบหน้าของคุณ</h2>
  <div class="card you">
    <div class="stats">
      <div class="stat"><b>${tries}</b><span>ข้อที่ทำไปแล้ว</span></div>
      <div class="stat"><b>${Math.round(score / tries * 100)}%</b><span>คะแนนเฉลี่ย</span></div>
      <div class="stat"><b>${Object.keys(s.topics).length}</b><span>หัวข้อที่เคยฝึก</span></div>
    </div>
    <div class="row"><a class="btn" href="#/progress">ดูรายละเอียด</a><a class="btn" href="#/redo">ฝึกข้อที่เคยผิด</a></div>
  </div>` : `<h2>ยังไม่รู้จะเริ่มตรงไหน</h2>
  <div class="subjects">
    ${pickStarters(c).map((t) => `<a class="card subject-card" href="#/t/${t.id}">
        <span class="code">${SUBJECT_INFO[t.subject].short} · หัวข้อแรกที่แนะนำ</span>
        <span class="name">${esc(t.name_th)}</span>
        <span class="muted small">${t.lesson ? "มีบทเรียน · " : ""}${t.problems ? `โจทย์ ${t.problems} ข้อ` : ""}</span>
      </a>`).join("")}
  </div>`}

  <h2>สิ่งที่ควรรู้ก่อนใช้</h2>
  <ul class="facts">
    <li><b>โจทย์ทุกข้อแต่งขึ้นใหม่</b> ไม่ใช่ข้อสอบจริง แต่จำนวนข้อและเวลาอ้างตามผังสอบทางการ
      <a href="#/official">ดูข้อสอบตัวอย่างทางการ</a></li>
    <li><b>ความคืบหน้าเก็บในเครื่องของคุณ</b> ไม่มีการส่งข้อมูลออก เปลี่ยนเครื่องหรือล้างเบราว์เซอร์แล้วข้อมูลจะหาย</li>
    <li><b>เนื้อหาเขียนโดยใช้ AI ช่วย</b> ผ่านการตรวจด้วยโปรแกรมและตรวจไขว้แล้ว แต่ยังไม่ได้ตรวจโดยครู
      <a href="#/how">อ่านเบื้องหลังการสร้าง</a></li>
  </ul>`;
  $app.querySelectorAll("[data-scroll]").forEach((el) => el.addEventListener("click", () => {
    const target = document.getElementById(el.dataset.scroll);
    if (target) { target.scrollIntoView({ behavior: "smooth", block: "start" }); target.focus?.(); }
  }));
}

/* หัวข้อแรกที่แนะนำของแต่ละวิชา: เลือกหัวข้อพื้นฐานที่มีบทเรียนก่อน */
function pickStarters(c) {
  return c.subjects.map((x) => {
    const ok = x.ready.filter((t) => t.lesson && t.problems);
    return ok.find((t) => t.id.includes(".foundation.")) || ok[0] || x.ready[0];
  }).filter(Boolean);
}

/* หน้าสอนใช้งาน: อธิบายสั้น ๆ แล้วให้ลองทำโจทย์จริงในหน้านี้เลย */
const GUIDE_DEMO_TOPIC = "tgat2.numerical.foundation.percent";

async function pageGuide() {
  const c = await catalog();
  store.flag("seenGuide");
  const demo = c.byId[GUIDE_DEMO_TOPIC];

  $app.innerHTML = `<h1>วิธีใช้เว็บนี้</h1>
  <p class="lead">อ่านจบใน 1 นาที แล้วลองทำโจทย์จริงหนึ่งข้อในขั้นที่ 3</p>

  <ol class="guide">
    <li>
      <h2><span class="n">1</span>เลือกวิชาและหัวข้อ</h2>
      <p>เมนูด้านบนมี 4 วิชา กดเข้าไปจะเห็นหัวข้อย่อยเรียงตามผังสอบ ป้ายท้ายแต่ละหัวข้อบอกสถานะ</p>
      <div class="demo-leaf" aria-hidden="true">
        <span class="t">ร้อยละและการเปลี่ยนแปลง</span>
        <span class="badges"><span class="badge acc">บทเรียน</span><span class="badge">โจทย์ 6 ข้อ</span>
          <span class="badge ok">ได้ 83%</span></span>
      </div>
      <p class="muted small">ป้ายสีเขียวคือคะแนนเฉลี่ยของคุณในหัวข้อนั้น จะขึ้นหลังฝึกไปแล้ว</p>
    </li>
    <li>
      <h2><span class="n">2</span>อ่านบทเรียนก่อน ถ้ายังไม่เคยเรียนเรื่องนั้น</h2>
      <p>แต่ละหัวข้อมีสองแท็บ คือ <b>เรียน</b> กับ <b>ฝึกโจทย์</b> บทเรียนใช้เวลาอ่านราว 10–30 นาที
        มีตัวอย่างทีละขั้น กับดักที่พบบ่อย และคำถามตรวจความเข้าใจท้ายบท ถ้าเคยเรียนมาแล้วข้ามไปฝึกโจทย์ได้เลย</p>
    </li>
    <li>
      <h2><span class="n">3</span>ฝึกโจทย์ · ลองทำข้อนี้ดู</h2>
      <ul class="tips">
        <li>ติดให้กด <b>ขอคำใบ้</b> ได้สามระดับ จากกว้างไปแคบ คำใบ้ไม่บอกคำตอบ</li>
        <li>เลือกคำตอบแล้วจะเห็น <b>เฉลยทีละขั้น</b> และเหตุผลของตัวเลือกที่คุณเลือก</li>
        <li>หัวข้อที่เป็นโจทย์ตัวเลขกด <b>ชุดใหม่</b> ได้ ตัวเลขจะเปลี่ยนทุกครั้ง</li>
      </ul>
      <div id="guideDemo" class="guide-demo"><p class="muted">กำลังโหลดโจทย์ตัวอย่าง…</p></div>
    </li>
    <li>
      <h2><span class="n">4</span>สอบเสมือนเมื่อพร้อม</h2>
      <p>จับเวลาตามจำนวนข้อและเวลาของข้อสอบจริง ระหว่างสอบไม่มีคำใบ้ ส่งแล้วจะได้คะแนนแยกรายส่วนและเฉลยทุกข้อ
        เลือกทำครึ่งชุดได้ถ้ามีเวลาน้อย</p>
      <div class="row">${c.subjects.map((x) =>
        `<a class="btn" href="#/exam/${x.id}">สอบเสมือน ${SUBJECT_INFO[x.id].short}</a>`).join("")}</div>
    </li>
    <li>
      <h2><span class="n">5</span>กลับมาดูความคืบหน้า</h2>
      <p>หน้า <a href="#/progress">ความคืบหน้า</a> แสดงคะแนนรายวิชา ประวัติการสอบ และหัวข้อที่ควรทบทวน
        ส่วนปุ่ม <a href="#/redo">ฝึกข้อที่เคยผิด</a> จะรวมข้อที่ยังทำไม่เต็มคะแนนมาให้ทำซ้ำ</p>
    </li>
  </ol>

  <h2>คำถามที่พบบ่อย</h2>
  <div class="card faq">
    <details><summary>ต้องสมัครสมาชิกหรือเสียเงินไหม</summary>
      <p>ไม่ต้อง ใช้ได้ทันทีและฟรีทั้งหมด</p></details>
    <details><summary>นี่คือข้อสอบจริงหรือเปล่า</summary>
      <p>ไม่ใช่ โจทย์ทุกข้อแต่งขึ้นใหม่เพื่อฝึก จำนวนข้อ เวลา และสัดส่วนเนื้อหาอ้างตามผังสอบของ ทปอ.
        ดูตัวอย่างข้อสอบทางการได้ที่หน้า <a href="#/official">ข้อสอบตัวอย่าง</a></p></details>
    <details><summary>ความคืบหน้าของฉันเก็บไว้ที่ไหน</summary>
      <p>ในเบราว์เซอร์ของเครื่องที่คุณใช้อยู่ ไม่มีการส่งออกไปที่ใด ถ้าเปลี่ยนเครื่อง เปลี่ยนเบราว์เซอร์
        หรือล้างข้อมูลเว็บ ความคืบหน้าจะเริ่มใหม่</p></details>
    <details><summary>ควรเริ่มจากวิชาไหน</summary>
      <p>TGAT ทั้งสามพาร์ตทุกคนต้องสอบ แนะนำเริ่มที่ TGAT2 ด้านที่ตัวเองไม่ถนัดที่สุด
        เพราะฝึกแล้วคะแนนขึ้นเห็นผลเร็ว ส่วน TPAT3 สำหรับคนที่จะยื่นคณะวิศวกรรมศาสตร์หรือสายใกล้เคียง</p></details>
    <details><summary>เจอข้อที่คิดว่าเฉลยผิด ทำอย่างไร</summary>
      <p>เนื้อหายังไม่ได้ผ่านการตรวจโดยครู จึงอาจมีจุดผิด ให้เทียบกับตำราหรือถามครู
        และอ่านที่มาของเนื้อหาได้ที่หน้า <a href="#/how">เบื้องหลังการสร้าง</a></p></details>
  </div>

  <div class="cta-row" style="margin-top:22px"><a class="btn primary big" href="#/">เลือกวิชาเริ่มฝึก</a></div>`;

  // โจทย์ตัวอย่างใช้ตัวฝึกโจทย์ตัวจริง ผู้ใช้จึงเห็นหน้าตาเดียวกับที่จะเจอ
  const box = document.getElementById("guideDemo");
  if (!demo || !demo.problems) { box.innerHTML = ""; return; }
  try {
    const data = await getJSON(`data/problems/${GUIDE_DEMO_TOPIC}.json`);
    const first = data.items.slice().sort((a, b) => a.difficulty - b.difficulty).slice(0, 1)
      .map((p) => ({ base: p, topic: GUIDE_DEMO_TOPIC }));
    startSession(box, first, { mode: "learn", title: demo.name_th, onRestart: () => pageGuide() });
  } catch (e) {
    box.innerHTML = `<p class="muted">โหลดโจทย์ตัวอย่างไม่ได้ ลองเข้าไปที่ <a href="#/t/${GUIDE_DEMO_TOPIC}/practice">หัวข้อนี้</a> โดยตรง</p>`;
  }
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
  store.setLast(id, tab);

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
          ${b.wrong_md.trim() === b.title.trim() ? "" : `<div class="box-wrong"><b>คิดผิด:</b> ${md(b.wrong_md, figs)}</div>`}
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
          <button class="btn primary" id="again">${opts.mode === "exam" ? "ทำชุดใหม่ (สุ่มข้อใหม่)" : "ทำชุดใหม่ (ตัวเลข/รูปใหม่)"}</button>
          <button class="btn" id="review">ดูเฉลยทีละข้อ</button>
        </div></div>
      ${opts.extraSummary ? opts.extraSummary({ total, n, used: S.used || 0 }) : ""}
      ${secTable}
      ${weak.length && opts.showTopics ? `<h3>หัวข้อที่ควรทบทวน</h3>${weak.map(([id]) =>
        `<a class="leaf" href="#/t/${id}"><span class="t">${esc(CATALOG.byId[id].name_th)}</span><span class="badge warn">ได้ ${Math.round(byTopic[id][0] / byTopic[id][1] * 100)}%</span></a>`).join("")}` : ""}`;
    document.getElementById("again").addEventListener("click", () => opts.onRestart());
    document.getElementById("review").addEventListener("click", () => { S.done = true; S.i = 0; render(); });
    if (opts.bindSummary) opts.bindSummary({ total, n, used: S.used || 0 });
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
  return EXAM_BLUEPRINT[sid].sections.map((sec) => ({ ...sec, name: sec.name || (c.byId[sec.id] || {}).name_th || sec.id }));
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
  // แบ่งจำนวนข้อให้แต่ละส่วนแบบเศษมากได้ก่อน ผลรวมจึงตรงกับจำนวนที่ปุ่มประกาศเสมอ
  // (ปัดแยกทีละส่วนทำให้ครึ่งชุดและชุดสั้นได้ข้อเกินมา 1-2 ข้อ)
  const total = size === "full" ? secs.reduce((a, x) => a + x.n, 0) : Math.round(bp.items * frac);
  const exact = secs.map((x) => x.n * frac);
  const quota = exact.map((v) => Math.max(1, Math.floor(v)));
  const order = exact.map((v, i) => [v - Math.floor(v), i]).sort((a, b) => b[0] - a[0]);
  for (let k = 0; quota.reduce((a, v) => a + v, 0) < total; k++) quota[order[k % order.length][1]]++;
  // ข้อที่ใช้บทอ่านเดียวกันไม่ออกพร้อมกันในชุดเดียว เพราะตัวเลือกของข้อหนึ่งอาจบอกคำตอบของอีกข้อ
  // ใช้กับ TGAT1 และ TGAT2 ที่มีบทอ่านหรือสถานการณ์ร่วมจริง วิชาอื่นโจทย์ยาวเพราะคำสั่ง ไม่ใช่เพราะใช้เรื่องเดียวกัน
  const sharesPassage = sid === "tgat1" || sid === "tgat2";
  // ใช้กลุ่มที่จัดไว้ในข้อมูลก่อน (ครอบคลุมข้อสั้นและข้อเรียงประโยคที่ข้อความขึ้นต้นต่างกัน) ถ้าไม่มีจึงเดาจากข้อความขึ้นต้น
  const passageKey = (p) => p.group
    || (sharesPassage && p.stem_md && p.stem_md.length > 200 ? p.stem_md.slice(0, 80) : null);
  const usedPassage = new Set();
  secs.forEach((sec, si) => {
    const pool = shuffle(bank.items.filter((p) => p.topic.startsWith(sec.id + ".")));
    const want = quota[si];
    const picked = [];
    for (const p of pool) {
      if (picked.length >= want) break;
      const key = passageKey(p);
      if (key && usedPassage.has(key)) continue;
      if (key) usedPassage.add(key);
      picked.push({ base: p, topic: p.topic });
    }
    if (picked.length < want) short.push(`${sec.name} (มี ${picked.length} จาก ${want} ข้อ)`);
    entries.push(...picked);
  });
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

/* ---------- ท้าเพื่อน
 * ไม่มีเซิร์ฟเวอร์: ลิงก์เก็บรหัสชุด (วิชา + เลขสุ่ม) ทุกเครื่องที่เปิดลิงก์เดียวกันสุ่มด้วยเลขเดียวกันจึงได้โจทย์ชุดเดียวกัน
 * คะแนนของคนท้าแนบไปในลิงก์เป็นตัวเลขธรรมดา (คะแนน-วินาที) ไม่มีการยืนยันตัวตน เป็นเกมระหว่างเพื่อน ไม่ใช่การสอบ */
const DUEL_N = 10;
const DUEL_MIN = 10;

function seededRandom(seed) {          // mulberry32
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function duelLink(sid, seed, result) {
  const base = location.href.split("#")[0];
  return `${base}#/duel/${sid}/${seed}${result ? "/" + result : ""}`;
}

async function pageDuel(sid, seedText, rival) {
  const c = await catalog();
  const subjects = c.subjects.filter((x) => EXAM_BLUEPRINT[x.id]);

  if (!sid || !seedText) {
    $app.innerHTML = `<h1>ท้าเพื่อน</h1>
      <p class="lead">เลือกวิชา แล้วจะได้ลิงก์ของโจทย์ ${DUEL_N} ข้อ ส่งลิงก์ให้เพื่อน ทุกคนที่เปิดจะได้โจทย์ชุดเดียวกัน
        จับเวลา ${DUEL_MIN} นาที ไม่มีคำใบ้ระหว่างทำ ส่งแล้วเห็นคะแนนและเฉลยทุกข้อ</p>
      <div class="subjects">${subjects.map((x) => `<button class="card subject-card duel-pick" data-sid="${x.id}">
        <span class="code">${SUBJECT_INFO[x.id].short}</span>
        <span class="name">${esc(x.name_th.replace(SUBJECT_INFO[x.id].short + " ", ""))}</span>
        <span class="what">สร้างชุดใหม่ของวิชานี้</span></button>`).join("")}</div>
      <div class="note">คะแนนเก็บในเครื่องของแต่ละคน เว็บไม่มีระบบสมาชิก การเทียบคะแนนทำโดยส่งลิงก์ผลให้กัน
        ชุดเดียวกันทำซ้ำได้ แต่ครั้งที่สองจะจำคำตอบได้ ถ้าจะแข่งใหม่ให้สร้างชุดใหม่</div>`;
    $app.querySelectorAll(".duel-pick").forEach((b) => b.addEventListener("click", () => {
      location.hash = `#/duel/${b.dataset.sid}/${Math.floor(Math.random() * 900000) + 100000}`;
    }));
    return;
  }

  const seed = parseInt(seedText, 10);
  if (!EXAM_BLUEPRINT[sid] || !Number.isFinite(seed)) return notFound();
  const secs = examSections(c, sid);
  const m = /^(\d+(?:\.\d+)?)-(\d+)$/.exec(rival || "");
  const rivalScore = m ? Math.min(DUEL_N, parseFloat(m[1])) : null;
  const rivalSec = m ? parseInt(m[2], 10) : null;
  const fmt = (t) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;

  $app.innerHTML = `${crumbs(c, sid)}<h1>ท้าเพื่อน · ${SUBJECT_INFO[sid].short} · ชุด ${seed}</h1>
    ${rivalScore != null ? `<div class="note"><b>เพื่อนทำได้ ${rivalScore} / ${DUEL_N} ใช้เวลา ${fmt(rivalSec)}</b> ลองทำชุดเดียวกันดู</div>` : ""}
    <div id="tabBody"><p class="muted">กำลังเตรียมโจทย์…</p></div>`;

  // เลือกโจทย์ด้วยเลขสุ่มของชุด: เรียงคลังตาม id ก่อน เพื่อให้ทุกเครื่องเริ่มจากลำดับเดียวกัน แล้วเวียนเลือกทีละส่วน
  const bank = await getJSON(`data/exam/${sid}.json`);
  const rnd = seededRandom(seed);
  const pools = secs.map((sec) => shuffle(bank.items.filter((p) => p.topic.startsWith(sec.id + "."))
    .sort((a, b) => (a.id < b.id ? -1 : 1)), rnd));
  const used = new Set();
  const picked = [];
  for (let k = 0; picked.length < DUEL_N && k < DUEL_N * 20; k++) {
    const pool = pools[k % pools.length];
    const p = pool.shift();
    if (!p) continue;
    const key = p.group || p.id;
    if (used.has(key)) continue;
    used.add(key);
    picked.push({ base: p, topic: p.topic });
  }
  const items = picked.sort((a, b) => a.base.difficulty - b.base.difficulty || (a.base.id < b.base.id ? -1 : 1));

  startSession(document.getElementById("tabBody"), items, {
    mode: "exam", fresh: false, limitSec: DUEL_MIN * 60, showTopics: true,
    title: `ท้าเพื่อน ${SUBJECT_INFO[sid].short} ชุด ${seed} · ${items.length} ข้อ`,
    onRestart: () => { location.hash = "#/duel"; },
    extraSummary: ({ total, n, used: sec }) => {
      const mine = Number.isInteger(total) ? total : total.toFixed(2);
      let verdict = "";
      if (rivalScore != null) {
        verdict = total > rivalScore || (total === rivalScore && sec < rivalSec)
          ? `<p><b>คุณชนะ</b> เพื่อนได้ ${rivalScore} / ${n} ใช้ ${fmt(rivalSec)}</p>`
          : total === rivalScore && sec === rivalSec
            ? `<p><b>เสมอกัน</b> เพื่อนได้ ${rivalScore} / ${n} ใช้ ${fmt(rivalSec)}</p>`
            : `<p><b>เพื่อนยังนำอยู่</b> เพื่อนได้ ${rivalScore} / ${n} ใช้ ${fmt(rivalSec)} ดูเฉลยข้อที่พลาดแล้วสร้างชุดใหม่ไปท้ากลับ</p>`;
      }
      return `<div class="card duel-share">
        ${verdict}
        <p style="margin:0 0 8px"><b>ส่งผลให้เพื่อน</b> เพื่อนเปิดลิงก์นี้จะได้โจทย์ชุดเดียวกัน และเห็นคะแนนของคุณเป็นเป้า</p>
        <textarea id="duelText" readonly rows="3" aria-label="ข้อความสำหรับส่งให้เพื่อน">ฉันได้ ${mine}/${n} ใช้เวลา ${fmt(sec)} ในชุด ${SUBJECT_INFO[sid].short} ลองทำชุดเดียวกันดู ${duelLink(sid, seed, `${mine}-${sec}`)}</textarea>
        <div class="row" style="justify-content:center;margin-top:8px">
          <button class="btn" id="duelCopy">คัดลอกข้อความ</button>
          <a class="btn" href="#/duel">สร้างชุดใหม่</a>
        </div>
        <p class="muted" id="duelCopied" role="status" style="margin:6px 0 0"></p></div>`;
    },
    bindSummary: () => {
      const btn = document.getElementById("duelCopy");
      const again = document.getElementById("again");
      if (again) again.textContent = "สร้างชุดใหม่";
      if (!btn) return;
      btn.addEventListener("click", async () => {
        const ta = document.getElementById("duelText");
        const note = document.getElementById("duelCopied");
        try { await navigator.clipboard.writeText(ta.value); note.textContent = "คัดลอกแล้ว นำไปวางในแชตได้เลย"; }
        catch { ta.focus(); ta.select(); note.textContent = "คัดลอกอัตโนมัติไม่ได้ เลือกข้อความในกล่องแล้วคัดลอกเอง"; }
      });
    },
  });
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
      <li><b>คาน รอก เฟือง</b> (TPAT3) — เก็บระบบเป็นข้อมูลก่อน แล้วให้ทั้งรูปและเฉลยสร้างจากข้อมูลชุดเดียวกัน
        เช่น จำนวนเส้นเชือกที่รับน้ำหนักนับจากเส้นทางเชือกเส้นเดียวกับที่ใช้วาดรูป รูปกับคำตอบจึงไม่มีทางขัดกัน</li>
      <li><b>ภาพฉายและเงา</b> — ตัวเลือกทั้งห้าต้องเป็นรูปที่ต่างกันจริงแม้หมุนหรือพลิก
        และโปรแกรมตรวจด้วยว่าคำตอบหาได้จากรูปจริง ไม่ขึ้นกับลูกบาศก์ที่ถูกบังจนมองไม่เห็น</li>
    </ul>
    <p>โจทย์กลุ่มตัวเลขใช้แม่แบบที่สุ่มค่าใหม่ได้ ก่อนนำขึ้นเว็บจะถูกสุ่มทดสอบข้อละ 200 ครั้ง
      ถ้ามีแม้แต่ครั้งเดียวที่ได้โจทย์กำกวม ตัวเลือกซ้ำ หรือคำใบ้เผยคำตอบ ถือว่าแม่แบบนั้นไม่ผ่าน</p>
  </div>

  <h2>ตรวจสองชั้น: เครื่องตรวจ และผู้ตรวจอีกคน</h2>
  <div class="card">
    <p><b>ชั้นแรกคือเครื่อง</b> ทุกข้อต้องผ่านกฎที่ตรวจได้อัตโนมัติ เช่น คำใบ้ต้องมีสามระดับและห้ามมีคำตอบอยู่ในนั้น ·
      ตัวลวงทุกตัวต้องมีเหตุผลของตัวเอง · คำตอบต้องไม่ใช่ตัวเลือกที่ยาวที่สุดบ่อยเกินไป จนเดาจากความยาวได้ ·
      ระดับความยากในแต่ละหัวข้อต้องกระจายตามสัดส่วนที่กำหนด</p>
    <p>ตัวอย่างสิ่งที่เครื่องจับได้ระหว่างทำ: โจทย์ภาพฉายข้อหนึ่งมีลูกบาศก์ซ่อนอยู่หลังอีกก้อนพอดี
      คำตอบจึงขึ้นกับก้อนที่ผู้ทำมองไม่เห็น โปรแกรมหยุดการสร้างไฟล์ทันทีจนกว่าจะเปลี่ยนทรง</p>
    <p><b>ชั้นที่สองคือผู้ตรวจอิสระ</b> เนื้อหาเขียนโดยใช้ AI สองระบบแบ่งงานกัน (Claude และ Codex)
      แล้วให้ระบบหนึ่งตรวจงานที่อีกระบบเขียนโดยไม่แก้เอง เขียนเป็นรายงานพร้อมระดับความรุนแรง
      แล้วคนเขียนเดิมเป็นผู้ตัดสินว่ารับหรือไม่รับทีละข้อพร้อมเหตุผล</p>
    <p>รอบแรกตรวจข้อภาษาไทย 129 ข้อ พบปัญหา 10 ข้อ รับแก้ 9 ข้อ เช่น โจทย์อุปมา "ตรัส : พูด :: เสวย : ?"
      ที่ตั้งคำตอบเป็น "กิน" แต่ตัวลวง "ดื่ม" ก็ถูกด้วย เพราะ เสวย ใช้กับการดื่มได้เช่นกัน
      ข้อนี้ผ่านการตรวจของเครื่องมาได้ เพราะเครื่องตรวจรูปแบบได้ แต่ตรวจความหมายของภาษาไม่ได้</p>
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
      <li>เนื้อหาเขียนโดยใช้ AI ช่วย ผ่านการตรวจของเครื่องและการตรวจไขว้แล้ว แต่ <b>ยังไม่ได้ผ่านการตรวจโดยครูหรือผู้เชี่ยวชาญ</b>
        จึงยังอาจมีจุดผิด</li>
      <li>เกณฑ์คะแนนย่อยของ TGAT3 ในเว็บนี้เป็นเกณฑ์ที่เรากำหนดขึ้นเพื่อฝึก ไม่ใช่เกณฑ์ทางการ</li>
      <li>ตอนนี้มี TGAT ครบทั้งสามพาร์ตและ TPAT3 ยังไม่มี TPAT วิชาอื่นและ A-Level</li>
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
    else if (a === "duel") await pageDuel(b, c2, h.split("/")[3]);
    else if (a === "progress") await pageProgress();
    else if (a === "redo") await pageRedo();
    else if (a === "official") pageOfficial();
    else if (a === "how") await pageBuild();
    else if (a === "guide") await pageGuide();
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
