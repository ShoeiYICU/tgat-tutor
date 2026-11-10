/* ค้นหาหัวข้อ บทเรียน โจทย์ และคำศัพท์ (ดัชนีสร้างตอน build ที่ data/search.json โหลดเมื่อเปิดหน้าค้นหาครั้งแรก)
 * ใช้ตัวแปรกลางจาก app.js: $app, esc, catalog, getJSON · ไฟล์นี้โหลดก่อน app.js */
"use strict";

const SEARCH_LIMIT = 8;
let SEARCH_IDX = null;

function normTH(s) { return String(s || "").toLowerCase().normalize("NFC"); }

function snippet(text, terms, len = 110) {
  const low = normTH(text);
  const at = Math.max(0, Math.min(...terms.map((t) => { const i = low.indexOf(t); return i < 0 ? Infinity : i; })));
  const from = Math.max(0, at - 35);
  let out = esc(text.slice(from, from + len));
  for (const t of terms) {
    if (!t) continue;
    const re = new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    out = out.replace(re, (m) => `<mark>${m}</mark>`);
  }
  return (from > 0 ? "…" : "") + out + (from + len < text.length ? "…" : "");
}

async function pageSearch(q0) {
  const c = await catalog();
  const q = decodeURIComponent(q0 || "");
  $app.innerHTML = `<h1>ค้นหา</h1>
    <div class="search-box"><input id="sq" type="search" value="${esc(q)}" placeholder="เช่น เซต · ร้อยละ · พับกล่อง · conditional · ประโยคสุภาพ"
      aria-label="คำค้นหา" autocomplete="off" enterkeyhint="search"></div>
    <div id="sres" aria-live="polite"><p class="muted">กำลังโหลดดัชนี…</p></div>`;
  const input = document.getElementById("sq");
  input.focus();
  try { SEARCH_IDX ||= await getJSON("data/search.json"); }
  catch { document.getElementById("sres").innerHTML = `<p class="muted">โหลดดัชนีค้นหาไม่สำเร็จ ลองใหม่อีกครั้งเมื่อมีอินเทอร์เน็ต</p>`; return; }
  const subjOf = (id) => (SUBJECT_INFO[id.split(".")[0]] || {}).short || "";
  const topicName = (id) => (c.byId[id] || {}).name_th || id;
  const pathOf = (id) => {
    const out = [];
    let t = c.byId[id];
    while (t && t.parent && c.byId[t.parent] && c.byId[t.parent].kind !== "subject") { t = c.byId[t.parent]; out.unshift(t.name_th); }
    return out.join(" › ");
  };
  const expanded = {};

  function run() {
    const raw = input.value.trim();
    history.replaceState(null, "", `#/search/${encodeURIComponent(raw)}`);
    const box = document.getElementById("sres");
    const terms = normTH(raw).split(/\s+/).filter(Boolean);
    if (!terms.length) { box.innerHTML = `<p class="muted">พิมพ์คำที่อยากหา ค้นได้ทั้งชื่อหัวข้อ เนื้อหาในบทเรียน ต้นโจทย์ และคำศัพท์ภาษาอังกฤษ</p>`; return; }
    const hit = (s) => { const n = normTH(s); return terms.every((t) => n.includes(t)); };
    const I = SEARCH_IDX;

    const topics = I.topics.filter((t) => hit(`${t.n} ${t.x} ${subjOf(t.id)}`))
      .sort((a, b) => (b.r - a.r) || (hit(b.n) - hit(a.n)) || (a.k === "leaf") - (b.k === "leaf"));
    const lessons = I.lessons.filter((l) => hit(l.t) && !topics.some((t) => t.id === l.id && t.k === "leaf"));
    const probs = I.problems.filter((p) => hit(p.t));
    const vocab = I.vocab.filter((v) => hit(`${v.w} ${v.th}`));

    const group = (key, title, list, row) => {
      if (!list.length) return "";
      const n = expanded[key] ? list.length : Math.min(SEARCH_LIMIT, list.length);
      return `<section class="sgroup"><h2>${title} <span class="badge">${list.length}</span></h2>
        ${list.slice(0, n).map(row).join("")}
        ${list.length > n ? `<button class="btn more" data-k="${key}">แสดงอีก ${list.length - n} รายการ</button>` : ""}</section>`;
    };
    const topicHref = (t) => t.k === "leaf" ? `#/t/${t.id}` : (c.byId[t.id] && (c.subjects.find((s) => s.id === t.s).children[t.id] || []).some((x) => x.kind === "leaf" && x.problems))
      ? `#/c/${t.id}` : `#/s/${t.s}`;
    const html =
      group("t", "หัวข้อ", topics, (t) => `<a class="leaf${t.r || t.k !== "leaf" ? "" : " soon"}" href="${topicHref(t)}">
        <span class="t">${snippet(t.n, terms, 90)}</span><span class="badges"><span class="badge">${subjOf(t.id)}</span>
        ${t.k !== "leaf" ? `<span class="badge acc">ทั้งบท</span>` : t.r ? "" : `<span class="badge">กำลังเตรียม</span>`}</span>
        <small class="muted spath">${esc(pathOf(t.id))}</small></a>`) +
      group("l", "ในบทเรียน", lessons, (l) => `<a class="leaf" href="#/t/${l.id}/learn"><span class="t">${esc(topicName(l.id))}</span>
        <span class="badges"><span class="badge">${subjOf(l.id)}</span></span><small class="muted spath">${snippet(l.t, terms)}</small></a>`) +
      group("p", "โจทย์", probs, (p) => {
        const tid = (/^prob\.(.+)\.\d+$/.exec(p.id) || [])[1] || "";
        return `<a class="leaf" href="#/t/${tid}/practice"><span class="t">${snippet(p.t, terms, 120)}</span>
          <span class="badges"><span class="badge">${subjOf(tid)}</span></span><small class="muted spath">${esc(topicName(tid))}</small></a>`;
      }) +
      group("v", "คำศัพท์", vocab, (v) => `<a class="leaf" href="#/vocab/${v.d}"><span class="t"><b>${esc(v.w)}</b> · ${esc(v.th)}</span>
        <span class="badges"><span class="badge">TGAT1</span></span></a>`);
    box.innerHTML = html || `<p class="muted">ไม่พบ “${esc(raw)}” ลองใช้คำที่สั้นลง หรือค้นเป็นภาษาอังกฤษ</p>`;
    box.querySelectorAll(".more").forEach((b) => b.addEventListener("click", () => { expanded[b.dataset.k] = true; run(); }));
  }
  let tm = null;
  input.addEventListener("input", () => { clearTimeout(tm); tm = setTimeout(run, 160); });
  run();
}
