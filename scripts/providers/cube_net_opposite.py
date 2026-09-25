"""provider: cube_net.opposite_face — ถามว่าหน้าใดอยู่ตรงข้ามกับหน้าที่กำหนด

คำตอบและตัวเลือกลวงมาจากการ **พับแผ่นคลี่จริงด้วยโค้ด** ใน cube_net.py
ไม่ใช่การพับในหัว จึงไม่มีทางที่โจทย์จะไม่มีคำตอบหรือมีคำตอบสองตัว

ตัวเลือกลวงได้มาฟรีจากโครงของปัญหา: ลูกบาศก์มี 6 หน้า ตัดหน้าที่ถาม
และหน้าตรงข้ามออก เหลือ 4 หน้าที่ "ติดกัน" พอดี — ครบ mcq5 โดยไม่ต้องคิดเพิ่ม
และทุกตัวเป็นตัวเลือกที่นักเรียนเลือกจริงถ้าใช้กฎผิด

เหตุผลของตัวเลือกลวงก็คำนวณจากตำแหน่งในแผ่นคลี่ ไม่ได้เขียนมือ:
แชร์ขอบ / เฉียงกันแบบรูปตัวแอล / หัวท้ายแถวสี่ช่อง / อยู่ไกลกันแต่ยังติดกัน

พารามิเตอร์
    nets              list[str]   ชื่อแผ่นคลี่จาก cube_net.NETS (บังคับ)
    ask_faces         list[str]   จำกัดว่าจะถามหน้าไหนได้ (ไม่บังคับ)
    skip_rule_applies bool|null   คุมความยาก
                                  true  = สุ่มเฉพาะคู่ที่หาได้ด้วยกฎเว้นหนึ่งช่อง (ง่าย)
                                  false = สุ่มเฉพาะคู่ที่กฎเว้นหนึ่งช่องใช้ไม่ได้
                                          บังคับให้ต้องตัดตัวเลือกแล้วจับคู่ที่เหลือ (ยาก)
                                  null  = ไม่จำกัด
    orient            bool        true = สุ่มการวางแผ่นคลี่ด้วย (หมุน/พลิก แล้วใส่ตัวอักษร
                                  ใหม่ตามลำดับการอ่าน) ได้โจทย์ที่ต่างกันในสายตาผู้สอบ
                                  แต่รูปทรงเดิม ความยากจึงเท่าเดิม
                                  ท่าที่ 0 คือท่าเดิมตามที่เขียนไว้ใน NETS เสมอ
    touching_count    int|null    จำนวนหน้าที่แชร์ขอบกับหน้าที่ถาม "ในแผ่นคลี่"
                                  นี่คือจำนวนตัวเลือกที่ตัดทิ้งได้ในขั้นแรก
                                  4 = ตัดได้ 4 ตัวเหลือคำตอบตัวเดียว จบในขั้นเดียว (ง่ายสุด)
                                  1 = ตัดได้แค่ตัวเดียว ต้องใช้กฎอื่นต่อ (ยากขึ้น)
                                  ใช้คุมให้โจทย์ที่สุ่มใหม่มีจำนวนขั้นเท่าเดิมกับข้อที่เขียนไว้
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import cube_net as CN  # noqa: E402

NAME = "cube_net.opposite_face"
DOC = "หน้าใดอยู่ตรงข้ามกับหน้าที่กำหนด — เฉลยและรูปคำนวณจากการพับแผ่นคลี่ด้วยโค้ด"
ANSWER_KIND = "label"

# ชื่อค่าที่ draw() คืน ใช้อ้างใน stem_tpl ได้
VAR_NAMES = ["net", "orient", "asked"]


def _placements(name: str) -> list:
    """คืนการวางทุกท่าของแผ่นคลี่ ท่าที่ 0 คือท่าเดิมตามที่เขียนไว้ใน NETS"""
    cells = CN.NETS[name]
    out = [cells]
    for o in CN.orientations(cells):
        if o != cells:
            out.append(o)
    return out


def cells_of(name: str, orient: int) -> list:
    places = _placements(name)
    if not 0 <= orient < len(places):
        raise ValueError(f"แผ่นคลี่ {name!r} ไม่มีท่าที่ {orient} (มี {len(places)} ท่า)")
    return places[orient]


def validate_params(params: dict) -> list[str]:
    bad: list[str] = []
    if not isinstance(params, dict):
        return ["params ต้องเป็นอ็อบเจกต์"]

    nets = params.get("nets")
    if not isinstance(nets, list) or not nets:
        bad.append("ต้องมี nets เป็นอาร์เรย์ชื่อแผ่นคลี่อย่างน้อย 1 ชื่อ")
    else:
        for n in nets:
            if n not in CN.NETS:
                bad.append(f"ไม่รู้จักแผ่นคลี่ {n!r} — ที่มีคือ {', '.join(sorted(CN.NETS))}")

    faces = params.get("ask_faces")
    if faces is not None:
        if not isinstance(faces, list) or not faces:
            bad.append("ask_faces ต้องเป็นอาร์เรย์ที่มีสมาชิก หรือไม่ต้องใส่เลย")
        elif isinstance(nets, list):
            for n in nets:
                if n in CN.NETS:
                    have = {lab for cells in _placements(n) for _, _, lab in cells}
                    for f in faces:
                        if f not in have:
                            bad.append(f"แผ่นคลี่ {n!r} ไม่มีหน้า {f!r} ในท่าใดเลย")

    sra = params.get("skip_rule_applies")
    if sra is not None and not isinstance(sra, bool):
        bad.append("skip_rule_applies ต้องเป็น true, false หรือไม่ใส่")

    orient = params.get("orient")
    if orient is not None and not isinstance(orient, bool):
        bad.append("orient ต้องเป็น true, false หรือไม่ใส่")

    tc = params.get("touching_count")
    if tc is not None and not (isinstance(tc, int) and not isinstance(tc, bool) and 1 <= tc <= 4):
        bad.append(f"touching_count ต้องเป็นจำนวนเต็ม 1-4 หรือไม่ใส่ (พบ {tc!r})")

    # ตรวจว่ามีชุดค่าที่ใช้ได้จริงอย่างน้อยหนึ่งชุด — กันพารามิเตอร์ที่ขัดกันเอง
    if not bad and not _all_cases(params):
        bad.append("พารามิเตอร์ชุดนี้ไม่มีชุดค่าที่ใช้ได้เลย "
                   "(nets, ask_faces และ skip_rule_applies ขัดกันเอง)")
    return bad


def var_names(params: dict) -> list[str]:
    return list(VAR_NAMES)


def _all_cases(params: dict) -> list[tuple[str, str]]:
    """คืนชุด (ชื่อแผ่นคลี่, หน้าที่ถาม) ทั้งหมดที่ผ่านพารามิเตอร์

    คำนวณจากการพับจริง จึงรู้ล่วงหน้าว่าโจทย์ที่เป็นไปได้มีกี่แบบ
    """
    out: list[tuple[str, int, str]] = []
    want_skip = params.get("skip_rule_applies")
    want_touch = params.get("touching_count")
    only = params.get("ask_faces")
    for name in params.get("nets") or []:
        if name not in CN.NETS:
            continue
        places = _placements(name) if params.get("orient") else [CN.NETS[name]]
        for oi, cells in enumerate(places):
            res = CN.solve_net(cells)
            if not res["valid"]:
                continue
            skip = CN.skip_one_pairs(cells)
            touching = CN.touching_pairs(cells)
            for a, b in res["pairs"]:
                for asked in (a, b):
                    if only is not None and asked not in only:
                        continue
                    if want_skip is not None:
                        if (frozenset((a, b)) in skip) != want_skip:
                            continue
                    if want_touch is not None:
                        n_touch = sum(1 for p in touching if asked in p)
                        if n_touch != want_touch:
                            continue
                    out.append((name, oi, asked))
    return out


def draw(params: dict, rng) -> dict | None:
    cases = _all_cases(params)
    if not cases:
        return None
    name, oi, asked = rng.choice(cases)
    return {"net": name, "orient": oi, "asked": asked}


# ---------------------------------------------------------------- เหตุผลตัวลวง

def _relation(cells, a: str, b: str) -> tuple[str, str]:
    """คืน (ข้อความเหตุผล, misconception tag) ของหน้า b เทียบกับหน้าที่ถาม a

    จำแนกจากตำแหน่งในแผ่นคลี่ ไม่ได้เขียนมือ
    """
    loc = {lab: (c, r) for c, r, lab in cells}
    (ca, ra), (cb, rb) = loc[a], loc[b]
    dc, dr = abs(ca - cb), abs(ra - rb)

    if dc + dr == 1:
        return (f"หน้า {b} แชร์ขอบกับหน้า {a} ในแผ่นคลี่ พับแล้วทำมุมกัน 90 องศา "
                f"จึงติดกัน ไม่ใช่คู่ตรงข้าม", "adjacent_in_net")
    if dc == 1 and dr == 1:
        return (f"หน้า {b} อยู่เฉียงกับหน้า {a} แบบรูปตัวแอล ซึ่งพับแล้วติดกัน "
                f"นักเรียนมักคิดว่าไม่ติดกันเพราะไม่ได้แชร์ขอบ", "diagonal_looks_far")
    if (dc == 3 and dr == 0) or (dr == 3 and dc == 0):
        return (f"หน้า {b} อยู่หัวท้ายแถวเดียวกันกับหน้า {a} ห่างกันสามช่อง "
                f"นักเรียนมักคิดว่าไกลสุดคือตรงข้าม แต่ห่างสามช่องพับมาชนกันพอดี",
                "farthest_means_opposite")
    return (f"หน้า {b} อยู่คนละแถวคนละคอลัมน์กับหน้า {a} จึงดูเหมือนไม่เกี่ยวกัน "
            f"แต่พับแล้วยังแชร์ขอบกัน", "different_row_and_column")


def _explain(cells, asked: str, answer: str, others: list, res: dict) -> dict:
    """เขียนวิธีคิด คำใบ้ และคำอธิบายคำตอบ จากผลการพับ

    ทุกบรรทัดสร้างจากสิ่งที่คำนวณได้จริง ไม่ใช่ข้อความสำเร็จรูปที่เดาว่าน่าจะถูก
    จึงตรงกับแผ่นคลี่ที่สุ่มมาเสมอ
    """
    touching = CN.touching_pairs(cells)
    skip = CN.skip_one_pairs(cells)
    cut = [lab for lab in others if frozenset((asked, lab)) in touching]
    left = [lab for lab in others if lab not in cut] + [answer]
    via_skip = frozenset((asked, answer)) in skip
    between = CN.between_label(cells, asked, answer) if via_skip else None
    line = CN.same_line(cells, asked, answer)
    pairs_txt = " , ".join(f"{a}-{b}" for a, b in res["pairs"])

    steps = [{
        "do_md": f"ตัดหน้าที่แชร์ขอบกับหน้า {asked} ในแผ่นคลี่ออกก่อน ได้ {', '.join(cut)}",
        "why_md": "หน้าที่แชร์ขอบกันพับแล้วทำมุม 90 องศา คือติดกัน จึงไม่ตรงข้ามกันแน่นอน",
    }]

    if len(left) == 1:
        steps.append({
            "do_md": f"เหลือ {answer} ตัวเดียว จึงตอบ {answer}",
            "why_md": "เมื่อตัดจนเหลือหน้าเดียวก็สรุปได้เลย ไม่ต้องใช้กฎอื่น",
        })
    elif via_skip:
        steps.append({
            "do_md": f"ยังเหลือ {', '.join(left)} — ดู{line}ที่มีหน้า {asked} อยู่ "
                     f"พบว่า {asked} กับ {answer} เว้นช่อง {between} อยู่หนึ่งช่อง",
            "why_md": "สองหน้าที่อยู่แนวเดียวกันและเว้นกันหนึ่งช่อง พับแล้วหันหลังชนกันพอดี "
                      "จึงเป็นคู่ตรงข้ามกันเสมอ",
        })
        steps.append({
            "do_md": f"จึงตอบ {answer}",
            "why_md": "กฎเว้นหนึ่งช่องชี้คู่ได้ตรง ๆ ไม่ต้องไล่จับคู่ที่เหลือ",
        })
    else:
        other_pairs = [f"{a}-{b}" for a, b in res["pairs"] if asked not in (a, b)]
        steps.append({
            "do_md": f"กฎเว้นหนึ่งช่องใช้กับหน้า {asked} ไม่ได้ เพราะไม่มีหน้าใดอยู่แนวเดียวกัน "
                     f"แล้วเว้นกันหนึ่งช่อง — ให้หาคู่อื่นให้ครบก่อน ได้ {' และ '.join(other_pairs)}",
            "why_md": "เมื่อกฎที่เร็วที่สุดใช้ไม่ได้ ให้เปลี่ยนไปหาคู่ที่หาง่ายกว่าก่อน "
                      "แล้วค่อยใช้ส่วนที่เหลือ",
        })
        steps.append({
            "do_md": f"ใช้สองคู่นั้นไปแล้วสี่หน้า เหลือ {asked} กับ {answer} จึงเป็นคู่กัน "
                     f"ตอบ {answer}",
            "why_md": "ลูกบาศก์มีคู่ตรงข้ามสามคู่พอดีและทุกหน้าอยู่คู่เดียว "
                      "ดังนั้นสองหน้าที่เหลือต้องจับคู่กันเอง",
        })

    steps.append({
        "do_md": f"ตรวจ: คู่ทั้งสามคือ {pairs_txt} ทุกหน้าโผล่ครั้งเดียว",
        "why_md": "ถ้ามีหน้าใดโผล่สองคู่หรือมีหน้าที่ไม่มีคู่ แปลว่าคิดผิด ขั้นนี้ใช้เวลา 3 วินาที",
    })

    hints = [
        f"เริ่มจากตัดหน้าที่แชร์ขอบกับหน้า {asked} ในแผ่นคลี่ออก เพราะหน้าที่ติดกันไม่ตรงข้ามกัน",
        (f"ดู{line}ที่มีหน้า {asked} อยู่ ว่ามีหน้าใดอยู่แนวเดียวกันแล้วเว้นกันหนึ่งช่อง"
         if via_skip else
         f"กฎเว้นหนึ่งช่องใช้กับหน้า {asked} ไม่ได้ ให้หาคู่ตรงข้ามคู่อื่นให้ครบก่อน"),
        ("อย่าลืมว่าหน้าที่อยู่เฉียงกันแบบรูปตัวแอลก็ติดกัน จึงตัดทิ้งได้ด้วย"
         if len(left) > 1 else
         "ตัดครบแล้วเหลือกี่หน้า ถ้าเหลือหน้าเดียวก็คือคำตอบ"),
    ]

    explanation = (f"คู่ตรงข้ามของแผ่นคลี่นี้คือ {pairs_txt} "
                   f"ซึ่งครบหกหน้าและแต่ละหน้าอยู่คู่เดียว จึงตอบหน้า {answer}")
    return {"steps": steps, "hints": hints, "explanation": explanation}


def build(params: dict, vals: dict) -> dict:
    name = vals["net"]
    asked = vals["asked"]
    cells = cells_of(name, vals.get("orient", 0))
    res = CN.solve_net(cells)
    if not res["valid"]:
        raise ValueError(f"แผ่นคลี่ {name!r} พับไม่ได้: {res['error']}")

    answer = CN.opposite_of(cells, asked)
    others = [lab for _, _, lab in cells if lab not in (asked, answer)]
    if len(others) != 4:
        raise ValueError(f"เหลือหน้าที่ติดกัน {len(others)} หน้า ควรได้ 4 หน้าพอดี")

    distractors = []
    for lab in others:
        reason, tag = _relation(cells, asked, lab)
        distractors.append({"value": lab, "reason": reason, "tag": tag})

    skip = CN.skip_one_pairs(cells)
    via_skip = frozenset((asked, answer)) in skip
    between = CN.between_label(cells, asked, answer) if via_skip else None

    explained = _explain(cells, asked, answer, others, res)

    return {
        "answer": answer,
        "distractors": distractors,
        "steps": explained["steps"],
        "hints": explained["hints"],
        "explanation": explained["explanation"],
        "figures": [{
            "id": "fig1",
            "type": "svg",
            "alt": CN.describe(cells),
            "svg": CN.net_svg(cells),
            "caption": None,
        }],
        # ข้อมูลเพิ่มให้ตัวสร้างเฉลยใช้ ไม่ใช่ส่วนของสัญญา
        "meta": {
            "net": name,
            "orient": vals.get("orient", 0),
            "pairs": res["pairs"],
            "found_by_skip_rule": via_skip,
            "between": between,
        },
    }
