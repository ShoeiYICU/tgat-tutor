"""provider 3 ตัวสำหรับโจทย์มิติสัมพันธ์สองมิติของ TGAT2

    shape2d.rotate_match          รูปใดคือภาพหมุนของรูปต้นแบบ
    shape2d.odd_one_out           รูปใดต่างจากพวก (โหมดหมุน / โหมดสะท้อน)
    shape2d.rotation_or_reflection  คู่นี้เป็นภาพหมุนหรือภาพสะท้อน

ทั้งสามตัวใช้เครื่องมือกลางใน scripts/shape2d.py ซึ่งคำนวณการหมุนและการสะท้อนจริง
แล้วเทียบด้วยรูปแบบมาตรฐาน จึงไม่มีทางที่เฉลยจะผิด

## จุดที่โจทย์ชุดนี้วัด

**ภาพหมุนกับภาพสะท้อนต่างกัน** รูปที่สะท้อนแล้วจะไม่มีทางหมุนให้ทับรูปเดิมได้
(สำหรับรูปที่ไม่สมมาตร) ผู้สอบส่วนใหญ่แยกสองอย่างนี้ไม่ออก จึงเป็นกับดักหลัก

เครื่องมือกลางคัดเฉพาะรูปที่ **หมุนได้ 4 ภาพต่างกัน และสะท้อนแล้วต่างจากทั้งสี่**
จึงมีภาพต่างกันครบ 8 แบบเสมอ ทำให้สร้างตัวเลือกที่ไม่ซ้ำกันได้แน่นอน
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import shape2d as S2  # noqa: E402

ANGLE = {0: "0 องศา", 1: "90 องศา", 2: "180 องศา", 3: "270 องศา"}


def _common_params(params: dict) -> list[str]:
    bad = []
    n = params.get("n_cells")
    if not (isinstance(n, int) and not isinstance(n, bool) and 4 <= n <= 7):
        bad.append(f"n_cells ต้องเป็นจำนวนเต็ม 4-7 (พบ {n!r})")
    b = params.get("box")
    if not (isinstance(b, int) and not isinstance(b, bool) and 3 <= b <= 5):
        bad.append(f"box ต้องเป็นจำนวนเต็ม 3-5 (พบ {b!r})")
    if not bad and params["n_cells"] > params["box"] ** 2 - 2:
        bad.append("n_cells มากเกินไปเมื่อเทียบกับ box จนหารูปที่ไม่สมมาตรแทบไม่ได้")
    return bad


def _fig(fid, cells, box, caption=None):
    return {"id": fid, "type": "svg", "alt": S2.describe(cells),
            "svg": S2.shape_svg(cells, box=box), "caption": caption}


# ================================================================ 1. หมุนให้ตรง

class _RotateMatch:
    NAME = "shape2d.rotate_match"
    DOC = "รูปใดคือภาพที่หมุนมาจากรูปต้นแบบ — คำนวณการหมุนจริงด้วยโค้ด"
    ANSWER_KIND = "text"
    VAR_NAMES = ["cells", "turns", "box", "angle_text"]

    @staticmethod
    def validate_params(params):
        if not isinstance(params, dict):
            return ["params ต้องเป็นอ็อบเจกต์"]
        bad = _common_params(params)
        t = params.get("turns")
        if t is not None and t not in (1, 2, 3):
            bad.append("turns ต้องเป็น 1 (90 องศา), 2 (180 องศา), 3 (270 องศา) หรือไม่ใส่")
        return bad

    @staticmethod
    def var_names(params):
        return list(_RotateMatch.VAR_NAMES)

    @staticmethod
    def draw(params, rng):
        shape = S2.random_shape(rng, params["n_cells"], params["box"])
        if shape is None:
            return None
        turns = params.get("turns") or rng.choice([1, 2, 3])
        return {"cells": sorted(shape), "turns": turns, "box": params["box"],
                "angle_text": ANGLE[turns]}

    @staticmethod
    def build(params, vals):
        base = S2.normalize(tuple(map(tuple, vals["cells"])))
        turns, box = vals["turns"], vals["box"]
        rots = S2.rotations(base)
        refs = S2.reflections(base)
        answer = rots[turns]

        # ตัวลวง: ภาพสะท้อนที่มุมเดียวกัน กับภาพหมุนมุมอื่น
        picks = [
            (refs[turns],
             f"เป็นภาพ**สะท้อน**ที่หมุนไปมุมเดียวกัน ไม่ใช่ภาพหมุน "
             f"รูปที่สะท้อนแล้วจะหมุนให้ทับรูปเดิมไม่ได้",
             "reflection_not_rotation"),
            (rots[(turns + 1) % 4],
             f"หมุนเกินไปอีกหนึ่งมุม เป็นภาพหมุน {ANGLE[(turns + 1) % 4]} "
             f"ไม่ใช่ {ANGLE[turns]}",
             "over_rotated"),
            (rots[(turns - 1) % 4],
             f"หมุนขาดไปหนึ่งมุม เป็นภาพหมุน {ANGLE[(turns - 1) % 4]} "
             f"ไม่ใช่ {ANGLE[turns]}",
             "under_rotated"),
            (refs[(turns + 2) % 4],
             "เป็นภาพสะท้อนที่หมุนไปคนละมุม ผิดทั้งสองอย่าง",
             "reflected_and_wrong_angle"),
        ]
        keys = [_key(answer)] + [_key(p[0]) for p in picks]
        if len(set(keys)) != 5:
            raise ValueError("ตัวเลือกซ้ำกัน")

        figures = [_fig("fig1", base, box, "รูปต้นแบบ")]
        answer_fig = "fig2"
        figures.append(_fig("fig2", answer, box))
        distractors = []
        for i, (cells, why, tag) in enumerate(picks):
            fid = f"fig{i + 3}"
            figures.append(_fig(fid, cells, box))
            distractors.append({"value": _key(cells), "reason": why,
                                "tag": tag, "fig": fid})

        steps = [
            {"do_md": f"หาจุดสังเกตของรูปต้นแบบ เช่นช่องที่ยื่นออกมาช่องเดียว "
                      f"แล้วดูว่าเมื่อหมุน {ANGLE[turns]} จุดนั้นควรไปอยู่ด้านใด",
             "why_md": "การจับจุดสังเกตหนึ่งจุดเร็วกว่าการไล่เทียบทั้งรูป "
                       "และตัดตัวเลือกได้ทีละหลายตัว"},
            {"do_md": "ตัดตัวเลือกที่เป็นภาพสะท้อนออกก่อน "
                      "โดยดูว่าลำดับของส่วนที่ยื่นออกสลับข้างหรือไม่",
             "why_md": "รูปที่ไม่สมมาตรเมื่อสะท้อนแล้วจะหมุนอย่างไรก็ไม่ทับรูปเดิม "
                       "นี่คือกับดักหลักของโจทย์ประเภทนี้"},
            {"do_md": f"เทียบตัวเลือกที่เหลือกับภาพหมุน {ANGLE[turns]} ของรูปต้นแบบ",
             "why_md": "เหลือไม่กี่ตัวแล้วจึงค่อยเทียบละเอียด ประหยัดเวลาในห้องสอบ"},
        ]
        hints = [
            "เลือกจุดสังเกตหนึ่งจุดในรูปต้นแบบก่อน อย่าพยายามเทียบทั้งรูปพร้อมกัน",
            "ตัดภาพสะท้อนออกก่อน ดูว่าลำดับของส่วนที่ยื่นออกสลับข้างหรือไม่",
            f"รูปต้นแบบหมุน {ANGLE[turns]} แล้วส่วนที่เคยอยู่ด้านบนจะไปอยู่ด้านใด",
        ]
        explanation = (
            f"ภาพหมุน {ANGLE[turns]} ของรูปต้นแบบคือรูปที่เลือก "
            "ตัวเลือกอื่นเป็นภาพสะท้อนหรือหมุนผิดมุม "
            "ข้อสังเกตสำคัญคือรูปที่ไม่สมมาตรเมื่อสะท้อนแล้วจะหมุนให้ทับรูปเดิมไม่ได้"
        )
        return {"answer": _key(answer), "answer_fig": answer_fig,
                "distractors": distractors, "steps": steps, "hints": hints,
                "explanation": explanation, "figures": figures,
                "meta": {"turns": turns}}


def _key(cells) -> str:
    """ข้อความมาตรฐานของรูป ใช้เทียบว่าตัวเลือกซ้ำกันไหม"""
    return " ".join(f"({c},{r})" for c, r in sorted(S2.normalize(cells)))


# ================================================================ 2. หาภาพต่าง

class _OddOneOut:
    NAME = "shape2d.odd_one_out"
    DOC = "รูปใดต่างจากพวก — อีกสี่รูปเป็นภาพหมุนของกันและกัน คำนวณด้วยโค้ด"
    ANSWER_KIND = "text"
    VAR_NAMES = ["cells", "box", "mode", "odd", "odd_slot"]

    @staticmethod
    def validate_params(params):
        if not isinstance(params, dict):
            return ["params ต้องเป็นอ็อบเจกต์"]
        bad = _common_params(params)
        m = params.get("mode")
        if m not in ("reflection", "altered"):
            bad.append('mode ต้องเป็น "reflection" (ตัวต่างเป็นภาพสะท้อน) '
                       'หรือ "altered" (ตัวต่างถูกย้ายช่องหนึ่งช่อง)')
        # โหมด altered ต้องมีรูปที่ใช้ได้ให้เลือกมากพอ
        # วัดแล้วพบว่ารูป 4 ช่องในกรอบ 3x3 มีที่ใช้ได้แค่ 2 แบบ (ตระกูลตัวแอลกับตระกูลตัวเอส)
        # ย้ายช่องหนึ่งช่องจึงวนกลับไปเป็นภาพหมุนหรือภาพสะท้อนของรูปเดิมทุกครั้ง
        if not bad and m == "altered":
            if params["n_cells"] < 5 or params["box"] < 4:
                bad.append("โหมด altered ต้องใช้ n_cells อย่างน้อย 5 และ box อย่างน้อย 4 "
                           "เพราะรูปที่เล็กกว่านั้นมีแบบที่ใช้ได้น้อยเกินไป "
                           "ย้ายช่องแล้ววนกลับไปเป็นภาพหมุนของรูปเดิมเสมอ")
        return bad

    @staticmethod
    def var_names(params):
        return list(_OddOneOut.VAR_NAMES)

    @staticmethod
    def draw(params, rng):
        shape = S2.random_shape(rng, params["n_cells"], params["box"])
        if shape is None:
            return None
        mode = params["mode"]
        rots = S2.rotations(shape)

        if mode == "reflection":
            odd = S2.reflections(shape)[rng.randrange(4)]
        else:
            odd = _move_one_cell(shape, rng)
            if odd is None:
                return None
            # ตัวต่างต้องไม่บังเอิญเป็นภาพหมุนหรือสะท้อนของรูปเดิม
            if odd in set(rots) | set(S2.reflections(shape)):
                return None

        return {"cells": sorted(shape), "box": params["box"], "mode": mode,
                "odd": sorted(odd), "odd_slot": rng.randrange(5)}

    @staticmethod
    def build(params, vals):
        shape = S2.normalize(tuple(map(tuple, vals["cells"])))
        odd = S2.normalize(tuple(map(tuple, vals["odd"])))
        box, mode, slot = vals["box"], vals["mode"], vals["odd_slot"]

        rots = S2.rotations(shape)
        group = [rots[0], rots[1], rots[2], rots[3]]
        items = group[:slot] + [odd] + group[slot:]
        if len({_key(x) for x in items}) != 5:
            raise ValueError("รูปในชุดซ้ำกัน")

        why_odd = ("เป็นภาพ**สะท้อน**ของอีกสี่รูป ไม่ใช่ภาพหมุน "
                   "จึงหมุนอย่างไรก็ไม่ทับกัน" if mode == "reflection" else
                   "มีช่องหนึ่งย้ายตำแหน่งไปจากรูปอื่น จึงไม่ใช่รูปเดียวกันตั้งแต่ต้น")

        figures, distractors = [], []
        answer_fig = None
        for i, cells in enumerate(items):
            fid = f"fig{i + 1}"
            figures.append(_fig(fid, cells, box))
            if cells == odd:
                answer_fig = fid
            else:
                # รูปต้นแบบ (หมุน 0 องศา) ไม่มีรูปอื่นในชุดที่เหมือนกันโดยไม่หมุน จึงบรรยายเป็นสมาชิกของกลุ่มแทน
                k = rots.index(cells)
                why = ("เป็นหนึ่งในสี่รูปที่หมุนแล้วทับกันได้พอดี" if k == 0
                       else f"เป็นภาพหมุน {ANGLE[k]} ของรูปอื่นในชุด")
                distractors.append({
                    "value": _key(cells),
                    "reason": f"{why} จึงอยู่พวกเดียวกัน ไม่ใช่รูปที่ต่าง",
                    "tag": "same_by_rotation", "fig": fid})

        steps = [
            {"do_md": "นับจำนวนช่องของทุกรูปก่อน ถ้ามีรูปที่จำนวนช่องต่างจากเพื่อน "
                      "ก็ตอบได้ทันที",
             "why_md": "เป็นการตัดที่เร็วที่สุดและใช้เวลาไม่ถึงห้าวินาที "
                       "ถ้าจำนวนเท่ากันหมดจึงค่อยดูรูปร่าง"},
            {"do_md": "เลือกจุดสังเกตหนึ่งจุด เช่นช่องที่ยื่นออกมาช่องเดียว "
                      "แล้วดูว่าช่องนั้นอยู่ด้านไหนเมื่อเทียบกับส่วนที่ยาวที่สุด",
             "why_md": "การหมุนไม่เปลี่ยนความสัมพันธ์ซ้ายขวาของสองส่วนนี้ "
                       "แต่การสะท้อนเปลี่ยน จึงใช้แยกได้"},
            {"do_md": f"รูปที่ต่างคือรูปที่{why_odd}",
             "why_md": "เมื่อเจอรูปที่ความสัมพันธ์สลับข้างจากเพื่อน ก็สรุปได้เลย"},
        ]
        hints = [
            "เริ่มจากนับจำนวนช่องของแต่ละรูป ถ้าเท่ากันหมดค่อยดูรูปร่าง",
            "เลือกจุดสังเกตจุดเดียว แล้วดูว่ามันอยู่ด้านไหนของส่วนที่ยาวที่สุด",
            "การหมุนไม่สลับซ้ายขวา แต่การสะท้อนสลับ ใช้ข้อนี้แยกรูปที่ต่างออกมา",
        ]
        explanation = (
            f"สี่รูปในชุดเป็นภาพหมุนของกันและกัน ส่วนรูปที่ตอบ{why_odd} "
            "หลักที่ใช้คือรูปที่ไม่สมมาตรเมื่อสะท้อนแล้วจะหมุนให้ทับรูปเดิมไม่ได้"
        )
        return {"answer": _key(odd), "answer_fig": answer_fig,
                "distractors": distractors, "steps": steps, "hints": hints,
                "explanation": explanation, "figures": figures,
                "meta": {"mode": mode}}


def _move_one_cell(shape, rng):
    """ย้ายช่องหนึ่งช่องไปติดที่อื่น ให้ยังต่อกันเป็นชิ้นเดียว"""
    cells = set(shape)
    for _ in range(60):
        drop = rng.choice(sorted(cells))
        rest = cells - {drop}
        if not rest or not _connected(rest):
            continue
        spots = set()
        for c, r in rest:
            for nb in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if nb not in rest:
                    spots.add(nb)
        spots.discard(drop)
        if not spots:
            continue
        cand = S2.normalize(rest | {rng.choice(sorted(spots))})
        if S2.usable(cand):
            return cand
    return None


def _connected(cells) -> bool:
    cells = set(cells)
    seen = {next(iter(cells))}
    stack = list(seen)
    while stack:
        c, r = stack.pop()
        for nb in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if nb in cells and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return seen == cells


# ================================================================ 3. หมุนหรือสะท้อน

class _RotOrRef:
    NAME = "shape2d.rotation_or_reflection"
    DOC = "คู่รูปนี้เป็นภาพหมุนหรือภาพสะท้อน — ตัดสินด้วยการคำนวณ"
    ANSWER_KIND = "text"
    VAR_NAMES = ["cells", "box", "kind", "turns"]

    @staticmethod
    def validate_params(params):
        if not isinstance(params, dict):
            return ["params ต้องเป็นอ็อบเจกต์"]
        return _common_params(params)

    @staticmethod
    def var_names(params):
        return list(_RotOrRef.VAR_NAMES)

    @staticmethod
    def draw(params, rng):
        shape = S2.random_shape(rng, params["n_cells"], params["box"])
        if shape is None:
            return None
        kind = rng.choice(["rotation", "reflection"])
        turns = rng.choice([1, 2, 3])
        return {"cells": sorted(shape), "box": params["box"],
                "kind": kind, "turns": turns}

    @staticmethod
    def build(params, vals):
        base = S2.normalize(tuple(map(tuple, vals["cells"])))
        box, kind, turns = vals["box"], vals["kind"], vals["turns"]
        second = (S2.rotations(base)[turns] if kind == "rotation"
                  else S2.reflections(base)[turns])

        if kind == "rotation":
            answer = f"เป็นภาพหมุน {ANGLE[turns]}"
            wrong = [
                ("เป็นภาพสะท้อน",
                 "สองรูปนี้หมุนให้ทับกันได้จริง จึงเป็นภาพหมุน ไม่ใช่ภาพสะท้อน",
                 "called_rotation_a_reflection"),
                ("เป็นภาพสะท้อนแล้วหมุนด้วย",
                 "ไม่ต้องสะท้อนเลยก็หมุนให้ทับกันได้แล้ว",
                 "extra_reflection"),
                ("เป็นรูปเดียวกันไม่ได้หมุน",
                 "สองรูปวางไม่เหมือนกัน ถ้าไม่หมุนจะไม่ทับกัน",
                 "no_transform"),
                ("เป็นคนละรูปกัน",
                 "จำนวนช่องและรูปร่างเหมือนกันทุกประการ ต่างแค่การวาง",
                 "different_shape"),
            ]
        else:
            answer = "เป็นภาพสะท้อน"
            wrong = [
                (f"เป็นภาพหมุน {ANGLE[turns]}",
                 "หมุนมุมนี้แล้วไม่ทับกัน เพราะลำดับซ้ายขวาสลับกันอยู่",
                 "called_reflection_a_rotation"),
                (f"เป็นภาพหมุน {ANGLE[(turns + 1) % 4]}",
                 "หมุนมุมไหนก็ไม่ทับกัน เพราะรูปนี้ไม่สมมาตร การสะท้อนจึงแยกจากการหมุนได้",
                 "wrong_rotation_angle"),
                ("เป็นรูปเดียวกันไม่ได้หมุน",
                 "สองรูปวางไม่เหมือนกัน ต้องมีการแปลงรูปเกิดขึ้น",
                 "no_transform"),
                ("เป็นคนละรูปกัน",
                 "จำนวนช่องและรูปร่างเหมือนกันทุกประการ ต่างแค่การวาง",
                 "different_shape"),
            ]

        figures = [_fig("fig1", base, box, "รูปที่ 1"),
                   _fig("fig2", second, box, "รูปที่ 2")]
        distractors = [{"value": w, "reason": why, "tag": tag}
                       for w, why, tag in wrong]

        steps = [
            {"do_md": "เลือกส่วนที่สังเกตง่ายสองส่วน เช่นแถวที่ยาวที่สุด "
                      "กับช่องที่ยื่นออกมาช่องเดียว",
             "why_md": "ต้องใช้สองส่วนเพื่อดูความสัมพันธ์ ถ้าดูส่วนเดียวจะบอกไม่ได้ว่าสลับข้างไหม"},
            {"do_md": "ดูว่าช่องที่ยื่นออกอยู่ทางซ้ายหรือขวาของแถวที่ยาวที่สุดในทั้งสองรูป",
             "why_md": "การหมุนไม่เปลี่ยนความสัมพันธ์ซ้ายขวา แต่การสะท้อนสลับเสมอ"},
            {"do_md": f"ในคู่นี้ความสัมพันธ์{'คงเดิม' if kind == 'rotation' else 'สลับข้าง'} "
                      f"จึง{answer}",
             "why_md": "สรุปจากหลักข้างต้นได้เลย ไม่ต้องลองหมุนในหัวทุกมุม"},
        ]
        hints = [
            "อย่าพยายามหมุนทั้งรูปในหัว ให้เลือกส่วนที่สังเกตง่ายสองส่วนก่อน",
            "ดูความสัมพันธ์ซ้ายขวาระหว่างสองส่วนนั้นในทั้งสองรูป",
            "การหมุนไม่เคยสลับซ้ายขวา ส่วนการสะท้อนสลับเสมอ",
        ]
        explanation = (
            f"เมื่อเทียบความสัมพันธ์ซ้ายขวาของสองส่วนในรูป พบว่า"
            f"{'ไม่สลับข้าง จึงเป็นภาพหมุน' if kind == 'rotation' else 'สลับข้าง จึงเป็นภาพสะท้อน'} "
            "หลักนี้ใช้ได้กับทุกรูปที่ไม่สมมาตร โดยไม่ต้องลองหมุนทีละมุม"
        )
        return {"answer": answer, "distractors": distractors, "steps": steps,
                "hints": hints, "explanation": explanation, "figures": figures,
                "meta": {"kind": kind, "turns": turns}}


ROTATE_MATCH = _RotateMatch
ODD_ONE_OUT = _OddOneOut
ROT_OR_REF = _RotOrRef
