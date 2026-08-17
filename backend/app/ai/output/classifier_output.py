from app.ai.constants.document_classification import (
    Category,
    Language,
    Purpose,
)
from pydantic import BaseModel, ConfigDict


class ClassifierOutput(BaseModel):
    """
    Validated schema returned by the document classifier.
    """

    model_config = ConfigDict(extra="forbid")

    categories: list[Category]
    language: Language
    purpose: Purpose
