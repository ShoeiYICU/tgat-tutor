/* ทวนตามช่วงเวลา · บัตรคำศัพท์ · จับเวลาอ่านหนังสือ · นับถอยหลังวันสอบ
 * ใช้ตัวแปรกลางจาก app.js (store, $app, esc, catalog, getJSON, startSession, shuffle, topicOfItemId,
 * SUBJECT_INFO, dayNum, dayKey, REVIEW_GAPS) ไฟล์นี้โหลดก่อน app.js จึงเรียกตัวแปรเหล่านั้นตอนทำงานเท่านั้น */
"use strict";

/* ======================================================== ทวนข้อที่ถึงกำหนด */

function dueItemIds() {
  const items = store.get().items || {};
  const today = dayNum();
  return Object.keys(items).filter((id) => {
    const it = items[id];
    if (it.box) return it.due <= today;
    // ข้อที่ผิดก่อนมีระบบทวน ถือว่าถึงกำหนดแล้ว
    return it.box == null && it.tries > 0 && it.best < 1;
  });
}
function upcomingCount(days) {
  const items = store.get().items || {};
  const lim = dayNum() + days;
  return Object.values(items).filter((it) => it.box && it.due <= lim).length;
}

async function pageReview() {
  const c = await catalog();
  const ids = dueItemIds();
  if (!ids.length) {
    const soon = upcomingCount(7);
    $app.innerHTML = `<h1>ทวนวันนี้</h1>
      <div class="card empty"><p><b>วันนี้ไม่มีข้อที่ต้องทวน</b></p>
      <p class="muted">ข้อที่ตอบผิดจะกลับมาให้ทำอีกครั้งในวันถัดไป ถ้าตอบถูกจะเว้นห่างออกไปเป็น 3 วัน 7 วัน 14 วัน และ 30 วัน
        ตอบถูกครบทุกรอบแล้วจึงถือว่าจำได้${soon ? ` · อีก 7 วันข้างหน้ามีข้อรอทวน ${soon} ข้อ` : ""}</p>
      <div class="row"><a class="btn primary" href="#/vocab">ทวนคำศัพท์</a><a class="btn" href="#/redo">ฝึกข้อที่เคยผิดทั้งหมด</a></div></div>`;
    return;
  }
  $app.innerHTML = `<h1>ทวนวันนี้</h1><div id="tabBody"><p class="muted">กำลังเตรียมโจทย์…</p></div>`;
  const byTopic = {};
  for (const id of ids) {
    const t = topicOfItemId(id);
    if (t && c.byId[t]) (byTopic[t] ||= []).push(id);
  }
  const files = await Promise.all(Object.keys(byTopic).map((t) => getJSON(`data/problems/${t}.json`).catch(() => null)));
  const items = store.get().items;
  const entries = [];
  files.forEach((f) => {
    if (!f) return;
    const want = new Set(byTopic[f.topic_id]);
    f.items.filter((p) => want.has(p.id)).forEach((p) => entries.push({ base: p, topic: f.topic_id }));
  });
  // ข้อที่เลยกำหนดนานที่สุดมาก่อน
  entries.sort((a, b) => ((items[a.base.id] || {}).due || 0) - ((items[b.base.id] || {}).due || 0));
  const picked = entries.slice(0, 20);
  const body = document.getElementById("tabBody");
  startSession(body, picked, {
    mode: "learn", fresh: true, showTopics: true,
    title: `ทวนวันนี้ ${picked.length} ข้อ`, onRestart: () => pageReview(),
  });
  body.insertAdjacentHTML("beforebegin", `<p class="muted">ถึงกำหนดทวน ${ids.length} ข้อ ครั้งละไม่เกิน 20 ข้อ
    · ตอบถูกแล้วข้อนั้นจะเว้นห่างออกไป ตอบผิดจะกลับมาพรุ่งนี้ · ตัวเลขและรูปสุ่มใหม่</p>`);
}

/* ======================================================== บัตรคำศัพท์ */

const VOCAB_NEW_PER_DAY = 15;
let VOCAB = null;
async function vocabData() { return (VOCAB ||= await getJSON("data/vocab/tgat1.json")); }

