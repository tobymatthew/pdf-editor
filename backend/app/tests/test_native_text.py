import tempfile

import fitz
from fastapi.testclient import TestClient

from app.main import app
from app.modules import document_intake, native_text


def _create_styled_text_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 96),
        "Styled native text",
        fontsize=18,
        fontname="Helvetica-Bold",
        color=(0, 0, 1),
    )
    page.insert_text(
        (72, 140),
        "Italic text",
        fontsize=14,
        fontname="Helvetica-Oblique",
        color=(1, 0, 0),
    )
    doc.save(path)
    doc.close()


def _create_scanned_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(page.rect, color=(0, 0, 0), fill=(1, 1, 1))
    doc.save(path)
    doc.close()


def test_extract_page_text_preserves_bbox_and_style(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_styled_text_pdf(f.name)
        meta = document_intake.create_document(f.name, "styled.pdf")

    result = native_text.extract_page_text(meta.id, 1)

    assert result.coordinate_space == "pdf_points"
    assert result.page_width == 612
    assert result.page_height == 792
    assert len(result.blocks) == 2

    first_block = result.blocks[0]
    assert first_block.text == "Styled native text"
    assert first_block.bbox.x > 70
    assert first_block.bbox.y > 70
    assert first_block.bbox.w > 50
    assert first_block.bbox.h > 10
    assert first_block.style.font_name == "Helvetica-Bold"
    assert first_block.style.font_size == 18
    assert first_block.style.color == "#0000ff"
    assert first_block.style.bold is True
    assert first_block.style.italic is False

    second_block = result.blocks[1]
    assert second_block.style.font_name == "Helvetica-Oblique"
    assert second_block.style.font_size == 14
    assert second_block.style.color == "#ff0000"
    assert second_block.style.bold is False
    assert second_block.style.italic is True


def test_get_native_text_endpoint_returns_cached_blocks(temp_data_dir):
    client = TestClient(app)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_styled_text_pdf(f.name)
        meta = document_intake.create_document(f.name, "styled.pdf")

    response = client.get(f"/documents/{meta.id}/pages/1/native-text")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_number"] == 1
    assert len(payload["blocks"]) == 2
    assert payload["blocks"][0]["style"]["font_name"] == "Helvetica-Bold"
    assert payload["blocks"][0]["style"]["font_size"] == 18
    assert payload["blocks"][0]["style"]["color"] == "#0000ff"

    cached = native_text.get_native_text_result(meta.id, 1)
    assert len(cached.blocks) == 2


def test_extract_page_text_returns_empty_blocks_for_scanned_page(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_scanned_pdf(f.name)
        meta = document_intake.create_document(f.name, "scanned.pdf")

    result = native_text.extract_page_text(meta.id, 1)

    assert result.blocks == []
