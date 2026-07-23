# app/services/document/models.py
from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.documents import Document

from app.ai.constants import (
    Category,
    Language,
    Purpose,
)


@dataclass(slots=True)
class ChunkMetadata:
    chunk_id: str
    header_path: list[str]
    page_start: int | None
    page_end: int | None
    estimated_tokens: int
    character_count: int
    previous_chunk: str | None = None
    next_chunk: str | None = None
    embedding: list[float] | None = None


@dataclass(slots=True)
class DocumentMetadata:
    """Chứa các thông số thống kê (dùng đẩy sang MySQL) và outline (dùng lưu Mongo)"""

    total_pages: int
    total_chunks: int
    total_characters: int
    estimated_tokens: int
    outline: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentAIClassification:
    categories: list[Category]
    language: Language
    purpose: Purpose

    def to_mongo(self) -> dict:
        return {
            "categories": [c.value for c in self.categories],
            "language": self.language.value,
            "purpose": self.purpose.value,
        }


@dataclass(slots=True)
class ProcessedDocument:
    raw_text: str
    chunks: list[Document]
    chunk_metadata: list[ChunkMetadata]
    metadata: DocumentMetadata
    classification: DocumentAIClassification | None = None

    def to_mongo_dict(self) -> dict:
        """Trả về dữ liệu tinh gọn để lưu vào MongoDB collection parsed_documents"""
        return {
            "outline": self.metadata.outline,
            "classification": (
                self.classification.to_mongo() if self.classification else None
            ),
        }
