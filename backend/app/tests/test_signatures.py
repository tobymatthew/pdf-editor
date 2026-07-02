import os
import io
import tempfile
from PIL import Image
import fitz

from app.main import app
from fastapi.testclient import TestClient

from app.modules import document_intake, edit_layer, signature_registry, export_pdf
from app.models.edit import EditCreate, EditTargetBBox


def _png_bytes(width: int, height: int, bg=(255, 255, 255, 255), ink=(0, 0, 0, 255)) -> bytes:
    img = Image.new("RGBA", (width, height), bg)
    # draw a diagonal stroke so trimming keeps content
    for x in range(10, width - 10):
        y = height // 2 + (x % 7) - 3
        img.putpixel((x, y), ink)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _create_test_pdf(path: str):
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()


def test_create_list_delete_signature(temp_data_dir):
    data = _png_bytes(120, 40)
    sig = signature_registry.create_signature(data, "My Sig")
    assert sig.name == "My Sig"
    assert sig.width > 0 and sig.height > 0

    listed = signature_registry.list_signatures()
    assert len(listed) == 1
    assert listed[0].id == sig.id

    path = signature_registry.get_signature_path(sig.id)
    assert path and os.path.exists(path)

    assert signature_registry.delete_signature(sig.id) is True
    assert signature_registry.list_signatures() == []
    assert not os.path.exists(path)


def test_signature_white_background_made_transparent(temp_data_dir):
    data = _png_bytes(60, 30, bg=(255, 255, 255, 255), ink=(10, 10, 10, 255))
    sig = signature_registry.create_signature(data, "ink")
    img = Image.open(signature_registry.get_signature_path(sig.id))
    assert img.mode == "RGBA"
    # corner pixel (no ink) should be transparent now
    assert img.getpixel((0, 0))[3] == 0
    signature_registry.delete_signature(sig.id)


def test_signature_off_white_background_made_transparent(temp_data_dir):
    data = _png_bytes(60, 30, bg=(235, 228, 215, 255), ink=(34, 43, 120, 255))
    sig = signature_registry.create_signature(data, "paper")
    img = Image.open(signature_registry.get_signature_path(sig.id))
    assert img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0
    signature_registry.delete_signature(sig.id)


def test_signature_aggressive_cleanup_handles_darker_paper(temp_data_dir):
    data = _png_bytes(60, 30, bg=(212, 200, 178, 255), ink=(25, 35, 115, 255))
    sig = signature_registry.create_signature(data, "paper-dark", aggressive=True)
    img = Image.open(signature_registry.get_signature_path(sig.id))
    assert img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0
    signature_registry.delete_signature(sig.id)


def test_create_signature_edit_copies_image(temp_data_dir):
    sig = signature_registry.create_signature(_png_bytes(100, 40), "sig")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "doc.pdf")
        os.unlink(f.name)

    data = EditCreate(
        page_number=1,
        type="signature",
        target_bbox=EditTargetBBox(x=72, y=72, w=180, h=72),
        signature_id=sig.id,
    )
    edit = edit_layer.create_edit(meta.id, 1, data)
    assert edit.type == "signature"
    assert edit.signature is not None
    assert edit.signature.source_signature_id == sig.id
    placed = os.path.join(
        str(temp_data_dir), meta.id, edit.signature.image_filename
    )
    assert os.path.exists(placed)

    fetched = edit_layer.get_edit(meta.id, 1, edit.id)
    assert fetched is not None
    resolved = edit_layer.resolve_signature_image_path(meta.id, fetched)
    assert resolved and os.path.exists(resolved)

    # deleting the library signature should NOT break the placed one
    signature_registry.delete_signature(sig.id)
    assert edit_layer.resolve_signature_image_path(meta.id, fetched) is not None

    document_intake.delete_document(meta.id)


def test_create_signature_edit_requires_signature_id(temp_data_dir):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "doc.pdf")
        os.unlink(f.name)
    data = EditCreate(
        page_number=1,
        type="signature",
        target_bbox=EditTargetBBox(x=72, y=72, w=180, h=72),
    )
    try:
        edit_layer.create_edit(meta.id, 1, data)
        assert False, "should have raised"
    except ValueError:
        pass
    document_intake.delete_document(meta.id)


def test_api_create_signature_with_name(temp_data_dir):
    client = TestClient(app)
    data = _png_bytes(80, 30)
    res = client.post(
        "/signatures",
        files={"file": ("sig.png", data, "image/png")},
        data={"name": "Api Sig"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Api Sig"
    assert body["width"] > 0

    img_res = client.get(f"/signatures/{body['id']}/image")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"

    listed = client.get("/signatures").json()
    assert any(s["id"] == body["id"] for s in listed)

    del_res = client.delete(f"/signatures/{body['id']}")
    assert del_res.status_code == 200


def test_export_with_signature_overlay(temp_data_dir):
    sig = signature_registry.create_signature(_png_bytes(100, 40), "sig")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        _create_test_pdf(f.name)
        meta = document_intake.create_document(f.name, "doc.pdf")
        os.unlink(f.name)

    edit_layer.create_edit(
        meta.id,
        1,
        EditCreate(
            page_number=1,
            type="signature",
            target_bbox=EditTargetBBox(x=72, y=72, w=180, h=72),
            signature_id=sig.id,
        ),
    )
    out = export_pdf.export_document(meta.id)
    assert os.path.exists(out)
    pdf = fitz.open(out)
    assert pdf.page_count == 1
    page = pdf[0]
    # the signature image should be present as an image on the page
    assert len(page.get_images()) >= 1
    pdf.close()
    signature_registry.delete_signature(sig.id)
    document_intake.delete_document(meta.id)
