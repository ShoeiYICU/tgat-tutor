"""speclib — เครื่องมือกลางที่ validate.py และ render_template.py ใช้ร่วมกัน

ใช้ไลบรารีมาตรฐานของ Python เท่านั้น ไม่ต้อง pip install อะไร
รองรับ Python 3.9 ขึ้นไป
"""

from __future__ import annotations

import ast
import json
import math
import operator
import pathlib
import re
import sys

# ---------------------------------------------------------------- ค่าคงที่จากสเปค

ID_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
PROBLEM_ID_RE = re.compile(r"^prob\.[a-z0-9_.]+\.\d{4}$")

TOPIC_KINDS = {"subject", "branch", "leaf"}
GRADE_BANDS = {"m1", "m2", "m3", "m4", "m5", "m6", "m_early", "mixed"}
DIFFICULTY_BANDS = {"easy", "medium", "hard"}
CONFIDENCE = {"low", "medium", "high"}
READING_LOAD = {"low", "medium", "high"}

PROBLEM_FORMATS = {
    "mcq4", "mcq5", "numeric", "multi_select",
    "matching", "ranking", "short_answer",
    # ปรนัย 4 ตัวเลือกที่ให้คะแนนลดหลั่น ใช้กับข้อสอบสถานการณ์อย่าง TGAT3
    # ซึ่งตัวเลือกไม่ได้มีแค่ถูกกับผิด แต่มี "ดีที่สุด" กับ "พอใช้ได้"
    "mcq4_tiered",
}

# คะแนนต่อตัวเลือกของข้อสอบแบบลดหลั่น ใช้ขั้นละ 0.25 ตามผังสอบ TGAT3
TIER_STEP = 0.25
TIER_SCORES = {0.0, 0.25, 0.5, 0.75, 1.0}
BLOCK_TYPES = {"hook", "concept", "formula", "example", "pitfall", "summary", "check"}

# ชนิดคำตอบของแม่แบบ — number ใช้ answer_expr, label/text ต้องใช้ provider
ANSWER_KINDS = {"number", "label", "text"}
FIGURE_TYPES = {"svg", "needs_drawing"}

LICENSE_STATUS = {"official_public", "permission_granted", "unknown", "restricted"}
VISIBILITY = {"public", "logged_in", "internal_only"}
TRANSCRIPTION_STATUS = {"raw", "checked"}
SOURCE_KINDS = {"official_release", "user_provided_file", "community_transcript"}
ANSWER_SOURCES = {"official_key", "our_solution", "unknown"}

# review_status: 03-schema กำหนด "ai_draft" / "human_verified"
# และ 06 เพิ่ม "ai_draft_needs_fact_check" สำหรับวิชาที่ต้องตรวจข้อเท็จจริง
REVIEW_STATUS = {"ai_draft", "ai_draft_needs_fact_check", "human_verified"}

# ---------------------------------------------------------------- นิพจน์ปลอดภัย

SAFE_FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "radians": math.radians, "degrees": math.degrees,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
    "min": min, "max": max,
}
SAFE_CONSTS = {"pi": math.pi, "e": math.e}

_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
_CMPOPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
}


class ExprError(Exception):
    """นิพจน์ไม่ปลอดภัยหรือเขียนผิด"""


