"""provider: paper_fold.punch_pattern — พับกระดาษแล้วเจาะรู หาตำแหน่งรูเมื่อคลี่ออก

รูปแบบข้อสอบนี้อยู่ในผังสอบ TPAT3 ด้านมิติสัมพันธ์
(ผังสอบมีตัวอย่างเป็นการพับกระดาษเจาะรู)

## กฎที่ข้อสอบวัด

คลี่ย้อนกลับทีละรอยพับ **แต่ละรอยพับสะท้อนรูเพิ่มเป็นสองเท่า**
พับ 2 ครั้งเจาะ 1 รู คลี่ออกได้ 4 รู · พับ 3 ครั้งได้ 8 รู
และรูที่สะท้อนต้องสะท้อนข้าม **รอยพับนั้น** ไม่ใช่ข้ามแกนกลางของกระดาษทั้งแผ่น

## ทำไมทำเป็น provider

ตำแหน่งรูหลังคลี่คำนวณได้ 100% ด้วยการติดตามการสะท้อนของแต่ละชั้นกระดาษ
เหมือนที่ cube_net.py พับกล่องด้วยโค้ด และโจทย์ต้องมีรูปทั้งแผ่นที่พับแล้ว
และรูปตัวเลือกแต่ละตัว ซึ่งนิพจน์เลขคณิตทำไม่ได้

## ชั้นกระดาษเก็บเป็นการแปลงแบบสะท้อน

แต่ละชั้นคือฟังก์ชัน (x, y) ในกระดาษที่พับแล้ว -> (X, Y) ในกระดาษเดิม
เก็บเป็น (ax, bx, ay, by) หมายถึง X = ax*x + bx และ Y = ay*y + by
โดย ax, ay เป็น 1 หรือ -1 เท่านั้น ซึ่งพอสำหรับรอยพับที่ขนานกับขอบกระดาษ

## ตัวเลือกลวงมาจากกฎที่ใช้ผิด

ทุกตัวคำนวณจากความเข้าใจผิดที่เกิดขึ้นจริง จึงอธิบายเหตุผลได้ทุกตัว
และเป็นรูปที่สร้างจากโค้ด ไม่ได้วาดมือ

พารามิเตอร์
    size      int   ความกว้างและความสูงของตารางกระดาษ (4 หรือ 8)
    n_folds   int   จำนวนรอยพับ (2 หรือ 3)
"""

from __future__ import annotations

NAME = "paper_fold.punch_pattern"
DOC = ("พับกระดาษแล้วเจาะรู หาตำแหน่งรูเมื่อคลี่ออก "
       "— ตำแหน่งรูและรูปทุกตัวเลือกคำนวณจากโค้ด")
ANSWER_KIND = "text"

VAR_NAMES = ["size", "folds", "folds_text", "px", "py", "fw", "fh"]

# รหัสรอยพับ: L = พับซ้ายทับขวา, R = พับขวาทับซ้าย, T = พับบนทับล่าง, B = พับล่างทับบน
FOLD_TEXT = {
    "L": "พับครึ่งซ้ายทับลงบนครึ่งขวา",
    "R": "พับครึ่งขวาทับลงบนครึ่งซ้าย",
    "T": "พับครึ่งบนทับลงบนครึ่งล่าง",
    "B": "พับครึ่งล่างทับลงบนครึ่งบน",
}
CELL = 30
PAD = 8


def validate_params(params: dict) -> list[str]:
    bad: list[str] = []
    if not isinstance(params, dict):
        return ["params ต้องเป็นอ็อบเจกต์"]

    size = params.get("size")
    if size not in (4, 8):
        bad.append(f"size ต้องเป็น 4 หรือ 8 (พบ {size!r}) "
                   "เพราะต้องหารสองได้ตามจำนวนรอยพับ")
    n = params.get("n_folds")
    if n not in (2, 3):
        bad.append(f"n_folds ต้องเป็น 2 หรือ 3 (พบ {n!r})")

    if not bad:
        # พับแกนเดียวกันซ้ำได้ไม่เกิน log2(size) ครั้ง จึงต้องเช็กว่าขนาดพอ
        if size == 4 and n == 3:
            # 3 รอยพับกับตาราง 4x4 ต้องพับแกนหนึ่งสองครั้ง (4->2->1) ซึ่งยังได้
            pass
        if size == 4 and n > 4:
            bad.append("ตาราง 4x4 พับได้มากสุด 4 ครั้ง")
    return bad


def var_names(params: dict) -> list[str]:
    return list(VAR_NAMES)


# ---------------------------------------------------------------- การพับ

