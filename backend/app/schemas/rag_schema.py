# app/schemas/rag_schema.py

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Câu hỏi của người dùng",
    )


class CitationSourceSchema(BaseModel):
    index: int
    document_id: int
    document_title: str
    page_start: int
    page_end: int
    header_path: list[str]
    chunk_id: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[CitationSourceSchema]
