from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from bson import ObjectId
from sqlalchemy.orm import Session

from app.exceptions.base import BadRequestError
from app.models.document_model import Document
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
            row[0]
            for row in self.sql_db.query(Document.title)
            .filter(Document.user_id == user_id)
            .all()
        }
        if base_title not in existing_titles:
            return base_title
        i = 1
        while f"{base_title} ({i})" in existing_titles:
            i += 1
        return f"{base_title} ({i})"

    async def upload_and_init_document(
        self, file_bytes: bytes, filename: str, user_id: int
    ) -> Document:
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
            "raw_text": "",
            "outline": [],
            "classification": None,
            "status": "pending",
            "created_at": datetime.now(UTC),
        }
        mongo_result = await self.mongo_collection.insert_one(mongo_data)

        # Lưu thông tin ban đầu vào MySQL
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

    def get_document(
        self,
        user_id: int,
        document_id: int,
    ) -> Optional[Document]:
        return (
            self.sql_db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            .first()
        )

    def list_documents(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 10,
        status_filter: Optional[str] = None,
    ) -> list[Document]:
        query = self.sql_db.query(Document).filter(Document.user_id == user_id)

        if status_filter:
            query = query.filter(Document.status == status_filter)

        return (
            query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
        )

    def list_document_ids(
        self,
        user_id: int,
        status_filter: str = "completed",
    ) -> list[int]:
        """
        Trả về danh sách ID của các tài liệu thuộc người dùng.
        Mặc định chỉ lấy tài liệu đã xử lý xong để phục vụ Retrieval / RAG.
        """
        rows = (
            self.sql_db.query(Document.id)
            .filter(
                Document.user_id == user_id,
                Document.status == status_filter,
            )
            .all()
        )

        return [row.id for row in rows]

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
