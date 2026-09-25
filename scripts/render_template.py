"""render_template.py — สุ่มโจทย์ใหม่จากโจทย์แม่แบบ และตรวจว่าแม่แบบไม่พัง

ทำ 2 หน้าที่
  1. เป็น "ชั้นที่ 2" ของระบบตรวจใน spec/07 — สุ่มค่าข้อละ 200 ครั้งแล้วหาว่าโจทย์พังกรณีไหน
  2. เป็นต้นแบบของตัวสร้างโจทย์ที่เว็บจะใช้จริง

วิธีใช้
    python scripts/render_template.py --stress                 ตรวจทุกแม่แบบ (สุ่มข้อละ 200 ครั้ง)
    python scripts/render_template.py --stress --draws 500     เพิ่มจำนวนรอบสุ่ม
    python scripts/render_template.py --show math.trig.sine_law          ดูโจทย์ที่สุ่มได้ 3 ข้อ
    python scripts/render_template.py --show math.trig.sine_law -n 10    ดู 10 ข้อ
    python scripts/render_template.py --show <topic_id> --full             ดูวิธีคิดและคำใบ้ด้วย
    python scripts/render_template.py --id prob.math.trig.sine_law.0001 --stress

รหัสออกจากโปรแกรม: 0 = ทุกแม่แบบผ่าน, 1 = มีแม่แบบที่พัง
"""

from __future__ import annotations

import argparse
import math
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import providers as P  # noqa: E402
import speclib as S  # noqa: E402


class TemplateBroken(Exception):
    """แม่แบบพังกับค่าที่สุ่มมาชุดนี้ — ชุดอื่นอาจยังใช้ได้"""


class TemplateFatal(TemplateBroken):
    """แม่แบบเขียนผิดจนใช้ไม่ได้เลย ไม่ต้องสุ่มต่อ"""


# ---------------------------------------------------------------- สุ่มค่า

def draw_vars(tpl: dict, rng: random.Random) -> dict:
    vals: dict = {}
    for v in tpl["vars"]:
        vtype = v.get("type")
        if vtype == "int":
            lo, hi = v["range"]
            step = v.get("step") or 1
            n = (hi - lo) // step
            vals[v["name"]] = lo + rng.randint(0, n) * step
        elif vtype == "float":
            lo, hi = v["range"]
            step = v.get("step")
            if step:
                n = int((hi - lo) / step)
                vals[v["name"]] = round(lo + rng.randint(0, n) * step, 10)
            else:
                vals[v["name"]] = round(rng.uniform(lo, hi), v.get("round", 2))
        elif vtype in ("choice", "name"):
            vals[v["name"]] = rng.choice(v["options"])
        else:
            raise TemplateFatal(f"vars type ไม่รองรับ: {vtype!r}")
    return vals


def add_display(tpl: dict, vals: dict) -> dict:
    """คำนวณค่าที่ใช้ "แสดงในโจทย์" จากตัวแปรที่สุ่มมา

    ใช้กับโจทย์ที่ตัวเลขในโจทย์เกิดจากการคำนวณ เช่น อนุกรมที่แสดงพจน์
    a1, a1+d, a1+2d ... โดยประกาศแค่ a1 กับ d
    คำนวณตามลำดับที่เขียนไว้ ตัวหลังอ้างตัวหน้าได้
    """
    out = dict(vals)
    for name, expr in (tpl.get("display") or {}).items():
        try:
            out[name] = S.eval_expr(expr, out)
        except ZeroDivisionError as e:
            raise TemplateBroken(f"display '{name}' หารด้วยศูนย์") from e
        except (ValueError, OverflowError, S.ExprError) as e:
            raise TemplateBroken(f"display '{name}' คำนวณไม่ได้: {e}") from e
    return out


def passes_constraints(tpl: dict, vals: dict) -> bool:
    for c in tpl.get("constraints") or []:
        try:
            if not S.eval_expr(c, vals):
                return False
        except ZeroDivisionError:
            return False
        except (S.ExprError, ValueError, OverflowError) as e:
            raise TemplateFatal(f"constraint '{c}' คำนวณไม่ได้: {e}") from e
    return True


