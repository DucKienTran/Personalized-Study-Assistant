from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.document.models import (
    DocumentAIClassification,
    ProcessedDocument,
)


class DocumentClassifier(ABC):
    """
    AI document classifier.
    Analyze the processed document and produce semantic metadata.
    """

    @abstractmethod
    async def classify(
        self,
        document: ProcessedDocument,
    ) -> DocumentAIClassification:
        raise NotImplementedError
