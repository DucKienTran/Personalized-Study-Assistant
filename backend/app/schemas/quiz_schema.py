from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QuizGenerateRequest(BaseModel):
    ALLOWED_QUESTION_TYPES: ClassVar[set[str]] = {
        "multiple_choice",
        "multiple_response",
        "true_false",
        "fill_blank",
        "short_answer",
        "essay",
    }
    notebook_id: int

    mode: Literal["study", "exam"]

    generation_strategy: Literal[
        "manual",
        "ai_recommended",
    ] = "manual"

    total_questions: int = Field(default=10, ge=1, le=50)

    question_types: list[str] = Field(
        default_factory=lambda: ["multiple_choice"]
    )

    difficulty_distribution: dict[str, float] | None = None

    custom_instruction: str | None = None

    target_total_points: Decimal = Field(
        default=Decimal("100.00"),
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    # Bắt buộc nếu mode="exam"
    time_limit_minutes: int | None = None

    @field_validator("target_total_points", mode="before")
    @classmethod
    def default_target_total_points(cls, value):
        return Decimal("100.00") if value is None else value

    @field_validator("question_types")
    @classmethod
    def validate_question_types(cls, value: list[str]) -> list[str]:
        unique_types = list(dict.fromkeys(value))
        if not unique_types:
            raise ValueError("At least one question type is required.")
        invalid = set(unique_types) - cls.ALLOWED_QUESTION_TYPES
        if invalid:
            raise ValueError(f"Unsupported question types: {sorted(invalid)}")
        return unique_types

    @model_validator(mode="after")
    def validate_business_rules(self):
        minimum_total = Decimal("0.01") * self.total_questions
        if self.target_total_points < minimum_total:
            raise ValueError(
                "'target_total_points' must allow at least 0.01 point per question."
            )

        if self.mode == "exam":
            if self.time_limit_minutes is None:
                raise ValueError(
                    "Exam mode requires 'time_limit_minutes'."
                )

        if (
            self.generation_strategy == "manual"
            and self.difficulty_distribution is None
        ):
            raise ValueError(
                "Manual generation requires 'difficulty_distribution'."
            )

        return self


class QuizAnswerRequest(BaseModel):
    user_answer: Any


class QuizAnswerSubmission(BaseModel):
    question_id: int
    user_answer: Any
    time_spent_seconds: int | None = Field(default=None, ge=0)
    mark_status: Literal["review", "critical"] | None = None


class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswerSubmission]

    submit_reason: Literal[
        "manual",
        "timeout",
        "auto_submit",
        "abandoned",
    ] = "manual"


class QuestionHintOut(BaseModel):
    question_id: int
    hint: str | None


class QuizProcessingOut(BaseModel):
    id: int
    title: str
    notebook_title: str

    generation_strategy: Literal[
        "manual",
        "ai_recommended",
    ]

    generation_status: Literal[
        "processing",
        "completed",
        "failed",
    ]

    total_questions: int

    created_at: datetime