function vocabState() { return store.get().vocab || {}; }
function vocabDue(words) {
  const v = vocabState(), today = dayNum();
  return words.filter((w) => v[w.id] && v[w.id].box && v[w.id].due <= today);
}
function vocabNewToday() {
  const n = store.get().vocabNew;
  return n && n.day === dayNum() ? n.n : 0;
}

function speak(text) {
  try {
    if (!("speechSynthesis" in window)) return false;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/\.\.\./g, " "));
    u.lang = "en-US"; u.rate = 0.92;
    const v = speechSynthesis.getVoices().find((x) => /^en(-|_)(US|GB)/i.test(x.lang));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
    return true;
  } catch { return false; }
}

async function pageVocab(deckId) {
  const data = await vocabData();
  const v = vocabState();
  const all = data.words;
  if (!deckId) {
    const due = vocabDue(all).length;
    const learned = all.filter((w) => v[w.id]).length;
    const mastered = all.filter((w) => v[w.id] && v[w.id].box === 0).length;
    const newLeft = Math.max(0, VOCAB_NEW_PER_DAY - vocabNewToday());
    $app.innerHTML = `<h1>คำศัพท์ TGAT1</h1>
      <p class="lead">บัตรคำ ${all.length} คำ แบ่ง ${data.decks.length} ชุด กดฟังเสียงได้ ทวนตามช่วงเวลา: คำที่จำไม่ได้กลับมาพรุ่งนี้ คำที่จำได้เว้นห่างออกไปเรื่อย ๆ</p>
      <div class="card vocab-today">
        <div class="stats">
          <div class="stat"><b>${due}</b><span>คำที่ถึงกำหนดทวน</span></div>
          <div class="stat"><b>${learned}</b><span>คำที่เคยเปิดแล้ว</span></div>
          <div class="stat"><b>${mastered}</b><span>คำที่จำได้แล้ว</span></div>
        </div>
        <div class="row"><a class="btn primary" href="#/vocab/today">เริ่มทวนวันนี้ (${due} คำ${newLeft ? ` + คำใหม่ไม่เกิน ${newLeft} คำ` : ""})</a></div>
      </div>
      <h2>เลือกชุด</h2>
      <div class="grid">${data.decks.map((d) => {
        const ws = all.filter((w) => w.deck === d.id);
        const seen = ws.filter((w) => v[w.id]).length;
        return `<a class="card subject-card" href="#/vocab/${d.id}">
          <span class="name">${esc(d.name)}</span>
          <span class="muted small">${ws.length} คำ · เปิดแล้ว ${seen} คำ</span>
          <div class="bar"><i style="width:${Math.round(seen / ws.length * 100)}%"></i></div></a>`;
      }).join("")}</div>`;
    return;
  }

  // สร้างคิวบัตร: คำที่ถึงกำหนดก่อน แล้วคำใหม่
  let queue;
  if (deckId === "today") {
    const fresh = all.filter((w) => !v[w.id]).slice(0, Math.max(0, VOCAB_NEW_PER_DAY - vocabNewToday()));
    queue = [...shuffle(vocabDue(all)), ...fresh];
  } else {
    const ws = all.filter((w) => w.deck === deckId);
    if (!ws.length) return notFound();
    queue = [...shuffle(vocabDue(ws)), ...ws.filter((w) => !(v[w.id] && v[w.id].box > 0 && v[w.id].due > dayNum()))
      .filter((w) => !vocabDue(ws).includes(w))];
  }
  const deckName = deckId === "today" ? "ทวนวันนี้" : (data.decks.find((d) => d.id === deckId) || {}).name;
  if (!queue.length) {
    $app.innerHTML = `<h1>${esc(deckName)}</h1><div class="card empty"><p><b>ไม่มีบัตรที่ต้องทวนตอนนี้</b></p>
      <p class="muted">คำที่จำได้จะกลับมาตามกำหนด มาทวนใหม่พรุ่งนี้ หรือเลือกชุดอื่น</p>
      <a class="btn primary" href="#/vocab">กลับไปหน้าคำศัพท์</a></div>`;
    return;
  }
  let i = 0, flipped = false, reverse = false, good = 0, again = 0;
  const total = queue.length;

  function grade(ok) {
    const w = queue[i];
    store.update((s) => {
      const vv = (s.vocab ||= {});
      const isNew = !vv[w.id];
      const st = (vv[w.id] ||= { box: 0, due: null });
      if (isNew) {
        const today = dayNum();
        if (!s.vocabNew || s.vocabNew.day !== today) s.vocabNew = { day: today, n: 0 };
        s.vocabNew.n += 1;
      }
      if (ok) {
        st.box = (st.box || 0) + 1;
        if (st.box >= REVIEW_GAPS.length) { st.box = 0; st.due = null; }
        else st.due = dayNum() + REVIEW_GAPS[st.box];
      } else { st.box = 1; st.due = dayNum() + 1; }
      const day = dayKey(new Date());
      (s.days ||= {})[day] = (s.days[day] || 0) + 1;
    });
    if (ok) good += 1;
    else { again += 1; if (queue.slice(i + 1).indexOf(w) < 0) queue.push(w); }   // จำไม่ได้ ให้กลับมาท้ายคิวอีกรอบ
    i += 1; flipped = false; draw();
  }

  function draw() {
    if (i >= queue.length) {
      $app.innerHTML = `<h1>${esc(deckName)}</h1>
        <div class="card"><p><b>ครบแล้ว ${total} คำ</b></p>
        <p>จำได้ ${good} ครั้ง · ยังจำไม่ได้ ${again} ครั้ง ${again ? "(คำเหล่านั้นจะกลับมาพรุ่งนี้)" : ""}</p>
        <div class="row"><a class="btn primary" href="#/vocab">กลับไปหน้าคำศัพท์</a><a class="btn" href="#/review">ทวนโจทย์วันนี้</a></div></div>`;
      return;
    }
    const w = queue[i];
    const front = reverse ? `<div class="vc-th big">${esc(w.th)}</div>` :
      `<div class="vc-word">${esc(w.word)}</div><div class="muted">${esc(w.pos)}</div>`;
    const back = `${reverse ? `<div class="vc-word">${esc(w.word)}</div><div class="muted">${esc(w.pos)}</div>` : `<div class="vc-th">${esc(w.th)}</div>`}
      <p class="vc-ex">${esc(w.ex)} <button class="btn vc-say" data-say="ex" aria-label="ฟังประโยคตัวอย่าง">🔊</button></p>
      <p class="muted">${esc(w.ex_th)}</p>`;
    $app.innerHTML = `<div class="crumbs"><a href="#/vocab">คำศัพท์</a> › ${esc(deckName)}</div>
      <div class="vc-head"><span>บัตรที่ ${i + 1} / ${queue.length}</span>
        <label class="muted"><input type="checkbox" id="vcRev" ${reverse ? "checked" : ""}> เริ่มจากความหมายไทย</label></div>
      <div class="card vc-card ${flipped ? "flipped" : ""}" id="vcCard" role="button" tabindex="0" aria-label="แตะเพื่อพลิกบัตร">
        ${front}
        <button class="btn vc-say" data-say="word" aria-label="ฟังเสียงคำศัพท์">🔊 ฟังเสียง</button>
        ${flipped ? `<hr>${back}` : `<p class="muted small">แตะบัตรหรือกด Space เพื่อดูความหมาย</p>`}
      </div>
      <div class="row vc-btns">${flipped
        ? `<button class="btn" id="vcAgain">ยังจำไม่ได้ (1)</button><button class="btn primary" id="vcGood">จำได้ (2)</button>`
        : `<button class="btn primary" id="vcFlip">ดูความหมาย</button>`}</div>`;
    const card = document.getElementById("vcCard");
    card.addEventListener("click", (e) => { if (!e.target.closest(".vc-say") && !flipped) { flipped = true; draw(); } });
    $app.querySelectorAll(".vc-say").forEach((b) => b.addEventListener("click", (e) => {
      e.stopPropagation();
      if (!speak(b.dataset.say === "ex" ? w.ex : w.word)) b.textContent = "เครื่องนี้อ่านออกเสียงไม่ได้";
    }));
    const on = (id, fn) => { const x = document.getElementById(id); if (x) x.addEventListener("click", fn); };
    on("vcFlip", () => { flipped = true; draw(); });
    on("vcAgain", () => grade(false));
    on("vcGood", () => grade(true));
    document.getElementById("vcRev").addEventListener("change", (e) => { reverse = e.target.checked; draw(); });
  }
  const keys = (e) => {
    if (!location.hash.startsWith("#/vocab/")) { document.removeEventListener("keydown", keys); return; }
    if (e.target.closest && e.target.closest("input, textarea, select")) return;
    if ((e.key === " " || e.key === "Enter") && !flipped) { e.preventDefault(); flipped = true; draw(); }
    else if (flipped && e.key === "1") grade(false);
    else if (flipped && e.key === "2") grade(true);
  };
  document.addEventListener("keydown", keys);
  draw();
}

