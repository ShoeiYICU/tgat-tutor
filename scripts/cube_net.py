"""cube_net.py — คำนวณคู่หน้าตรงข้ามของลูกบาศก์จากแผ่นคลี่ และวาดแผ่นคลี่เป็น SVG

ใช้สำหรับสร้างและตรวจโจทย์หัวข้อพับกล่อง (tgat2.spatial.box_folding.*)
เพื่อไม่ให้ต้องอาศัยการพับในหัวซึ่งผิดได้ง่าย

วิธีคำนวณ: พับแผ่นคลี่จริงด้วยการไล่ BFS จากช่องหนึ่งไปช่องที่ติดกัน
โดยแต่ละช่องเก็บกรอบอ้างอิงสามมิติ (normal, right, up)
การเดินไปทางขวาในแผ่นคลี่ = หมุนกรอบรอบแกน up 90 องศา เป็นต้น
สองหน้าตรงข้ามกันเมื่อเวกเตอร์ normal ของมันเป็นลบของกัน

    python scripts/cube_net.py          ตรวจแผ่นคลี่ทุกแบบที่นิยามไว้
"""

from __future__ import annotations

import sys

Vec = tuple[int, int, int]


def neg(v: Vec) -> Vec:
    return (-v[0], -v[1], -v[2])


def solve_net(cells: list[tuple[int, int, str]]) -> dict:
    """คืนผลการพับแผ่นคลี่

    cells = [(col, row, label), ...]
    คืน {"valid": bool, "pairs": [(label, label) x3], "adjacent": set(frozenset),
         "normals": {label: normal}, "error": str|None}
    """
    if len(cells) != 6:
        return {"valid": False, "error": f"ต้องมี 6 ช่อง แต่มี {len(cells)}",
                "pairs": [], "adjacent": set(), "normals": {}}

    pos = {(c, r): lab for c, r, lab in cells}
    if len(pos) != 6:
        return {"valid": False, "error": "มีช่องที่พิกัดซ้ำกัน",
                "pairs": [], "adjacent": set(), "normals": {}}

    start = (cells[0][0], cells[0][1])
    frames: dict[tuple[int, int], tuple[Vec, Vec, Vec]] = {
        start: ((0, 0, 1), (1, 0, 0), (0, 1, 0))  # normal, right, up
    }
    order = [start]
    queue = [start]
    while queue:
        cur = queue.pop(0)
        n, rt, up = frames[cur]
        c, r = cur
        moves = {
            (c + 1, r): (rt, neg(n), up),          # ขวา: หมุนรอบแกน up
            (c - 1, r): (neg(rt), n, up),          # ซ้าย
            (c, r + 1): (neg(up), rt, n),          # ลง: หมุนรอบแกน right
            (c, r - 1): (up, rt, neg(n)),          # ขึ้น
        }
        for nxt, frame in moves.items():
            if nxt in pos and nxt not in frames:
                frames[nxt] = frame
                order.append(nxt)
                queue.append(nxt)

    if len(frames) != 6:
        return {"valid": False, "error": "แผ่นคลี่ไม่ต่อกันเป็นชิ้นเดียว",
                "pairs": [], "adjacent": set(), "normals": {}}

    normals = {pos[k]: frames[k][0] for k in frames}
    if len({v for v in normals.values()}) != 6:
        return {"valid": False, "error": "พับแล้วมีหน้าทับกัน ไม่ใช่แผ่นคลี่ลูกบาศก์ที่ถูกต้อง",
                "pairs": [], "adjacent": set(), "normals": normals}

    pairs = []
    done = set()
    for lab, nv in normals.items():
        if lab in done:
            continue
        for other, ov in normals.items():
            if other != lab and ov == neg(nv):
                pairs.append((lab, other))
                done.update({lab, other})
                break
    if len(pairs) != 3:
        return {"valid": False, "error": "หาคู่ตรงข้ามได้ไม่ครบ 3 คู่",
                "pairs": pairs, "adjacent": set(), "normals": normals}

    opposite = {frozenset(p) for p in pairs}
    labels = list(normals)
    adjacent = {frozenset((a, b)) for i, a in enumerate(labels)
                for b in labels[i + 1:] if frozenset((a, b)) not in opposite}

    # ช่องที่แชร์ขอบกันในแผ่นคลี่ (ใช้เขียนเหตุผลของตัวเลือกลวง)
    touching = set()
    for (c, r), lab in pos.items():
        for nxt in ((c + 1, r), (c, r + 1)):
            if nxt in pos:
                touching.add(frozenset((lab, pos[nxt])))

    # frames[label] = (normal, right, up) ของหน้านั้นหลังพับ
    # ใช้หาทิศของสัญลักษณ์ที่วาดบนแผ่นคลี่ เช่น ลูกศรที่ชี้ขึ้นบนแผ่นคลี่
    # เมื่อพับแล้วจะชี้ไปทางหน้าที่มี normal เท่ากับเวกเตอร์ up ของหน้านั้น
    face_frames = {pos[k]: frames[k] for k in frames}

    return {"valid": True, "error": None, "pairs": pairs, "adjacent": adjacent,
            "normals": normals, "touching": touching, "frames": face_frames}