def _apply(layers, w, h, code):
    """พับหนึ่งครั้ง คืน (layers ใหม่, w ใหม่, h ใหม่) หรือ None ถ้าพับไม่ได้"""
    if code in ("L", "R"):
        if w % 2:
            return None
        half = w // 2
        out = []
        for ax, bx, ay, by in layers:
            if code == "R":
                out.append((ax, bx, ay, by))                      # ครึ่งซ้ายอยู่กับที่
                out.append((-ax, ax * (w - 1) + bx, ay, by))      # ครึ่งขวาสะท้อนมาทับ
            else:
                out.append((ax, ax * half + bx, ay, by))          # ครึ่งขวาอยู่กับที่
                out.append((-ax, ax * (half - 1) + bx, ay, by))   # ครึ่งซ้ายสะท้อนมาทับ
        return out, half, h

    if h % 2:
        return None
    half = h // 2
    out = []
    for ax, bx, ay, by in layers:
        if code == "B":
            out.append((ax, bx, ay, by))
            out.append((ax, bx, -ay, ay * (h - 1) + by))
        else:
            out.append((ax, bx, ay, ay * half + by))
            out.append((ax, bx, -ay, ay * (half - 1) + by))
    return out, w, half


def fold_layers(size: int, folds: list[str]):
    """คืน (layers, w, h) หลังพับตามลำดับ หรือ None ถ้าพับไม่ได้"""
    layers = [(1, 0, 1, 0)]
    w = h = size
    for code in folds:
        got = _apply(layers, w, h, code)
        if got is None:
            return None
        layers, w, h = got
    return layers, w, h


def _holes(layers, px: int, py: int) -> frozenset:
    return frozenset((ax * px + bx, ay * py + by) for ax, bx, ay, by in layers)


def draw(params: dict, rng) -> dict | None:
    size, n = params["size"], params["n_folds"]
    # สุ่มลำดับรอยพับที่พับได้จริงกับขนาดนี้
    folds = []
    w = h = size
    for _ in range(n):
        opts = []
        if w % 2 == 0 and w > 1:
            opts += ["L", "R"]
        if h % 2 == 0 and h > 1:
            opts += ["T", "B"]
        if not opts:
            return None
        code = rng.choice(opts)
        folds.append(code)
        if code in ("L", "R"):
            w //= 2
        else:
            h //= 2

    got = fold_layers(size, folds)
    if got is None:
        return None
    layers, fw, fh = got
    if len(layers) != 2 ** n:
        return None

    px, py = rng.randint(0, fw - 1), rng.randint(0, fh - 1)
    vals = {
        "size": size, "folds": folds,
        "folds_text": " แล้ว".join(FOLD_TEXT[c] for c in folds),
        "px": px, "py": py, "fw": fw, "fh": fh,
    }
    cands = _candidates(vals)
    if cands is None:
        return None
    if len({c[0] for c in cands}) != 5:
        return None
    return vals


# ---------------------------------------------------------------- ตัวเลือก

def _key(holes: frozenset) -> str:
    """ข้อความมาตรฐานของชุดรู ใช้เทียบว่าตัวเลือกซ้ำกันไหม"""
    return " ".join(f"({y + 1},{x + 1})" for x, y in sorted(holes, key=lambda p: (p[1], p[0])))


def _apply_translate(layers, w, h, code):
    """พับแบบ "เลื่อนทับ" แทนการสะท้อน — ใช้สร้างตัวเลือกลวง ไม่ใช่การพับที่ถูก

    คนที่เข้าใจผิดจะคิดว่าพับแล้วครึ่งที่ยกมาทับ "เลื่อนลงมาตรง ๆ"
    ที่จริงมันพลิกกลับด้าน ตำแหน่งรูที่คลี่ออกจึงต่างกัน
    """
    if code in ("L", "R"):
        if w % 2:
            return None
        half = w // 2
        out = []
        for ax, bx, ay, by in layers:
            if code == "R":
                out.append((ax, bx, ay, by))
                out.append((ax, ax * half + bx, ay, by))
            else:
                out.append((ax, ax * half + bx, ay, by))
                out.append((ax, bx, ay, by))
        return out, half, h
    if h % 2:
        return None
    half = h // 2
    out = []
    for ax, bx, ay, by in layers:
        if code == "B":
            out.append((ax, bx, ay, by))
            out.append((ax, bx, ay, ay * half + by))
        else:
            out.append((ax, bx, ay, ay * half + by))
            out.append((ax, bx, ay, by))
    return out, w, half


