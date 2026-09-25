"""provider: gear_train.direction_and_speed — ระบบเฟือง ถามทิศการหมุนและความเร็ว

รูปแบบข้อสอบนี้อยู่ในผังสอบ TPAT3 ด้านเชิงกลและฟิสิกส์
(ตัวอย่างในผังสอบคือ "ถ้าเฟือง C หมุนทวนเข็มนาฬิกา...")

## กฎสองข้อที่ข้อสอบวัด

1. **ทิศ** เฟืองที่ขบกันหมุนสวนทางกันเสมอ จึงสลับทิศทุกครั้งที่ขบ
   เฟืองลำดับที่คี่หมุนทิศเดียวกับตัวแรก ลำดับที่คู่หมุนสวนทาง
2. **ความเร็ว** รอบต่อนาทีแปรผกผันกับจำนวนฟัน
   และ **ขึ้นกับเฟืองตัวแรกกับตัวสุดท้ายเท่านั้น** เฟืองที่อยู่ระหว่างกลาง
   (เฟืองทด) ไม่มีผลต่ออัตราทดเลย มีผลแค่ทิศ

ข้อ 2 คือกับดักหลักของรูปแบบนี้ ผู้สอบมักคิดว่าเฟืองกลางเปลี่ยนความเร็วด้วย

## ทำไมทำเป็น provider

เฉลยทั้งทิศและความเร็วคำนวณจากจำนวนฟันได้ 100% และโจทย์ต้องมี **รูปเฟือง**
ที่วาดตามค่าที่สุ่มมา ซึ่งนิพจน์เลขคณิตทำไม่ได้

พารามิเตอร์
    n_gears      int        จำนวนเฟืองในระบบ (3-5)
    teeth_choices list[int] จำนวนฟันที่เลือกใช้ได้ (ต้องมีอย่างน้อย 3 ค่า)
    rpm_choices  list[int]  รอบต่อนาทีของเฟืองตัวแรกที่เลือกใช้ได้
    integer_rpm  bool       true = ยอมรับเฉพาะชุดที่คำตอบเป็นจำนวนเต็ม (ค่าเริ่มต้น true)
"""

from __future__ import annotations

NAME = "gear_train.direction_and_speed"
DOC = ("ระบบเฟือง ถามทิศการหมุนและรอบต่อนาทีของเฟืองตัวสุดท้าย "
       "— เฉลยและรูปคำนวณจากจำนวนฟันด้วยโค้ด")
ANSWER_KIND = "text"

VAR_NAMES = ["teeth", "rpm_in", "dir_in", "labels"]

CW = "ตามเข็มนาฬิกา"
CCW = "ทวนเข็มนาฬิกา"
LABELS = ["A", "B", "C", "D", "E", "F"]


def _opp(d: str) -> str:
    return CCW if d == CW else CW


def validate_params(params: dict) -> list[str]:
    bad: list[str] = []
    if not isinstance(params, dict):
        return ["params ต้องเป็นอ็อบเจกต์"]

    n = params.get("n_gears")
    if not (isinstance(n, int) and not isinstance(n, bool) and 3 <= n <= 5):
        bad.append(f"n_gears ต้องเป็นจำนวนเต็ม 3-5 (พบ {n!r})")

    for key, lo in (("teeth_choices", 3), ("rpm_choices", 1)):
        v = params.get(key)
        if not (isinstance(v, list) and len(v) >= lo
                and all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in v)):
            bad.append(f"{key} ต้องเป็นอาร์เรย์จำนวนเต็มบวกอย่างน้อย {lo} ค่า (พบ {v!r})")
        elif len(set(v)) != len(v):
            bad.append(f"{key} มีค่าซ้ำกัน")

    ir = params.get("integer_rpm")
    if ir is not None and not isinstance(ir, bool):
        bad.append("integer_rpm ต้องเป็น true, false หรือไม่ใส่")

    if not bad and params.get("integer_rpm", True):
        teeth, rpms = params["teeth_choices"], params["rpm_choices"]
        ok = any(rpm * t_first % t_last == 0
                 for rpm in rpms for t_first in teeth for t_last in teeth
                 if t_first != t_last)
        if not ok:
            bad.append("integer_rpm เปิดอยู่ แต่ไม่มีชุด teeth_choices กับ rpm_choices ใดเลย "
                       "ที่ให้คำตอบเป็นจำนวนเต็ม — ปรับค่าให้หารกันลงตัวได้")
    return bad


def var_names(params: dict) -> list[str]:
    return list(VAR_NAMES)


