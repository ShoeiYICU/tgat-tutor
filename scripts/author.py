"""author.py — ตัวช่วยเขียนบทเรียนและโจทย์แบบย่อ แล้วขยายเป็น JSON เต็มตามสเปค

ทำไมต้องมี: ไฟล์ JSON ตามสเปคมีฟิลด์บังคับเยอะ (difficulty_signals, style_ref,
distractor_reasons ตาม index ...) ถ้าเขียนมือทุกข้อจะช้าและพลาดง่าย
ไฟล์เนื้อหาใน content/ จึงเขียนแบบย่อด้วยฟังก์ชันในไฟล์นี้ แล้วให้โค้ดเติมส่วนที่เหลือ

ใช้ใน content/*.py เช่น

    from author import *
    L = lesson("tgat3.foundation.how_to_read", "ชื่อบท", "คำโปรย",
               objectives=[...], blocks=[hook("..."), concept("หัว", "เนื้อ"), ...])
    P = [q("โจทย์", "คำตอบ", [("ตัวลวง", "เหตุผล"), ...], steps=[...], hints=[...], explain="...", diff=2)]
    save("tgat3.foundation.how_to_read", "TGAT3", "mcq4_tiered", P, lesson=L)

กฎ
    - ไม่เขียนทับไฟล์ที่ไม่ได้สร้างจาก content/ (ดูจากฟิลด์ generated_from)
    - ตำแหน่งคำตอบกระจายเท่า ๆ กันทั้งไฟล์ ไม่ให้คำตอบกองอยู่ข้อเดียว
    - ทุกโจทย์เป็น origin "original" และ review_status "ai_draft" เสมอ

ข้อควรระวังตอนเขียน (validate.py เตือนให้ถ้าพลาด)
    - **อย่าให้คำตอบเป็นตัวเลือกที่ยาวที่สุดเกือบทุกข้อ** — ผู้สอบจะเดาจากความยาวได้
      ให้คำตอบกระชับ และให้ตัวลวงบางตัวมี "เหตุผลที่ฟังขึ้น" ต่อท้าย ซึ่งเป็นลักษณะของข้อสอบจริงอยู่แล้ว
"""

from __future__ import annotations

import inspect
import json
import re
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

NOTES = {
    "TGAT1": "แนวข้อสอบ TGAT1 การสื่อสารภาษาอังกฤษ แต่งใหม่ ไม่ใช่ข้อสอบจริง",
    "TGAT2": "แนวข้อสอบ TGAT2 การคิดอย่างมีเหตุผล แต่งใหม่ ไม่ใช่ข้อสอบจริง",
    "TGAT3": "แนวข้อสอบ TGAT3 สมรรถนะการทำงาน แต่งใหม่ ไม่ใช่ข้อสอบจริง",
    "TPAT3": "แนวข้อสอบ TPAT3 ความถนัดวิทยาศาสตร์ เทคโนโลยี และวิศวกรรมศาสตร์ แต่งใหม่ ไม่ใช่ข้อสอบจริง",
}
N_CHOICES = {"mcq4": 4, "mcq5": 5, "mcq4_tiered": 4}


# ================================================================== โจทย์

def signals(diff: int, reading: str = "low") -> dict:
    """เลือก difficulty_signals ที่สอดคล้องกับระดับความยากตามตาราง C.3"""
    base = {"steps_count": 2, "topics_count": 1, "needs_insight": False,
            "heavy_computation": False, "trap_present": False, "reading_load": "low"}
    if diff <= 2:
        return base
    if diff == 3:
        return {**base, "steps_count": 3, "reading_load": reading if reading != "high" else "medium"}
    if diff == 4:
        return {**base, "steps_count": 3, "reading_load": "high" if reading == "high" else base["reading_load"],
                "topics_count": 1 if reading == "high" else 2, "trap_present": True}
    return {**base, "steps_count": 3, "needs_insight": True, "trap_present": True}


