from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.mysql import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)

    quiz_type = Column(String(50), nullable=False, default="strict")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="quizzes")
    user = relationship("User")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    results = relationship("QuizResult", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(BigInteger, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)

    question_text = Column(Text, nullable=False)

    question_type = Column(String(50), nullable=False, default="multiple_choice")

    # List các lựa chọn cho trắc nghiệm: ["A. ...", "B. ..."] dạng JSON
    options = Column(JSON, nullable=True)

    correct_answer = Column(JSON, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(BigInteger, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    score = Column(Float, nullable=True)

    # Danh sách câu trả lời của user dưới dạng JSON
    # Ví dụ [{"question_id": 1, "user_answer": "A"}, {"question_id": 2, "user_answer": "Bài làm tự luận..."}]
    answers_json = Column(JSON, nullable=False)

    # Nhận xét từ AI
    ai_comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    quiz = relationship("Quiz", back_populates="results")
    user = relationship("User")
