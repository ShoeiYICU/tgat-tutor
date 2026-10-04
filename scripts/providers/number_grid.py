"""provider: number_grid.missing_value — ตารางตัวเลขที่ต้องหาค่าที่หายไป

รูปแบบข้อสอบนี้อยู่ในผังสอบ TPAT3 ด้านตัวเลข (ตัวอย่างในผังสอบคือ
"จากตัวเลขในตารางข้างล่าง X แทนจำนวนใด")

ต่างจากอนุกรมแถวเดียวตรงที่ต้องหากฎทั้งแนวนอนและแนวตั้ง แล้วตรวจให้สอดคล้องกัน
ผู้สอบที่ดูแค่แถวเดียวจะได้คำตอบที่เข้ากับแถวนั้นแต่ขัดกับคอลัมน์

## ทำไมทำเป็น provider ไม่ใช่แม่แบบเลขคณิต

เพราะโจทย์ต้องมี **รูปตาราง** ที่สร้างตามค่าที่สุ่มมา ซึ่งนิพจน์เลขคณิตทำไม่ได้
ส่วนตัวเลขในตารางและเฉลยคำนวณจากสูตรเชิงเส้น cell(r,c) = base + r*dr + c*dc
จึงถูกต้องเสมอโดยไม่ต้องให้ใครตรวจเลข

## ตัวเลือกลวงมาจากกฎที่ใช้ผิด ไม่ใช่การสุ่มตัวเลข

แต่ละตัวคือผลของความเข้าใจผิดที่เกิดขึ้นจริง และคำนวณได้ จึงอธิบายเหตุผลได้ทุกตัว

พารามิเตอร์
    rows           int   จำนวนแถว (3-5)
    cols           int   จำนวนคอลัมน์ (3-5)
    base_range     [lo, hi]  ช่วงค่าของช่องซ้ายบน
    dr_range       [lo, hi]  ช่วงผลต่างระหว่างแถว
    dc_range       [lo, hi]  ช่วงผลต่างระหว่างคอลัมน์
    hide_inner     bool  true = ซ่อนช่องที่ไม่อยู่ขอบตาราง (ยากขึ้น เพราะต้องดูสองทิศ)
"""

from __future__ import annotations

NAME = "number_grid.missing_value"
DOC = "ตารางตัวเลขที่ต้องหาค่าที่หายไป — ตัวเลขในตารางและเฉลยคำนวณจากสูตรเชิงเส้น"
ANSWER_KIND = "number"

VAR_NAMES = ["rows", "cols", "base", "dr", "dc", "hr", "hc"]

CELL_W = 56
CELL_H = 40
PAD = 10


def validate_params(params: dict) -> list[str]:
    bad: list[str] = []
    if not isinstance(params, dict):
        return ["params ต้องเป็นอ็อบเจกต์"]

    for key, lo, hi in (("rows", 3, 5), ("cols", 3, 5)):
        v = params.get(key)
        if not (isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi):
            bad.append(f"{key} ต้องเป็นจำนวนเต็ม {lo}-{hi} (พบ {v!r})")

    for key in ("base_range", "dr_range", "dc_range"):
        r = params.get(key)
        if not (isinstance(r, list) and len(r) == 2
                and all(isinstance(x, int) and not isinstance(x, bool) for x in r)
                and r[0] <= r[1]):
            bad.append(f"{key} ต้องเป็น [ต่ำสุด, สูงสุด] ที่เป็นจำนวนเต็ม (พบ {r!r})")

    hi_ = params.get("hide_inner")
    if hi_ is not None and not isinstance(hi_, bool):
        bad.append("hide_inner ต้องเป็น true, false หรือไม่ใส่")

    if not bad:
        rows, cols = params["rows"], params["cols"]
        if params.get("hide_inner") and (rows < 3 or cols < 3):
            bad.append("hide_inner ต้องมีตารางอย่างน้อย 3x3 จึงจะมีช่องที่ไม่อยู่ขอบ")
        for key in ("dr_range", "dc_range"):
            lo, hi = params[key]
            if lo <= 0 <= hi:
                bad.append(f"{key} คร่อมศูนย์ ถ้าผลต่างเป็น 0 ทั้งแถวหรือคอลัมน์จะซ้ำกันหมด "
                           "ทำให้กฎไม่ชัดและตัวเลือกลวงชนกัน")
    return bad


def var_names(params: dict) -> list[str]:
    return list(VAR_NAMES)


