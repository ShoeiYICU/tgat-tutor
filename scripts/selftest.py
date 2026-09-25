"""selftest.py — ทดสอบว่า validate.py ยังจับข้อผิดพลาดได้ครบ

ทำงานโดยคัดลอก data/ ไปโฟลเดอร์ชั่วคราว ใส่ข้อผิดพลาดที่รู้อยู่แล้วลงไป
แล้วเช็คว่า validator รายงานครบทุกจุด — ไม่แตะไฟล์จริงใน data/

รันหลังแก้ validate.py หรือ speclib.py ทุกครั้ง
    python scripts/selftest.py

รหัสออกจากโปรแกรม: 0 = ผ่าน, 1 = มีจุดที่ validator ตรวจไม่เจอ
"""

from __future__ import annotations

import copy
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJ = HERE.parent


def read(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write(p: pathlib.Path, d) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def break_topics(td: pathlib.Path) -> None:
    p = td / "topics" / "math.topics.json"
    d = read(p)
    by_id = {t["id"]: t for t in d["topics"]}
    by_id["math.trig.ratio"]["requires"] = ["math.trig.sine_law"]        # วงวน
    by_id["math.geometry.pythagoras"]["est_minutes"] = 90                # เกิน 10-30
    by_id["math.geometry.triangle_basic"]["requires"].append("math.nope")  # ไม่มีจริง
    write(p, d)


def break_problems(td: pathlib.Path) -> None:
    p = td / "problems" / "math.trig.sine_law.json"
    d = read(p)
    pr = d["problems"][0]
    pr["choices"][0]["is_answer"] = True
    pr["hints"] = pr["hints"][:2]
    pr["difficulty"] = 5
    pr["solution_steps"][1]["why_md"] = ""
    pr["distractor_reasons"].pop("2", None)
    pr["template"]["answer_expr"] = "__import__('os').system('dir')"
    pr["template"]["distractors"][0]["expr"] = "a * sin(radians(Z))"
    d["problems"].append(copy.deepcopy(pr))   # id ซ้ำ
    write(p, d)


def break_provider_templates(td: pathlib.Path) -> None:
    """ใส่ข้อผิดพลาดของแม่แบบแบบ provider (หัวข้อที่คำตอบไม่ใช่ตัวเลข)"""
    p = td / "problems" / "tgat2.spatial.box_folding.net_opposites.json"
    d = read(p)
    pr = d["problems"]

    pr[0]["template"]["provider"] = "cube_net.ไม่มีจริง"          # provider ไม่มีในทะเบียน
    pr[1]["template"].pop("answer_kind")                          # ไม่ระบุชนิดคำตอบ
    pr[2]["template"]["answer_kind"] = "number"                   # ชนิดไม่ตรงกับ provider
    pr[3]["template"]["params"]["nets"] = ["แผ่นคลี่ที่ไม่มี"]      # ชื่อแผ่นคลี่ผิด
    pr[4]["template"]["answer_expr"] = "1 + 1"                    # ใส่ฟิลด์ของโหมดเลขคณิต
    pr[5]["template"]["stem_tpl"] = "หน้าใดตรงข้ามกับหน้า {ไม่มีตัวแปรนี้}"
    pr[7]["answer_numeric"] = 42                                  # คำตอบข้อความแต่ใส่ตัวเลข
    # พารามิเตอร์ที่ขัดกันเอง: zigzag ไม่มีคู่ที่กฎเว้นหนึ่งช่องหาได้เลย
    pr[8]["template"]["params"] = {"nets": ["zigzag"], "skip_rule_applies": True}
    # touching_count มีแต่ใน provider แบบถามหน้าเดียว (ข้อ 0007 กับ 0012 เป็นแบบถามคู่)
    pr[9]["template"]["params"] = {"nets": ["cross"], "touching_count": 9}  # นอกช่วง 1-4
    write(p, d)


def break_explanations(td: pathlib.Path) -> None:
    """ใส่ข้อผิดพลาดของ "เฉลยที่สุ่มได้" (steps_tpl / hints_tpl / explanation_tpl)"""
    p = td / "problems" / "tgat2.numerical.series.constant_difference.json"
    d = read(p)
    pr = d["problems"]

    pr[0]["template"].pop("steps_tpl")                      # ไม่มีวิธีคิดเลย
    pr[1]["template"]["steps_tpl"] = pr[1]["template"]["steps_tpl"][:1]   # เหลือขั้นเดียว
    pr[2]["template"]["steps_tpl"][0]["why_md"] = ""         # บอกว่าทำอะไร แต่ไม่บอกทำไม
    pr[3]["template"]["hints_tpl"] = pr[3]["template"]["hints_tpl"][:2]   # คำใบ้ไม่ครบ 3
    pr[4]["template"].pop("explanation_tpl")                 # ไม่มีคำอธิบายคำตอบ
    pr[5]["template"]["explanation_tpl"] = "ตอบ {ไม่มีตัวแปรนี้} นะ"      # อ้างชื่อที่ไม่มี
    write(p, d)


def leaky_hint_data(td: pathlib.Path) -> None:
    """ทำให้คำใบ้บอกคำตอบ เพื่อทดสอบตัวตรวจชั้นที่ 2 (ไม่ใช่ชั้นที่ 1)

    validate.py จับไม่ได้เพราะต้องแทนค่าจริงก่อนจึงจะรู้ว่าคำใบ้มีคำตอบอยู่
    """
    p = td / "problems" / "tgat2.numerical.series.constant_difference.json"
    d = read(p)
    d["problems"][0]["template"]["hints_tpl"][2] = "คำตอบคือ {answer} ลองคิดดู"
    write(p, d)


def break_problem_figures(td: pathlib.Path) -> None:
    """ใส่ข้อผิดพลาดของการอ้างรูปในโจทย์

    สำคัญมากกับโจทย์ที่ตัวเลือกเป็นรูป (พับกระดาษเจาะรู)
    เพราะถ้ารูปหาย ผู้สอบจะเห็นตัวเลือกว่างเปล่าแล้วเดาไม่ได้เลย
    """
    p = td / "problems" / "tpat3.aptitude.spatial.paper_fold_punch.json"
    if not p.is_file():
        return
    d = read(p)
    pr = d["problems"]
    # ลบรูปที่ตัวเลือกอ้างถึง -> ต้องฟ้องว่าอ้างรูปที่ไม่มี
    pr[0]["figures"] = [f for f in pr[0]["figures"] if f["id"] != "fig3"]
    # ตั้ง id รูปซ้ำกันสองที่
    pr[1]["figures"][2]["id"] = pr[1]["figures"][1]["id"]
    write(p, d)


def break_tiered(td: pathlib.Path) -> None:
    """ใส่ข้อผิดพลาดของข้อสอบที่ให้คะแนนลดหลั่น (format mcq4_tiered)

    ไม่มีไฟล์แบบนี้ใน data/ จริงยังไม่มี จึงดัดแปลงไฟล์ที่มีอยู่ให้เป็นแบบลดหลั่น
    แล้วใส่ข้อผิดพลาดลงไป
    """
    p = td / "problems" / "tgat2.language.communication.analogy_semantic.json"
    d = read(p)
    pr = d["problems"]

    def to_tiered(item, scores, answer_at):
        item["format"] = "mcq4_tiered"
        item["choices"] = copy.deepcopy(item["choices"][:4])
        for i, c in enumerate(item["choices"]):
            c["is_answer"] = (i == answer_at)
            if scores[i] is not None:
                c["score"] = scores[i]
            else:
                c.pop("score", None)
        item["distractor_reasons"] = {
            str(i): "เหตุผลสำหรับตัวเลือกนี้" for i in range(4) if i != answer_at
        }

    to_tiered(pr[0], [None, None, None, None], 0)        # ไม่มี score เลย
    to_tiered(pr[1], [1, 0.6, 0.25, 0], 0)               # 0.6 ไม่ใช่ขั้นที่อนุญาต
    to_tiered(pr[2], [1, 1, 0.25, 0], 0)                 # ได้ 1 คะแนนสองตัว
    to_tiered(pr[3], [1, 0.5, 0.25, 0], 1)               # is_answer ไม่ตรงกับตัวที่ได้ 1
    to_tiered(pr[4], [1, 0, 0, 0], 0)                    # ไม่มีคะแนนบางส่วน (เตือน)
    write(p, d)


def break_lessons(td: pathlib.Path) -> None:
    p = td / "lessons" / "math.trig.sine_law.json"
    d = read(p)
    for b in d["blocks"]:
        if b["type"] == "formula":
            b["avoid_when"] = ""
            break
    for b in d["blocks"]:
        if b["type"] == "example":
            b["steps"][0]["why_md"] = ""
            break
    for b in d["blocks"]:
        if b["type"] == "check":
            b["answer_index"] = 99
            break
    d["review_status"] = "ยังไม่ตรวจ"
    write(p, d)


BROKEN_EXAM = {
    "schema_version": "1.0",
    "exam_code": "ALEVEL_61",
    "year": 2567,
    "round": None,
    "paper_title": "ชุดทดสอบ selftest",
    "source": {"kind": "user_provided_file", "source_name": "ทดสอบ", "source_url": None,
               "retrieved_date": "2026-09-19", "file_ref": None, "note": None},
    "license_status": "unknown",
    "visibility": "public",
    "transcription_status": "checked",
    "structure": {"num_items": 2, "duration_min": 90, "scoring_note": ""},
    "items": [
        {"item_no": 1, "verbatim": True, "stem_md": None, "figures": [], "choices": None,
         "official_answer": None, "answer_source": "unknown",
         "topic_ids": ["math.trig.sine_law"], "primary_topic_id": "math.trig.sine_law",
         "difficulty": 3,
         "difficulty_signals": {"steps_count": 3, "topics_count": 1, "needs_insight": False,
                                "heavy_computation": False, "trap_present": False,
                                "reading_load": "low"},
         "our_solution_steps": [], "our_solution_author": "ai_draft",
         "misconception_tags": [], "practice_template_ref": None, "notes": None},
        {"item_no": 1, "verbatim": True, "stem_md": "โจทย์ทดสอบ", "figures": [],
         "choices": None, "official_answer": None, "answer_source": "our_solution",
         "topic_ids": ["math.no_such_topic"], "primary_topic_id": "math.trig.ratio",
         "difficulty": 3,
         "difficulty_signals": {"steps_count": 3, "topics_count": 1, "needs_insight": False,
                                "heavy_computation": False, "trap_present": False,
                                "reading_load": "low"},
         "our_solution_steps": [{"do_md": "x", "why_md": ""}],
         "our_solution_author": "ai_draft", "misconception_tags": [],
         "practice_template_ref": "prob.no_such_topic.0001", "notes": None},
    ],
}

EXPECT = [
    ("ผังหัวข้อ: วงวนใน requires", "วงวนใน requires"),
    ("ผังหัวข้อ: leaf เวลาเกินช่วง", "est_minutes ระหว่าง 10-30"),
    ("ผังหัวข้อ: requires ชี้ไปหาที่ไม่มี", "ไม่มีอยู่ในผัง"),
    ("โจทย์: id ซ้ำ", "id ซ้ำกับใน"),
    ("โจทย์: มีคำตอบถูก 2 ตัว", "is_answer = true หนึ่งตัว"),
    ("โจทย์: hints ไม่ครบ 3", "hints ต้องมี 3 ระดับ"),
    ("โจทย์: ความยากขัดกับ signals", "ไม่สอดคล้องกับ difficulty_signals"),
    ("โจทย์: why_md ว่าง", "why_md ที่ไม่ว่าง"),
    ("โจทย์: distractor_reasons ขาด index", "distractor_reasons ขาด index"),
    ("แม่แบบ: นิพจน์ไม่ปลอดภัย", "ไม่อนุญาต"),
    ("แม่แบบ: ใช้ตัวแปรที่ไม่ได้ประกาศ", "ที่ไม่ได้ประกาศใน vars"),
    ("แม่แบบ provider: ไม่รู้จักชื่อ provider", "ไม่รู้จัก provider"),
    ("แม่แบบ provider: ไม่ระบุ answer_kind", "ต้องระบุ answer_kind"),
    ("แม่แบบ provider: answer_kind ไม่ตรงกับ provider", "ไม่ตรงกับ provider"),
    ("แม่แบบ provider: ชื่อแผ่นคลี่ไม่มีจริง", "ไม่รู้จักแผ่นคลี่"),
    ("แม่แบบ provider: ใส่ฟิลด์ของโหมดเลขคณิต", "จะถูกเมินเงียบ"),
    ("แม่แบบ provider: stem_tpl อ้างตัวแปรที่ provider ไม่ได้คืน", "ไม่ได้คืนค่าชื่อนี้"),
    ("แม่แบบ provider: touching_count นอกช่วง", "touching_count ต้องเป็นจำนวนเต็ม 1-4"),
    ("แม่แบบ provider: พารามิเตอร์ขัดกันเอง", "ไม่มีชุดค่าที่ใช้ได้เลย"),
    ("แม่แบบ provider: คำตอบข้อความแต่ใส่ answer_numeric", "answer_numeric ไม่เป็น null"),
    ("เฉลยที่สุ่มได้: ไม่มี steps_tpl", "ไม่มี steps_tpl"),
    ("เฉลยที่สุ่มได้: วิธีคิดเหลือขั้นเดียว", "steps_tpl ต้องเป็นอาร์เรย์ที่มีอย่างน้อย 2 ขั้น"),
    ("เฉลยที่สุ่มได้: ขั้นที่ไม่บอกว่าทำไม", "ต้องมี why_md ที่ไม่ว่าง"),
    ("เฉลยที่สุ่มได้: คำใบ้ไม่ครบ 3 ระดับ", "hints_tpl ต้องมี 3 ระดับ"),
    ("เฉลยที่สุ่มได้: ไม่มี explanation_tpl", "ไม่มี explanation_tpl"),
    ("เฉลยที่สุ่มได้: อ้างชื่อตัวแปรที่ไม่มี", "เฉลยอ้างช่องแทนค่า"),
    ("คะแนนลดหลั่น: ไม่มี score", "ต้องมี score ทุกตัวเลือก"),
    ("คะแนนลดหลั่น: score ไม่ใช่ขั้น 0.25", "ไม่ใช่ขั้นที่อนุญาต"),
    ("คะแนนลดหลั่น: ได้ 1 คะแนนสองตัว", "ได้ 1 คะแนนเพียงตัวเดียว"),
    ("คะแนนลดหลั่น: is_answer ไม่ตรงกับตัวที่ได้ 1", "ต้องเป็นตัวที่ is_answer = true"),
    ("คะแนนลดหลั่น: ไม่มีคะแนนบางส่วน (เตือน)", "ให้ใช้ format mcq4 แทน"),
    ("โจทย์: อ้างรูปที่ไม่มีในข้อนั้น", "โจทย์อ้างถึงรูป"),
    ("โจทย์: นิยาม id รูปซ้ำสองที่", "นิยามรูป id"),
    ("บทเรียน: formula ขาด avoid_when", "formula ต้องมี avoid_when"),
    ("บทเรียน: answer_index นอกช่วง", "answer_index"),
    ("บทเรียน: review_status ไม่ถูกต้อง", "review_status ="),
    ("ข้อสอบจริง: public แต่ license ไม่ใช่ official_public", "visibility = 'public'"),
    ("ข้อสอบจริง: checked แต่ไม่มีที่มาให้ย้อนตรวจ", "ไม่มี source_url"),
    ("ข้อสอบจริง: stem null แต่ไม่มี notes", "ต้องเขียนใน notes"),
    ("ข้อสอบจริง: item_no ซ้ำ", "item_no ซ้ำ"),
    ("ข้อสอบจริง: practice_template_ref ชี้ไปหาโจทย์ที่ไม่มี", "practice_template_ref ชี้ไปหา"),
]


def check_layer2(src: pathlib.Path) -> bool:
    """ทดสอบตัวตรวจชั้นที่ 2 (render_template --stress)

    ข้อบกพร่องบางอย่างรู้ได้ต่อเมื่อแทนค่าจริงแล้ว เช่น คำใบ้ที่ไปบอกคำตอบ
    validate.py จับไม่ได้ จึงต้องทดสอบชั้นที่ 2 แยก
    """
    print()
    print("-" * 72)
    print("  ทดสอบตัวตรวจชั้นที่ 2 (ต้องจับได้ว่าคำใบ้ไปบอกคำตอบ)")
    print("-" * 72)
    ok = True
    with tempfile.TemporaryDirectory(prefix="addmission_layer2_") as tmp:
        td = pathlib.Path(tmp) / "data"
        shutil.copytree(src, td)
        leaky_hint_data(td)
        r = subprocess.run(
            [sys.executable, str(HERE / "render_template.py"), "--stress",
             "--draws", "20", "--data", str(td)],
            capture_output=True, text=True, encoding="utf-8",
        )
        out = r.stdout + r.stderr
        if "คำใบ้ต้องชี้ทางเท่านั้น" in out and r.returncode == 1:
            print("  จับได้    คำใบ้ที่มีคำตอบอยู่ในข้อความ")
        else:
            print(f"  ไม่จับได้  คำใบ้ที่มีคำตอบอยู่ในข้อความ (exit={r.returncode})")
            ok = False

    # ข้อมูลจริงต้องผ่านชั้นที่ 2 ด้วย
    r2 = subprocess.run(
        [sys.executable, str(HERE / "render_template.py"), "--stress", "--draws", "50"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if r2.returncode == 0:
        print("  ข้อมูลจริงผ่านชั้นที่ 2")
    else:
        print("  ข้อมูลจริงไม่ผ่านชั้นที่ 2 (ดู python scripts/render_template.py --stress)")
        ok = False
    return ok


def check_gate() -> bool:
    """ทดสอบด่านคัดกรองของ generate.py — ไม่เรียก API ไม่เสียเงิน

    นี่คือด่านที่กันของเสียจาก AI ไม่ให้เข้า data/ ถ้าด่านนี้พังเงียบ ๆ
    ของที่ยิงมาจะเข้าไปทั้งที่ยังผิด จึงต้องมีอะไรเฝ้ามันไว้
    """
    print()
    print("-" * 72)
    print("  ทดสอบด่านคัดกรองของ generate.py (ต้องรับของดี ปฏิเสธของเสีย)")
    print("-" * 72)
    sys.path.insert(0, str(HERE))
    try:
        import generate as G
        import speclib as SL
    except Exception as e:  # noqa: BLE001
        print(f"  ไม่จับได้  โหลด generate.py ไม่ได้: {e}")
        return False

    root = SL.data_root()
    src = root / "problems" / "tgat2.numerical.series.constant_difference.json"
    if not src.is_file():
        print("  ข้าม      ไม่มีไฟล์ตัวอย่างให้ทดสอบ")
        return True

    good = read(src)
    tid = good["topic_id"]
    ok = True

    passed, _ = G.gate("problems", tid, good, root)
    if passed:
        print("  ถูกต้อง   รับไฟล์ที่ผ่านตัวตรวจ")
    else:
        print("  ผิด       ปฏิเสธไฟล์ที่ควรผ่าน")
        ok = False

    broken = copy.deepcopy(good)
    broken["problems"][0]["template"].pop("steps_tpl", None)
    passed, _ = G.gate("problems", tid, broken, root)
    if passed:
        print("  ผิด       รับไฟล์ที่ขาด steps_tpl เข้ามา")
        ok = False
    else:
        print("  ถูกต้อง   ปฏิเสธไฟล์ที่ขาด steps_tpl")

    return ok


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    src = PROJ / "data"
    if not src.is_dir():
        print("ไม่พบโฟลเดอร์ data/ — selftest ต้องใช้ไฟล์ตัวอย่างใน data/ เป็นฐาน")
        return 1

    with tempfile.TemporaryDirectory(prefix="addmission_selftest_") as tmp:
        td = pathlib.Path(tmp) / "data"
        shutil.copytree(src, td)
        break_topics(td)
        break_problems(td)
        break_provider_templates(td)
        break_explanations(td)
        break_tiered(td)
        break_problem_figures(td)
        break_lessons(td)
        (td / "exams").mkdir(exist_ok=True)
        write(td / "exams" / "ALEVEL_61.2567.json", BROKEN_EXAM)

        print("=" * 72)
        print(f"  selftest: ใส่ข้อผิดพลาดที่รู้อยู่แล้ว {len(EXPECT)} ประเภท "
              "แล้วเช็คว่า validator จับได้ครบ")
        print("=" * 72)
        r = subprocess.run(
            [sys.executable, str(HERE / "validate.py"), "--data", str(td), "--quiet"],
            capture_output=True, text=True, encoding="utf-8",
        )
        out = r.stdout + r.stderr

        missed = []
        for label, needle in EXPECT:
            if needle in out:
                print(f"  จับได้    {label}")
            else:
                print(f"  ไม่จับได้  {label}")
                missed.append(label)

        print()
        print(f"ผล: จับได้ {len(EXPECT) - len(missed)}/{len(EXPECT)} ประเภท   "
              f"exit code ของ validator = {r.returncode} (ต้องเป็น 1)")

        # ต้องไม่รายงานอะไรกับข้อมูลจริงที่สะอาด
        r2 = subprocess.run(
            [sys.executable, str(HERE / "validate.py"), "--quiet"],
            capture_output=True, text=True, encoding="utf-8",
        )
        clean_ok = r2.returncode == 0
        print(f"ข้อมูลจริงใน data/ {'ผ่าน' if clean_ok else 'ไม่ผ่าน (ดู python scripts/validate.py)'}")

        layer2_ok = check_layer2(src)
        gate_ok = check_gate()
        if missed or r.returncode != 1 or not clean_ok or not layer2_ok or not gate_ok:
            print("\n=> selftest ไม่ผ่าน")
            if missed:
                print("   validator ตรวจไม่เจอ: " + ", ".join(missed))
            return 1
        print("\n=> selftest ผ่าน validator ยังทำงานถูกต้อง")
        return 0


if __name__ == "__main__":
    sys.exit(main())
