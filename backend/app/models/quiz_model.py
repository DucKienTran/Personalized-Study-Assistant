from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
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

    notebook_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = Column(String(255), nullable=False)

    quiz_type = Column(
        String(50),
        nullable=False,
        default="strict",
    )  # strict | open

    mode = Column(
        String(20),
        nullable=False,
        default="study",
        server_default="study",
    )  # study | exam

    generation_strategy = Column(
        String(30),
        nullable=False,
        default="manual",
        server_default="manual",
    )  # manual | ai_recommended

    total_questions = Column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
    )

    target_total_points = Column(
        Numeric(12, 2),
        nullable=False,
        default=100,
        server_default="100",
    )

    question_types = Column(
        JSON,
        nullable=True,
    )  # ["multiple_choice", "true_false"]

    difficulty_distribution = Column(
        JSON,
        nullable=True,
    )
    # {
    #     "easy": 2,
    #     "medium": 5,
    #     "hard": 3
    # }

    custom_instruction = Column(Text, nullable=True)

    time_limit_minutes = Column(Integer, nullable=True)

    generation_status = Column(
        String(20),
        nullable=False,
        default="processing",
        server_default="processing",
    )  # processing | completed | failed

    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Snapshot document_ids đang active tại thời điểm generate
    source_document_ids = Column(JSON, nullable=False)

    # Relationships
    notebook = relationship("Notebook", back_populates="quizzes")
    user = relationship("User")

    questions = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
    )

    attempts = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan",
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)

    quiz_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_text = Column(Text, nullable=False)

    question_type = Column(
        String(50),
        nullable=False,
        default="multiple_choice",
    )

    options = Column(JSON, nullable=True)

    statements = Column(JSON, nullable=True)

    correct_answer = Column(JSON, nullable=True)

    explanations = Column(JSON, nullable=True)

    hint = Column(Text, nullable=True)

    points = Column(
        Numeric(12, 2),
        nullable=False,
        default=1,
        server_default="1",
    )

    quiz = relationship("Quiz", back_populates="questions")

    progresses = relationship(
        "QuizProgress",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)

    quiz_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    score = Column(Numeric(12, 2), nullable=True)

    attempt_status = Column(
        String(20),
        nullable=False,
        default="in_progress",
        server_default="in_progress",
    )  # in_progress | completed

    # Thời điểm người dùng bắt đầu làm bài
    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Thời điểm nộp bài
    submitted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Tổng thời gian làm bài (giây)
    duration_seconds = Column(
        Integer,
        nullable=True,
    )

    # Thứ tự hiển thị câu hỏi trong attempt (để shuffle/resume/review)
    question_order = Column(
        JSON,
        nullable=False,
    )  # [8, 2, 5, 1, 6, 4]

    # Nhận xét tổng quan sau khi hoàn thành bài
    ai_comment = Column(
        Text,
        nullable=True,
    )

    # submit | timeout | auto_submit | abandoned ...
    submit_reason = Column(
        String(30),
        nullable=True,
    )

    # Audit timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    quiz = relationship(
        "Quiz",
        back_populates="attempts",
    )

    user = relationship("User")

    progresses = relationship(
        "QuizProgress",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class QuizProgress(Base):
    __tablename__ = "quiz_progress"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    attempt_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_answer = Column(
        JSON,
        nullable=False,
    )

    is_correct = Column(
        Boolean,
        nullable=True,
    )

    answered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    time_spent_seconds = Column(
        Integer,
        nullable=True,
    )

    ai_feedback = Column(
        Text,
        nullable=True,
    )

    awarded_points = Column(Numeric(12, 2), nullable=True)

    mark_status = Column(
        String(20),
        nullable=True,
    )  # review | critical

    attempt = relationship(
        "QuizAttempt",
        back_populates="progresses",
    )

    question = relationship(
        "QuizQuestion",
        back_populates="progresses",
    )

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_progress_per_attempt",
        ),
    )
