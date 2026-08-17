from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.conversation_model import Conversation, Message
from app.models.document_model import Document
from app.models.notebook_model import Notebook
from app.models.quiz_model import Quiz, QuizAttempt, QuizProgress, QuizQuestion
from app.models.user_activity_model import UserDailyActivity
from app.schemas.dashboard_schema import (
    ActivityPointOut,
    AggregateLearningStatsOut,
    DashboardAnalyticsOut,
    DashboardCandidateStatsOut,
    DashboardStatsOut,
    LearningCurvePointOut,
    QuestionTypeHighlightOut,
    QuestionTypeStatsOut,
    TrendStatOut,
    WeeklyActivityChangeOut,
)


class DashboardService:
    ACTIVITY_HISTORY_DAYS = 365

    def __init__(self, db: Session):
        self.db = db

    def get_stats(self, current_user) -> DashboardStatsOut:
        notebook_count = (
            self.db.query(Notebook).filter(Notebook.user_id == current_user.id).count()
        )

        document_count = (
            self.db.query(Document).filter(Document.user_id == current_user.id).count()
        )

        quiz_count = self.db.query(Quiz).filter(Quiz.user_id == current_user.id).count()

        message_count = (
            self.db.query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                Conversation.user_id == current_user.id,
                Message.sender == "user",
            )
            .count()
        )

        return DashboardStatsOut(
            notebook_count=notebook_count,
            document_count=document_count,
            quiz_count=quiz_count,
            message_count=message_count,
        )

    def get_analytics(
        self, current_user, days: int = ACTIVITY_HISTORY_DAYS
    ) -> DashboardAnalyticsOut:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)

        quiz_timestamps = (
            self.db.query(QuizAttempt.created_at)
            .filter(QuizAttempt.user_id == current_user.id)
            .all()
        )
        message_timestamps = (
            self.db.query(Message.created_at)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                Conversation.user_id == current_user.id,
                Message.sender == "user",
            )
            .all()
        )

        activity_rows = (
            self.db.query(
                UserDailyActivity.activity_date,
                UserDailyActivity.active_seconds,
            )
            .filter(
                UserDailyActivity.user_id == current_user.id,
                UserDailyActivity.activity_date >= start_date,
                UserDailyActivity.activity_date <= end_date,
            )
            .all()
        )
        activity = self._build_activity_series(activity_rows, start_date, days)

        correct_count = func.sum(
            case((QuizProgress.is_correct.is_(True), 1), else_=0)
        ).label("correct_count")
        attempt_rows = (
            self.db.query(
                QuizAttempt.id,
                QuizAttempt.started_at,
                QuizAttempt.submitted_at,
                QuizAttempt.duration_seconds,
                Quiz.total_questions,
                correct_count,
            )
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .outerjoin(QuizProgress, QuizProgress.attempt_id == QuizAttempt.id)
            .filter(
                QuizAttempt.user_id == current_user.id,
                QuizAttempt.attempt_status == "completed",
            )
            .group_by(
                QuizAttempt.id,
                QuizAttempt.started_at,
                QuizAttempt.submitted_at,
                QuizAttempt.duration_seconds,
                Quiz.total_questions,
            )
            .order_by(QuizAttempt.started_at.asc(), QuizAttempt.id.asc())
            .all()
        )
        learning_curve = [
            LearningCurvePointOut(
                attempt=index,
                accuracy=round((row.correct_count or 0) / row.total_questions * 100, 1),
            )
            for index, row in enumerate(attempt_rows, start=1)
            if row.total_questions > 0
        ]

        type_rows = (
            self.db.query(
                QuizQuestion.question_type,
                func.count(QuizProgress.id).label("answered_count"),
                func.sum(case((QuizProgress.is_correct.is_(True), 1), else_=0)).label(
                    "correct_count"
                ),
            )
            .join(QuizProgress, QuizProgress.question_id == QuizQuestion.id)
            .join(QuizAttempt, QuizAttempt.id == QuizProgress.attempt_id)
            .filter(
                QuizAttempt.user_id == current_user.id,
                QuizAttempt.attempt_status == "completed",
            )
            .group_by(QuizQuestion.question_type)
            .order_by(QuizQuestion.question_type.asc())
            .all()
        )
        question_types = [
            QuestionTypeStatsOut(
                question_type=row.question_type,
                answered_count=row.answered_count,
                correct_count=row.correct_count or 0,
                accuracy=round((row.correct_count or 0) / row.answered_count * 100, 1),
            )
            for row in type_rows
            if row.answered_count > 0
        ]

        total_questions = sum(row.total_questions for row in attempt_rows if row.total_questions > 0)
        total_correct = sum(row.correct_count or 0 for row in attempt_rows)
        total_active_seconds = (
            self.db.query(func.coalesce(func.sum(UserDailyActivity.active_seconds), 0))
            .filter(UserDailyActivity.user_id == current_user.id)
            .scalar()
        )
        aggregate = AggregateLearningStatsOut(
            completed_attempts=len(attempt_rows),
            overall_accuracy=(
                round(total_correct / total_questions * 100, 1) if total_questions else None
            ),
            total_study_seconds=int(total_active_seconds or 0),
        )
        candidates = self._build_candidate_stats(
            attempt_rows,
            question_types,
            [row[0] for row in quiz_timestamps],
            [row[0] for row in message_timestamps],
            end_date,
        )

        return DashboardAnalyticsOut(
            activity=activity,
            learning_curve=learning_curve,
            aggregate=aggregate,
            question_types=question_types,
            candidates=candidates,
        )

    @staticmethod
    def _build_candidate_stats(
        attempt_rows,
        question_types: list[QuestionTypeStatsOut],
        quiz_timestamps: list[datetime],
        message_timestamps: list[datetime],
        today: date,
        trend_size: int = 5,
    ) -> DashboardCandidateStatsOut:
        dated_activity = [*quiz_timestamps, *message_timestamps]
        active_dates = {timestamp.date() for timestamp in dated_activity}
        streak = 0
        cursor = today
        while cursor in active_dates:
            streak += 1
            cursor -= timedelta(days=1)

        valid_attempts = [row for row in attempt_rows if row.total_questions > 0]
        accuracy_values = [
            float(row.correct_count or 0) / row.total_questions * 100
            for row in valid_attempts
        ]
        time_values = [
            row.duration_seconds / row.total_questions
            for row in valid_attempts
            if row.duration_seconds is not None
        ]

        accuracy_trend = DashboardService._compare_windows(accuracy_values, trend_size)
        time_trend = DashboardService._compare_windows(time_values, trend_size)

        ranked_types = sorted(
            question_types,
            key=lambda item: (item.accuracy, item.answered_count, item.question_type),
        )
        worst = ranked_types[0] if ranked_types else None
        best = ranked_types[-1] if ranked_types else None

        current_start = today - timedelta(days=6)
        previous_start = current_start - timedelta(days=7)
        current_count = sum(current_start <= timestamp.date() <= today for timestamp in dated_activity)
        previous_count = sum(
            previous_start <= timestamp.date() < current_start for timestamp in dated_activity
        )
        weekly_change = (
            round((current_count - previous_count) / previous_count * 100, 1)
            if previous_count
            else None
        )

        return DashboardCandidateStatsOut(
            current_streak_days=streak,
            accuracy_trend=accuracy_trend,
            time_spent_trend=time_trend,
            best_question_type=(
                QuestionTypeHighlightOut(
                    question_type=best.question_type,
                    accuracy=best.accuracy,
                    answered_count=best.answered_count,
                )
                if best
                else None
            ),
            worst_question_type=(
                QuestionTypeHighlightOut(
                    question_type=worst.question_type,
                    accuracy=worst.accuracy,
                    answered_count=worst.answered_count,
                )
                if worst
                else None
            ),
            weekly_activity_change=WeeklyActivityChangeOut(
                current_count=current_count,
                previous_count=previous_count,
                percent_change=weekly_change,
            ),
        )

    @staticmethod
    def _compare_windows(values: list[float], size: int) -> TrendStatOut | None:
        if len(values) < size * 2:
            return None
        recent = values[-size:]
        previous = values[-size * 2 : -size]
        recent_average = sum(recent) / size
        previous_average = sum(previous) / size
        return TrendStatOut(
            recent_value=round(recent_average, 1),
            previous_value=round(previous_average, 1),
            delta=round(recent_average - previous_average, 1),
            sample_size=size,
        )

    @staticmethod
    def _build_activity_series(
        activity_rows,
        start_date: date,
        days: int,
    ) -> list[ActivityPointOut]:
        seconds_by_date = {row.activity_date: int(row.active_seconds or 0) for row in activity_rows}
        return [
            ActivityPointOut(
                date=start_date + timedelta(days=offset),
                study_seconds=seconds_by_date.get(start_date + timedelta(days=offset), 0),
            )
            for offset in range(days)
        ]
