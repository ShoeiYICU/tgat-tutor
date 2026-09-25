"""shape2d.py — เครื่องมือกลางสำหรับรูปสองมิติบนตาราง

ใช้สร้างและตรวจโจทย์มิติสัมพันธ์ที่เกี่ยวกับการหมุนและการสะท้อน
    หมุนภาพสองมิติ / แยกการหมุนออกจากการสะท้อน / หาภาพต่าง

## ทำไมต้องมีไฟล์นี้

โจทย์กลุ่มนี้ตอบผิดได้ง่ายมากถ้าวาดรูปด้วยมือ เพราะ "หมุนแล้วได้รูปนี้จริงไหม"
ต้องพิสูจน์ ไม่ใช่มองเอา ไฟล์นี้จึงคำนวณการหมุนและการสะท้อนจริง
แล้วเทียบด้วยรูปแบบมาตรฐาน (canonical form) จึงไม่มีทางผิด

## รูปที่ใช้ได้ต้องไม่สมมาตร

ถ้ารูปมีความสมมาตรในการหมุน ภาพหมุนบางมุมจะเท่ากับรูปเดิม ทำให้ตัวเลือกซ้ำ
ถ้ารูปสะท้อนแล้วเท่ากับภาพหมุนของตัวเอง (achiral) จะแยกหมุนกับสะท้อนไม่ออกเลย
`usable()` จึงคัดเฉพาะรูปที่ **หมุนได้ 4 ภาพต่างกัน และสะท้อนแล้วต่างจากทั้งสี่**
ทำให้มีภาพที่ต่างกันครบ 8 แบบเสมอ
"""

from __future__ import annotations

Cell = tuple[int, int]
Shape = frozenset


# ---------------------------------------------------------------- พื้นฐาน

def normalize(cells) -> Shape:
    """เลื่อนรูปให้ชิดมุมซ้ายบน เพื่อให้เทียบรูปกันได้โดยไม่สนตำแหน่ง"""
    cells = set(cells)
    mc = min(c for c, _ in cells)
    mr = min(r for _, r in cells)
    return frozenset((c - mc, r - mr) for c, r in cells)


def rot90(cells) -> Shape:
    """หมุนตามเข็มนาฬิกา 90 องศา"""
    return normalize((-r, c) for c, r in cells)


def flip_h(cells) -> Shape:
    """สะท้อนซ้ายขวา"""
    return normalize((-c, r) for c, r in cells)


def rotations(cells) -> list:
    """คืนภาพหมุนทั้งสี่มุม เรียงจาก 0, 90, 180, 270 องศา"""
    out, cur = [], normalize(cells)
    for _ in range(4):
        out.append(cur)
        cur = rot90(cur)
    return out


def reflections(cells) -> list:
    """คืนภาพสะท้อนทั้งสี่มุม (สะท้อนก่อนแล้วหมุน)"""
    return rotations(flip_h(cells))


def usable(cells) -> bool:
    """รูปนี้ใช้ทำโจทย์ได้ไหม — ต้องไม่สมมาตรทั้งการหมุนและการสะท้อน"""
    rots = rotations(cells)
    if len(set(rots)) != 4:
        return False                       # สมมาตรในการหมุน ภาพซ้ำกัน
    refs = reflections(cells)
    if set(rots) & set(refs):
        return False                       # สะท้อนแล้วเท่ากับภาพหมุน แยกไม่ออก
    return True


def size_of(cells) -> tuple[int, int]:
    return (max(c for c, _ in cells) + 1, max(r for _, r in cells) + 1)


# ---------------------------------------------------------------- สุ่มรูป

def random_shape(rng, n_cells: int, box: int, tries: int = 400):
    """สุ่มรูปที่ต่อกันเป็นชิ้นเดียว มี n_cells ช่อง และใช้ทำโจทย์ได้

    คืน None ถ้าสุ่มไม่ได้ในจำนวนครั้งที่กำหนด
    """
    for _ in range(tries):
        cells = {(rng.randrange(box), rng.randrange(box))}
        while len(cells) < n_cells:
            c, r = rng.choice(sorted(cells))
            nxt = rng.choice([(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)])
            if 0 <= nxt[0] < box and 0 <= nxt[1] < box:
                cells.add(nxt)
        shape = normalize(cells)
        w, h = size_of(shape)
        if w > box or h > box:
            continue
        if usable(shape):
            return shape
    return None


# ---------------------------------------------------------------- วาดรูป

CELL = 26
PAD = 8


