"""generate.py — ผลิตบทเรียนและโจทย์เป็นชุดด้วย Claude API แล้วบังคับให้ผ่านตัวตรวจก่อนรับ

นี่คือตัวที่ทำให้ผลิต 1,500 หัวข้อได้จริงในเวลาที่เป็นไปได้
แต่ **ของที่ยิงมาไม่ได้เข้า data/ อัตโนมัติ** ต้องผ่านสองด่านก่อน
  ด่าน 1  validate.py            ฟอร์แมตถูกตามสเปค
  ด่าน 2  render_template.py     แม่แบบรันได้ 200 รอบไม่พัง เฉลยไม่รั่ว
ถ้าไม่ผ่าน ไฟล์จะไปอยู่ data/_generate/rejected/ พร้อมผลตรวจ ให้คนดูว่าทำไม

ต่างจากสคริปต์อื่นในโฟลเดอร์นี้: ไฟล์นี้ **ต้องติดตั้งไลบรารีเพิ่ม**
    pip install anthropic
สคริปต์ตรวจงาน (validate / render_template / selftest / sync_status / cube_net)
ยังใช้ไลบรารีมาตรฐานล้วนเหมือนเดิม จึงรันได้ทุกเครื่องโดยไม่ต้องติดตั้งอะไร

## วิธีใช้

    python scripts/generate.py --plan
        ดูว่าหัวข้อไหนยังไม่มีบทเรียน/โจทย์ ไม่เรียก API ไม่เสียเงิน

    python scripts/generate.py --topic <topic_id> --kind lesson --dry-run
        ประกอบคำสั่งจริงแล้วพิมพ์ออกมา พร้อมประเมินค่าใช้จ่าย ไม่เรียก API

    python scripts/generate.py --topic <topic_id> --kind lesson
        ยิงหัวข้อเดียว รอผล ใช้ตอนจูนคำสั่ง

    python scripts/generate.py --kind problems --batch --limit 20
        ยิงเป็นชุดผ่าน Batches API ถูกลงครึ่งราคา เหมาะกับงานก้อนใหญ่

    python scripts/generate.py --collect <batch_id>
        เก็บผลของ batch ที่ส่งไว้แล้ว (ถ้าปิดเครื่องไประหว่างรอ)

## กฎที่ฝังไว้ในสคริปต์ ไม่ใช่แค่ในคำสั่ง

1. ห้ามเขียนอะไรลง data/exams/ เด็ดขาด — คลังข้อสอบจริงต้องมาจากไฟล์ต้นฉบับเท่านั้น
   ไม่ใช่จากความจำของ AI (ความเสียหายอันดับ 0 ใน spec/07)
2. ไฟล์ที่ไม่ผ่านตัวตรวจไม่เข้า data/ แม้แต่ชั่วคราว
3. ไม่ทับไฟล์ที่มีอยู่แล้ว ถ้าอยากทำใหม่ต้องลบของเดิมเองก่อน
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import speclib as S  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
PROJ = HERE.parent
SPEC = PROJ / "spec"

# ---------------------------------------------------------------- ค่าตั้งต้น

# ค่าเริ่มต้นใช้รุ่นที่เก่งที่สุด เพราะงานนี้พลาดแล้วแพงกว่าค่า token
# (เฉลยผิดที่หลุดไปถึงเด็กเสียหายกว่าส่วนต่างราคามาก)
DEFAULT_MODEL = "claude-opus-5"

# ราคาต่อ 1 ล้าน token (ดอลลาร์) — อัปเดตเมื่อราคาเปลี่ยน
PRICES = {
    "claude-opus-5": (5.00, 25.00),
    "claude-fable-5-1": (10.00, 50.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.10
BATCH_MULT = 0.50

WORKDIR = PROJ / "data" / "_generate"
STATE_PATH = WORKDIR / "state.json"


# ---------------------------------------------------------------- สถานะงาน

def load_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"runs": [], "batches": {}}


def save_state(state: dict) -> None:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def record(state: dict, entry: dict) -> None:
    state["runs"].append(entry)
    save_state(state)


# ---------------------------------------------------------------- อ่านผังหัวข้อ

def load_topics(root: pathlib.Path) -> dict:
    rep = S.Report()
    out: dict[str, dict] = {}
    tdir = root / "topics"
    if not tdir.is_dir():
        return out
    for path in sorted(tdir.glob("*.topics.json")):
        data = S.load_json(path, rep)
        if not data:
            continue
        # หมายเหตุระดับวิชาสำคัญมาก เพราะเป็นที่เก็บกฎอย่าง "วิชานี้ใช้ mcq5 ไม่ใช่ mcq4"
        # ถ้าไม่ส่งต่อไปให้ AI จะได้ไฟล์ที่จำนวนตัวเลือกผิดทั้งชุด
        subject_note = next((t.get("notes") for t in data.get("topics") or []
                             if t.get("kind") == "subject"), None)
        for t in data.get("topics") or []:
            t = dict(t)
            t["_subject"] = data.get("subject")
            t["_exam_codes"] = data.get("exam_codes")
            t["_subject_name_th"] = data.get("subject_name_th")
            t["_subject_note"] = subject_note
            t["_source_note"] = data.get("source_note")
            out[t["id"]] = t
    if rep.errors:
        rep.print_summary("อ่านผังหัวข้อไม่สำเร็จ")
        raise SystemExit(1)
    return out


def pending(root: pathlib.Path, topics: dict, kind: str, subject: str | None) -> list[str]:
    """คืน topic_id ของ leaf ที่ยังไม่มีไฟล์ประเภทนี้ เรียงตาม order"""
    folder = root / ("lessons" if kind == "lesson" else "problems")
    have = {p.stem for p in folder.glob("*.json")} if folder.is_dir() else set()
    rows = [t for t in topics.values()
            if t.get("kind") == "leaf" and t["id"] not in have
            and (subject is None or t.get("_subject") == subject)]
    rows.sort(key=lambda t: (t.get("_subject") or "", t.get("order") or 0, t["id"]))
    return [t["id"] for t in rows]


# ---------------------------------------------------------------- ย่อตัวอย่าง

def compact(data: dict, keep: int) -> dict:
    """ย่อไฟล์ตัวอย่างให้เล็กลงก่อนใส่ในคำสั่ง

    ตัดสองอย่าง
      - เนื้อ SVG ที่ยาวมาก (เหลือหมายเหตุ) เพราะโครงสำคัญกว่าพิกัด
      - จำนวนข้อ (เหลือกระจายตามระดับความยาก) เพราะโครงซ้ำกันทุกข้อ
    ทำให้ค่า token ต่อครั้งลดลงหลายเท่าโดยยังสอนรูปแบบได้ครบ
    """
    out = json.loads(json.dumps(data, ensure_ascii=False))

    def strip_svg(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "svg" and isinstance(v, str) and len(v) > 200:
                    node[k] = "<svg …ตัดเนื้อรูปออกเพื่อประหยัดที่ สร้างด้วยสคริปต์…/>"
                else:
                    strip_svg(v)
        elif isinstance(node, list):
            for v in node:
                strip_svg(v)

    strip_svg(out)

    if "problems" in out and keep and len(out["problems"]) > keep:
        # เลือกให้กระจายระดับความยาก ไม่ใช่เอาแต่ข้อแรก ๆ ซึ่งง่ายทั้งหมด
        by_diff: dict[int, list] = {}
        for p in out["problems"]:
            by_diff.setdefault(p.get("difficulty", 0), []).append(p)
        picked, i = [], 0
        while len(picked) < keep:
            added = False
            for d in sorted(by_diff):
                if i < len(by_diff[d]) and len(picked) < keep:
                    picked.append(by_diff[d][i])
                    added = True
            if not added:
                break
            i += 1
        out["problems"] = picked
        out["_note"] = (f"ตัวอย่างนี้ตัดมา {len(picked)} ข้อจากไฟล์จริงที่มี "
                        f"{len(data['problems'])} ข้อ เพื่อให้เห็นรูปแบบ")
    return out


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- ประกอบคำสั่ง

RULES = """คุณกำลังผลิตเนื้อหาสำหรับเว็บติวสอบเข้ามหาวิทยาลัยของไทย (TCAS)
ผู้ใช้เป้าหมายคือเด็กไทย ม.ปลาย ที่ไม่มีเงินเรียนคอร์ส และเริ่มจากศูนย์จริง ๆ

