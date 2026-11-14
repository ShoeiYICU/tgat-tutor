/* แข่งกับเพื่อนแบบห้อง: สร้างห้อง ได้เลขห้อง 6 หลัก เพื่อนใส่เลขห้องเพื่อเข้าร่วม (1–10 คน)
 * ทุกคนได้โจทย์ชุดเดียวกัน คะแนนต่อข้อคิดจากความถูกต้องและเวลาที่เหลือ ตารางอันดับอัปเดตสด
 * เว็บนี้ไม่มีเซิร์ฟเวอร์ของตัวเอง จึงส่งข้อความระหว่างเครื่องผ่านตัวกลางรับส่งข้อความสาธารณะ (MQTT)
 * ข้อมูลที่ส่งมีเพียงชื่อเล่นที่ผู้เล่นพิมพ์ คะแนน และความคืบหน้า ไม่มีข้อมูลอื่นของผู้ใช้
 * ใช้ตัวแปรกลางจาก app.js: $app, esc, md, mdi, catalog, getJSON, shuffle, LETTERS, SUBJECT_INFO, EXAM_BLUEPRINT,
 *   parseNum, numRight, fmtNum, stepsHTML */
"use strict";

const RACE = {
  lib: "https://cdn.jsdelivr.net/npm/mqtt@5.10.1/dist/mqtt.min.js",
  // เลขตัวแรกของเลขห้องบอกว่าใช้ตัวกลางตัวไหน ทุกคนในห้องจึงต่อไปที่เดียวกันเสมอ
  brokers: ["wss://broker.emqx.io:8084/mqtt", "wss://broker.hivemq.com:8884/mqtt"],
  nameKey: "tgat-tutor.race.name",
  ttl: 3 * 3600,           // ข้อมูลห้องหมดอายุเองใน 3 ชั่วโมง
  cur: null,               // ห้องที่กำลังเปิดอยู่
};

function raceLoadLib() {
  if (window.mqtt) return Promise.resolve();
  if (!RACE.libP) {
    RACE.libP = new Promise((ok, bad) => {
      const s = document.createElement("script");
      s.src = RACE.lib; s.onload = ok;
      s.onerror = () => { RACE.libP = null; bad(new Error("โหลดตัวเชื่อมต่อไม่ได้ ต้องมีอินเทอร์เน็ต")); };
      document.head.appendChild(s);
    });
  }
  return RACE.libP;
}

function raceConnect(brokerIdx, timeoutMs = 9000) {
  return raceLoadLib().then(() => new Promise((ok, bad) => {
    const cl = window.mqtt.connect(RACE.brokers[brokerIdx], {
      protocolVersion: 5, clean: true, keepalive: 30, reconnectPeriod: 2500, connectTimeout: timeoutMs,
      clientId: "tt-" + Math.random().toString(36).slice(2, 12),
    });
    let done = false;
    const to = setTimeout(() => { if (!done) { done = true; cl.end(true); bad(new Error("เชื่อมต่อไม่สำเร็จ")); } }, timeoutMs + 500);
    cl.once("connect", () => { if (!done) { done = true; clearTimeout(to); ok(cl); } });
  }));
}

