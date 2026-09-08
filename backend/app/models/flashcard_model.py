from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship

from app.core.database import Base


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"

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
    description = Column(Text, nullable=True)

    # manual | processing | completed | failed
    generation_status = Column(
        String(20),
        nullable=False,
        default="manual",
        server_default="manual",
    )

    error_message = Column(Text, nullable=True)

    # Snapshot of active notebook document IDs used when this deck was generated.
    # Empty list for manually-created decks.
    source_document_ids = Column(JSON, nullable=False, default=list)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    notebook = relationship("Notebook", back_populates="flashcard_decks")
    user = relationship("User")

    cards = relationship(
        "Flashcard",
        back_populates="deck",
        cascade="all, delete-orphan",
        order_by="Flashcard.position",
    )

    study_sessions = relationship(
        "FlashcardStudySession",
        back_populates="deck",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_flashcard_decks_user_notebook", "user_id", "notebook_id"),)


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)

    deck_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("flashcard_decks.id", ondelete="CASCADE"),
        nullable=False,
    )

    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)

    # Optional provenance for AI/RAG-generated cards.
    source_document_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_chunk_id = Column(String(255), nullable=True)
    source_metadata = Column(JSON, nullable=True)

    position = Column(Integer, nullable=False, default=0, server_default="0")
    is_suspended = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deck = relationship("FlashcardDeck", back_populates="cards")
    source_document = relationship("Document")

    review_states = relationship(
        "FlashcardReviewState",
        back_populates="card",
        cascade="all, delete-orphan",
    )

    review_logs = relationship(
        "FlashcardReviewLog",
        back_populates="card",
        cascade="all, delete-orphan",
    )

    session_cards = relationship(
        "FlashcardSessionCard",
        back_populates="card",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_flashcards_deck_position", "deck_id", "position"),
        Index("ix_flashcards_deck_suspended", "deck_id", "is_suspended"),
    )


class FlashcardReviewState(Base):
    __tablename__ = "flashcard_review_states"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    card_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("flashcards.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # new | learning | review | relearning
    state = Column(
        String(20),
        nullable=False,
        default="new",
        server_default="new",
    )

    due = Column(DateTime(timezone=True), nullable=True)

    # FSRS scheduler state.
    # Kept nullable because a truly new card may not have scheduler values yet.
    stability = Column(Float, nullable=True)
    difficulty = Column(Float, nullable=True)
    step = Column(Integer, nullable=True)

    elapsed_days = Column(Integer, nullable=False, default=0, server_default="0")
    scheduled_days = Column(Integer, nullable=False, default=0, server_default="0")

    reps = Column(Integer, nullable=False, default=0, server_default="0")
    lapses = Column(Integer, nullable=False, default=0, server_default="0")

    last_review = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    card = relationship("Flashcard", back_populates="review_states")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "card_id",
            "user_id",
            name="uq_flashcard_review_state_card_user",
        ),
        Index("ix_flashcard_review_states_user_due", "user_id", "due"),
        Index("ix_flashcard_review_states_user_state", "user_id", "state"),
    )


class FlashcardStudySession(Base):
    __tablename__ = "flashcard_study_sessions"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    deck_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("flashcard_decks.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # active | completed | abandoned
    status = Column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    new_cards_count = Column(Integer, nullable=False, default=0, server_default="0")
    review_cards_count = Column(Integer, nullable=False, default=0, server_default="0")
    reviewed_count = Column(Integer, nullable=False, default=0, server_default="0")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deck = relationship("FlashcardDeck", back_populates="study_sessions")
    user = relationship("User")

    session_cards = relationship(
        "FlashcardSessionCard",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="FlashcardSessionCard.queue_position",
    )

    review_logs = relationship(
        "FlashcardReviewLog",
        back_populates="session",
    )

    __table_args__ = (
        Index(
            "ix_flashcard_sessions_user_deck_status",
            "user_id",
            "deck_id",
            "status",
        ),
    )


class FlashcardSessionCard(Base):
    __tablename__ = "flashcard_session_cards"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    session_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("flashcard_study_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    card_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("flashcards.id", ondelete="CASCADE"),
        nullable=False,
    )

    # new | learning | review | relearning
    queue_type = Column(String(20), nullable=False)

    queue_position = Column(Integer, nullable=False)

    # A card may stay in the same session but become temporarily unavailable
    # after Again/Hard until the scheduler's learning delay has elapsed.
    available_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    review_count = Column(Integer, nullable=False, default=0, server_default="0")
    completed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session = relationship("FlashcardStudySession", back_populates="session_cards")
    card = relationship("Flashcard", back_populates="session_cards")

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "card_id",
            name="uq_flashcard_session_card",
        ),
        Index(
            "ix_flashcard_session_queue",
            "session_id",
            "completed",
            "available_at",
            "queue_position",
        ),
    )


class FlashcardReviewLog(Base):
    __tablename__ = "flashcard_review_logs"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    card_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("flashcards.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    session_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("flashcard_study_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # again | hard | good | easy
    rating = Column(String(10), nullable=False)

    state_before = Column(String(20), nullable=False)
    state_after = Column(String(20), nullable=False)

    due_before = Column(DateTime(timezone=True), nullable=True)
    due_after = Column(DateTime(timezone=True), nullable=True)

    stability_before = Column(Float, nullable=True)
    stability_after = Column(Float, nullable=True)

    difficulty_before = Column(Float, nullable=True)
    difficulty_after = Column(Float, nullable=True)

    scheduled_days = Column(Integer, nullable=False, default=0, server_default="0")
    elapsed_days = Column(Integer, nullable=False, default=0, server_default="0")

    reviewed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    response_time_ms = Column(Integer, nullable=True)

    card = relationship("Flashcard", back_populates="review_logs")
    user = relationship("User")
    session = relationship("FlashcardStudySession", back_populates="review_logs")

    __table_args__ = (
        Index(
            "ix_flashcard_review_logs_user_reviewed",
            "user_id",
            "reviewed_at",
        ),
        Index(
            "ix_flashcard_review_logs_card_user_reviewed",
            "card_id",
            "user_id",
            "reviewed_at",
        ),
    )
