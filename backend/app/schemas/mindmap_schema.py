from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MindmapCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class MindmapListItem(BaseModel):
    id: int
    notebook_id: int
    title: str
    source_document_ids: list[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MindmapNode(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1, max_length=160)
    children: list["MindmapNode"]

    model_config = ConfigDict(extra="forbid")


class MindmapOut(MindmapListItem):
    content_json: MindmapNode
