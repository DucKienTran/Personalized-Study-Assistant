from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship

from app.core.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    document_id = Column(
        BIGINT(unsigned=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), nullable=False)
    quiz_type = Column(String(50), nullable=False, default="strict")  # strict | open
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    mode = Column(
        String(20), nullable=False, default="study", server_default="study"
    )  # "study" | "exam"
    time_limit_minutes = Column(Integer, nullable=True)
    status = Column(
        String(20), nullable=False, default="processing", server_default="processing"
    )  # "processing" | "completed" | "failed"

    # Relationships
    document = relationship("Document", back_populates="quizzes")
    user = relationship("User")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    results = relationship("QuizResult", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(
        BIGINT(unsigned=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False, default="multiple_choice")
    options = Column(JSON, nullable=True)
    correct_answer = Column(JSON, nullable=True)
    explanations = Column(JSON, nullable=True)
    points = Column(Integer, nullable=False, default=1, server_default="1")
    hint = Column(Text, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(
        BIGINT(unsigned=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(Float, nullable=True)
    attempt_status = Column(
        String(20), nullable=False, default="in_progress", server_default="in_progress"
    )  # in_progress | completed
    ai_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Để mặc định là Null, khi nào nộp bài thật mới điền lý do vào
    submit_reason = Column(String(30), nullable=True)

    quiz = relationship("Quiz", back_populates="results")
    user = relationship("User")


class QuizProgress(Base):
    __tablename__ = "quiz_progress"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    result_id = Column(
        BIGINT(unsigned=True), ForeignKey("quiz_results.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(
        BIGINT(unsigned=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )

    user_answer = Column(JSON, nullable=False)  # Câu trả lời của user cho câu hỏi này
    is_correct = Column(Boolean, nullable=True)  # Đúng/Sai/Null (chờ chấm tự luận)
    answered_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ai_feedback = Column(
        Text, nullable=True
    )  # Lời giải thích/Nhận xét động từ AI cho riêng câu này

    __table_args__ = (UniqueConstraint("result_id", "question_id", name="uq_progress_per_attempt"),)