กฎที่ละเมิดไม่ได้
1. ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอธิบายนอก JSON ห้ามมีคอมเมนต์ ห้ามมีคอมมาเกิน
2. ห้ามนึกข้อสอบจริงจากความจำแล้วอ้างว่าเป็นข้อสอบจริง เด็ดขาด
   ทุกอย่างที่คุณแต่งคือ "แนวข้อสอบ" ไม่ใช่ข้อสอบจริง
   ถ้าจะอ้างอิงปีหรือข้อ ให้ใส่ใน style_ref.note ว่าเป็นแนวข้อสอบเท่านั้น
3. ห้ามยืนยันโครงสร้างข้อสอบ สัดส่วนคะแนน หรือคะแนนต่ำสุดของคณะ
   ถ้าไม่มีข้อมูลในคำสั่งนี้ ให้เว้นไว้ ห้ามเดา
4. ใช้เฉพาะ topic_id ที่ให้มาในคำสั่ง ห้ามคิด topic_id ใหม่
5. review_status ต้องเป็น "ai_draft" เสมอ (หรือ "ai_draft_needs_fact_check"
   ถ้าเนื้อหามีปี พ.ศ. ชื่อบุคคล เลขมาตรา หรือข้อเท็จจริงที่ต้องตรวจ)
6. LaTeX ใช้ $...$ กับ $$...$$ และ backslash ใน JSON ต้อง escape เป็น \\\\ ทุกที่