def q(stem, answer, wrong, steps, hints, explain, diff=2, sec=None, tags=None,
      figures=None, reading="low"):
    """โจทย์ปรนัยปกติ: answer = ข้อความคำตอบ, wrong = [(ข้อความ, เหตุผลที่ผิด), ...]"""
    return {"kind": "mcq", "stem": stem, "answer": answer, "wrong": wrong,
            "steps": steps, "hints": hints, "explain": explain, "diff": diff,
            "sec": sec, "tags": tags or [], "figures": figures or [], "reading": reading}


def t(stem, options, steps, hints, explain, diff=2, sec=None, tags=None, reading="medium"):
    """โจทย์ให้คะแนนขั้นบันได (TGAT3): options = [(ข้อความ, คะแนน, เหตุผล), ...]
    ต้องมีคะแนน 1 พอดีหนึ่งตัว"""
    return {"kind": "tiered", "stem": stem, "options": options, "steps": steps,
            "hints": hints, "explain": explain, "diff": diff, "sec": sec,
            "tags": tags or [], "figures": [], "reading": reading}


def qf(stem, choices, answer_index, reasons, steps, hints, explain, diff=2, sec=None, tags=None, reading="low"):
    """โจทย์ที่ตัวเลือกเป็นชุดตายตัวและต้องเรียงลำดับเดิมทุกข้อ (เช่น ความเพียงพอของข้อมูล)
    reasons = {index: เหตุผลที่ผิด} ต้องครบทุกตัวเลือกผิด"""
    return {"kind": "fixed", "stem": stem, "choices": choices, "answer_index": answer_index,
            "reasons": reasons, "steps": steps, "hints": hints, "explain": explain, "diff": diff,
            "sec": sec, "tags": tags or [], "figures": [], "reading": reading}


def tq(template, diff=2, sec=None, tags=None, reading="low", calc=False):
    """โจทย์แม่แบบ (สุ่มตัวเลขได้): ตัวอย่างในไฟล์สร้างจากแม่แบบเอง จึงตรงกันเสมอ

    template ต้องมี vars, answer_expr, distractors, stem_tpl, steps_tpl, hints_tpl, explanation_tpl
    ตามสเปค C.4/C.7 จำนวน distractors = จำนวนตัวเลือก - 1
    """
    return {"kind": "tpl", "template": template, "diff": diff, "sec": sec,
            "tags": tags or [], "reading": reading, "calc": calc, "figures": []}


def _from_template(pid, it, salt=0):
    """สุ่มหนึ่งชุดที่ผ่านเกณฑ์คุณภาพ แล้วแปลงเป็น stem/answer/wrong/steps แบบโจทย์ปกติ

    salt ใช้เปลี่ยน seed เมื่อสุ่มได้โจทย์ซ้ำกับข้ออื่นในหัวข้อเดียวกัน
    """
    import render_template as R  # นำเข้าตอนใช้ เพื่อไม่ให้ content ที่ไม่ใช้แม่แบบต้องโหลด provider

    tpl = it["template"]
    rng = random.Random(f"{pid}#{salt}" if salt else pid)
    for _ in range(4000):
        item, _why = R.make_item(tpl, rng)
        if item is not None and not R.quality_problems(item, tpl):
            break
    else:
        raise AssertionError(f"{pid}: แม่แบบสุ่มชุดที่ผ่านเกณฑ์ไม่ได้ใน 4000 ครั้ง")

    def fmt(v):
        txt = R.format_value(v, item["unit"], tpl.get("answer_round"))
        return f"${txt}$" if isinstance(v, (int, float)) and not item["unit"] else txt

    return {**it, "kind": "mcq", "stem": item["stem"], "answer": fmt(item["answer"]),
            "wrong": [(fmt(d["value"]), d["reason"]) for d in item["distractors"]],
            "steps": [(s["do_md"], s["why_md"]) for s in item["steps"]],
            "hints": item["hints"], "explain": item["explanation"], "template": tpl}


