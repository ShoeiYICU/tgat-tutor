/* กระดาษทด: เขียนด้วยนิ้ว ปากกา (เช่น Apple Pencil) หรือเมาส์ ทับบนโจทย์หรือบนกระดาษเปล่า
 * ปากกา (รับแรงกด) · ปากกาเน้นข้อความ · ยางลบทั้งเส้น · ยางลบบางส่วน · สี · ขนาด · ย้อนกลับ/ทำซ้ำ · ล้าง
 * พื้นหลัง (โปร่งใส/กระดาษ/ตาราง/เส้นบรรทัด/จุด) · หลายหน้า · โหมดปากกาเท่านั้น (กันมือวางบนจอ)
 * ลายมือเก็บแยกตามข้อ (Scratch.setKey) ไว้ในเครื่องของผู้ใช้ */
(function () {
  "use strict";
  const LS = "tgat-tutor.scratch.v1";
  // "ink" คือสีตัวอักษรของธีม (ดำในโหมดสว่าง ขาวในโหมดมืด)
  const COLORS = ["ink", "#2563eb", "#dc2626", "#16a34a", "#ea580c", "#9333ea"];
  const inkOf = (c) => (c === "ink" ? (getComputedStyle(document.body).color || "#1f2937") : c);
  const SIZES = { pen: [1.6, 3, 5.5], hl: [14, 22, 32], erase: [10, 22, 40] };
  const MAX_KEYS = 40;

  const st = {
    open: false, key: "global", tool: "pen", color: COLORS[0], size: 1, bg: "clear", penOnly: false,
    pages: null, page: 0, undo: [], redo: [], cur: null, penAt: 0, peek: false,
  };
  let root, cv, ctx, bgcv, bgctx, dpr = 1;

  // ---------- เก็บข้อมูล
  function loadAll() { try { return JSON.parse(localStorage.getItem(LS)) || {}; } catch { return {}; } }
  function saveAll(all) { try { localStorage.setItem(LS, JSON.stringify(all)); } catch { /* เต็มหรือถูกปิด ไม่เป็นไร */ } }
  function loadPrefs() {
    const p = loadAll()._prefs || {};
    for (const k of ["tool", "color", "size", "bg", "penOnly"]) if (p[k] != null) st[k] = p[k];
  }
  function persist() {
    const all = loadAll();
    all._prefs = { tool: st.tool, color: st.color, size: st.size, bg: st.bg, penOnly: st.penOnly };
    const notes = all.notes || {};
    const used = st.pages && st.pages.some((p) => p.length);
    if (used) notes[st.key] = { at: Date.now(), pages: st.pages.map((p) => p.map(packStroke)) };
    else delete notes[st.key];
    const keys = Object.keys(notes).sort((a, b) => notes[b].at - notes[a].at);
    for (const k of keys.slice(MAX_KEYS)) delete notes[k];
    all.notes = notes;
    saveAll(all);
  }
  const r1 = (v) => Math.round(v * 10) / 10;
  function packStroke(s) { return { t: s.t, c: s.c, w: s.w, p: s.p.map((q) => [r1(q[0]), r1(q[1]), Math.round(q[2] * 100) / 100]) }; }
  function loadKey() {
    const n = (loadAll().notes || {})[st.key];
    st.pages = n ? n.pages : [[]];
    st.page = 0; st.undo = []; st.redo = [];
  }

  // ---------- วาด
  function widthAt(s, pr) { return s.t === "hl" ? s.w : s.w * (0.35 + 1.1 * pr); }
  function drawStroke(c, s) {
    const pts = s.p;
    if (!pts.length) return;
    c.save();
    c.lineCap = "round"; c.lineJoin = "round";
    c.strokeStyle = c.fillStyle = inkOf(s.c);
    if (s.t === "hl") { c.globalAlpha = 0.28; c.lineCap = "butt"; }
    if (pts.length === 1) {
      c.beginPath(); c.arc(pts[0][0], pts[0][1], widthAt(s, pts[0][2]) / 2, 0, Math.PI * 2); c.fill();
    } else if (s.t === "hl") {
      c.lineWidth = s.w;
      c.beginPath(); c.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length - 1; i++) {
        const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2;
        c.quadraticCurveTo(pts[i][0], pts[i][1], mx, my);
      }
      const L = pts[pts.length - 1]; c.lineTo(L[0], L[1]); c.stroke();
    } else {
      // เส้นปากกา: วาดทีละช่วงด้วยความหนาตามแรงกด ต่อด้วยเส้นโค้งผ่านจุดกึ่งกลาง
      let px = pts[0][0], py = pts[0][1];
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i];
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
        c.lineWidth = widthAt(s, (a[2] + b[2]) / 2);
        c.beginPath(); c.moveTo(px, py); c.quadraticCurveTo(a[0], a[1], mx, my); c.stroke();
        px = mx; py = my;
      }
      const L = pts[pts.length - 1];
      c.lineWidth = widthAt(s, L[2]); c.beginPath(); c.moveTo(px, py); c.lineTo(L[0], L[1]); c.stroke();
    }
    c.restore();
  }
  // เขียนทับโจทย์: เส้นผูกกับตำแหน่งบนหน้าเว็บ เลื่อนหน้าแล้วเส้นเลื่อนตาม · กระดาษแบบอื่นอยู่กับจอ
  function off() { return st.bg === "clear" ? (window.scrollY || 0) : 0; }
  function redraw() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.setTransform(dpr, 0, 0, dpr, 0, -off() * dpr);
    for (const s of st.pages[st.page]) drawStroke(ctx, s);
    if (st.cur && st.cur.t !== "erase" && st.cur.t !== "cut") drawStroke(ctx, st.cur);
    pageLabel();
  }
  function drawBg() {
    const w = bgcv.width / dpr, h = bgcv.height / dpr;
    bgctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    bgctx.clearRect(0, 0, w, h);
    root.classList.toggle("clear", st.bg === "clear");
    if (st.bg === "clear") return;
    bgctx.fillStyle = getComputedStyle(root).getPropertyValue("--sc-paper") || "#fff";
    bgctx.fillRect(0, 0, w, h);
    bgctx.strokeStyle = getComputedStyle(root).getPropertyValue("--sc-rule") || "#d7dde8";
    bgctx.fillStyle = bgctx.strokeStyle;
    bgctx.lineWidth = 1;
    const g = 28;
    if (st.bg === "grid") {
      bgctx.beginPath();
      for (let x = g; x < w; x += g) { bgctx.moveTo(x + 0.5, 0); bgctx.lineTo(x + 0.5, h); }
      for (let y = g; y < h; y += g) { bgctx.moveTo(0, y + 0.5); bgctx.lineTo(w, y + 0.5); }
      bgctx.stroke();
    } else if (st.bg === "lines") {
      bgctx.beginPath();
      for (let y = 2 * g; y < h; y += g) { bgctx.moveTo(0, y + 0.5); bgctx.lineTo(w, y + 0.5); }
      bgctx.stroke();
    } else if (st.bg === "dots") {
      for (let x = g; x < w; x += g) for (let y = g; y < h; y += g) { bgctx.beginPath(); bgctx.arc(x, y, 1.3, 0, 7); bgctx.fill(); }
    }
  }
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    for (const c of [cv, bgcv]) {
      c.width = Math.round(window.innerWidth * dpr); c.height = Math.round(window.innerHeight * dpr);
    }
    drawBg(); redraw();
  }

  // ---------- ยางลบ
  function hitStroke(s, x, y, r) {
    const pad = r + (s.t === "hl" ? s.w / 2 : s.w);
    for (let i = 0; i < s.p.length; i++) {
      const a = s.p[i], b = s.p[i + 1] || a;
      if (distSeg(x, y, a, b) <= pad) return true;
    }
    return false;
  }
  function distSeg(x, y, a, b) {
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const L = dx * dx + dy * dy;
    let t = L ? ((x - a[0]) * dx + (y - a[1]) * dy) / L : 0;
    t = Math.max(0, Math.min(1, t));
    const px = a[0] + t * dx - x, py = a[1] + t * dy - y;
    return Math.sqrt(px * px + py * py);
  }
  // ยางลบบางส่วน: ตัดจุดที่อยู่ในวงยางลบออก แล้วแยกเส้นที่เหลือเป็นหลายเส้น
  function cutStrokes(list, x, y, r) {
    const out = []; let changed = false;
    for (const s of list) {
      if (!hitStroke(s, x, y, r)) { out.push(s); continue; }
      changed = true;
      let part = [];
      for (const q of s.p) {
        if (Math.hypot(q[0] - x, q[1] - y) <= r) { if (part.length > 1) out.push({ ...s, p: part }); part = []; }
        else part.push(q);
      }
      if (part.length > 1) out.push({ ...s, p: part });
    }
    return changed ? out : null;
  }

  // ---------- การสัมผัส
  function pos(ev) {
    const r = cv.getBoundingClientRect();
    const pr = ev.pointerType === "pen" ? (ev.pressure || 0.5) : 0.5;
    return [ev.clientX - r.left, ev.clientY - r.top + off(), pr];
  }
  function down(ev) {
    if (!st.open) return;
    const now = Date.now();
    if (ev.pointerType === "pen") {
      st.penAt = now;
      // ฝ่ามือแตะจอก่อนปลายปากกา: ทิ้งเส้นจากฝ่ามือแล้วเริ่มเส้นปากกา
      if (st.cur && st.cur.touch) { if (st.cur.before) st.pages[st.page] = st.cur.before; st.cur = null; }
    } else if (ev.pointerType === "touch") {
      if (st.penOnly) return;                       // ผู้ใช้เลือกให้นิ้วไม่ขีดเส้น
      if (now - st.penAt < 600) return;             // เพิ่งใช้ปากกา: ถือว่าเป็นฝ่ามือ พอวางปากกาแล้วนิ้วเขียนได้ตามปกติ
    }
    if (st.cur) return;                             // มีเส้นที่กำลังเขียนอยู่แล้ว ไม่ให้นิ้วที่สองมาแทน
    if (ev.button > 0 && ev.pointerType === "mouse") return;
    ev.preventDefault();
    try { cv.setPointerCapture(ev.pointerId); } catch { /* บางเบราว์เซอร์ไม่ยอม ไม่เป็นไร */ }
    const [x, y, pr] = pos(ev);
    const eraserBtn = ev.pointerType === "pen" && (ev.buttons & 32);   // ปุ่มยางลบของปากกาบางรุ่น
    const tool = eraserBtn ? "erase" : st.tool;
    if (tool === "erase" || tool === "cut") {
      st.cur = { t: tool, before: st.pages[st.page].slice(), id: ev.pointerId, r: SIZES.erase[st.size] / 2, touch: ev.pointerType === "touch" };
      st.cur.last = [x, y];
      eraseAt(x, y);
    } else {
      st.cur = { t: tool, c: st.color, w: SIZES[tool][st.size], p: [[x, y, pr]], id: ev.pointerId, touch: ev.pointerType === "touch" };
      redraw();
    }
  }
  function eraseAt(x, y) {
    const page = st.pages[st.page];
    if (st.cur.t === "erase") {
      const keep = page.filter((s) => !hitStroke(s, x, y, st.cur.r));
      if (keep.length !== page.length) { st.pages[st.page] = keep; redraw(); }
    } else {
      const cut = cutStrokes(page, x, y, st.cur.r);
      if (cut) { st.pages[st.page] = cut; redraw(); }
    }
  }
  function move(ev) {
    if (ev.pointerType === "pen") st.penAt = Date.now();
    if (!st.cur || ev.pointerId !== st.cur.id) return;
    ev.preventDefault();
    const evs = ev.getCoalescedEvents ? ev.getCoalescedEvents() : [ev];
    for (const e of (evs.length ? evs : [ev])) {
      const [x, y, pr] = pos(e);
      if (st.cur.t === "erase" || st.cur.t === "cut") {
        const L = st.cur.last || [x, y], step = Math.max(2, st.cur.r / 2);
        const n = Math.ceil(Math.hypot(x - L[0], y - L[1]) / step);
        for (let i = 1; i <= n; i++) eraseAt(L[0] + (x - L[0]) * i / n, L[1] + (y - L[1]) * i / n);
        st.cur.last = [x, y];
      }
      else {
        const L = st.cur.p[st.cur.p.length - 1];
        if (Math.hypot(x - L[0], y - L[1]) >= 0.8) st.cur.p.push([x, y, pr]);
      }
    }
    if (st.cur.t !== "erase" && st.cur.t !== "cut") redraw();
  }
  function up(ev) {
    if (!st.cur || ev.pointerId !== st.cur.id) return;
    const c = st.cur; st.cur = null;
    if (c.t === "erase" || c.t === "cut") {
      if (c.before.length !== st.pages[st.page].length || c.before.some((s, i) => s !== st.pages[st.page][i])) {
        st.undo.push({ page: st.page, before: c.before, after: st.pages[st.page].slice() }); st.redo = [];
      }
    } else {
      delete c.id; delete c.touch;
      const before = st.pages[st.page].slice();
      st.pages[st.page].push(c);
      st.undo.push({ page: st.page, before, after: st.pages[st.page].slice() }); st.redo = [];
    }
    redraw(); persist(); tools();
  }

  // ---------- คำสั่ง
  function undo() {
    const a = st.undo.pop(); if (!a) return;
    st.pages[a.page] = a.before.slice(); st.page = a.page; st.redo.push(a); redraw(); persist(); tools();
  }
  function redo() {
    const a = st.redo.pop(); if (!a) return;
    st.pages[a.page] = a.after.slice(); st.page = a.page; st.undo.push(a); redraw(); persist(); tools();
  }
  function clearPage() {
    if (!st.pages[st.page].length) return;
    st.undo.push({ page: st.page, before: st.pages[st.page].slice(), after: [] }); st.redo = [];
    st.pages[st.page] = []; redraw(); persist(); tools();
  }
  function goPage(d) {
    const n = st.page + d;
    if (n < 0) return;
    if (n >= st.pages.length) { if (!st.pages[st.page].length) return; st.pages.push([]); }
    st.page = n; redraw(); tools();
  }
  function pageLabel() { const el = root && root.querySelector(".sc-page"); if (el) el.textContent = `${st.page + 1}/${st.pages.length}`; }

  // ---------- หน้าตา
  function icon(name, label, extra = "") { return `<button type="button" class="sc-b ${extra}" data-a="${name}" aria-label="${label}" title="${label}">${ICONS[name] || label}</button>`; }
  const ICONS = {
    pen: "✒︎", hl: "▮", erase: "⌫", cut: "✂︎", undo: "↶", redo: "↷", clear: "🗑", close: "✕",
    prev: "‹", next: "›",
  };
  function tools() {
    if (!root) return;
    root.querySelectorAll("[data-a]").forEach((b) => {
      const a = b.dataset.a;
      b.classList.toggle("on", a === st.tool);
      if (a === "undo") b.disabled = !st.undo.length;
      if (a === "redo") b.disabled = !st.redo.length;
    });
    root.querySelectorAll("[data-c]").forEach((b) => b.classList.toggle("on", b.dataset.c === st.color));
    root.querySelectorAll("[data-s]").forEach((b) => b.classList.toggle("on", +b.dataset.s === st.size));
    const bg = root.querySelector(".sc-bg"); if (bg) bg.value = st.bg;
    const po = root.querySelector(".sc-penonly"); if (po) po.checked = st.penOnly;
    pageLabel();
    if (fab) fab.classList.toggle("has", hasNotes(st.key));
  }
  function build() {
    root = document.createElement("div");
    root.className = "scratch";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-label", "กระดาษทด");
    root.innerHTML = `
      <canvas class="sc-bgc"></canvas><canvas class="sc-ink"></canvas>
      <div class="sc-bar" role="toolbar" aria-label="เครื่องมือกระดาษทด">
        <div class="sc-grp">${icon("pen", "ปากกา")}${icon("hl", "ปากกาเน้นข้อความ")}${icon("erase", "ยางลบทั้งเส้น")}${icon("cut", "ยางลบบางส่วน")}</div>
        <div class="sc-grp">${COLORS.map((c) => `<button type="button" class="sc-c" data-c="${c}" style="--c:${c === "ink" ? "var(--text)" : c}" aria-label="สี ${c === "ink" ? "หมึกปกติ" : c}"></button>`).join("")}</div>
        <div class="sc-grp">${[0, 1, 2].map((i) => `<button type="button" class="sc-s" data-s="${i}" aria-label="ขนาด ${["เล็ก", "กลาง", "ใหญ่"][i]}"><i style="--d:${4 + i * 4}px"></i></button>`).join("")}</div>
        <div class="sc-grp">${icon("undo", "ย้อนกลับ")}${icon("redo", "ทำซ้ำ")}${icon("clear", "ล้างหน้านี้")}</div>
        <div class="sc-grp">${icon("prev", "หน้าก่อน")}<span class="sc-page"></span>${icon("next", "หน้าถัดไป หรือเพิ่มหน้า")}</div>
        <div class="sc-grp">
          <select class="sc-bg" aria-label="พื้นหลัง">
            <option value="clear">เขียนทับโจทย์</option><option value="plain">กระดาษเปล่า</option>
            <option value="grid">ตาราง</option><option value="lines">เส้นบรรทัด</option><option value="dots">จุด</option>
          </select>
          <label class="sc-po" title="เปิดไว้: เขียนได้เฉพาะปากกา นิ้วจะไม่ขีดเส้น · ปิดไว้: เขียนได้ทั้งนิ้วและปากกา"><input type="checkbox" class="sc-penonly"> ปิดการเขียนด้วยนิ้ว</label>
        </div>
        ${icon("close", "ปิดกระดาษทด", "sc-close")}
      </div>`;
    document.body.appendChild(root);
    bgcv = root.querySelector(".sc-bgc"); cv = root.querySelector(".sc-ink");
    bgctx = bgcv.getContext("2d"); ctx = cv.getContext("2d");
    cv.addEventListener("pointerdown", down);
    cv.addEventListener("pointermove", move);
    cv.addEventListener("pointerup", up);
    cv.addEventListener("pointercancel", up);
    cv.addEventListener("contextmenu", (e) => e.preventDefault());
    root.querySelector(".sc-bar").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      if (b.dataset.c) { st.color = b.dataset.c; if (st.tool !== "hl") st.tool = "pen"; }
      else if (b.dataset.s != null) st.size = +b.dataset.s;
      else {
        const a = b.dataset.a;
        if (["pen", "hl", "erase", "cut"].includes(a)) st.tool = a;
        else if (a === "undo") undo(); else if (a === "redo") redo(); else if (a === "clear") clearPage();
        else if (a === "prev") goPage(-1); else if (a === "next") goPage(1);
        else if (a === "close") close();
      }
      tools(); persist();
    });
    root.querySelector(".sc-bg").addEventListener("change", (e) => { st.bg = e.target.value; drawBg(); redraw(); persist(); });
    root.querySelector(".sc-penonly").addEventListener("change", (e) => { st.penOnly = e.target.checked; persist(); });
    window.addEventListener("resize", () => { if (st.open || st.peek) resize(); });
    let ticking = false;
    window.addEventListener("scroll", () => {
      if (!st.peek || ticking) return;
      ticking = true;
      requestAnimationFrame(() => { ticking = false; if (st.peek) redraw(); });
    }, { passive: true });
    document.addEventListener("keydown", (e) => {
      if (!st.open) return;
      const k = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && k === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); }
      else if ((e.ctrlKey || e.metaKey) && k === "y") { e.preventDefault(); redo(); }
      else if (k === "escape") close();
    });
  }

  /* ปิดโหมดเขียนแล้วลายมือที่เขียนทับโจทย์ยังแสดงอยู่ (แตะทะลุได้ เลื่อนหน้าได้) */
  function setPeek() {
    const want = !st.open && st.key !== "global" && st.bg === "clear" && hasNotes(st.key);
    if (want && !root) build();
    if (!root) return;
    st.peek = want;
    root.classList.toggle("peek", want);
    if (want) { if (!st.pages || st.peekKey !== st.key) { loadKey(); st.peekKey = st.key; } st.page = 0; resize(); }
  }
  function open() {
    if (!root) build();
    loadKey(); st.peekKey = st.key;
    st.peek = false; root.classList.remove("peek");
    st.open = true;
    root.classList.add("open");
    document.documentElement.classList.add("scratch-open");
    resize(); tools();
  }
  function close() {
    if (!root) return;
    persist();
    st.open = false;
    root.classList.remove("open");
    document.documentElement.classList.remove("scratch-open");
    st.cur = null;
    tools(); setPeek();
  }
  function hasNotes(key) {
    const n = (loadAll().notes || {})[key];
    return !!(n && n.pages.some((p) => p.length));
  }

  // ปุ่มลอยเปิดกระดาษทด
  let fab = null;
  function ensureFab() {
    if (fab) return;
    fab = document.createElement("button");
    fab.type = "button"; fab.className = "sc-fab";
    fab.setAttribute("aria-label", "เปิดกระดาษทด");
    fab.innerHTML = `<span aria-hidden="true">✎</span><span class="sc-fab-t">กระดาษทด</span>`;
    fab.addEventListener("click", () => (st.open ? close() : open()));
    document.body.appendChild(fab);
  }

  window.Scratch = {
    /** แอปเรียกทุกครั้งที่เปลี่ยนข้อ ลายมือจะผูกกับข้อนั้น · show=false ซ่อนปุ่ม */
    setKey(key, show = true) {
      ensureFab();
      if (st.open && key !== st.key) { persist(); st.key = key || "global"; loadKey(); redraw(); tools(); }
      else st.key = key || "global";
      fab.hidden = !show;
      tools();
      if (!st.open) setPeek();
    },
    open, close,
  };
  loadPrefs();
})();
