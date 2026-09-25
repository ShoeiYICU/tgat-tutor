"""shape3d.py — ทรงที่ประกอบจากลูกบาศก์หน่วย และภาพวาดสามมิติแบบไอโซเมตริก

ใช้กับโจทย์ TGAT2 มิติสัมพันธ์ที่ต้องหมุนภาพสามมิติ

หลักที่ยึด
    - ทรงหนึ่งเก็บเป็นเซตของพิกัดจำนวนเต็ม (x, y, z) ของลูกบาศก์แต่ละก้อน
    - การหมุนคือการแปลงพิกัด ไม่ใช่การวาดใหม่ด้วยมือ เฉลยจึงถูกต้องเสมอ
    - usable() คัดเฉพาะทรงที่ "ภาพสะท้อนไม่เท่ากับภาพหมุนใด ๆ" เพื่อให้ตัวลวงแบบภาพสะท้อนใช้ได้จริง

แกน
    x  ชี้ไปทางขวา-ล่างของภาพ
    y  ชี้ไปทางซ้าย-ล่างของภาพ
    z  ชี้ขึ้น

วิธีตรวจตัวเอง
    python scripts/shape3d.py
"""

from __future__ import annotations

Cell = tuple[int, int, int]


# ---------------------------------------------------------------- พื้นฐาน

def normalize(cells) -> frozenset:
    cells = set(cells)
    mx = min(x for x, _, _ in cells)
    my = min(y for _, y, _ in cells)
    mz = min(z for _, _, z in cells)
    return frozenset((x - mx, y - my, z - mz) for x, y, z in cells)


def rot_z(cells) -> frozenset:
    """หมุนรอบแกนตั้ง 90 องศา ตามเข็มนาฬิกาเมื่อมองจากด้านบน"""
    return normalize((y, -x, z) for x, y, z in cells)


def rot_x(cells) -> frozenset:
    """หมุนรอบแกนนอน (แกน x) 90 องศา"""
    return normalize((x, -z, y) for x, y, z in cells)


def rot_y(cells) -> frozenset:
    """หมุนรอบแกนนอนอีกแกนหนึ่ง (แกน y) 90 องศา"""
    return normalize((z, y, -x) for x, y, z in cells)


def mirror(cells) -> frozenset:
    """ภาพสะท้อน (สลับซ้ายขวา)"""
    return normalize((-x, y, z) for x, y, z in cells)


def rotations(cells) -> set:
    """ท่าวางทั้งหมดที่ได้จากการหมุน (ไม่เกิน 24 ท่า)"""
    seen = {normalize(cells)}
    frontier = [normalize(cells)]
    while frontier:
        cur = frontier.pop()
        for f in (rot_x, rot_y, rot_z):
            nxt = f(cur)
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return seen


def usable(cells) -> bool:
    """ทรงนี้ใช้ทำโจทย์ได้ไหม

    ต้องไม่สมมาตรในการหมุน (ครบ 24 ท่าไม่ซ้ำ) และภาพสะท้อนต้องไม่ตรงกับท่าหมุนใดเลย
    ไม่เช่นนั้นตัวลวงแบบภาพสะท้อนจะกลายเป็นคำตอบที่ถูกต้องไปด้วย
    """
    rots = rotations(cells)
    return len(rots) == 24 and not (rots & rotations(mirror(cells)))


def connected(cells) -> bool:
    cells = set(normalize(cells))
    seen = {next(iter(cells))}
    stack = list(seen)
    while stack:
        x, y, z = stack.pop()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nxt = (x + d[0], y + d[1], z + d[2])
            if nxt in cells and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == len(cells)


# ---------------------------------------------------------------- วาดภาพ

A, B, C = 26, 15, 30          # ระยะในแนวนอน · แนวลึก · ความสูงของลูกบาศก์หนึ่งก้อน
PAD = 12
FILL = {"top": 0.22, "left": 0.10, "right": 0.34}   # ความเข้มของแต่ละหน้า


def _pt(x, y, z):
    return ((x - y) * A, (x + y) * B - z * C)


