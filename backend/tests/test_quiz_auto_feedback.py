from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.quizzes import submit_quiz_feedback
from app.models.quiz_model import Quiz, QuizAttempt, QuizProgress, QuizQuestion
from app.schemas.quiz_profile_schema import FeedbackIn
from app.services.quiz.quiz_service import QuizService


class FakeQuery:
    def __init__(self, *, first=None, all_results=None):
        self.first_result = first
        self.all_results = all_results or []

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def first(self):
        return self.first_result

    def all(self):
        return self.all_results


class CompletionSession:
    def __init__(self, quiz, question, attempt, *, exam=False):
        self.quiz = quiz
        self.question = question
        self.attempt = attempt
        self.exam = exam
        self.added = []
        self.committed = False

    def query(self, model):
        if model is Quiz:
            return FakeQuery(first=self.quiz)
        if model is QuizQuestion:
            return FakeQuery(
                first=self.question,
                all_results=[self.question] if self.exam else [],
            )
        if model is QuizAttempt:
            return FakeQuery(first=self.attempt)
        if model is QuizProgress:
            return FakeQuery(first=None)
        raise AssertionError(f"Unexpected model: {model}")

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None

    def commit(self):
        self.committed = True


def make_quiz(mode="study", status="pending"):
    return SimpleNamespace(
        id=1,
        user_id=7,
        mode=mode,
        auto_feedback_status=status,
        target_total_points=Decimal("10.00"),
    )


def make_question():
    return SimpleNamespace(
        id=11,
        question_type="multiple_choice",
        correct_answer="A",
        explanations=None,
        statements=None,
        points=Decimal("10.00"),
    )


def make_attempt(status="in_progress"):
    return SimpleNamespace(
        id=21,
        attempt_status=status,
        submitted_at=None,
        submit_reason=None,
        started_at=datetime.now(timezone.utc),
        duration_seconds=None,
        score=None,
    )


def run_study_completion(random_value, *, completion=True, status="pending"):
    quiz = make_quiz(status=status)
    attempt = make_attempt()
    session = CompletionSession(quiz, make_question(), attempt)
    service = QuizService(session, SimpleNamespace())

    def complete(*_args):
        if completion:
            attempt.attempt_status = "completed"
        return completion

    service._complete_study_attempt_if_ready = complete
    with patch(
        "app.services.quiz.quiz_service.random.random", return_value=random_value
    ) as random_mock:
        result = service.save_single_answer_progress(1, 11, 7, "A")
    return result, quiz, random_mock, session


def run_exam_completion(random_value, *, status="pending"):
    quiz = make_quiz(mode="exam", status=status)
    attempt = make_attempt()
    session = CompletionSession(quiz, make_question(), attempt, exam=True)
    service = QuizService(session, SimpleNamespace())
    with patch(
        "app.services.quiz.quiz_service.random.random", return_value=random_value
    ) as random_mock:
        result = service.submit_entire_quiz(
            1,
            7,
            [{"question_id": 11, "user_answer": "A"}],
            "manual",
        )
    return result, quiz, random_mock, session


def test_first_study_completion_selected():
    result, quiz, random_mock, session = run_study_completion(0.1)
    assert result["show_auto_feedback"] is True
    assert quiz.auto_feedback_status == "shown"
    random_mock.assert_called_once_with()
    assert session.committed is True


def test_first_study_completion_skipped():
    result, quiz, random_mock, _ = run_study_completion(0.35)
    assert result["show_auto_feedback"] is False
    assert quiz.auto_feedback_status == "skipped"
    random_mock.assert_called_once_with()


@pytest.mark.parametrize("status", ["shown", "skipped"])
def test_later_study_completion_does_not_resample(status):
    result, quiz, random_mock, _ = run_study_completion(0.1, status=status)
    assert result["show_auto_feedback"] is False
    assert quiz.auto_feedback_status == status
    random_mock.assert_not_called()


def test_study_non_final_question_stays_pending():
    result, quiz, random_mock, _ = run_study_completion(0.1, completion=False)
    assert result["show_auto_feedback"] is False
    assert quiz.auto_feedback_status == "pending"
    random_mock.assert_not_called()


def test_first_exam_completion_selected():
    result, quiz, random_mock, session = run_exam_completion(0.1)
    assert result["show_auto_feedback"] is True
    assert quiz.auto_feedback_status == "shown"
    random_mock.assert_called_once_with()
    assert session.committed is True


def test_first_exam_completion_skipped():
    result, quiz, random_mock, _ = run_exam_completion(0.8)
    assert result["show_auto_feedback"] is False
    assert quiz.auto_feedback_status == "skipped"
    random_mock.assert_called_once_with()


@pytest.mark.parametrize("status", ["shown", "skipped"])
def test_later_exam_attempt_does_not_resample(status):
    result, quiz, random_mock, _ = run_exam_completion(0.1, status=status)
    assert result["show_auto_feedback"] is False
    assert quiz.auto_feedback_status == status
    random_mock.assert_not_called()


def test_migration_backfills_completed_quizzes_as_skipped(monkeypatch):
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "d4e7a92b1c6f_add_quiz_auto_feedback_status.py"
    )
    spec = importlib.util.spec_from_file_location("quiz_auto_feedback_migration", migration_path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements = []
    monkeypatch.setattr(migration.op, "add_column", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    sql = str(statements[0]).lower()
    assert "auto_feedback_status = 'skipped'" in sql
    assert "quiz_attempts.attempt_status = 'completed'" in sql


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "shown", "skipped"])
async def test_manual_feedback_remains_independent(status):
    feedback_service = SimpleNamespace(
        apply_feedback=AsyncMock(return_value={"difficulty": 0.0})
    )
    feedback = FeedbackIn(tags=["too_hard"])

    response = await submit_quiz_feedback(
        feedback=feedback,
        current_user=SimpleNamespace(id=7, auto_feedback_status=status),
        feedback_service=feedback_service,
    )

    feedback_service.apply_feedback.assert_awaited_once_with(
        user_id=7,
        feedback=feedback,
    )
    assert response.data["difficulty"] == 0.0
