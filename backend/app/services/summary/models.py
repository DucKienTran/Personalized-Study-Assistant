from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    RELATED = "related"
    PREREQUISITE = "prerequisite"
    PART_OF = "part_of"
    CONTRASTS_WITH = "contrasts_with"


class Relationship(BaseModel):
    source: str
    target: str
    type: RelationshipType
    description: str | None = None


class Digest(BaseModel):
    """
    Internal semantic representation.

    Đây KHÔNG phải output cho user.
    Được dùng ở mọi tầng recursive summarization.
    """

    title: str

    overview: str

    key_concepts: list[str] = Field(default_factory=list)

    entities: list[str] = Field(default_factory=list)

    formulas: list[str] = Field(default_factory=list)

    relationships: list[Relationship] = Field(default_factory=list)

    keywords: list[str] = Field(default_factory=list)

    source_refs: list[str] = Field(default_factory=list)


class DigestSource(BaseModel):
    """
    Input nhỏ nhất của Digest Builder.

    Leaf level:
        id = chunk_id

    Recursive level:
        id = digest_id
    """

    id: str

    content: str