/* ======================================================== เวลาอ่านหนังสือ */

const STUDY_COLORS = { tgat1: "#3b82f6", tgat2: "#f59e0b", tgat3: "#10b981", tpat3: "#ef4444", math1: "#8b5cf6", other: "#64748b" };
const subjName = (k) => (SUBJECT_INFO[k] ? SUBJECT_INFO[k].short : "อื่น ๆ");

function addStudy(subject, sec) {
  if (!sec) return;
  store.update((s) => {
    const d = (s.study ||= {})[dayKey(new Date())] ||= {};
    d[subject] = (d[subject] || 0) + sec;
  });
}

/* นับเวลาอัตโนมัติขณะอยู่ในหน้าเรียนหรือฝึก: นับเฉพาะตอนเปิดหน้าอยู่และมีการแตะหรือพิมพ์ภายใน 90 วินาที */
const StudyClock = (() => {
  const TICK = 15;
  let subject = null, lastAct = Date.now();
  const act = () => { lastAct = Date.now(); };
  ["pointerdown", "keydown", "wheel", "touchstart", "scroll"].forEach((ev) => addEventListener(ev, act, { passive: true }));
  setInterval(() => {
    if (!subject || document.hidden || Date.now() - lastAct > 90000) return;
    if (manualTimer()) return;            // ตัวจับเวลาเองกำลังเดิน ไม่นับซ้ำ
    addStudy(subject, TICK);
  }, TICK * 1000);
  return { set(s) { subject = s || null; act(); } };
})();

