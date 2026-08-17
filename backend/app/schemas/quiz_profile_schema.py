from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DifficultyRating(str, Enum):
    """
    Rating sao độ khó user chọn trong popup feedback.
    Phải khớp đúng key trong DIFFICULTY_RATING_DELTAS
    (app/core/constants/quiz_profile.py) — đổi 1 bên phải đổi bên kia.
    """

    TOO_EASY = "too_easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    TOO_HARD = "too_hard"


class FeedbackTag(str, Enum):
    """
    Tag preset (checkbox, chọn được nhiều cái) trong popup feedback.
    Phải khớp đúng key trong PRESET_TAG_DELTAS
    (app/core/constants/quiz_profile.py) — đổi 1 bên phải đổi bên kia.
    """

    TOO_HARD = "too_hard"
    TOO_EASY = "too_easy"
    REPETITIVE = "repetitive"
    NOT_RELEVANT = "not_relevant"
    TOO_SHALLOW = "too_shallow"
    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"
    NOT_ENOUGH_SOURCE_COVERAGE = "not_enough_source_coverage"
    HALLUCINATED = "hallucinated"


class FeedbackIn(BaseModel):
    """
    Payload FE gửi lên sau khi user hoàn thành popup feedback 1 quiz attempt.

    - difficulty + tags: xử lý bởi preset_feedback_mapper (không AI).
    - comment: chỉ khi khác None/rỗng thì feedback_analyzer_ai_service
      mới được gọi (xem feedback_service.py để orchestrate).
    """

    tags: List[FeedbackTag] = Field(default_factory=list)
    comment: Optional[str] = Field(default=None, max_length=1000)


class MergedQuizProfileOut(BaseModel):
    """
    Quiz profile cuối cùng (DEFAULT_QUIZ_PROFILE + personal offset, đã
    clamp theo QUIZ_PROFILE_BOUNDS) — output của
    personal_offset_service.get_merged_profile(), input cho
    QuizPromptBuilder.

    Field set phải khớp:
    - DEFAULT_QUIZ_PROFILE
    - QuizProfileOffset model
    - QUIZ_PROFILE_FIELDS
    app/core/constants/quiz_profile.py.
    """

    difficulty: float
    coverage: float
    reasoning_depth: float
    anti_repetition: float
    relevance: float
    time_per_question: float
    strict_source_grounding: float