def _steps(steps):
    return [{"do_md": d, "why_md": w} for d, w in steps]


def _build(pid, topic, exam, fmt, it, pos, salt=0):
    n = N_CHOICES[fmt]
    if it["kind"] == "tpl":
        it = _from_template(pid, it, salt)
    if it["kind"] == "fixed":
        assert len(it["choices"]) == n, f"{pid}: ต้องมี {n} ตัวเลือก"
        choices = [{"md": c, "is_answer": i == it["answer_index"]} for i, c in enumerate(it["choices"])]
        reasons = {str(i): r for i, r in it["reasons"].items()}
        missing = {str(i) for i in range(n) if i != it["answer_index"]} - set(reasons)
        assert not missing, f"{pid}: ขาดเหตุผลของตัวเลือก {sorted(missing)}"
    elif it["kind"] == "mcq":
        assert len(it["wrong"]) == n - 1, f"{pid}: ต้องมีตัวลวง {n - 1} ตัว (พบ {len(it['wrong'])})"
        others = list(it["wrong"])
        random.Random(pid).shuffle(others)
        entries = others[:pos] + [(it["answer"], None)] + others[pos:]
        choices = [{"md": txt, "is_answer": why is None} for txt, why in entries]
        reasons = {str(i): why for i, (_, why) in enumerate(entries) if why is not None}
    else:
        opts = it["options"]
        assert len(opts) == n, f"{pid}: ต้องมี {n} ตัวเลือก"
        best = [o for o in opts if o[1] == 1]
        assert len(best) == 1, f"{pid}: ต้องมีตัวเลือกคะแนน 1 หนึ่งตัว"
        others = [o for o in opts if o[1] != 1]
        random.Random(pid).shuffle(others)
        entries = others[:pos] + best + others[pos:]
        choices = [{"md": txt, "is_answer": sc == 1, "score": sc} for txt, sc, _ in entries]
        reasons = {str(i): why for i, (_, sc, why) in enumerate(entries) if sc != 1}

    texts = [c["md"] for c in choices]
    assert len(set(texts)) == len(texts), f"{pid}: มีตัวเลือกซ้ำกัน"
    assert len(it["hints"]) == 3, f"{pid}: ต้องมีคำใบ้ 3 ข้อ"
    assert len(it["steps"]) >= 2, f"{pid}: ต้องมีวิธีคิดอย่างน้อย 2 ขั้น"
    # เวลาเฉลี่ยต่อข้อของแต่ละวิชา ใช้เมื่อผู้เขียนไม่ได้ระบุ sec เอง
    sec = it["sec"] or {"TGAT1": 60, "TGAT2": 45, "TGAT3": 60, "TPAT3": 150}[exam]
    return {
        "id": pid,
        "topic_ids": [topic],
        "primary_topic_id": topic,
        "exam_code": exam,
        "origin": "original",
        "style_ref": {"year": None, "item_no": None, "note": NOTES[exam]},
        "format": fmt,
        "difficulty": it["diff"],
        "difficulty_signals": signals(it["diff"], it["reading"]),
        "est_seconds": sec,
        "stem_md": it["stem"],
        "figures": it["figures"],
        "choices": choices,
        "answer_numeric": None,
        "solution_steps": _steps(it["steps"]),
        "answer_explanation_md": it["explain"],
        "hints": it["hints"],
        "distractor_reasons": reasons,
        "misconception_tags": it["tags"],
        "template": it.get("template"),
        "template_note": None if it.get("template") else
            "โจทย์เชิงภาษา/สถานการณ์/ตรรกะ คำตอบขึ้นกับความหมาย สุ่มด้วยนิพจน์คำนวณไม่ได้ จึงแต่งเป็นข้อ ๆ",
        "calculator_allowed": bool(it.get("calc")),
        "review_status": "ai_draft",
    }


