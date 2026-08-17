from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class DashboardStatsOut(BaseModel):
    notebook_count: int
    document_count: int
    quiz_count: int
    message_count: int


class ActivityPointOut(BaseModel):
    date: date
    study_seconds: int


class LearningCurvePointOut(BaseModel):
    attempt: int
    accuracy: float


class AggregateLearningStatsOut(BaseModel):
    completed_attempts: int
    overall_accuracy: float | None
    total_study_seconds: int


class QuestionTypeStatsOut(BaseModel):
    question_type: str
    answered_count: int
    correct_count: int
    accuracy: float


class TrendStatOut(BaseModel):
    recent_value: float
    previous_value: float
    delta: float
    sample_size: int


class QuestionTypeHighlightOut(BaseModel):
    question_type: str
    accuracy: float
    answered_count: int


class WeeklyActivityChangeOut(BaseModel):
    current_count: int
    previous_count: int
    percent_change: float | None


class DashboardCandidateStatsOut(BaseModel):
    current_streak_days: int
    accuracy_trend: TrendStatOut | None
    time_spent_trend: TrendStatOut | None
    best_question_type: QuestionTypeHighlightOut | None
    worst_question_type: QuestionTypeHighlightOut | None
    weekly_activity_change: WeeklyActivityChangeOut


class DashboardAnalyticsOut(BaseModel):
    activity: list[ActivityPointOut]
    learning_curve: list[LearningCurvePointOut]
    aggregate: AggregateLearningStatsOut
    question_types: list[QuestionTypeStatsOut]
    candidates: DashboardCandidateStatsOut


class InsightStatOut(BaseModel):
    key: str
    label: str
    value: str


class DashboardInsightOut(BaseModel):
    text: str
    selected_stats: list[InsightStatOut]
    has_meaningful_data: bool
    cached: bool = False
    generated_at: datetime | None = None
    refresh_available_at: datetime | None = None


class DashboardInsightLLMOutput(BaseModel):
    text: str
    selected_keys: list[str]


class CandidateStatForPrompt(BaseModel):
    key: str
    label: str
    value: str
    context: dict[str, Any]
