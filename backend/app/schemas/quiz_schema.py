from typing import Any, List, Optional

from pydantic import BaseModel


class QuizGenerateRequest(BaseModel):
    document_id: int
    question_types: List[str]
    total_questions: int
    level: str
    mode: str = "study"
    time_limit_minutes: Optional[int] = None


class QuizAnswerRequest(BaseModel):
    user_answer: Any


class QuizSubmitRequest(BaseModel):
    submit_reason: str  # "manual", "timeout", "disconnected", "tab_switch_violation"
