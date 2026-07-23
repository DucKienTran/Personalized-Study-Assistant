# app/models/document_model.py
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    ForeignKey,
    Integer,
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

    status = Column(
        String(50), default="pending"
    )  # pending, processing, completed, failed

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # AI Classification info (Copy một phần từ AI Classification sang MySQL)
    language = Column(String(10), nullable=True)
    purpose = Column(String(50), nullable=True)
    categories = Column(JSON, nullable=True)  # [ "social_sciences_humanities", ... ]

    # Thống kê
    total_pages = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    total_characters = Column(Integer, default=0)
    estimated_tokens = Column(Integer, default=0)

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

    mongo_summary_id = Column(String(50), nullable=False)

    level = Column(String(50), nullable=False)  # short | normal | detailed
    format = Column(String(50), nullable=False)  # paragraph | bullet | markdown
    instruction = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    document = relationship("Document", back_populates="summaries")
