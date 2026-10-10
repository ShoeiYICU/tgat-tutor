from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEED = 2569
RNG = random.Random(SEED)


def load_problems():
    items = []
    for path in sorted((ROOT / "data" / "problems").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for p in data.get("problems", []):
            if p.get("exam_code") in {"TGAT1", "TGAT2", "TGAT3", "TPAT3"}:
                items.append(p)
    return items


def ids_from_reports(names, prefixes):
    found = set()
    pattern = re.compile(r"prob\.(?:tgat1|tgat2|tgat3|tpat3)\.[A-Za-z0-9_.]+")
    for name in names:
        path = ROOT / "งานสำหรับ-codex" / name
        if not path.exists():
            continue
        for pid in pattern.findall(path.read_text(encoding="utf-8")):
            if any(pid.startswith(prefix) for prefix in prefixes):
                found.add(pid.rstrip("."))
    return found


def select_stratified(pool, total, risk_ids, risk_total, max_figures=None):
    chosen = []
    topic_counts = Counter()
    diff_counts = Counter()
    exam_counts = Counter()
    shuffled = list(pool)
    RNG.shuffle(shuffled)

    def pick(candidates, count):
        nonlocal chosen
        for _ in range(count):
            candidates = [p for p in candidates if p not in chosen]
            if max_figures is not None:
                used = sum(bool(p.get("figures")) for p in chosen)
                if used >= max_figures:
                    candidates = [p for p in candidates if not p.get("figures")]
            if not candidates:
                raise RuntimeError("ตัวเลือกไม่พอสำหรับเงื่อนไขการสุ่ม")
            best = min(
                candidates,
                key=lambda p: (
                    topic_counts[p["primary_topic_id"]],
                    diff_counts[p["difficulty"]],
                    exam_counts[p["exam_code"]],
                    shuffled.index(p),
                ),
            )
            chosen.append(best)
            topic_counts[best["primary_topic_id"]] += 1
            diff_counts[best["difficulty"]] += 1
            exam_counts[best["exam_code"]] += 1

    pick([p for p in shuffled if p["id"] in risk_ids], risk_total)
    pick([p for p in shuffled if p["id"] not in risk_ids], total - risk_total)
    return chosen


def clean(text):
    value = str(text or "").replace("\r\n", "\n").strip()
    return re.sub(r"\[\[(fig\d+)\]\]", r"รูป \1 (ดูรูปด้านบน)", value)


def render_figures(problem):
    figures = problem.get("figures") or []
    if not figures:
        return ""
    out = ["", "**รูปประกอบ**", ""]
    for fig in figures:
        out.append(f"*{fig.get('id', 'รูป')} — {clean(fig.get('alt', ''))}*")
        svg = fig.get("svg") or fig.get("svg_md")
        if svg:
            out.extend(["", svg, ""])
    return "\n".join(out)


def render_problem(problem, number, risk, kind):
    lines = [f"### ข้อ {number} · {problem['id']}", ""]
    lines.extend([clean(problem.get("stem_md")), render_figures(problem), "", "**ตัวเลือก**", ""])
    for i, choice in enumerate(problem.get("choices", []), 1):
        mark = " — **✓ คำตอบที่คลังถือว่าถูก**" if choice.get("is_answer") else ""
        score = f" · คะแนน {choice.get('score'):g}" if kind == "TGAT3" and choice.get("score") is not None else ""
        lines.append(f"{i}. {clean(choice.get('md'))}{score}{mark}")
    lines.extend(["", f"**เหตุผลที่คลังให้:** {clean(problem.get('answer_explanation_md'))}", ""])
    if kind == "TGAT3":
        lines.extend(["ผู้ตรวจ:  [ ] ถูกต้อง ใช้ได้   [ ] ใช้ได้แต่ควรปรับ   [ ] ผิด หรือมีคำตอบถูกมากกว่าหนึ่ง", "", "[ ] ลำดับคะแนนสมเหตุผล   [ ] ควรสลับลำดับ: ____________________", ""])
    else:
        lines.extend(["ผู้ตรวจ:  [ ] ถูกต้อง ใช้ได้   [ ] ใช้ได้แต่ควรปรับ   [ ] ผิด หรือมีคำตอบถูกมากกว่าหนึ่ง", ""])
        if kind == "TGAT1":
            lines.extend(["[ ] เป็นภาษาที่คนพูดจริง   [ ] ถูกไวยากรณ์แต่ไม่เป็นธรรมชาติ", ""])
    lines.extend(["ถ้าไม่ใช่ช่องแรก โปรดเขียนสั้น ๆ: ______________________________________________", "", "---", ""])
    return "\n".join(lines)


def write_set(filename, title, audience, items, risk_ids, kind):
    lines = [f"# {title}", "", f"ผู้ตรวจที่เหมาะ: {audience}", "", f"ชุดนี้สุ่มแบบแบ่งชั้นด้วย seed `{SEED}` จำนวน {len(items)} ข้อ โดยไม่ได้คัดเฉพาะข้อที่ดูดี หนึ่งในสามมาจากกลุ่มที่เคยมีความเสี่ยงหรือถูกแก้ไข", "", "กรุณาทำเครื่องหมายจากข้อความและรูปที่เห็น หากไม่แน่ใจให้เลือก “ใช้ได้แต่ควรปรับ” และเขียนเหตุผลสั้น ๆ", "", "---", ""]
    for i, item in enumerate(items, 1):
        lines.append(render_problem(item, i, item["id"] in risk_ids, kind))
    lines.extend(["## ข้อมูลการสุ่มซ้ำ", "", f"- seed: `{SEED}`", f"- จำนวนข้อ: {len(items)}", f"- กลุ่มเสี่ยง: {sum(p['id'] in risk_ids for p in items)}", "- id ที่เลือก:", ""])
    lines.extend(f"  - `{p['id']}`" for p in items)
    (OUT / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    problems = load_problems()
    risk_tgat1 = ids_from_reports(
        ["รายงาน-รอบ10.md", "รายงาน-รอบ14.md", "รายงาน-รอบ18.md"],
        ["prob.tgat1."],
    )
    risk_tgat3 = ids_from_reports(
        ["รายงาน-รอบ14.md", "รายงาน-รอบ17.md"],
        ["prob.tgat3."],
    )
    for p in problems:
        if p.get("exam_code") == "TGAT3" and re.search(r"ความปลอดภัย|อันตราย|ฉุกเฉิน|คุกคาม|ทำร้าย", p.get("stem_md", "")):
            risk_tgat3.add(p["id"])
    risk_math = ids_from_reports(
        ["รายงาน-รอบ7.md", "รายงาน-รอบ8.md", "รายงาน-รอบ9.md", "รายงาน-รอบ10.md", "รายงาน-รอบ11.md", "รายงาน-รอบ12.md"],
        ["prob.tgat2.", "prob.tpat3."],
    )
    for p in problems:
        if p.get("primary_topic_id") == "tpat3.aptitude.numerical.estimation_engineering":
            risk_math.add(p["id"])

    tgat1_pool = [p for p in problems if p.get("exam_code") == "TGAT1"]
    tgat3_pool = [p for p in problems if p.get("exam_code") == "TGAT3"]
    math_pool = [p for p in problems if p.get("exam_code") in {"TGAT2", "TPAT3"}]
    set1 = select_stratified(tgat1_pool, 30, risk_tgat1, 10)
    set2 = select_stratified(tgat3_pool, 24, risk_tgat3, 8)
    set3 = select_stratified(math_pool, 24, risk_math, 8, max_figures=8)

    write_set("1-TGAT1-ภาษาอังกฤษ.md", "ชุดตรวจ TGAT1 ภาษาอังกฤษ", "ครูภาษาอังกฤษหรือเจ้าของภาษา", set1, risk_tgat1, "TGAT1")
    write_set("2-TGAT3-ข้อสถานการณ์.md", "ชุดตรวจ TGAT3 ข้อสถานการณ์", "ครูแนะแนวหรือครูด้านสมรรถนะ", set2, risk_tgat3, "TGAT3")
    write_set("3-TGAT2-และ-TPAT3.md", "ชุดตรวจ TGAT2 และ TPAT3", "ครูคณิตศาสตร์หรือครูฟิสิกส์", set3, risk_math, "MATH")

    manifest = {
        "seed": SEED,
        "sets": {
            "TGAT1": [p["id"] for p in set1],
            "TGAT3": [p["id"] for p in set2],
            "TGAT2_TPAT3": [p["id"] for p in set3],
        },
    }
    (OUT / "รายการสุ่ม.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