function raceLeave() {
  const r = RACE.cur;
  if (!r) return;
  RACE.cur = null;
  clearInterval(r.tick); clearTimeout(r.nextTo);
  try { r.cl.end(true); } catch { /* ปิดไปแล้ว */ }
}
window.addEventListener("hashchange", () => { if (!/^#\/race\/\d{6}/.test(location.hash)) raceLeave(); });

const racePid = (code) => {
  const k = `tgat-tutor.race.${code}`;
  let v = null;
  try { v = JSON.parse(sessionStorage.getItem(k)); } catch { /* */ }
  if (!v) { v = { pid: Math.random().toString(36).slice(2, 10), host: false }; try { sessionStorage.setItem(k, JSON.stringify(v)); } catch { /* */ } }
  return v;
};
const raceName = () => { try { return localStorage.getItem(RACE.nameKey) || ""; } catch { return ""; } };
const raceFmt = (ms) => { const s = Math.round(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

/* ---------- หน้าเริ่ม: สร้างห้อง หรือ ใส่เลขห้อง */
async function pageRace(code) {
  raceLeave();
  if (code && /^\d{6}$/.test(code)) return raceRoom(code);
  const c = await catalog();
  const subjects = c.subjects.filter((x) => EXAM_BLUEPRINT[x.id]);
  const opt = (arr, sel, f = (v) => v) => arr.map((v) => `<option value="${v}"${v === sel ? " selected" : ""}>${f(v)}</option>`).join("");
  $app.innerHTML = `<h1>แข่งกับเพื่อน</h1>
    <p class="lead">สร้างห้องแล้วบอกเลขห้องให้เพื่อน ทุกคนได้โจทย์ชุดเดียวกัน ตอบถูกและตอบเร็วได้คะแนนมาก ดูอันดับสดระหว่างแข่ง</p>
    <div class="card race-form">
      <label>ชื่อที่ใช้ในห้อง <input id="rcName" maxlength="16" value="${esc(raceName())}" placeholder="ชื่อเล่น" autocomplete="off"></label>
    </div>
    <div class="race-two">
      <div class="card race-form">
        <h2>เข้าห้องของเพื่อน</h2>
        <label>เลขห้อง 6 หลัก <input id="rcCode" inputmode="numeric" maxlength="6" placeholder="เช่น 148302" autocomplete="off"></label>
        <button class="btn primary" id="rcJoin">เข้าห้อง</button>
      </div>
      <div class="card race-form">
        <h2>สร้างห้องใหม่</h2>
        <label>วิชา <select id="rcSid">${subjects.map((x) => `<option value="${x.id}">${esc(SUBJECT_INFO[x.id].short)}</option>`).join("")}</select></label>
        <label>บทที่ใช้ <select id="rcChap"><option value="">ทุกบทของวิชา</option></select></label>
        <label>จำนวนข้อ <select id="rcN">${opt([5, 10, 15, 20], 10, (v) => `${v} ข้อ`)}</select></label>
        <label>เวลาต่อข้อ <select id="rcPer">${opt([30, 45, 60, 90, 120], 60, (v) => `${v} วินาที`)}</select></label>
        <label>จำนวนผู้เล่นสูงสุด <select id="rcMax">${opt([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 10, (v) => `${v} คน`)}</select></label>
        <button class="btn primary" id="rcCreate">สร้างห้อง</button>
      </div>
    </div>
    <p class="muted" id="rcMsg" role="status"></p>
    <div class="note">ต้องต่ออินเทอร์เน็ตตลอดการแข่ง ชื่อเล่นและคะแนนถูกส่งผ่านตัวกลางรับส่งข้อความสาธารณะเพื่อให้เครื่องของทุกคนในห้องเห็นกัน
      จึงไม่ควรใช้ชื่อจริงหรือข้อมูลส่วนตัวเป็นชื่อในห้อง ข้อมูลห้องหมดอายุเองภายใน 3 ชั่วโมง</div>`;
  const $ = (id) => document.getElementById(id);
  const msg = (t) => { $("rcMsg").textContent = t; };
  const fillChap = () => {
    const s = c.subjects.find((x) => x.id === $("rcSid").value);
    const chaps = s.topics.filter((t) => t.kind !== "leaf" && (s.children[t.id] || []).some((k) => k.kind === "leaf" && k.problems));
    $("rcChap").innerHTML = `<option value="">ทุกบทของวิชา</option>` + chaps.map((t) => `<option value="${t.id}">${esc(t.name_th)}</option>`).join("");
  };
  $("rcSid").addEventListener("change", fillChap); fillChap();
  const keepName = () => {
    const n = $("rcName").value.trim().slice(0, 16);
    if (!n) { msg("พิมพ์ชื่อที่ใช้ในห้องก่อน"); $("rcName").focus(); return null; }
    try { localStorage.setItem(RACE.nameKey, n); } catch { /* */ }
    return n;
  };
  $("rcJoin").addEventListener("click", () => {
    if (!keepName()) return;
    const v = $("rcCode").value.trim();
    if (!/^[1-9]\d{5}$/.test(v) || +v[0] > RACE.brokers.length) return msg("เลขห้องต้องเป็นตัวเลข 6 หลักที่เพื่อนให้มา");
    location.hash = `#/race/${v}`;
  });
  $("rcCode").addEventListener("keydown", (e) => { if (e.key === "Enter") $("rcJoin").click(); });
  $("rcCreate").addEventListener("click", async () => {
    if (!keepName()) return;
    const sid = $("rcSid").value, chap = $("rcChap").value, n = +$("rcN").value;
    $("rcCreate").disabled = true; msg("กำลังสร้างห้อง…");
    try {
      const bank = await getJSON(`data/exam/${sid}.json`);
      let pool = bank.items.filter((p) => !chap || p.topic.startsWith(chap + "."));
      const used = new Set(); const ids = [];
      for (const p of shuffle(pool)) {
        const key = p.group || p.id;
        if (used.has(key)) continue;
        used.add(key); ids.push(p.id);
        if (ids.length >= n) break;
      }
      if (ids.length < 1) throw new Error("บทนี้ยังไม่มีโจทย์");
      // ลองตัวกลางทีละตัว ตัวแรกที่ต่อได้เป็นตัวที่ห้องนี้ใช้
      let cl = null, bi = 0;
      for (; bi < RACE.brokers.length; bi++) { try { cl = await raceConnect(bi); break; } catch { /* ลองตัวถัดไป */ } }
      if (!cl) throw new Error("เชื่อมต่อไม่สำเร็จ ตรวจอินเทอร์เน็ตแล้วลองใหม่ (เครือข่ายบางแห่งปิดกั้นการเชื่อมต่อแบบนี้)");
      const code = String(bi + 1) + String(Math.floor(Math.random() * 100000)).padStart(5, "0");
      const me = racePid(code); me.host = true;
      try { sessionStorage.setItem(`tgat-tutor.race.${code}`, JSON.stringify(me)); } catch { /* */ }
      const cfg = { v: 1, host: me.pid, sid, chap, ids, per: +$("rcPer").value, max: +$("rcMax").value, state: "lobby", at: Date.now() };
      await new Promise((ok) => cl.publish(`tgattutor/v1/${code}/cfg`, JSON.stringify(cfg),
        { qos: 1, retain: true, properties: { messageExpiryInterval: RACE.ttl } }, ok));
      cl.end(true);
      location.hash = `#/race/${code}`;
    } catch (e) { msg(e.message); $("rcCreate").disabled = false; }
  });
}

/* ---------- ในห้อง */
async function raceRoom(code) {
  const name = raceName();
  if (!name) { location.hash = "#/race"; return; }
  const me = racePid(code);
  const base = `tgattutor/v1/${code}/`;
  $app.innerHTML = `<p class="crumbs"><a href="#/">หน้าแรก</a> › <a href="#/race">แข่งกับเพื่อน</a> › <span>ห้อง ${code}</span></p>
    <h1>ห้อง ${code}</h1><div id="raceBody"><p class="muted">กำลังเชื่อมต่อ…</p></div>`;
  const body = document.getElementById("raceBody");
  let cl;
  try { cl = await raceConnect(+code[0] - 1); }
  catch (e) { body.innerHTML = `<div class="card empty"><p><b>${esc(e.message)}</b></p><p class="muted">ตรวจอินเทอร์เน็ตแล้วลองใหม่ เครือข่ายบางแห่ง (เช่น ของโรงเรียน) อาจปิดกั้น ลองสลับไปใช้เน็ตมือถือ</p><a class="btn" href="#/race">กลับ</a></div>`; return; }
  if (!/^#\/race\//.test(location.hash) || !location.hash.endsWith(code)) { cl.end(true); return; }

  const R = RACE.cur = { cl, code, cfg: null, players: {}, items: null, i: 0, score: 0, right: 0, used: 0, log: [], phase: "wait", tick: null, nextTo: null };
  const pubOpts = { qos: 1, retain: true, properties: { messageExpiryInterval: RACE.ttl } };
  const pubMe = (extra = {}) => {
    R.mine = { name, joined: R.joined, i: R.i, score: R.score, right: R.right, used: R.used, done: R.phase === "done", ...extra };
    R.players[me.pid] = R.mine;
    cl.publish(`${base}p/${me.pid}`, JSON.stringify(R.mine), pubOpts);
  };
  const ranked = () => Object.entries(R.players).map(([pid, p]) => ({ pid, ...p }))
    .sort((a, b) => b.score - a.score || a.used - b.used || a.joined - b.joined);
  const board = (final) => {
    const n = R.cfg ? R.cfg.ids.length : 0;
    return `<table class="race-board"><thead><tr><th scope="col">อันดับ</th><th scope="col">ชื่อ</th><th scope="col">คะแนน</th><th scope="col">ถูก</th><th scope="col">${final ? "เวลารวม" : "ทำถึงข้อ"}</th></tr></thead><tbody>
      ${ranked().map((p, k) => `<tr class="${p.pid === me.pid ? "me" : ""}"><td>${k + 1}</td><td>${esc(p.name)}${p.pid === R.cfg.host ? ` <span class="badge">เจ้าของห้อง</span>` : ""}</td>
        <td><b>${p.score}</b></td><td>${p.right}</td><td>${p.done ? (final ? raceFmt(p.used) : "ครบแล้ว") : `${p.i}/${n}`}</td></tr>`).join("")}
    </tbody></table>`;
  };

  function lobby() {
    const list = Object.entries(R.players).map(([pid, p]) => ({ pid, ...p })).sort((a, b) => a.joined - b.joined);
    const isHost = R.cfg.host === me.pid;
    const chapName = R.cfg.chap && CATALOG.byId[R.cfg.chap] ? ` · ${CATALOG.byId[R.cfg.chap].name_th}` : "";
    body.innerHTML = `<div class="card" style="text-align:center">
        <p class="muted" style="margin:0">บอกเลขห้องนี้ให้เพื่อน</p>
        <div class="result-big race-code">${code}</div>
        <p>${esc(SUBJECT_INFO[R.cfg.sid].short)}${esc(chapName)} · ${R.cfg.ids.length} ข้อ · ข้อละ ${R.cfg.per} วินาที · สูงสุด ${R.cfg.max} คน</p>
        <div class="row" style="justify-content:center"><button class="btn" id="rcCopy">คัดลอกลิงก์ห้อง</button>
          ${isHost ? `<button class="btn primary" id="rcStart">เริ่มแข่ง (${list.length} คน)</button>` : ""}</div>
        ${isHost ? "" : `<p class="muted">รอเจ้าของห้องกดเริ่ม</p>`}
      </div>
      <h3>ผู้เล่นในห้อง ${list.length} / ${R.cfg.max}</h3>
      <div class="race-players">${list.map((p) => `<span class="badge ${p.pid === me.pid ? "acc" : ""}">${esc(p.name)}${p.pid === R.cfg.host ? " ★" : ""}</span>`).join("")}</div>
      <div class="note">คะแนนต่อข้อ: ตอบถูกได้ 500 คะแนน บวกโบนัสความเร็วสูงสุดอีก 500 ตามเวลาที่เหลือ ตอบผิดหรือหมดเวลาได้ 0 เปลี่ยนคำตอบไม่ได้</div>`;
    const cp = document.getElementById("rcCopy");
    cp.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(`${location.href.split("#")[0]}#/race/${code}`); cp.textContent = "คัดลอกแล้ว"; }
      catch { cp.textContent = `เลขห้อง ${code}`; }
    });
    const stBtn = document.getElementById("rcStart");
    if (stBtn) stBtn.addEventListener("click", () => {
      cl.publish(`${base}cfg`, JSON.stringify({ ...R.cfg, state: "run", at: Date.now() }), pubOpts);
    });
  }

  function question() {
    const p = R.items[R.i];
    const figs = Object.fromEntries((p.figures || []).map((f) => [f.id, f]));
    const isNum = p.format === "numeric";
    const n = R.items.length;
    R.qT0 = Date.now(); R.locked = false;
    body.innerHTML = `<div class="race-play"><div>
        <div class="qhead"><span>ข้อ ${R.i + 1} / ${n} · คะแนน ${R.score}</span><span class="timer" id="rcT"></span></div>
        <div class="bar"><i id="rcBar" style="width:100%"></i></div>
        <div class="qcard">
          <div class="stem">${md(p.stem_md, figs)}</div>
          ${isNum ? `<div class="numans"><label for="numIn">คำตอบ (ตัวเลข)</label>
            <input id="numIn" inputmode="decimal" autocomplete="off" placeholder="เช่น 12 หรือ 0.25">
            <button class="btn primary" id="numBtn">ส่งคำตอบ</button></div>`
          : `<div class="choices">${p.choices.map((ch, j) => `<button class="choice" data-j="${j}">
              <span class="letter">${LETTERS[j]}</span><span class="body">${mdi(ch, figs)}</span></button>`).join("")}</div>`}
          <p id="rcFb" role="status" class="race-fb"></p>
        </div></div>
      <aside><h3>อันดับสด</h3><div id="rcBoard">${board(false)}</div></aside></div>`;
    if (window.Scratch) Scratch.setKey(`race:${code}:${R.i}`);
    window.scrollTo(0, 0);

    const answer = (picked) => {
      if (R.locked) return;
      R.locked = true;
      clearInterval(R.tick);
      const ms = Math.min(Date.now() - R.qT0, R.cfg.per * 1000);
      let frac = 0;
      if (picked != null) frac = isNum ? (numRight(p, picked) ? 1 : 0) : p.scores ? p.scores[picked] : (picked === p.answer_index ? 1 : 0);
      const pts = frac > 0 ? Math.round(frac * (500 + 500 * (1 - ms / (R.cfg.per * 1000)))) : 0;
      R.score += pts; R.used += ms; if (frac === 1) R.right += 1;
      R.log.push({ picked, pts, frac });
      body.querySelectorAll(".choice").forEach((b) => {
        b.disabled = true;
        const j = +b.dataset.j;
        if (j === p.answer_index) b.classList.add("right"); else if (j === picked) b.classList.add("wrong");
      });
      const nb = document.getElementById("numBtn"); if (nb) { nb.disabled = true; document.getElementById("numIn").disabled = true; }
      const ans = isNum ? fmtNum(p.answer_numeric.value) : `ข้อ ${LETTERS[p.answer_index]}`;
      const fb = document.getElementById("rcFb");
      fb.className = `race-fb ${frac === 1 ? "good" : frac > 0 ? "mid" : "bad"}`;
      fb.textContent = picked == null ? `หมดเวลา คำตอบคือ ${ans}` : frac === 1 ? `ถูกต้อง +${pts}` : frac > 0 ? `ได้บางส่วน +${pts} (ดีที่สุดคือ ${ans})` : `ยังไม่ถูก คำตอบคือ ${ans}`;
      R.i += 1;
      if (R.i >= n) R.phase = "done";
      pubMe();
      R.nextTo = setTimeout(() => (R.phase === "done" ? finished() : question()), 1500);
    };
    body.querySelectorAll(".choice").forEach((b) => b.addEventListener("click", () => answer(+b.dataset.j)));
    if (isNum) {
      const inp = document.getElementById("numIn");
      const send = () => { const v = parseNum(inp.value); if (v == null) { document.getElementById("rcFb").textContent = "อ่านตัวเลขไม่ได้ เช่น 12, -3.5 หรือ 3/4"; return; } answer(v); };
      document.getElementById("numBtn").addEventListener("click", send);
      inp.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
    }
    clearInterval(R.tick);
    const tick = () => {
      const left = Math.max(0, R.cfg.per * 1000 - (Date.now() - R.qT0));
      const t = document.getElementById("rcT"), bar = document.getElementById("rcBar");
      if (!t) return clearInterval(R.tick);
      t.textContent = `เหลือ ${Math.ceil(left / 1000)} วินาที`;
      bar.style.width = `${left / (R.cfg.per * 10)}%`;
      if (left <= 0) answer(null);
    };
    R.tick = setInterval(tick, 200); tick();
  }

  function finished() {
    if (window.Scratch) Scratch.setKey("global", false);
    const all = ranked();
    const stillPlaying = all.filter((p) => !p.done).length;
    const myRank = all.findIndex((p) => p.pid === me.pid) + 1;
    body.innerHTML = `<div class="card" style="text-align:center">
        <p class="muted" style="margin:0" id="rcStill">${stillPlaying ? `ยังมีเพื่อนกำลังทำอยู่ ${stillPlaying} คน อันดับอาจเปลี่ยน` : "แข่งจบแล้ว"}</p>
        <div class="result-big" id="rcRank">อันดับ ${myRank} / ${all.length}</div>
        <p>${R.score} คะแนน · ถูก ${R.right} / ${R.items.length} · ใช้เวลา ${raceFmt(R.used)}</p>
        <div class="row" style="justify-content:center"><a class="btn primary" href="#/race">สร้างหรือเข้าห้องใหม่</a></div>
      </div>
      <div id="rcBoard">${board(true)}</div>
      <h3>เฉลยของคุณ</h3>
      ${R.items.map((p, k) => {
        const figs = Object.fromEntries((p.figures || []).map((f) => [f.id, f]));
        const g = R.log[k] || { picked: null, pts: 0, frac: 0 };
        const isNum = p.format === "numeric";
        const ans = isNum ? fmtNum(p.answer_numeric.value) : `${LETTERS[p.answer_index]}. ${p.choices[p.answer_index]}`;
        const mine = g.picked == null ? "ไม่ได้ตอบ" : isNum ? fmtNum(g.picked) : `${LETTERS[g.picked]}`;
        return `<details class="reveal race-rev"><summary><span class="badge ${g.frac === 1 ? "ok" : g.frac > 0 ? "acc" : "warn"}">${g.frac === 1 ? "ถูก" : g.frac > 0 ? "บางส่วน" : "ผิด"} +${g.pts}</span> ข้อ ${k + 1}</summary>
          <div class="stem">${md(p.stem_md, figs)}</div>
          <p><b>คุณตอบ:</b> ${esc(mine)} · <b>คำตอบ:</b> ${mdi(ans, figs)}</p>
          <div class="solution">${md(p.explanation_md, figs)}${stepsHTML(p.steps, figs)}</div></details>`;
      }).join("")}`;
  }

  async function onCfg(cfg) {
    const first = !R.cfg;
    R.cfg = cfg;
    if (first) {
      await catalog();
      const bank = await getJSON(`data/exam/${cfg.sid}.json`);
      const byId = Object.fromEntries(bank.items.map((p) => [p.id, p]));
      R.items = cfg.ids.map((id) => byId[id]).filter(Boolean);
      if (!R.items.length) { body.innerHTML = `<div class="card empty"><p><b>โหลดโจทย์ของห้องนี้ไม่ได้</b></p><p class="muted">ลองรีเฟรชหน้าเว็บให้เป็นรุ่นล่าสุดแล้วเข้าห้องใหม่</p></div>`; return raceLeave(); }
      R.joined = Date.now();
      pubMe();
    }
    if (RACE.cur !== R) return;
    if (cfg.state === "lobby" && R.phase === "wait") lobby();
    else if (cfg.state === "run" && R.phase === "wait") {
      R.phase = "play";
      let k = 3;
      const cd = () => {
        if (RACE.cur !== R) return;
        if (k === 0) return question();
        body.innerHTML = `<div class="card" style="text-align:center"><p class="muted">เริ่มใน</p><div class="result-big">${k}</div></div>`;
        k -= 1; R.nextTo = setTimeout(cd, 900);
      };
      cd();
    }
  }

  let gotCfg = false;
  cl.on("message", (topic, payload) => {
    if (RACE.cur !== R) return;
    let d = null;
    try { d = payload.length ? JSON.parse(payload.toString()) : null; } catch { return; }
    const key = topic.slice(base.length);
    if (key === "cfg") { if (d && d.v === 1 && Array.isArray(d.ids)) { gotCfg = true; onCfg(d); } return; }
    if (!key.startsWith("p/")) return;
    const pid = key.slice(2);
    if (!d) delete R.players[pid];
    else if (pid !== me.pid && typeof d.name === "string") {
      R.players[pid] = { name: d.name.slice(0, 16), joined: +d.joined || 0, i: +d.i || 0, score: +d.score || 0, right: +d.right || 0, used: +d.used || 0, done: !!d.done };
    }
    if (!R.cfg) return;
    // ห้องเต็ม: คนที่เข้าหลังสุดเกินจำนวนที่ตั้งไว้ต้องออก
    const order = Object.entries(R.players).sort((a, b) => a[1].joined - b[1].joined || (a[0] < b[0] ? -1 : 1)).map((x) => x[0]);
    if (R.phase === "wait" && order.indexOf(me.pid) >= R.cfg.max) {
      cl.publish(`${base}p/${me.pid}`, "", { qos: 1, retain: true });
      body.innerHTML = `<div class="card empty"><p><b>ห้องเต็มแล้ว</b></p><p class="muted">ห้องนี้รับได้ ${R.cfg.max} คน</p><a class="btn" href="#/race">กลับ</a></div>`;
      return setTimeout(raceLeave, 300);
    }
    if (R.phase === "wait" && R.cfg.state === "lobby") lobby();
    else {
      const b = document.getElementById("rcBoard"); if (b) b.innerHTML = board(R.phase === "done");
      const st = document.getElementById("rcStill");
      if (st) {
        const all = ranked(), left = all.filter((p) => !p.done).length;
        st.textContent = left ? `ยังมีเพื่อนกำลังทำอยู่ ${left} คน อันดับอาจเปลี่ยน` : "แข่งจบแล้ว";
        document.getElementById("rcRank").textContent = `อันดับ ${all.findIndex((p) => p.pid === me.pid) + 1} / ${all.length}`;
      }
    }
  });
  cl.on("connect", () => cl.subscribe(`${base}#`, { qos: 1 }));
  cl.subscribe(`${base}#`, { qos: 1 });
  setTimeout(() => {
    if (RACE.cur === R && !gotCfg) {
      body.innerHTML = `<div class="card empty"><p><b>ไม่พบห้อง ${code}</b></p><p class="muted">ตรวจเลขห้องอีกครั้ง หรือห้องอาจหมดอายุแล้ว</p><a class="btn primary" href="#/race">กลับ</a></div>`;
      raceLeave();
    }
  }, 6000);
}
