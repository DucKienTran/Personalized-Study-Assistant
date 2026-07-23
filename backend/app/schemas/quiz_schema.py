from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class QuizGenerateRequest(BaseModel):
    document_id: int
    mode: str  # "study" | "exam"
    generation_mode: str = "simple"  # "simple" | "custom"

    total_questions: int = Field(default=10, ge=1, le=50)
    question_types: List[str] = Field(default_factory=lambda: ["multiple_choice"])
    difficulty: Optional[str] = None  # Đặt "medium" mặc định
    custom_instruction: Optional[str] = (
        None  # chỉ có tác dụng khi generation_mode="custom"
    )

    target_total_points: Optional[float] = None
    time_limit_minutes: Optional[int] = None  # bắt buộc nếu mode="exam"

    @model_validator(mode="after")
    def validate_business_rules(self):

        if self.mode == "exam":
            if self.time_limit_minutes is None:
                raise ValueError("Mode exam bắt buộc phải có time_limit_minutes.")
            if "essay" in self.question_types:
                raise ValueError(
                    "Câu hỏi tự luận (essay) không được phép trong đề thi mode exam."
                )
        return self


class QuizAnswerRequest(BaseModel):
    user_answer: Any


class QuizSubmitRequest(BaseModel):
    answers: List[Dict[str, Any]]  # [{"question_id": 1, "user_answer": "A"}, ...]
    submit_reason: str = (
        "manual"  # "manual" | "timeout" | "disconnected" | "tab_switch_violation"
    )


class QuestionHintOut(BaseModel):  # schema list các hint của 1 Quiz
    question_id: int
    hint: str | None


class QuizProcessingOut(BaseModel):  # Schema hiển thị trạng thái tạo Quiz
    id: int
    title: str
    document_title: str
    generation_mode: str
    difficulty: str
    total_questions: int
    created_at: datetime
