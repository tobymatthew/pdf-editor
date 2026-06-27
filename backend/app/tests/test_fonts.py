import tempfile
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from app.main import app
from app.modules import document_intake, edit_layer, export_pdf, font_registry
from app.models.edit import CoverConfig, EditCreate, EditTargetBBox, TextConfig
from app.models.font import FontInfo


def _create_test_pdf(path: str, text: str = "Hello World") -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=20)
    doc.save(path)
    doc.close()


def test_default_scan_roots_include_app_and_macos_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(font_registry, "APP_FONT_DIR", tmp_path / "fonts")

    roots = font_registry.default_scan_roots()

    assert roots[0] == tmp_path / "fonts"
    assert Path("/System/Library/Fonts") in roots
    assert Path("/Library/Fonts") in roots
    assert Path.home() / "Library/Fonts" in roots


def test_discover_fonts_uses_reader_and_deduplicates(tmp_path):
    root = tmp_path / "fonts"
    nested = root / "nested"
    nested.mkdir(parents=True)

    first = nested / "My Sans Regular.ttf"
    second = root / "My Sans Bold.otf"
    first.write_text("stub")
    second.write_text("stub")

    metadata = {
        first.resolve(): ("My Sans", "Regular", 400),
        second.resolve(): ("My Sans", "Bold", 700),
    }

    fonts = font_registry.discover_fonts(
        roots=[root, root],
        metadata_reader=lambda path: metadata.get(path),
    )

    assert len(fonts) == 2
    assert {font.family for font in fonts} == {"My Sans"}
    assert {font.weight for font in fonts} == {400, 700}
    assert {Path(font.path) for font in fonts} == {first.resolve(), second.resolve()}


def test_fonts_endpoint_returns_registry(monkeypatch):
    client = TestClient(app)
    fonts = [
        FontInfo(
            id="font-1",
            family="Example Sans",
            style="Regular",
            weight=400,
            path="/tmp/example-sans.ttf",
        )
    ]
    monkeypatch.setattr(font_registry, "list_fonts", lambda: fonts)

    response = client.get("/fonts")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == "font-1"
    assert payload[0]["family"] == "Example Sans"
    assert payload[0]["style"] == "Regular"


def test_resolve_font_path_falls_back_to_arial_then_helvetica(tmp_path):
    arial = tmp_path / "Arial.ttf"
    helvetica = tmp_path / "Helvetica.ttf"
    arial.write_text("stub")
    helvetica.write_text("stub")

    fonts = [
        FontInfo(
            id="arial",
            family="Arial",
            style="Regular",
            weight=400,
            path=str(arial),
        ),
        FontInfo(
            id="helvetica",
            family="Helvetica",
            style="Regular",
            weight=400,
            path=str(helvetica),
        ),
    ]

    assert (
        font_registry.resolve_font_path(font_id="missing", font_family="Missing", fonts=fonts)
        == str(arial)
    )

    assert (
        font_registry.resolve_font_path(font_id="missing", font_family="Helvetica", fonts=fonts)
        == str(helvetica)
    )


def test_export_with_selected_font_preserves_searchable_text(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "font-export.pdf")

    edit_layer.create_edit(
        meta.id,
        1,
        EditCreate(
            page_number=1,
            target_bbox=EditTargetBBox(x=10, y=20, w=100, h=30),
            cover=CoverConfig(enabled=True, method="white", padding=2),
            text=TextConfig(
                value="New Text",
                x=10,
                y=20,
                font_size=16,
                font_id="chosen",
                font_family="Chosen",
            ),
        ),
    )

    out_path = export_pdf.export_document(meta.id)

    assert Path(out_path).exists()
    pdf = fitz.open(out_path)
    try:
        assert "New Text" in pdf[0].get_text().replace("\xa0", " ")
    finally:
        pdf.close()