# ================================================================== แม่แบบเลขคณิต (C.4)

def V(name, lo, hi, step=1):
    return {"name": name, "type": "int", "range": [lo, hi], "step": step}


def auto_constraints(answer, wrong):
    """กันตัวเลือกซ้ำกัน ตัวเลือกติดลบ/ศูนย์ และตัวลวงที่ห่างจากคำตอบเกิน 5 เท่า
    (ตัวตรวจแม่แบบถือว่าพังแม้เกิดแค่ครั้งเดียวจาก 200 ครั้ง จึงต้องกันไว้ที่ต้นทาง)"""
    exprs = [answer] + [e for e, _ in wrong]
    out = [f"({e}) > 0" for e in exprs]
    out += [f"({a}) != ({b})" for i, a in enumerate(exprs) for b in exprs[i + 1:]]
    out += [f"({e}) <= 5*({answer})" for e, _ in wrong] + [f"5*({e}) >= ({answer})" for e, _ in wrong]
    # นิพจน์ที่ใช้ // ต้องหารลงตัวจริง ไม่อย่างนั้นค่าที่แสดงถูกปัดลงเงียบ ๆ
    # และไม่ตรงกับเหตุผลที่เขียนไว้ เช่น "หารด้วยจำนวนเดิม" ควรได้ 50.67 แต่แสดง 50
    # (Codex พบในการตรวจไขว้รอบ 8) จึงบังคับให้ค่าจาก // เท่ากับค่าจาก / ทุกครั้งที่สุ่ม
    out += [f"({e}) == ({e.replace('//', '/')})" for e in exprs if "//" in e]
    return out


def hint_constraints(answer, hints):
    """ค่าที่โผล่ในคำใบ้ต้องไม่เท่ากับคำตอบ ไม่อย่างนั้นคำใบ้จะกลายเป็นเฉลย"""
    names = sorted({m for h in hints for m in re.findall(r"\{([A-Za-z_]\w*)\}", h)} - {"answer"})
    return [f"({n}) != ({answer})" for n in names]


def T(stem, vars, answer, wrong, steps, hints, explain, constraints=None, display=None, qexprs=None, unit=None, rnd=None):
    return {"vars": vars,
            "constraints": (constraints or []) + auto_constraints(answer, wrong) + hint_constraints(answer, hints),
            "display": display or {},
            "stem_tpl": stem, "answer_expr": answer, "answer_round": rnd, "answer_unit": unit,
            "distractors": [{"expr": e, "reason": r} for e, r in wrong],
            "quality_rules": ["ตัวเลือกทุกตัวต้องเป็นจำนวนบวกและไม่ซ้ำกัน", "คำตอบคำนวณจากนิพจน์ ไม่ได้ใส่มือ"],
            "quality_exprs": qexprs or ["answer > 0"],
            "steps_tpl": [{"do_md": d, "why_md": w} for d, w in steps],
            "hints_tpl": hints, "explanation_tpl": explain}



# ================================================================== บทเรียน

def hook(body):
    return {"type": "hook", "body_md": body}


def concept(heading, body, figures=None):
    b = {"type": "concept", "heading": heading, "body_md": body}
    if figures:
        b["figures"] = figures
    return b


def technique(name, use_when, avoid_when, how_md="", tip=None, tex=""):
    """บล็อก formula สำหรับวิชาที่ไม่มีสูตร: ใช้เป็น 'หลักการ/เทคนิค' """
    b = {"type": "formula", "name": name, "formula_tex": tex, "variables": [],
         "use_when": use_when, "avoid_when": avoid_when}
    if how_md:
        b["derivation_md"] = how_md
    if tip:
        b["memory_tip"] = tip
    return b


def example(label, stem, steps, answer, diff=2, figures=None):
    return {"type": "example", "label": label, "difficulty": diff, "stem_md": stem,
            "steps": _steps(steps), "answer_md": answer, "figures": figures or []}


