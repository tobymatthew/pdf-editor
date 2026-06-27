import sys
import tempfile
import types

import fitz
import pytest

from app import config
from app.modules import document_intake, edit_layer, ocr
from app.models.edit import CoverConfig, EditCreate, EditTargetBBox, EditUpdate, TextConfig


def _create_test_pdf(path: str, text: str = "Hello World"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=20)
    doc.save(path)
    doc.close()


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "documents"
    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    return data_dir


def test_edit_validation_and_configured_data_dir(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "test.pdf")

    edit = edit_layer.create_edit(
        meta.id,
        1,
        EditCreate(
            page_number=1,
            target_bbox=EditTargetBBox(x=10, y=20, w=100, h=30),
            cover=CoverConfig(enabled=True, method="white", padding=2),
            text=TextConfig(value="New Text", x=10, y=20, font_size=16),
        ),
    )
    edit_path = temp_data_dir / meta.id / "edits" / "edits_page_001.json"
    assert edit_path.exists()

    edit = edit_layer.update_edit(
        meta.id,
        1,
        edit.id,
        EditUpdate(text=TextConfig(value="Updated", x=12, y=24, font_size=18)),
    )
    assert edit is not None
    assert edit.text.value == "Updated"

    assert edit_layer.list_edits(meta.id, 1)[0].id == edit.id
    assert edit_layer.delete_edit(meta.id, 1, edit.id)
    assert edit_layer.list_edits(meta.id, 1) == []

    first = edit_layer.create_edit(
        meta.id,
        1,
        EditCreate(
            page_number=1,
            target_bbox=EditTargetBBox(x=10, y=20, w=100, h=30),
            cover=CoverConfig(enabled=True, method="white", padding=2),
            text=TextConfig(value="First", x=10, y=20, font_size=16),
        ),
    )
    second = edit_layer.create_edit(
        meta.id,
        1,
        EditCreate(
            page_number=1,
            target_bbox=EditTargetBBox(x=40, y=50, w=80, h=20),
            cover=CoverConfig(enabled=True, method="white", padding=2),
            text=TextConfig(value="Second", x=40, y=50, font_size=16),
        ),
    )
    restored = edit_layer.replace_edits(meta.id, 1, [first])
    assert [item.id for item in restored] == [first.id]
    assert [item.id for item in edit_layer.list_edits(meta.id, 1)] == [first.id]
    assert second.id not in [item.id for item in edit_layer.list_edits(meta.id, 1)]

    with pytest.raises(ValueError, match="Document missing not found"):
        edit_layer.list_edits("missing", 1)

    with pytest.raises(ValueError, match="Page number 2 out of range"):
        edit_layer.create_edit(
            meta.id,
            2,
            EditCreate(
                page_number=2,
                target_bbox=EditTargetBBox(x=10, y=20, w=100, h=30),
                cover=CoverConfig(enabled=True, method="white", padding=2),
                text=TextConfig(value="New Text", x=10, y=20, font_size=16),
            ),
        )

    with pytest.raises(ValueError, match="Page number 2 out of range"):
        edit_layer.update_edit(
            meta.id,
            2,
            "edit-id",
            EditUpdate(text=TextConfig(value="Updated", x=12, y=24, font_size=18)),
        )

    with pytest.raises(ValueError, match="Page number 2 out of range"):
        edit_layer.delete_edit(meta.id, 2, "edit-id")


def test_ocr_engine_uses_backend_config_and_configured_data_dir(temp_data_dir, monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "ocr.pdf")

    captured = {}

    def fake_reader(langs, gpu=False):
        captured["langs"] = langs
        captured["gpu"] = gpu

        class FakeReader:
            def readtext(self, image):
                return []

        return FakeReader()

    monkeypatch.setattr(config, "OCR_LANG", "de")
    monkeypatch.setattr(config, "OCR_GPU", True)
    monkeypatch.setitem(sys.modules, "easyocr", types.SimpleNamespace(Reader=fake_reader))
    ocr.OCR_CACHE.clear()

    engine = ocr._get_ocr_engine()
    assert captured == {"langs": ["de"], "gpu": True}
    assert engine is not None

    result = ocr.ocr_page(meta.id, 1)
    assert result.page_number == 1
    assert (temp_data_dir / meta.id / "edits" / "ocr_page_001.json").exists()
