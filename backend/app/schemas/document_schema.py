from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    title: str
    status: str
    file_type: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentContentOut(BaseModel):
    title: str
    file_type: str
    total_pages: int
    content_raw: str
