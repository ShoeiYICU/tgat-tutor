/* ใช้แบบไม่มีเน็ต: ลงทะเบียน service worker · แถบแจ้งเมื่อออฟไลน์ · หน้าดาวน์โหลดเนื้อหาทั้งหมด
 * ใช้ตัวแปรกลางจาก app.js: $app, esc, catalog, SUBJECT_INFO, KATEX · ไฟล์นี้โหลดก่อน app.js */
"use strict";

const OFFLINE_OK_KEY = "tgat-tutor.offline";

if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
  addEventListener("load", () => { navigator.serviceWorker.register("sw.js").catch(() => { /* เบราว์เซอร์ไม่รองรับ ใช้ออนไลน์ตามปกติ */ }); });
}

/* แถบเล็กด้านบนเมื่อไม่มีเน็ต */
function offlineBanner() {
  let bar = document.getElementById("offlineBar");
  if (navigator.onLine) { if (bar) bar.remove(); return; }
  if (bar) return;
  bar = document.createElement("div");
  bar.id = "offlineBar";
  bar.className = "offline-bar";
  bar.innerHTML = `ตอนนี้ไม่มีอินเทอร์เน็ต ใช้ได้เฉพาะเนื้อหาที่เคยเปิดหรือดาวน์โหลดไว้ · <a href="#/offline">ดูรายละเอียด</a>`;
  document.body.prepend(bar);
}
addEventListener("online", offlineBanner);
addEventListener("offline", offlineBanner);
addEventListener("load", offlineBanner);

async function offlineFileList() {
  const c = await catalog();
  const urls = ["./", "index.html", "data/catalog.json", "data/search.json", "data/vocab/tgat1.json",
    `${KATEX}.css`, `${KATEX}.js`, "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js",
    // ฟอนต์ของสูตรคณิตที่ใช้บ่อย (ตัวแสดงสูตรโหลดเองเมื่อมีสูตร ต้องเก็บไว้ก่อนจึงแสดงสูตรได้ตอนไม่มีเน็ต)
    ...["Main-Regular", "Main-Bold", "Main-Italic", "Math-Italic", "AMS-Regular", "Size1-Regular", "Size2-Regular",
      "Size3-Regular", "Size4-Regular"].map((f) => KATEX.replace(/katex\.min$/, `fonts/KaTeX_${f}.woff2`))];
  // ไฟล์โปรแกรมตามที่หน้าเว็บโหลดอยู่จริง (มีเลขรุ่นใน URL)
  document.querySelectorAll("script[src], link[rel=stylesheet]").forEach((el) => {
    const u = el.getAttribute("src") || el.getAttribute("href");
    if (u && !/^https?:/.test(u)) urls.push(u);
  });
  for (const s of c.subjects) {
    urls.push(`data/exam/${s.id}.json`);
    for (const t of s.topics) {
      if (t.lesson) urls.push(`data/lessons/${t.id}.json`);
      if (t.problems) urls.push(`data/problems/${t.id}.json`);
    }
  }
  return [...new Set(urls)];
}

