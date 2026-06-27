import os
import tempfile
import json
from PIL import Image
import fitz

from app.modules import document_intake, page_rendering, edit_layer
from app.models.edit import EditCreate, EditTargetBBox, CoverConfig, TextConfig


def _create_test_pdf(path: str, text: str = "Hello World"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=20)
    doc.save(path)
    doc.close()


def test_create_document():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "test.pdf")
        assert meta.page_count == 1
        assert meta.original_filename == "test.pdf"
        assert len(meta.page_sizes) == 1
        assert meta.page_sizes[0]["width"] > 0
        os.unlink(f.name)
    document_intake.delete_document(meta.id)


def test_render_page():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "test.pdf")
        img_path, preview_path = page_rendering.render_page(meta.id, 1)
        assert os.path.exists(img_path)
        assert os.path.exists(preview_path)
        img = Image.open(img_path)
        assert img.width > 0
        assert img.height > 0
        os.unlink(f.name)
    document_intake.delete_document(meta.id)


def test_create_and_list_edits():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "test.pdf")
        data = EditCreate(
            page_number=1,
            target_bbox=EditTargetBBox(x=10, y=20, w=100, h=30),
            cover=CoverConfig(enabled=True, method="white", padding=2),
            text=TextConfig(value="New Text", x=10, y=20, font_size=16),
        )
        edit = edit_layer.create_edit(meta.id, 1, data)
        assert edit.id is not None
        assert edit.text.value == "New Text"

        edits = edit_layer.list_edits(meta.id, 1)
        assert len(edits) == 1
        assert edits[0].id == edit.id

        ok = edit_layer.delete_edit(meta.id, 1, edit.id)
        assert ok
        assert len(edit_layer.list_edits(meta.id, 1)) == 0
        os.unlink(f.name)
    document_intake.delete_document(meta.id)


def test_multi_page():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((50, 100), f"Page {i+1}", fontsize=20)
        doc.save(f.name)
        doc.close()

        meta = document_intake.create_document(f.name, "multi.pdf")
        assert meta.page_count == 3
        assert len(meta.page_sizes) == 3
        os.unlink(f.name)
    document_intake.delete_document(meta.id)
