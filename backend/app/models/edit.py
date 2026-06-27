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


class Edit(BaseModel):
    id: str
    page_number: int
    type: str = "text_replacement"
    target_bbox: EditTargetBBox
    cover: CoverConfig = CoverConfig()
    text: TextConfig = TextConfig()


class EditCreate(BaseModel):
    page_number: int
    type: str = "text_replacement"
    target_bbox: EditTargetBBox
    cover: CoverConfig = CoverConfig()
    text: TextConfig = TextConfig()


class EditUpdate(BaseModel):
    target_bbox: Optional[EditTargetBBox] = None
    cover: Optional[CoverConfig] = None
    text: Optional[TextConfig] = None