def build_one(tpl: dict, vals: dict) -> dict:
    """สร้างโจทย์ 1 ข้อจากค่าที่สุ่มมา คืน dict หรือโยน TemplateBroken"""
    ndigits = tpl.get("answer_round")
    try:
        raw_answer = S.eval_expr(tpl["answer_expr"], vals)
    except ZeroDivisionError as e:
        raise TemplateBroken("answer_expr หารด้วยศูนย์") from e
    except (ValueError, OverflowError) as e:
        raise TemplateBroken(f"answer_expr คำนวณไม่ได้ (เช่น รากติดลบ): {e}") from e
    except S.ExprError as e:
        raise TemplateBroken(f"answer_expr ผิด: {e}") from e

    if isinstance(raw_answer, bool) or not isinstance(raw_answer, (int, float)):
        raise TemplateBroken(f"answer_expr ไม่ได้คืนตัวเลข (ได้ {raw_answer!r})")
    if isinstance(raw_answer, float) and (math.isnan(raw_answer) or math.isinf(raw_answer)):
        raise TemplateBroken("answer_expr ได้ค่า NaN หรือ infinity")

    answer = round(raw_answer, ndigits) if ndigits is not None else raw_answer

    distractors = []
    for d in tpl.get("distractors") or []:
        try:
            val = S.eval_expr(d["expr"], vals)
        except ZeroDivisionError as e:
            raise TemplateBroken(f"distractor '{d['expr']}' หารด้วยศูนย์") from e
        except (ValueError, OverflowError, S.ExprError) as e:
            raise TemplateBroken(f"distractor '{d['expr']}' คำนวณไม่ได้: {e}") from e
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            raise TemplateBroken(f"distractor '{d['expr']}' ได้ NaN หรือ infinity")
        distractors.append({
            "value": round(val, ndigits) if ndigits is not None else val,
            "reason": d.get("reason", ""),
        })

    # คำตอบที่เอาไปแทนในข้อความ ต้องจัดรูปแบบเดียวกับที่แสดงในตัวเลือก
    # ไม่อย่างนั้นเฉลยจะเขียน 18 แต่ตัวเลือกเขียน 18.0 ซึ่งดูเหมือนคนละค่า
    scope = dict(vals)
    scope["answer"] = format_value(answer, None, ndigits)
    return {
        "vars": vals,
        "stem": S.render_stem(tpl["stem_tpl"], vals),
        "answer": answer,
        "unit": tpl.get("answer_unit"),
        "distractors": distractors,
        "figures": [],
        "steps": render_steps(tpl.get("steps_tpl"), scope),
        "hints": [S.render_stem(h, scope) for h in (tpl.get("hints_tpl") or [])],
        "explanation": S.render_stem(tpl.get("explanation_tpl") or "", scope),
    }


def render_steps(steps_tpl, scope: dict) -> list:
    """แทนค่าลงในวิธีคิดทีละขั้น

    นี่คือส่วนที่ทำให้โจทย์ที่สุ่มใหม่มีเฉลยละเอียดของตัวเอง
    ไม่ใช่ยืมเฉลยของข้อต้นฉบับซึ่งตัวเลขไม่ตรงกัน
    """
    out = []
    for st in steps_tpl or []:
        out.append({
            "do_md": S.render_stem(st.get("do_md") or "", scope),
            "why_md": S.render_stem(st.get("why_md") or "", scope),
        })
    return out


# ------------------------------------------------- แม่แบบที่คำนวณด้วย provider

