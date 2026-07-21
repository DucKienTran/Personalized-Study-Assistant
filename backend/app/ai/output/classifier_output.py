from pydantic import BaseModel, ConfigDict

from app.ai.constants import (
    Category,
    Language,
    Purpose,
)


class ClassifierOutput(BaseModel):
    """
    Validated schema returned by the document classifier.
    """

    model_config = ConfigDict(extra="forbid")

    categories: list[Category]

    language: Language

    purpose: Purpose

    keywords: list[str]