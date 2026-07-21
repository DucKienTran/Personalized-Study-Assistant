from datetime import UTC, datetime
import logging

from bson import ObjectId
from sqlalchemy.orm import Session

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
        parser_service: DocumentParserService,
        storage_service: StorageService,
        llm_client: LLMClient,
    ):
        self.sql_db = sql_db
        self.mongo_collection = mongo_db["parsed_documents"]
        self.parser_service = parser_service
        self.storage_service = storage_service
        self.pipeline = DocumentProcessingPipeline(llm_client=llm_client)

    async def execute_processing_pipeline(
        self, document_id: int, mongo_id: str, object_name: str
    ) -> None:
        self.sql_db.query(SQLDocument).filter(SQLDocument.id == document_id).update(
            {"status": "processing"}
        )
        self.sql_db.commit()

        try:
            target_id = ObjectId(mongo_id)
        except Exception:
            target_id = mongo_id

        logger.info("Connected DB Name: %s", self.mongo_collection.database.name)
        logger.info("Connected Collection: %s", self.mongo_collection.name)
        logger.info("MongoDB Server Address: %s", self.mongo_collection.database.client.address)

        await self.mongo_collection.update_one(
            {"_id": target_id},
            {"$set": {"status": "processing", "processing_started_at": datetime.now(UTC)}},
        )

        try:
            parsed_document = await self.parser_service.parse_document(
                object_name=object_name,
                storage_service=self.storage_service,
            )

            processed_document = await self.pipeline.process(
                markdown=parsed_document.markdown,
                total_pages=parsed_document.total_pages,
            )

            for chunk, cm in zip(processed_document.chunks, processed_document.chunk_metadata):
                cm.chunk_id = f"doc_{document_id}_{cm.chunk_id}"
                if cm.previous_chunk:
                    cm.previous_chunk = f"doc_{document_id}_{cm.previous_chunk}"
                if cm.next_chunk:
                    cm.next_chunk = f"doc_{document_id}_{cm.next_chunk}"

            serialized_data = processed_document.to_dict()

            classification_data = None
            if processed_document.classification:
                classification_data = processed_document.classification.to_mongo()

            mongo_result = await self.mongo_collection.update_one(
                {"_id": target_id},
                {
                    "$set": {
                        "status": "completed",
                        "total_pages": parsed_document.total_pages,
                        "content_raw": processed_document.raw_text,
                        "metadata": serialized_data["metadata"],
                        "chunks": serialized_data["chunks"],
                        "classification": classification_data,
                        "processed_at": datetime.now(UTC),
                    }
                },
            )

            if mongo_result.matched_count == 0:
                raise ValueError(
                    f"Document with mongo_id {mongo_id} not found in MongoDB collection"
                )

            logger.info(
                f"Successfully processed and updated MongoDB for document ID: {document_id}"
            )

            self.sql_db.query(SQLDocument).filter(SQLDocument.id == document_id).update(
                {"status": "completed"}
            )
            self.sql_db.commit()

        except Exception as e:
            logger.exception(f"Background processing failed at document_id {document_id}:")

            try:
                await self.mongo_collection.update_one(
                    {"_id": target_id}, {"$set": {"status": "failed", "error_log": str(e)}}
                )
            except Exception as mongo_err:
                logger.error(f"Failed to update status in MongoDB: {mongo_err}")

            try:
                self.sql_db.query(SQLDocument).filter(SQLDocument.id == document_id).update(
                    {"status": "failed"}
                )
                self.sql_db.commit()

            except Exception as sql_err:
                logger.error(f"Failed to update status in MySQL: {sql_err}")

            raise e
