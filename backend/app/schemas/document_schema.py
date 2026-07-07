from typing import Optional

from pydantic import BaseModel


class DocumentUploadResponseData(BaseModel):
    document_id: int
    title: str
    status: str


class DocumentUploadResponse(BaseModel):
    message: str
    data: DocumentUploadResponseData


class SummaryRequest(BaseModel):
    document_id: int


class SummaryResponseData(BaseModel):
    document_id: int
    title: str
    status: str
    parsed_content: Optional[str] = None
    summary_content: Optional[str] = None


class SummaryResponse(BaseModel):
    message: str
    data: SummaryResponseData
