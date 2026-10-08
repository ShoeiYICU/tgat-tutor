"""ตัวตรวจงานตัวเองสำหรับ Codex — รันก่อนเขียนรายงานทุกรอบ

    python scripts/codex_selfcheck.py                  เทียบกับ commit ล่าสุด (HEAD)
    python scripts/codex_selfcheck.py --base 8249064   เทียบกับ commit ที่ระบุ
    python scripts/codex_selfcheck.py --md             พิมพ์ตารางพร้อมวางในรายงาน

อ่านอย่างเดียว ไม่แก้ไฟล์ใด ตัวเลขทุกตัวนับจากไฟล์ที่ build แล้วใน data/
ใช้นิยามเดียวกับที่ Claude ใช้ตรวจ ตัวเลขในรายงานของสองฝ่ายจึงตรงกัน

สิ่งที่ตรวจ (เลขข้อตรงกับ งานสำหรับ-codex/เกณฑ์ตรวจงานตัวเองก่อนส่ง.md)
    5.3  ไฟล์ที่เปลี่ยนอยู่ในขอบเขตของ Codex ทั้งหมด
    5.5  รายชื่อโจทย์และบทเรียนที่เปลี่ยนจริง แยกว่าเปลี่ยนส่วนใด
    2.1  คำตอบยาวที่สุดหรือสั้นที่สุดเกินครึ่งของหัวข้อ
    2.2  คำตอบเป็นค่ากลางของตัวเลือกเกินครึ่งของหัวข้อ
    2.3  ข้อที่มีตัวลวงคำเด็ดขาดตั้งแต่ 2 ตัว
    1.7  คำอธิบายเฉลยที่ไม่มีเหตุผล
    3.4  misconception_tags ของโจทย์ที่ไม่มี pitfall รองรับ (รายงานเฉย ๆ ไม่นับเป็นไม่ผ่าน)
    3.7  กับดักต่อบทเกิน 4 ตัว และกับดักที่ชื่อซ้ำกับเนื้อหา
    3.6  สูตรที่มี formula_tex แต่ variables ว่าง
    3.2  คำถามท้ายบทที่ answer_index ไม่ชี้ตัวเลือกจริง หรือมีตัวเลือกซ้ำ

สิ่งที่ตัวตรวจนี้ทำไม่ได้ และต้องทำด้วยมือ: คำตอบถูกไหม มีคำตอบเดียวไหม ตัวลวงผิดเพราะข้อเท็จจริงใด
กฎในบทเรียนมีข้อยกเว้นไหม — ผ่านตัวตรวจนี้ไม่ได้แปลว่างานถูก
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODEX_SOURCES = ("content/tgat1/", "content/tgat3/", "content/eng/", "content/tpat3/thinking.py",
                 "content/tpat3/numeric_fluid_energy.py", "content/tpat3/aptitude_lessons.py")
CODEX_GENERATED_FROM = ("content/tgat1/", "content/tgat3/", "content/eng/", "thinking.py", "numeric_fluid_energy.py", "aptitude_lessons.py")
REPORT_DIR = "งานสำหรับ-codex/"

ABSOLUTE = re.compile(r"เสมอ|แน่นอน|ทันที|ทุกคน|ทุกกรณี|ทุกชนิด|ทุกตัว|เท่านั้น|อย่างเดียว"
                      r"|\b(?:always|never|all|only|every)\b", re.IGNORECASE)
REASON = re.compile(r"เพราะ|จาก|because", re.IGNORECASE)
MAX_PITFALLS = 4


def git(*args: str) -> str:
    out = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=ROOT, capture_output=True)
    return out.stdout.decode("utf-8", errors="replace")


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_at(base: str, rel: str):
    raw = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=ROOT, capture_output=True).stdout
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001 — ไฟล์ใหม่ที่ยังไม่มีใน base
        return None


def choice_number(md: str):
    if "[[" in md:
        return None
    m = re.fullmatch(r"[^\d-]*(-?\d[\d,]*(?:\.\d+)?)\D*", md.replace("$", "").replace("\\,", "").strip())
    return float(m.group(1).replace(",", "")) if m else None


def codex_topics() -> set[str]:
    """หัวข้อที่ Codex เป็นเจ้าของ ดูจาก generated_from ของบทเรียน"""
    owned = set()
    for f in sorted((ROOT / "data/lessons").glob("*.json")):
        gen = str(load(f).get("generated_from") or "")
        if any(k in gen for k in CODEX_GENERATED_FROM):
            owned.add(f.stem)
    return owned


def codex_problem_file(path: pathlib.Path, owned: set[str]) -> bool:
    """โจทย์ของหัวข้อที่ Codex เขียนบทเรียน แต่สร้างจากตัวสร้างของ Claude (มี template.provider) ไม่นับเป็นของ Codex"""
    if path.stem not in owned:
        return False
    return not any((p.get("template") or {}).get("provider") for p in load(path)["problems"])


def is_codex_path(rel: str, owned: set[str]) -> bool:
    if rel.startswith(REPORT_DIR) or any(rel.startswith(s) for s in CODEX_SOURCES):
        return True
    m = re.fullmatch(r"data/(?:lessons|problems)/(.+)\.json", rel)
    return bool(m and m.group(1) in owned)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--md", action="store_true", help="พิมพ์ตารางมาร์กดาวน์สำหรับวางในรายงาน")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    owned = codex_topics()
    rows: list[tuple[str, str, str]] = []   # (เกณฑ์, ผล, รายละเอียด)
    detail: list[str] = []

    # ---------- 5.3 ขอบเขตไฟล์
    changed = [ln[3:].strip().strip('"') for ln in git("status", "--porcelain").splitlines() if ln.strip()]
    changed += [p for p in git("diff", "--name-only", args.base).splitlines() if p.strip()]
    changed = sorted({p.split(" -> ")[-1] for p in changed})
    outside = [p for p in changed if not is_codex_path(p, owned) and not p.startswith("web/data/")]
    rows.append(("5.3 ไฟล์อยู่ในขอบเขต", "ผ่าน" if not outside else "ไม่ผ่าน",
                 f"เปลี่ยน {len(changed)} ไฟล์ · นอกขอบเขต {len(outside)}"))
    detail += [f"  นอกขอบเขต: {p}" for p in outside]
    web_built = [p for p in changed if p.startswith("web/data/")]
    if web_built:
        rows.append(("5.6 ไม่รัน build_site.py", "ไม่ผ่าน", f"web/data เปลี่ยน {len(web_built)} ไฟล์"))

    # ---------- 5.5 สิ่งที่เปลี่ยนจริง
    item_changes = collections.Counter()
    changed_items, option_changed = [], []
    for f in sorted((ROOT / "data/problems").glob("*.json")):
        if not codex_problem_file(f, owned):
            continue
        old = load_at(args.base, f"data/problems/{f.name}")
        old_by = {p["id"]: p for p in (old or {}).get("problems", [])}
        for p in load(f)["problems"]:
            o = old_by.get(p["id"])
            if o == p:
                continue
            changed_items.append(p["id"])
            if o is None:
                item_changes["ข้อใหม่"] += 1
                continue
            keys = [k for k in p if p[k] != o.get(k)]
            for k in keys:
                item_changes[k] += 1
            if "choices" in keys or "stem_md" in keys:
                option_changed.append(p["id"])
    lesson_changes = collections.Counter()
    changed_lessons = []
    for f in sorted((ROOT / "data/lessons").glob("*.json")):
        if f.stem not in owned:
            continue
        old = load_at(args.base, f"data/lessons/{f.name}")
        new = load(f)
        if old == new:
            continue
        changed_lessons.append(f.stem)
        old_blocks = [json.dumps(b, ensure_ascii=False, sort_keys=True) for b in (old or {}).get("blocks", [])]
        for b in new["blocks"]:
            if json.dumps(b, ensure_ascii=False, sort_keys=True) not in old_blocks:
                lesson_changes[b["type"]] += 1
    rows.append(("5.5 โจทย์ที่เปลี่ยน", "ข้อมูล", f"{len(changed_items)} ข้อ · โจทย์หรือตัวเลือกเปลี่ยน {len(option_changed)} ข้อ · "
                 + (", ".join(f"{k} {v}" for k, v in item_changes.most_common()) or "ไม่มี")))
    rows.append(("5.5 บทเรียนที่เปลี่ยน", "ข้อมูล", f"{len(changed_lessons)} บท · บล็อกที่เปลี่ยนหรือเพิ่ม: "
                 + (", ".join(f"{k} {v}" for k, v in lesson_changes.most_common()) or "ไม่มี")))
    detail += ["  ต้องทำเองโดยปิดเฉลย (เกณฑ์ 1.1–1.6): " + pid for pid in option_changed]

    # ---------- เกณฑ์รายหัวข้อของโจทย์
    longest_bad, median_bad, multi_abs, no_reason = [], [], [], []
    n_items = n_dis = n_abs_dis = n_abs_ans = 0
    for f in sorted((ROOT / "data/problems").glob("*.json")):
        if not codex_problem_file(f, owned):
            continue
        probs = load(f)["problems"]
        counted = longest = shortest = numeric = median = 0
        for p in probs:
            ch = p.get("choices") or []
            ans = [i for i, c in enumerate(ch) if c.get("is_answer")]
            if not ch or not ans:
                continue
            n_items += 1
            a = ans[0]
            lens = [len(c.get("md", "")) for c in ch]
            if len(lens) >= 4 and max(lens) >= 25 and not any("[[" in c.get("md", "") for c in ch):
                counted += 1
                longest += lens[a] == max(lens) and lens.count(max(lens)) == 1
                shortest += lens[a] == min(lens) and lens.count(min(lens)) == 1
            vals = [choice_number(c.get("md", "")) for c in ch]
            if len(ch) == 5 and None not in vals and len(set(vals)) == 5:
                numeric += 1
                median += sorted(vals).index(vals[a]) == 2
            hits = 0
            for i, c in enumerate(ch):
                h = bool(ABSOLUTE.search(c.get("md", "")))
                if i == a:
                    n_abs_ans += h
                else:
                    n_dis += 1
                    n_abs_dis += h
                    hits += h
            if hits >= 2:
                multi_abs.append(p["id"])
            if not REASON.search(p.get("answer_explanation_md") or ""):
                no_reason.append(p["id"])
        if counted >= 4 and (longest / counted > 0.5 or shortest / counted > 0.5):
            longest_bad.append(f"{f.stem} (ยาวสุด {longest}/{counted} · สั้นสุด {shortest}/{counted})")
        if numeric >= 6 and median / numeric > 0.5:
            median_bad.append(f"{f.stem} ({median}/{numeric})")
    rows.append(("2.1 คำตอบยาวสุดหรือสั้นสุด", "ผ่าน" if not longest_bad else "ไม่ผ่าน", f"หัวข้อที่เกินครึ่ง {len(longest_bad)}"))
    rows.append(("2.2 คำตอบเป็นค่ากลาง", "ผ่าน" if not median_bad else "ไม่ผ่าน", f"หัวข้อที่เกินครึ่ง {len(median_bad)}"))
    rows.append(("2.3 ตัวลวงคำเด็ดขาด", "ผ่าน" if not multi_abs else "ต้องตัดสินรายข้อ",
                 f"ตัวลวง {n_abs_dis}/{n_dis} · คำตอบ {n_abs_ans}/{n_items} · ข้อที่มีตั้งแต่ 2 ตัว {len(multi_abs)}"))
    rows.append(("1.7 คำอธิบายเฉลยมีเหตุผล", "ผ่าน" if not no_reason else "ไม่ผ่าน", f"ไม่มี เพราะ/จาก/because {len(no_reason)} ข้อ"))
    detail += [f"  ยาวสุดหรือสั้นสุด: {x}" for x in longest_bad] + [f"  ค่ากลาง: {x}" for x in median_bad]
    detail += [f"  คำเด็ดขาด ≥ 2 ตัว (คงไว้ได้ถ้าเป็นเนื้อหาของข้อ ต้องเขียนเหตุผล): {x}" for x in multi_abs]
    detail += [f"  ไม่มีเหตุผลในเฉลย: {x}" for x in no_reason]

    # ---------- บทเรียน
    too_many, dup_title, no_vars, bad_check, tag_gap = [], [], [], [], []
    for f in sorted((ROOT / "data/lessons").glob("*.json")):
        if f.stem not in owned:
            continue
        blocks = load(f)["blocks"]
        pits = [b for b in blocks if b["type"] == "pitfall"]
        if len(pits) > MAX_PITFALLS:
            too_many.append(f"{f.stem} ({len(pits)} ตัว)")
        for b in pits:
            if b["title"].strip() == b["wrong_md"].strip():
                dup_title.append(f"{f.stem} · {b['misconception_tag']}")
        for b in blocks:
            if b["type"] == "formula" and (b.get("formula_tex") or "").strip() and not b.get("variables"):
                no_vars.append(f"{f.stem} · {b['name']}")
            if b["type"] == "check":
                ch = b.get("choices") or []
                if not (0 <= b.get("answer_index", -1) < len(ch)) or len(set(ch)) != len(ch):
                    bad_check.append(f"{f.stem} · {b['question_md'][:40]}")
        pf = ROOT / "data/problems" / f.name
        if pf.exists():
            have = {b.get("misconception_tag") for b in pits}
            miss = sorted({t for p in load(pf)["problems"] for t in (p.get("misconception_tags") or [])} - have)
            if miss:
                tag_gap.append(f"{f.stem}: {', '.join(miss)}")
    rows.append((f"3.7 กับดักไม่เกิน {MAX_PITFALLS} ตัวต่อบท", "ผ่าน" if not too_many else "ไม่ผ่าน", f"บทที่เกิน {len(too_many)}"))
    rows.append(("3.7 ชื่อกับดักไม่ซ้ำกับเนื้อหา", "ผ่าน" if not dup_title else "ไม่ผ่าน", f"กับดักที่ title = wrong_md {len(dup_title)} ตัว"))
    rows.append(("3.6 สูตรมี variables", "ผ่าน" if not no_vars else "ไม่ผ่าน", f"สูตรที่มี formula_tex แต่ variables ว่าง {len(no_vars)}"))
    rows.append(("3.2 คำถามท้ายบทรูปแบบถูก", "ผ่าน" if not bad_check else "ไม่ผ่าน", f"ผิดรูปแบบ {len(bad_check)} ข้อ"))
    rows.append(("3.4 tag ที่ไม่มีกับดักรองรับ", "ข้อมูล", f"{len(tag_gap)} บท (ไม่ต้องเพิ่มกับดักเพื่อให้ชื่อตรงอย่างเดียว)"))
    detail += [f"  กับดักเกิน: {x}" for x in too_many] + [f"  ชื่อซ้ำเนื้อหา: {x}" for x in dup_title[:40]]
    if len(dup_title) > 40:
        detail.append(f"  … และอีก {len(dup_title) - 40} ตัว")
    detail += [f"  สูตรไม่มี variables: {x}" for x in no_vars] + [f"  คำถามท้ายบท: {x}" for x in bad_check]
    detail += [f"  tag ไม่มีกับดักรองรับ (ข้อมูล): {x}" for x in tag_gap]

    # ---------- พิมพ์ผล
    print(f"ตัวตรวจงานตัวเองของ Codex · เทียบกับ {args.base} · หัวข้อในขอบเขต {len(owned)} · โจทย์ {n_items} ข้อ\n")
    if args.md:
        print("| เกณฑ์ | ผล | ตัวเลข |\n|---|---|---|")
        for name, res, info in rows:
            print(f"| {name} | {res} | {info} |")
    else:
        for name, res, info in rows:
            print(f"[{res:^14}] {name}: {info}")
    if detail:
        print("\nรายละเอียด")
        print("\n".join(detail))
    failed = [r for r in rows if r[1] == "ไม่ผ่าน"]
    print(f"\n=> {'มีเกณฑ์ที่ไม่ผ่าน ' + str(len(failed)) + ' ข้อ' if failed else 'ผ่านทุกเกณฑ์ที่ตรวจด้วยเครื่องได้'} "
          "(คำตอบถูกและมีคำตอบเดียวหรือไม่ ต้องตรวจด้วยมือ)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