function studyContextFromHash(h) {
  const [a, b] = h.replace(/^#\/?/, "").split("/");
  if (a === "t" && b) return decodeURIComponent(b).split(".")[0];
  if (["s", "exam", "duel"].includes(a) && b) return b;
  if (a === "vocab") return "tgat1";
  if (a === "review" || a === "redo") return "other";
  return null;
}

function manualTimer() { return store.get().timer || null; }
function weekData() {
  const s = store.get().study || {};
  const out = [];
  for (let k = 6; k >= 0; k--) {
    const d = new Date(); d.setDate(d.getDate() - k);
    out.push({ d, key: dayKey(d), v: s[dayKey(d)] || {} });
  }
  return out;
}
function fmtMin(sec) {
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)} ชม. ${m % 60} นาที` : `${m} นาที`;
}
function todayStudySec() { return Object.values((store.get().study || {})[dayKey(new Date())] || {}).reduce((a, b) => a + b, 0); }

function studyChartHTML() {
  const wk = weekData();
  const tot = wk.map((x) => Object.values(x.v).reduce((a, b) => a + b, 0));
  const max = Math.max(1800, ...tot);
  const subjects = [...new Set(wk.flatMap((x) => Object.keys(x.v)))];
  const W = 320, H = 150, bw = 30, gap = (W - 7 * bw) / 8;
  const bars = wk.map((x, i) => {
    let y = H - 20;
    const xs = gap + i * (bw + gap);
    const segs = subjects.map((k) => {
      const h = (x.v[k] || 0) / max * (H - 30);
      if (!h) return "";
      y -= h;
      return `<rect x="${xs}" y="${y.toFixed(1)}" width="${bw}" height="${h.toFixed(1)}" rx="3" fill="${STUDY_COLORS[k] || STUDY_COLORS.other}"><title>${subjName(k)} ${fmtMin(x.v[k])}</title></rect>`;
    }).join("");
    const lab = x.d.toLocaleDateString("th-TH", { weekday: "narrow" });
    return `${segs}<text x="${xs + bw / 2}" y="${H - 5}" text-anchor="middle" font-size="11" fill="currentColor" opacity=".7">${lab}</text>
      ${tot[i] ? `<text x="${xs + bw / 2}" y="${(y - 4).toFixed(1)}" text-anchor="middle" font-size="10" fill="currentColor">${Math.round(tot[i] / 60)}</text>` : ""}`;
  }).join("");
  const sum = tot.reduce((a, b) => a + b, 0);
  return `<div class="card study-chart">
    <div class="row" style="justify-content:space-between"><b>เวลาเรียน 7 วันล่าสุด · รวม ${fmtMin(sum)}</b><a href="#/timer">จับเวลาเอง</a></div>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="กราฟเวลาเรียนรายวัน 7 วันล่าสุด หน่วยนาที">${bars}</svg>
    <p class="legend">${subjects.length ? subjects.map((k) => `<span><i style="background:${STUDY_COLORS[k] || STUDY_COLORS.other}"></i>${subjName(k)}</span>`).join("")
      : `<span class="muted">ยังไม่มีเวลาเรียนบันทึกไว้ เว็บจะนับให้เองเมื่อเปิดบทเรียนหรือทำโจทย์</span>`}</p>
  </div>`;
}

async function pageTimer() {
  const c = await catalog();
  const opts = [...c.subjects.map((x) => [x.id, SUBJECT_INFO[x.id].short]), ["other", "อื่น ๆ (อ่านหนังสือนอกเว็บ)"]];
  let tick = null;
  function draw() {
    const t = manualTimer();
    const run = t ? Math.floor((Date.now() - t.start) / 1000) : 0;
    const hh = String(Math.floor(run / 3600)).padStart(2, "0"), mm = String(Math.floor(run / 60) % 60).padStart(2, "0"), ss = String(run % 60).padStart(2, "0");
    const goal = t && t.goal ? t.goal * 60 : 0;
    $app.innerHTML = `<h1>จับเวลาอ่านหนังสือ</h1>
      <p class="muted">เวลาที่ทำโจทย์หรืออ่านบทเรียนในเว็บนับให้อัตโนมัติอยู่แล้ว ใช้ตัวจับเวลานี้ตอนอ่านหนังสือหรือทำแบบฝึกนอกเว็บ</p>
      <div class="card timer-card">
        <div class="timer-big" aria-live="off">${hh}:${mm}:${ss}</div>
        ${goal ? `<div class="bar"><i style="width:${Math.min(100, run / goal * 100)}%"></i></div>
          <p class="muted small">${run >= goal ? "ครบเวลาที่ตั้งไว้แล้ว พักสายตาสัก 5 นาที" : `เป้า ${t.goal} นาที`}</p>` : ""}
        <div class="row">
          <select id="tmSub" ${t ? "disabled" : ""} aria-label="วิชา">${opts.map(([k, n]) => `<option value="${k}" ${t && t.subject === k ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>
          ${t ? "" : `<select id="tmGoal" aria-label="เป้าเวลา"><option value="0">ไม่ตั้งเป้า</option><option value="25">25 นาที</option><option value="50">50 นาที</option><option value="90">90 นาที</option></select>`}
          ${t ? `<button class="btn primary" id="tmStop">หยุดและบันทึก</button><button class="btn" id="tmDrop">ยกเลิก</button>`
              : `<button class="btn primary" id="tmStart">เริ่มจับเวลา</button>`}
        </div>
        <p class="muted small">วันนี้เรียนไปแล้ว ${fmtMin(todayStudySec())}</p>
      </div>
      ${studyChartHTML()}
      <h2>วันสอบของฉัน</h2>
      ${examDatesEditorHTML()}`;
    const on = (id, fn) => { const x = document.getElementById(id); if (x) x.addEventListener("click", fn); };
    on("tmStart", () => {
      const subject = document.getElementById("tmSub").value, goal = +document.getElementById("tmGoal").value;
      store.update((s) => { s.timer = { subject, goal, start: Date.now() }; });
      draw();
    });
    on("tmStop", () => {
      const t2 = manualTimer();
      if (t2) addStudy(t2.subject, Math.min(12 * 3600, Math.floor((Date.now() - t2.start) / 1000)));
      store.update((s) => { delete s.timer; });
      draw();
    });
    on("tmDrop", () => { if (confirm("ยกเลิกโดยไม่บันทึกเวลานี้ใช่ไหม")) { store.update((s) => { delete s.timer; }); draw(); } });
    bindExamDates(draw);
  }
  draw();
  clearInterval(window.__tmTick);
  window.__tmTick = tick = setInterval(() => {
    if (!location.hash.startsWith("#/timer")) { clearInterval(tick); return; }
    const el = document.querySelector(".timer-big");
    if (el && manualTimer() && !document.activeElement.matches("input, select")) draw();
  }, 1000);
}

