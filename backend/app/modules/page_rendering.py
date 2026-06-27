import os
import fitz
from PIL import Image

from app import config
from app.modules.document_intake import get_document


def _page_path(document_id: str, page_number: int) -> str:
    return os.path.join(config.DATA_DIR, document_id, "pages", f"page_{page_number:03d}.png")


def _preview_path(document_id: str, page_number: int) -> str:
    return os.path.join(
        config.DATA_DIR, document_id, "pages", f"page_{page_number:03d}_preview.png"
    )


def render_page(document_id: str, page_number: int, dpi: int = 200) -> tuple[str, str]:
    meta = get_document(document_id)
    if not meta:
        raise ValueError(f"Document {document_id} not found")
    if page_number < 1 or page_number > meta.page_count:
        raise ValueError(f"Page number {page_number} out of range")

    src = os.path.join(config.DATA_DIR, document_id, "original.pdf")
    pdf = fitz.open(src)
    page = pdf[page_number - 1]

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_path = _page_path(document_id, page_number)
    pix.save(img_path)

    # Preview at lower DPI
    preview_zoom = config.PREVIEW_DPI / 72
    mat_preview = fitz.Matrix(preview_zoom, preview_zoom)
    pix_preview = page.get_pixmap(matrix=mat_preview)
    preview_path = _preview_path(document_id, page_number)
    pix_preview.save(preview_path)

    pdf.close()
    return img_path, preview_path


def get_page_image(document_id: str, page_number: int) -> str:
    path = _page_path(document_id, page_number)
    if not os.path.exists(path):
        render_page(document_id, page_number)
    return path


def get_page_preview(document_id: str, page_number: int) -> str:
    path = _preview_path(document_id, page_number)
    if not os.path.exists(path):
        render_page(document_id, page_number)
    return path


def get_page_dimensions(document_id: str, page_number: int) -> tuple[int, int]:
    meta = get_document(document_id)
    if not meta:
        raise ValueError(f"Document {document_id} not found")
    size = meta.page_sizes[page_number - 1]
    return int(size["width"]), int(size["height"])