def build_via_provider(tpl: dict, vals: dict) -> dict:
    """สร้างโจทย์จาก provider — ใช้กับหัวข้อที่นิพจน์เลขคณิตทำไม่ได้

    ต่างจาก build_one ตรงที่คำตอบเป็นอะไรก็ได้ (ชื่อหน้า คำ ข้อความ)
    และ provider เป็นคนสร้างรูปให้ตามค่าที่สุ่มมา
    """
    mod = P.get(tpl["provider"])
    if mod is None:
        raise TemplateFatal(f"ไม่รู้จัก provider {tpl['provider']!r} "
                            f"— ที่มีคือ {', '.join(P.names())}")
    params = tpl.get("params") or {}
    try:
        out = mod.build(params, vals)
    except Exception as e:  # noqa: BLE001 — provider พังถือเป็นแม่แบบพัง
        raise TemplateBroken(f"provider {mod.NAME} พังกับค่า {vals}: {e}") from e

    for key in ("answer", "distractors"):
        if key not in out:
            raise TemplateFatal(f"provider {mod.NAME} ไม่คืนฟิลด์ {key}")
    for i, d in enumerate(out["distractors"]):
        if "value" not in d:
            raise TemplateBroken(f"provider {mod.NAME} distractor ตัวที่ {i + 1} ไม่มี value")
        if not d.get("reason"):
            raise TemplateBroken(f"provider {mod.NAME} distractor ตัวที่ {i + 1} "
                                 "ไม่มี reason อธิบายว่าคิดผิดแบบไหนจึงได้ค่านี้")

    for key in ("steps", "hints", "explanation"):
        if not out.get(key):
            raise TemplateFatal(
                f"provider {mod.NAME} ไม่คืน {key} — โจทย์ที่สุ่มใหม่ต้องมีเฉลยของตัวเอง "
                "ไม่ใช่ยืมเฉลยของข้อต้นฉบับ")

    item = {
        "vars": vals,
        "stem": S.render_stem(tpl["stem_tpl"], vals),
        "answer": out["answer"],
        "unit": tpl.get("answer_unit"),
        "distractors": out["distractors"],
        "figures": out.get("figures") or [],
        "steps": out["steps"],
        "hints": out["hints"],
        "explanation": out["explanation"],
        "meta": out.get("meta") or {},
    }
    # provider ที่ตัวเลือกเป็นรูป (เช่น พับกระดาษเจาะรู) บอกมาว่ารูปไหนคือคำตอบ
    # ต้องส่งต่อ ไม่อย่างนั้นตัวที่เอาไปสร้างไฟล์โจทย์จะจับคู่ตัวเลือกกับรูปไม่ได้
    if out.get("answer_fig"):
        item["answer_fig"] = out["answer_fig"]
    return item


def make_item(tpl: dict, rng: random.Random):
    """สุ่มค่าและสร้างโจทย์ 1 ข้อ — ทางเข้าเดียวของทั้งสองโหมด

    คืน (item, None) ถ้าสร้างได้
    คืน (None, "rejected") ถ้าค่าที่สุ่มไม่ผ่านเงื่อนไข (ยังไม่ถือว่าพัง)
    โยน TemplateBroken ถ้าแม่แบบเสีย
    """
    if tpl.get("provider"):
        mod = P.get(tpl["provider"])
        if mod is None:
            raise TemplateFatal(f"ไม่รู้จัก provider {tpl['provider']!r} "
                                f"— ที่มีคือ {', '.join(P.names())}")
        try:
            vals = mod.draw(tpl.get("params") or {}, rng)
        except Exception as e:  # noqa: BLE001
            raise TemplateFatal(f"provider {mod.NAME} สุ่มค่าไม่ได้: {e}") from e
        if vals is None:
            return None, "rejected"
        return build_via_provider(tpl, vals), None

    vals = draw_vars(tpl, rng)
    # constraints อ้างค่าใน display ได้ (validate.py อนุญาตไว้แล้ว) จึงต้องคำนวณ display ก่อน
    # แต่ display บางตัวคำนวณไม่ได้กับค่าที่ constraints ตั้งใจกันไว้ (เช่นหารด้วยศูนย์)
    # ถ้า display พัง ให้ลองตรวจ constraints ที่อ้างแค่ vars ก่อน ถ้าไม่ผ่านถือว่าเป็นชุดที่ถูกกันไว้
    try:
        full = add_display(tpl, vals)
    except TemplateBroken:
        if not _passes_known_constraints(tpl, vals):
            return None, "rejected"
        raise
    if not passes_constraints(tpl, full):
        return None, "rejected"
    return build_one(tpl, full), None


def _passes_known_constraints(tpl: dict, vals: dict) -> bool:
    """ตรวจเฉพาะ constraints ที่คำนวณได้จากค่าที่มี (ข้ามตัวที่อ้างค่า display)"""
    for c in tpl.get("constraints") or []:
        try:
            if not S.eval_expr(c, vals):
                return False
        except (S.ExprError, ZeroDivisionError, ValueError, OverflowError):
            continue
    return True


