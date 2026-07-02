from pydantic import BaseModel
from typing import Optional


class SignatureInfo(BaseModel):
    id: str
    name: str
    width: int
    height: int
    created_at: float


class SignatureCreateRequest(BaseModel):
    name: Optional[str] = None
