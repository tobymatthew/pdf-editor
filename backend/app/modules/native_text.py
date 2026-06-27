import json
import os
from typing import Optional

import fitz

from app import config
from app.models.native_text import NativeTextBlock, NativeTextPageResult, NativeTextStyle
from app.models.ocr import OCRBBox
from app.modules.document_intake import validate_document_page


def _result_path(document_id: str, page_number: int) -> str:
    return os.path.join(
        config.DATA_DIR, document_id, "edits", f"native_text_page_{page_number:03d}.json"
    )


def _document_pdf_path(document_id: str) -> str:
    return os.path.join(config.DATA_DIR, document_id, "original.pdf")


def _normalize_color(color_value: object) -> Optional[str]:
    if not isinstance(color_value, int):
        return None
    return f"#{color_value & 0xFFFFFF:06x}"


def _extract_style(span: dict) -> NativeTextStyle:
    font_name = span.get("font", "") or "Arial"
    font_name_lower = font_name.lower()
    return NativeTextStyle(
        font_name=font_name,
        font_size=round(float(span.get("size", 0.0)), 2),
        color=_normalize_color(span.get("color")),
        bold="bold" in font_name_lower,
        italic="italic" in font_name_lower or "oblique" in font_name_lower,
    )


def extract_page_text(document_id: str, page_number: int) -> NativeTextPageResult:
    meta = validate_document_page(document_id, page_number)
    pdf = fitz.open(_document_pdf_path(document_id))
    try:
        page = pdf[page_number - 1]
        blocks: list[NativeTextBlock] = []
        next_block_index = 0

        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = (span.get("text") or "").strip()
                    if not text:
                        continue

                    x0, y0, x1, y1 = span.get("bbox", (0, 0, 0, 0))
                    blocks.append(
                        NativeTextBlock(
                            id=f"span_{next_block_index:03d}",
                            text=text,
                            bbox=OCRBBox(
                                x=round(float(x0), 2),
                                y=round(float(y0), 2),
                                w=round(float(x1 - x0), 2),
                                h=round(float(y1 - y0), 2),
                            ),
                            style=_extract_style(span),
                        )
                    )
                    next_block_index += 1

        page_size = meta.page_sizes[page_number - 1]
        return NativeTextPageResult(
            page_number=page_number,
            page_width=page_size["width"],
            page_height=page_size["height"],
            blocks=blocks,
        )
    finally:
        pdf.close()


def get_native_text_result(document_id: str, page_number: int) -> NativeTextPageResult:
    result_path = _result_path(document_id, page_number)
    if os.path.exists(result_path):
        with open(result_path) as f:
            return NativeTextPageResult(**json.loads(f.read()))

    result = extract_page_text(document_id, page_number)
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "w") as f:
        f.write(result.model_dump_json(indent=2))
    return result
