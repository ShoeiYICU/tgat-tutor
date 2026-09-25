"""providers — แม่แบบโจทย์ที่คำนวณด้วยโค้ดเฉพาะทาง (ไม่ใช่นิพจน์เลขคณิต)

## ทำไมต้องมี

แม่แบบปกติในสเปค C ใช้ `answer_expr` ซึ่งเป็นนิพจน์เลขคณิต คำนวณได้เฉพาะ
**คำตอบที่เป็นตัวเลข** และไม่มีทางสร้างรูปได้ หัวข้ออย่าง "คู่หน้าตรงข้าม
จากแผ่นคลี่" ต้องการสองอย่างที่นิพจน์ให้ไม่ได้
  1. คำตอบเป็น "ชื่อหน้า" (ก ข ค) ไม่ใช่ตัวเลข
  2. โจทย์ต้องมีรูปแผ่นคลี่ที่วาดตามค่าที่สุ่มมา

การขยายภาษานิพจน์ให้ทำเรื่องพวกนี้ได้จะกลายเป็นภาษาโปรแกรมย่อยใน JSON
ซึ่งตรวจไม่ได้และไม่ปลอดภัย จึงเลือกทางตรงข้าม: **ให้ JSON เรียกชื่อฟังก์ชัน
ที่เขียนไว้ในไฟล์นี้เท่านั้น** โค้ดอยู่ในโฟลเดอร์ที่คนอ่านและรีวิวได้
JSON ระบุได้แค่ชื่อ provider กับพารามิเตอร์ที่ provider นั้นยอมรับ

## สัญญาของ provider (ทุกโมดูลต้องมีครบ)

    NAME            str    ชื่อที่ JSON ใช้เรียก เช่น "cube_net.opposite_face"
    DOC             str    อธิบายว่าสร้างโจทย์แบบไหน
    ANSWER_KIND     str    "number" | "label" | "text"
    validate_params(params) -> list[str]
                           ตรวจพารามิเตอร์แบบไม่ต้องรัน คืนรายการปัญหา (ว่าง = ผ่าน)
    var_names(params) -> list[str]
                           ชื่อค่าที่ draw() จะคืน เพื่อให้ validator ตรวจ stem_tpl ได้
    draw(params, rng) -> dict | None
                           สุ่มค่าหนึ่งชุด คืน None ถ้าชุดนี้ใช้ไม่ได้ (เทียบเท่า constraints)
    build(params, vals) -> dict
                           {"answer": ...,
                            "distractors": [{"value","reason","tag"}],
                            "steps":  [{"do_md","why_md"}, ...]   (อย่างน้อย 2 ขั้น)
                            "hints":  [str, str, str]             (3 ระดับเสมอ)
                            "explanation": str
                            "figures": [ {...} ]}

## ถ้าตัวเลือกเป็นรูป (ไม่ใช่ข้อความ)

โจทย์บางแบบตัวเลือกต้องเป็นรูป เช่น พับกระดาษเจาะรู ที่ผู้สอบต้องเลือก
รูปแบบรูที่ถูกต้อง provider แบบนี้ต้องคืนเพิ่มสองอย่าง
    "answer_fig": "fig2"                      รูปที่เป็นคำตอบ
    distractors[i]["fig"]: "fig3"             รูปของตัวลวงแต่ละตัว
และต้องใส่รูปทุกตัวไว้ใน "figures" ให้ครบ

`value` ของแต่ละตัวเลือกยังต้องเป็น **ข้อความที่ต่างกันจริง** (เช่นพิกัดรูแบบมาตรฐาน)
เพราะเกณฑ์คุณภาพใช้ค่านี้ตรวจว่าตัวเลือกซ้ำกันไหม ไม่ได้ใช้ชื่อรูป

`build` ต้องคืนตัวเลือกลวงที่ **มีเหตุผลกำกับทุกตัว** เหมือนแม่แบบปกติ
เพราะ render_template จะเอาไปตรวจด้วยเกณฑ์คุณภาพชุดเดียวกัน

## ต้องคืนเฉลยของโจทย์ที่สุ่มมาด้วย ไม่ใช่แค่คำตอบ

`steps` `hints` `explanation` เป็นฟิลด์บังคับ เพราะโจทย์ที่สุ่มใหม่ต้องอธิบายตัวเองได้
ถ้าคืนแต่คำตอบ ผู้ใช้กดสุ่มแล้วจะได้โจทย์ที่ไม่มีวิธีคิด ซึ่งใช้ไม่ได้กับคนที่เรียนจาก 0

และต้องเป็นเฉลยที่ **คำนวณจากค่าที่สุ่มมาจริง** ไม่ใช่ข้อความสำเร็จรูป
เช่นในตัวพับกล่อง ขั้นตอนจะเปลี่ยนไปตามว่ากฎเว้นหนึ่งช่องใช้ได้หรือไม่

กฎที่ตรวจให้อัตโนมัติ: **ห้ามมีคำตอบอยู่ใน `hints` แม้แต่ข้อเดียว**
ไม่อย่างนั้นการกดขอคำใบ้จะกลายเป็นการกดดูเฉลย

## ข้อห้าม

provider ต้องเป็นฟังก์ชันที่ให้ผลเหมือนเดิมทุกครั้งเมื่อรับค่าเดิม (deterministic)
ห้ามอ่านไฟล์ ห้ามต่อเน็ต ห้ามใช้เวลาปัจจุบัน — ไม่อย่างนั้น stress test
จะให้ผลไม่ซ้ำเดิมและเลิกเชื่อถือได้
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from providers import cube_net_opposite  # noqa: E402
from providers import cube_net_pair  # noqa: E402
from providers import gear_train  # noqa: E402
from providers import number_grid  # noqa: E402
from providers import paper_fold  # noqa: E402
from providers import shape2d_items  # noqa: E402

# shape2d_items มี provider สามตัวในไฟล์เดียว เพราะใช้เครื่องมือกลางชุดเดียวกัน
# แต่ละตัวเป็นคลาสที่มีหน้าตาตามสัญญา provider ทุกประการ
_MODULES = [
    cube_net_opposite, cube_net_pair, gear_train, number_grid, paper_fold,
    shape2d_items.ROTATE_MATCH, shape2d_items.ODD_ONE_OUT, shape2d_items.ROT_OR_REF,
]

REGISTRY = {m.NAME: m for m in _MODULES}


def get(name: str):
    """คืนโมดูล provider ตามชื่อ หรือ None ถ้าไม่มี"""
    return REGISTRY.get(name)


def names() -> list[str]:
    return sorted(REGISTRY)
