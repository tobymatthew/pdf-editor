from pydantic import BaseModel
from typing import Optional


class FontInfo(BaseModel):
    id: str
    family: str
    style: str
    weight: Optional[int] = None
    path: str
