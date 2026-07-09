from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.document_model import Document
from app.services.document.parser import DocumentParserService


class DocumentService:
    def __init__(self, sql_db: Session, mongo_db, parser_service: DocumentParserService):
        self.sql_db = sql_db
        self.mongo_collection = mongo_db["parsed_documents"]
        self.parser_service = parser_service

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
    
    async def upload_and_process_document(self, file_bytes: bytes, filename: str, user_id: int):
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hệ thống chỉ hỗ trợ xử lý tài liệu định dạng PDF.",
            )

        total_pages, extracted_text = self.parser_service._extract_text_sync(file_bytes, filename)
        final_title = self._get_unique_title(user_id, filename)

        mongo_data = {
            "title": final_title,
            "total_pages": total_pages,
            "content_raw": extracted_text,
            "summary": None,
            "status": "pending",
            "created_at": datetime.now(UTC),
        }
        mongo_result = await self.mongo_collection.insert_one(mongo_data)

        # Lưu MySQL
        new_doc = Document(
            user_id=user_id,
            title=final_title,
            file_path="chua_co_storage",
            file_type="pdf",
            mongo_id=str(mongo_result.inserted_id),
            status="pending",
        )
        self.sql_db.add(new_doc)
        self.sql_db.commit()
        self.sql_db.refresh(new_doc)

        # Chỉ trả về Object thô, không bọc chữ "status": "success" bừa bãi
        return new_doc

    def get_documents(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 10,
        status_filter: str = None,
        document_id: int = None,
    ):
        query = self.sql_db.query(Document).filter(Document.user_id == user_id)
        if document_id:
            return query.filter(Document.id == document_id).first()
        if status_filter:
            query = query.filter(Document.status == status_filter)
        return query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

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

    
