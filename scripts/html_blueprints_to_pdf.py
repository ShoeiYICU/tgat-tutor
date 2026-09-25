from __future__ import annotations

import csv
import html as html_lib
import re
import sys
from pathlib import Path

from lxml import html
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path(r"C:\Windows\Fonts\tahoma.ttf"), Path(r"C:\Windows\Fonts\tahomabd.ttf")),
        (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("ArchiveRegular", str(regular)))
            pdfmetrics.registerFont(TTFont("ArchiveBold", str(bold)))
            pdfmetrics.registerFont(TTFont("ArchiveJapanese", r"C:\Windows\Fonts\YuGothR.ttc", subfontIndex=0))
            pdfmetrics.registerFont(TTFont("ArchiveKorean", r"C:\Windows\Fonts\malgun.ttf"))
            pdfmetrics.registerFont(TTFont("ArchiveChinese", r"C:\Windows\Fonts\simsun.ttc", subfontIndex=0))
            return "ArchiveRegular", "ArchiveBold"
    raise RuntimeError("No suitable Unicode TrueType font found")


def clean_lines(source: Path) -> tuple[str, list[str]]:
    tree = html.fromstring(source.read_bytes())
    for node in tree.xpath("//script|//style|//nav|//footer|//noscript|//svg"):
        node.drop_tree()
    title = " ".join(tree.xpath("//h1[1]//text()") or tree.xpath("//title/text()") or [source.stem])
    title = re.sub(r"\s+", " ", title).strip()
    blocks: list[str] = []
    for node in tree.xpath("//h1|//h2|//h3|//h4|//p|//li|//th|//td"):
        text = " ".join(node.itertext())
        text = re.sub(r"\s+", " ", text).strip()
        if text and text not in blocks[-1:]:
            blocks.append(text)
    if not blocks:
        text = re.sub(r"\s+", " ", tree.text_content()).strip()
        blocks = [text] if text else []
    return title, blocks


def add_cjk_fallbacks(escaped: str, exam_code: str) -> str:
    if exam_code == "ALEVEL_85":
        font = "ArchiveJapanese"
    elif exam_code == "ALEVEL_86":
        font = "ArchiveKorean"
    elif exam_code == "ALEVEL_87":
        font = "ArchiveChinese"
    else:
        return escaped
    pattern = r"([\u3000-\u9fff\uac00-\ud7af]+)"
    return re.sub(pattern, rf'<font name="{font}">\1</font>', escaped)


def make_pdf(source: Path, output: Path, source_url: str, exam_code: str) -> None:
    regular, bold = register_fonts()
    title, lines = clean_lines(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "ThaiHeading", parent=styles["Heading1"], fontName=bold,
        fontSize=16, leading=21, alignment=TA_CENTER, spaceAfter=8 * mm,
    )
    body = ParagraphStyle(
        "ThaiBody", parent=styles["BodyText"], fontName=regular,
        fontSize=10.5, leading=15, spaceAfter=2.5 * mm, wordWrap="CJK",
    )
    source_style = ParagraphStyle(
        "Source", parent=body, fontSize=8, leading=11, textColor="#555555",
        spaceAfter=5 * mm,
    )
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=title, author="MyTCAS source archive",
    )
    story = [
        Paragraph(html_lib.escape(title), heading),
        Paragraph("แหล่งต้นฉบับ: " + html_lib.escape(source_url), source_style),
    ]
    for line in lines:
        escaped = add_cjk_fallbacks(html_lib.escape(line), exam_code)
        if len(escaped) > 12000:
            chunks = [escaped[i:i + 12000] for i in range(0, len(escaped), 12000)]
        else:
            chunks = [escaped]
        for chunk in chunks:
            story.append(Paragraph(chunk, body))
    doc.build(story)


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: html_blueprints_to_pdf.py MANIFEST TEMP_DIR ROOT", file=sys.stderr)
        return 2
    manifest, temp_dir, root = map(Path, sys.argv[1:])
    made = 0
    with manifest.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row.get("material_type") != "โครงสร้างและตัวอย่างข้อสอบ":
            continue
        local = Path(row["local_path"])
        source = temp_dir / (row["exam_code"] + ".html")
        if not source.exists():
            print(f"missing source: {source}", file=sys.stderr)
            continue
        output = local.with_suffix(".pdf")
        make_pdf(source, output, row["source_url"], row["exam_code"])
        made += 1
    print(f"created={made}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
