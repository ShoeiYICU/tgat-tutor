/* พับแผ่นคลี่ลูกบาศก์แบบ 3 มิติ
 * อ่านแผ่นคลี่จากรูป SVG ของโจทย์ (ช่องสี่เหลี่ยมจัตุรัส 6 ช่อง) แล้วพับด้วย CSS 3D ไม่ใช้ไลบรารี
 * แต่ละหน้าคือ SVG เดิมที่ตัด viewBox ให้เหลือช่องเดียว ตัวอักษรและลูกศรบนหน้าจึงตรงกับโจทย์ทุกอย่าง
 * ใช้: Fold3D.mount(ช่องที่จะวาง, ข้อความ svg) คืน true ถ้าเป็นแผ่นคลี่ลูกบาศก์ที่พับได้ */
(function () {
  "use strict";

  function parseNet(svgText) {
    let doc;
    try { doc = new DOMParser().parseFromString(svgText, "image/svg+xml"); } catch { return null; }
    const svg = doc.documentElement;
    if (!svg || svg.nodeName.toLowerCase() !== "svg") return null;
    const rects = [...svg.querySelectorAll("rect")].map((r) => ({
      x: +r.getAttribute("x") || 0, y: +r.getAttribute("y") || 0,
      w: +r.getAttribute("width") || 0, h: +r.getAttribute("height") || 0,
    })).filter((r) => r.w > 8 && Math.abs(r.w - r.h) < 0.5);
    if (rects.length < 6) return null;
    // ช่องของแผ่นคลี่คือสี่เหลี่ยมจัตุรัสขนาดที่พบบ่อยที่สุด
    const count = {};
    for (const r of rects) count[r.w] = (count[r.w] || 0) + 1;
    const size = +Object.keys(count).sort((a, b) => count[b] - count[a])[0];
    const seen = new Set();
    const cells = rects.filter((r) => r.w === size && !seen.has(`${r.x},${r.y}`) && seen.add(`${r.x},${r.y}`));
    if (cells.length !== 6) return null;
    const x0 = Math.min(...cells.map((c) => c.x)), y0 = Math.min(...cells.map((c) => c.y));
    for (const c of cells) {
      c.col = Math.round((c.x - x0) / size); c.row = Math.round((c.y - y0) / size);
      if (Math.abs(c.x - x0 - c.col * size) > 1 || Math.abs(c.y - y0 - c.row * size) > 1) return null;
    }
    const at = (r, c) => cells.find((k) => k.row === r && k.col === c);
    const DIRS = [["R", 0, 1], ["L", 0, -1], ["D", 1, 0], ["U", -1, 0]];
    const deg = (k) => DIRS.filter(([, dr, dc]) => at(k.row + dr, k.col + dc)).length;
    // หน้าฐาน = ช่องที่มีเพื่อนบ้านมากที่สุด ทำให้ต้นไม้การพับตื้นที่สุด
    const base = cells.reduce((a, b) => (deg(b) > deg(a) ? b : a));
    base.dir = null;
    const order = [base], done = new Set([base]);
    for (let i = 0; i < order.length; i++) {
      const p = order[i];
      p.kids = [];
      for (const [d, dr, dc] of DIRS) {
        const k = at(p.row + dr, p.col + dc);
        if (k && !done.has(k)) { done.add(k); k.dir = d; p.kids.push(k); order.push(k); }
      }
    }
    if (order.length !== 6) return null;
    // ตรวจว่าพับแล้วเป็นลูกบาศก์จริง: หน้าทั้งหกต้องหันออกคนละทิศ
    const normals = new Set();
    (function walk(k, M) {
      normals.add([M[0][2], M[1][2], M[2][2]].map((v) => Math.round(v)).join(","));
      for (const c of k.kids) walk(c, mul(M, ROT[c.dir]));
    })(base, [[1, 0, 0], [0, 1, 0], [0, 0, 1]]);
    if (normals.size !== 6) return null;
    return { size, cells, base, svg };
  }

  // เมทริกซ์ของการพับ 90° ตามที่ CSS ทำจริง (แกน x ขวา y ลง z ออกหาผู้ดู) ใช้ตรวจว่าพับได้ลูกบาศก์
  // R = rotateY(90) · L = rotateY(-90) · D = rotateX(-90) · U = rotateX(90)
  const ROT = {
    R: [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
    L: [[0, 0, -1], [0, 1, 0], [1, 0, 0]],
    D: [[1, 0, 0], [0, 0, 1], [0, -1, 0]],
    U: [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
  };
  const mul = (A, B) => A.map((r) => B[0].map((_, j) => r.reduce((s, v, k) => s + v * B[k][j], 0)));

  const ORIGIN = { R: "0 50%", L: "100% 50%", D: "50% 0", U: "50% 100%" };
  const OFFSET = { R: [1, 0], L: [-1, 0], D: [0, 1], U: [0, -1] };
  function hinge(d, deg) {
    return d === "R" ? `rotateY(${deg}deg)` : d === "L" ? `rotateY(${-deg}deg)`
      : d === "D" ? `rotateX(${-deg}deg)` : `rotateX(${deg}deg)`;
  }

  function mount(slot, svgText) {
    const net = parseNet(svgText);
    if (!net) return false;
    const F = Math.max(56, Math.min(110, Math.floor((slot.clientWidth || 320) / 4.6)));
    const cols = Math.max(...net.cells.map((c) => c.col)) + 1;
    const rows = Math.max(...net.cells.map((c) => c.row)) + 1;
    const H = Math.round(Math.max(rows, 3.4) * F + 30);
    slot.innerHTML = `
      <div class="f3-stage" style="height:${H}px" aria-label="ภาพสามมิติของการพับแผ่นคลี่ ลากเพื่อหมุนดู">
        <div class="f3-world"></div>
      </div>
      <div class="f3-ctrl">
        <button type="button" class="btn f3-play">▶ พับ</button>
        <input type="range" class="f3-range" min="0" max="100" value="0" aria-label="ระดับการพับ">
        <button type="button" class="btn f3-reset">มุมเดิม</button>
      </div>
      <p class="muted f3-note">ลากที่ภาพเพื่อหมุนดูรอบลูกบาศก์ · หน้าที่ติดกับหน้าฐานพับเข้าหาด้านหลัง</p>`;
    const stage = slot.querySelector(".f3-stage"), world = slot.querySelector(".f3-world");
    const range = slot.querySelector(".f3-range"), play = slot.querySelector(".f3-play");

    const faces = new Map();
    function makeFace(cell) {
      const el = document.createElement("div");
      el.className = "f3-face" + (cell === net.base ? " base" : "");
      el.style.width = el.style.height = F + "px";
      const s = document.importNode(net.svg, true);
      s.setAttribute("viewBox", `${cell.x} ${cell.y} ${net.size} ${net.size}`);
      s.setAttribute("width", "100%"); s.setAttribute("height", "100%");
      s.setAttribute("preserveAspectRatio", "none");
      s.removeAttribute("role");
      el.appendChild(s);
      if (cell.dir) {
        const [ox, oy] = OFFSET[cell.dir];
        el.style.left = ox * F + "px"; el.style.top = oy * F + "px";
        el.style.transformOrigin = ORIGIN[cell.dir];
      }
      faces.set(cell, el);
      for (const k of cell.kids) el.appendChild(makeFace(k));
      return el;
    }
    world.appendChild(makeFace(net.base));

    // จุดศูนย์กลาง: ตอนแบนใช้กลางแผ่นคลี่ ตอนพับเสร็จใช้กลางลูกบาศก์
    const netCx = (cols / 2 - net.base.col) * F, netCy = (rows / 2 - net.base.row) * F;
    let t = 0, rx = -22, ry = 28, anim = null;

    function draw() {
      const e = t * t * (3 - 2 * t);
      for (const [cell, el] of faces) if (cell.dir) el.style.transform = hinge(cell.dir, 90 * e);
      const cx = netCx + (F / 2 - netCx) * e, cy = netCy + (F / 2 - netCy) * e, cz = -F / 2 * e;
      world.style.transformOrigin = `${cx}px ${cy}px ${cz}px`;
      world.style.left = `calc(50% - ${cx}px)`; world.style.top = `calc(50% - ${cy}px)`;
      world.style.transform = `rotateX(${rx * e + (-8) * (1 - e)}deg) rotateY(${ry * e}deg)`;
      range.value = Math.round(t * 100);
      play.textContent = t >= 1 ? "↺ คลี่กลับ" : "▶ พับ";
    }
    function go(to) {
      cancelAnimationFrame(anim);
      const from = t, t0 = performance.now(), dur = 1600 * Math.abs(to - from) + 1;
      (function step(now) {
        const k = Math.min(1, (now - t0) / dur);
        t = from + (to - from) * k;
        draw();
        if (k < 1) anim = requestAnimationFrame(step);
      })(t0);
    }
    play.addEventListener("click", () => go(t >= 1 ? 0 : 1));
    range.addEventListener("input", () => { cancelAnimationFrame(anim); t = range.value / 100; draw(); });
    slot.querySelector(".f3-reset").addEventListener("click", () => { rx = -22; ry = 28; draw(); });

    // ลากเพื่อหมุนมุมมอง ใช้ได้ทั้งเมาส์ นิ้ว และปากกา
    let drag = null;
    stage.addEventListener("pointerdown", (ev) => {
      drag = { x: ev.clientX, y: ev.clientY, rx, ry };
      try { stage.setPointerCapture(ev.pointerId); } catch { /* ไม่เป็นไร */ }
      if (t < 1) go(1);
    });
    stage.addEventListener("pointermove", (ev) => {
      if (!drag) return;
      ry = drag.ry + (ev.clientX - drag.x) * 0.6;
      rx = Math.max(-85, Math.min(85, drag.rx - (ev.clientY - drag.y) * 0.6));
      draw();
    });
    const end = () => { drag = null; };
    stage.addEventListener("pointerup", end);
    stage.addEventListener("pointercancel", end);
    draw();
    return true;
  }

  window.Fold3D = { mount, parseNet };
})();