def opposite_of(cells, label: str) -> str:
    res = solve_net(cells)
    for a, b in res["pairs"]:
        if a == label:
            return b
        if b == label:
            return a
    raise ValueError(f"ไม่พบหน้า {label}")


CELL = 44
ORIGIN = 10


def net_svg(cells: list[tuple[int, int, str]]) -> str:
    """วาดแผ่นคลี่เป็น SVG ใช้ currentColor เพื่อให้เห็นได้ทั้งธีมสว่างและมืด"""
    cols = max(c for c, _, _ in cells) + 1
    rows = max(r for _, r, _ in cells) + 1
    w = ORIGIN * 2 + cols * CELL
    h = ORIGIN * 2 + rows * CELL
    rects, texts = [], []
    for col, row, label in cells:
        x = ORIGIN + col * CELL
        y = ORIGIN + row * CELL
        rects.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
        texts.append(f'<text x="{x + CELL // 2}" y="{y + 29}">{label}</text>')
    return (
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img">'
        f'<g fill="none" stroke="currentColor" stroke-width="2">{"".join(rects)}</g>'
        f'<g fill="currentColor" font-size="20" text-anchor="middle" '
        f'font-family="system-ui, sans-serif">{"".join(texts)}</g>'
        f'</svg>'
    )


def describe(cells: list[tuple[int, int, str]]) -> str:
    """คำบรรยายรูปสำหรับฟิลด์ alt

    ต้องบอกคอลัมน์ของทุกช่องด้วย ไม่ใช่แค่ว่าแถวไหนมีช่องอะไร เพราะช่องเดียวกันในแถวบน
    จะอยู่เหนือช่องใดของแถวกลางเป็นตัวกำหนดว่าพับแล้วหน้าไหนตรงข้ามกัน
    (เดิมบอกแค่รายชื่อช่องต่อแถว คนที่อ่านจาก alt อย่างเดียวจึงพับตามไม่ได้ — Codex พบในการตรวจไขว้รอบ 10)
    """
    by_row: dict[int, list[tuple[int, str]]] = {}
    for c, r, lab in cells:
        by_row.setdefault(r, []).append((c, lab))
    parts = []
    for r in sorted(by_row):
        items = ", ".join(f"{lab} อยู่คอลัมน์ {c + 1}" for c, lab in sorted(by_row[r]))
        parts.append(f"แถวที่ {r + 1}: {items}")
    return ("แผ่นคลี่ลูกบาศก์บนตาราง ช่องที่อยู่คอลัมน์เดียวกันในแถวติดกันคือช่องที่ติดกันตามแนวตั้ง · "
            + " / ".join(parts))


def skip_one_pairs(cells) -> set:
    """คู่ช่องที่อยู่แถวหรือคอลัมน์เดียวกันและมีช่องคั่นอยู่ 1 ช่อง (กฎเว้นหนึ่งช่อง)"""
    pos = {(c, r): lab for c, r, lab in cells}
    out = set()
    for (c, r), lab in pos.items():
        for dc, dr in ((1, 0), (0, 1)):
            mid = (c + dc, r + dr)
            far = (c + 2 * dc, r + 2 * dr)
            if mid in pos and far in pos:
                out.add(frozenset((lab, pos[far])))
    return out


def touching_pairs(cells) -> set:
    """คู่ช่องที่แชร์ขอบกันในแผ่นคลี่"""
    pos = {(c, r): lab for c, r, lab in cells}
    out = set()
    for (c, r), lab in pos.items():
        for nxt in ((c + 1, r), (c, r + 1)):
            if nxt in pos:
                out.add(frozenset((lab, pos[nxt])))
    return out


def same_line(cells, a: str, b: str) -> str | None:
    """คืน 'แถว' หรือ 'คอลัมน์' ถ้าสองหน้าอยู่แนวเดียวกัน ไม่ใช่คืน None"""
    loc = {lab: (c, r) for c, r, lab in cells}
    (ca, ra), (cb, rb) = loc[a], loc[b]
    if ra == rb:
        return "แถว"
    if ca == cb:
        return "คอลัมน์"
    return None


