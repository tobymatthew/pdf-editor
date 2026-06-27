from typing import Optional

from pydantic import BaseModel

from app.models.ocr import OCRBBox


class NativeTextStyle(BaseModel):
    font_name: str
    font_size: float
    color: Optional[str] = None
    bold: bool = False
    italic: bool = False


class NativeTextBlock(BaseModel):
    id: str
    text: str
    bbox: OCRBBox
    style: NativeTextStyle


class NativeTextPageResult(BaseModel):
    page_number: int
    page_width: float
    page_height: float
    coordinate_space: str = "pdf_points"
    blocks: list[NativeTextBlock]
