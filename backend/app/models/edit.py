from pydantic import BaseModel
from typing import Optional


class CoverConfig(BaseModel):
    enabled: bool = True
    method: str = "sampled_background"  # white | sampled_background | inpaint
    padding: int = 4


class TextConfig(BaseModel):
    value: str = ""
    x: float = 0
    y: float = 0
    font_size: float = 22
    font_id: Optional[str] = None
    font_family: str = "Arial"
    color: str = "#111111"
    bold: bool = False
    italic: bool = False


class EditTargetBBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class SignatureRef(BaseModel):
    image_filename: str  # relative to the document's data dir
    source_signature_id: Optional[str] = None
    width: int = 0
    height: int = 0


class Edit(BaseModel):
    id: str
    page_number: int
    type: str = "text_replacement"
    target_bbox: EditTargetBBox
    cover: CoverConfig = CoverConfig()
    text: TextConfig = TextConfig()
    signature: Optional[SignatureRef] = None


class EditCreate(BaseModel):
    page_number: int
    type: str = "text_replacement"
    target_bbox: EditTargetBBox
    cover: CoverConfig = CoverConfig()
    text: TextConfig = TextConfig()
    signature_id: Optional[str] = None  # library id, when type == "signature"


class EditUpdate(BaseModel):
    target_bbox: Optional[EditTargetBBox] = None
    cover: Optional[CoverConfig] = None
    text: Optional[TextConfig] = None
    signature: Optional[SignatureRef] = None
