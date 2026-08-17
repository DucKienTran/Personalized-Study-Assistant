from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PastedTextDocumentCreate(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty.")
        if len(title) > 255:
            raise ValueError("Title must contain at most 255 characters.")
        return title

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content must not be empty.")
        return value


class DocumentOut(BaseModel):
    id: int
    title: str
    status: str
    file_type: Optional[str] = None
    file_size: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentOutlineItem(BaseModel):
    text: str
    level: int
    anchor: str


class DocumentContentOut(BaseModel):
    title: str
    file_type: str
    total_pages: int
    content_raw: str
    outline: list[DocumentOutlineItem] = Field(default_factory=list)


class FileUrlOut(BaseModel):
    url: str
