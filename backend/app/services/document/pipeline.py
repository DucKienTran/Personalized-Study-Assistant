from __future__ import annotations
import logging
from app.services.ai.classifier_service import AIClassifier
from app.ai.llm.base import LLMClient
from app.services.document.chunk_builder import DocumentChunkBuilder
from app.services.document.cleaner import DocumentCleaner
from app.services.document.metadata_builder import MetadataBuilder
from app.services.document.models import ProcessedDocument

logger = logging.getLogger(__name__)


class DocumentProcessingPipeline:
    def __init__(self, llm_client: LLMClient):
        self.cleaner = DocumentCleaner()
        self.chunk_builder = DocumentChunkBuilder()
        self.metadata_builder = MetadataBuilder()
        self.classifier = AIClassifier(llm_client)

    async def process(
        self,
        markdown: str,
        total_pages: int,
    ) -> ProcessedDocument:
        logger.info("Starting document processing pipeline...")

        # Content cleaning
        cleaned_markdown = self.cleaner.clean(markdown)
        logger.info("Cleaned document content. Total length: %d characters.", len(cleaned_markdown))

        # AI Classification
        logger.info("Sending document text to AI model for classification...")
        classification = await self.classifier.classify(cleaned_markdown)
        logger.info(
            "Classification completed. Language: %s, Categories: %s",
            classification.language,
            classification.categories,
        )

        # Chunking
        logger.info("Splitting document content into chunks...")
        sections = self.chunk_builder.build(cleaned_markdown)
        logger.info("Successfully split document into %d chunks.", len(sections))

        # Metadata Building
        logger.info("Generating metadata and mapping page numbers for chunks...")
        metadata, chunk_metadata = self.metadata_builder.build(
            chunks=sections,
            total_pages=total_pages,
        )
        logger.info("Metadata generation completed.")

        return ProcessedDocument(
            raw_text=cleaned_markdown,
            chunks=sections,
            chunk_metadata=chunk_metadata,
            metadata=metadata,
            classification=classification,
        )