import math
import tempfile

import fitz
import pytest

from app import config
from app.modules import document_intake, ocr, page_rendering
from app.modules.coordinates import image_bbox_to_pdf_bbox, pdf_bbox_to_image_bbox
from app.models.ocr import OCRBBox


def _create_test_pdf(path: str, text: str = "Hello World"):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 100), text, fontsize=20)
    doc.save(path)
    doc.close()


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "documents"
    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    return data_dir


def test_bbox_conversion_is_stable_across_dpi_values():
    page_width = 612
    page_height = 792
    expected_pdf_bbox = OCRBBox(x=72, y=144, w=180, h=36)

    for dpi in (72, 144, 200, 300):
        image_width = page_width * dpi / 72
        image_height = page_height * dpi / 72
        image_bbox = OCRBBox(
            x=expected_pdf_bbox.x * dpi / 72,
            y=expected_pdf_bbox.y * dpi / 72,
            w=expected_pdf_bbox.w * dpi / 72,
            h=expected_pdf_bbox.h * dpi / 72,
        )

        pdf_bbox = image_bbox_to_pdf_bbox(
            image_bbox,
            image_width=image_width,
            image_height=image_height,
            page_width=page_width,
            page_height=page_height,
        )
        round_trip_bbox = pdf_bbox_to_image_bbox(
            pdf_bbox,
            page_width=page_width,
            page_height=page_height,
            image_width=image_width,
            image_height=image_height,
        )

        assert math.isclose(pdf_bbox.x, expected_pdf_bbox.x, abs_tol=1e-6)
        assert math.isclose(pdf_bbox.y, expected_pdf_bbox.y, abs_tol=1e-6)
        assert math.isclose(pdf_bbox.w, expected_pdf_bbox.w, abs_tol=1e-6)
        assert math.isclose(pdf_bbox.h, expected_pdf_bbox.h, abs_tol=1e-6)
        assert math.isclose(round_trip_bbox.x, image_bbox.x, abs_tol=1e-6)
        assert math.isclose(round_trip_bbox.y, image_bbox.y, abs_tol=1e-6)
        assert math.isclose(round_trip_bbox.w, image_bbox.w, abs_tol=1e-6)
        assert math.isclose(round_trip_bbox.h, image_bbox.h, abs_tol=1e-6)


def test_ocr_page_saves_pdf_space_bboxes_with_debug_metadata(temp_data_dir, monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "ocr.pdf")

    page_rendering.render_page(meta.id, 1, dpi=144)
    page_width = meta.page_sizes[0]["width"]
    page_height = meta.page_sizes[0]["height"]
    expected_pdf_bbox = OCRBBox(x=72, y=144, w=180, h=36)
    image_bbox = [
        [expected_pdf_bbox.x * 2, expected_pdf_bbox.y * 2],
        [(expected_pdf_bbox.x + expected_pdf_bbox.w) * 2, expected_pdf_bbox.y * 2],
        [(expected_pdf_bbox.x + expected_pdf_bbox.w) * 2, (expected_pdf_bbox.y + expected_pdf_bbox.h) * 2],
        [expected_pdf_bbox.x * 2, (expected_pdf_bbox.y + expected_pdf_bbox.h) * 2],
    ]

    class FakeReader:
        def readtext(self, image):
            return [(image_bbox, "Hello World", 0.99)]

    monkeypatch.setattr(ocr, "_get_ocr_engine", lambda: FakeReader())

    result = ocr.ocr_page(meta.id, 1)

    assert result.coordinate_space == "pdf_points"
    assert result.page_width == page_width
    assert result.page_height == page_height
    assert result.image_width == 1224
    assert result.image_height == 1584
    assert len(result.blocks) == 1
    assert result.blocks[0].bbox == expected_pdf_bbox
