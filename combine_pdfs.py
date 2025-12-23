#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Combine single-page PDFs into a single document with cover and table of contents.

This script scans a target directory for PDF files, parses their names to
construct a two-level table of contents, and then merges the PDFs into one
file. It also generates a cover page. The filename pattern is expected to be
similar to:

    01. 章节标题 — 总标题.pdf

The text before the dash is treated as the second-level entry (e.g. chapter),
while the text after the dash forms the first-level (e.g. part or book name).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


DASH_PATTERN = re.compile(r"\s*[—\-]\s*")
LEADING_INDEX = re.compile(r"^(?P<index>\d+)(?:[\.、\s]+)(?P<title>.*)$")

CHINESE_FONT_CANDIDATES = [
    ("MicrosoftYaHei", "msyh.ttc"),
    ("MicrosoftYaHei", "msyh.ttf"),
    ("SimHei", "simhei.ttf"),
    ("SimSun", "simsun.ttc"),
    ("SimSun", "simsun.ttf"),
]

STRUCTURE = [
    ("前言", [
        "0. 前言",
    ]),
    ("一、空气动力学试验及设备基础知识", [
        "1. 讲义内容简介",
        "2. 空气动力学试验的概念",
        "3. 使用本讲义的最佳实践",
        "4. Python 科学计算教程",
        "5. 使用 uv 高效管理 Python 环境",
        "6. Jupyter Notebook 入门教程",
        "7. 工程设计方法论",
    ]),
    ("二、设备设计建设项目工程方法论", [
        "8. 灵敏度",
        "9. 优化",
        "10. 参数驱动的几何体设计与建模",
        "11. 模型：微分方程和仿真",
        "12. 模型：量纲分析",
    ]),
    ("三、空气动力学试验设备立项论证", [
        "13. 本章内容",
        "14. 立项论证",
        "15. 低速风洞Reynolds数范围论证",
        "16. 直流式风洞快速设计",
        "17. 稳定段优化设计",
    ]),
    ("四、空气动力学试验设备可行性研究", [
        "18. 可行性论证",
        "19. 空气动力学试验设备",
        "20. 计算流体力学（CFD）在内流问题中的应用与工作流",
        "21. 风洞大开角性能评估CFD模拟",
    ]),
    ("五、空气动力学试验设备验收过程", [
        "22. 空气动力学试验设备验收",
        "23. 低速风洞流场品质要求与流场校测",
        "24. 基于蒙特卡洛法（MCM）的压力传感器测量不确定度评定",
    ]),
]

DEFAULT_COVER_TITLE = "空气动力学实验设备总体气动设计导论"

BODY_FONT_NAME = "Helvetica"
BOLD_FONT_NAME = "Helvetica-Bold"
_FONTS_INITIALISED = False


def _candidate_font_paths(filename: str) -> Iterable[Path]:
    search_paths = [
        Path(filename),
        Path.cwd() / filename,
        Path(__file__).resolve().parent / filename,
    ]

    windir = os.environ.get("WINDIR")
    if windir:
        search_paths.append(Path(windir) / "Fonts" / filename)
        search_paths.append(Path(windir) / "fonts" / filename)

    local_font_dir = Path.home() / "AppData" / "Local" / \
        "Microsoft" / "Windows" / "Fonts"
    search_paths.append(local_font_dir / filename)

    seen = set()
    for path in search_paths:
        try:
            resolved = path.resolve()
        except FileNotFoundError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            yield resolved


def ensure_chinese_fonts() -> Tuple[str, str]:
    global BODY_FONT_NAME, BOLD_FONT_NAME, _FONTS_INITIALISED
    if _FONTS_INITIALISED:
        return BODY_FONT_NAME, BOLD_FONT_NAME

    for family, filename in CHINESE_FONT_CANDIDATES:
        for font_path in _candidate_font_paths(filename):
            font_name = f"{family}-ReportLab"
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            except Exception:
                continue
            BODY_FONT_NAME = font_name
            BOLD_FONT_NAME = font_name
            _FONTS_INITIALISED = True
            return BODY_FONT_NAME, BOLD_FONT_NAME

    _FONTS_INITIALISED = True
    return BODY_FONT_NAME, BOLD_FONT_NAME