def shape_svg(cells, box: int | None = None, marked: Cell | None = None) -> str:
    """วาดรูปเป็น SVG ช่องทึบบนตารางจาง ๆ

    marked = ช่องที่ทำเครื่องหมายไว้ ใช้เมื่อโจทย์ต้องอ้างช่องใดช่องหนึ่ง
    """
    cells = normalize(cells)
    w, h = size_of(cells)
    if box:
        w = h = max(box, w, h)
    width = PAD * 2 + w * CELL
    height = PAD * 2 + h * CELL

    grid = []
    for i in range(w + 1):
        x = PAD + i * CELL
        grid.append(f'<line x1="{x}" y1="{PAD}" x2="{x}" y2="{PAD + h * CELL}"/>')
    for i in range(h + 1):
        y = PAD + i * CELL
        grid.append(f'<line x1="{PAD}" y1="{y}" x2="{PAD + w * CELL}" y2="{y}"/>')
    grid_g = (f'<g fill="none" stroke="currentColor" stroke-width="1" '
              f'opacity="0.35">{"".join(grid)}</g>')

    fills = "".join(
        f'<rect x="{PAD + c * CELL + 1}" y="{PAD + r * CELL + 1}" '
        f'width="{CELL - 2}" height="{CELL - 2}"/>' for c, r in sorted(cells)
    )
    fill_g = f'<g fill="currentColor">{fills}</g>'

    mark_g = ""
    if marked and marked in cells:
        mc, mr = marked
        cx = PAD + mc * CELL + CELL // 2
        cy = PAD + mr * CELL + CELL // 2
        # ช่องที่ทำเครื่องหมายถูกถมสีทึบอยู่แล้ว วงกลมจึงต้องใช้สีพื้นหลังกับสีเน้น
        # จึงจะมองเห็น (มีค่าสำรองไว้เผื่อเปิดไฟล์นอกเว็บที่ไม่มีตัวแปรสี)
        mark_g = (f'<circle cx="{cx}" cy="{cy}" r="{CELL // 4}" fill="none" '
                  f'stroke="var(--surface, #ffffff)" stroke-width="4"/>'
                  f'<circle cx="{cx}" cy="{cy}" r="{CELL // 4}" fill="none" '
                  f'stroke="var(--accent, #3b5bdb)" stroke-width="2.5" '
                  f'stroke-dasharray="3 2"/>')

    return (f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img">{grid_g}{fill_g}{mark_g}</svg>')


def describe(cells) -> str:
    """คำบรรยายรูปสำหรับฟิลด์ alt — ไล่ทีละแถวเพื่อให้คนอ่านสร้างภาพตามได้"""
    cells = normalize(cells)
    w, h = size_of(cells)
    rows = []
    for r in range(h):
        cols = [str(c + 1) for c in range(w) if (c, r) in cells]
        if cols:
            rows.append(f"แถวที่ {r + 1} มีช่องที่ {', '.join(cols)}")
    return f"รูปบนตาราง {w} x {h} ช่อง · " + " / ".join(rows)


# ---------------------------------------------------------------- ตรวจตัวเอง

def _selfcheck() -> int:
    """ตรวจว่าการหมุนและการสะท้อนทำงานถูกต้อง"""
    import random
    rng = random.Random(7)
    bad = 0

    # หมุนสี่ครั้งต้องกลับมาเท่าเดิม
    for _ in range(200):
        s = random_shape(rng, rng.randint(4, 6), 4)
        if s is None:
            continue
        cur = s
        for _ in range(4):
            cur = rot90(cur)
        if cur != s:
            print("  ผิด: หมุนสี่ครั้งแล้วไม่กลับมาเท่าเดิม")
            bad += 1
        if flip_h(flip_h(s)) != s:
            print("  ผิด: สะท้อนสองครั้งแล้วไม่กลับมาเท่าเดิม")
            bad += 1
        if len(set(rotations(s)) | set(reflections(s))) != 8:
            print("  ผิด: รูปที่ผ่าน usable() ควรมีภาพต่างกัน 8 แบบ")
            bad += 1
        if len(s) != len(rot90(s)) or len(s) != len(flip_h(s)):
            print("  ผิด: จำนวนช่องเปลี่ยนหลังแปลงรูป")
            bad += 1

    # รูปที่สมมาตรต้องถูกคัดออก
    square = normalize({(0, 0), (1, 0), (0, 1), (1, 1)})
    if usable(square):
        print("  ผิด: รูปสี่เหลี่ยมจัตุรัสสมมาตร ไม่ควรผ่าน usable()")
        bad += 1
    ell = normalize({(0, 0), (0, 1), (0, 2), (1, 2)})   # ตัวแอล เป็นรูปที่มีคู่สะท้อน
    if not usable(ell):
        print("  ผิด: รูปตัวแอลไม่สมมาตร ควรผ่าน usable()")
        bad += 1
    return bad


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    n = _selfcheck()
    if n:
        print(f"\nการแปลงรูปมีปัญหา {n} จุด")
    else:
        print("การหมุนและการสะท้อนทำงานถูกต้อง "
              "(หมุนครบรอบกลับที่เดิม · สะท้อนสองครั้งกลับที่เดิม · "
              "รูปที่ใช้ได้มีภาพต่างกัน 8 แบบ · รูปสมมาตรถูกคัดออก)")
    sys.exit(1 if n else 0)
