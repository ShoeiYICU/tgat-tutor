"""provider: cube_net.opposite_pair — ถามว่าข้อใดเป็น "คู่หน้าตรงข้าม"

ต่างจาก cube_net.opposite_face ตรงที่ไม่ได้ชี้หน้าให้ ผู้สอบต้องหาคู่เอง
จึงแพงกว่าในเชิงความคิด: ต้องไล่จับคู่จนครบสามคู่ก่อนจะกล้าตอบ

ตัวเลือกลวงคือ "คู่ที่ติดกันบนลูกบาศก์" ซึ่งมีอยู่ 12 คู่พอดี (6 หน้า จับคู่ได้ 15 คู่
หักคู่ตรงข้าม 3 คู่) — เลือกมา 4 คู่ ทุกคู่เป็นคำตอบที่นักเรียนเลือกจริงถ้าจับคู่ผิด

พารามิเตอร์
    nets              list[str]   ชื่อแผ่นคลี่จาก cube_net.NETS (บังคับ)
    skip_rule_applies bool|null   คุมความยากของคู่ที่เป็นคำตอบ
                                  true  = คู่ที่หาได้ด้วยกฎเว้นหนึ่งช่อง
                                  false = คู่ที่กฎเว้นหนึ่งช่องใช้ไม่ได้ (ต้องจับคู่ที่เหลือ)
                                  null  = ไม่จำกัด
    orient            bool        true = สุ่มการวางแผ่นคลี่ด้วย (หมุน/พลิก แล้วใส่ตัวอักษรใหม่
                                  ตามลำดับการอ่าน) รูปทรงเดิม ความยากเท่าเดิม
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import cube_net as CN  # noqa: E402
from providers.cube_net_opposite import _placements, _relation, cells_of  # noqa: E402

NAME = "cube_net.opposite_pair"
DOC = "ข้อใดเป็นคู่หน้าตรงข้ามกัน — ต้องจับคู่ให้ครบก่อนตอบ เฉลยคำนวณจากการพับด้วยโค้ด"
ANSWER_KIND = "text"

VAR_NAMES = ["net", "orient", "correct", "wrong"]

# จำนวนตัวเลือกลวงต่อข้อ — ให้รวมเป็น 5 ตัวเลือกตามรูปแบบ TGAT2
N_WRONG = 4


def _label(pair) -> str:
    """แสดงคู่หน้าเป็นข้อความที่ใช้ในตัวเลือก"""
    a, b = pair
    return f"{a} กับ {b}"


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

    sra = params.get("skip_rule_applies")
    if sra is not None and not isinstance(sra, bool):
        bad.append("skip_rule_applies ต้องเป็น true, false หรือไม่ใส่")

    orient = params.get("orient")
    if orient is not None and not isinstance(orient, bool):
        bad.append("orient ต้องเป็น true, false หรือไม่ใส่")

    if not bad:
        cases = _all_cases(params)
        if not cases:
            bad.append("พารามิเตอร์ชุดนี้ไม่มีคู่ที่ใช้เป็นคำตอบได้เลย "
                       "(nets กับ skip_rule_applies ขัดกันเอง)")
        else:
            # ต้องมีคู่ที่ติดกันพอจะทำตัวเลือกลวงครบ
            for name, oi, _pair in cases:
                res = CN.solve_net(cells_of(name, oi))
                if len(res["adjacent"]) < N_WRONG:
                    bad.append(f"แผ่นคลี่ {name!r} มีคู่ที่ติดกันแค่ {len(res['adjacent'])} คู่ "
                               f"ทำตัวเลือกลวงไม่ครบ {N_WRONG} ตัว")
    return bad


def var_names(params: dict) -> list[str]:
    return list(VAR_NAMES)


def _all_cases(params: dict) -> list[tuple[str, tuple]]:
    """คืนชุด (ชื่อแผ่นคลี่, คู่ที่เป็นคำตอบ) ทั้งหมดที่ผ่านพารามิเตอร์"""
    out: list[tuple[str, int, tuple]] = []
    want_skip = params.get("skip_rule_applies")
    for name in params.get("nets") or []:
        if name not in CN.NETS:
            continue
        places = _placements(name) if params.get("orient") else [CN.NETS[name]]
        for oi, cells in enumerate(places):
            res = CN.solve_net(cells)
            if not res["valid"]:
                continue
            skip = CN.skip_one_pairs(cells)
            for pair in res["pairs"]:
                if want_skip is not None and (frozenset(pair) in skip) != want_skip:
                    continue
                out.append((name, oi, tuple(pair)))
    return out


def draw(params: dict, rng) -> dict | None:
    cases = _all_cases(params)
    if not cases:
        return None
    name, oi, pair = rng.choice(cases)
    cells = cells_of(name, oi)
    res = CN.solve_net(cells)
    # ตัวเลือกลวงสุ่มจากคู่ที่ติดกัน โดยเรียงให้ผลซ้ำได้เมื่อ seed เดิม
    adjacent = sorted(tuple(sorted(p)) for p in res["adjacent"])
    if len(adjacent) < N_WRONG:
        return None
    wrong = rng.sample(adjacent, N_WRONG)
    return {
        "net": name,
        "orient": oi,
        "correct": "".join(pair),
        "wrong": ["".join(w) for w in wrong],
    }


def _explain_pair(cells, correct: tuple, wrong: list, res: dict, skip: set) -> dict:
    """เขียนวิธีคิดของโจทย์แบบถามคู่ — วิธีที่เร็วที่สุดคือตัดตัวเลือกที่ติดกันทิ้ง

    ไม่ได้ให้ไล่จับคู่ทั้งสามคู่ก่อน เพราะในห้องสอบการตัดตัวเลือกเร็วกว่า
    """
    touching = CN.touching_pairs(cells)
    a, b = correct
    via_skip = frozenset(correct) in skip
    between = CN.between_label(cells, a, b) if via_skip else None
    line = CN.same_line(cells, a, b)
    pairs_txt = " , ".join(f"{x}-{y}" for x, y in res["pairs"])

    shared = [f"{x} กับ {y}" for x, y in wrong if frozenset((x, y)) in touching]
    diag = [f"{x} กับ {y}" for x, y in wrong if frozenset((x, y)) not in touching]

    steps = [{
        "do_md": "ไล่ตัวเลือกทีละข้อ ตัดคู่ที่แชร์ขอบกันในแผ่นคลี่ออกก่อน"
                 + (f" ได้แก่ {', '.join(shared)}" if shared else ""),
        "why_md": "คู่ที่แชร์ขอบกันพับแล้วทำมุม 90 องศา คือติดกัน จึงเป็นคำตอบไม่ได้ "
                  "ขั้นนี้มักตัดได้ครึ่งหนึ่งของตัวเลือก",
    }]
    if diag:
        steps.append({
            "do_md": f"ตัดคู่ที่เหลือซึ่งอยู่เฉียงกันหรืออยู่ห่างกันแต่ยังติดกันบนลูกบาศก์ "
                     f"ได้แก่ {', '.join(diag)}",
            "why_md": "คู่ที่อยู่เฉียงกันแบบรูปตัวแอลพับแล้วติดกัน นักเรียนมักคิดว่าไม่ติดกัน "
                      "เพราะไม่ได้แชร์ขอบ",
        })
    if via_skip:
        steps.append({
            "do_md": f"เหลือ {a} กับ {b} — ยืนยันด้วยกฎเว้นหนึ่งช่อง: "
                     f"ทั้งสองอยู่{line}เดียวกันและเว้นช่อง {between} อยู่หนึ่งช่อง",
            "why_md": "สองหน้าที่อยู่แนวเดียวกันและเว้นกันหนึ่งช่อง พับแล้วหันหลังชนกันพอดี",
        })
    else:
        steps.append({
            "do_md": f"เหลือ {a} กับ {b} — แผ่นคลี่นี้ใช้กฎเว้นหนึ่งช่องไม่ได้ "
                     f"ต้องไล่จับคู่ให้ครบ ได้ {pairs_txt}",
            "why_md": "แผ่นคลี่แบบขั้นบันไดไม่มีคู่ใดอยู่แนวเดียวกันเลย จึงต้องพับไล่ทีละหน้า "
                      "หรือใช้วิธีตัดตัวเลือกอย่างเดียว",
        })
    steps.append({
        "do_md": f"ตรวจ: คู่ทั้งสามคือ {pairs_txt} ทุกหน้าโผล่ครั้งเดียว",
        "why_md": "ถ้ามีหน้าใดโผล่สองคู่หรือมีหน้าที่ไม่มีคู่ แปลว่าคิดผิด",
    })

    hints = [
        "ข้อนี้ตัดตัวเลือกเร็วกว่าไล่จับคู่ ให้ดูว่าคู่ในตัวเลือกใดแชร์ขอบกันในแผ่นคลี่",
        "คู่ที่อยู่เฉียงกันแบบรูปตัวแอลก็ติดกันบนลูกบาศก์ ตัดทิ้งได้ด้วย",
        ("คู่ที่ถูกต้องจะอยู่แถวหรือคอลัมน์เดียวกันและเว้นกันหนึ่งช่อง"
         if via_skip else
         "แผ่นคลี่นี้ไม่มีคู่ใดเว้นหนึ่งช่องเลย ต้องใช้วิธีตัดตัวเลือกให้หมดจนเหลือข้อเดียว"),
    ]

    explanation = (f"คู่ตรงข้ามของแผ่นคลี่นี้คือ {pairs_txt} "
                   f"ซึ่งครบหกหน้าและแต่ละหน้าอยู่คู่เดียว จึงตอบ {_label(correct)}")
    return {"steps": steps, "hints": hints, "explanation": explanation}


def build(params: dict, vals: dict) -> dict:
    name = vals["net"]
    cells = cells_of(name, vals.get("orient", 0))
    res = CN.solve_net(cells)
    if not res["valid"]:
        raise ValueError(f"แผ่นคลี่ {name!r} พับไม่ได้: {res['error']}")

    correct = tuple(vals["correct"])
    if frozenset(correct) not in {frozenset(p) for p in res["pairs"]}:
        raise ValueError(f"คู่ {vals['correct']!r} ไม่ใช่คู่ตรงข้ามของแผ่นคลี่ {name!r}")

    distractors = []
    for w in vals["wrong"]:
        a, b = tuple(w)
        if frozenset((a, b)) not in res["adjacent"]:
            raise ValueError(f"คู่ลวง {w!r} ไม่ได้ติดกันบนลูกบาศก์ — อาจเป็นคู่ตรงข้ามจริง")
        reason, tag = _relation(cells, a, b)
        distractors.append({"value": _label((a, b)), "reason": reason, "tag": tag})

    skip = CN.skip_one_pairs(cells)
    explained = _explain_pair(cells, correct, [tuple(w) for w in vals["wrong"]], res, skip)

    return {
        "answer": _label(correct),
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
        "meta": {
            "net": name,
            "orient": vals.get("orient", 0),
            "pairs": res["pairs"],
            "found_by_skip_rule": frozenset(correct) in skip,
        },
    }
