"""mech.py — กลไกเชิงกล: คาน รอก ระบบส่งกำลัง และแรงสมดุล

ใช้กับโจทย์ TPAT3 ส่วนความถนัดเชิงกลและฟิสิกส์

หลักที่ยึด (เหมือน cube_net.py และ shape3d.py)
    - ระบบหนึ่งเก็บเป็น "ข้อมูล" ก่อน แล้วทั้งภาพและเฉลยสร้างจากข้อมูลชุดเดียวกัน
      จึงไม่มีทางที่ภาพกับเฉลยจะไม่ตรงกัน
    - เลขคำตอบคำนวณด้วย Fraction เสมอ ไม่ใช้ทศนิยมลอย ๆ
    - ฟังก์ชันที่คืนคำตอบจะ assert เงื่อนไขทางฟิสิกส์ไว้ด้วย ถ้าโจทย์ตั้งไว้ผิดจะหยุดทันที

หน่วยที่ใช้ทั้งไฟล์
    แรงเป็นนิวตัน · ระยะเป็นเมตร · โมเมนต์เป็นนิวตัน-เมตร · ใช้ g = 10 m/s²

วิธีตรวจตัวเอง
    python scripts/mech.py
"""

from __future__ import annotations

from fractions import Fraction as Fr

G = 10  # m/s² ใช้ค่านี้ทุกที่ และต้องเขียนบอกไว้ในโจทย์ทุกข้อที่ใช้

PAD = 14
ACCENT = "var(--accent, #3b5bdb)"


def F(x) -> Fr:
    """แปลงเป็นเศษส่วนให้ตรงกับที่เขียน — ทศนิยมต้องผ่าน str ก่อน

    ถ้าใช้ Fr(0.2) ตรง ๆ จะได้เศษส่วนของเลขฐานสองที่ใกล้เคียง ไม่ใช่หนึ่งในห้า
    ทำให้ผลลัพธ์กลายเป็นเศษส่วนหน้าตาประหลาดและเทียบกับจำนวนเต็มไม่ผ่าน
    """
    return Fr(str(x)) if isinstance(x, float) else Fr(x)


def _num(x) -> str:
    """เขียนจำนวนให้อ่านง่าย: จำนวนเต็มไม่ต้องมีจุด เศษส่วนลงตัวแล้วเขียนเป็นทศนิยม"""
    f = F(x)
    if f.denominator == 1:
        return str(f.numerator)
    d = float(f)
    s = f"{d:.4f}".rstrip("0").rstrip(".")
    return s


def _svg(w: int, h: int, body: str) -> str:
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img">'
            f'<g fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>')


def _label(x: int, y: int, text: str, size: int = 13, anchor: str = "middle") -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="currentColor" stroke="none">{text}</text>')


def _arrow_down(x: int, y: int, length: int, color: str = "currentColor") -> str:
    y2 = y + length
    return (f'<g stroke="{color}"><line x1="{x}" y1="{y}" x2="{x}" y2="{y2 - 8}"/>'
            f'<polygon points="{x},{y2} {x - 5},{y2 - 9} {x + 5},{y2 - 9}" '
            f'fill="{color}" stroke="none"/></g>')


def _arrow(x1: int, y1: int, x2: int, y2: int, color: str = ACCENT) -> str:
    """ลูกศรจาก (x1,y1) ไป (x2,y2) หัวลูกศรวาดจากทิศของเส้น"""
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - 10 * math.cos(ang), y2 - 10 * math.sin(ang)
    p1 = (bx - 5 * math.sin(ang), by + 5 * math.cos(ang))
    p2 = (bx + 5 * math.sin(ang), by - 5 * math.cos(ang))
    pts = f"{x2:.0f},{y2:.0f} {p1[0]:.0f},{p1[1]:.0f} {p2[0]:.0f},{p2[1]:.0f}"
    return (f'<g stroke="{color}"><line x1="{x1}" y1="{y1}" x2="{bx:.0f}" y2="{by:.0f}"/>'
            f'<polygon points="{pts}" fill="{color}" stroke="none"/></g>')


# ============================================================ คานและโมเมนต์

