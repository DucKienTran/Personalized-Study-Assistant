# app/models/notebook_model.py
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(
        String(20),
        nullable=False,
        default="#3C6543",  # Moss Green
    )
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Quan hệ
    user = relationship("User", back_populates="notebooks")
    notebook_documents = relationship(
        "NotebookDocument",
        back_populates="notebook",
        cascade="all, delete-orphan",
    )
    summaries = relationship(
        "NotebookSummary", back_populates="notebook", cascade="all, delete-orphan"
    )
    quizzes = relationship(
        "Quiz", back_populates="notebook", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation",
        back_populates="notebook",
        cascade="all, delete-orphan",
    )


class NotebookDocument(Base):
    """Bảng liên kết Notebook <-> Document (many-to-many), kèm trạng thái is_active
    để bật/tắt document dùng cho retrieval (RAG, Summary, Quiz) trong từng notebook.
    """

    __tablename__ = "notebook_documents"
    __table_args__ = (
        UniqueConstraint("notebook_id", "document_id", name="uq_notebook_document"),
    )

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    notebook_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_active = Column(Boolean, default=True, nullable=False)
    added_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Quan hệ
    notebook = relationship("Notebook", back_populates="notebook_documents")
    document = relationship("Document", back_populates="notebook_documents")


class NotebookSummary(Base):
    """Summary tổng hợp cho cả notebook (thay thế DocumentSummary cũ).
    Được tổng hợp từ các document đang is_active=True trong notebook tại thời
    điểm generate. Nội dung thực tế (markdown) lưu ở Mongo qua mongo_summary_id,
    MySQL chỉ giữ metadata + snapshot nguồn.
    """

    __tablename__ = "notebook_summaries"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    notebook_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)

    mongo_summary_id = Column(String(50), nullable=False)

    level = Column(String(50), nullable=False)  # brief | standard | comprehensive
    format = Column(String(50), nullable=False)  # paragraph | bullet | markdown
    instruction = Column(Text, nullable=True)

    # Snapshot document_ids đang active tại thời điểm generate — vì tập active
    # có thể đổi sau đó, cần biết summary này thực sự tổng hợp từ đâu.
    source_document_ids = Column(JSON, nullable=False)  # [12, 15, 18]

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    notebook = relationship("Notebook", back_populates="summaries")
