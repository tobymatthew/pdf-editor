import io
import tempfile

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import config
from app.main import app
from app.modules import document_intake, page_analysis


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "documents"
    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    return data_dir


def _image_bytes(width: int = 900, height: int = 1200) -> bytes:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, width - 40, height - 40), outline="black", width=6)
    draw.text((80, 100), "Scanned page raster content", fill="black")

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _create_native_text_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (50, 100),
        "This page contains meaningful selectable native PDF text.",
        fontsize=18,
    )
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
    page.insert_image(fitz.Rect(36, 120, 576, 720), stream=_image_bytes())
    page.insert_text(
        (50, 80),
        "Hybrid page with a text layer above a significant image.",
        fontsize=18,
    )
    doc.save(path)
    doc.close()


@pytest.mark.parametrize(
    ("factory", "expected_mode"),
    [
        (_create_native_text_pdf, "native_text"),
        (_create_scanned_pdf, "scanned"),
        (_create_hybrid_pdf, "hybrid"),
    ],
)
def test_page_analysis_detects_expected_mode(temp_data_dir, factory, expected_mode):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        factory(f.name)
        meta = document_intake.create_document(f.name, "analysis.pdf")

    analyses = page_analysis.load_page_analysis(meta.id)

    assert len(analyses) == 1
    assert analyses[0].mode == expected_mode
    assert analyses[0].page_number == 1


def test_pages_api_exposes_page_analysis(temp_data_dir):
    client = TestClient(app)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_hybrid_pdf(f.name)
        meta = document_intake.create_document(f.name, "hybrid.pdf")

    response = client.get(f"/documents/{meta.id}/pages")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["analysis"]["mode"] == "hybrid"
    assert payload[0]["analysis"]["has_meaningful_text"] is True
    assert payload[0]["analysis"]["image_area_ratio"] > 0.25