# ---------------------------------------------------------------- ตรวจคุณภาพ

# ตัวเลือกลวงที่ห่างจากคำตอบเกินเท่านี้ ถือว่า "ดูผิดชัดเจน" ตามกฎในสเปค 06
PLAUSIBLE_RATIO = 5.0


def quality_problems(item: dict, tpl: dict) -> list[tuple[str, str]]:
    """เงื่อนไขที่ต้องผ่านทุกข้อ ไม่ว่าแม่แบบจะเขียน quality_rules ไว้หรือไม่

    คืนรายการ (ระดับ, ข้อความ) โดยระดับเป็น "error" (โจทย์ใช้ไม่ได้)
    หรือ "weak" (ใช้ได้แต่คุณภาพต่ำ เช่น ตัวเลือกลวงที่เดาได้ว่าผิด)
    """
    bad: list[tuple[str, str]] = []
    answer = item["answer"]
    dvals = [d["value"] for d in item["distractors"]]
    numeric = isinstance(answer, (int, float)) and not isinstance(answer, bool)

    for i, d in enumerate(item["distractors"]):
        if d["value"] == answer:
            bad.append(("error",
                        f"ตัวเลือกลวงตัวที่ {i + 1} ({d['reason']}) มีค่าเท่ากับคำตอบ = {answer}"))
    if len(set(dvals)) != len(dvals):
        bad.append(("error", f"ตัวเลือกลวงซ้ำกันเอง: {dvals}"))
    if numeric and answer == 0:
        bad.append(("error", "คำตอบเป็น 0 (มักเป็นสัญญาณว่าสุ่มได้กรณีพิเศษ)"))

    # คำตอบที่ไม่ใช่ตัวเลข (ชื่อหน้า คำ ข้อความ) — ตัวเลือกทุกตัวต้องเทียบกันได้
    if not numeric:
        if not isinstance(answer, str) or not answer.strip():
            bad.append(("error", f"คำตอบไม่ใช่ตัวเลขและไม่ใช่ข้อความที่มีเนื้อหา (ได้ {answer!r})"))
        for i, v in enumerate(dvals):
            if type(v) is not type(answer):
                bad.append(("error", f"ตัวเลือกลวงตัวที่ {i + 1} เป็นชนิด "
                                     f"{type(v).__name__} ต่างจากคำตอบที่เป็น "
                                     f"{type(answer).__name__} — ผู้สอบจะเดาได้จากรูปแบบ"))
        for i, d in enumerate(item["distractors"]):
            tag = d.get("tag")
            if tag is not None and not re.fullmatch(r"[a-z0-9_]+", str(tag)):
                bad.append(("error", f"ตัวเลือกลวงตัวที่ {i + 1} มี tag {tag!r} "
                                     "ที่ไม่ใช่ snake_case อังกฤษ "
                                     "(ต้องตรงกับ misconception_tags ในบทเรียน)"))

    # ตัวเลือกลวงต้องดูน่าเชื่อ ไม่ใช่ค่าที่เดาได้ว่าผิดโดยไม่ต้องคำนวณ
    if numeric and answer > 0:
        for i, d in enumerate(item["distractors"]):
            v = d["value"]
            if not isinstance(v, (int, float)):
                continue
            if v <= 0:
                bad.append(("weak", f"ตัวเลือกลวงตัวที่ {i + 1} ({d['reason']}) "
                                    f"เป็นค่า {v} ซึ่งเดาได้ว่าผิดทันที"))
            elif v > answer * PLAUSIBLE_RATIO or v < answer / PLAUSIBLE_RATIO:
                bad.append(("weak", f"ตัวเลือกลวงตัวที่ {i + 1} ({d['reason']}) = {v} "
                                    f"ห่างจากคำตอบ {answer} เกิน {PLAUSIBLE_RATIO:g} เท่า "
                                    "นักเรียนจะตัดทิ้งได้โดยไม่ต้องคำนวณ"))

    bad += explanation_problems(item, tpl)

    # เงื่อนไขที่แม่แบบเขียนเป็นนิพจน์ไว้ (ไม่บังคับ)
    # แม่แบบแบบ provider ไม่ใช้ช่องนี้ เพราะค่าที่สุ่มอาจเป็นข้อความซึ่งคำนวณไม่ได้
    if tpl.get("provider"):
        return bad
    scope = dict(item["vars"])
    scope["answer"] = answer
    for i, expr in enumerate(tpl.get("quality_exprs") or []):
        try:
            if not S.eval_expr(expr, scope):
                bad.append(("error", f"ไม่ผ่าน quality_exprs[{i}]: {expr}"))
        except Exception as e:  # noqa: BLE001
            bad.append(("error", f"quality_exprs[{i}] คำนวณไม่ได้: {e}"))
    return bad