สิ่งที่ตัวตรวจอัตโนมัติจะจับได้ทันทีถ้าคุณทำพลาด — เสียเวลาทั้งสองฝ่าย
- ความยาก (difficulty) ไม่ตรงกับ difficulty_signals ตามตาราง C.3
- hints ไม่ครบ 3 ระดับ หรือ solution_steps มีขั้นที่ไม่มี why_md
- distractor_reasons ไม่ครบทุกตัวเลือกที่ผิด
- แม่แบบที่ไม่มี steps_tpl / hints_tpl / explanation_tpl
- คำใบ้ที่มีค่าคำตอบอยู่ในข้อความ
- นิพจน์ที่ใช้ฟังก์ชันนอกรายการที่อนุญาต
"""


def spec_slice(name: str, start: str | None = None, end: str | None = None) -> str:
    text = (SPEC / name).read_text(encoding="utf-8")
    if start:
        i = text.find(start)
        if i >= 0:
            text = text[i:]
    if end:
        j = text.find(end)
        if j >= 0:
            text = text[:j]
    return text.strip()


def build_system(kind: str, root: pathlib.Path) -> list[dict]:
    """ประกอบ system prompt เป็นบล็อก โดยวาง cache_control ไว้บล็อกท้ายสุด

    ทุกบล็อกต้องเหมือนกันเป๊ะทุกครั้งที่ยิง ไม่งั้นแคชแตกแล้วจ่ายเต็มราคาทุกครั้ง
    จึงห้ามใส่เวลา ชื่อหัวข้อ หรืออะไรที่เปลี่ยนไปในนี้ — ของพวกนั้นไปอยู่ใน user message
    """
    schema = spec_slice("03-schema.md")
    if kind == "lesson":
        prompt_spec = spec_slice("05-prompt-lesson.md")
        exemplars = [
            ("บทเรียนหัวข้อที่มีสูตร", root / "lessons" /
             "tgat2.numerical.series.constant_difference.json"),
            ("บทเรียนหัวข้อที่ไม่มีสูตร ใช้ขั้นตอนการคิดแทน", root / "lessons" /
             "tgat2.language.communication.analogy_semantic.json"),
        ]
        keep = 0
    else:
        prompt_spec = spec_slice("06-prompt-problems.md")
        exemplars = [
            ("โจทย์ที่มีแม่แบบเลขคณิต พร้อมเฉลยที่แทนค่าได้", root / "problems" /
             "tgat2.numerical.series.constant_difference.json"),
            ("โจทย์ที่ใช้ provider เพราะคำตอบไม่ใช่ตัวเลขและต้องมีรูป", root / "problems" /
             "tgat2.spatial.box_folding.net_opposites.json"),
            ("โจทย์ที่ทำแม่แบบไม่ได้จริง ๆ จึงใช้ template null", root / "problems" /
             "tgat2.language.communication.analogy_semantic.json"),
        ]
        keep = 4

    parts = [
        {"type": "text", "text": RULES},
        {"type": "text", "text": "# สเปคข้อมูล (กฎตายตัว)\n\n" + schema},
        {"type": "text", "text": "# คำสั่งงานโดยละเอียด\n\n" + prompt_spec},
    ]

    shown = []
    for label, path in exemplars:
        if not path.is_file():
            continue
        body = json.dumps(compact(read_json(path), keep), ensure_ascii=False, indent=2)
        shown.append(f"## ตัวอย่างที่ผ่านตัวตรวจแล้ว — {label}\n\n```json\n{body}\n```")
    if shown:
        parts.append({
            "type": "text",
            "text": ("# ตัวอย่างงานที่รับแล้ว ใช้เป็นมาตรฐานคุณภาพ\n\n"
                     "ทุกไฟล์ด้านล่างผ่าน validate.py และ render_template.py --stress แล้ว\n"
                     "ให้ลอกระดับความละเอียดและวิธีเขียน why_md ตามนี้\n\n"
                     + "\n\n".join(shown)),
        })

    # แคชทุกอย่างที่คงที่ — บล็อกท้ายสุดคือจุดตัดแคช
    parts[-1] = dict(parts[-1], cache_control={"type": "ephemeral", "ttl": "1h"})
    return parts


def topic_brief(topic: dict, topics: dict) -> str:
    """ข้อมูลหัวข้อที่ต้องบอก AI รวมหัวข้อที่ต้องรู้ก่อน"""
    lines = [
        f"- topic_id: {topic['id']}",
        f"- ชื่อหัวข้อ: {topic.get('name_th')} ({topic.get('name_en')})",
        f"- วิชา: {topic.get('_subject_name_th')} ({topic.get('_subject')})",
        f"- exam_code ที่ใช้: {', '.join(topic.get('_exam_codes') or [])}",
        f"- ระดับชั้น: {topic.get('grade_band')}",
        f"- ความยากของหัวข้อ: {topic.get('difficulty_band')}",
        f"- เวลาที่ควรสอนจบ: {topic.get('est_minutes')} นาที",
        f"- คำค้น: {', '.join(topic.get('keywords') or [])}",
    ]
    parent = topics.get(topic.get("parent") or "")
    if parent:
        lines.append(f"- อยู่ใต้หัวข้อ: {parent.get('name_th')} ({parent['id']})")
    reqs = [topics[r]["name_th"] for r in (topic.get("requires") or []) if r in topics]
    if reqs:
        lines.append(f"- ผู้เรียนควรรู้เรื่องนี้มาก่อน: {', '.join(reqs)}")
    if topic.get("notes"):
        lines.append(f"- หมายเหตุของหัวข้อนี้: {topic['notes']}")
    if topic.get("_subject_note"):
        lines.append(f"\n## กฎระดับวิชา (สำคัญ ต้องทำตาม)\n{topic['_subject_note']}")
    if topic.get("_source_note"):
        lines.append(f"\n## โครงสอบที่ยืนยันแล้ว (ใช้เป็นข้อเท็จจริงได้)\n"
                     f"{topic['_source_note']}\n"
                     "ข้อมูลนอกเหนือจากนี้ห้ามเดา ถ้าไม่มีให้เว้นไว้")
    return "\n".join(lines)


def build_user(kind: str, topic: dict, topics: dict, n_problems: int) -> str:
    brief = topic_brief(topic, topics)
    if kind == "lesson":
        want = ("เขียน **บทเรียน 1 ไฟล์** สำหรับหัวข้อนี้ ตามโครง lesson ในสเปคส่วน B\n"
                "ตอบเป็น JSON ของไฟล์บทเรียนทั้งไฟล์ เริ่มด้วย { และจบด้วย }")
    else:
        want = (f"แต่งโจทย์ **{n_problems} ข้อ** สำหรับหัวข้อนี้ ตามโครง problem ในสเปคส่วน C\n"
                "ตอบเป็น JSON ของไฟล์โจทย์ทั้งไฟล์ เริ่มด้วย { และจบด้วย }\n"
                "ทุกข้อที่ทำแม่แบบได้ ต้องมี template พร้อม steps_tpl / hints_tpl / "
                "explanation_tpl ครบ")
    return f"# หัวข้อที่ต้องทำ\n\n{brief}\n\n# สิ่งที่ต้องส่ง\n\n{want}\n"


# ---------------------------------------------------------------- โครงคำตอบ

def output_schema(kind: str) -> dict:
    """JSON schema บังคับรูปคำตอบ — กันปัญหา "มีข้อความปนมาใน JSON" ตั้งแต่ต้นทาง

    บังคับแค่ระดับซองจดหมาย ส่วนกฎลึก (ความยากตรงกับสัญญาณ เฉลยไม่รั่ว)
    ปล่อยให้ validate.py กับ render_template.py ตรวจ เพราะเขียนเป็น schema ไม่ได้
    """
    if kind == "lesson":
        return {
            "type": "object",
            "properties": {
                "schema_version": {"type": "string"},
                "topic_id": {"type": "string"},
                "title": {"type": "string"},
                "review_status": {"type": "string"},
                "blocks": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["schema_version", "topic_id", "title", "review_status", "blocks"],
            "additionalProperties": True,
        }
    return {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string"},
            "topic_id": {"type": "string"},
            "problems": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["schema_version", "topic_id", "problems"],
        "additionalProperties": True,
    }


# ---------------------------------------------------------------- ค่าใช้จ่าย

def estimate_tokens(text: str) -> int:
    """ประเมินจำนวน token แบบหยาบ ๆ สำหรับข้อความไทยผสมอังกฤษ

    ไม่แม่น ใช้ดูขนาดคร่าว ๆ ก่อนยิงเท่านั้น เลขจริงมาจาก response.usage
    ภาษาไทยกินหลาย token ต่อตัวอักษรมากกว่าอังกฤษ จึงใช้ตัวหารต่ำไว้ก่อน
    """
    return max(1, len(text) // 3)


def cost_of(model: str, usage: dict, batch: bool) -> float:
    price_in, price_out = PRICES.get(model, PRICES[DEFAULT_MODEL])
    mult = BATCH_MULT if batch else 1.0
    fresh = usage.get("input_tokens", 0)
    c_write = usage.get("cache_creation_input_tokens", 0)
    c_read = usage.get("cache_read_input_tokens", 0)
    out = usage.get("output_tokens", 0)
    dollars = (
        fresh * price_in
        + c_write * price_in * CACHE_WRITE_MULT
        + c_read * price_in * CACHE_READ_MULT
        + out * price_out
    ) / 1_000_000
    return dollars * mult


def usage_dict(usage) -> dict:
    keys = ("input_tokens", "output_tokens",
            "cache_creation_input_tokens", "cache_read_input_tokens")
    return {k: (getattr(usage, k, None) or 0) for k in keys}


# ---------------------------------------------------------------- ตรวจแล้วรับ

def gate(kind: str, topic_id: str, body: dict, root: pathlib.Path) -> tuple[bool, str]:
    """เอาไฟล์ที่ได้ไปตรวจในสำเนาชั่วคราวของ data/ คืน (ผ่านไหม, ผลตรวจ)

    ตรวจในสำเนา ไม่ใช่ใน data/ จริง เพราะของที่ยังไม่ผ่านไม่ควรแตะข้อมูลจริง
    แม้แต่ชั่วคราว — ถ้าเครื่องดับกลางทางจะเหลือไฟล์เสียคาไว้
    """
    folder = "lessons" if kind == "lesson" else "problems"
    logs = []
    with tempfile.TemporaryDirectory(prefix="addmission_gen_") as tmp:
        td = pathlib.Path(tmp) / "data"
        shutil.copytree(root, td, ignore=shutil.ignore_patterns("_generate", "raw"))
        target = td / folder / f"{topic_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")

        checks = [
            ("ด่าน 1 ฟอร์แมต", [sys.executable, str(HERE / "validate.py"),
                                "--data", str(td)]),
            ("ด่าน 2 รันแม่แบบ", [sys.executable, str(HERE / "render_template.py"),
                                  "--stress", "--data", str(td)]),
        ]
        for label, cmd in checks:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            logs.append(f"===== {label} (exit {r.returncode}) =====\n{r.stdout}{r.stderr}")
            if r.returncode != 0:
                return False, "\n\n".join(logs)
    return True, "\n\n".join(logs)


def accept(kind: str, topic_id: str, body: dict, root: pathlib.Path) -> pathlib.Path:
    folder = root / ("lessons" if kind == "lesson" else "problems")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{topic_id}.json"
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def reject(kind: str, topic_id: str, raw: str, log: str, why: str) -> pathlib.Path:
    d = WORKDIR / "rejected"
    d.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    # ต่อชื่อเป็นสตริง ห้ามใช้ with_suffix เพราะ topic_id มีจุดคั่นอยู่แล้ว
    # with_suffix จะไปแทนที่เวลาที่ต่อท้าย ทำให้การปฏิเสธครั้งหลังทับครั้งแรก
    stem = f"{topic_id}.{kind}.{stamp}"
    out = d / (stem + ".json")
    out.write_text(raw, encoding="utf-8")
    (d / (stem + ".log.txt")).write_text(f"เหตุผล: {why}\n\n{log}", encoding="utf-8")
    return out


def parse_body(text: str) -> tuple[dict | None, str]:
    """แกะ JSON ออกจากคำตอบ เผื่อกรณีที่ยังมีข้อความหรือรั้ว code fence ปนมา"""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None, "ไม่พบ JSON ในคำตอบ"
    try:
        return json.loads(t[i:j + 1]), ""
    except json.JSONDecodeError as e:
        return None, f"JSON ไม่ถูกต้อง (บรรทัด {e.lineno} คอลัมน์ {e.colno}): {e.msg}"


# ---------------------------------------------------------------- เรียก API

def make_client():
    try:
        import anthropic
    except ImportError:
        print("ไฟล์นี้ต้องติดตั้งไลบรารีเพิ่มก่อน:\n\n    pip install anthropic\n")
        print("(สคริปต์ตรวจงานตัวอื่นไม่ต้องติดตั้งอะไร ใช้ได้เลยเหมือนเดิม)")
        raise SystemExit(2)
    return anthropic, anthropic.Anthropic()


def request_params(kind: str, system: list, user: str, model: str, max_tokens: int) -> dict:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": "high",
            "format": {"type": "json_schema", "schema": output_schema(kind)},
        },
    }


def call_one(anthropic_mod, client, params: dict, use_fallbacks: bool):
    """ยิงหนึ่งครั้งแบบ streaming แล้วคืน message

    ใช้ streaming เพราะ max_tokens สูง (ไฟล์โจทย์ยาว) ถ้าไม่สตรีมจะชน timeout ของ HTTP
    ถอย 2 ชั้นถ้าเซิร์ฟเวอร์ไม่รับพารามิเตอร์ที่เป็น beta หรือของใหม่
    เพราะ API เปลี่ยนเร็วกว่าสคริปต์นี้ และงานต้องไม่ค้างเพราะพารามิเตอร์เสริม
    """
    attempts = []
    if use_fallbacks:
        attempts.append(("พร้อม fallbacks", dict(params),
                         {"betas": ["server-side-fallback-2026-07-01"],
                          "fallbacks": "default"}))
    attempts.append(("ปกติ", dict(params), None))
    stripped = dict(params)
    stripped["output_config"] = {"effort": "high"}
    attempts.append(("ไม่บังคับโครง JSON", stripped, None))

    last = None
    for label, p, extra in attempts:
        try:
            if extra:
                with client.beta.messages.stream(**p, **extra) as stream:
                    return stream.get_final_message(), label
            with client.messages.stream(**p) as stream:
                return stream.get_final_message(), label
        except anthropic_mod.BadRequestError as e:
            last = e
            print(f"    ({label} ใช้ไม่ได้: {e.message[:120]} — ลองแบบถอยลง)")
            continue
    raise last if last else RuntimeError("ยิงไม่สำเร็จและไม่มีข้อผิดพลาดให้รายงาน")


def text_of(message) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


def run_single(args, root, topics, state) -> int:
    anthropic_mod, client = make_client()
    topic = topics[args.topic]
    system = build_system(args.kind, root)
    user = build_user(args.kind, topic, topics, args.n)
    params = request_params(args.kind, system, user, args.model, args.max_tokens)

    print(f"ยิง {args.kind} ของ {args.topic} ด้วย {args.model} …")
    t0 = time.time()
    message, how = call_one(anthropic_mod, client, params,
                            use_fallbacks=not args.no_fallbacks)
    secs = time.time() - t0

    u = usage_dict(message.usage)
    dollars = cost_of(args.model, u, batch=False)
    print(f"  ได้คำตอบใน {secs:.0f} วินาที ({how})")
    print(f"  token: เข้า {u['input_tokens']} / แคชเขียน "
          f"{u['cache_creation_input_tokens']} / แคชอ่าน {u['cache_read_input_tokens']} "
          f"/ ออก {u['output_tokens']}")
    print(f"  ค่าใช้จ่ายครั้งนี้ ~${dollars:.3f}")
    if u["cache_read_input_tokens"] == 0 and u["cache_creation_input_tokens"] == 0:
        print("  ! แคชไม่ทำงาน ครั้งต่อไปจะจ่ายเต็มราคาอีก — ตรวจว่า system prompt "
              "เหมือนเดิมทุก byte")

    entry = {"kind": args.kind, "topic_id": args.topic, "model": args.model,
             "usage": u, "dollars": round(dollars, 4), "seconds": round(secs),
             "when": time.strftime("%Y-%m-%d %H:%M:%S"), "how": how}

    if message.stop_reason == "refusal":
        entry["result"] = "refusal"
        record(state, entry)
        print("  X ถูกปฏิเสธด้วยเหตุผลด้านนโยบาย ไม่ได้เนื้อหา")
        return 1
    if message.stop_reason == "max_tokens":
        entry["result"] = "truncated"
        record(state, entry)
        print(f"  X คำตอบถูกตัดกลางทาง (ชน max_tokens={args.max_tokens}) "
              "ให้เพิ่ม --max-tokens แล้วยิงใหม่")
        return 1

    raw = text_of(message)
    body, err = parse_body(raw)
    if body is None:
        entry["result"] = "bad_json"
        record(state, entry)
        p = reject(args.kind, args.topic, raw, "", err)
        print(f"  X {err}\n     เก็บไว้ที่ {p}")
        return 1

    ok, log = gate(args.kind, args.topic, body, root)
    if not ok:
        entry["result"] = "failed_checks"
        record(state, entry)
        p = reject(args.kind, args.topic,
                   json.dumps(body, ensure_ascii=False, indent=2), log, "ไม่ผ่านตัวตรวจ")
        print(f"  X ไม่ผ่านตัวตรวจ เก็บไว้ที่ {p}")
        print("     อ่านไฟล์ .log.txt ข้าง ๆ เพื่อดูว่าต้องแก้อะไร")
        return 1

    path = accept(args.kind, args.topic, body, root)
    entry["result"] = "accepted"
    record(state, entry)
    print(f"  OK ผ่านทั้งสองด่าน เขียนแล้วที่ {path}")
    print("     ขั้นต่อไป: ให้คนอ่านเนื้อหาจริง ตัวตรวจจับความผิดทางวิชาการไม่ได้")
    return 0


# ---------------------------------------------------------------- โหมดชุด

def run_batch(args, root, topics, state) -> int:
    anthropic_mod, client = make_client()
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    ids = pending(root, topics, args.kind, args.subject)[: args.limit]
    if not ids:
        print("ไม่มีหัวข้อที่ค้างอยู่ตามเงื่อนไขที่ระบุ")
        return 0

    system = build_system(args.kind, root)
    reqs = []
    for tid in ids:
        user = build_user(args.kind, topics[tid], topics, args.n)
        p = request_params(args.kind, system, user, args.model, args.max_tokens)
        # Batches API ไม่รับ fallbacks และไม่ใช้ streaming
        reqs.append(Request(custom_id=tid, params=MessageCreateParamsNonStreaming(**p)))

    print(f"ส่ง batch {len(reqs)} หัวข้อ ({args.kind}) ด้วย {args.model} "
          f"— คิดราคาครึ่งเดียว")
    batch = client.messages.batches.create(requests=reqs)
    print(f"  batch id: {batch.id}")
    state["batches"][batch.id] = {"kind": args.kind, "model": args.model,
                                  "topic_ids": ids, "n": args.n,
                                  "when": time.strftime("%Y-%m-%d %H:%M:%S"),
                                  "status": "submitted"}
    save_state(state)
    print(f"  เก็บ id ไว้ใน {STATE_PATH} แล้ว ปิดเครื่องได้ "
          f"แล้วกลับมาเก็บผลด้วย --collect {batch.id}")

    if args.no_wait:
        return 0
    return collect(args, root, topics, state, batch.id, client)


def collect(args, root, topics, state, batch_id: str, client=None) -> int:
    if client is None:
        _, client = make_client()
    info = state["batches"].get(batch_id)
    if info is None:
        print(f"ไม่รู้จัก batch {batch_id} ใน {STATE_PATH} — ระบุ --kind เองถ้าจะเก็บผล")
        if not args.kind:
            return 1
        info = {"kind": args.kind, "model": args.model}

    while True:
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        c = b.request_counts
        print(f"  รอ… สถานะ {b.processing_status} "
              f"(กำลังทำ {c.processing} / เสร็จ {c.succeeded} / พลาด {c.errored})")
        time.sleep(args.poll)

    kind = info["kind"]
    model = info.get("model", args.model)
    tally = {"accepted": 0, "failed_checks": 0, "bad_json": 0, "errored": 0,
             "refusal": 0, "truncated": 0}
    total = 0.0

    for result in client.messages.batches.results(batch_id):
        tid = result.custom_id
        rt = result.result.type
        if rt != "succeeded":
            tally["errored"] += 1
            print(f"  X {tid}: batch รายงาน {rt}")
            record(state, {"kind": kind, "topic_id": tid, "model": model,
                           "result": "errored", "batch": batch_id,
                           "when": time.strftime("%Y-%m-%d %H:%M:%S")})
            continue

        msg = result.result.message
        u = usage_dict(msg.usage)
        dollars = cost_of(model, u, batch=True)
        total += dollars
        entry = {"kind": kind, "topic_id": tid, "model": model, "usage": u,
                 "dollars": round(dollars, 4), "batch": batch_id,
                 "when": time.strftime("%Y-%m-%d %H:%M:%S")}

        if msg.stop_reason in ("refusal", "max_tokens"):
            key = "refusal" if msg.stop_reason == "refusal" else "truncated"
            tally[key] += 1
            entry["result"] = key
            record(state, entry)
            print(f"  X {tid}: {msg.stop_reason}")
            continue

        raw = text_of(msg)
        body, err = parse_body(raw)
        if body is None:
            tally["bad_json"] += 1
            entry["result"] = "bad_json"
            record(state, entry)
            reject(kind, tid, raw, "", err)
            print(f"  X {tid}: {err}")
            continue

        ok, log = gate(kind, tid, body, root)
        if not ok:
            tally["failed_checks"] += 1
            entry["result"] = "failed_checks"
            record(state, entry)
            reject(kind, tid, json.dumps(body, ensure_ascii=False, indent=2),
                   log, "ไม่ผ่านตัวตรวจ")
            print(f"  X {tid}: ไม่ผ่านตัวตรวจ")
            continue

        accept(kind, tid, body, root)
        tally["accepted"] += 1
        entry["result"] = "accepted"
        record(state, entry)
        print(f"  OK {tid}")

    state["batches"][batch_id]["status"] = "collected"
    save_state(state)

    print()
    print("=" * 72)
    print(f"  ผลของ batch {batch_id}")
    print("=" * 72)
    for k, v in tally.items():
        if v:
            print(f"  {k:14s} {v}")
    print(f"\nค่าใช้จ่ายรวม ~${total:.2f}")
    if tally["failed_checks"] or tally["bad_json"]:
        print(f"ไฟล์ที่ไม่ผ่านอยู่ใน {WORKDIR / 'rejected'} พร้อมผลตรวจ")
    if tally["accepted"]:
        print("ไฟล์ที่ผ่านเข้า data/ แล้ว แต่ยังต้องให้คนอ่านเนื้อหาก่อนเผยแพร่")
    return 0 if tally["accepted"] else 1


# ---------------------------------------------------------------- โหมดไม่เสียเงิน

def run_plan(root, topics, args) -> int:
    print("=" * 72)
    print("  หัวข้อที่ยังไม่มีไฟล์ (ไม่เรียก API ไม่เสียเงิน)")
    print("=" * 72)
    for kind in ("lesson", "problems"):
        ids = pending(root, topics, kind, args.subject)
        label = "บทเรียน" if kind == "lesson" else "โจทย์"
        print(f"\n{label}: ค้าง {len(ids)} หัวข้อ")
        for tid in ids[: args.limit]:
            print(f"  {tid}   {topics[tid].get('name_th')}")
        if len(ids) > args.limit:
            print(f"  … อีก {len(ids) - args.limit} หัวข้อ (ใช้ --limit เพื่อดูเพิ่ม)")
    return 0


def run_dry(args, root, topics) -> int:
    topic = topics[args.topic]
    system = build_system(args.kind, root)
    user = build_user(args.kind, topic, topics, args.n)

    sys_text = "\n\n".join(b["text"] for b in system)
    n_sys = estimate_tokens(sys_text)
    n_user = estimate_tokens(user)
    price_in, price_out = PRICES.get(args.model, PRICES[DEFAULT_MODEL])
    guess_out = 8000 if args.kind == "lesson" else 16000

    first = (n_sys * price_in * CACHE_WRITE_MULT + n_user * price_in
             + guess_out * price_out) / 1e6
    later = (n_sys * price_in * CACHE_READ_MULT + n_user * price_in
             + guess_out * price_out) / 1e6

    print("=" * 72)
    print(f"  ซ้อมยิง {args.kind} ของ {args.topic} — ไม่เรียก API")
    print("=" * 72)
    print(f"\nsystem prompt: {len(system)} บล็อก ~{n_sys:,} token (ประเมินหยาบ)")
    for i, b in enumerate(system):
        head = b["text"].strip().split("\n", 1)[0][:56]
        cached = " [จุดตัดแคช]" if "cache_control" in b else ""
        print(f"  {i + 1}. ~{estimate_tokens(b['text']):>7,} token  {head}{cached}")
    print(f"user message: ~{n_user:,} token")
    print(f"\nประเมินค่าใช้จ่ายด้วย {args.model} (สมมติคำตอบ {guess_out:,} token)")
    print(f"  ครั้งแรก (ต้องเขียนแคช) ~${first:.3f}")
    print(f"  ครั้งต่อ ๆ ไป (อ่านแคช)  ~${later:.3f}")
    print(f"  ถ้าใช้ --batch จะเหลือครึ่ง  ~${later * BATCH_MULT:.3f} ต่อหัวข้อ")
    print(f"\nทั้งวิชา TGAT2 ที่ค้าง {len(pending(root, topics, args.kind, 'tgat2'))} หัวข้อ")
    print(f"  แบบยิงทีละข้อ ~${later * len(pending(root, topics, args.kind, 'tgat2')):.2f}")
    print(f"  แบบ batch     ~${later * BATCH_MULT * len(pending(root, topics, args.kind, 'tgat2')):.2f}")
    print("\n(เลข token เป็นการประเมินหยาบจากจำนวนตัวอักษร เลขจริงมาจาก response.usage)")

    if args.show_prompt:
        print("\n" + "=" * 72)
        print("  USER MESSAGE")
        print("=" * 72)
        print(user)
        print("=" * 72)
        print("  SYSTEM (บล็อกสุดท้ายย่อ)")
        print("=" * 72)
        for b in system[:-1]:
            print(b["text"][:1500])
            print("  …")
        print(system[-1]["text"][:1500] + "\n  …")
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    S.utf8_stdout()
    ap = argparse.ArgumentParser(
        description="ผลิตบทเรียน/โจทย์ด้วย Claude API แล้วบังคับให้ผ่านตัวตรวจก่อนรับ")
    ap.add_argument("--plan", action="store_true",
                    help="ดูว่าหัวข้อไหนยังค้าง ไม่เรียก API")
    ap.add_argument("--dry-run", action="store_true",
                    help="ประกอบคำสั่งและประเมินค่าใช้จ่าย ไม่เรียก API")
    ap.add_argument("--show-prompt", action="store_true",
                    help="ใน --dry-run ให้พิมพ์เนื้อคำสั่งออกมาด้วย")
    ap.add_argument("--topic", help="topic_id ที่จะทำ (โหมดยิงทีละข้อ)")
    ap.add_argument("--kind", choices=["lesson", "problems"], help="จะทำบทเรียนหรือโจทย์")
    ap.add_argument("--batch", action="store_true",
                    help="ยิงเป็นชุดผ่าน Batches API (ถูกลงครึ่งราคา)")
    ap.add_argument("--collect", metavar="BATCH_ID", help="เก็บผลของ batch ที่ส่งไว้แล้ว")
    ap.add_argument("--no-wait", action="store_true",
                    help="ส่ง batch แล้วจบเลย ไม่ต้องรอ")
    ap.add_argument("--poll", type=int, default=60, help="วินาทีระหว่างการถามสถานะ batch")
    ap.add_argument("--limit", type=int, default=20, help="จำนวนหัวข้อสูงสุดต่อครั้ง")
    ap.add_argument("--subject", help="ทำเฉพาะวิชานี้ เช่น tgat2")
    ap.add_argument("-n", type=int, default=12, help="จำนวนโจทย์ต่อหัวข้อ (ค่าเริ่มต้น 12)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"ค่าเริ่มต้น {DEFAULT_MODEL}")
    ap.add_argument("--max-tokens", type=int, default=32000, dest="max_tokens")
    ap.add_argument("--no-fallbacks", action="store_true",
                    help="ไม่ใช้ server-side fallbacks")
    ap.add_argument("--data", help="โฟลเดอร์ data (ปกติหาให้อัตโนมัติ)")
    args = ap.parse_args()

    root = pathlib.Path(args.data) if args.data else S.data_root()
    topics = load_topics(root)
    if not topics:
        print(f"ไม่พบผังหัวข้อใน {root / 'topics'}")
        return 1
    state = load_state()

    if args.plan:
        return run_plan(root, topics, args)

    if args.collect:
        return collect(args, root, topics, state, args.collect)

    if not args.kind:
        print("ต้องระบุ --kind lesson หรือ --kind problems")
        return 1

    if args.topic:
        if args.topic not in topics:
            print(f"ไม่มี topic_id {args.topic!r} ในผังหัวข้อ")
            return 1
        if topics[args.topic].get("kind") != "leaf":
            print(f"{args.topic} ไม่ใช่ leaf — ทำบทเรียนหรือโจทย์ได้เฉพาะ leaf")
            return 1
        if args.dry_run:
            return run_dry(args, root, topics)
        return run_single(args, root, topics, state)

    if args.batch:
        return run_batch(args, root, topics, state)

    print("ระบุ --topic <id> เพื่อยิงทีละข้อ หรือ --batch เพื่อยิงเป็นชุด")
    print("หรือ --plan เพื่อดูว่าค้างอะไรอยู่ (ไม่เสียเงิน)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
