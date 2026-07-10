from typing import Optional

from pydantic import BaseModel
from datetime import datetime
from pydantic import ConfigDict


class SaveSummaryRequest(BaseModel):
    document_id: int
    title: str
    summary_text: str
    level: str = "normal"
    format: str = "markdown"
    instruction: Optional[str] = ""


class OverwriteSummaryRequest(BaseModel):
    summary_text: str


# Schema dùng để trả dữ liệu cho danh sách lịch sử
class SummaryOut(BaseModel):
    id: int
    document_id: int
    title: str
    level: str
    format: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
