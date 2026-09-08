from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FlashcardRating = Literal["again", "hard", "good", "easy"]
FlashcardLearningState = Literal["new", "learning", "review", "relearning"]
FlashcardGenerationStatus = Literal["manual", "processing", "completed", "failed"]
FlashcardSessionStatus = Literal["active", "completed", "abandoned"]


# ---------------------------------------------------------------------------
# Deck requests
# ---------------------------------------------------------------------------


class FlashcardDeckCreate(BaseModel):
    notebook_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Deck title must not be empty.")
        return title


class FlashcardDeckUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("Deck title must not be empty.")
        return title


class FlashcardDeckGenerate(BaseModel):
    notebook_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    total_cards: int = Field(default=20, ge=1, le=100)
    custom_instruction: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Deck title must not be empty.")
        return title


# ---------------------------------------------------------------------------
# Card requests
# ---------------------------------------------------------------------------


class FlashcardCreate(BaseModel):
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)

    source_document_id: int | None = None
    source_chunk_id: str | None = Field(default=None, max_length=255)
    source_metadata: dict | None = None

    position: int | None = Field(default=None, ge=0)

    @field_validator("front", "back")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Flashcard front/back must not be empty.")
        return text


class FlashcardUpdate(BaseModel):
    front: str | None = Field(default=None, min_length=1)
    back: str | None = Field(default=None, min_length=1)

    position: int | None = Field(default=None, ge=0)

    @field_validator("front", "back")
    @classmethod
    def normalize_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("Flashcard front/back must not be empty.")
        return text


# ---------------------------------------------------------------------------
# Study / review requests
# ---------------------------------------------------------------------------


class FlashcardStudySessionCreate(BaseModel):
    """Optional limits are intentionally simple.

    They let the backend construct a deterministic study session while leaving
    room for frontend study preferences later without coupling scheduling logic
    to the UI.
    """

    new_card_limit: int | None = Field(default=None, ge=0, le=500)
    review_card_limit: int | None = Field(default=None, ge=0, le=2000)


class FlashcardReviewRequest(BaseModel):
    card_id: int
    rating: FlashcardRating
    response_time_ms: int | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Common response models
# ---------------------------------------------------------------------------


class FlashcardOut(BaseModel):
    id: int
    deck_id: int

    front: str
    back: str
    source_document_id: int | None = None
    source_chunk_id: str | None = None
    source_metadata: dict | None = None

    position: int
    is_suspended: bool

    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FlashcardDeckListItemOut(BaseModel):
    id: int
    notebook_id: int
    user_id: int

    title: str
    description: str | None = None

    generation_status: FlashcardGenerationStatus
    source_document_ids: list[int] = Field(default_factory=list)

    card_count: int = 0
    suspended_card_count: int = 0

    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FlashcardDeckDetailOut(FlashcardDeckListItemOut):
    cards: list[FlashcardOut] = Field(default_factory=list)


class FlashcardNotebookAnalyticsOut(BaseModel):
    notebook_id: int
    deck_count: int
    card_count: int
    total_reviews: int
    rating_counts: dict[FlashcardRating, int]
    success_rate: float
    total_review_time_ms: int
    average_review_time_ms: float


class FlashcardReviewStateOut(BaseModel):
    card_id: int
    user_id: int

    state: FlashcardLearningState
    due: datetime | None = None

    stability: float | None = None
    difficulty: float | None = None
    step: int | None = None

    elapsed_days: int
    scheduled_days: int
    reps: int
    lapses: int

    last_review: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FlashcardStudyOverviewOut(BaseModel):
    deck_id: int
    total_cards: int

    new_count: int
    learning_count: int
    review_due_count: int
    relearning_count: int

    suspended_count: int

    # Convenience total for the main "Study" CTA.
    due_now_count: int


class FlashcardSessionCardOut(BaseModel):
    card_id: int
    queue_type: FlashcardLearningState
    queue_position: int

    available_at: datetime
    review_count: int
    completed: bool

    card: FlashcardOut

    model_config = ConfigDict(from_attributes=True)


class FlashcardStudySessionOut(BaseModel):
    id: int
    deck_id: int
    user_id: int

    status: FlashcardSessionStatus

    started_at: datetime
    completed_at: datetime | None = None

    new_cards_count: int
    review_cards_count: int
    reviewed_count: int

    current_card: FlashcardSessionCardOut | None = None

    remaining_new: int = 0
    remaining_learning: int = 0
    remaining_review: int = 0
    remaining_relearning: int = 0

    # If no card is available right now but one is waiting for a learning delay,
    # the frontend can show a countdown rather than treating the session as done.
    next_available_at: datetime | None = None


class FlashcardReviewResultOut(BaseModel):
    reviewed_card_id: int
    rating: FlashcardRating

    state_before: FlashcardLearningState
    state_after: FlashcardLearningState

    next_due: datetime | None = None

    current_card: FlashcardSessionCardOut | None = None
    next_available_at: datetime | None = None

    remaining_new: int = 0
    remaining_learning: int = 0
    remaining_review: int = 0
    remaining_relearning: int = 0

    session_completed: bool = False


class FlashcardReviewLogOut(BaseModel):
    id: int
    card_id: int
    user_id: int
    session_id: int | None = None

    rating: FlashcardRating

    state_before: FlashcardLearningState
    state_after: FlashcardLearningState

    due_before: datetime | None = None
    due_after: datetime | None = None

    stability_before: float | None = None
    stability_after: float | None = None

    difficulty_before: float | None = None
    difficulty_after: float | None = None

    scheduled_days: int
    elapsed_days: int

    reviewed_at: datetime
    response_time_ms: int | None = None

    model_config = ConfigDict(from_attributes=True)
