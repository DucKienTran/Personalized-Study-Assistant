# app/services/ai/retrieval_models.py
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RetrievalResult:
    chunk_id: str
    document_id: int
    text: str
    vector_score: float | None = None
    bm25_score: float | None = None
    page_start: int = 0
    page_end: int = 0
    header_path: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CitationSource:
    index: int  # Ví dụ: 1 cho [1]
    document_id: int
    document_title: str
    page_start: int
    page_end: int
    header_path: list[str]
    chunk_id: str
    snippet: str | None = None


@dataclass(slots=True)
class RAGResponse:
    answer: str
    sources: list[CitationSource]
