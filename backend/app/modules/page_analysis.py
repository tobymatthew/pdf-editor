import json
import os

import fitz

from app import config
from app.models.document import PageAnalysis

MIN_MEANINGFUL_WORDS = 3
MIN_MEANINGFUL_CHARACTERS = 20
MIN_SIGNIFICANT_IMAGE_AREA_RATIO = 0.25


def _doc_path(document_id: str) -> str:
    return os.path.join(config.DATA_DIR, document_id)


def _analysis_path(document_id: str) -> str:
    return os.path.join(_doc_path(document_id), "page_analysis.json")


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


def _extract_text_metrics(page: fitz.Page) -> tuple[int, int]:
    words = page.get_text("words")
    text_word_count = 0
    text_character_count = 0

    for word in words:
        text = word[4].strip()
        if not text:
            continue
        text_word_count += 1
        text_character_count += sum(1 for ch in text if not ch.isspace())

    return text_word_count, text_character_count


def _extract_image_metrics(page: fitz.Page) -> tuple[int, float]:
    page_area = max(page.rect.width * page.rect.height, 1.0)
    image_area = 0.0
    image_count = 0
    seen_xrefs: set[int] = set()

    for image in page.get_images(full=True):
        xref = image[0]
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)

        rects = page.get_image_rects(xref)
        if not rects:
            continue

        image_count += len(rects)
        for rect in rects:
            image_area += max(rect.width, 0.0) * max(rect.height, 0.0)

    return image_count, _clamp_ratio(image_area / page_area)


def classify_page(page: fitz.Page, page_number: int) -> PageAnalysis:
    text_word_count, text_character_count = _extract_text_metrics(page)
    image_count, image_area_ratio = _extract_image_metrics(page)

    has_meaningful_text = (
        text_word_count >= MIN_MEANINGFUL_WORDS
        or text_character_count >= MIN_MEANINGFUL_CHARACTERS
    )
    has_significant_image_content = (
        image_count > 0 and image_area_ratio >= MIN_SIGNIFICANT_IMAGE_AREA_RATIO
    )

    if has_meaningful_text and has_significant_image_content:
        mode = "hybrid"
    elif has_meaningful_text:
        mode = "native_text"
    else:
        mode = "scanned"

    return PageAnalysis(
        page_number=page_number,
        mode=mode,
        has_meaningful_text=has_meaningful_text,
        text_word_count=text_word_count,
        text_character_count=text_character_count,
        image_count=image_count,
        image_area_ratio=image_area_ratio,
    )


def analyze_pdf(pdf_path: str) -> list[PageAnalysis]:
    pdf = fitz.open(pdf_path)
    try:
        return [classify_page(pdf[i], i + 1) for i in range(pdf.page_count)]
    finally:
        pdf.close()


def save_page_analysis(document_id: str, analyses: list[PageAnalysis]) -> None:
    with open(_analysis_path(document_id), "w") as f:
        json.dump([analysis.model_dump() for analysis in analyses], f, indent=2)


def load_page_analysis(document_id: str) -> list[PageAnalysis]:
    path = _analysis_path(document_id)
    if not os.path.exists(path):
        return []

    with open(path) as f:
        raw = json.load(f)

    return [PageAnalysis(**item) for item in raw]