async function pageOffline() {
  const sw = "serviceWorker" in navigator;
  let info = {};
  try { info = JSON.parse(localStorage.getItem(OFFLINE_OK_KEY)) || {}; } catch { /* */ }
  let est = "";
  try {
    const e = await navigator.storage.estimate();
    if (e && e.usage) est = `เว็บนี้ใช้พื้นที่ในเครื่องประมาณ ${(e.usage / 1048576).toFixed(1)} MB`;
  } catch { /* */ }
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  $app.innerHTML = `<h1>ใช้แบบไม่มีเน็ต</h1>
    <p class="lead">หน้าที่เคยเปิดแล้วจะเปิดได้อีกแม้ไม่มีอินเทอร์เน็ต ถ้าจะใช้ได้ครบทุกวิชา ให้ดาวน์โหลดเนื้อหาทั้งหมดเก็บไว้ในเครื่องก่อน</p>
    <div class="card">
      ${sw ? `<p><b>ดาวน์โหลดเนื้อหาทั้งหมด</b> บทเรียน โจทย์ เฉลย คำศัพท์ และตัวแสดงสูตรคณิต รวมราว 15–20 MB</p>
        <div class="row"><button class="btn primary" id="dlAll">${info.at ? "ดาวน์โหลดใหม่ให้เป็นฉบับล่าสุด" : "ดาวน์โหลดทั้งหมด"}</button></div>
        <div class="bar" id="dlBar" hidden><i style="width:0%"></i></div>
        <p class="muted small" id="dlMsg">${info.at ? `ดาวน์โหลดครบล่าสุดเมื่อ ${new Date(info.at).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" })}` : "ยังไม่ได้ดาวน์โหลด"}${est ? ` · ${est}` : ""}</p>`
      : `<p>เบราว์เซอร์นี้ไม่รองรับการเก็บเว็บไว้ใช้แบบไม่มีเน็ต ลองเปิดด้วย Safari หรือ Chrome รุ่นใหม่</p>`}
    </div>
    <h2>ติดตั้งเป็นแอปบนหน้าจอ</h2>
    <div class="card">
      ${isIOS ? `<ol><li>เปิดเว็บนี้ด้วย Safari</li><li>แตะปุ่มแชร์ (สี่เหลี่ยมมีลูกศรชี้ขึ้น)</li><li>เลือก "เพิ่มไปยังหน้าจอโฮม"</li></ol>`
        : `<p>ใน Chrome บนมือถือ แตะเมนู ⋮ แล้วเลือก "ติดตั้งแอป" หรือ "เพิ่มลงในหน้าจอหลัก" · บนคอมพิวเตอร์ กดไอคอนติดตั้งที่ปลายช่องที่อยู่เว็บ</p>`}
      <p class="muted small">เปิดจากไอคอนบนหน้าจอแล้วจะเต็มจอเหมือนแอป ความคืบหน้าและลายมือในกระดาษทดยังเก็บในเครื่องเหมือนเดิม</p>
    </div>
    <p class="muted small">ข้อมูลความคืบหน้าทั้งหมดเก็บในเบราว์เซอร์ของเครื่องนี้ ถ้าลบข้อมูลเว็บหรือเปลี่ยนเครื่อง ข้อมูลจะหาย</p>`;
  const btn = document.getElementById("dlAll");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const reg = await navigator.serviceWorker.ready.catch(() => null);
    if (!reg || !reg.active) { document.getElementById("dlMsg").textContent = "ยังเตรียมระบบไม่เสร็จ ลองรีเฟรชหน้าแล้วกดใหม่"; return; }
    btn.disabled = true;
    const urls = (await offlineFileList()).map((u) => new URL(u, location.href).href);
    const bar = document.getElementById("dlBar"); bar.hidden = false;
    const msg = document.getElementById("dlMsg");
    msg.textContent = `กำลังดาวน์โหลด 0 / ${urls.length} ไฟล์`;
    const onMsg = (ev) => {
      const d = ev.data || {};
      if (d.type !== "download-progress") return;
      bar.firstElementChild.style.width = `${Math.round(d.done / d.total * 100)}%`;
      msg.textContent = `กำลังดาวน์โหลด ${d.done} / ${d.total} ไฟล์${d.failed ? ` · ไม่สำเร็จ ${d.failed}` : ""}`;
      if (d.done === d.total) {
        navigator.serviceWorker.removeEventListener("message", onMsg);
        btn.disabled = false;
        if (!d.failed) {
          try { localStorage.setItem(OFFLINE_OK_KEY, JSON.stringify({ at: Date.now(), n: d.total })); } catch { /* */ }
          msg.textContent = `เสร็จแล้ว ${d.total} ไฟล์ ใช้ได้ทุกวิชาแม้ไม่มีอินเทอร์เน็ต`;
        } else msg.textContent = `ดาวน์โหลดไม่สำเร็จ ${d.failed} ไฟล์ ลองกดใหม่เมื่อเน็ตเสถียร`;
      }
    };
    navigator.serviceWorker.addEventListener("message", onMsg);
    reg.active.postMessage({ type: "download-all", urls });
  });
}