/* ======================================================== วันสอบ */

/* วันที่เริ่มต้นมาจากเว็บที่รวบรวมกำหนดการ TCAS70 (ค้นเมื่อ 10 พ.ย. 2569) ยังไม่ใช่ประกาศของ ทปอ. ผู้ใช้แก้เองได้ */
const DEFAULT_EXAMS = [
  { id: "tgat", name: "TGAT / TPAT2–5", date: "2027-01-30" },
  { id: "alevel", name: "A-Level", date: "2027-03-13" },
];
function examDates() { return store.get().examDates || DEFAULT_EXAMS; }
function daysUntil(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return dayNum(new Date(y, m - 1, d)) - dayNum();
}
function thDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" });
}
function countdownHTML() {
  const list = examDates().filter((e) => e.date && daysUntil(e.date) >= 0).sort((a, b) => a.date.localeCompare(b.date));
  if (!list.length) return "";
  return `<div class="countdown">${list.map((e) => {
    const n = daysUntil(e.date);
    return `<a class="cd" href="#/timer"><b>${n === 0 ? "วันนี้" : n}</b><span>${n === 0 ? "" : "วัน "}ถึง ${esc(e.name)}</span><small>${thDate(e.date)}</small></a>`;
  }).join("")}</div>`;
}
function examDatesEditorHTML() {
  return `<div class="card"><div class="exam-dates">${examDates().map((e, i) => `
      <label><span>${esc(e.name)}</span><input type="date" data-i="${i}" value="${esc(e.date || "")}"></label>`).join("")}</div>
    <p class="muted small">วันที่ตั้งต้นมาจากเว็บที่รวบรวมกำหนดการ TCAS70 ยังไม่ใช่ประกาศทางการ ตรวจวันสอบจริงที่
      <a href="https://www.mytcas.com/" target="_blank" rel="noopener noreferrer">mytcas.com</a> แล้วแก้ที่นี่ได้ เว็บจะนับถอยหลังบนหน้าแรกให้</p>
    <button class="btn" id="edReset">กลับเป็นค่าตั้งต้น</button></div>`;
}
function bindExamDates(redraw) {
  document.querySelectorAll(".exam-dates input").forEach((inp) => inp.addEventListener("change", () => {
    const list = examDates().map((e) => ({ ...e }));
    list[+inp.dataset.i].date = inp.value;
    store.update((s) => { s.examDates = list; });
  }));
  const r = document.getElementById("edReset");
  if (r) r.addEventListener("click", () => { store.update((s) => { delete s.examDates; }); redraw(); });
}