def explanation_problems(item: dict, tpl: dict) -> list:
    """ตรวจว่าโจทย์ที่สุ่มมา "อธิบายตัวเองได้" ครบ

    นี่คือเงื่อนไขที่แม่แบบต่างจากโจทย์ที่เขียนมือ: ถ้าไม่ตรวจ ผู้ใช้จะกดสุ่มแล้วได้
    โจทย์ที่มีแต่คำตอบ ไม่มีวิธีคิด ซึ่งไร้ประโยชน์กับคนที่เรียนจาก 0
    """
    bad: list[tuple[str, str]] = []
    answer_txt = format_value(item["answer"], None, tpl.get("answer_round"))

    steps = item.get("steps") or []
    if len(steps) < 2:
        bad.append(("error", f"วิธีคิดมี {len(steps)} ขั้น ต้องมีอย่างน้อย 2 ขั้น"))
    for i, st in enumerate(steps):
        if not (st.get("do_md") or "").strip():
            bad.append(("error", f"วิธีคิดขั้นที่ {i + 1} ไม่มี do_md"))
        if not (st.get("why_md") or "").strip():
            bad.append(("error", f"วิธีคิดขั้นที่ {i + 1} ไม่มี why_md "
                                 "(ต้องบอกว่าทำไมจึงทำขั้นนี้ ไม่ใช่บอกแค่ว่าทำอะไร)"))

    hints = item.get("hints") or []
    if len(hints) != 3:
        bad.append(("error", f"hints มี {len(hints)} ข้อ ต้องมี 3 ระดับเสมอ"))
    for i, h in enumerate(hints):
        if not (h or "").strip():
            bad.append(("error", f"hints ข้อที่ {i + 1} เป็นข้อความว่าง"))
        # คำใบ้ห้ามบอกคำตอบ ไม่อย่างนั้นการกดขอคำใบ้กลายเป็นการกดดูเฉลย
        elif _reveals(h, answer_txt):
            bad.append(("error", f"hints ข้อที่ {i + 1} มีคำตอบ ({answer_txt}) อยู่ในข้อความ "
                                 "— คำใบ้ต้องชี้ทางเท่านั้น ห้ามเฉลย"))

    if not (item.get("explanation") or "").strip():
        bad.append(("error", "ไม่มีคำอธิบายคำตอบ (explanation)"))

    # ข้อความที่แทนค่าแล้วต้องไม่มีช่องแทนค่าค้างอยู่
    texts = [item["stem"], item.get("explanation") or ""] + hints
    texts += [st.get("do_md", "") for st in steps] + [st.get("why_md", "") for st in steps]
    left = set()
    for t in texts:
        left |= S.placeholders(t)
    for nm in sorted(left):
        bad.append(("error", f"ข้อความยังมีช่องแทนค่า {{{nm}}} ค้างอยู่ "
                             "— ชื่อนี้ไม่มีใน vars, display หรือค่าที่ provider คืนมา"))
    return bad


