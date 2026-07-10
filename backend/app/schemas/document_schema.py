# schemas/document.py (file mới)
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentOut(BaseModel):
    id: int
    title: str
    status: str
    file_type: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # pydantic v2, model này đọc trực tiếp từ ORM object
