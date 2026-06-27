import os
import tempfile
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models.document import DocumentMetadata, PageCropBox, PageInfo
from app.models.font import FontInfo
from app.models.edit import Edit, EditCreate, EditUpdate
from app.models.native_text import NativeTextPageResult
from app.models.ocr import OCRPageResult
from app.modules import (
    document_intake,
    page_rendering,
    ocr,
    edit_layer,
    export_pdf,
    native_text,
    font_registry,
    page_crop,
)

app = FastAPI(title="Scan-Aware PDF Editor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "pdf_editor_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/fonts", response_model=list[FontInfo])
async def list_fonts() -> list[FontInfo]:
    return font_registry.list_fonts()


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)) -> DocumentMetadata:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    tmp = os.path.join(UPLOAD_DIR, file.filename)
    with open(tmp, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        meta = document_intake.create_document(tmp, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.remove(tmp)

    return meta


@app.get("/documents/{document_id}")
async def get_document(document_id: str) -> DocumentMetadata:
    meta = document_intake.get_document(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found")
    return meta


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    ok = document_intake.delete_document(document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


@app.get("/documents/{document_id}/pages")
async def list_pages(document_id: str) -> list[PageInfo]:
    pages = document_intake.list_pages(document_id)
    if not pages:
        raise HTTPException(status_code=404, detail="Document not found")
    return pages


@app.get("/documents/{document_id}/pages/{page_number}/crop")
async def get_crop(document_id: str, page_number: int) -> Optional[PageCropBox]:
    try:
        return page_crop.get_crop_box(document_id, page_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/documents/{document_id}/pages/{page_number}/crop")
async def set_crop(document_id: str, page_number: int, data: PageCropBox) -> PageCropBox:
    try:
        return page_crop.set_crop_box(document_id, page_number, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/documents/{document_id}/pages/{page_number}/crop")
async def clear_crop(document_id: str, page_number: int):
    try:
        return {"ok": page_crop.clear_crop_box(document_id, page_number)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/documents/{document_id}/pages/{page_number}/render")
async def render_page(document_id: str, page_number: int):
    try:
        _, preview = page_rendering.render_page(document_id, page_number)
        return {"preview_path": preview}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/documents/{document_id}/pages/{page_number}/image")
async def get_page_image(document_id: str, page_number: int, preview: bool = True):
    try:
        if preview:
            path = page_rendering.get_page_preview(document_id, page_number)
        else:
            path = page_rendering.get_page_image(document_id, page_number)
        return FileResponse(path, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/documents/{document_id}/pages/{page_number}/ocr")
async def run_ocr(document_id: str, page_number: int) -> OCRPageResult:
    try:
        result = ocr.ocr_page(document_id, page_number)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/documents/{document_id}/pages/{page_number}/ocr")
async def get_ocr(document_id: str, page_number: int) -> OCRPageResult:
    result = ocr.get_ocr_result(document_id, page_number)
    if not result:
        raise HTTPException(status_code=404, detail="OCR not run yet")
    return result


@app.get("/documents/{document_id}/pages/{page_number}/native-text")
async def get_native_text(document_id: str, page_number: int) -> NativeTextPageResult:
    try:
        return native_text.get_native_text_result(document_id, page_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/documents/{document_id}/pages/{page_number}/edits")
async def list_edits(document_id: str, page_number: int) -> list[Edit]:
    try:
        return edit_layer.list_edits(document_id, page_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/documents/{document_id}/pages/{page_number}/edits")
async def create_edit(document_id: str, page_number: int, data: EditCreate) -> Edit:
    try:
        return edit_layer.create_edit(document_id, page_number, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/documents/{document_id}/pages/{page_number}/edits")
async def replace_edits(document_id: str, page_number: int, data: list[Edit]) -> list[Edit]:
    try:
        return edit_layer.replace_edits(document_id, page_number, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.patch("/documents/{document_id}/pages/{page_number}/edits/{edit_id}")
async def update_edit(
    document_id: str, page_number: int, edit_id: str, data: EditUpdate
) -> Edit:
    try:
        edit = edit_layer.update_edit(document_id, page_number, edit_id, data)
        if not edit:
            raise HTTPException(status_code=404, detail="Edit not found")
        return edit
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/documents/{document_id}/pages/{page_number}/edits/{edit_id}")
async def delete_edit(document_id: str, page_number: int, edit_id: str):
    try:
        ok = edit_layer.delete_edit(document_id, page_number, edit_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Edit not found")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/documents/{document_id}/export")
async def export_document(document_id: str):
    try:
        pdf_path = export_pdf.export_document(document_id)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="edited.pdf",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