def draw(params: dict, rng) -> dict | None:
    n = params["n_gears"]
    choices = list(params["teeth_choices"])
    if len(choices) < 3:
        return None
    # เฟืองที่ขบกันต้องมีจำนวนฟันไม่เท่ากัน ไม่งั้นอัตราทดเป็น 1 แล้วโจทย์ไม่วัดอะไร
    teeth = [rng.choice(choices)]
    for _ in range(n - 1):
        nxt = [t for t in choices if t != teeth[-1]]
        if not nxt:
            return None
        teeth.append(rng.choice(nxt))
    if teeth[0] == teeth[-1]:
        return None          # อัตราทดเป็น 1 พอดี ความเร็วไม่เปลี่ยน ข้อนี้ไม่วัดกฎที่สอง

    rpm_in = rng.choice(list(params["rpm_choices"]))
    if params.get("integer_rpm", True) and (rpm_in * teeth[0]) % teeth[-1] != 0:
        return None

    vals = {
        "teeth": teeth,
        "rpm_in": rpm_in,
        "dir_in": rng.choice([CW, CCW]),
        "labels": LABELS[:n],
    }
    if len({v for v, _, _ in _candidates(vals)}) != 5:
        return None
    return vals


def _fmt(n) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.2f}".rstrip("0").rstrip(".")


def _answer_text(direction: str, rpm) -> str:
    return f"{direction} {_fmt(rpm)} รอบต่อนาที"


def _candidates(v: dict):
    """คืน [(ข้อความคำตอบ, เหตุผล, tag)] โดยตัวแรกคือคำตอบที่ถูก"""
    teeth, rpm_in, dir_in = v["teeth"], v["rpm_in"], v["dir_in"]
    n = len(teeth)
    meshes = n - 1
    dir_out = dir_in if meshes % 2 == 0 else _opp(dir_in)
    rpm_out = rpm_in * teeth[0] / teeth[-1]

    # ใช้เฉพาะเฟืองตัวที่สองเป็นตัวหาร เหมือนคิดว่าเฟืองกลางกำหนดอัตราทด
    rpm_second = rpm_in * teeth[0] / teeth[1]
    return [
        (_answer_text(dir_out, rpm_out), "", ""),
        (_answer_text(_opp(dir_out), rpm_out),
         f"คำนวณความเร็วถูก แต่ได้ทิศผิด ระบบนี้ขบกัน {meshes} ครั้ง "
         f"จึงสลับทิศ {meshes} ครั้ง ไม่ใช่นับจำนวนเฟือง",
         "wrong_direction"),
        (_answer_text(dir_out, rpm_in * teeth[-1] / teeth[0]),
         "กลับเศษกับส่วนของอัตราทด เอาจำนวนฟันของเฟืองตัวสุดท้ายไปคูณ "
         "ทั้งที่รอบต่อนาทีแปรผกผันกับจำนวนฟัน",
         "ratio_inverted"),
        (_answer_text(dir_out, rpm_second),
         "ใช้จำนวนฟันของเฟืองตัวที่สองเป็นตัวหาร เหมือนคิดว่าเฟืองที่อยู่ระหว่างกลาง "
         "กำหนดอัตราทด ที่จริงเฟืองกลางมีผลแค่ทิศ ไม่มีผลต่อความเร็ว",
         "middle_gear_affects_ratio"),
        (_answer_text(dir_out, rpm_in),
         "คิดว่าความเร็วไม่เปลี่ยนเพราะเฟืองทุกตัวขบกันเป็นระบบเดียว "
         "ที่จริงจำนวนฟันต่างกันทำให้รอบต่อนาทีต่างกัน",
         "speed_unchanged"),
    ]


R_SCALE = 0.9
PAD = 14


def gear_svg(v: dict) -> str:
    """วาดเฟืองเรียงกันเป็นแถว โดยรัศมีสัมพันธ์กับจำนวนฟัน

    วาดเป็นวงกลมพร้อมฟันเป็นขีดสั้นรอบวง ไม่ได้วาดฟันครบจำนวนจริง
    เพราะจำนวนฟันจริงมากเกินกว่าจะเห็นชัดในรูปเล็ก จึงกำกับตัวเลขไว้ให้อ่าน
    """
    teeth, labels = v["teeth"], v["labels"]
    radii = [t * R_SCALE for t in teeth]
    xs, x = [], PAD
    for i, r in enumerate(radii):
        if i == 0:
            x += r
        else:
            x += radii[i - 1] + r - 4      # ขบกันจึงวาดให้ขอบเกยกันเล็กน้อย
        xs.append(x)
    h = PAD * 2 + max(radii) * 2 + 34
    w = xs[-1] + radii[-1] + PAD
    cy = PAD + max(radii)

    parts = []
    for xi, r, t, lab in zip(xs, radii, teeth, labels):
        parts.append(f'<circle cx="{xi:.0f}" cy="{cy:.0f}" r="{r:.0f}"/>')
        parts.append(f'<circle cx="{xi:.0f}" cy="{cy:.0f}" r="{r * 0.18:.0f}"/>')
    shapes = (f'<g fill="none" stroke="currentColor" stroke-width="2">'
              f'{"".join(parts)}</g>')

    texts = []
    for xi, r, t, lab in zip(xs, radii, teeth, labels):
        texts.append(f'<text x="{xi:.0f}" y="{cy + 5:.0f}" font-size="17" '
                     f'font-weight="bold">{lab}</text>')
        texts.append(f'<text x="{xi:.0f}" y="{cy + max(radii) + 24:.0f}" '
                     f'font-size="14">{t} ฟัน</text>')
    labels_g = (f'<g fill="currentColor" text-anchor="middle" '
                f'font-family="system-ui, sans-serif">{"".join(texts)}</g>')

    return (f'<svg viewBox="0 0 {w:.0f} {h:.0f}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img">{shapes}{labels_g}</svg>')


