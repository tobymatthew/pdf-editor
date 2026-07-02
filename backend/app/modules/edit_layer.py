import os
import json
import uuid
import shutil
from typing import Optional

from app import config
from app.models.edit import Edit, EditCreate, EditUpdate, SignatureRef
from app.modules import signature_registry
from app.modules.document_intake import validate_document_page


def _edits_path(document_id: str, page_number: int) -> str:
    return os.path.join(
        config.DATA_DIR, document_id, "edits", f"edits_page_{page_number:03d}.json"
    )


def _doc_dir(document_id: str) -> str:
    return os.path.join(config.DATA_DIR, document_id)


def _signature_image_rel(edit_id: str) -> str:
    return os.path.join("signature_images", f"{edit_id}.png")


def _resolve_signature_edit(document_id: str, edit_id: str, signature_id: str) -> Optional[SignatureRef]:
    meta = signature_registry.get_signature_meta(signature_id)
    src_path = signature_registry.get_signature_path(signature_id)
    if not meta or not src_path:
        return None
    dest_dir = os.path.join(_doc_dir(document_id), "signature_images")
    os.makedirs(dest_dir, exist_ok=True)
    dest_rel = _signature_image_rel(edit_id)
    shutil.copy2(src_path, os.path.join(_doc_dir(document_id), dest_rel))
    return SignatureRef(
        image_filename=dest_rel,
        source_signature_id=signature_id,
        width=meta.width,
        height=meta.height,
    )


def _load_edits(document_id: str, page_number: int) -> list[dict]:
    path = _edits_path(document_id, page_number)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.loads(f.read())


def _save_edits(document_id: str, page_number: int, edits: list[dict]):
    path = _edits_path(document_id, page_number)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(edits, f, indent=2)


def replace_edits(document_id: str, page_number: int, edits: list[Edit]) -> list[Edit]:
    validate_document_page(document_id, page_number)
    normalized = []
    for edit in edits:
        data = edit.model_dump()
        data["page_number"] = page_number
        normalized.append(data)
    _save_edits(document_id, page_number, normalized)
    return [Edit(**edit) for edit in normalized]


def create_edit(document_id: str, page_number: int, data: EditCreate) -> Edit:
    validate_document_page(document_id, page_number)
    edit_id = uuid.uuid4().hex[:12]
    signature_ref = None
    if data.type == "signature":
        if not data.signature_id:
            raise ValueError("signature_id is required for signature edits")
        signature_ref = _resolve_signature_edit(
            document_id, edit_id, data.signature_id
        )
        if not signature_ref:
            raise ValueError(f"Signature {data.signature_id} not found")
    edit = Edit(
        id=edit_id,
        page_number=page_number,
        type=data.type,
        target_bbox=data.target_bbox,
        cover=data.cover,
        text=data.text,
        signature=signature_ref,
    )
    edits = _load_edits(document_id, page_number)
    edits.append(edit.model_dump())
    _save_edits(document_id, page_number, edits)
    return edit


def update_edit(document_id: str, page_number: int, edit_id: str, changes: EditUpdate) -> Optional[Edit]:
    validate_document_page(document_id, page_number)
    edits = _load_edits(document_id, page_number)
    for i, e in enumerate(edits):
        if e["id"] == edit_id:
            if changes.target_bbox is not None:
                e["target_bbox"] = changes.target_bbox.model_dump()
            if changes.cover is not None:
                e["cover"] = changes.cover.model_dump()
            if changes.text is not None:
                e["text"] = changes.text.model_dump()
            edits[i] = e
            _save_edits(document_id, page_number, edits)
            return Edit(**e)
    return None


def delete_edit(document_id: str, page_number: int, edit_id: str) -> bool:
    validate_document_page(document_id, page_number)
    edits = _load_edits(document_id, page_number)
    filtered = [e for e in edits if e["id"] != edit_id]
    if len(filtered) == len(edits):
        return False
    _save_edits(document_id, page_number, filtered)
    return True


def list_edits(document_id: str, page_number: int) -> list[Edit]:
    validate_document_page(document_id, page_number)
    return [Edit(**e) for e in _load_edits(document_id, page_number)]


def get_edit(document_id: str, page_number: int, edit_id: str) -> Optional[Edit]:
    validate_document_page(document_id, page_number)
    for entry in _load_edits(document_id, page_number):
        if entry["id"] == edit_id:
            return Edit(**entry)
    return None


def resolve_signature_image_path(document_id: str, edit: Edit) -> Optional[str]:
    if not edit.signature:
        return None
    path = os.path.join(_doc_dir(document_id), edit.signature.image_filename)
    return path if os.path.exists(path) else None