def pitfall(title, wrong, why, right, tag):
    return {"type": "pitfall", "title": title, "wrong_md": wrong,
            "why_wrong_md": why, "correct_md": right, "misconception_tag": tag}


def summary(*bullets):
    return {"type": "summary", "bullets_md": list(bullets)}


def check(question, choices, answer_index, explain):
    return {"type": "check", "question_md": question, "choices": choices,
            "answer_index": answer_index, "explain_md": explain}


def lesson(topic, title, subtitle, objectives, blocks, minutes=15, prereq=None,
           nxt=None, glossary=None, patterns=None, sources=None):
    return {
        "schema_version": "1.0",
        "topic_id": topic,
        "title": title,
        "subtitle": subtitle,
        "prereq_topic_ids": prereq or [],
        "objectives": objectives,
        "est_minutes": minutes,
        "blocks": blocks,
        "glossary": [{"term_th": a, "term_en": b, "def_md": c} for a, b, c in (glossary or [])],
        "common_exam_patterns": patterns or [],
        "next_topic_ids": nxt or [],
        "sources": sources or ["ผังการสอบจาก mytcas.com (โครงสร้างข้อสอบ) และเนื้อหาที่เรียบเรียงขึ้นใหม่เพื่อการฝึก"],
        "review_status": "ai_draft",
    }


# ================================================================== เขียนไฟล์

def _caller():
    frame = inspect.stack()[2]
    try:
        return pathlib.Path(frame.filename).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return pathlib.Path(frame.filename).name


def _write(path: pathlib.Path, obj: dict, src: str) -> None:
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("generated_from") != src:
            raise SystemExit(f"ไม่เขียนทับ {path.name}: ไฟล์นี้ไม่ได้สร้างจาก {src} "
                             f"(generated_from = {old.get('generated_from')!r})")
    obj = {**obj, "generated_from": src}
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save(topic, exam, fmt, items, lesson=None):
    """เขียนไฟล์โจทย์ (และบทเรียนถ้าส่งมา) ของหัวข้อเดียว"""
    src = _caller()
    n = N_CHOICES[fmt]
    # กระจายตำแหน่งคำตอบให้เท่ากัน แล้วสลับลำดับด้วย seed คงที่
    pos = [i % n for i in range(len(items))]
    random.Random(topic).shuffle(pos)
    probs = []
    seen = set()
    for i, it in enumerate(items, 1):
        pid = f"prob.{topic}.{i:04d}"
        # แม่แบบเดียวกันอาจสุ่มได้ชุดเดิม ถ้าซ้ำกับข้อก่อนหน้าให้เปลี่ยน seed แล้วสุ่มใหม่
        for salt in range(40):
            pr = _build(pid, topic, exam, fmt, it, pos[i - 1], salt)
            # ข้อที่ตัวเลือกเป็นรูปจะมี md เหมือนกันหมด ([[fig2]]…) จึงต้องเทียบภาพจริงด้วย
            key = (pr["stem_md"], tuple(sorted(c["md"] for c in pr["choices"])),
                   tuple(f.get("svg", "") for f in pr.get("figures") or []))
            if key not in seen or it["kind"] != "tpl":
                break
        assert key not in seen, f"{pid}: โจทย์ซ้ำกับข้ออื่นในหัวข้อเดียวกัน"
        seen.add(key)
        probs.append(pr)
    if items:
        _write(DATA / "problems" / f"{topic}.json",
               {"schema_version": "1.0", "topic_id": topic, "problems": probs}, src)
    if lesson:
        assert lesson["topic_id"] == topic
        _write(DATA / "lessons" / f"{topic}.json", lesson, src)
    print(f"  {topic}: บทเรียน {'มี' if lesson else '-'} · โจทย์ {len(probs)} ข้อ")