def check_expr(expr: str, var_names) -> list[str]:
    """ตรวจว่านิพจน์ใช้ได้ตามกฎใน 03-schema ข้อ C.4 คืนรายการปัญหา (ว่าง = ผ่าน)"""
    if not isinstance(expr, str) or not expr.strip():
        return ["นิพจน์ว่าง"]
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        return [f"เขียนนิพจน์ผิดไวยากรณ์: {e.msg}"]

    allowed_names = set(var_names) | set(SAFE_CONSTS)
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare,
                             ast.BoolOp, ast.And, ast.Or, ast.Load)):
            continue
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float, bool)):
                problems.append(f"ใช้ค่าคงที่ที่ไม่ใช่ตัวเลข: {node.value!r}")
            continue
        if type(node) in _BINOPS or type(node) in _UNARYOPS or type(node) in _CMPOPS:
            continue
        if isinstance(node, ast.Name):
            if node.id in SAFE_FUNCS:
                continue
            if node.id not in allowed_names:
                problems.append(
                    f"ใช้ชื่อ '{node.id}' ที่ไม่ได้ประกาศใน vars และไม่ใช่ค่าคงที่/ฟังก์ชันที่อนุญาต"
                )
            continue
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCS:
                problems.append("เรียกฟังก์ชันที่ไม่อนุญาต")
            if node.keywords:
                problems.append("ห้ามใช้ keyword argument ในนิพจน์")
            continue
        problems.append(f"ใช้โครงสร้างที่ไม่อนุญาต: {type(node).__name__}")
    return problems


