from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Câu hỏi của người dùng",
    )

    notebook_id: int = Field(
        ...,
        description="Notebook dùng làm phạm vi tìm kiếm",
    )

    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="Số lượng chunk retrieval",
    )

    chat_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Lịch sử hội thoại",
    )

    conversation_id: Optional[int] = Field(
        default=None,
        description="Conversation hiện tại",
    )


class CitationSourceSchema(BaseModel):
    index: int
    document_id: int
    document_title: str
    page_start: int
    page_end: int
    header_path: list[str]
    chunk_id: str
    snippet: Optional[str] = None


class RAGMetadataSchema(BaseModel):
    original_query: str
    rewritten_query: Optional[str] = None
    notebook_id: int
    active_document_count: int
    active_document_ids: List[int]
    retrieved_chunks: int = 0
    context_chunks: int = 0
    used_reranker: bool = False


class RAGQueryResponse(BaseModel):
    answer: str

    sources: List[CitationSourceSchema]

    metadata: Optional[RAGMetadataSchema] = None
