from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.document_model import Document, DocumentSummary


class DocumentSummaryService:
    def __init__(self, sql_db: Session, mongo_db):
        self.sql_db = sql_db
        self.mongo_db = mongo_db
        # Đặt tên collection đồng bộ là document_summaries theo ý em
        self.mongo_collection = mongo_db["document_summaries"]

    async def save_manual_summary(
        self,
        user_id: int,
        document_id: int,
        title: str,
        summary_text: str,
        config: dict,
    ):
        """
        Lưu mới hoàn toàn một bản tóm tắt thủ công.
        """
        doc = (
            self.sql_db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu hợp lệ",
            )

        mongo_data = {
            "summary_text": summary_text,
            "draft_text": None,  # Để dành cho tính năng bản nháp gần nhất sau này của em
            "created_at": datetime.now(UTC),
        }
        mongo_result = await self.mongo_collection.insert_one(mongo_data)
        mongo_summary_id = str(mongo_result.inserted_id)

        new_summary_meta = DocumentSummary(
            document_id=document_id,
            title=title,
            mongo_summary_id=mongo_summary_id,
            level=config.get("level", "normal"),
            format=config.get("format", "markdown"),
            instruction=config.get("instruction", ""),
        )
        self.sql_db.add(new_summary_meta)
        self.sql_db.commit()
        self.sql_db.refresh(new_summary_meta)

        return {
            "summary_id": new_summary_meta.id,
            "title": new_summary_meta.title,
            "mongo_summary_id": mongo_summary_id,
            "message": "Đã lưu bản tóm tắt thành công.",
        }

    async def overwrite_summary(self, user_id: int, summary_id: int, summary_text: str):
        """
        Ghi đè nội dung tóm tắt khi người dùng xác nhận chỉnh sửa / đồng ý lưu tiếp đè lên bản cũ.
        """
        summary_meta = (
            self.sql_db.query(DocumentSummary)
            .join(Document)
            .filter(DocumentSummary.id == summary_id, Document.user_id == user_id)
            .first()
        )
        if not summary_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bản tóm tắt không tồn tại",
            )

        await self.mongo_collection.update_one(
            {"_id": ObjectId(summary_meta.mongo_summary_id)},
            {"$set": {"summary_text": summary_text, "updated_at": datetime.now(UTC)}},
        )

        summary_meta.updated_at = datetime.now(UTC)
        self.sql_db.commit()

        return {
            "summary_id": summary_meta.id,
            "message": "Ghi đè bản tóm tắt thành công.",
        }

    def get_summary_history_list(self, user_id: int, document_id: int = None):
        """
        Lấy danh sách tất cả các bản tóm tắt (Chỉ lấy Metadata từ MySQL giúp tải cực nhẹ).
        Nếu truyền document_id: Lấy lịch sử riêng của file đó.
        Nếu không truyền: Lấy toàn bộ lịch sử tóm tắt của User theo thứ tự thời gian mới nhất lên đầu.
        """
        query = (
            self.sql_db.query(DocumentSummary)
            .join(Document)
            .filter(Document.user_id == user_id)
        )

        if document_id:
            query = query.filter(DocumentSummary.document_id == document_id)

        # Sắp xếp lịch sử tóm tắt mới nhất lên đầu
        return query.order_by(DocumentSummary.created_at.desc()).all()

    async def get_summary_detail(self, user_id: int, summary_id: int):
        """
        Bấm vào một bản ghi lịch sử cụ thể -> Tiến hành bốc nội dung text từ MongoDB lên.
        """
        summary_meta = (
            self.sql_db.query(DocumentSummary)
            .join(Document)
            .filter(DocumentSummary.id == summary_id, Document.user_id == user_id)
            .first()
        )
        if not summary_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bản tóm tắt không tồn tại",
            )

        # Bốc text từ Mongo
        mongo_doc = await self.mongo_collection.find_one(
            {"_id": ObjectId(summary_meta.mongo_summary_id)}
        )

        return {
            "id": summary_meta.id,
            "document_id": summary_meta.document_id,
            "document_title": summary_meta.document.title,  # Lấy luôn tên file gốc để FE hiển thị tiêu đề header
            "title": summary_meta.title,
            "level": summary_meta.level,
            "format": summary_meta.format,
            "instruction": summary_meta.instruction,
            "summary_text": mongo_doc.get("summary_text") if mongo_doc else "",
            "draft_text": mongo_doc.get("draft_text") if mongo_doc else None,
            "created_at": summary_meta.created_at,
        }
