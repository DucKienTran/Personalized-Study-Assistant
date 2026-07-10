from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)

    mongo_id = Column(String(50), nullable=True)

    # metadata Chứa toàn bộ thông tin phân loại
    # {"purpose": "learning", "unlock_essay": true, "has_educational_images": true, "image_captions": [...]}
    metadata_info = Column(JSON, nullable=True)

    status = Column(
        String(50), default="pending"
    )  # pending, processing, completed, failed

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Quan hệ
    user = relationship("User", back_populates="documents")
    quizzes = relationship(
        "Quiz", back_populates="document", cascade="all, delete-orphan"
    )

    summaries = relationship(
        "DocumentSummary", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentSummary(Base):
    __tablename__ = "document_summaries"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    document_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)

    # Khóa ngoại dạng chuỗi trỏ sang ObjectId của MongoDB
    mongo_summary_id = Column(String(50), nullable=False)

    # Lưu cấu hình lúc sinh bản tóm tắt
    level = Column(String(50), nullable=False)  # short | normal | detailed
    format = Column(String(50), nullable=False)  # paragraph | bullet | markdown
    instruction = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Quan hệ ngược lại với Document
    document = relationship("Document", back_populates="summaries")
