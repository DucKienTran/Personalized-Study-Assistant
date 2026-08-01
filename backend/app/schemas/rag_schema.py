from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    notebook_id: int = Field(..., description="Notebook đang chat")
    document_ids: Optional[List[int]] = Field(
        None,
        description=(
            "Override tùy chọn: chỉ dùng chunk từ các document_id này. "
            "Nếu bỏ trống, service tự lấy toàn bộ document đang is_active=True trong notebook."
        ),
    )
    top_k: int = Field(5, ge=1, le=20, description="Số lượng chunk lấy ra")
    chat_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Lịch sử hội thoại"
    )
    conversation_id: Optional[int] = None


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
    retrieved_chunks: int = 0
    context_chunks: int = 0
    used_reranker: bool = False


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[CitationSourceSchema]
    metadata: Optional[RAGMetadataSchema] = None