def eval_expr(expr: str, values: dict):
    """คำนวณนิพจน์แบบจำกัดสิทธิ์ (ไม่มี builtins ไม่มี import)"""
    tree = ast.parse(expr, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in values:
                return values[node.id]
            if node.id in SAFE_CONSTS:
                return SAFE_CONSTS[node.id]
            raise ExprError(f"ไม่รู้จักตัวแปร '{node.id}'")
        if isinstance(node, ast.BinOp):
            op = _BINOPS.get(type(node.op))
            if op is None:
                raise ExprError("ตัวดำเนินการไม่อนุญาต")
            return op(ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp):
            op = _UNARYOPS.get(type(node.op))
            if op is None:
                raise ExprError("ตัวดำเนินการไม่อนุญาต")
            return op(ev(node.operand))
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op_node, right_node in zip(node.ops, node.comparators):
                op = _CMPOPS.get(type(op_node))
                if op is None:
                    raise ExprError("ตัวเปรียบเทียบไม่อนุญาต")
                right = ev(right_node)
                if not op(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            vals = [ev(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCS:
                raise ExprError("เรียกฟังก์ชันที่ไม่อนุญาต")
            return SAFE_FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise ExprError(f"โครงสร้างไม่อนุญาต: {type(node).__name__}")

    return ev(tree)


def render_stem(template_text: str, values: dict) -> str:
    """แทนค่า {ชื่อตัวแปร} ในโจทย์

    แทนเฉพาะชื่อที่ประกาศใน vars เท่านั้น จึงไม่กระทบวงเล็บปีกกาของ LaTeX
    (เช่น \\frac{a}{b} จะไม่ถูกแตะ) — อย่าใช้ str.format กับข้อความที่มี LaTeX
    """
    out = template_text
    for name, val in values.items():
        out = out.replace("{" + name + "}", _fmt(val))
    return out


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


# ตัวหาช่องแทนค่า {ชื่อ} ที่ "ไม่ใช่" วงเล็บปีกกาของ LaTeX
#
# LaTeX เขียนปีกกาต่อท้ายคำสั่งหรือต่อท้ายปีกกาอีกอัน เช่น \frac{n}{2} หรือ $x_{1}$
# จึงข้ามกรณีที่ตัวอักษรก่อนปีกกาเปิดเป็น \ } ตัวอักษร ตัวเลข _ หรือ ^
# ทำให้เหลือเฉพาะช่องแทนค่าจริงที่ยืนเดี่ยว ๆ ในข้อความ
_PLACEHOLDER_RE = re.compile(
    r"(?:^|(?<=[^\\}\w_^]))\{([A-Za-z_][A-Za-z0-9_]*|[฀-๿][฀-๿\w]*)\}"
)


def placeholders(text: str) -> set:
    """คืนชื่อช่องแทนค่าที่พบในข้อความ โดยไม่นับวงเล็บปีกกาของ LaTeX

    ใช้ตรวจว่ามีการอ้างชื่อตัวแปรที่พิมพ์ผิดหรือไม่ได้ประกาศไว้
    """
    if not isinstance(text, str):
        return set()
    return set(_PLACEHOLDER_RE.findall(text))


# ---------------------------------------------------------------- ความยาก C.3

def allowed_difficulty(sg: dict) -> set:
    """แปลง difficulty_signals เป็นช่วง difficulty ที่ยอมรับได้ ตามตาราง C.3"""
    steps = sg.get("steps_count", 0)
    topics = sg.get("topics_count", 1)
    heavy = bool(sg.get("heavy_computation"))
    trap = bool(sg.get("trap_present"))
    load = sg.get("reading_load", "low")

    if sg.get("needs_insight"):
        return {5}
    if steps >= 3 and (topics >= 2 or load == "high" or heavy):
        return {4}
    if steps >= 3:
        return {3, 4}
    if steps <= 2 and topics == 1 and not trap and not heavy and load == "low":
        return {1, 2}
    if trap or load == "medium" or topics >= 2:
        return {2, 3}
    return {2, 3}


# ---------------------------------------------------------------- รายงานผล

class Report:
    """เก็บ error / warning แล้วพิมพ์สรุปเป็นภาษาไทย"""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.files_checked = 0

    def error(self, where: str, msg: str) -> None:
        self.errors.append((where, msg))

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append((where, msg))

    def print_summary(self, title: str = "ผลการตรวจ") -> int:
        print()
        print("=" * 72)
        print(f"  {title}")
        print("=" * 72)
        if self.errors:
            print(f"\n[ต้องแก้] {len(self.errors)} รายการ")
            for where, msg in self.errors:
                print(f"  X {where}\n      {msg}")
        if self.warnings:
            print(f"\n[ควรดู] {len(self.warnings)} รายการ")
            for where, msg in self.warnings:
                print(f"  ! {where}\n      {msg}")
        print()
        print(f"ไฟล์ที่ตรวจ: {self.files_checked}   "
              f"ต้องแก้: {len(self.errors)}   ควรดู: {len(self.warnings)}")
        if self.errors:
            print("=> ยังไม่ผ่าน แก้รายการ [ต้องแก้] ให้หมดก่อน")
        elif self.warnings:
            print("=> ผ่าน แต่มีรายการที่ควรดู")
        else:
            print("=> ผ่านทั้งหมด")
        return 1 if self.errors else 0


# ---------------------------------------------------------------- อ่านไฟล์

def load_json(path: pathlib.Path, rep: Report):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        rep.error(str(path), "ไม่พบไฟล์")
    except UnicodeDecodeError as e:
        rep.error(str(path), f"ไฟล์ไม่ใช่ UTF-8: {e}")
    except json.JSONDecodeError as e:
        rep.error(str(path), f"JSON ไม่ถูกต้อง (บรรทัด {e.lineno} คอลัมน์ {e.colno}): {e.msg}")
    return None


def data_root(start: pathlib.Path | None = None) -> pathlib.Path:
    """หาโฟลเดอร์ data/ ของโปรเจกต์ (ขึ้นจากตำแหน่งสคริปต์)"""
    here = (start or pathlib.Path(__file__)).resolve()
    for parent in [here] + list(here.parents):
        cand = parent / "data"
        if cand.is_dir():
            return cand
    return (here.parent.parent / "data")


def require(obj: dict, fields, where: str, rep: Report) -> bool:
    """ตรวจว่ามีฟิลด์บังคับครบ คืน False ถ้าขาด"""
    missing = [f for f in fields if f not in obj]
    if missing:
        rep.error(where, f"ขาดฟิลด์บังคับ: {', '.join(missing)}")
        return False
    return True


def enum_check(obj: dict, field: str, allowed: set, where: str, rep: Report) -> None:
    if field in obj and obj[field] not in allowed:
        rep.error(where, f"{field} = {obj[field]!r} ไม่อยู่ในค่าที่อนุญาต {sorted(allowed)}")


def utf8_stdout() -> None:
    """กัน UnicodeEncodeError บน Windows console"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
