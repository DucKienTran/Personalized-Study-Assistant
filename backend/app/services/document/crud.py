from datetime import UTC, datetime

from bson import ObjectId
from sqlalchemy.orm import Session

from app.models.document_model import Document


class DocumentCRUDService:
    def __init__(self, sql_db: Session, mongo_db):
        self.sql_db = sql_db
        self.mongo_collection = mongo_db["parsed_documents"]

    async def create_document(self, user_id: int, filename: str, total_pages: int, text: str):
        # lưu mongodb
        mongo_data = {
            "title": filename,
            "total_pages": total_pages,
            "content_raw": text,
            "summary": None,
            "status": "pending",
            "created_at": datetime.now(UTC),
        }
        mongo_result = await self.mongo_collection.insert_one(mongo_data)

        # lưu mysql
        new_doc = Document(
            user_id=user_id,
            title=filename,
            file_path="chua_co_storage",
            file_type="pdf",
            mongo_id=str(mongo_result.inserted_id),
            status="pending",
        )
        self.sql_db.add(new_doc)
        self.sql_db.commit()
        self.sql_db.refresh(new_doc)
        return new_doc

    def get_documents(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 10,
        status_filter: str = None,
        document_id: int = None,
    ):
        """Lấy danh sách, có hỗ trợ lọc và phân trang, hoặc lấy 1 document cụ thể"""
        query = self.sql_db.query(Document).filter(Document.user_id == user_id)

        # Nếu truyền document_id
        if document_id:
            return query.filter(Document.id == document_id).first()

        # Nếu có filter theo status
        if status_filter:
            query = query.filter(Document.status == status_filter)

        # Sắp xếp mới nhất lên đầu và phân trang
        return query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    def update_document_status(self, document_id: int, new_status: str):
        """Cập nhật trạng thái của document"""
        doc = self.sql_db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = new_status
            self.sql_db.commit()
            self.sql_db.refresh(doc)
        return doc

    async def delete_document(self, document_id: int, user_id: int):
        doc = (
            self.sql_db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )

        if not doc:
            return False

        if doc.mongo_id:
            await self.mongo_collection.delete_one({"_id": ObjectId(doc.mongo_id)})

        self.sql_db.delete(doc)
        self.sql_db.commit()
        return True