@dataclass
class PdfEntry:
    order: int
    display_title: str
    parent_title: str
    path: Path
    page_count: int = 0
    start_page: int = 0


def parse_filename(path: Path) -> Tuple[int, str, str]:
    """Parse order, display title, and parent title from a filename."""
    stem = path.stem
    parts = DASH_PATTERN.split(stem, maxsplit=1)
    if len(parts) == 2:
        left, right = parts
        parent = right.strip()
    else:
        left, parent = stem, ""
    left = left.strip()

    match = LEADING_INDEX.match(left)
    if match:
        order = int(match.group("index"))
        title_text = match.group("title").strip()
        display = f"{match.group('index')}. {title_text}" if title_text else left
    else:
        order = sys.maxsize
        display = left
    return order, display, parent


def normalise_title(title: str) -> str:
    """Strip leading indices and whitespace for comparison."""

    match = LEADING_INDEX.match(title.strip())
    if match:
        text = match.group("title").strip()
    else:
        text = title.strip()
    return re.sub(r"\s+", "", text)


def generate_cover(path: Path, title: str, subtitle: str | None) -> int:
    """Create a single-page cover and return its page count."""
    body_font, bold_font = ensure_chinese_fonts()
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    c.setFont(bold_font, 32)
    c.drawCentredString(width / 2, height * 0.65, title)

    if subtitle:
        c.setFont(body_font, 16)
        c.drawCentredString(width / 2, height * 0.55, subtitle)

    c.setFont(body_font, 12)
    c.drawCentredString(width / 2, height * 0.45,
                        date.today().strftime("%Y年%m月%d日"))

    c.showPage()
    c.save()
    return len(PdfReader(str(path)).pages)


def _start_toc_page(pdf: canvas.Canvas) -> float:
    width, height = A4
    top_margin = 30 * mm
    body_font, bold_font = ensure_chinese_fonts()
    pdf.setFont(bold_font, 24)
    pdf.drawCentredString(width / 2, height - top_margin + 5 * mm, "目录")
    pdf.setFont(body_font, 12)
    return height - top_margin - 15 * mm


def generate_toc(path: Path, groups: "OrderedDict[str, List[PdfEntry]]") -> int:
    """Create a table-of-contents PDF and return its page count."""
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    left_margin = 25 * mm
    bottom_margin = 25 * mm
    indent = 12 * mm
    line_height = 14

    body_font, bold_font = ensure_chinese_fonts()

    y = _start_toc_page(c)

    for parent, entries in groups.items():
        if parent:
            if y < bottom_margin:
                c.showPage()
                y = _start_toc_page(c)
            c.setFont(bold_font, 12)
            c.drawString(left_margin, y, parent)
            y -= line_height
            c.setFont(body_font, 12)

        for entry in entries:
            if y < bottom_margin:
                c.showPage()
                y = _start_toc_page(c)
            c.drawString(left_margin + indent, y, entry.display_title)
            c.drawRightString(width - left_margin, y, str(entry.start_page))
            y -= line_height

    c.save()
    return len(PdfReader(str(path)).pages)


def assign_start_pages(entries: Iterable[PdfEntry], cover_pages: int, toc_pages: int) -> None:
    """Assign starting page numbers to each entry based on page counts."""
    offset = cover_pages + toc_pages
    running = 0
    for entry in entries:
        entry.start_page = offset + running + 1
        running += entry.page_count


def _add_bookmark(writer: PdfWriter, title: str, page_number: int, parent: Optional[object] = None) -> object:
    if page_number < 0:
        page_number = 0
    try:
        return writer.add_outline_item(title, page_number, parent=parent)
    except AttributeError:
        # 兼容旧版本 PyPDF2
        return writer.addBookmark(title, page_number, parent=parent)


