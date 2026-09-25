"""sync_status.py — สร้าง/อัปเดต data/_status.csv จากผังหัวข้อทุกวิชา

อ่าน leaf ทั้งหมดจาก data/topics/*.topics.json แล้ว
  - เพิ่มแถวใหม่สำหรับ leaf ที่ยังไม่มีในตาราง
  - คงค่าสถานะเดิมของ leaf ที่มีอยู่แล้วไว้ ไม่เขียนทับ
  - ตรวจจากไฟล์จริงว่ามีบทเรียน/โจทย์แล้วหรือยัง แล้วอัปเดต *_status ให้ตรงความจริง
  - เตือนถ้ามีแถวที่ topic_id ไม่มีอยู่ในผังแล้ว (เช่นหลังเปลี่ยนโครงผัง)

วิธีใช้
    python scripts/sync_status.py           อัปเดตไฟล์
    python scripts/sync_status.py --dry-run ดูว่าจะเปลี่ยนอะไร โดยไม่เขียนไฟล์
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import speclib as S  # noqa: E402

COLUMNS = ["topic_id", "subject", "name_th", "lesson_status", "problem_status",
           "lesson_reviewed", "problem_reviewed", "problem_count", "note"]


def main() -> int:
    S.utf8_stdout()
    ap = argparse.ArgumentParser(description="อัปเดต data/_status.csv จากผังหัวข้อ")
    ap.add_argument("--dry-run", action="store_true", help="แสดงผลโดยไม่เขียนไฟล์")
    ap.add_argument("--data", default=None)
    args = ap.parse_args()

    root = pathlib.Path(args.data) if args.data else S.data_root()
    status_path = root / "_status.csv"

    # 1) leaf ทั้งหมดจากผัง
    leaves: dict[str, dict] = {}
    for p in sorted((root / "topics").glob("*.topics.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for t in d["topics"]:
            if t["kind"] == "leaf":
                leaves[t["id"]] = {"subject": d["subject"], "name_th": t["name_th"]}

    # 2) แถวเดิม
    existing: dict[str, dict] = {}
    if status_path.exists():
        with status_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("topic_id"):
                    existing[row["topic_id"]] = row

    # 3) ของที่มีอยู่จริงในดิสก์
    def has(kind: str, tid: str) -> bool:
        return (root / kind / f"{tid}.json").exists()

    def n_problems(tid: str) -> int:
        p = root / "problems" / f"{tid}.json"
        if not p.exists():
            return 0
        try:
            return len(json.loads(p.read_text(encoding="utf-8")).get("problems") or [])
        except Exception:
            return 0

    rows, added, updated = [], 0, 0
    for tid, info in sorted(leaves.items()):
        old = existing.get(tid)
        cnt = n_problems(tid)
        row = {
            "topic_id": tid,
            "subject": info["subject"],
            "name_th": info["name_th"],
            "lesson_status": "done" if has("lessons", tid) else (old or {}).get("lesson_status") or "todo",
            "problem_status": "done" if cnt else (old or {}).get("problem_status") or "todo",
            "lesson_reviewed": (old or {}).get("lesson_reviewed") or "none",
            "problem_reviewed": (old or {}).get("problem_reviewed") or "none",
            "problem_count": str(cnt),
            "note": (old or {}).get("note") or "",
        }
        # ของหายไปจากดิสก์แต่ตารางบอกว่า done
        if not has("lessons", tid) and row["lesson_status"] == "done":
            row["lesson_status"] = "todo"
            row["lesson_reviewed"] = "none"
        if cnt == 0 and row["problem_status"] == "done":
            row["problem_status"] = "todo"
            row["problem_reviewed"] = "none"
        if old is None:
            added += 1
        elif any(old.get(k, "") != row[k] for k in COLUMNS):
            updated += 1
        rows.append(row)

    orphans = sorted(set(existing) - set(leaves))

    print(f"leaf ในผัง: {len(leaves)}   แถวเดิม: {len(existing)}")
    print(f"เพิ่มใหม่: {added}   อัปเดต: {updated}")
    if orphans:
        print(f"\nแถวที่ topic_id ไม่มีอยู่ในผังแล้ว {len(orphans)} แถว (จะถูกตัดออก):")
        for o in orphans[:20]:
            print("   -", o)
        if len(orphans) > 20:
            print(f"   ... และอีก {len(orphans) - 20}")
        print("  ถ้าเพิ่งเปลี่ยนโครงผัง เป็นเรื่องปกติ")
        print("  แต่ถ้ามีบทเรียนหรือโจทย์ที่ยัง tag รหัสเก่าอยู่ ต้องแก้ก่อน (รัน validate.py)")

    by_subject: dict[str, list] = {}
    for r in rows:
        by_subject.setdefault(r["subject"], []).append(r)
    print("\nความคืบหน้าต่อวิชา")
    for sub, rs in sorted(by_subject.items()):
        ld = sum(1 for r in rs if r["lesson_status"] == "done")
        pd = sum(1 for r in rs if r["problem_status"] == "done")
        pc = sum(int(r["problem_count"]) for r in rs)
        print(f"  {sub:8s} leaf {len(rs):3d} | บทเรียน {ld:3d} | หัวข้อที่มีโจทย์ {pd:3d} | โจทย์รวม {pc:4d} ข้อ")

    if args.dry_run:
        print("\n(--dry-run ไม่ได้เขียนไฟล์)")
        return 0

    with status_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nเขียน {status_path} แล้ว ({len(rows)} แถว)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
