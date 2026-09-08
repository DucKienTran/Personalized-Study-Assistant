# app/services/rag/retrieval_models.py
from dataclasses import dataclass, field


@dataclass(slots=True)
class RetrievalResult:
    chunk_id: str
    document_id: int
    text: str
    vector_score: float | None = None
    bm25_score: float | None = None
    retrieval_score: float | None = None  # RRF fusion score
    rerank_score: float | None = None
    rank: int | None = None
    page_start: int = 0
    page_end: int = 0
    header_path: list[str] = field(default_factory=list)
    previous_chunk: str | None = None
    next_chunk: str | None = None
    context_role: str = "reranked"
    neighbor_of: str | None = None
    document_title: str | None = None
    beir_corpus_id: str | None = None


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
