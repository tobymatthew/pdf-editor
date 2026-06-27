import os
import json
import uuid
from typing import Optional

from app import config
from app.models.edit import Edit, EditCreate, EditUpdate
from app.modules.document_intake import validate_document_page


def _edits_path(document_id: str, page_number: int) -> str:
    return os.path.join(
        config.DATA_DIR, document_id, "edits", f"edits_page_{page_number:03d}.json"
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
    edit = Edit(
        id=uuid.uuid4().hex[:12],
        page_number=page_number,
        type=data.type,
        target_bbox=data.target_bbox,
        cover=data.cover,
        text=data.text,
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