def describe(v: dict) -> str:
    pairs = ", ".join(f"เฟือง {lab} มี {t} ฟัน"
                      for lab, t in zip(v["labels"], v["teeth"]))
    return (f"ระบบเฟือง {len(v['teeth'])} ตัวขบกันเรียงเป็นแถว {pairs} "
            f"· รัศมีในรูปสัมพันธ์กับจำนวนฟัน")


def build(params: dict, vals: dict) -> dict:
    teeth, labels = vals["teeth"], vals["labels"]
    rpm_in, dir_in = vals["rpm_in"], vals["dir_in"]
    n = len(teeth)
    meshes = n - 1
    dir_out = dir_in if meshes % 2 == 0 else _opp(dir_in)
    rpm_out = rpm_in * teeth[0] / teeth[-1]

    cands = _candidates(vals)
    answer = cands[0][0]
    distractors = [{"value": val, "reason": why, "tag": tag}
                   for val, why, tag in cands[1:]]

    chain = " → ".join(labels)
    middle = labels[1:-1]
    faster = "เร็วขึ้น" if rpm_out > rpm_in else "ช้าลง"

    steps = [
        {"do_md": f"นับจำนวนครั้งที่เฟืองขบกัน: เฟือง {n} ตัวเรียง {chain} "
                  f"จึงขบกัน {meshes} ครั้ง",
         "why_md": "ทิศสลับที่การขบ ไม่ใช่ที่ตัวเฟือง ถ้านับจำนวนเฟืองแทนจะได้ทิศผิด"},
        {"do_md": f"เฟือง {labels[0]} หมุน{dir_in} ขบกัน {meshes} ครั้ง "
                  f"({'คู่' if meshes % 2 == 0 else 'คี่'}) "
                  f"เฟือง {labels[-1]} จึงหมุน{dir_out}",
         "why_md": "ขบกันจำนวนคู่ได้ทิศเดิม ขบกันจำนวนคี่ได้ทิศสวนทาง"},
        {"do_md": f"หาความเร็ว: รอบต่อนาทีแปรผกผันกับจำนวนฟัน "
                  f"จึงได้ {rpm_in} x {teeth[0]} ÷ {teeth[-1]} = {_fmt(rpm_out)} รอบต่อนาที",
         "why_md": (f"ใช้เฉพาะจำนวนฟันของ {labels[0]} กับ {labels[-1]} "
                    f"เพราะเฟือง {', '.join(middle)} ที่อยู่ระหว่างกลางไม่มีผลต่ออัตราทด "
                    "มีผลแค่ทิศ" if middle else
                    "เฟืองสองตัวขบกันโดยตรง อัตราทดจึงมาจากจำนวนฟันของทั้งคู่")},
        {"do_md": f"ตรวจความสมเหตุสมผล: {labels[-1]} มีฟัน {teeth[-1]} "
                  f"{'น้อยกว่า' if teeth[-1] < teeth[0] else 'มากกว่า'} "
                  f"{labels[0]} ที่มี {teeth[0]} จึงต้องหมุน{faster} ซึ่งตรงกับคำตอบ",
         "why_md": "เฟืองเล็กหมุนเร็วกว่าเฟืองใหญ่ ใช้ตรวจทิศทางของคำตอบได้ในสามวินาที"},
    ]

    hints = [
        f"แยกคิดสองเรื่อง: ทิศการหมุน และรอบต่อนาที เริ่มจากนับว่าเฟืองขบกันกี่ครั้ง",
        "เฟืองที่ขบกันหมุนสวนทางกันเสมอ จึงสลับทิศทุกครั้งที่ขบ ไม่ใช่ทุกตัวเฟือง",
        ("รอบต่อนาทีแปรผกผันกับจำนวนฟัน และขึ้นกับเฟืองตัวแรกกับตัวสุดท้ายเท่านั้น "
         "เฟืองที่อยู่ระหว่างกลางไม่มีผลต่อความเร็ว"),
    ]

    explanation = (
        f"เฟืองขบกัน {meshes} ครั้ง จึงสลับทิศ {meshes} ครั้ง "
        f"ทำให้เฟือง {labels[-1]} หมุน{dir_out} "
        f"ส่วนความเร็วคิดจากจำนวนฟันของ {labels[0]} กับ {labels[-1]} เท่านั้น "
        f"ได้ {rpm_in} x {teeth[0]} ÷ {teeth[-1]} = {_fmt(rpm_out)} รอบต่อนาที "
        f"จึงตอบ {answer}"
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
            "svg": gear_svg(vals),
            "caption": None,
        }],
        "meta": {"meshes": meshes, "ratio": f"{teeth[0]}:{teeth[-1]}",
                 "dir_out": dir_out, "rpm_out": rpm_out},
    }
