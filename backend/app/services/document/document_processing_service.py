# app/services/document/document_processing_service.py
from datetime import UTC, datetime
import logging

from bson import ObjectId
from chromadb.api import ClientAPI
from sqlalchemy.orm import Session
from app.core.config import settings
from app.ai.llm.base import LLMClient
from app.models.document_model import Document as SQLDocument
from app.services.document.parser import DocumentParserService
from app.services.document.pipeline import DocumentProcessingPipeline
from app.storage.base import StorageService

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    def __init__(
        self,
        sql_db: Session,
        mongo_db,
        chroma_client: ClientAPI,
        parser_service: DocumentParserService,
        storage_service: StorageService,
        llm_client: LLMClient,
    ):
        self.sql_db = sql_db
        self.mongo_collection = mongo_db["parsed_documents"]
        self.chroma_client = chroma_client
        self.parser_service = parser_service
        self.storage_service = storage_service
        self.pipeline = DocumentProcessingPipeline(llm_client=llm_client)

    async def execute_processing_pipeline(
        self, document_id: int, mongo_id: str, object_name: str
    ) -> None:
        # 1. Chuyển trạng thái MySQL -> processing
        self.sql_db.query(SQLDocument).filter(SQLDocument.id == document_id).update(
            {"status": "processing"}
        )
        self.sql_db.commit()

        try:
            target_id = ObjectId(mongo_id)
        except Exception:
            target_id = mongo_id

        # 2. Chuyển trạng thái MongoDB -> processing
        await self.mongo_collection.update_one(
            {"_id": target_id},
            {
                "$set": {
                    "status": "processing",
                    "processing_started_at": datetime.now(UTC),
                }
            },
        )

        try:
            # 3. Parse tài liệu ra Markdown
            parsed_document = await self.parser_service.parse_document(
                object_name=object_name,
                storage_service=self.storage_service,
            )

            # 4. Chạy Pipeline (Clean -> Classify -> Chunk -> Metadata -> Embedding)
            processed_document = await self.pipeline.process(
                markdown=parsed_document.markdown,
                total_pages=parsed_document.total_pages,
            )

            # 5. Chuẩn hóa chunk_id độc nhất cho từng chunk
            for chunk, cm in zip(
                processed_document.chunks, processed_document.chunk_metadata
            ):
                cm.chunk_id = f"doc_{document_id}_{cm.chunk_id}"

            # Trích xuất dữ liệu Classification
            language_val = None
            purpose_val = None
            categories_val = []

            if processed_document.classification:
                language_val = processed_document.classification.language.value
                purpose_val = processed_document.classification.purpose.value
                categories_val = [
                    c.value for c in processed_document.classification.categories
                ]

                # 6. Đẩy Chunks & Vectors sang ChromaDB
                chroma_collection = self.chroma_client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION_NAME
                )
                ids = []
                documents = []
                embeddings = []
                metadatas = []

                for chunk, cm in zip(
                    processed_document.chunks, processed_document.chunk_metadata
                ):
                    ids.append(cm.chunk_id)
                    documents.append(chunk.page_content)
                    embeddings.append(cm.embedding)

                    metadata = {
                        "document_id": document_id,
                        "chunk_id": cm.chunk_id,
                        "page_start": cm.page_start or 0,
                        "page_end": cm.page_end or 0,
                        "language": language_val or "unknown",
                        "purpose": purpose_val or "unknown",
                    }

                    if cm.header_path:
                        metadata["header_path"] = cm.header_path

                    if categories_val:
                        metadata["categories"] = categories_val

                    metadatas.append(metadata)

                if ids:
                    chroma_collection.add(
                        ids=ids,
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas,
                    )

            # 7. Cập nhật MongoDB (parsed_documents) - KHÔNG LƯU chunks/metadata
            classification_dict = (
                processed_document.classification.to_mongo()
                if processed_document.classification
                else None
            )

            mongo_result = await self.mongo_collection.update_one(
                {"_id": target_id},
                {
                    "$set": {
                        "status": "completed",
                        "raw_text": processed_document.raw_text,
                        "outline": processed_document.metadata.outline,
                        "classification": classification_dict,
                        "processed_at": datetime.now(UTC),
                    }
                },
            )

            if mongo_result.matched_count == 0:
                raise ValueError(
                    f"Document with mongo_id {mongo_id} not found in MongoDB collection"
                )

            # 8. Cập nhật thống kê & Classification thông tin vào MySQL
            self.sql_db.query(SQLDocument).filter(SQLDocument.id == document_id).update(
                {
                    "status": "completed",
                    "language": language_val,
                    "purpose": purpose_val,
                    "categories": categories_val,
                    "total_pages": processed_document.metadata.total_pages,
                    "total_chunks": processed_document.metadata.total_chunks,
                    "total_characters": processed_document.metadata.total_characters,
                    "estimated_tokens": processed_document.metadata.estimated_tokens,
                }
            )
            self.sql_db.commit()

            logger.info(f"Successfully processed document ID: {document_id}")

        except Exception as e:
            logger.exception(
                f"Background processing failed at document_id {document_id}:"
            )

            try:
                await self.mongo_collection.update_one(
                    {"_id": target_id},
                    {"$set": {"status": "failed", "error_log": str(e)}},
                )
            except Exception as mongo_err:
                logger.error(f"Failed to update status in MongoDB: {mongo_err}")

            try:
                self.sql_db.query(SQLDocument).filter(
                    SQLDocument.id == document_id
                ).update({"status": "failed"})
                self.sql_db.commit()
            except Exception as sql_err:
                logger.error(f"Failed to update status in MySQL: {sql_err}")

            raise e
