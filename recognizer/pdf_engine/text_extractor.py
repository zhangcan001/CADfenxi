from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz


@dataclass
class PdfTextResult:
    text: str
    blocks: list[dict] = field(default_factory=list)
    engine_name: str = "pymupdf"
    engine_version: str = fitz.version[0]


def extract_page_text(pdf_path: Path, page_no: int) -> PdfTextResult:
    document = fitz.open(pdf_path)
    try:
        page_index = page_no - 1
        if page_index < 0 or page_index >= document.page_count:
            raise IndexError("PDF_PAGE_NOT_FOUND")

        page = document.load_page(page_index)
        text = page.get_text("text") or ""
        raw_blocks = page.get_text("blocks") or []
        blocks = [
            {
                "bbox": [float(block[0]), float(block[1]), float(block[2]), float(block[3])],
                "text": block[4],
                "block_no": int(block[5]),
                "block_type": int(block[6]),
            }
            for block in raw_blocks
        ]
        return PdfTextResult(text=text, blocks=blocks)
    finally:
        document.close()
