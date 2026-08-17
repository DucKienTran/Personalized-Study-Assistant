from datetime import UTC, datetime
import logging
from pathlib import Path
import re
from typing import Optional
from urllib.parse import quote
from uuid import uuid4

from bson import ObjectId
from chromadb.api import ClientAPI
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.exceptions.base import BadRequestError
from app.models.document_model import Document
from app.services.document.metadata_builder import build_markdown_outline
from app.storage.base import StorageService

logger = logging.getLogger(__name__)

SUPPORTED_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}

class DocumentService:
    def __init__(
        self,
        sql_db: Session,
        mongo_db,
        storage_service: StorageService,
        chroma_client: ClientAPI,
        redis: Redis,
    ):
        self.sql_db = sql_db
        self.mongo_collection = mongo_db["parsed_documents"]
        self.storage_service = storage_service
        self.chroma_client = chroma_client
        self.redis = redis

    # ==================================================
    # PRIVATE HELPERS
    # ==================================================

    def _get_owned_document(self, document_id: int, user_id: int) -> Optional[Document]:
        """Helper lấy thông tin Document thuộc sở hữu của user."""
        return (
            self.sql_db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            .first()
        )

    def _get_unique_title(self, user_id: int, base_title: str) -> str:
        """Tạo tên document duy nhất để tránh trùng lặp cho user."""
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

    # ==================================================
    # DOCUMENT CRUD & LIFECYCLE MANAGEMENT
    # ==================================================

    async def upload_and_init_document(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: int,
        title: str | None = None,
    ) -> Document:
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_FILE_TYPES:
            raise BadRequestError("Hệ thống hiện chỉ hỗ trợ PDF, DOCX, TXT và MD.")

        object_name = f"{uuid4()}{extension}"

        uploaded_to_storage = False
        mongo_id = None

        try:
            # Upload file lên Storage
            await self.storage_service.upload_file(
                object_name=object_name,
                file_bytes=file_bytes,
                content_type=SUPPORTED_FILE_TYPES[extension],
            )
            uploaded_to_storage = True

            final_title = self._get_unique_title(user_id, title or filename)

            # Khởi tạo document trên Mongo
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
            mongo_id = mongo_result.inserted_id

            # Tạo record MySQL
            new_doc = Document(
                user_id=user_id,
                title=final_title,
                file_path=object_name,
                file_type=extension.lstrip("."),
                mongo_id=str(mongo_id),
                status="pending",
                file_size=len(file_bytes),
            )

            self.sql_db.add(new_doc)
            self.sql_db.commit()
            self.sql_db.refresh(new_doc)

            logger.info(
                f"Document uploaded successfully: ID {new_doc.id} for User {user_id}."
            )

            return new_doc

        except Exception:
            self.sql_db.rollback()

            # rollback Mongo
            if mongo_id is not None:
                await self.mongo_collection.delete_one({"_id": mongo_id})

            # rollback Storage
            if uploaded_to_storage:
                try:
                    await self.storage_service.delete_file(object_name)
                except Exception as storage_error:
                    logger.error(
                        f"Failed to rollback storage object '{object_name}': {storage_error}"
                    )

            raise

    async def get_document_content(
        self,
        document_id: int,
        user_id: int,
    ) -> Optional[dict]:
        document = self._get_owned_document(document_id, user_id)
        if document is None or not document.mongo_id:
            return None

        try:
            target_id = ObjectId(document.mongo_id)
        except Exception:
            target_id = document.mongo_id

        mongo_doc = await self.mongo_collection.find_one({"_id": target_id})

        if mongo_doc is None:
            return None

        raw_text = mongo_doc.get("raw_text", mongo_doc.get("content_raw", ""))
        stored_outline = mongo_doc.get("outline", [])
        outline = (
            stored_outline
            if stored_outline and isinstance(stored_outline[0], dict)
            else build_markdown_outline(raw_text)
        )

        return {
            "title": document.title,
            "file_type": document.file_type,
            "total_pages": mongo_doc.get("total_pages", 0),
            "content_raw": raw_text,
            "outline": outline,
        }

    def get_document(
        self,
        user_id: int,
        document_id: int,
    ) -> Optional[Document]:
        return self._get_owned_document(document_id, user_id)

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

    async def delete_document(self, document_id: int, user_id: int) -> bool:
        doc = self._get_owned_document(document_id, user_id)
        if not doc:
            logger.warning(
                f"Attempted to delete document {document_id} for User {user_id}, but it was not found."
            )
            return False

        # 1. Xóa Vector Embeddings trên ChromaDB
        try:
            chroma_collection = self.chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME
            )
            chroma_collection.delete(where={"document_id": document_id})
        except Exception as e:
            logger.error(
                f"Failed to delete Chroma embeddings for Document {document_id}: {str(e)}"
            )

        # 2. Xóa metadata/parsed text trên MongoDB
        if doc.mongo_id:
            try:
                target_id = ObjectId(doc.mongo_id)
            except Exception:
                target_id = doc.mongo_id
            await self.mongo_collection.delete_one({"_id": target_id})

        # 3. Xóa record trong MySQL
        self.sql_db.delete(doc)
        self.sql_db.commit()

        # 4. Tăng version cache BM25 trong Redis để invalidate index cũ
        await self.redis.incr(f"rag:bm25:version:{user_id}")

        logger.info(
            f"Document {document_id} deleted successfully across all storage layers for User {user_id}."
        )

        return True

    async def get_document_file_url(
        self,
        document_id: int,
        user_id: int,
    ) -> Optional[str]:
        document = self._get_owned_document(document_id, user_id)
        if document is None:
            return None

        return await self.storage_service.get_presigned_url(
            object_name=document.file_path,
        )

    async def get_document_download_url(
        self,
        document_id: int,
        user_id: int,
    ) -> Optional[str]:
        document = self._get_owned_document(document_id, user_id)
        if document is None:
            return None

        extension = f".{document.file_type.lower().lstrip('.')}"
        content_type = SUPPORTED_FILE_TYPES.get(extension, "application/octet-stream")
        filename = re.sub(r'[\\/\r\n\x00-\x1f\x7f"]', "_", document.title).strip()
        duplicate_suffix = re.search(rf"{re.escape(extension)} \((\d+)\)$", filename, re.IGNORECASE)
        if duplicate_suffix:
            filename = (
                filename[: duplicate_suffix.start()]
                + f" ({duplicate_suffix.group(1)}){extension}"
            )
        elif not filename.lower().endswith(extension):
            filename = f"{filename or 'document'}{extension}"

        ascii_filename = filename.encode("ascii", "ignore").decode().strip() or f"document{extension}"
        disposition = (
            f'attachment; filename="{ascii_filename}"; '
            f"filename*=UTF-8''{quote(filename, safe='')}"
        )
        return await self.storage_service.get_presigned_url(
            object_name=document.file_path,
            response_headers={
                "response-content-disposition": disposition,
                "response-content-type": content_type,
            },
        )
