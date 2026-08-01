from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class GenerateNotebookSummaryRequest(BaseModel):
    """
    notebook_id lấy từ path (/notebooks/{notebook_id}/summary),
    không lặp lại trong body.
    """

    level: str = "standard"
    format: str = "markdown"
    instruction: Optional[str] = ""


class SaveNotebookSummaryRequest(BaseModel):
    """
    Lưu một bản Summary chính thức của Notebook.
    """

    title: str
    summary_text: str

    level: str = "standard"
    format: str = "markdown"
    instruction: Optional[str] = ""


class OverwriteNotebookSummaryRequest(BaseModel):
    """
    Ghi đè nội dung một Summary đã lưu.
    """

    title: str | None = None
    summary_text: str


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class NotebookSummaryOut(BaseModel):
    """
    Metadata của một bản Summary trong lịch sử.
    """

    id: int
    notebook_id: int

    title: str

    level: str
    format: str

    source_document_ids: list[int]

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotebookSummaryDetail(BaseModel): 
    """ Chi tiết của một bản Summary bao gồm cả nội dung từ MongoDB. """ 
    id: int 
    notebook_id: int 
    notebook_title: str
    title: str
    level: str 
    format: str 
    instruction: Optional[str] = "" 
    summary_text: str 
    draft_text: Optional[str] = None 
    created_at: datetime 

    model_config = ConfigDict(from_attributes=True)

