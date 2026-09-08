from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConversationSummary(BaseModel):
    id: int
    title: str
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    sender: str
    content: str
    sources_json: Optional[str] = None
    resource_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    id: int
    title: str
    messages: list[MessageOut]


class CreateConversationRequest(BaseModel):
    notebook_id: int


class RenameConversationRequest(BaseModel):
    title: str