def _reveals(text: str, answer_txt: str) -> bool:
    """คำใบ้มีคำตอบอยู่หรือไม่

    ต้องเทียบแบบมีขอบเขตคำ ไม่ใช่ค้นข้อความตรง ๆ เพราะ
      - ตัวเลข 7 เป็นส่วนของ 17 หรือ 0.7 ได้
      - ชื่อหน้าเป็นอักษรไทยตัวเดียว เช่น "ก" ซึ่งอยู่ในคำว่า "จาก" หรือ "การ"
        ถ้าค้นแบบ substring จะฟ้องผิดแทบทุกครั้ง
    """
    if not answer_txt:
        return False
    if re.fullmatch(r"-?\d+(\.\d+)?", answer_txt):
        return re.search(rf"(?<![\d.]){re.escape(answer_txt)}(?![\d.])", text) is not None
    # คำตอบที่เป็นตัวอักษรหรือข้อความ: ต้องไม่ติดกับอักษรไทยตัวอื่น
    # (ในข้อความของเรา ชื่อหน้าจะมีวรรคหรือเครื่องหมายคั่นเสมอ เพราะเป็นสัญลักษณ์ ไม่ใช่คำ)
    pat = rf"(?<![฀-๿]){re.escape(answer_txt)}(?![฀-๿])"
    return re.search(pat, text) is not None


# ---------------------------------------------------------------- โหมดทำงาน

def stress_one(pid: str, tpl: dict, draws: int, seed: int) -> dict:
    """สุ่ม draws ครั้ง คืนสรุปผล"""
    rng = random.Random(seed)
    result = {"id": pid, "accepted": 0, "tried": 0, "fatal": None,
              "failures": [], "weak": [], "rejected": 0, "distinct": 0}
    signatures: set = set()
    max_tries = draws * 200
    while result["accepted"] < draws and result["tried"] < max_tries:
        result["tried"] += 1
        try:
            item, why_not = make_item(tpl, rng)
        except TemplateFatal as e:
            result["fatal"] = str(e)
            return result
        except TemplateBroken as e:
            result["accepted"] += 1
            result["failures"].append(({}, str(e)))
            continue
        if item is None:
            result["rejected"] += 1
            continue
        result["accepted"] += 1
        vals = item["vars"]
        signatures.add(tuple(sorted((k, str(v)) for k, v in vals.items())))
        for level, why in quality_problems(item, tpl):
            bucket = "failures" if level == "error" else "weak"
            result[bucket].append((vals, why))
    result["distinct"] = len(signatures)
    return result


# แม่แบบที่สุ่มได้น้อยกว่านี้ ผู้ใช้จะเจอโจทย์ซ้ำเร็วเกินไป
MIN_DISTINCT = 4


# ตัวอักษรกำกับตัวเลือกแบบข้อสอบไทย
THAI_LABELS = ["ก", "ข", "ค", "ง", "จ", "ฉ", "ช", "ซ"]


def format_value(v, unit, ndigits=None) -> str:
    if isinstance(v, float):
        txt = f"{v:.{ndigits}f}" if ndigits is not None else f"{v:g}"
    else:
        txt = str(v)
    return f"{txt} {unit}" if unit else txt