def draw(params: dict, rng) -> dict | None:
    rows, cols = params["rows"], params["cols"]
    base = rng.randint(*params["base_range"])
    dr = rng.randint(*params["dr_range"])
    dc = rng.randint(*params["dc_range"])
    if dr == 0 or dc == 0:
        return None
    if params.get("hide_inner"):
        hr = rng.randint(1, rows - 2)
        hc = rng.randint(1, cols - 2)
    else:
        hr = rng.randint(0, rows - 1)
        hc = rng.randint(0, cols - 1)

    vals = {"rows": rows, "cols": cols, "base": base, "dr": dr, "dc": dc,
            "hr": hr, "hc": hc}
    # ตัวเลือกต้องต่างกันจริงทั้งห้าตัว ไม่งั้นข้อนี้ใช้ไม่ได้ ให้สุ่มใหม่
    if len({v for v, _, _ in _candidates(vals)}) != 5:
        return None
    # ค่าลบในตารางทำให้โจทย์อ่านยากขึ้นมากโดยไม่ได้วัดอะไรเพิ่ม จึงเลี่ยง
    if any(_cell(vals, r, c) <= 0 for r in range(rows) for c in range(cols)):
        return None
    return vals


def _cell(v: dict, r: int, c: int) -> int:
    return v["base"] + r * v["dr"] + c * v["dc"]


def _candidates(v: dict):
    """คืน [(ค่า, เหตุผล, tag)] โดยตัวแรกคือคำตอบที่ถูก

    ตัวลวงทุกตัวคือผลของกฎที่ใช้ผิดจริง ไม่ใช่ตัวเลขที่สุ่มมา
    """
    hr, hc, dr, dc, base = v["hr"], v["hc"], v["dr"], v["dc"], v["base"]
    # นับตำแหน่งพลาดหนึ่งช่องเกิดได้ทั้งนับเกินและนับขาด สลับกันตามค่าที่สุ่มได้
    # ถ้าใช้แบบนับเกินอย่างเดียว คำตอบจะเป็นค่ากลางของตัวเลือกบ่อยจนเดาได้
    if (base + hr + hc) % 2:
        off = (base + (hr + 1) * dr + hc * dc,
               "นับตำแหน่งแถวเกินไปหนึ่งช่อง เพราะเริ่มนับแถวแรกเป็นหนึ่งแทนที่จะเป็นศูนย์")
    else:
        off = (base + hr * dr + (hc - 1) * dc,
               "นับตำแหน่งคอลัมน์ขาดไปหนึ่งช่อง จึงได้ค่าของช่องทางซ้ายแทน")
    cands = _candidates_base(v)
    cands[3] = (off[0], off[1], "off_by_one_row")
    return cands


def _candidates_base(v: dict):
    hr, hc, dr, dc, base = v["hr"], v["hc"], v["dr"], v["dc"], v["base"]
    return [
        (base + hr * dr + hc * dc, "", ""),
        (base + hc * dr + hr * dc,
         "สลับแถวกับคอลัมน์ คือเอาผลต่างของแถวไปคูณกับตำแหน่งคอลัมน์",
         "row_col_swapped"),
        (base + (hr + hc) * dr,
         "ใช้ผลต่างของแถวกับทั้งสองทิศ ไม่ได้สังเกตว่าผลต่างของคอลัมน์เป็นอีกค่า",
         "same_difference_both_axes"),
        (base + (hr + 1) * dr + hc * dc,
         "นับตำแหน่งแถวเกินไปหนึ่งช่อง เพราะเริ่มนับแถวแรกเป็นหนึ่งแทนที่จะเป็นศูนย์",
         "off_by_one_row"),
        (base + dr + dc,
         "บวกผลต่างของแถวกับคอลัมน์เข้าด้วยกันครั้งเดียว "
         "ไม่ได้คูณกับจำนวนช่องที่ห่างจากช่องแรก",
         "added_instead_of_multiplied"),
    ]


def grid_svg(v: dict) -> str:
    rows, cols = v["rows"], v["cols"]
    w = PAD * 2 + cols * CELL_W
    h = PAD * 2 + rows * CELL_H
    rects, texts = [], []
    for r in range(rows):
        for c in range(cols):
            x = PAD + c * CELL_W
            y = PAD + r * CELL_H
            rects.append(f'<rect x="{x}" y="{y}" width="{CELL_W}" height="{CELL_H}"/>')
            label = "X" if (r, c) == (v["hr"], v["hc"]) else str(_cell(v, r, c))
            weight = ' font-weight="bold"' if label == "X" else ""
            texts.append(f'<text x="{x + CELL_W // 2}" y="{y + 26}"{weight}>{label}</text>')
    return (
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img">'
        f'<g fill="none" stroke="currentColor" stroke-width="2">{"".join(rects)}</g>'
        f'<g fill="currentColor" font-size="18" text-anchor="middle" '
        f'font-family="system-ui, sans-serif">{"".join(texts)}</g>'
        f'</svg>'
    )


