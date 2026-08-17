import pytest
from pydantic import ValidationError
from unittest.mock import patch

from app.exceptions.quiz import InvalidQuizOperationError, QuizNotFoundError
from app.models.quiz_model import QuizProgress, QuizQuestion
from app.schemas.quiz_schema import QuizSubmitRequest
from app.services.quiz.quiz_service import QuizService


class FakeQuiz:
    def __init__(self, id=1, user_id=1, mode="study", notebook_id=1):
        self.id = id
        self.user_id = user_id
        self.mode = mode
        self.notebook_id = notebook_id


class FakeQuery:
    """Giả lập chuỗi .query(Model).filter(...).first()/.all() của SQLAlchemy.
    Không quan tâm điều kiện filter thật sự — chỉ trả về kết quả đã set sẵn."""

    def __init__(self, result):
        self._result = result

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._result if isinstance(self._result, list) else []


class FakeSession:
    def __init__(self, quiz_result=None):
        self._quiz_result = quiz_result

    def query(self, _model):
        return FakeQuery(self._quiz_result)


class DeleteSession(FakeSession):
    def __init__(self, quiz_result=None):
        super().__init__(quiz_result)
        self.deleted = None
        self.committed = False

    def delete(self, value):
        self.deleted = value

    def commit(self):
        self.committed = True


class DummyPipeline:
    pass


class CountQuery:
    def __init__(self, count):
        self._count = count

    def filter(self, *_args, **_kwargs):
        return self

    def count(self):
        return self._count


class CountSession:
    def __init__(self, answered_count, question_count):
        self.answered_count = answered_count
        self.question_count = question_count

    def query(self, model):
        if model is QuizProgress:
            return CountQuery(self.answered_count)
        if model is QuizQuestion:
            return CountQuery(self.question_count)
        raise AssertionError(f"Unexpected model: {model}")


def test_get_quiz_for_rendering_rejects_wrong_owner():
    # Quiz thuộc user_id=1, nhưng user_id=2 đang cố truy cập
    quiz_owned_by_user_1 = FakeQuiz(id=1, user_id=1)
    service = QuizService(FakeSession(quiz_owned_by_user_1), DummyPipeline())

    with pytest.raises(QuizNotFoundError):
        service.get_quiz_for_rendering(quiz_id=1, user_id=2)


def test_get_quiz_for_rendering_not_found_when_quiz_missing():
    service = QuizService(FakeSession(quiz_result=None), DummyPipeline())

    with pytest.raises(QuizNotFoundError):
        service.get_quiz_for_rendering(quiz_id=999, user_id=1)


def test_get_quiz_for_rendering_includes_source_document_snapshot():
    quiz = FakeQuiz(id=1, user_id=1)
    quiz.title = "Source-aware quiz"
    quiz.time_limit_minutes = None
    quiz.target_total_points = 100
    quiz.generation_status = "completed"
    quiz.error_message = None
    quiz.source_document_ids = [3, 7]
    service = QuizService(FakeSession(quiz), DummyPipeline())
    service._get_ordered_questions = lambda *_args: []

    result = service.get_quiz_for_rendering(quiz_id=1, user_id=1)

    assert result["notebook_id"] == 1
    assert result["source_document_ids"] == [3, 7]


def test_save_single_answer_rejects_exam_mode():
    # Quiz mode="exam" không được phép gọi /answer từng câu
    quiz_exam_mode = FakeQuiz(id=1, user_id=1, mode="exam")
    service = QuizService(FakeSession(quiz_exam_mode), DummyPipeline())

    with pytest.raises(InvalidQuizOperationError):
        service.save_single_answer_progress(
            quiz_id=1, question_id=1, user_id=1, user_answer="A"
        )


def test_submit_entire_quiz_rejects_study_mode():
    # Quiz mode="study" không được phép gọi /submit tổng hợp
    quiz_study_mode = FakeQuiz(id=1, user_id=1, mode="study")
    service = QuizService(FakeSession(quiz_study_mode), DummyPipeline())

    with pytest.raises(InvalidQuizOperationError):
        service.submit_entire_quiz(
            quiz_id=1, user_id=1, answers_payload=[], submit_reason="manual"
        )


def test_exam_submission_accepts_persisted_question_marks():
    request = QuizSubmitRequest(
        answers=[
            {"question_id": 1, "user_answer": "A", "mark_status": "review"},
            {"question_id": 2, "user_answer": "B", "mark_status": "critical"},
        ]
    )

    assert request.answers[0].mark_status == "review"
    assert request.answers[1].mark_status == "critical"

    with pytest.raises(ValidationError):
        QuizSubmitRequest(
            answers=[
                {"question_id": 1, "user_answer": "A", "mark_status": "other"}
            ]
        )


def test_study_attempt_completes_only_after_all_questions_are_answered():
    session = CountSession(answered_count=1, question_count=2)
    service = QuizService(session, DummyPipeline())
    attempt = type(
        "Attempt",
        (),
        {"id": 1, "attempt_status": "in_progress", "submitted_at": None},
    )()

    assert service._complete_study_attempt_if_ready(quiz_id=1, attempt=attempt) is False
    assert attempt.attempt_status == "in_progress"

    session.answered_count = 2

    assert service._complete_study_attempt_if_ready(quiz_id=1, attempt=attempt) is True
    assert attempt.attempt_status == "completed"
    assert attempt.submitted_at is not None


def test_question_order_is_a_permutation_and_differs_from_previous_attempt():
    question_ids = [1, 2, 3, 4]

    with patch(
        "app.services.quiz.quiz_service.random.shuffle",
        side_effect=lambda values: None,
    ):
        question_order = QuizService._shuffle_question_order(
            question_ids,
            previous_question_order=question_ids,
        )

    assert sorted(question_order) == question_ids
    assert question_order != question_ids


def test_delete_quiz_checks_ownership_and_commits():
    quiz = FakeQuiz(id=1, user_id=1)
    session = DeleteSession(quiz)
    service = QuizService(session, DummyPipeline())

    service.delete_quiz(quiz_id=1, user_id=1)

    assert session.deleted is quiz
    assert session.committed is True


def test_delete_quiz_rejects_wrong_owner():
    service = QuizService(DeleteSession(FakeQuiz(id=1, user_id=2)), DummyPipeline())

    with pytest.raises(QuizNotFoundError):
        service.delete_quiz(quiz_id=1, user_id=1)
