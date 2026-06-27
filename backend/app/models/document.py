from pydantic import BaseModel
from typing import Literal, Optional


PageLiteracyMode = Literal["native_text", "scanned", "hybrid"]


class DocumentMetadata(BaseModel):
    id: str
    original_filename: str
    page_count: int
    page_sizes: list[dict]  # [{width, height}]
    render_scale: float
    created_at: float


class PageAnalysis(BaseModel):
    page_number: int
    mode: PageLiteracyMode
    has_meaningful_text: bool
    text_word_count: int
    text_character_count: int
    image_count: int
    image_area_ratio: float


class PageCropBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class PageInfo(BaseModel):
    page_number: int
    width: float
    height: float
    preview_path: Optional[str] = None
    render_path: Optional[str] = None
    has_ocr: bool = False
    analysis: Optional[PageAnalysis] = None
    crop_box: Optional[PageCropBox] = None
