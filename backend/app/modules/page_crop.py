import json
import os
from typing import Optional

from app import config
from app.models.document import PageCropBox


def _crop_path(document_id: str, page_number: int) -> str:
    return os.path.join(
        config.DATA_DIR, document_id, "edits", f"crop_page_{page_number:03d}.json"
    )


def _clamp_crop(crop: PageCropBox, page_width: float, page_height: float) -> PageCropBox:
    x = min(max(crop.x, 0), page_width - 1)
    y = min(max(crop.y, 0), page_height - 1)
    w = min(max(crop.w, 1), page_width - x)
    h = min(max(crop.h, 1), page_height - y)
    return PageCropBox(x=x, y=y, w=w, h=h)


def get_crop_box(document_id: str, page_number: int) -> Optional[PageCropBox]:
    from app.modules.document_intake import validate_document_page

    validate_document_page(document_id, page_number)
    path = _crop_path(document_id, page_number)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return PageCropBox(**json.loads(f.read()))


def set_crop_box(document_id: str, page_number: int, crop: PageCropBox) -> PageCropBox:
    from app.modules.document_intake import validate_document_page

    meta = validate_document_page(document_id, page_number)
    size = meta.page_sizes[page_number - 1]
    clamped = _clamp_crop(crop, size["width"], size["height"])
    path = _crop_path(document_id, page_number)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(clamped.model_dump_json(indent=2))
    return clamped


def clear_crop_box(document_id: str, page_number: int) -> bool:
    from app.modules.document_intake import validate_document_page

    validate_document_page(document_id, page_number)
    path = _crop_path(document_id, page_number)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