def show(pid: str, tpl: dict, n: int, seed: int, verbose: bool = False) -> None:
    rng = random.Random(seed)
    ndigits = tpl.get("answer_round")
    print(f"\n{'=' * 72}\n  โจทย์ที่สุ่มจากแม่แบบ {pid}\n{'=' * 72}")
    made = 0
    tries = 0
    skipped_weak = 0
    skipped_dup = 0
    seen: set = set()
    while made < n and tries < n * 500:
        tries += 1
        try:
            item, _ = make_item(tpl, rng)
        except TemplateFatal as e:
            print(f"  แม่แบบใช้ไม่ได้เลย: {e}")
            return
        except TemplateBroken as e:
            print(f"  (ข้ามค่าชุดหนึ่ง: {e})")
            continue
        if item is None:
            continue
        # ห้ามออกโจทย์ที่ค่าตัวแปรชุดเดียวกันซ้ำในชุดเดียว
        key = tuple(sorted((k, str(v)) for k, v in item["vars"].items()))
        if key in seen:
            skipped_dup += 1
            continue
        seen.add(key)
        issues = quality_problems(item, tpl)
        if any(level == "error" for level, _ in issues):
            continue
        if issues:
            skipped_weak += 1
            continue
        made += 1
        choices = [("ถูก", item["answer"])] + [
            ("ลวง", d["value"]) for d in item["distractors"]
        ]
        rng.shuffle(choices)
        print(f"\nข้อ {made}   [ค่าที่สุ่ม: {item['vars']}]")
        print(f"  {item['stem']}")
        for fig in item.get("figures") or []:
            # ไม่พิมพ์ตัว SVG ออกมา เพราะยาวและอ่านไม่รู้เรื่องในคอนโซล
            print(f"  [รูป {fig.get('id')}] {fig.get('alt')}")
        for i, (kind, val) in enumerate(choices):
            mark = "   <-- คำตอบ" if kind == "ถูก" else ""
            label = THAI_LABELS[i] if i < len(THAI_LABELS) else str(i + 1)
            print(f"    {label}. {format_value(val, item['unit'], ndigits)}{mark}")
        if verbose:
            print("  วิธีคิด:")
            for j, st in enumerate(item.get("steps") or [], 1):
                print(f"    {j}. {st['do_md']}")
                print(f"       เพราะ {st['why_md']}")
            print("  คำใบ้:")
            for j, h in enumerate(item.get("hints") or [], 1):
                print(f"    {j}. {h}")
            print(f"  อธิบายคำตอบ: {item.get('explanation')}")
    if skipped_weak:
        print(f"\n  (ข้ามไป {skipped_weak} ชุด เพราะตัวเลือกลวงดูผิดชัดเจนเกินไป)")
    if skipped_dup:
        print(f"  (ข้ามไป {skipped_dup} ชุด เพราะค่าตัวแปรซ้ำกับข้อที่ออกไปแล้ว)")
    if made < n:
        print(f"\n  สร้างได้แค่ {made}/{n} ข้อ — constraints อาจแน่นเกินไป "
              f"หรือชุดค่าที่เป็นไปได้มีน้อยกว่า {n} ชุด")


# ---------------------------------------------------------------- main

def load_templates(root: pathlib.Path, rep: S.Report, only_id=None, only_topic=None):
    """คืนรายการ (problem_id, template, ชื่อไฟล์) ของโจทย์ที่มีแม่แบบ"""
    out = []
    pdir = root / "problems"
    if not pdir.is_dir():
        return out
    for path in sorted(pdir.glob("*.json")):
        data = S.load_json(path, rep)
        if not data:
            continue
        if only_topic and data.get("topic_id") != only_topic:
            continue
        for p in data.get("problems") or []:
            if only_id and p.get("id") != only_id:
                continue
            if p.get("template"):
                out.append((p["id"], p["template"], path.name))
    return out


