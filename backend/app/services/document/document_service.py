from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from bson import ObjectId
from sqlalchemy.orm import Session

from app.exceptions.base import BadRequestError
from app.models.document_model import Document
from app.services.document.parser import DocumentParserService
from app.services.document.pipeline import DocumentProcessingPipeline
from app.storage.base import StorageService

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

# abc
class DocumentService:
    def __init__(self, sql_db: Session, mongo_db, storage_service: StorageService):
        self.sql_db = sql_db
        self.mongo_collection = mongo_db["parsed_documents"]
        self.storage_service = storage_service

    def _get_unique_title(self, user_id: int, base_title: str) -> str:
        existing_titles = {
            row[0] for row in self.sql_db.query(Document.title).filter(Document.user_id == user_id).all()
        }
        if base_title not in existing_titles:
            return base_title
        i = 1
        while f"{base_title} ({i})" in existing_titles:
            i += 1
        return f"{base_title} ({i})"

    async def upload_and_init_document(self, file_bytes: bytes, filename: str, user_id: int) -> Document:
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise BadRequestError("Hệ thống hiện chỉ hỗ trợ PDF và DOCX.")

        object_name = f"{uuid4()}{extension}"
        await self.storage_service.upload_file(
            object_name=object_name,
            file_bytes=file_bytes,
            content_type=(
                "application/pdf"
                if extension == ".pdf"
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )

        final_title = self._get_unique_title(user_id, filename)

        mongo_data = {
            "title": final_title,
            "object_name": object_name,
            "total_pages": 0,
            "content_raw": "",
            "metadata": {},
            "chunks": [],
            "classification": None,
            "summaries": {},
            "status": "pending",
            "created_at": datetime.now(UTC),
        }
        mongo_result = await self.mongo_collection.insert_one(mongo_data)

        # lưu metadata vào SQL
        new_doc = Document(
            user_id=user_id,
            title=final_title,
            file_path=object_name,
            file_type=extension.lstrip("."),
            mongo_id=str(mongo_result.inserted_id),
            status="pending",
        )
        self.sql_db.add(new_doc)
        self.sql_db.commit()
        self.sql_db.refresh(new_doc)

        return new_doc

    async def get_document_content(
        self,
        document_id: int,
        user_id: int,
    ) -> Optional[dict]:

        document = (
            self.sql_db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            .first()
        )

        if document is None:
            return None

        mongo_doc = await self.mongo_collection.find_one(
            {"_id": ObjectId(document.mongo_id)}
        )

        if mongo_doc is None:
            return None

        return {
            "title": document.title,
            "file_type": document.file_type,
            "total_pages": mongo_doc["total_pages"],
            "content_raw": mongo_doc["content_raw"],
        }

    async def process_document(
        self,
        document_id: int,
        user_id: int,
    ) -> Document:
        """
        Process an uploaded document.

        Pipeline

        pending
            ↓
        processing
            ↓
        classifier (future)
            ↓
        embedding (future)
            ↓
        vector database (future)
            ↓
        completed
        """

        document = self.get_documents(
            user_id=user_id,
            document_id=document_id,
        )

        if document is None:
            raise BadRequestError("Không tìm thấy tài liệu.")

        if document.status == "completed":
            return document

        mongo_document = await self.mongo_collection.find_one(
            {
                "_id": ObjectId(document.mongo_id),
            }
        )

        if mongo_document is None:
            raise BadRequestError("Không tìm thấy dữ liệu tài liệu trong MongoDB.")

        document.status = "processing"

        self.sql_db.commit()

        await self.mongo_collection.update_one(
            {
                "_id": ObjectId(document.mongo_id),
            },
            {
                "$set": {
                    "status": "processing",
                    "processing_started_at": datetime.now(UTC),
                }
            },
        )

        # =====================================================
        # Future
        # =====================================================
        #
        # processed = mongo_document["processed"]
        #
        # classification = await self.classifier.classify(
        #     processed
        # )
        #
        # await self.mongo_collection.update_one(...)
        #
        # await self.embedding_service.embed_document(...)
        #
        # await self.vector_store.upsert(...)
        #
        # =====================================================

        document.status = "completed"

        self.sql_db.commit()

        await self.mongo_collection.update_one(
            {
                "_id": ObjectId(document.mongo_id),
            },
            {
                "$set": {
                    "status": "completed",
                    "processed_at": datetime.now(UTC),
                }
            },
        )

        self.sql_db.refresh(document)

        return document

    async def delete_document(self, document_id: int, user_id: int) -> bool:
        doc = (
            self.sql_db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )
        if not doc:
            return False
        self.sql_db.delete(doc)
        self.sql_db.commit()
        return True