def merge_with_bookmarks(output_path: Path, cover_path: Path, toc_path: Path,
                         entries: List[PdfEntry], groups: "OrderedDict[str, List[PdfEntry]]") -> None:
    writer = PdfWriter()

    def append_pdf(reader: PdfReader) -> None:
        for page in reader.pages:
            writer.add_page(page)

    append_pdf(PdfReader(str(cover_path)))
    append_pdf(PdfReader(str(toc_path)))

    for entry in entries:
        append_pdf(PdfReader(str(entry.path)))

    for parent_title, group_entries in groups.items():
        if not group_entries:
            continue
        parent_page = min(item.start_page for item in group_entries) - 1
        parent_bookmark = _add_bookmark(writer, parent_title, parent_page)
        for item in group_entries:
            _add_bookmark(writer, item.display_title,
                          item.start_page - 1, parent=parent_bookmark)

    with output_path.open("wb") as f:
        writer.write(f)


def build_groups(entries: List[PdfEntry], structure: List[Tuple[str, List[str]]] | None = None) -> "OrderedDict[str, List[PdfEntry]]":
    if structure is None:
        structure = STRUCTURE

    if structure:
        groups: "OrderedDict[str, List[PdfEntry]]" = OrderedDict()
        idx = 0
        total = len(entries)
        for caption, titles in structure:
            group_entries: List[PdfEntry] = []
            for expected_title in titles:
                if idx >= total:
                    raise ValueError("结构中的章节数量超过了实际 PDF 数量")
                entry = entries[idx]
                if normalise_title(entry.display_title) != normalise_title(expected_title):
                    raise ValueError(
                        f"结构期待标题『{expected_title}』，但当前 PDF 为『{entry.display_title}』"
                    )
                group_entries.append(entry)
                idx += 1
            if group_entries:
                groups[caption] = group_entries
        if idx < total:
            groups.setdefault("未匹配章节", []).extend(entries[idx:])
        return groups

    groups: "OrderedDict[str, List[PdfEntry]]" = OrderedDict()
    for entry in entries:
        parent = entry.parent_title or "其他"
        groups.setdefault(parent, []).append(entry)
    return groups


def collect_entries(pdf_dir: Path) -> List[PdfEntry]:
    entries: List[PdfEntry] = []
    for path in sorted(pdf_dir.glob("*.pdf")):
        order, display, parent = parse_filename(path)
        entry = PdfEntry(order=order, display_title=display,
                         parent_title=parent, path=path)
        entries.append(entry)

    # Re-sort to guarantee numerical order, fallback to filename
    entries.sort(key=lambda item: (item.order, item.path.name))

    if not entries:
        raise FileNotFoundError(f"No PDF files found in {pdf_dir}")

    for entry in entries:
        entry.page_count = len(PdfReader(str(entry.path)).pages)
    return entries


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine single-page PDFs into a single document with cover and TOC.")
    parser.add_argument("pdf_dir", type=Path,
                        help="Directory that contains the source PDF files.")
    parser.add_argument("output", type=Path,
                        help="Path for the combined PDF output.")
    parser.add_argument(
        "--title", help="Cover title. Defaults to the first group title.")
    parser.add_argument(
        "--subtitle", help="Optional subtitle for the cover page.")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    pdf_dir: Path = args.pdf_dir
    output_path: Path = args.output

    entries = collect_entries(pdf_dir)

    groups = build_groups(entries, STRUCTURE)

    default_cover = DEFAULT_COVER_TITLE if groups else "合并文档"
    cover_title = args.title or default_cover
    cover_subtitle = args.subtitle

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        cover_path = tmpdir / "cover.pdf"
        toc_path = tmpdir / "toc.pdf"

        cover_pages = generate_cover(cover_path, cover_title, cover_subtitle)

        # Iteratively refine TOC page numbers because the TOC length depends on page numbers themselves.
        toc_pages_assumed = 1
        while True:
            assign_start_pages(entries, cover_pages, toc_pages_assumed)
            actual_toc_pages = generate_toc(toc_path, groups)
            if actual_toc_pages == toc_pages_assumed:
                toc_pages = actual_toc_pages
                break
            toc_pages_assumed = actual_toc_pages

        # Ensure final page numbers are consistent with final TOC page count.
        assign_start_pages(entries, cover_pages, toc_pages)
        generate_toc(toc_path, groups)

        merge_with_bookmarks(output_path, cover_path,
                             toc_path, entries, groups)

    print(f"Combined PDF written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
