from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.models.notebook_model import Notebook, NotebookSummary


class SummaryRecordService:
    def __init__(
        self,
        sql_db: Session,
        mongo_db: AsyncIOMotorDatabase,
    ) -> None:
        self.sql_db = sql_db
        # Đã đổi sang collection notebook_summaries để đồng bộ hoàn toàn với kiến trúc mới
        self.summary_collection = mongo_db["notebook_summaries"]

    async def save_summary(
        self,
        user_id: int,
        notebook_id: int,
        title: str,
        summary_text: str,
        config: dict,
    ) -> dict[str, Any]:
        """
        Lưu một bản tóm tắt mới.
        """
        notebook = (
            self.sql_db.query(Notebook)
            .filter(Notebook.id == notebook_id, Notebook.user_id == user_id)
            .first()
        )
        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy Notebook hợp lệ",
            )

        # Lấy danh sách các file đang active tại thời điểm lưu để ghi vào metadata
        active_doc_ids = [
            nd.document_id for nd in notebook.notebook_documents if nd.is_active
        ]

        mongo_data = {
            "summary_text": summary_text,
            "draft_text": None,  # Để dành cho tính năng bản nháp gần nhất sau này
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        mongo_result = await self.summary_collection.insert_one(mongo_data)

        new_summary_record = NotebookSummary(
            notebook_id=notebook_id,
            title=title,
            mongo_summary_id=str(mongo_result.inserted_id),
            level=config.get("level", "standard"),
            format=config.get("format", "markdown"),
            instruction=config.get("instruction", ""),
            source_document_ids=active_doc_ids,
        )
        self.sql_db.add(new_summary_record)
        self.sql_db.commit()
        self.sql_db.refresh(new_summary_record)

        return {
            "summary_id": new_summary_record.id,
            "title": new_summary_record.title,
            "mongo_summary_id": new_summary_record.mongo_summary_id,
            "message": "Đã lưu bản tóm tắt thành công.",
        }

    async def update_summary(
        self,
        user_id: int,
        notebook_id: int,
        summary_id: int,
        summary_text: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """
        Cập nhật tên hoặc nội dung bản tóm tắt khi người dùng xác nhận chỉnh sửa.
        """
        summary_record = (
            self.sql_db.query(NotebookSummary)
            .join(Notebook)
            .filter(
                NotebookSummary.id == summary_id,
                NotebookSummary.notebook_id == notebook_id,
                Notebook.user_id == user_id,
            )
            .first()
        )
        if not summary_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bản tóm tắt không tồn tại",
            )

        await self.summary_collection.update_one(
            {"_id": ObjectId(summary_record.mongo_summary_id)},
            {
                "$set": {
                    "summary_text": summary_text,
                    "updated_at": datetime.now(UTC),
                }
            },
        )

        if title is not None:
            summary_record.title = title

        summary_record.updated_at = datetime.now(UTC)
        self.sql_db.commit()

        return {
            "summary_id": summary_record.id,
            "message": "Cập nhật",
        }

    def get_summary_history_list(
        self,
        user_id: int,
        notebook_id: int,
    ) -> list[NotebookSummary]:
        """
        Lấy danh sách lịch sử Summary của Notebook.

        Chỉ lấy metadata từ MySQL.
        Không truy cập MongoDB.
        """

        notebook = (
            self.sql_db.query(Notebook)
            .filter(
                Notebook.id == notebook_id,
                Notebook.user_id == user_id,
            )
            .first()
        )

        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy Notebook hợp lệ",
            )

        summaries = (
            self.sql_db.query(NotebookSummary)
            .filter(NotebookSummary.notebook_id == notebook_id)
            .order_by(NotebookSummary.created_at.desc())
            .all()
        )

        return summaries

    async def get_summary_detail(
        self,
        user_id: int,
        notebook_id: int,
        summary_id: int,
    ) -> dict[str, Any]:
        """
        Lấy chi tiết một Notebook Summary.

        Metadata lấy từ MySQL.
        Nội dung summary lấy từ MongoDB.
        """
        summary_record = (
            self.sql_db.query(NotebookSummary)
            .join(Notebook)
            .filter(
                NotebookSummary.id == summary_id,
                NotebookSummary.notebook_id == notebook_id,
                Notebook.user_id == user_id,
            )
            .first()
        )

        if not summary_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bản tóm tắt không tồn tại",
            )

        mongo_summary = await self.summary_collection.find_one(
            {
                "_id": ObjectId(summary_record.mongo_summary_id),
            }
        )

        if not mongo_summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy nội dung Summary",
            )

        return {
            "id": summary_record.id,
            "notebook_id": summary_record.notebook_id,
            "notebook_title": summary_record.notebook.title,
            "title": summary_record.title,
            "level": summary_record.level,
            "format": summary_record.format,
            "instruction": summary_record.instruction,
            "summary_text": mongo_summary.get("summary_text", ""),
            "draft_text": mongo_summary.get("draft_text"),
            "created_at": summary_record.created_at,
        }