def describe(v: dict) -> str:
    rows = []
    for r in range(v["rows"]):
        cells = ["X" if (r, c) == (v["hr"], v["hc"]) else str(_cell(v, r, c))
                 for c in range(v["cols"])]
        rows.append(f"แถวที่ {r + 1} คือ {', '.join(cells)}")
    return (f"ตารางตัวเลข {v['rows']} แถว {v['cols']} คอลัมน์ · " + " / ".join(rows)
            + f" · ช่อง X อยู่แถวที่ {v['hr'] + 1} คอลัมน์ที่ {v['hc'] + 1}")


def build(params: dict, vals: dict) -> dict:
    cands = _candidates(vals)
    answer = cands[0][0]
    distractors = [{"value": val, "reason": why, "tag": tag}
                   for val, why, tag in cands[1:]]

    hr, hc, dr, dc = vals["hr"], vals["hc"], vals["dr"], vals["dc"]
    rows, cols = vals["rows"], vals["cols"]

    # เลือกแถวและคอลัมน์ที่ไม่มีช่อง X เพื่อใช้หากฎ — มีอยู่แน่นอนเพราะตารางอย่างน้อย 3x3
    ref_r = next(r for r in range(rows) if r != hr)
    ref_c = next(c for c in range(cols) if c != hc)
    row_example = ", ".join(str(_cell(vals, ref_r, c)) for c in range(cols))
    col_example = ", ".join(str(_cell(vals, r, ref_c)) for r in range(rows))
    left = _cell(vals, hr, hc - 1) if hc > 0 else None
    above = _cell(vals, hr - 1, hc) if hr > 0 else None

    steps = [
        {"do_md": f"หากฎของแถวจากแถวที่ไม่มี X เช่นแถวที่ {ref_r + 1} "
                  f"คือ {row_example} เพิ่มขึ้นทีละ {dc}",
         "why_md": "ต้องหากฎจากแถวที่รู้ค่าครบก่อน เพราะแถวที่มี X หาผลต่างตรง ๆ ไม่ได้"},
        {"do_md": f"หากฎของคอลัมน์จากคอลัมน์ที่ไม่มี X เช่นคอลัมน์ที่ {ref_c + 1} "
                  f"คือ {col_example} เพิ่มขึ้นทีละ {dr}",
         "why_md": "ตารางแบบนี้มีสองกฎพร้อมกัน ถ้าดูแค่ทิศเดียวจะได้คำตอบที่ขัดกับอีกทิศ"},
    ]
    if left is not None:
        steps.append({
            "do_md": f"เดินตามแถว: ช่องซ้ายของ X คือ {left} บวกผลต่างของคอลัมน์ "
                     f"ได้ {left} + {dc} = {answer}",
            "why_md": "เดินจากช่องที่ติดกันทีละช่อง ปลอดภัยกว่าการคูณตำแหน่งแล้วนับพลาด",
        })
    if above is not None:
        steps.append({
            "do_md": f"ตรวจจากคอลัมน์: ช่องบนของ X คือ {above} บวกผลต่างของแถว "
                     f"ได้ {above} + {dr} = {answer}",
            "why_md": "ได้ค่าเดียวกันจากสองทิศ จึงมั่นใจว่าไม่ได้นับช่องพลาด",
        })
    if left is None and above is None:
        steps.append({
            "do_md": f"คิดจากช่องซ้ายบน: {vals['base']} + {hr} x {dr} + {hc} x {dc} = {answer}",
            "why_md": "X อยู่ที่มุมซ้ายบนของตาราง จึงไม่มีช่องที่ติดกันให้เดินตาม "
                      "ต้องคิดจากตำแหน่งโดยตรง",
        })

    hints = [
        "ตารางแบบนี้มีกฎสองทิศพร้อมกัน ให้หากฎของแถวและกฎของคอลัมน์แยกกันก่อน",
        f"หากฎจากแถวหรือคอลัมน์ที่ **ไม่มี** ช่อง X อยู่ เช่นแถวที่ {ref_r + 1} "
        f"หรือคอลัมน์ที่ {ref_c + 1}",
        "ได้กฎแล้วให้เดินจากช่องที่ติดกับ X ทีละช่อง แล้วตรวจอีกทิศให้ได้ค่าเดียวกัน",
    ]

    explanation = (
        f"ผลต่างระหว่างคอลัมน์คือ {dc} และผลต่างระหว่างแถวคือ {dr} "
        f"ช่อง X อยู่แถวที่ {hr + 1} คอลัมน์ที่ {hc + 1} "
        f"จึงมีค่า {vals['base']} + {hr} x {dr} + {hc} x {dc} = {answer} "
        "ซึ่งสอดคล้องทั้งแนวแถวและแนวคอลัมน์"
    )

    return {
        "answer": answer,
        "distractors": distractors,
        "steps": steps,
        "hints": hints,
        "explanation": explanation,
        "figures": [{
            "id": "fig1",
            "type": "svg",
            "alt": describe(vals),
            "svg": grid_svg(vals),
            "caption": None,
        }],
        "meta": {"dr": dr, "dc": dc, "hide": [hr, hc]},
    }
