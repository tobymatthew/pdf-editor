import os
import json
from typing import Optional
import numpy as np
from PIL import Image

from app import config
from app.models.ocr import OCRPageResult, OCRBlock, OCRBBox
from app.modules.document_intake import validate_document_page
from app.modules.page_rendering import get_page_image, get_page_dimensions
from app.modules.coordinates import image_bbox_to_pdf_bbox


OCR_CACHE = {}


def _load_ocr_engine():
    import easyocr
    return easyocr.Reader([config.OCR_LANG], gpu=config.OCR_GPU)


def _get_ocr_engine():
    if "engine" not in OCR_CACHE:
        OCR_CACHE["engine"] = _load_ocr_engine()
    return OCR_CACHE["engine"]


def _ocr_result_path(document_id: str, page_number: int) -> str:
    return os.path.join(config.DATA_DIR, document_id, "edits", f"ocr_page_{page_number:03d}.json")


def ocr_page(document_id: str, page_number: int) -> OCRPageResult:
    validate_document_page(document_id, page_number)
    result_path = _ocr_result_path(document_id, page_number)
    result_dir = os.path.dirname(result_path)
    os.makedirs(result_dir, exist_ok=True)

    cached = get_ocr_result(document_id, page_number)
    if cached:
        return cached

    img_path = get_page_image(document_id, page_number)
    img = Image.open(img_path)
    img_w, img_h = img.size
    page_w, page_h = get_page_dimensions(document_id, page_number)

    engine = _get_ocr_engine()
    img_np = np.array(img.convert("RGB"))
    raw = engine.readtext(img_np)

    blocks = []
    for i, (bbox_pts, text, confidence) in enumerate(raw):
        xs = [p[0] for p in bbox_pts]
        ys = [p[1] for p in bbox_pts]
        x = min(xs)
        y = min(ys)
        w = max(xs) - x
        h = max(ys) - y
        pdf_bbox = image_bbox_to_pdf_bbox(
            OCRBBox(x=x, y=y, w=w, h=h),
            image_width=img_w,
            image_height=img_h,
            page_width=page_w,
            page_height=page_h,
        )

        blocks.append(
            OCRBlock(
                id=f"block_{i:03d}",
                text=text,
                bbox=OCRBBox(
                    x=round(pdf_bbox.x, 2),
                    y=round(pdf_bbox.y, 2),
                    w=round(pdf_bbox.w, 2),
                    h=round(pdf_bbox.h, 2),
                ),
                confidence=round(float(confidence), 3),
            )
        )

    result = OCRPageResult(
        page_number=page_number,
        image_width=img_w,
        image_height=img_h,
        page_width=page_w,
        page_height=page_h,
        blocks=blocks,
    )

    with open(result_path, "w") as f:
        f.write(result.model_dump_json(indent=2))

    return result


def get_ocr_result(document_id: str, page_number: int) -> Optional[OCRPageResult]:
    result_path = _ocr_result_path(document_id, page_number)
    if not os.path.exists(result_path):
        return None
    with open(result_path) as f:
        return OCRPageResult(**json.loads(f.read()))
