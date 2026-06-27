import io
import os
import tempfile

import fitz
from PIL import Image, ImageDraw

from app import config
from app.models.edit import CoverConfig, EditCreate, EditTargetBBox, TextConfig
from app.models.ocr import OCRBBox, OCRBlock, OCRPageResult
from app.modules import document_intake, edit_layer, export_pdf


def _image_bytes(width: int = 900, height: int = 1200) -> bytes:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, width - 40, height - 40), outline="black", width=6)
    draw.text((80, 100), "Scanned raster words", fill="black")

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _create_native_text_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 100), "Hello World Native Text", fontsize=20)
    doc.save(path)
    doc.close()


def _create_scanned_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=_image_bytes())
    doc.save(path)
    doc.close()


def _create_hybrid_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(36, 160, 576, 720), stream=_image_bytes())
    page.insert_text((50, 100), "Hybrid Native Text", fontsize=20)
    doc.save(path)
    doc.close()


def _create_replacement_edit(document_id: str, text: str) -> None:
    edit_layer.create_edit(
        document_id,
        1,
        EditCreate(
            page_number=1,
            target_bbox=EditTargetBBox(x=45, y=72, w=260, h=40),
            cover=CoverConfig(enabled=True, method="white", padding=2),
            text=TextConfig(value=text, x=50, y=78, font_size=20),
        ),
    )


def _open_exported_pdf(document_id: str) -> fitz.Document:
    return fitz.open(export_pdf.export_document(document_id))


def _normalized_text(page: fitz.Page) -> str:
    return page.get_text().replace("\xa0", " ")


def test_native_text_export_preserves_pdf_page_without_full_page_raster(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_native_text_pdf(f.name)
        meta = document_intake.create_document(f.name, "native.pdf")

    _create_replacement_edit(meta.id, "Replacement Text")

    pdf = _open_exported_pdf(meta.id)
    try:
        page = pdf[0]
        text = _normalized_text(page)
        assert "Replacement Text" in text
        assert "Hello World Native Text" not in text
        assert len(page.get_images(full=True)) == 0
    finally:
        pdf.close()


def test_scanned_export_uses_image_background_and_searchable_edit_text(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_scanned_pdf(f.name)
        meta = document_intake.create_document(f.name, "scanned.pdf")

    _create_replacement_edit(meta.id, "Typed Fix")

    pdf = _open_exported_pdf(meta.id)
    try:
        page = pdf[0]
        assert "Typed Fix" in _normalized_text(page)
        assert len(page.get_images(full=True)) == 1
    finally:
        pdf.close()


def test_scanned_export_adds_cached_ocr_as_invisible_searchable_text(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_scanned_pdf(f.name)
        meta = document_intake.create_document(f.name, "scanned-ocr.pdf")

    result = OCRPageResult(
        page_number=1,
        image_width=612,
        image_height=792,
        page_width=612,
        page_height=792,
        blocks=[
            OCRBlock(
                id="ocr_001",
                text="Invisible OCR Words",
                bbox=OCRBBox(x=60, y=90, w=180, h=30),
                confidence=0.99,
            )
        ],
    )
    ocr_path = os.path.join(config.DATA_DIR, meta.id, "edits", "ocr_page_001.json")
    with open(ocr_path, "w") as f:
        f.write(result.model_dump_json(indent=2))

    pdf = _open_exported_pdf(meta.id)
    try:
        assert "Invisible OCR Words" in pdf[0].get_text()
    finally:
        pdf.close()


def test_hybrid_export_preserves_existing_image_and_adds_replacement_text(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_hybrid_pdf(f.name)
        meta = document_intake.create_document(f.name, "hybrid.pdf")

    _create_replacement_edit(meta.id, "Hybrid Replacement")

    pdf = _open_exported_pdf(meta.id)
    try:
        page = pdf[0]
        text = _normalized_text(page)
        assert "Hybrid Replacement" in text
        assert "Hybrid Native Text" not in text
        assert len(page.get_images(full=True)) == 1
    finally:
        pdf.close()
