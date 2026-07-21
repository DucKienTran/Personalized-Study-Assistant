from __future__ import annotations

from dataclasses import asdict, dataclass, field

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


@dataclass(slots=True)
class DocumentMetadata:
    total_pages: int
    total_chunks: int
    total_characters: int
    estimated_tokens: int
    headings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentAIClassification:
    categories: list[Category]
    language: Language
    purpose: Purpose
    keywords: list[str]

    def to_mongo(self) -> dict:
        return {
            "categories": [c.value for c in self.categories],
            "language": self.language.value,
            "purpose": self.purpose.value,
            "keywords": self.keywords,
        }


@dataclass(slots=True)
class ProcessedDocument:
    raw_text: str
    chunks: list[Document]
    chunk_metadata: list[ChunkMetadata]
    metadata: DocumentMetadata
    classification: DocumentAIClassification | None = None

    def to_dict(self) -> dict:
        assert len(self.chunks) == len(
            self.chunk_metadata
        ), "chunks và chunk_metadata lệch số lượng — bug ở ChunkBuilder/MetadataBuilder"

        return {
            "metadata": asdict(self.metadata),
            "chunks": [
                {
                    "chunk_id": cm.chunk_id,
                    "content": chunk.page_content,
                    "header_path": cm.header_path,
                    "page_start": cm.page_start,
                    "page_end": cm.page_end,
                    "estimated_tokens": cm.estimated_tokens,
                    "character_count": cm.character_count,
                    "previous_chunk": cm.previous_chunk,
                    "next_chunk": cm.next_chunk,
                }
                for chunk, cm in zip(self.chunks, self.chunk_metadata)
            ],
        }
