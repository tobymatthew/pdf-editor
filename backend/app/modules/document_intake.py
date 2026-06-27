import os
import json
import uuid
import time
import shutil
from typing import Optional
import fitz  # PyMuPDF

from app import config
from app.models.document import DocumentMetadata, PageInfo
from app.modules import page_analysis, page_crop


def _doc_path(document_id: str) -> str:
    return os.path.join(config.DATA_DIR, document_id)


def _meta_path(document_id: str) -> str:
    return os.path.join(_doc_path(document_id), "metadata.json")


def create_document(file_path: str, original_filename: str) -> DocumentMetadata:
    doc_id = uuid.uuid4().hex[:12]
    doc_dir = _doc_path(doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    pdf_dest = os.path.join(doc_dir, "original.pdf")
    shutil.copy2(file_path, pdf_dest)

    pdf = fitz.open(pdf_dest)
    page_count = pdf.page_count
    page_sizes = []
    for i in range(page_count):
        page = pdf[i]
        rect = page.rect
        page_sizes.append({"width": rect.width, "height": rect.height})
    pdf.close()

    meta = DocumentMetadata(
        id=doc_id,
        original_filename=original_filename,
        page_count=page_count,
        page_sizes=page_sizes,
        render_scale=1.0,
        created_at=time.time(),
    )

    os.makedirs(os.path.join(doc_dir, "pages"), exist_ok=True)
    os.makedirs(os.path.join(doc_dir, "edits"), exist_ok=True)

    with open(_meta_path(doc_id), "w") as f:
        f.write(meta.model_dump_json(indent=2))

    analyses = page_analysis.analyze_pdf(pdf_dest)
    page_analysis.save_page_analysis(doc_id, analyses)

    return meta


def get_document(document_id: str) -> Optional[DocumentMetadata]:
    meta_path = _meta_path(document_id)
    if not os.path.exists(meta_path):
        return None
    with open(meta_path) as f:
        return DocumentMetadata(**json.loads(f.read()))


def validate_document_page(document_id: str, page_number: int) -> DocumentMetadata:
    meta = get_document(document_id)
    if not meta:
        raise ValueError(f"Document {document_id} not found")
    if page_number < 1 or page_number > meta.page_count:
        raise ValueError(f"Page number {page_number} out of range")
    return meta


def list_pages(document_id: str) -> list[PageInfo]:
    meta = get_document(document_id)
    if not meta:
        return []
    analyses_by_page = {
        analysis.page_number: analysis
        for analysis in page_analysis.load_page_analysis(document_id)
    }
    pages = []
    for i, size in enumerate(meta.page_sizes):
        pnum = i + 1
        preview_path = os.path.join(
            _doc_path(document_id), "pages", f"page_{pnum:03d}_preview.png"
        )
        render_path = os.path.join(
            _doc_path(document_id), "pages", f"page_{pnum:03d}.png"
        )
        pages.append(
            PageInfo(
                page_number=pnum,
                width=size["width"],
                height=size["height"],
                preview_path=preview_path if os.path.exists(preview_path) else None,
                render_path=render_path if os.path.exists(render_path) else None,
                has_ocr=os.path.exists(
                    os.path.join(_doc_path(document_id), "edits", f"ocr_page_{pnum:03d}.json")
                ),
                analysis=analyses_by_page.get(pnum),
                crop_box=page_crop.get_crop_box(document_id, pnum),
            )
        )
    return pages


def delete_document(document_id: str) -> bool:
    doc_dir = _doc_path(document_id)
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)
        return True
    return False
