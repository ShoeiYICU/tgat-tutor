"""build_site.py — แปลงข้อมูลใน data/ ให้เป็นไฟล์ที่เว็บ (web/) อ่านได้

เว็บเป็นเว็บนิ่ง (static) ไม่มีเซิร์ฟเวอร์ ไม่มีฐานข้อมูล จึงวางบนโฮสต์ฟรีได้
(GitHub Pages / Netlify / Cloudflare Pages) และไม่มีค่าใช้จ่ายรายเดือน

ปัญหาคือ provider เขียนด้วย Python แต่เว็บรันบนเบราว์เซอร์
ทางแก้: **สุ่มโจทย์ล่วงหน้าตอน build** ข้อละหลายสิบแบบ แล้วเก็บเป็น JSON
ผู้ใช้กด "สุ่มโจทย์ใหม่" ก็คือหยิบแบบถัดไปจากชุดนี้ ซึ่งผ่านเกณฑ์คุณภาพชุดเดียวกับ stress test แล้ว

วิธีใช้
    python scripts/build_site.py                 สร้าง web/data/ ใหม่ทั้งหมด (TGAT และ TPAT3)
    python scripts/build_site.py --variants 60   จำนวนแบบที่สุ่มล่วงหน้าต่อโจทย์แม่แบบ 1 ข้อ

กฎความปลอดภัยที่โค้ดนี้บังคับ
    - อ่านเฉพาะ data/topics, data/lessons, data/problems
    - **ไม่แตะ data/exams/ และ all_data/ เด็ดขาด** เพราะเป็นข้อสอบจริงที่ห้ามเผยแพร่
    - ข้อที่ origin ไม่ใช่ "original" จะไม่ถูกส่งออก
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import render_template as R  # noqa: E402

DATA = ROOT / "data"
OUT = ROOT / "web" / "data"
SUBJECTS = ["tgat1", "tgat2", "tgat3", "tpat3"]
LETTERS = "กขคงจ"


# ------------------------------------------------------------ แปลงโจทย์หนึ่งข้อ

def public_problem(p: dict) -> dict:
    """ตัดเหลือเฉพาะฟิลด์ที่หน้าเว็บต้องใช้ (ไม่ส่ง template หรือข้อมูลภายในออกไป)"""
    choices = p.get("choices") or []
    ans = [i for i, c in enumerate(choices) if c.get("is_answer")]
    out = {
        "id": p["id"],
        "format": p["format"],
        "difficulty": p["difficulty"],
        "est_seconds": p.get("est_seconds"),
        "stem_md": p["stem_md"],
        "figures": [{k: f.get(k) for k in ("id", "svg", "alt", "caption")}
                    for f in p.get("figures") or []],
        "choices": [c["md"] for c in choices],
        "answer_index": ans[0] if ans else None,
        "steps": p.get("solution_steps") or [],
        "explanation_md": p.get("answer_explanation_md") or "",
        "hints": p.get("hints") or [],
        "why_wrong": p.get("distractor_reasons") or {},
    }
    if p["format"] == "mcq4_tiered":
        out["scores"] = [c.get("score", 0) for c in choices]
    return out


def variant_from_item(base_id: str, n: int, p: dict, tpl: dict, item: dict,
                      rng: random.Random) -> dict:
    """ประกอบโจทย์ที่สุ่มใหม่ให้หน้าตาเหมือนโจทย์ปกติ (ตรรกะเดียวกับตอนสร้างไฟล์โจทย์)"""
    fig_by_value = {}
    if "answer_fig" in item:
        fig_by_value[item["answer"]] = item["answer_fig"]
        for d in item["distractors"]:
            if d.get("fig"):
                fig_by_value[d["value"]] = d["fig"]

    def render(val):
        fid = fig_by_value.get(val)
        if fid:
            return f"[[{fid}]]"
        txt = R.format_value(val, item["unit"], tpl.get("answer_round"))
        # ตัวเลขล้วนแสดงเป็นคณิตศาสตร์ ให้หน้าตาเหมือนข้อต้นฉบับที่สร้างจาก author.py
        if isinstance(val, (int, float)) and not isinstance(val, bool) and not item["unit"]:
            return f"${txt}$"
        return txt

    entries = [(item["answer"], True, None)] + [
        (d["value"], False, d["reason"]) for d in item["distractors"]]
    rng.shuffle(entries)
    choices, why, ans = [], {}, None
    for i, (val, is_ans, reason) in enumerate(entries):
        choices.append(render(val))
        if is_ans:
            ans = i
        else:
            why[str(i)] = reason
    return {
        "id": f"{base_id}~{n}",
        "format": p["format"],
        "difficulty": p["difficulty"],
        "est_seconds": p.get("est_seconds"),
        "stem_md": item["stem"],
        "figures": [{k: f.get(k) for k in ("id", "svg", "alt", "caption")}
                    for f in item.get("figures") or []],
        "choices": choices,
        "answer_index": ans,
        "steps": item["steps"],
        "explanation_md": item["explanation"],
        "hints": item["hints"],
        "why_wrong": why,
    }


MIN_VARIANTS = 4          # ต่ำกว่านี้ผู้ใช้จะเจอโจทย์ซ้ำเร็วเกินไป
BYTE_BUDGET = 30_000      # เพดานขนาดของแบบสุ่มต่อโจทย์หนึ่งข้อ (ข้อที่มีรูปจะได้จำนวนแบบน้อยลง)


def variants(p: dict, count: int) -> list[dict]:
    """สุ่มโจทย์ใหม่จากแม่แบบ เก็บเฉพาะแบบที่ไม่ซ้ำและผ่านเกณฑ์คุณภาพ

    ข้อที่ตัวเลือกเป็นรูปจะมี SVG ติดมาด้วยทุกแบบ จึงจำกัดด้วยขนาดไบต์เพิ่มอีกชั้น
    เพื่อไม่ให้ไฟล์ข้อมูลใหญ่จนโหลดช้าบนเน็ตมือถือ
    """
    tpl = p.get("template")
    if not tpl:
        return []
    rng = random.Random(p["id"])  # seed คงที่ → build ซ้ำได้ผลเดิม
    seen, out, used = set(), [], 0
    for _ in range(count * 40):
        if len(out) >= count or (len(out) >= MIN_VARIANTS and used >= BYTE_BUDGET):
            break
        item, _why = R.make_item(tpl, rng)
        if item is None or R.quality_problems(item, tpl) or R.explanation_problems(item, tpl):
            continue
        key = (item["stem"], str(item["answer"]),
               json.dumps(item.get("figures"), ensure_ascii=False, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        v = variant_from_item(p["id"], len(out) + 1, p, tpl, item, rng)
        used += len(json.dumps(v, ensure_ascii=False))
        out.append(v)
    return out


# ------------------------------------------------------------------ ส่งออก

def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: pathlib.Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")


def _exam_groups() -> dict:
    """id ข้อ → ชื่อกลุ่ม จากไฟล์จัดกลุ่มที่ผู้ตรวจอีกฝ่ายทำไว้ (ไม่มีไฟล์ก็ไม่จัดกลุ่ม)"""
    path = DATA / "exam_groups.json"
    if not path.exists():
        return {}
    out = {}
    for g in json.loads(path.read_text(encoding="utf-8"))["groups"]:
        for pid in g["ids"]:
            assert pid not in out, f"exam_groups.json: {pid} อยู่มากกว่าหนึ่งกลุ่ม"
            out[pid] = g["id"]
    return out


EXAM_GROUP = _exam_groups()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", type=int, default=12)
    args = ap.parse_args()

    if OUT.exists():
        shutil.rmtree(OUT)

    catalog = {"subjects": []}
    n_lessons = n_prob = n_var = 0

    for s in SUBJECTS:
        tf = load(DATA / "topics" / f"{s}.topics.json")
        topics = []
        exam_pool: list[dict] = []
        for t in tf["topics"]:
            tid = t["id"]
            entry = {k: t.get(k) for k in ("id", "name_th", "name_en", "kind", "parent",
                                           "order", "est_minutes", "requires")}
            entry["weight"] = "; ".join(w.get("typical_items", "")
                                        for w in t.get("exam_weight") or [])
            if t["kind"] == "subject":
                entry["notes"] = t.get("notes")

            lp = DATA / "lessons" / f"{tid}.json"
            if lp.exists():
                lesson = load(lp)
                dump(OUT / "lessons" / f"{tid}.json", lesson)
                entry["lesson"] = True
                n_lessons += 1

            pp = DATA / "problems" / f"{tid}.json"
            if pp.exists():
                probs = [p for p in load(pp)["problems"] if p.get("origin") == "original"]
                items = []
                for p in probs:
                    base = public_problem(p)
                    base["variants"] = variants(p, args.variants)
                    n_var += len(base["variants"])
                    items.append(base)
                dump(OUT / "problems" / f"{tid}.json", {"topic_id": tid, "items": items})
                entry["problems"] = len(items)
                entry["templated"] = sum(1 for p in items if p["variants"])
                n_prob += len(items)
                # เก็บไว้ทำไฟล์รวมสำหรับโหมดสอบเสมือน (ไม่มีแบบสุ่ม จึงเล็กกว่ามาก)
                # group = ข้อที่ใช้บทอ่านหรือสถานการณ์เดียวกัน (data/exam_groups.json) ชุดสอบจะสุ่มกลุ่มละไม่เกินหนึ่งข้อ
                exam_pool.extend({**{k: v for k, v in it.items() if k != "variants"},
                                  "topic": tid,
                                  **({"group": EXAM_GROUP[it["id"]]} if it["id"] in EXAM_GROUP else {})}
                                 for it in items)
            topics.append(entry)

        # โหมดสอบเสมือนดึงไฟล์เดียวแทนการดึงไฟล์รายหัวข้อหลายสิบไฟล์
        dump(OUT / "exam" / f"{s}.json", {"subject": s, "items": exam_pool})

        catalog["subjects"].append({
            "id": s,
            "name_th": tf["subject_name_th"],
            "exam_codes": tf.get("exam_codes"),
            "topics": topics,
        })

    # ตัวเลขสรุปสำหรับหน้าเบื้องหลัง (หน้าเว็บจะได้ไม่ต้องนับเอง)
    catalog["stats"] = {"lessons": n_lessons, "problems": n_prob, "variants": n_var,
                        "topics": sum(len(x["topics"]) for x in catalog["subjects"])}
    dump(OUT / "catalog.json", catalog)
    print(f"web/data: บทเรียน {n_lessons} · โจทย์ {n_prob} ข้อ · แบบสุ่มล่วงหน้า {n_var} แบบ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
