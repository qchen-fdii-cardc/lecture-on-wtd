from __future__ import annotations

import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "缺少 pypdf 库，请先运行 `uv add pypdf` 或 `pip install pypdf` 后再重试。"
    ) from exc


def extract_pdf_assets(pdf_path: Path, output_dir: Path) -> None:
    if not pdf_path.exists():
        raise FileNotFoundError(f"未找到 PDF 文件: {pdf_path}")

    reader = PdfReader(str(pdf_path))

    output_dir.mkdir(parents=True, exist_ok=True)
    text_dir = output_dir / "text"
    images_dir = output_dir / "images"
    text_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)

    text_parts: list[str] = []
    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        text_parts.append(f"--- 第 {page_index} 页 ---\n{page_text}\n")

        images = getattr(page, "images", [])
        if images:
            for image_index, image in enumerate(images, start=1):
                image_extension = image.name.split(
                    ".")[-1] if "." in image.name else "bin"
                image_filename = (
                    f"page{page_index:03d}_img{image_index:02d}.{image_extension}"
                )
                image_path = images_dir / image_filename
                with open(image_path, "wb") as image_file:
                    image_file.write(image.data)

    text_output = text_dir / f"{pdf_path.stem}.txt"
    text_output.write_text("\n".join(text_parts), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        pdf_file = Path(sys.argv[1])
        output_folder = Path(sys.argv[2])
    else:
        project_root = Path(__file__).resolve().parent
        pdf_file = project_root / "materials" / "1000-4750(2013)03-0424-07.pdf"
        output_folder = project_root / "materials" / \
            "1000-4750(2013)03-0424-07_assets"

    extract_pdf_assets(pdf_file, output_folder)
    print(f"文本与图片已导出至: {output_folder}")