def _candidates(v: dict):
    """คืน [(ข้อความชุดรู, ชุดรู, เหตุผล, tag)] ตัวแรกคือคำตอบที่ถูก หรือ None ถ้าสร้างไม่ได้

    ตัวลวงทุกตัวเลือกมาโดยตั้งใจว่า **ต้องไม่ตรงกับคำตอบด้วยเหตุผลเชิงเรขาคณิต**
    เคยใช้กฎ "สะท้อนข้ามแกนกลางแผ่น" กับ "สลับแกนรอยพับ" แล้วพบว่าชนคำตอบ
    มากกว่าครึ่งของชุดที่สุ่มได้ เพราะรูปแบบรูที่พับสองแกนมักสมมาตรอยู่แล้ว
    จึงเปลี่ยนมาใช้กฎที่ต่างจากคำตอบเชิงโครงสร้าง
    """
    size, folds, px, py = v["size"], v["folds"], v["px"], v["py"]
    got = fold_layers(size, folds)
    if got is None:
        return None
    layers, fw, fh = got
    right = _holes(layers, px, py)

    top = layers[0]
    ox, oy = top[0] * px + top[1], top[2] * py + top[3]

    # ผิดแบบ 1: คลี่ไม่ครบ เหลือรูแค่ครึ่งเดียว โดยเก็บฝั่งที่มีรอยเจาะเดิมอยู่
    if folds[-1] in ("L", "R"):
        same = {(x, y) for x, y in right if (x < size // 2) == (ox < size // 2)}
    else:
        same = {(x, y) for x, y in right if (y < size // 2) == (oy < size // 2)}
    if len(same) != len(right) // 2:
        return None
    wrong_half = frozenset(same)

    # ผิดแบบ 2: ไม่สะท้อนเลย คิดว่าเจาะทะลุได้รูเดียว
    wrong_one = frozenset({(ox, oy)})

    # ผิดแบบ 3: คิดว่าครึ่งที่พับมาทับ "เลื่อนลงมาตรง ๆ" ไม่ได้พลิกกลับด้าน
    tl = [(1, 0, 1, 0)]
    tw = th = size
    for code in folds:
        step = _apply_translate(tl, tw, th, code)
        if step is None:
            return None
        tl, tw, th = step
    wrong_translate = _holes(tl, px, py)

    # ผิดแบบ 4: หมุนรูปแบบรูไป 90 องศา ความผิดพลาดเรื่องการวางแนวกระดาษ
    wrong_rotate = frozenset((size - 1 - y, x) for x, y in right)

    out = [
        (_key(right), right, "", ""),
        (_key(wrong_half), wrong_half,
         f"คลี่ไม่ครบทุกรอยพับ ได้รูเพียง {len(wrong_half)} รู "
         f"ที่จริงพับ {len(folds)} ครั้งต้องได้ {len(right)} รู",
         "unfolded_partially"),
        (_key(wrong_one), wrong_one,
         "คิดว่าเจาะครั้งเดียวได้รูเดียว ที่จริงกระดาษที่พับซ้อนกันอยู่หลายชั้น "
         "เจาะครั้งเดียวจึงทะลุทุกชั้น",
         "single_hole"),
        (_key(wrong_translate), wrong_translate,
         "คิดว่าครึ่งที่พับมาทับเลื่อนลงมาตรง ๆ ที่จริงมันพลิกกลับด้าน "
         "ตำแหน่งรูจึงต้องสะท้อนข้ามรอยพับ ไม่ใช่เลื่อนมาซ้อน",
         "translated_not_mirrored"),
        (_key(wrong_rotate), wrong_rotate,
         "วางแนวกระดาษผิด ได้รูปแบบรูที่ถูกแต่หมุนไป 90 องศา",
         "rotated_90"),
    ]
    return out


# ---------------------------------------------------------------- รูป

def sheet_svg(w: int, h: int, holes, fold_marks=None) -> str:
    """วาดกระดาษ w x h พร้อมรูที่ระบุ (holes เป็นเซตของ (x, y) เริ่มจาก 0)"""
    width = PAD * 2 + w * CELL
    height = PAD * 2 + h * CELL
    parts = [f'<rect x="{PAD}" y="{PAD}" width="{w * CELL}" height="{h * CELL}"/>']
    for i in range(1, w):
        x = PAD + i * CELL
        parts.append(f'<line x1="{x}" y1="{PAD}" x2="{x}" y2="{PAD + h * CELL}" '
                     f'stroke-dasharray="3 3"/>')
    for i in range(1, h):
        y = PAD + i * CELL
        parts.append(f'<line x1="{PAD}" y1="{y}" x2="{PAD + w * CELL}" y2="{y}" '
                     f'stroke-dasharray="3 3"/>')
    grid = f'<g fill="none" stroke="currentColor" stroke-width="2">{"".join(parts)}</g>'

    circles = "".join(
        f'<circle cx="{PAD + x * CELL + CELL // 2}" cy="{PAD + y * CELL + CELL // 2}" '
        f'r="{CELL // 3}"/>' for x, y in sorted(holes)
    )
    dots = f'<g fill="currentColor">{circles}</g>'
    return (f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img">{grid}{dots}</svg>')


def _alt(holes, w, h, what: str) -> str:
    if not holes:
        return f"กระดาษ {w} x {h} ช่อง ไม่มีรู"
    spots = ", ".join(f"แถวที่ {y + 1} ช่องที่ {x + 1}"
                      for x, y in sorted(holes, key=lambda p: (p[1], p[0])))
    return f"{what} ตาราง {w} x {h} ช่อง มีรู {len(holes)} รู ที่ {spots}"


def build(params: dict, vals: dict) -> dict:
    size = vals["size"]
    folds = vals["folds"]
    px, py, fw, fh = vals["px"], vals["py"], vals["fw"], vals["fh"]

    cands = _candidates(vals)
    if cands is None:
        raise ValueError(f"สร้างตัวเลือกจากค่า {vals} ไม่ได้")

    answer_key, answer_holes = cands[0][0], cands[0][1]
    figures = [{
        "id": "fig1",
        "type": "svg",
        "alt": _alt({(px, py)}, fw, fh, "กระดาษที่พับแล้วและตำแหน่งที่เจาะ"),
        "svg": sheet_svg(fw, fh, {(px, py)}),
        "caption": "กระดาษหลังพับครบทุกรอย จุดทึบคือตำแหน่งที่เจาะ",
    }]
    distractors = []
    for i, (key, holes, why, tag) in enumerate(cands):
        fid = f"fig{i + 2}"
        figures.append({
            "id": fid,
            "type": "svg",
            "alt": _alt(holes, size, size, "กระดาษที่คลี่ออกแล้ว"),
            "svg": sheet_svg(size, size, holes),
            "caption": None,
        })
        if i == 0:
            answer_fig = fid
        else:
            distractors.append({"value": key, "reason": why, "tag": tag, "fig": fid})

    n = len(folds)
    steps = [
        {"do_md": f"นับรอยพับ: พับ {n} ครั้ง กระดาษจึงซ้อนกัน {2 ** n} ชั้น",
         "why_md": "เจาะครั้งเดียวทะลุทุกชั้น จำนวนรูหลังคลี่จึงเท่ากับจำนวนชั้น "
                   "ใช้ตัดตัวเลือกที่จำนวนรูไม่ตรงได้ทันที"},
        {"do_md": f"คลี่รอยพับสุดท้าย ({FOLD_TEXT[folds[-1]]}) "
                  f"รูจะสะท้อนข้ามรอยพับนั้นเพิ่มเป็นสองเท่า",
         "why_md": "คลี่ย้อนจากรอยพับล่าสุดไปหารอยแรก ถ้าคลี่สลับลำดับจะได้ตำแหน่งผิด"},
        {"do_md": "คลี่รอยที่เหลือทีละรอย สะท้อนรูข้ามรอยพับนั้นทุกครั้ง "
                  f"จนได้รูครบ {len(answer_holes)} รู",
         "why_md": "ต้องสะท้อนข้ามเส้นรอยพับจริง ไม่ใช่ข้ามแกนกลางของกระดาษทั้งแผ่น "
                   "ซึ่งเป็นสองเส้นที่ไม่ตรงกันเมื่อพับไม่สมมาตร"},
        {"do_md": f"ได้ตำแหน่งรูทั้งหมดคือ {answer_key}",
         "why_md": "ตรวจครั้งสุดท้ายว่าจำนวนรูตรงกับจำนวนชั้นที่นับไว้ในขั้นแรก"},
    ]
    hints = [
        f"เริ่มจากนับว่าพับกี่ครั้ง แล้วกระดาษซ้อนกันกี่ชั้น "
        f"จำนวนรูหลังคลี่ต้องเท่ากับจำนวนชั้น",
        "คลี่ย้อนกลับทีละรอยพับ จากรอยที่พับล่าสุดไปหารอยที่พับก่อน",
        "แต่ละครั้งที่คลี่ ให้สะท้อนรูข้าม **เส้นรอยพับนั้น** "
        "ไม่ใช่ข้ามเส้นกลางของกระดาษทั้งแผ่น",
    ]
    explanation = (
        f"พับ {n} ครั้งทำให้กระดาษซ้อนกัน {2 ** n} ชั้น เจาะครั้งเดียวจึงได้ "
        f"{len(answer_holes)} รู เมื่อคลี่ย้อนทีละรอยพับและสะท้อนรูข้ามรอยพับนั้นทุกครั้ง "
        f"ได้ตำแหน่งรูคือ {answer_key}"
    )

    return {
        "answer": answer_key,
        "answer_fig": answer_fig,
        "distractors": distractors,
        "steps": steps,
        "hints": hints,
        "explanation": explanation,
        "figures": figures,
        "meta": {"folds": folds, "layers": 2 ** n, "holes": len(answer_holes)},
    }