class Lever:
    """คานตรงยาว `length` เมตร มีจุดหมุนที่ `pivot` เมตรจากปลายซ้าย

    loads = [(ตำแหน่งเมตรจากปลายซ้าย, แรงนิวตันที่กดลง, ชื่อ)]
    โมเมนต์คิดรอบจุดหมุน: ทวนเข็ม (ซ้ายของจุดหมุน) เป็นบวก ตามเข็ม (ขวา) เป็นลบ
    """

    def __init__(self, length, pivot, loads):
        self.length = F(length)
        self.pivot = F(pivot)
        self.loads = [(F(x), F(f), name) for x, f, name in loads]
        assert 0 <= self.pivot <= self.length, "จุดหมุนต้องอยู่บนคาน"
        for x, f, _ in self.loads:
            assert 0 <= x <= self.length, "น้ำหนักต้องวางอยู่บนคาน"
            assert f != 0, "แรงเป็นศูนย์ไม่มีผลต่อคาน"

    def moment(self, side: str) -> Fr:
        """ผลรวมโมเมนต์ของแรงกดลงในด้านที่ระบุ ('left' หรือ 'right') รอบจุดหมุน

        นับเฉพาะแรงที่กดลง (ค่าบวก) เพราะใช้อธิบายคานกระดานหกซึ่งมีแต่น้ำหนักกดลง
        คานที่มีแรงยกขึ้นด้วยให้ใช้ torque() ซึ่งคิดทั้งทิศและด้านให้ครบ
        """
        out = Fr(0)
        for x, f, _ in self.loads:
            arm = self.pivot - x if side == "left" else x - self.pivot
            if arm > 0 and f > 0:
                out += f * arm
        return out

    def torque(self) -> Fr:
        """โมเมนต์รวมรอบจุดหมุน ตามเข็มเป็นบวก · แรงบวกคือกดลง แรงลบคือยกขึ้น"""
        return sum((f * (x - self.pivot) for x, f, _ in self.loads), Fr(0))

    def net(self) -> Fr:
        """โมเมนต์สุทธิ เป็นบวกแปลว่าด้านซ้ายชนะ (คานจะหมุนให้ซ้ายลง)"""
        return -self.torque()

    def balanced(self) -> bool:
        return self.torque() == 0

    def tips(self) -> str:
        n = self.net()
        return "สมดุล" if n == 0 else ("ซ้ายลง" if n > 0 else "ขวาลง")

    def solve_force(self, x, up: bool = False) -> Fr:
        """ขนาดของแรงที่ต้องเพิ่มที่ตำแหน่ง x เพื่อให้คานสมดุล

        up=False คือแรงกดลง (เช่น วางน้ำหนักถ่วง) · up=True คือแรงยกขึ้น
        (เช่น มือที่ยกด้ามรถเข็นล้อเดียว ซึ่งอยู่ด้านเดียวกับของ)
        """
        x = F(x)
        arm = x - self.pivot
        assert arm != 0, "วางที่จุดหมุนไม่ช่วยให้สมดุล เพราะแขนโมเมนต์เป็นศูนย์"
        coeff = (-1 if up else 1) * arm
        f = -self.torque() / coeff
        assert f > 0, "ทิศหรือตำแหน่งที่เลือกทำให้คานยิ่งเสียสมดุล"
        chk = Lever(self.length, self.pivot,
                    list(self.loads) + [(x, -f if up else f, "ใหม่")])
        assert chk.balanced(), "คำนวณแรงแล้วยังไม่สมดุล"
        return f

    def svg(self, width: int = 360) -> str:
        span = 40  # ความสูงส่วนที่วาดเหนือคาน
        x0, x1 = PAD + 10, width - PAD - 10
        scale = (x1 - x0) / float(self.length)
        y = PAD + span + 20

        def px(m) -> int:
            return int(round(x0 + float(m) * scale))

        body = [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke-width="4"/>']
        # จุดหมุนเป็นสามเหลี่ยม
        p = px(self.pivot)
        body.append(f'<polygon points="{p},{y + 3} {p - 12},{y + 26} {p + 12},{y + 26}" '
                    f'fill="currentColor" stroke="none"/>')
        body.append(f'<line x1="{p - 22}" y1="{y + 26}" x2="{p + 22}" y2="{y + 26}"/>')
        for x, f, name in self.loads:
            cx = px(x)
            if f > 0:
                body.append(_arrow_down(cx, y - span, span - 6))
            else:
                # แรงยกขึ้น วาดลูกศรชี้ขึ้นจากใต้คาน เพื่อให้เห็นว่าเป็นคนละทิศกับน้ำหนัก
                top = y - span + 6
                body.append(f'<g stroke="{ACCENT}"><line x1="{cx}" y1="{y - 6}" x2="{cx}" y2="{top + 8}"/>'
                            f'<polygon points="{cx},{top} {cx - 5},{top + 9} {cx + 5},{top + 9}" '
                            f'fill="{ACCENT}" stroke="none"/></g>')
            body.append(_label(cx, y - span - 6, f"{name} {_num(abs(f))} N"))
            # ระยะจากจุดหมุน
            d = abs(x - self.pivot)
            if d > 0:
                mid = (cx + p) // 2
                body.append(f'<line x1="{cx}" y1="{y + 34}" x2="{p}" y2="{y + 34}" '
                            f'stroke="{ACCENT}" stroke-width="1.5"/>')
                body.append(_label(mid, y + 50, f"{_num(d)} m", 12))
        return _svg(width, y + 62, "".join(body))

    def alt(self) -> str:
        parts = [f"คานยาว {_num(self.length)} เมตร จุดหมุนอยู่ห่างจากปลายซ้าย {_num(self.pivot)} เมตร"]
        for x, f, name in self.loads:
            side = "ซ้าย" if x < self.pivot else ("ขวา" if x > self.pivot else "ตรง")
            dirn = "กดลง" if f > 0 else "ยกขึ้น"
            parts.append(f"{name} {_num(abs(f))} นิวตัน {dirn}ห่างจากจุดหมุนไปทาง{side} "
                         f"{_num(abs(x - self.pivot))} เมตร")
        return " · ".join(parts)

    def fig(self, fid: str = "fig1", caption: str = "คานและจุดหมุน") -> dict:
        return {"id": fid, "type": "svg", "svg": self.svg(), "alt": self.alt(), "caption": caption}


# ============================================================ รอก

class Tackle:
    """ระบบรอกพวง: บล็อกล่าง (เคลื่อนที่) มี k ล้อ บล็อกบน (ยึดเพดาน) มี k ล้อ

    เชือกเส้นเดียวเริ่มจากผูกที่บล็อกบน แล้วอ้อมล้อสลับบน-ล่าง ปลายเชือกเป็นแรงดึง
    จำนวนเส้นเชือกที่พาดระหว่างสองบล็อกคือสิ่งที่รับน้ำหนัก และนับจากเส้นทางเชือกจริง
    ที่ใช้วาดภาพ จึงไม่มีทางกรอกตัวเลขได้เปรียบเชิงกลผิด
    """

    def __init__(self, k: int, load):
        assert k >= 1, "ต้องมีล้อที่บล็อกล่างอย่างน้อยหนึ่งล้อ"
        self.k = k
        self.load = F(load)
        self.path = self._build_path()

    def _build_path(self) -> list:
        """เส้นทางเชือกเป็นลำดับของ ('top'|'bottom', index) ตามลำดับที่เชือกพาด"""
        seq = [("anchor_top", 0)]
        for i in range(self.k):
            seq.append(("bottom", i))
            seq.append(("top", i))
        seq.append(("free_end", 0))
        return seq

    def supporting(self) -> int:
        """นับเส้นเชือกที่พาดระหว่างบล็อกบนกับบล็อกล่าง = ได้เปรียบเชิงกล"""
        n = 0
        for a, b in zip(self.path, self.path[1:]):
            ka = "bottom" if a[0] == "bottom" else "top"
            kb = "bottom" if b[0] == "bottom" else "top"
            if ka != kb:
                n += 1
        return n

    def ma(self) -> int:
        return self.supporting()

    def effort(self) -> Fr:
        """แรงดึงที่ต้องออก (รอกอุดมคติ ไม่คิดแรงเสียดทานและน้ำหนักรอก)"""
        return self.load / self.ma()

    def rope_pulled(self, height) -> Fr:
        """ต้องดึงเชือกยาวเท่าไรเพื่อยกของขึ้นสูง `height` เมตร (งานเข้า = งานออก)"""
        h = F(height)
        s = h * self.ma()
        assert self.effort() * s == self.load * h, "งานเข้าไม่เท่างานออก แบบจำลองผิด"
        return s

    def svg(self, width: int = 300) -> str:
        """เส้นเชือกวาดเป็นเส้นตรงแนวตั้งขนานกัน แล้วให้ล้ออยู่ระหว่างเส้นคู่ที่มันคล้องอยู่

        เส้นแนวตั้งหนึ่งเส้น = เส้นเชือกที่รับน้ำหนักหนึ่งเส้น จำนวนเส้นในภาพจึงเท่ากับ
        supporting() เสมอ เพราะวาดจากเส้นทางเชือกชุดเดียวกับที่ใช้คำนวณ
        """
        n = self.supporting()                  # จำนวนเส้นแนวตั้งระหว่างบล็อก
        sp = 26                                # ระยะห่างระหว่างเส้นเชือก
        r = sp // 2                            # รัศมีล้อ = ครึ่งระยะห่าง เชือกจึงแตะขอบล้อพอดี
        y_top, y_bot = PAD + 46, PAD + 168
        need = (n + 1) * sp + 70
        width = max(width, need)
        x0 = (width - n * sp) // 2             # ตำแหน่งเส้นแรก
        xs = [x0 + j * sp for j in range(n)]
        body = []

        # เพดานและลายขีด
        body.append(f'<line x1="{PAD}" y1="{PAD + 8}" x2="{width - PAD}" y2="{PAD + 8}" stroke-width="3"/>')
        for i in range(PAD, width - PAD, 12):
            body.append(f'<line x1="{i}" y1="{PAD + 8}" x2="{i + 7}" y2="{PAD + 1}" stroke-width="1.2"/>')

        # ล้อล่างคล้องเส้นคู่ (0,1), (2,3), ... · ล้อบนคล้องคู่ (1,2), (3,4), ... และคู่สุดท้ายคือปลายเชือก
        bottom_c = [(xs[j] + xs[j + 1]) // 2 for j in range(0, n - 1, 2)]
        top_c = [(xs[j] + xs[j + 1]) // 2 for j in range(1, n - 1, 2)]
        x_free = xs[-1] + sp                   # ปลายเชือกที่ใช้ดึง
        top_c.append((xs[-1] + x_free) // 2)
        assert len(bottom_c) == self.k and len(top_c) == self.k, "จำนวนล้อในภาพไม่ตรงกับแบบจำลอง"

        # โครงบล็อกบน ยึดเพดาน · ขยายให้คลุมปลายเชือกที่ผูกตายไว้กับบล็อกด้วย
        bx0, bx1 = min(xs[0] - 8, min(top_c) - r - 6), max(top_c) + r + 6
        body.append(f'<line x1="{(bx0 + bx1) // 2}" y1="{PAD + 8}" x2="{(bx0 + bx1) // 2}" y2="{y_top - r - 6}"/>')
        body.append(f'<rect x="{bx0}" y="{y_top - r - 6}" width="{bx1 - bx0}" height="{2 * r + 12}" rx="6"/>')
        # โครงบล็อกล่าง
        lx0, lx1 = min(bottom_c) - r - 6, max(bottom_c) + r + 6
        body.append(f'<rect x="{lx0}" y="{y_bot - r - 6}" width="{lx1 - lx0}" height="{2 * r + 12}" rx="6"/>')

        # เส้นเชือก วาดก่อนล้อเพื่อให้ล้อทับปลายเส้นพอดี
        # เส้นแรกคือปลายที่ผูกตายไว้ใต้บล็อกบน จึงเริ่มที่ขอบล่างของโครง ไม่ใช่กลางล้อ
        y_dead = y_top + r + 6
        body.append(f'<line x1="{xs[0]}" y1="{y_dead}" x2="{xs[0]}" y2="{y_bot}" '
                    f'stroke="{ACCENT}" stroke-width="2"/>')
        body.append(f'<circle cx="{xs[0]}" cy="{y_dead}" r="3.5" fill="{ACCENT}" stroke="none"/>')
        for x in xs[1:]:
            body.append(f'<line x1="{x}" y1="{y_top}" x2="{x}" y2="{y_bot}" stroke="{ACCENT}" stroke-width="2"/>')
        # ส่วนโค้งที่คล้องล้อ
        for c in bottom_c:
            body.append(f'<path d="M {c - r} {y_bot} A {r} {r} 0 0 0 {c + r} {y_bot}" '
                        f'stroke="{ACCENT}" stroke-width="2"/>')
        for c in top_c:
            body.append(f'<path d="M {c - r} {y_top} A {r} {r} 0 0 1 {c + r} {y_top}" '
                        f'stroke="{ACCENT}" stroke-width="2"/>')
        # ปลายเชือกที่ดึงลง
        body.append(f'<line x1="{x_free}" y1="{y_top}" x2="{x_free}" y2="{y_bot + 6}" '
                    f'stroke="{ACCENT}" stroke-width="2"/>')
        body.append(_arrow_down(x_free, y_bot + 6, 26, ACCENT))
        body.append(_label(x_free + 4, y_bot + 46, "แรงดึง", 12, "start"))

        for c in top_c:
            body.append(f'<circle cx="{c}" cy="{y_top}" r="{r}"/>')
            body.append(f'<circle cx="{c}" cy="{y_top}" r="2.5" fill="currentColor" stroke="none"/>')
        for c in bottom_c:
            body.append(f'<circle cx="{c}" cy="{y_bot}" r="{r}"/>')
            body.append(f'<circle cx="{c}" cy="{y_bot}" r="2.5" fill="currentColor" stroke="none"/>')

        # ของที่ยก แขวนใต้บล็อกล่าง
        lcx = (lx0 + lx1) // 2
        bw = max(66, lx1 - lx0)
        y_box = y_bot + r + 20
        body.append(f'<line x1="{lcx}" y1="{y_bot + r + 6}" x2="{lcx}" y2="{y_box}"/>')
        body.append(f'<rect x="{lcx - bw // 2}" y="{y_box}" width="{bw}" height="32" rx="4"/>')
        body.append(_label(lcx, y_box + 21, f"{_num(self.load)} N"))
        return _svg(width, y_box + 48, "".join(body))

    def alt(self) -> str:
        return (f"ระบบรอกพวง: บล็อกบนยึดเพดานมี {self.k} ล้อ บล็อกล่างเคลื่อนที่ได้มี {self.k} ล้อ "
                f"แขวนของหนัก {_num(self.load)} นิวตัน มีเส้นเชือกพาดระหว่างสองบล็อก {self.ma()} เส้น "
                f"ปลายเชือกอีกด้านเป็นแรงดึงลง")

    def fig(self, fid: str = "fig1", caption: str = "ระบบรอกพวง") -> dict:
        return {"id": fid, "type": "svg", "svg": self.svg(), "alt": self.alt(), "caption": caption}


# ============================================================ ระบบส่งกำลัง

LINKS = {
    "mesh": (-1, "ขบกัน"),          # เฟืองขบกันตรง ๆ หมุนสวนทาง
    "belt": (+1, "สายพานไม่ไขว้"),   # สายพานปกติ หมุนทางเดียวกัน
    "cross": (-1, "สายพานไขว้"),     # สายพานไขว้ หมุนสวนทาง
    "shaft": (+1, "เพลาเดียวกัน"),   # ยึดเพลาเดียวกัน หมุนทางเดียวกันและเร็วเท่ากัน
}


class Drive:
    """ระบบส่งกำลังเป็นลูกโซ่: wheels = [(ชื่อ, ขนาด)] · links[i] เชื่อม wheels[i] กับ wheels[i+1]

    ขนาดคือจำนวนฟัน (เฟือง) หรือรัศมี (ล้อสายพาน) ใช้หน่วยเดียวกันทั้งระบบ
    ทิศและอัตราเร็วคำนวณไล่ไปตามลูกโซ่ ไม่ได้กรอกด้วยมือ
    """

    def __init__(self, wheels, links):
        assert len(links) == len(wheels) - 1, "จำนวนการเชื่อมต่อต้องน้อยกว่าจำนวนล้อหนึ่งตัว"
        for k in links:
            assert k in LINKS, f"ไม่รู้จักการเชื่อมต่อ {k}"
        self.wheels = [(n, F(s)) for n, s in wheels]
        self.links = list(links)

    def spin(self) -> list:
        """ทิศหมุนของทุกล้อ เทียบกับล้อแรก: +1 ทางเดียวกัน · -1 สวนทาง"""
        out = [1]
        for k in self.links:
            out.append(out[-1] * LINKS[k][0])
        return out

    def speed(self) -> list:
        """อัตราเร็วเชิงมุมของทุกล้อ เทียบกับล้อแรกเป็น 1"""
        out = [Fr(1)]
        for i, k in enumerate(self.links):
            _, s1 = self.wheels[i]
            _, s2 = self.wheels[i + 1]
            out.append(out[-1] if k == "shaft" else out[-1] * s1 / s2)
        return out

    def ratio(self) -> Fr:
        """อัตราทดรวม = อัตราเร็วล้อแรกหารอัตราเร็วล้อสุดท้าย"""
        return 1 / self.speed()[-1]

    def same_direction(self, i: int, j: int) -> bool:
        s = self.spin()
        return s[i] == s[j]

    def svg(self, width: int = 380) -> str:
        n = len(self.wheels)
        sizes = [float(s) for _, s in self.wheels]
        mx = max(sizes)
        rs = [int(14 + 22 * (s / mx)) for s in sizes]
        gap = (width - 2 * PAD - sum(2 * r for r in rs)) // max(1, n - 1) if n > 1 else 0
        cy = PAD + int(mx and max(rs)) + 30
        body, x = [], PAD
        cxs = []
        for r in rs:
            cxs.append(x + r)
            x += 2 * r + gap
        for i, ((name, size), r) in enumerate(zip(self.wheels, rs)):
            cx = cxs[i]
            body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>')
            body.append(f'<circle cx="{cx}" cy="{cy}" r="3" fill="currentColor" stroke="none"/>')
            body.append(_label(cx, cy + r + 18, f"{name} ({_num(size)})", 12))
        for i, k in enumerate(self.links):
            a, b = cxs[i], cxs[i + 1]
            ra, rb = rs[i], rs[i + 1]
            if k == "shaft":
                body.append(f'<line x1="{a}" y1="{cy}" x2="{b}" y2="{cy}" stroke="{ACCENT}" stroke-width="3"/>')
            elif k == "mesh":
                body.append(f'<line x1="{a + ra}" y1="{cy}" x2="{b - rb}" y2="{cy}" '
                            f'stroke="{ACCENT}" stroke-width="2" stroke-dasharray="3 3"/>')
            else:
                top = (f'<line x1="{a}" y1="{cy - ra}" x2="{b}" y2="{cy - rb}" '
                       f'stroke="{ACCENT}" stroke-width="1.6"/>'
                       f'<line x1="{a}" y1="{cy + ra}" x2="{b}" y2="{cy + rb}" '
                       f'stroke="{ACCENT}" stroke-width="1.6"/>')
                if k == "cross":
                    top = (f'<line x1="{a}" y1="{cy - ra}" x2="{b}" y2="{cy + rb}" '
                           f'stroke="{ACCENT}" stroke-width="1.6"/>'
                           f'<line x1="{a}" y1="{cy + ra}" x2="{b}" y2="{cy - rb}" '
                           f'stroke="{ACCENT}" stroke-width="1.6"/>')
                body.append(top)
            mid = (a + b) // 2
            body.append(_label(mid, cy - max(ra, rb) - 10, LINKS[k][1], 11))
        return _svg(width, cy + max(rs) + 30, "".join(body))

    def alt(self) -> str:
        parts = []
        for i, k in enumerate(self.links):
            n1 = self.wheels[i][0]
            n2 = self.wheels[i + 1][0]
            parts.append(f"{n1} กับ {n2} เชื่อมแบบ{LINKS[k][1]}")
        sz = " · ".join(f"{n} ขนาด {_num(s)}" for n, s in self.wheels)
        return f"ระบบส่งกำลังเรียงกัน: {sz} · " + " · ".join(parts)

    def fig(self, fid: str = "fig1", caption: str = "ระบบส่งกำลัง") -> dict:
        return {"id": fid, "type": "svg", "svg": self.svg(), "alt": self.alt(), "caption": caption}


# ============================================================ แรงและสมดุล

class Forces:
    """แรงหลายแรงกระทำที่จุดเดียว: vectors = [(ชื่อ, fx, fy)] ให้ +x ไปขวา +y ขึ้น"""

    def __init__(self, vectors):
        self.v = [(n, F(x), F(y)) for n, x, y in vectors]

    def resultant(self) -> tuple:
        return (sum((x for _, x, _ in self.v), Fr(0)), sum((y for _, _, y in self.v), Fr(0)))

    def balanced(self) -> bool:
        return self.resultant() == (Fr(0), Fr(0))

    def needed(self) -> tuple:
        """แรงที่ต้องเพิ่มเพื่อให้สมดุล"""
        rx, ry = self.resultant()
        return (-rx, -ry)

    def magnitude(self) -> Fr:
        """ขนาดของแรงลัพธ์ ใช้ได้เมื่อผลออกมาเป็นจำนวนลงตัว (เลือกเลขให้ลงตัวเสมอ)"""
        rx, ry = self.resultant()
        sq = rx * rx + ry * ry
        root = Fr(int(round(float(sq) ** 0.5)))
        assert root * root == sq, f"ขนาดแรงลัพธ์ไม่ลงตัว ({sq}) ให้เลือกเลขชุดพีทาโกรัส"
        return root

    def svg(self, width: int = 300, scale: float = 0.0) -> str:
        cy = width // 2
        cx = width // 2
        mx = max(max(abs(float(x)), abs(float(y))) for _, x, y in self.v)
        sc = scale or (width / 2 - 42) / mx
        body = [f'<circle cx="{cx}" cy="{cy}" r="4" fill="currentColor" stroke="none"/>']
        for name, x, y in self.v:
            ex = cx + float(x) * sc
            ey = cy - float(y) * sc          # y ในภาพชี้ลง จึงกลับเครื่องหมาย
            body.append(_arrow(cx, cy, int(round(ex)), int(round(ey))))
            lx = cx + float(x) * sc * 1.18
            ly = cy - float(y) * sc * 1.18
            body.append(_label(int(round(lx)), int(round(ly)) + 4, name, 12))
        return _svg(width, width, "".join(body))

    def alt(self) -> str:
        def d(x, y):
            if x and not y:
                return "ไปทางขวา" if x > 0 else "ไปทางซ้าย"
            if y and not x:
                return "ขึ้น" if y > 0 else "ลง"
            return f"เฉียง ({_num(x)}, {_num(y)})"
        return "แรงกระทำที่จุดเดียวกัน: " + " · ".join(
            f"{n} ขนาด {_num(Forces([(n, x, y)]).magnitude())} นิวตัน {d(x, y)}" for n, x, y in self.v)

    def fig(self, fid: str = "fig1", caption: str = "แรงที่กระทำต่อวัตถุ") -> dict:
        return {"id": fid, "type": "svg", "svg": self.svg(), "alt": self.alt(), "caption": caption}


# ============================================================ ภาพฉายของทรงสามมิติ

def projections(cells) -> dict:
    """ภาพฉายสามด้านของทรงที่ประกอบจากลูกบาศก์ (ใช้แกนเดียวกับ shape3d)

    front = มองจากด้าน -y เห็นระนาบ (x, z) · side = มองจากด้าน +x เห็น (y, z) · top = มองจากบน เห็น (x, y)
    คืนค่าเป็นเซตของช่อง (col, row) แบบเดียวกับ shape2d เพื่อวาดต่อได้ทันที
    """
    cs = [tuple(c) for c in cells]
    zmax = max(z for _, _, z in cs)
    ymax = max(y for _, y, _ in cs)
    front = {(x, zmax - z) for x, _, z in cs}
    side = {(y, zmax - z) for _, y, z in cs}
    top = {(x, ymax - y) for x, y, _ in cs}
    return {"front": front, "side": side, "top": top}


# ============================================================ ตรวจตัวเอง

def _selfcheck() -> int:
    bad = 0

    def ok(cond, msg):
        nonlocal bad
        if not cond:
            bad += 1
            print("  ผิด  ", msg)

    # --- คาน: กฎโมเมนต์ที่รู้คำตอบอยู่แล้ว
    lv = Lever(4, 2, [(0, 30, "ก"), (3, 30, "ข")])
    ok(lv.moment("left") == 60 and lv.moment("right") == 30, "โมเมนต์สองข้างของคานตัวอย่าง")
    ok(lv.tips() == "ซ้ายลง", "คานที่ซ้ายหนักกว่าต้องเอียงซ้ายลง")
    ok(Lever(4, 2, [(0, 30, "ก"), (4, 30, "ข")]).balanced(), "คานสมมาตรต้องสมดุล")
    ok(Lever(6, 2, [(0, 60, "ก")]).solve_force(5) == 40, "แรงที่ต้องใช้ถ่วงให้สมดุล = 120/3")
    # คานชั้นหนึ่งแบบคานดีดคานงัด: แขนยาวกว่าต้องใช้แรงน้อยกว่า
    ok(Lever(5, 1, [(0, 100, "ของ")]).solve_force(5) == 25, "แขนยาว 4 เท่า ใช้แรงหนึ่งในสี่")
    # คานอันดับสอง เช่น รถเข็นล้อเดียว จุดหมุนอยู่ปลายคาน แรงยกอยู่ด้านเดียวกับของ
    wb = Lever(1.2, 0, [(0.4, 900, "ของ")])
    ok(wb.solve_force(1.2, up=True) == 300, f"รถเข็นล้อเดียวควรใช้แรง 300 N (ได้ {wb.solve_force(1.2, up=True)})")
    ok(Lever(1.2, 0, [(0.4, 900, "ของ"), (1.2, -300, "มือ")]).balanced(), "รถเข็นที่ใส่แรงยกแล้วต้องสมดุล")
    ok(Lever(1.4, 0.2, [(0, 600, "ของ")]).solve_force(1.4) == 100, "ชะแลงควรใช้แรง 100 N")


    # --- รอก: ได้เปรียบเชิงกลต้องเท่ากับจำนวนเส้นเชือกที่นับจากเส้นทางจริง
    for k, expect in [(1, 2), (2, 4), (3, 6)]:
        t = Tackle(k, 600)
        ok(t.ma() == expect, f"รอก {k} ล้อล่างต้องได้เปรียบ {expect} เท่า (ได้ {t.ma()})")
        ok(t.effort() == Fr(600, expect), f"แรงดึงของรอก {k} ล้อล่าง")
        ok(t.rope_pulled(2) == 2 * expect, f"ระยะดึงเชือกของรอก {k} ล้อล่าง")
    ok(Tackle(2, 800).effort() == 200, "รอกพวงสี่เส้น ยก 800 N ใช้แรง 200 N")

    # --- ระบบส่งกำลัง
    d = Drive([("A", 20), ("B", 60)], ["mesh"])
    ok(d.spin() == [1, -1], "เฟืองขบกันต้องหมุนสวนทาง")
    ok(d.speed()[1] == Fr(1, 3) and d.ratio() == 3, "เฟือง 20 ขับ 60 ต้องช้าลงสามเท่า")
    idler = Drive([("A", 20), ("B", 40), ("C", 20)], ["mesh", "mesh"])
    ok(idler.spin() == [1, -1, 1], "เฟืองกลางทำให้ตัวปลายหมุนทางเดียวกับตัวขับ")
    ok(idler.ratio() == 1, "เฟืองกลางไม่เปลี่ยนอัตราทดรวม")
    belt = Drive([("A", 10), ("B", 30)], ["belt"])
    ok(belt.spin() == [1, 1] and belt.ratio() == 3, "สายพานไม่ไขว้: ทางเดียวกัน อัตราทดตามรัศมี")
    ok(Drive([("A", 10), ("B", 30)], ["cross"]).spin() == [1, -1], "สายพานไขว้ต้องสวนทาง")
    sh = Drive([("A", 10), ("B", 40), ("C", 20)], ["shaft", "mesh"])
    ok(sh.speed() == [Fr(1), Fr(1), Fr(2)], "เพลาเดียวกันเร็วเท่ากัน แล้วค่อยทดที่คู่ที่ขบกัน")

    # --- แรง
    f = Forces([("F1", 3, 0), ("F2", 0, 4)])
    ok(f.magnitude() == 5, "แรงลัพธ์ของ 3 กับ 4 ตั้งฉากต้องเป็น 5")
    ok(f.needed() == (Fr(-3), Fr(-4)), "แรงที่ต้องเพิ่มเพื่อสมดุล")
    ok(Forces([("ก", 5, 0), ("ข", -5, 0)]).balanced(), "แรงเท่ากันทิศตรงข้ามต้องสมดุล")
    ok(not Forces([("ก", 5, 0), ("ข", -3, 0)]).balanced(), "แรงไม่เท่ากันต้องไม่สมดุล")

    # --- ภาพฉาย: ทรงตัว L สองชั้น
    cells = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 0, 1)]
    pr = projections(cells)
    ok(pr["front"] == {(0, 1), (1, 1), (2, 1), (0, 0)}, f"ภาพฉายด้านหน้าของทรงตัว L ({sorted(pr['front'])})")
    ok(pr["top"] == {(0, 0), (1, 0), (2, 0)}, "ภาพฉายจากด้านบนของทรงตัว L")
    ok(pr["side"] == {(0, 0), (0, 1)}, "ภาพฉายด้านข้างของทรงตัว L")
    # ทรงที่หนาขึ้นในแกน y ต้องไม่เปลี่ยนภาพด้านหน้า
    thick = cells + [(0, 1, 0), (1, 1, 0), (2, 1, 0), (0, 1, 1)]
    ok(projections(thick)["front"] == pr["front"], "เพิ่มความหนาในแกน y ไม่ควรเปลี่ยนภาพด้านหน้า")

    # --- SVG ต้องสร้างได้และมี viewBox
    for svg in [lv.svg(), Tackle(2, 600).svg(), d.svg(), f.svg()]:
        ok(svg.startswith("<svg viewBox=") and svg.endswith("</svg>"), "รูปแบบ SVG")

    print("mech.py:", "ผ่านทั้งหมด" if bad == 0 else f"ผิด {bad} รายการ")
    return bad


if __name__ == "__main__":
    import sys
    sys.exit(1 if _selfcheck() else 0)