def iso_svg(cells) -> str:
    """วาดทรงเป็นภาพสามมิติ ใช้ currentColor จึงเห็นได้ทั้งธีมสว่างและมืด"""
    cells = normalize(cells)
    pts = [_pt(x + dx, y + dy, z + dz) for x, y, z in cells
           for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
    minx = min(p[0] for p in pts)
    miny = min(p[1] for p in pts)
    w = max(p[0] for p in pts) - minx + PAD * 2
    h = max(p[1] for p in pts) - miny + PAD * 2

    def poly(corners, kind):
        pp = " ".join(f"{px - minx + PAD:.1f},{py - miny + PAD:.1f}" for px, py in corners)
        return (f'<polygon points="{pp}" fill="currentColor" fill-opacity="{FILL[kind]}" '
                f'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>')

    body = []
    # วาดจากก้อนที่อยู่ไกลที่สุดไปหาก้อนที่อยู่ใกล้ที่สุด ก้อนหน้าจึงบังก้อนหลังได้ถูกต้อง
    for x, y, z in sorted(cells, key=lambda c: c[0] + c[1] + c[2]):
        top = [_pt(x, y, z + 1), _pt(x + 1, y, z + 1), _pt(x + 1, y + 1, z + 1), _pt(x, y + 1, z + 1)]
        right = [_pt(x + 1, y, z), _pt(x + 1, y + 1, z), _pt(x + 1, y + 1, z + 1), _pt(x + 1, y, z + 1)]
        left = [_pt(x, y + 1, z), _pt(x + 1, y + 1, z), _pt(x + 1, y + 1, z + 1), _pt(x, y + 1, z + 1)]
        body += [poly(top, "top"), poly(left, "left"), poly(right, "right")]
    return (f'<svg viewBox="0 0 {w:.0f} {h:.0f}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img">{"".join(body)}</svg>')


def describe(cells) -> str:
    """คำบรรยายภาพสำหรับฟิลด์ alt — ไล่ทีละชั้นจากล่างขึ้นบน"""
    cells = normalize(cells)
    zs = sorted({z for _, _, z in cells})
    parts = []
    for z in zs:
        at = sorted((x, y) for x, y, zz in cells if zz == z)
        pos = ", ".join(f"({x + 1}, {y + 1})" for x, y in at)
        parts.append(f"ชั้นที่ {z + 1} มีลูกบาศก์ที่ตำแหน่ง (แถว, คอลัมน์) {pos}")
    return f"ทรงประกอบจากลูกบาศก์ {len(cells)} ก้อน · " + " / ".join(parts)


# ---------------------------------------------------------------- ตรวจตัวเอง

def _selfcheck() -> int:
    # ทรง L สามก้อน มีปีกด้านข้างและก้อนซ้อนบน — ไม่สมมาตร จึงใช้ทดสอบได้
    L = normalize({(0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0), (2, 1, 1)})
    problems = []

    if not connected(L):
        problems.append("ทรงทดสอบควรต่อกันเป็นชิ้นเดียว")
    if len(rotations(L)) != 24:
        problems.append(f"ทรงทดสอบควรมี 24 ท่า แต่ได้ {len(rotations(L))}")
    if not usable(L):
        problems.append("ทรงทดสอบควรใช้ทำโจทย์ได้ (ภาพสะท้อนต้องไม่ตรงกับท่าหมุนใด)")

    # หมุนรอบแกนเดียวกันสี่ครั้งต้องกลับมาเท่าเดิม
    for name, f in (("rot_x", rot_x), ("rot_y", rot_y), ("rot_z", rot_z)):
        cur = L
        for _ in range(4):
            cur = f(cur)
        if cur != L:
            problems.append(f"{name} หมุนครบสี่ครั้งแล้วไม่กลับมาเท่าเดิม")

    # ลูกบาศก์ 2x2x2 สมมาตร จึงต้องใช้ทำโจทย์ไม่ได้
    cube = {(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)}
    if usable(cube):
        problems.append("ลูกบาศก์ตันไม่ควรผ่าน usable()")

    svg = iso_svg(L)
    if not svg.startswith("<svg") or svg.count("<polygon") != len(L) * 3:
        problems.append("ภาพที่วาดมีจำนวนหน้าไม่ถูกต้อง")

    for p in problems:
        print("  ไม่ผ่าน:", p)
    print("shape3d: ผ่านทั้งหมด" if not problems else f"shape3d: มีปัญหา {len(problems)} ข้อ")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(_selfcheck())