/* ======================================================== การ์ด "วันนี้" บนหน้าแรก */

async function todayCardHTML() {
  const due = dueItemIds().length;
  let vdue = 0, vnew = 0;
  try {
    const data = await vocabData();
    vdue = vocabDue(data.words).length;
    vnew = Math.min(VOCAB_NEW_PER_DAY - vocabNewToday(), data.words.filter((w) => !vocabState()[w.id]).length);
  } catch { /* ไม่มีไฟล์คำศัพท์ */ }
  const sec = todayStudySec();
  return `${countdownHTML()}
    <div class="today">
      <a class="card today-item" href="#/review"><b>${due}</b><span>ข้อที่ถึงกำหนดทวน</span><em>${due ? "ทวนเลย →" : "ไม่มีวันนี้"}</em></a>
      <a class="card today-item" href="#/vocab"><b>${vdue}</b><span>คำศัพท์ที่ต้องทวน</span><em>${vnew > 0 ? `+ คำใหม่ ${vnew} คำ →` : "ทวนคำศัพท์ →"}</em></a>
      <a class="card today-item" href="#/timer"><b>${Math.round(sec / 60)}</b><span>นาทีที่เรียนวันนี้</span><em>จับเวลา · ดูกราฟ →</em></a>
    </div>`;
}
