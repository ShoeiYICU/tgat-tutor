"""build_content.py — รันไฟล์เนื้อหาทั้งหมดใน content/ เพื่อสร้าง data/lessons และ data/problems

วิธีใช้
    python scripts/build_content.py              รันทุกไฟล์
    python scripts/build_content.py tgat3        รันเฉพาะไฟล์ที่ path มีคำนี้

ลำดับงานปกติหลังแก้เนื้อหา
    python scripts/build_content.py
    python scripts/validate.py
    python scripts/build_site.py
"""

import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    files = sorted(p for p in (ROOT / "content").rglob("*.py")
                   if not p.name.startswith("_") and only in p.as_posix())
    for f in files:
        print(f.relative_to(ROOT).as_posix())
        runpy.run_path(str(f), run_name="__main__")
    print(f"รันแล้ว {len(files)} ไฟล์")
    return 0


if __name__ == "__main__":
    sys.exit(main())