def main() -> int:
    S.utf8_stdout()
    ap = argparse.ArgumentParser(description="สุ่มโจทย์จากแม่แบบ และตรวจว่าแม่แบบไม่พัง")
    ap.add_argument("--stress", action="store_true",
                    help="โหมดตรวจ: สุ่มข้อละหลายครั้งเพื่อหากรณีที่โจทย์พัง")
    ap.add_argument("--draws", type=int, default=200,
                    help="จำนวนครั้งที่สุ่มต่อ 1 แม่แบบ (ค่าเริ่มต้น 200 ตามสเปค)")
    ap.add_argument("--show", metavar="TOPIC_ID", default=None,
                    help="โหมดดูตัวอย่าง: แสดงโจทย์ที่สุ่มได้ของหัวข้อนี้")
    ap.add_argument("-n", type=int, default=3, help="จำนวนข้อที่ต้องการดูในโหมด --show")
    ap.add_argument("--id", default=None, help="เจาะจงโจทย์ข้อเดียวด้วย problem id")
    ap.add_argument("--full", action="store_true",
                    help="ในโหมด --show ให้แสดงวิธีคิด คำใบ้ และคำอธิบายคำตอบด้วย")
    ap.add_argument("--seed", type=int, default=20260919, help="ค่าตั้งต้นการสุ่ม")
    ap.add_argument("--data", default=None, help="โฟลเดอร์ data (ปกติหาให้อัตโนมัติ)")
    args = ap.parse_args()

    root = pathlib.Path(args.data) if args.data else S.data_root()
    rep = S.Report()
    templates = load_templates(root, rep, only_id=args.id, only_topic=args.show)

    if rep.errors:
        return rep.print_summary("อ่านไฟล์ไม่สำเร็จ")
    if not templates:
        print("ไม่พบโจทย์ที่มี template ตามเงื่อนไขที่ระบุ")
        print(f"(มองหาใน {root / 'problems'})")
        return 1

    if args.show:
        for pid, tpl, _ in templates[: max(1, args.n // 3) or 1]:
            show(pid, tpl, args.n, args.seed, verbose=args.full)
        return 0

    if not args.stress:
        print("ระบุโหมดด้วย --stress (ตรวจแม่แบบ) หรือ --show <topic_id> (ดูตัวอย่างโจทย์)")
        return 1

    print(f"ตรวจแม่แบบ {len(templates)} ข้อ สุ่มข้อละ {args.draws} ครั้ง\n")
    n_pass = 0
    for pid, tpl, fname in templates:
        r = stress_one(pid, tpl, args.draws, args.seed)
        where = f"{fname} :: {pid}"
        if r["fatal"]:
            rep.error(where, f"แม่แบบใช้ไม่ได้เลย: {r['fatal']}")
            print(f"  X {pid}  ใช้ไม่ได้เลย")
            continue
        if r["accepted"] < args.draws:
            rep.error(where, f"สุ่ม {r['tried']} ครั้งแต่ผ่าน constraints แค่ {r['accepted']} ครั้ง "
                             f"(ต้องการ {args.draws}) — constraints แน่นเกินไป "
                             "หรือช่วงค่าของตัวแปรแคบเกินไป")
        if 0 < r["distinct"] < MIN_DISTINCT:
            rep.warn(where, f"แม่แบบนี้สุ่มได้แค่ {r['distinct']} แบบที่ต่างกันจริง "
                            f"(สุ่ม {r['accepted']} ครั้ง) ผู้ใช้จะเจอโจทย์ซ้ำเร็วเกินไป — "
                            "ขยายช่วงค่าตัวแปร หรือเพิ่มตัวเลือกใน params")
        reject_rate = r["rejected"] / r["tried"] if r["tried"] else 0
        if reject_rate > 0.9:
            rep.warn(where, f"ค่าที่สุ่มถูก constraints ตีตก {reject_rate:.0%} "
                            "ประสิทธิภาพต่ำ ควรปรับช่วงค่าให้ตรงกับเงื่อนไขมากขึ้น")
        def grouped(rows):
            out: dict[str, list] = {}
            for vals, why in rows:
                key = why.split(":")[0].split("=")[0].strip()
                out.setdefault(key, []).append((vals, why))
            return out

        for _key, items in grouped(r["failures"]).items():
            vals, why = items[0]
            rep.error(where, f"พัง {len(items)}/{r['accepted']} ครั้ง — {why}\n"
                             f"        ตัวอย่างค่าที่ทำให้พัง: {vals}\n"
                             f"        แก้ที่ constraints ไม่ใช่ที่ answer_expr")
        for _key, items in grouped(r["weak"]).items():
            vals, why = items[0]
            rep.warn(where, f"คุณภาพต่ำ {len(items)}/{r['accepted']} ครั้ง — {why}\n"
                            f"        ตัวอย่างค่าที่ทำให้เกิด: {vals}\n"
                            "        แก้ด้วยการบีบช่วงค่าตัวแปร หรือเปลี่ยนสูตรตัวเลือกลวง")

        if r["failures"]:
            print(f"  X  {pid}  พัง {len(r['failures'])}/{r['accepted']} ครั้ง")
        elif r["weak"]:
            print(f"  !  {pid}  ใช้ได้ แต่คุณภาพต่ำ {len(r['weak'])}/{r['accepted']} ครั้ง")
            n_pass += 1
        else:
            n_pass += 1
            print(f"  OK {pid}  ผ่าน {r['accepted']}/{r['accepted']} ครั้ง  "
                  f"(โจทย์ที่ต่างกันจริง {r['distinct']} แบบ)")

    rep.files_checked = len(templates)
    print(f"\nแม่แบบที่ผ่านสะอาด: {n_pass}/{len(templates)}")
    return rep.print_summary("ผลตรวจชั้นที่ 2 (รันแม่แบบจริง)")


if __name__ == "__main__":
    sys.exit(main())
