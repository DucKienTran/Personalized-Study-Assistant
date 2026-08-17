from collections import namedtuple
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.schemas.dashboard_schema import QuestionTypeStatsOut
from app.services.dashboard.dashboard_service import DashboardService


class QueryResult:
    def __init__(self, rows):
        self.rows = rows

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: self

    def all(self):
        return self.rows


class QueuedDB:
    def __init__(self, results):
        self.results = iter(results)

    def query(self, *_args):
        return QueryResult(next(self.results))


def test_activity_series_groups_by_day_and_includes_zero_days():
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)

    points = DashboardService._build_activity_series(
        [start, start + timedelta(hours=3), start + timedelta(days=2)],
        [start + timedelta(days=1, hours=4)],
        start.date(),
        4,
    )

    assert [(point.quiz_attempts, point.messages) for point in points] == [
        (2, 0),
        (0, 1),
        (1, 0),
        (0, 0),
    ]


def test_get_analytics_calculates_accuracy_in_chronological_attempt_order():
    now = datetime.now(timezone.utc)
    AttemptRow = namedtuple(
        "AttemptRow",
        [
            "id",
            "started_at",
            "submitted_at",
            "duration_seconds",
            "total_questions",
            "correct_count",
        ],
    )
    TypeRow = namedtuple(
        "TypeRow", ["question_type", "answered_count", "correct_count"]
    )
    db = QueuedDB(
        [
            [(now,)],
            [(now,), (now,)],
            [
                AttemptRow(7, now - timedelta(days=1), now, 300, 10, 6),
                AttemptRow(8, now, now, 240, 8, 7),
            ],
            [TypeRow("multiple_choice", 18, 13)],
        ]
    )

    analytics = DashboardService(db).get_analytics(SimpleNamespace(id=42))

    assert len(analytics.activity) == DashboardService.ACTIVITY_HISTORY_DAYS
    assert analytics.activity[-1].quiz_attempts == 1
    assert analytics.activity[-1].messages == 2
    assert [(point.attempt, point.accuracy) for point in analytics.learning_curve] == [
        (1, 60.0),
        (2, 87.5),
    ]
    assert analytics.aggregate.completed_attempts == 2
    assert analytics.aggregate.overall_accuracy == 72.2
    assert analytics.aggregate.total_study_seconds == 540
    assert analytics.question_types[0].accuracy == 72.2


def test_candidate_stats_compare_recent_attempts_and_weekly_activity():
    today = datetime(2026, 8, 11, tzinfo=timezone.utc)
    rows = [
        SimpleNamespace(
            total_questions=10,
            correct_count=5 if index < 5 else 8,
            duration_seconds=200 if index < 5 else 150,
        )
        for index in range(10)
    ]
    question_types = [
        QuestionTypeStatsOut(
            question_type="multiple_choice",
            answered_count=20,
            correct_count=16,
            accuracy=80,
        ),
        QuestionTypeStatsOut(
            question_type="essay",
            answered_count=10,
            correct_count=5,
            accuracy=50,
        ),
    ]

    candidates = DashboardService._build_candidate_stats(
        rows,
        question_types,
        [today, today - timedelta(days=1), today - timedelta(days=8)],
        [],
        today.date(),
    )

    assert candidates.current_streak_days == 2
    assert candidates.accuracy_trend.delta == 30
    assert candidates.time_spent_trend.delta == -5
    assert candidates.best_question_type.question_type == "multiple_choice"
    assert candidates.worst_question_type.question_type == "essay"
    assert candidates.weekly_activity_change.current_count == 2
    assert candidates.weekly_activity_change.previous_count == 1
    assert candidates.weekly_activity_change.percent_change == 100