def between_label(cells, a: str, b: str) -> str | None:
    """คืน label ของช่องที่อยู่ระหว่าง a กับ b (กรณีเว้นหนึ่งช่อง)"""
    pos = {(c, r): lab for c, r, lab in cells}
    loc = {lab: (c, r) for c, r, lab in cells}
    (ca, ra), (cb, rb) = loc[a], loc[b]
    mid = ((ca + cb) // 2, (ra + rb) // 2)
    if abs(ca - cb) + abs(ra - rb) == 2 and (ca == cb or ra == rb):
        return pos.get(mid)
    return None


# แผ่นคลี่ที่ใช้ในบทเรียนและโจทย์ (col, row, label)
#
# ทุกแบบในรายการนี้ผ่านการตรวจด้วย solve_net แล้วว่าพับเป็นลูกบาศก์ได้จริง
# และรายการนี้ครอบคลุม "รูปทรง" ของแผ่นคลี่ลูกบาศก์ครบทั้ง 11 แบบ
# (ยืนยันด้วยการไล่ hexomino ทั้ง 35 รูปทรงแล้วให้ solve_net ตัดสิน — ดู check_coverage)
#
# หลายชื่อที่เป็นรูปทรงเดียวกันแต่วางตัวอักษรต่างกัน ถือเป็นโจทย์ที่ต่างกัน
# เพราะสิ่งที่ผู้สอบเห็นคือตำแหน่งของตัวอักษร ไม่ใช่รูปทรงเปล่า
NETS: dict[str, list[tuple[int, int, str]]] = {
    # --- รูปทรงกากบาท แถวกลาง 4 ช่อง ---
    "cross": [(1, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (2, 1, "ง"), (3, 1, "จ"), (1, 2, "ฉ")],
    "tee": [(2, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (2, 1, "ง"), (3, 1, "จ"), (1, 2, "ฉ")],
    "cross_b": [(1, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (2, 1, "ง"), (3, 1, "จ"), (2, 2, "ฉ")],
    "row4_ends": [(3, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (2, 1, "ง"), (3, 1, "จ"), (1, 2, "ฉ")],
    # --- รูปทรงคอลัมน์ 4 ช่อง ---
    "col4": [(1, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (1, 2, "ง"), (2, 2, "จ"), (1, 3, "ฉ")],
    "cross_c": [(1, 0, "ก"), (1, 1, "ข"), (0, 1, "ค"), (2, 1, "ง"), (1, 2, "จ"), (1, 3, "ฉ")],
    "tee_col": [(0, 0, "ก"), (1, 0, "ข"), (2, 0, "ค"), (1, 1, "ง"), (1, 2, "จ"), (1, 3, "ฉ")],
    "cross_stem": [(0, 0, "ก"), (1, 0, "ข"), (1, 1, "ค"), (2, 1, "ง"), (1, 2, "จ"), (1, 3, "ฉ")],
    "zshape_long": [(0, 0, "ก"), (1, 0, "ข"), (1, 1, "ค"), (1, 2, "ง"), (1, 3, "จ"), (2, 3, "ฉ")],
    "sshape": [(0, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (1, 2, "ง"), (1, 3, "จ"), (2, 3, "ฉ")],
    # --- รูปทรงขั้นบันได กฎเว้นหนึ่งช่องใช้ได้น้อยหรือใช้ไม่ได้เลย ---
    "zigzag": [(0, 0, "ก"), (1, 0, "ข"), (1, 1, "ค"), (2, 1, "ง"), (2, 2, "จ"), (3, 2, "ฉ")],
    "zig_b": [(0, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (1, 2, "ง"), (2, 2, "จ"), (2, 3, "ฉ")],
    "plus_right": [(1, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (2, 1, "ง"), (2, 2, "จ"), (3, 1, "ฉ")],
    "step_wide": [(1, 0, "ก"), (0, 1, "ข"), (1, 1, "ค"), (2, 1, "ง"), (2, 2, "จ"), (3, 2, "ฉ")],
    "zig_cross": [(1, 0, "ก"), (1, 1, "ข"), (0, 2, "ค"), (1, 2, "ง"), (2, 2, "จ"), (2, 3, "ฉ")],
    "stair5": [(2, 0, "ก"), (3, 0, "ข"), (4, 0, "ค"), (0, 1, "ง"), (1, 1, "จ"), (2, 1, "ฉ")],
}


# ---------------------------------------------------------------- ตรวจความครบ

def _norm(cells) -> frozenset:
    mc = min(c for c, _ in cells)
    mr = min(r for _, r in cells)
    return frozenset((c - mc, r - mr) for c, r in cells)


def _canon(cells) -> frozenset:
    """ตัวแทนรูปทรงที่ไม่ขึ้นกับการหมุนหรือพลิก"""
    cur, out = _norm(cells), set()
    for _ in range(4):
        cur = _norm({(-r, c) for c, r in cur})
        out.add(cur)
        out.add(_norm({(-c, r) for c, r in cur}))
    return min(out, key=lambda s: sorted(s))


def all_cube_shapes() -> dict:
    """ไล่ hexomino ทุกรูปทรงแล้วคืนเฉพาะที่ solve_net บอกว่าพับเป็นลูกบาศก์ได้

    ไม่ได้เชื่อทฤษฎีที่ว่ามี 11 แบบ แต่คำนวณเอาเอง — ถ้าตัวพับผิด ตัวเลขนี้จะไม่ใช่ 11
    """
    shapes = {_norm({(0, 0)})}
    for _ in range(5):
        grown = set()
        for sh in shapes:
            for (c, r) in sh:
                for nxt in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                    if nxt not in sh:
                        grown.add(_norm(sh | {nxt}))
        shapes = grown

    labels = ["ก", "ข", "ค", "ง", "จ", "ฉ"]
    out: dict = {}
    for sh in shapes:
        cells = [(c, r, labels[i])
                 for i, (c, r) in enumerate(sorted(sh, key=lambda t: (t[1], t[0])))]
        if solve_net(cells)["valid"]:
            out.setdefault(_canon(sh), cells)
    return out


def orientations(cells) -> list[list[tuple[int, int, str]]]:
    """คืนแผ่นคลี่เดียวกันในทุกการวางที่ต่างกันจริง (หมุน 4 ท่า และพลิก)

    ใส่ตัวอักษรใหม่ตามลำดับการอ่าน (ซ้ายไปขวา บนลงล่าง) ทุกครั้ง
    เพื่อให้หน้าตาเหมือนข้อสอบจริง ไม่ใช่ตัวอักษรสลับที่ไม่มีระเบียบ

    ผลที่ได้คือโจทย์ที่ต่างกันในสายตาผู้สอบ แต่เป็นรูปทรงเดิม
    จึงยังคงความยากเท่าเดิม — ใช้เพิ่มจำนวนโจทย์ที่สุ่มได้โดยไม่เปลี่ยนระดับ
    """
    labels = ["ก", "ข", "ค", "ง", "จ", "ฉ"]
    shape = {(c, r) for c, r, _ in cells}
    seen, out = set(), []
    cur = _norm(shape)
    for _ in range(4):
        cur = _norm({(-r, c) for c, r in cur})
        for cand in (cur, _norm({(-c, r) for c, r in cur})):
            if cand in seen:
                continue
            seen.add(cand)
            ordered = sorted(cand, key=lambda t: (t[1], t[0]))
            out.append([(c, r, labels[i]) for i, (c, r) in enumerate(ordered)])
    return out


def check_coverage() -> tuple[int, int, list]:
    """คืน (จำนวนรูปทรงที่ครอบคลุม, จำนวนรูปทรงทั้งหมด, รายการที่ขาด)"""
    every = all_cube_shapes()
    mine = {_canon({(c, r) for c, r, _ in cells}) for cells in NETS.values()}
    missing = [cells for key, cells in every.items() if key not in mine]
    return len(every) - len(missing), len(every), missing


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    bad = 0
    for name, cells in NETS.items():
        res = solve_net(cells)
        if not res["valid"]:
            bad += 1
            print(f"  ใช้ไม่ได้  {name:12s} {res['error']}")
            continue
        pairs = " , ".join(f"{a}-{b}" for a, b in res["pairs"])
        skip = skip_one_pairs(cells)
        n_skip = sum(1 for p in res["pairs"] if frozenset(p) in skip)
        print(f"  ใช้ได้     {name:12s} คู่ตรงข้าม: {pairs}   "
              f"(กฎเว้นหนึ่งช่องหาได้ {n_skip}/3 คู่)")
    if bad:
        print(f"\nมีแผ่นคลี่ที่พับไม่ได้ {bad} แบบ ต้องเอาออกจาก NETS")
        return 1

    print(f"\nแผ่นคลี่ทั้ง {len(NETS)} แบบพับเป็นลูกบาศก์ได้จริง")

    have, total, missing = check_coverage()
    print(f"ครอบคลุมรูปทรงของแผ่นคลี่ลูกบาศก์ {have}/{total} รูปทรง "
          f"(ไล่ hexomino ทั้งหมดแล้วให้ตัวพับตัดสิน)")
    if missing:
        print("\nรูปทรงที่ยังไม่มีใน NETS — เพิ่มได้เลย:")
        for cells in missing:
            body = ", ".join(f'({c}, {r}, "{lab}")' for c, r, lab in cells)
            print(f'    [{body}]')
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
