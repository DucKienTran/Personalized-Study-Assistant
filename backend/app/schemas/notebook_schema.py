from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document_schema import DocumentOut

# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class NotebookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(
        default="#3C6543",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )


class NotebookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(
        default="#3C6543",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )


class AddDocumentsToNotebookRequest(BaseModel):
    document_ids: list[int] = Field(..., description="Danh sách document_id thêm vào notebook")


class ToggleDocumentActiveRequest(BaseModel):
    is_active: bool


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class NotebookDocumentOut(BaseModel):
    """Document trong 1 notebook, kèm is_active dùng cho retrieval (RAG/Summary/Quiz).
    NotebookDocument (ORM) có is_active/added_at trực tiếp + quan hệ .document,
    nên from_attributes tự lồng được document -> DocumentOut."""

    is_active: bool
    added_at: datetime
    document: DocumentOut

    model_config = ConfigDict(from_attributes=True)


class NotebookOut(BaseModel):
    """Dùng cho danh sách notebook (trang /notebooks). document_count không phải
    cột thật trong DB nên service cần tự tính (len(notebook_documents)) rồi
    truyền vào khi khởi tạo, không thể model_validate thẳng từ ORM object."""

    id: int
    title: str
    description: Optional[str] = None
    color: str

    document_count: int = 0

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotebookDetailOut(BaseModel):
    """Dùng cho trang workspace của 1 notebook (sidebar document list)."""

    id: int
    title: str
    description: Optional[str] = None
    color: str

    documents: list[NotebookDocumentOut] = Field(default_factory=list)

    active_document_count: int = 0
    quiz_count: int = 0
    message_count: int = 0
    total_size: int

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
