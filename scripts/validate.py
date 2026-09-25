"""validate.py — ตรวจฟอร์แมตข้อมูลทั้งหมดใน data/ ตามสเปคในโฟลเดอร์ spec/

นี่คือ "ชั้นที่ 1" ของระบบตรวจในไฟล์ spec/07-quality-and-legal.md

วิธีใช้
    python scripts/validate.py                       ตรวจทุกไฟล์ใน data/
    python scripts/validate.py data/problems/x.json  ตรวจเฉพาะไฟล์ที่ระบุ
    python scripts/validate.py --quiet               แสดงแค่สรุป

รหัสออกจากโปรแกรม: 0 = ผ่าน, 1 = มีรายการต้องแก้
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import providers as P  # noqa: E402
import speclib as S  # noqa: E402


# ============================================================ TOPIC TREE

TOPIC_FIELDS = ["id", "name_th", "name_en", "kind", "parent", "order", "grade_band",
                "requires", "est_minutes", "exam_weight", "difficulty_band", "keywords"]


def validate_topics(paths, rep: S.Report) -> dict:
    """ตรวจผังหัวข้อทุกไฟล์ คืน index {topic_id: topic} เพื่อให้ตัวอื่นใช้ต่อ"""
    index: dict[str, dict] = {}
    for path in paths:
        rep.files_checked += 1
        data = S.load_json(path, rep)
        if data is None:
            continue
        where0 = path.name
        if not S.require(data, ["schema_version", "subject", "subject_name_th",
                                "exam_codes", "topics"], where0, rep):
            continue
        for t in data["topics"]:
            tid = t.get("id", "<ไม่มี id>")
            where = f"{path.name} :: {tid}"
            if not S.require(t, TOPIC_FIELDS, where, rep):
                continue
            if not S.ID_RE.match(tid):
                rep.error(where, "รูปแบบ id ผิด ใช้ได้เฉพาะ a-z 0-9 _ คั่นชั้นด้วยจุด")
            if tid in index:
                rep.error(where, "id ซ้ำกับหัวข้ออื่น")
            S.enum_check(t, "kind", S.TOPIC_KINDS, where, rep)
            S.enum_check(t, "grade_band", S.GRADE_BANDS, where, rep)
            S.enum_check(t, "difficulty_band", S.DIFFICULTY_BANDS, where, rep)
            if not isinstance(t.get("requires"), list):
                rep.error(where, "requires ต้องเป็นอาร์เรย์")
            if not isinstance(t.get("keywords"), list) or not t["keywords"]:
                rep.error(where, "keywords ต้องเป็นอาร์เรย์และมีอย่างน้อย 1 คำ")
            if t.get("kind") == "leaf":
                em = t.get("est_minutes")
                if not isinstance(em, int) or not (10 <= em <= 30):
                    rep.error(where, f"leaf ต้องมี est_minutes ระหว่าง 10-30 (พบ {em})")
            for w in t.get("exam_weight") or []:
                if "exam_code" not in w or "confidence" not in w:
                    rep.error(where, "exam_weight ต้องมี exam_code และ confidence")
                elif w["confidence"] not in S.CONFIDENCE:
                    rep.error(where, f"exam_weight.confidence = {w['confidence']!r} ไม่ถูกต้อง")
                freq = w.get("frequency")
                if freq is not None and not (0 <= freq <= 1):
                    rep.error(where, f"frequency ต้องอยู่ระหว่าง 0 ถึง 1 (พบ {freq})")
            index[tid] = t

    # ตรวจ parent / requires / DAG เมื่อรวมทุกไฟล์แล้ว
    for tid, t in index.items():
        where = f"topics :: {tid}"
        parent = t.get("parent")
        if parent is None:
            if t.get("kind") != "subject":
                rep.error(where, "parent เป็น null ได้เฉพาะ kind = subject")
        elif parent not in index:
            rep.error(where, f"parent {parent!r} ไม่มีอยู่ในผัง")
        elif index[parent].get("kind") == "leaf":
            rep.error(where, f"parent {parent!r} เป็น leaf จึงมีลูกไม่ได้")
        for req in t.get("requires") or []:
            if req not in index:
                rep.error(where, f"requires ชี้ไปหา {req!r} ที่ไม่มีอยู่ในผัง")
            elif index[req].get("kind") != "leaf":
                rep.warn(where, f"requires ควรชี้ไปหา leaf แต่ {req!r} เป็น {index[req].get('kind')}")
        n_req = len(t.get("requires") or [])
        if n_req > 3:
            rep.warn(where, f"requires มี {n_req} ตัว (สเปคแนะนำไม่เกิน 3) ผังอาจรัดตัวเกินไป")

    for cycle in find_cycles(index):
        rep.error("topics :: requires", "พบวงวนใน requires (ผังต้องเป็น DAG): "
                                        + " -> ".join(cycle))

    leaves = [t for t in index.values() if t.get("kind") == "leaf"]
    if leaves:
        no_req = [t["id"] for t in leaves if not (t.get("requires") or [])]
        ratio = len(no_req) / len(leaves)
        if ratio > 0.30:
            rep.warn("topics", f"leaf ที่ไม่มี requires เลยมี {len(no_req)}/{len(leaves)} "
                               f"({ratio:.0%}) เกิน 30% ที่สเปคแนะนำ "
                               "= อาจยังไม่ได้คิดเรื่องพื้นฐานที่ต้องรู้มาก่อน")
    return index


def find_cycles(index: dict) -> list[list[str]]:
    """หาวงวนใน requires ด้วย DFS"""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {k: WHITE for k in index}
    cycles: list[list[str]] = []

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = GREY
        stack.append(node)
        for nxt in index[node].get("requires") or []:
            if nxt not in index:
                continue
            if color[nxt] == GREY:
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for k in index:
        if color[k] == WHITE:
            dfs(k, [])
    return cycles


# ============================================================ FIGURES (ใช้ร่วม)

def validate_figures(figs, where: str, rep: S.Report) -> None:
    if figs is None:
        return
    if not isinstance(figs, list):
        rep.error(where, "figures ต้องเป็นอาร์เรย์ (ไม่มีรูปให้ใส่ [])")
        return
    for fig in figs:
        if "type" not in fig or "alt" not in fig or "id" not in fig:
            rep.error(where, "figure ต้องมี id, type และ alt")
            continue
        if fig["type"] not in S.FIGURE_TYPES:
            rep.error(where, f"figure.type = {fig['type']!r} ไม่ถูกต้อง")
        if fig["type"] == "svg":
            if not fig.get("svg"):
                rep.error(where, f"figure {fig['id']} เป็น svg แต่ไม่มีโค้ด svg")
            elif "currentColor" not in fig["svg"]:
                rep.warn(where, f"figure {fig['id']} ไม่ได้ใช้ currentColor "
                                "อาจมองไม่เห็นในธีมมืด")
        elif not fig.get("description"):
            rep.error(where, f"figure {fig['id']} เป็น needs_drawing แต่ไม่มี description")


# ============================================================ LESSON

LESSON_FIELDS = ["schema_version", "topic_id", "title", "subtitle", "prereq_topic_ids",
                 "objectives", "est_minutes", "blocks", "glossary",
                 "common_exam_patterns", "next_topic_ids", "sources", "review_status"]


def validate_lessons(paths, topics: dict, rep: S.Report) -> None:
    for path in paths:
        rep.files_checked += 1
        data = S.load_json(path, rep)
        if data is None:
            continue
        where0 = path.name
        if not S.require(data, LESSON_FIELDS, where0, rep):
            continue
        tid = data["topic_id"]
        if topics and tid not in topics:
            rep.error(where0, f"topic_id {tid!r} ไม่มีอยู่ในผังหัวข้อ")
        elif topics and topics[tid].get("kind") != "leaf":
            rep.error(where0, f"topic_id {tid!r} ไม่ใช่ leaf จึงมีบทเรียนไม่ได้")
        if path.stem != tid:
            rep.warn(where0, f"ชื่อไฟล์ควรเป็น {tid}.json เพื่อให้ตรงกับ topic_id")
        S.enum_check(data, "review_status", S.REVIEW_STATUS, where0, rep)
        if not (2 <= len(data["objectives"]) <= 5):
            rep.warn(where0, f"objectives มี {len(data['objectives'])} ข้อ "
                             "สเปคแนะนำ 2-5 ข้อ")
        if not data["sources"]:
            rep.error(where0, "sources ว่าง ต้องระบุอ้างอิงอย่างน้อย 1 รายการ")

        seen = set()
        for i, b in enumerate(data["blocks"]):
            where = f"{path.name} :: block[{i}]"
            btype = b.get("type")
            if btype not in S.BLOCK_TYPES:
                rep.error(where, f"type = {btype!r} ไม่อยู่ใน 7 ชนิดที่อนุญาต")
                continue
            seen.add(btype)
            validate_figures(b.get("figures"), where, rep)
            if btype == "hook" and not b.get("body_md"):
                rep.error(where, "hook ต้องมี body_md")
            elif btype == "concept":
                if not b.get("heading") or not b.get("body_md"):
                    rep.error(where, "concept ต้องมี heading และ body_md")
                elif len(b["body_md"].split()) > 400:
                    rep.warn(where, "concept ยาวเกิน ~400 คำ ควรซอยเป็นหลายบล็อก")
            elif btype == "formula":
                for f in ("name", "use_when", "avoid_when"):
                    if not b.get(f):
                        rep.error(where, f"formula ต้องมี {f} (สเปคบังคับ)")
                if "formula_tex" not in b:
                    rep.error(where, "formula ต้องมีฟิลด์ formula_tex (วิชาที่ไม่มีสูตรใส่ \"\")")
            elif btype == "example":
                if not b.get("stem_md") or not b.get("answer_md"):
                    rep.error(where, "example ต้องมี stem_md และ answer_md")
                steps = b.get("steps") or []
                if len(steps) < 2:
                    rep.error(where, "example ต้องมี steps อย่างน้อย 2 ขั้น")
                for j, st in enumerate(steps):
                    if not st.get("do_md") or not st.get("why_md"):
                        rep.error(f"{where}.steps[{j}]",
                                  "ทุกขั้นต้องมีทั้ง do_md และ why_md (สเปคบังคับ)")
                    elif st["do_md"].strip() == st["why_md"].strip():
                        rep.warn(f"{where}.steps[{j}]", "why_md ซ้ำกับ do_md ไม่ได้บอกเหตุผล")
            elif btype == "pitfall":
                for f in ("title", "wrong_md", "why_wrong_md", "correct_md", "misconception_tag"):
                    if not b.get(f):
                        rep.error(where, f"pitfall ต้องมี {f}")
                tag = b.get("misconception_tag")
                if tag and not re.fullmatch(r"[a-z0-9_]+", tag):
                    rep.error(where, f"misconception_tag {tag!r} ต้องเป็น snake_case อังกฤษ")
            elif btype == "summary":
                if not b.get("bullets_md"):
                    rep.error(where, "summary ต้องมี bullets_md")
            elif btype == "check":
                ch = b.get("choices") or []
                if not b.get("question_md") or not ch:
                    rep.error(where, "check ต้องมี question_md และ choices")
                ai = b.get("answer_index")
                if not isinstance(ai, int) or not (0 <= ai < len(ch)):
                    rep.error(where, f"answer_index = {ai!r} อยู่นอกช่วง 0..{len(ch) - 1}")
                if not b.get("explain_md"):
                    rep.error(where, "check ต้องมี explain_md")

        for need in ("concept", "summary", "check"):
            if need not in seen:
                rep.warn(where0, f"ไม่มีบล็อกชนิด {need} ตามโครงที่สเปคแนะนำ")

        # การอ้างรูปด้วย [[figX]] ต้องชี้ไปหารูปที่นิยามไว้จริงในบทเรียนนี้
        defined, referenced = set(), set()
        for b in data["blocks"]:
            for fig in b.get("figures") or []:
                if fig.get("id"):
                    if fig["id"] in defined:
                        rep.error(where0, f"นิยามรูป id {fig['id']!r} ซ้ำสองที่")
                    defined.add(fig["id"])
            for field in ("body_md", "stem_md", "answer_md", "wrong_md",
                          "why_wrong_md", "correct_md", "explain_md", "question_md"):
                referenced.update(re.findall(r"\[\[([A-Za-z0-9_]+)\]\]", b.get(field) or ""))
            for st in b.get("steps") or []:
                for field in ("do_md", "why_md"):
                    referenced.update(re.findall(r"\[\[([A-Za-z0-9_]+)\]\]", st.get(field) or ""))
        for ref in sorted(referenced - defined):
            rep.error(where0, f"เนื้อหาอ้างถึงรูป [[{ref}]] แต่ไม่มีรูป id นี้นิยามไว้ในบทเรียน")
        for unused in sorted(defined - referenced):
            rep.warn(where0, f"นิยามรูป {unused!r} ไว้แต่ไม่มีเนื้อหาอ้างถึงด้วย [[{unused}]]")


# ============================================================ PROBLEM

PROBLEM_FIELDS = ["id", "topic_ids", "primary_topic_id", "exam_code", "origin",
                  "style_ref", "format", "difficulty", "difficulty_signals",
                  "est_seconds", "stem_md", "figures", "choices", "answer_numeric",
                  "solution_steps", "answer_explanation_md", "hints",
                  "distractor_reasons", "misconception_tags", "template",
                  "calculator_allowed", "review_status"]

SIGNAL_FIELDS = ["steps_count", "topics_count", "needs_insight",
                 "heavy_computation", "trap_present", "reading_load"]


def validate_problems(paths, topics: dict, rep: S.Report) -> dict:
    ids: dict[str, str] = {}
    for path in paths:
        rep.files_checked += 1
        data = S.load_json(path, rep)
        if data is None:
            continue
        where0 = path.name
        if not S.require(data, ["schema_version", "topic_id", "problems"], where0, rep):
            continue
        file_topic = data["topic_id"]
        if topics and file_topic not in topics:
            rep.error(where0, f"topic_id {file_topic!r} ไม่มีอยู่ในผังหัวข้อ")
        if path.stem != file_topic:
            rep.warn(where0, f"ชื่อไฟล์ควรเป็น {file_topic}.json")

        by_difficulty: dict[int, int] = {}
        for p in data["problems"]:
            pid = p.get("id", "<ไม่มี id>")
            where = f"{path.name} :: {pid}"
            if not S.require(p, PROBLEM_FIELDS, where, rep):
                continue
            if not S.PROBLEM_ID_RE.match(pid):
                rep.error(where, "รูปแบบ id ผิด ต้องเป็น prob.<topic_id>.<เลข 4 หลัก>")
            if pid in ids:
                rep.error(where, f"id ซ้ำกับใน {ids[pid]}")
            ids[pid] = path.name
            if not pid.startswith(f"prob.{file_topic}."):
                rep.error(where, f"id ต้องขึ้นต้นด้วย prob.{file_topic}.")

            if p["origin"] != "original":
                rep.error(where, f"origin ต้องเป็น 'original' เท่านั้น (พบ {p['origin']!r}) "
                                 "ข้อสอบจริงต้องอยู่ใน data/exams/ ดู spec/09")
            S.enum_check(p, "format", S.PROBLEM_FORMATS, where, rep)
            S.enum_check(p, "review_status", S.REVIEW_STATUS, where, rep)
            validate_figures(p.get("figures"), where, rep)
            validate_problem_figure_refs(p, where, rep)

            if topics:
                for t in p["topic_ids"]:
                    if t not in topics:
                        rep.error(where, f"topic_ids มี {t!r} ที่ไม่มีอยู่ในผังหัวข้อ")
            if p["primary_topic_id"] not in p["topic_ids"]:
                rep.error(where, "primary_topic_id ต้องอยู่ใน topic_ids ด้วย")

            # ความยาก
            sg = p["difficulty_signals"]
            if S.require(sg, SIGNAL_FIELDS, f"{where}.difficulty_signals", rep):
                if sg["reading_load"] not in S.READING_LOAD:
                    rep.error(where, f"reading_load = {sg['reading_load']!r} ไม่ถูกต้อง")
                allowed = S.allowed_difficulty(sg)
                d = p["difficulty"]
                if not isinstance(d, int) or not (1 <= d <= 5):
                    rep.error(where, f"difficulty ต้องเป็น 1-5 (พบ {d!r})")
                elif d not in allowed:
                    gap = min(abs(d - a) for a in allowed)
                    msg = (f"difficulty = {d} ไม่สอดคล้องกับ difficulty_signals "
                           f"(ตาราง C.3 ให้ {sorted(allowed)})")
                    rep.error(where, msg) if gap >= 2 else rep.warn(where, msg)
                by_difficulty[d] = by_difficulty.get(d, 0) + 1

            # ตัวเลือก / คำตอบ
            fmt = p["format"]
            choices = p.get("choices")
            if fmt in ("mcq4", "mcq5", "mcq4_tiered", "multi_select", "ranking"):
                want = {"mcq4": 4, "mcq5": 5, "mcq4_tiered": 4}.get(fmt)
                if not choices:
                    rep.error(where, f"format {fmt} ต้องมี choices")
                else:
                    if want and len(choices) != want:
                        rep.error(where, f"format {fmt} ต้องมี {want} ตัวเลือก (พบ {len(choices)})")
                    n_ans = sum(1 for c in choices if c.get("is_answer"))
                    if fmt == "multi_select":
                        if n_ans < 2:
                            rep.error(where, "multi_select ต้องมีคำตอบถูกตั้งแต่ 2 ตัว")
                    elif n_ans != 1:
                        rep.error(where, f"ต้องมี is_answer = true หนึ่งตัวเท่านั้น (พบ {n_ans})")
                    if fmt == "mcq4_tiered":
                        validate_tiered(choices, where, rep)
                    wrong = {str(i) for i, c in enumerate(choices) if not c.get("is_answer")}
                    got = set(p["distractor_reasons"] or {})
                    if wrong - got:
                        rep.error(where, "distractor_reasons ขาด index "
                                         f"{sorted(wrong - got)} (นับจาก 0)")
                    if got - wrong:
                        rep.error(where, "distractor_reasons มี index ที่ไม่ใช่ตัวเลือกผิด: "
                                         f"{sorted(got - wrong)}")
            elif fmt == "numeric":
                an = p.get("answer_numeric")
                if not an or "value" not in an:
                    rep.error(where, "format numeric ต้องมี answer_numeric.value")
                elif "tolerance" not in an:
                    rep.warn(where, "answer_numeric ควรมี tolerance")

            # เฉลย / คำใบ้
            steps = p["solution_steps"]
            if len(steps) < 2:
                rep.error(where, "solution_steps ต้องมีอย่างน้อย 2 ขั้น")
            for j, st in enumerate(steps):
                if not st.get("do_md") or not st.get("why_md"):
                    rep.error(f"{where}.solution_steps[{j}]",
                              "ทุกขั้นต้องมี do_md และ why_md ที่ไม่ว่าง")
            if not isinstance(p["hints"], list) or len(p["hints"]) != 3:
                rep.error(where, f"hints ต้องมี 3 ระดับเสมอ (พบ {len(p.get('hints') or [])})")
            elif any(not h.strip() for h in p["hints"]):
                rep.error(where, "hints มีข้อที่เป็นข้อความว่าง")
            if not p["answer_explanation_md"]:
                rep.error(where, "answer_explanation_md ว่าง")
            for tag in p["misconception_tags"] or []:
                if not re.fullmatch(r"[a-z0-9_]+", tag):
                    rep.error(where, f"misconception_tags {tag!r} ต้องเป็น snake_case อังกฤษ")

            # โจทย์แม่แบบ
            tpl = p.get("template")
            if tpl is None:
                if not p.get("template_note"):
                    rep.error(where, "template เป็น null ต้องอธิบายเหตุผลใน template_note")
            else:
                validate_template(tpl, where, rep)
                # แม่แบบกับตัวโจทย์ที่เขียนไว้ต้องเป็นเรื่องเดียวกัน
                if tpl.get("answer_kind", "number") != "number":
                    if p.get("answer_numeric") is not None:
                        rep.error(where, f"answer_kind = {tpl['answer_kind']!r} "
                                         "แต่ answer_numeric ไม่เป็น null — "
                                         "คำตอบที่ไม่ใช่ตัวเลขต้องอยู่ใน choices เท่านั้น")
                    if not p.get("choices"):
                        rep.error(where, f"answer_kind = {tpl['answer_kind']!r} "
                                         "ต้องมี choices เพราะคำตอบไม่ใช่ตัวเลข")

        # คำตอบที่ยาวที่สุดบ่อยเกินไป = เดาได้โดยไม่ต้องคิด (คนทำข้อสอบเก่งจับทางนี้ได้เร็ว)
        # ข้ามข้อที่ตัวเลือกเป็นรูปหรือสั้นมาก เพราะความยากไม่ได้อยู่ที่ข้อความ
        longest = shortest = counted = 0
        for p in data["problems"]:
            ch = p.get("choices") or []
            lens = [len(c.get("md", "")) for c in ch]
            if len(lens) < 4 or max(lens) < 25 or any("[[" in c.get("md", "") for c in ch):
                continue
            counted += 1
            ans = [i for i, c in enumerate(ch) if c.get("is_answer")]
            if ans and lens[ans[0]] == max(lens) and lens.count(max(lens)) == 1:
                longest += 1
            if ans and lens[ans[0]] == min(lens) and lens.count(min(lens)) == 1:
                shortest += 1
        if counted >= 4 and longest / counted > 0.5:
            rep.warn(where0, f"คำตอบเป็นตัวเลือกที่ยาวที่สุด {longest}/{counted} ข้อ "
                             "ผู้สอบเดาได้จากความยาว ควรให้ความยาวคละกัน (ไม่เกินครึ่ง)")
        if counted >= 4 and shortest / counted > 0.5:
            rep.warn(where0, f"คำตอบเป็นตัวเลือกที่สั้นที่สุด {shortest}/{counted} ข้อ "
                             "ผู้สอบเดาได้จากความยาว ควรให้ความยาวคละกัน (ไม่เกินครึ่ง)")

        # สัดส่วนความยากต่อไฟล์ — ปรับตามจำนวนข้อจริง
        # สเปคกำหนดสัดส่วน 2:3:4:2:1 ต่อชุด 12 ข้อ วิชาที่ทำแม่แบบไม่ได้ใช้ 20 ข้อ
        total = sum(by_difficulty.values())
        if total >= 8:
            base = {1: 2, 2: 3, 3: 4, 4: 2, 5: 1}
            scale = total / 12
            off = []
            for k, v in base.items():
                want = round(v * scale)
                got = by_difficulty.get(k, 0)
                # ยอมให้คลาดได้ 1 ข้อ บวกอีก 1 ต่อทุก 12 ข้อที่เพิ่มขึ้น
                tolerance = 1 + int(scale)
                if abs(got - want) > tolerance:
                    off.append(f"ระดับ {k}: มี {got} ควรมีราว {want}")
            if off:
                rep.warn(where0, f"สัดส่วนความยากต่างจากสเปค (C.3) เมื่อคิดตาม {total} ข้อ: "
                                 + " | ".join(off))
    return ids


# ฟิลด์ที่เป็นของแม่แบบเลขคณิตเท่านั้น ถ้าใส่มาพร้อม provider จะไม่มีผลอะไร
# ซึ่งอันตรายกว่าผิดพลาดตรง ๆ เพราะคนเขียนจะเข้าใจว่าเงื่อนไขถูกบังคับใช้แล้ว
ARITHMETIC_ONLY = ["vars", "answer_expr", "display", "constraints",
                   "distractors", "quality_exprs", "answer_round"]


def validate_provider_template(tpl: dict, where: str, rep: S.Report) -> None:
    """ตรวจแม่แบบที่คำนวณด้วย provider (คำตอบเป็นข้อความได้ และสร้างรูปได้)

    ตรวจได้โดยไม่ต้องรัน provider จริง — การรันเป็นหน้าที่ของชั้นที่ 2
    """
    w = f"{where}.template"
    name = tpl["provider"]
    mod = P.get(name)
    if mod is None:
        rep.error(w, f"ไม่รู้จัก provider {name!r} — ที่มีคือ {', '.join(P.names()) or '(ยังไม่มี)'}")
        return

    for f in ARITHMETIC_ONLY:
        if f in tpl:
            rep.error(w, f"แม่แบบแบบ provider ใส่ฟิลด์ {f!r} ไม่ได้ "
                         f"เพราะ provider เป็นคนคำนวณเอง ฟิลด์นี้จะถูกเมินเงียบ ๆ")

    kind = tpl.get("answer_kind")
    if kind is None:
        rep.error(w, "แม่แบบแบบ provider ต้องระบุ answer_kind")
    elif kind not in S.ANSWER_KINDS:
        rep.error(w, f"answer_kind = {kind!r} ไม่อยู่ในค่าที่อนุญาต {sorted(S.ANSWER_KINDS)}")
    elif kind != mod.ANSWER_KIND:
        rep.error(w, f"answer_kind = {kind!r} ไม่ตรงกับ provider {name} "
                     f"ที่ให้คำตอบชนิด {mod.ANSWER_KIND!r}")

    params = tpl.get("params")
    if params is None:
        rep.error(w, f"ต้องมี params สำหรับ provider {name}")
        params = {}
    else:
        for problem in mod.validate_params(params):
            rep.error(f"{w}.params", problem)

    # ตรวจว่า {ชื่อ} ใน stem_tpl ตรงกับค่าที่ provider จะคืนมา
    try:
        known = set(mod.var_names(params))
    except Exception as e:  # noqa: BLE001
        rep.error(w, f"provider {name} บอกชื่อตัวแปรไม่ได้: {e}")
        return
    # จับทั้งชื่อแบบอังกฤษและชื่อที่เขียนเป็นภาษาไทย เพราะวงเล็บปีกกาที่มีอักษรไทย
    # ไม่มีทางเป็น LaTeX จึงถือเป็นการอ้างตัวแปรที่พิมพ์ผิดเสมอ
    used = set(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*|[฀-๿][฀-๿\w]*)\}",
                          tpl["stem_tpl"]))
    for u in sorted(used - known):
        rep.error(w, f"stem_tpl อ้าง {{{u}}} แต่ provider {name} ไม่ได้คืนค่าชื่อนี้ "
                     f"(คืนแค่ {', '.join(sorted(known))})")

    if not tpl.get("quality_rules"):
        rep.warn(w, "ไม่มี quality_rules ควรเขียนว่าโจทย์ที่ใช้ได้ต้องเป็นอย่างไร")


def validate_problem_figure_refs(p: dict, where: str, rep: S.Report) -> None:
    """ตรวจว่าการอ้างรูป [[figN]] ในโจทย์ชี้ไปหารูปที่มีอยู่จริง

    กฎเดียวกับที่บทเรียนมีอยู่แล้ว แต่เดิมไม่ได้ตรวจฝั่งโจทย์
    สำคัญขึ้นมากตอนที่ตัวเลือกเป็นรูป (เช่น โจทย์พับกระดาษเจาะรู)
    เพราะถ้ารูปหาย ผู้สอบจะเห็นตัวเลือกว่างเปล่าแล้วเดาไม่ได้เลย
    """
    defined = set()
    for fig in p.get("figures") or []:
        fid = fig.get("id")
        if not fid:
            continue
        if fid in defined:
            rep.error(where, f"นิยามรูป id {fid!r} ซ้ำสองที่")
        defined.add(fid)

    referenced = set()
    texts = [p.get("stem_md") or "", p.get("answer_explanation_md") or ""]
    texts += [c.get("md") or "" for c in (p.get("choices") or [])]
    texts += [str(v) for v in (p.get("distractor_reasons") or {}).values()]
    texts += list(p.get("hints") or [])
    for st in p.get("solution_steps") or []:
        texts += [st.get("do_md") or "", st.get("why_md") or ""]
    for t in texts:
        referenced.update(re.findall(r"\[\[([A-Za-z0-9_]+)\]\]", t))

    for ref in sorted(referenced - defined):
        rep.error(where, f"โจทย์อ้างถึงรูป [[{ref}]] แต่ไม่มีรูป id นี้ในข้อนี้")
    for unused in sorted(defined - referenced):
        rep.warn(where, f"นิยามรูป {unused!r} ไว้แต่ไม่มีข้อความใดอ้างถึงด้วย [[{unused}]]")


def validate_tiered(choices: list, where: str, rep: S.Report) -> None:
    """ตรวจข้อสอบที่ให้คะแนนลดหลั่น (ใช้กับข้อสอบสถานการณ์อย่าง TGAT3)

    ข้อสอบแบบนี้ไม่มีคำว่า "ตัวลวง" ในความหมายเดิม เพราะบางตัวเลือกก็เป็น
    คำตอบที่ยอมรับได้ เพียงแต่ไม่ดีที่สุด การให้คะแนนจึงเป็นตัวสอนเอง
    ว่าอะไรดีกว่าอะไร ถ้าทำเป็นถูก/ผิด จะสอนผิดไปเลย
    """
    scores = []
    for i, c in enumerate(choices):
        if "score" not in c:
            rep.error(f"{where}.choices[{i}]",
                      "format mcq4_tiered ต้องมี score ทุกตัวเลือก "
                      "(0, 0.25, 0.5, 0.75 หรือ 1)")
            return
        s = c["score"]
        if not isinstance(s, (int, float)) or isinstance(s, bool):
            rep.error(f"{where}.choices[{i}]", f"score = {s!r} ต้องเป็นตัวเลข")
            return
        if round(float(s), 4) not in S.TIER_SCORES:
            rep.error(f"{where}.choices[{i}]",
                      f"score = {s} ไม่ใช่ขั้นที่อนุญาต "
                      f"{sorted(S.TIER_SCORES)} (ผังสอบใช้ขั้นละ {S.TIER_STEP})")
            return
        scores.append(float(s))

    best = [i for i, s in enumerate(scores) if s == 1.0]
    if len(best) != 1:
        rep.error(where, f"ต้องมีตัวเลือกที่ได้ 1 คะแนนเพียงตัวเดียว (พบ {len(best)} ตัว)")
    else:
        if not choices[best[0]].get("is_answer"):
            rep.error(where, f"ตัวเลือกที่ได้ 1 คะแนน (ข้อที่ {best[0] + 1}) "
                             "ต้องเป็นตัวที่ is_answer = true ด้วย")
    for i, c in enumerate(choices):
        if c.get("is_answer") and scores[i] != 1.0:
            rep.error(f"{where}.choices[{i}]",
                      f"ตั้ง is_answer = true แต่ score = {scores[i]} ไม่ใช่ 1")

    partial = [s for s in scores if 0 < s < 1]
    if not partial:
        rep.warn(where, "ไม่มีตัวเลือกที่ได้คะแนนบางส่วนเลย "
                        "ถ้าตั้งใจให้เป็นถูก/ผิดล้วน ให้ใช้ format mcq4 แทน")
    # ไม่เตือนกรณีทุกตัวเลือกได้คะแนน เพราะผังสอบ TGAT3 ระบุช่วงคะแนน 0.25-1.00
    # ข้อที่ตัวเลือกได้ 0.25 / 0.5 / 0.75 / 1 ครบสี่ระดับจึงตรงกับรูปแบบข้อสอบจริงพอดี
    if len(set(scores)) < 3:
        rep.warn(where, "คะแนนของตัวเลือกมีไม่ถึง 3 ระดับ "
                        "ข้อแบบนี้สอนเกณฑ์ 'ดีกว่า/ด้อยกว่า' ได้น้อย")


def validate_template(tpl: dict, where: str, rep: S.Report) -> None:
    if tpl.get("provider"):
        validate_provider_template(tpl, where, rep)
        return
    if "answer_kind" in tpl and tpl["answer_kind"] != "number":
        rep.error(f"{where}.template",
                  f"answer_kind = {tpl['answer_kind']!r} ต้องใช้ provider "
                  "เพราะ answer_expr คำนวณได้เฉพาะตัวเลข")
    if not S.require(tpl, ["vars", "stem_tpl", "answer_expr"], f"{where}.template", rep):
        return
    names: list[str] = []
    for v in tpl["vars"]:
        nm = v.get("name")
        if not nm:
            rep.error(f"{where}.template", "vars มีรายการที่ไม่มี name")
            continue
        names.append(nm)
        vtype = v.get("type")
        if vtype in ("int", "float"):
            rng = v.get("range")
            if not (isinstance(rng, list) and len(rng) == 2 and rng[0] < rng[1]):
                rep.error(f"{where}.template.vars[{nm}]",
                          f"range ต้องเป็น [ต่ำสุด, สูงสุด] และต่ำสุด < สูงสุด (พบ {rng!r})")
        elif vtype in ("choice", "name"):
            if not v.get("options"):
                rep.error(f"{where}.template.vars[{nm}]",
                          f"type {vtype} ต้องมี options")
        else:
            rep.error(f"{where}.template.vars[{nm}]",
                      f"type = {vtype!r} ไม่ถูกต้อง (int/float/choice/name)")

    # display: ค่าที่คำนวณไว้แสดงในโจทย์ (เช่น พจน์ของอนุกรมที่มาจาก a1 กับ d)
    display = tpl.get("display") or {}
    if not isinstance(display, dict):
        rep.error(f"{where}.template", "display ต้องเป็นอ็อบเจกต์ {ชื่อ: นิพจน์}")
        display = {}
    known = list(names)
    for dname, dexpr in display.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dname):
            rep.error(f"{where}.template.display", f"ชื่อ {dname!r} ใช้เป็นชื่อตัวแปรไม่ได้")
        if dname in names:
            rep.error(f"{where}.template.display", f"ชื่อ {dname!r} ซ้ำกับตัวแปรใน vars")
        for problem in S.check_expr(dexpr, known):
            rep.error(f"{where}.template.display[{dname}]", problem)
        known.append(dname)
    names = known

    # ตัวแปรที่ประกาศแล้วต้องถูกใช้ที่ใดที่หนึ่ง ไม่จำเป็นต้องอยู่ใน stem_tpl
    # เพราะอาจใช้ผ่าน display, constraints หรือสูตรคำตอบเท่านั้น
    used_in = [tpl["stem_tpl"], tpl["answer_expr"]]
    used_in += list(display.values())
    used_in += list(tpl.get("constraints") or [])
    used_in += [x.get("expr", "") for x in (tpl.get("distractors") or [])]
    used_in += list(tpl.get("quality_exprs") or [])
    used_in += list(tpl.get("hints_tpl") or [])
    used_in += [tpl.get("explanation_tpl") or ""]
    for st in tpl.get("steps_tpl") or []:
        used_in += [st.get("do_md") or "", st.get("why_md") or ""]
    haystack = "\n".join(str(x) for x in used_in)
    for nm in names:
        if not re.search(rf"(?<![A-Za-z0-9_]){re.escape(nm)}(?![A-Za-z0-9_])", haystack):
            rep.warn(f"{where}.template",
                     f"ประกาศตัวแปร {nm} แต่ไม่ได้ใช้ที่ใดเลย (ทั้ง stem_tpl, display, "
                     "constraints, answer_expr และ distractors)")

    for problem in S.check_expr(tpl["answer_expr"], names):
        rep.error(f"{where}.template.answer_expr", problem)
    for i, c in enumerate(tpl.get("constraints") or []):
        for problem in S.check_expr(c, names):
            rep.error(f"{where}.template.constraints[{i}]", problem)
    dis = tpl.get("distractors") or []
    if not dis:
        rep.warn(f"{where}.template", "ไม่มี distractors ระบบจะสร้างตัวเลือกลวงไม่ได้")
    for i, d in enumerate(dis):
        if not d.get("reason"):
            rep.error(f"{where}.template.distractors[{i}]",
                      "ต้องมี reason อธิบายว่าความผิดพลาดแบบไหนทำให้ได้ค่านี้")
        for problem in S.check_expr(d.get("expr", ""), names):
            rep.error(f"{where}.template.distractors[{i}].expr", problem)
    if not tpl.get("quality_rules"):
        rep.warn(f"{where}.template", "ไม่มี quality_rules ควรระบุเงื่อนไขที่ทำให้โจทย์ใช้ได้")
    for i, q in enumerate(tpl.get("quality_exprs") or []):
        for problem in S.check_expr(q, names + ["answer"]):
            rep.error(f"{where}.template.quality_exprs[{i}]", problem)

    validate_explanation_tpl(tpl, where, names, rep)


def validate_explanation_tpl(tpl: dict, where: str, names: list, rep: S.Report) -> None:
    """ตรวจว่าแม่แบบอธิบายโจทย์ที่สุ่มใหม่ได้ด้วยตัวเอง

    ถ้าไม่มีส่วนนี้ ผู้ใช้กดสุ่มแล้วจะได้โจทย์ที่มีแต่คำตอบ ไม่มีวิธีคิด
    ซึ่งใช้ไม่ได้กับคนที่เรียนจาก 0 ที่เป็นกลุ่มเป้าหมายหลักของเว็บ
    """
    w = f"{where}.template"
    known = set(names) | {"answer"}

    steps = tpl.get("steps_tpl")
    if not steps:
        rep.error(w, "ไม่มี steps_tpl — โจทย์ที่สุ่มใหม่จะไม่มีวิธีคิด "
                     "(ห้ามยืมวิธีคิดของข้อต้นฉบับเพราะตัวเลขไม่ตรงกัน)")
    elif not isinstance(steps, list) or len(steps) < 2:
        rep.error(w, f"steps_tpl ต้องเป็นอาร์เรย์ที่มีอย่างน้อย 2 ขั้น (พบ {len(steps or [])})")
    else:
        for i, st in enumerate(steps):
            for field in ("do_md", "why_md"):
                if not (st.get(field) or "").strip():
                    rep.error(f"{w}.steps_tpl[{i}]", f"ต้องมี {field} ที่ไม่ว่าง")

    hints = tpl.get("hints_tpl")
    if not hints:
        rep.error(w, "ไม่มี hints_tpl — โจทย์ที่สุ่มใหม่จะไม่มีคำใบ้")
    elif not isinstance(hints, list) or len(hints) != 3:
        rep.error(w, f"hints_tpl ต้องมี 3 ระดับเสมอ (พบ {len(hints or [])})")
    elif any(not str(h).strip() for h in hints):
        rep.error(w, "hints_tpl มีข้อที่เป็นข้อความว่าง")

    if not (tpl.get("explanation_tpl") or "").strip():
        rep.error(w, "ไม่มี explanation_tpl — โจทย์ที่สุ่มใหม่จะไม่มีคำอธิบายคำตอบ")

    # ทุกช่องแทนค่าที่อ้างต้องมีจริง ไม่อย่างนั้นข้อความจะมี {ชื่อ} ค้างให้ผู้ใช้เห็น
    texts = [tpl.get("explanation_tpl") or ""] + [str(h) for h in (hints or [])]
    for st in steps or []:
        texts += [st.get("do_md") or "", st.get("why_md") or ""]
    unknown = set()
    for t in texts:
        unknown |= S.placeholders(t) - known
    for nm in sorted(unknown):
        rep.error(w, f"เฉลยอ้างช่องแทนค่า {{{nm}}} ที่ไม่มีใน vars, display หรือ 'answer'")


# ============================================================ EXAM PAPER (ฟีเจอร์ C)

EXAM_FIELDS = ["schema_version", "exam_code", "year", "round", "paper_title", "source",
               "license_status", "visibility", "transcription_status", "structure", "items"]

ITEM_FIELDS = ["item_no", "verbatim", "stem_md", "figures", "choices", "official_answer",
               "answer_source", "topic_ids", "primary_topic_id", "difficulty",
               "difficulty_signals", "our_solution_steps", "our_solution_author",
               "misconception_tags", "practice_template_ref"]


def validate_exams(paths, topics: dict, problem_ids: dict, rep: S.Report) -> None:
    for path in paths:
        rep.files_checked += 1
        data = S.load_json(path, rep)
        if data is None:
            continue
        where0 = path.name
        if not S.require(data, EXAM_FIELDS, where0, rep):
            continue
        S.enum_check(data, "license_status", S.LICENSE_STATUS, where0, rep)
        S.enum_check(data, "visibility", S.VISIBILITY, where0, rep)
        S.enum_check(data, "transcription_status", S.TRANSCRIPTION_STATUS, where0, rep)

        src = data["source"] or {}
        if src.get("kind") not in S.SOURCE_KINDS:
            rep.error(where0, f"source.kind = {src.get('kind')!r} ไม่ถูกต้อง")
        has_trace = bool(src.get("source_url") or src.get("file_ref"))
        if data["transcription_status"] == "checked" and not has_trace:
            rep.error(where0, "transcription_status = 'checked' แต่ไม่มี source_url หรือ "
                              "file_ref ให้ย้อนตรวจ (spec/09 ข้อ 3.2)")
        if data["visibility"] == "public" and data["license_status"] != "official_public":
            rep.error(where0, f"visibility = 'public' แต่ license_status = "
                              f"{data['license_status']!r} — สเปค 09 ข้อ 1 ให้เปิดสาธารณะ "
                              "เฉพาะชุดที่เป็น official_public")
        if data["visibility"] != "internal_only" and data["transcription_status"] == "raw":
            rep.warn(where0, "ชุดนี้ยังเป็น raw (ยังไม่มีคนเทียบต้นฉบับ) แต่ตั้งให้ผู้ใช้เห็นแล้ว")

        n_declared = (data.get("structure") or {}).get("num_items")
        if n_declared and len(data["items"]) != n_declared:
            rep.warn(where0, f"structure.num_items = {n_declared} แต่มี items "
                             f"{len(data['items'])} ข้อ")

        seen_no = set()
        for it in data["items"]:
            no = it.get("item_no", "?")
            where = f"{path.name} :: ข้อ {no}"
            if not S.require(it, ITEM_FIELDS, where, rep):
                continue
            if no in seen_no:
                rep.error(where, "item_no ซ้ำ")
            seen_no.add(no)
            S.enum_check(it, "answer_source", S.ANSWER_SOURCES, where, rep)
            if it["our_solution_author"] not in ("ai_draft", "human_verified"):
                rep.error(where, f"our_solution_author = {it['our_solution_author']!r} ไม่ถูกต้อง")
            validate_figures(it.get("figures"), where, rep)

            if it["stem_md"] is None:
                if not it.get("notes"):
                    rep.error(where, "stem_md เป็น null ต้องเขียนใน notes ว่าทำไม "
                                     "(เช่น อ่านไม่ออก) ห้ามเดาเนื้อโจทย์")
                if it["topic_ids"]:
                    rep.warn(where, "stem_md เป็น null แต่ tag หัวข้อไว้ — "
                                    "spec/09 ข้อ 5.2 ห้ามเดาว่าโจทย์ถามอะไร")
                continue

            if topics:
                for t in it["topic_ids"]:
                    if t not in topics:
                        rep.error(where, f"topic_ids มี {t!r} ที่ไม่มีอยู่ในผังหัวข้อ")
            if it["topic_ids"] and it["primary_topic_id"] not in it["topic_ids"]:
                rep.error(where, "primary_topic_id ต้องอยู่ใน topic_ids")
            sg = it.get("difficulty_signals") or {}
            if S.require(sg, SIGNAL_FIELDS, f"{where}.difficulty_signals", rep):
                allowed = S.allowed_difficulty(sg)
                if it["difficulty"] not in allowed:
                    rep.warn(where, f"difficulty = {it['difficulty']} ไม่สอดคล้องกับ signals "
                                    f"(ตาราง C.3 ให้ {sorted(allowed)})")
            for j, st in enumerate(it["our_solution_steps"] or []):
                if not st.get("do_md") or not st.get("why_md"):
                    rep.error(f"{where}.our_solution_steps[{j}]",
                              "ทุกขั้นต้องมี do_md และ why_md")
            ref = it.get("practice_template_ref")
            if ref and problem_ids and ref not in problem_ids:
                rep.error(where, f"practice_template_ref ชี้ไปหา {ref!r} "
                                 "ที่ไม่มีอยู่ใน data/problems/")


# ============================================================ main

def collect(root: pathlib.Path):
    topics = sorted((root / "topics").glob("*.topics.json")) if (root / "topics").is_dir() else []
    lessons = sorted((root / "lessons").glob("*.json")) if (root / "lessons").is_dir() else []
    problems = sorted((root / "problems").glob("*.json")) if (root / "problems").is_dir() else []
    exams = []
    if (root / "exams").is_dir():
        exams = sorted(p for p in (root / "exams").glob("*.json") if p.parent.name == "exams")
    return topics, lessons, problems, exams


def main() -> int:
    S.utf8_stdout()
    ap = argparse.ArgumentParser(description="ตรวจฟอร์แมตข้อมูลตามสเปคใน spec/")
    ap.add_argument("paths", nargs="*", help="ไฟล์ที่ต้องการตรวจ (ไม่ระบุ = ตรวจทั้ง data/)")
    ap.add_argument("--data", default=None, help="โฟลเดอร์ data (ปกติหาให้อัตโนมัติ)")
    ap.add_argument("--quiet", action="store_true", help="แสดงแค่สรุป")
    args = ap.parse_args()

    root = pathlib.Path(args.data) if args.data else S.data_root()
    rep = S.Report()

    if not root.is_dir():
        print(f"ไม่พบโฟลเดอร์ data ที่ {root}")
        print("สร้างโฟลเดอร์ data/topics, data/lessons, data/problems, data/exams ก่อน")
        return 1

    all_topics, all_lessons, all_problems, all_exams = collect(root)

    # ผังหัวข้อต้องโหลดทั้งหมดเสมอ เพราะทุกอย่างอ้างถึงมัน
    topics_index = validate_topics(all_topics, rep)
    if not topics_index:
        rep.warn("data/topics", "ยังไม่มีผังหัวข้อ จึงข้ามการตรวจว่า topic_id มีจริงหรือไม่ "
                               "— สร้างผังหัวข้อก่อนด้วย spec/04-prompt-topic-tree.md")

    if args.paths:
        sel = [pathlib.Path(p) for p in args.paths]
        lessons = [p for p in sel if "lessons" in p.parts]
        problems = [p for p in sel if "problems" in p.parts]
        exams = [p for p in sel if "exams" in p.parts]
    else:
        lessons, problems, exams = all_lessons, all_problems, all_exams

    validate_lessons(lessons, topics_index, rep)
    problem_ids = validate_problems(problems, topics_index, rep)
    validate_exams(exams, topics_index, problem_ids, rep)

    if not args.quiet:
        print(f"ผังหัวข้อ: {len(all_topics)} ไฟล์ ({len(topics_index)} หัวข้อ)")
        print(f"บทเรียน:  {len(lessons)} ไฟล์")
        print(f"โจทย์:    {len(problems)} ไฟล์ ({len(problem_ids)} ข้อ)")
        print(f"ข้อสอบจริง: {len(exams)} ไฟล์")
    return rep.print_summary("ผลตรวจชั้นที่ 1 (ฟอร์แมต)")


if __name__ == "__main__":
    sys.exit(main())
