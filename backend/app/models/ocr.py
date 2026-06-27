from typing import Optional

from pydantic import BaseModel


class OCRBBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class OCRBlock(BaseModel):
    id: str
    text: str
    bbox: OCRBBox
    confidence: float


class OCRPageResult(BaseModel):
    page_number: int
    image_width: int
    image_height: int
    page_width: Optional[float] = None
    page_height: Optional[float] = None
    coordinate_space: str = "pdf_points"
    blocks: list[OCRBlock]
