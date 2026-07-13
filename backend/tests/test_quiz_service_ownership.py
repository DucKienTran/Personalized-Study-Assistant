import pytest

from app.exceptions.quiz import QuizNotFoundError, InvalidQuizOperationError
from app.services.ai.quiz_service import QuizService


class FakeQuiz:
    def __init__(self, id=1, user_id=1, mode="study"):
        self.id = id
        self.user_id = user_id
        self.mode = mode


class FakeQuery:
    """Giả lập chuỗi .query(Model).filter(...).first()/.all() của SQLAlchemy.
    Không quan tâm điều kiện filter thật sự — chỉ trả về kết quả đã set sẵn."""

    def __init__(self, result):
        self._result = result

    def filter(self, *_args, **_kwargs):
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


class DummyDocumentService:
    pass


class DummyAIClient:
    pass


def test_get_quiz_for_rendering_rejects_wrong_owner():
    # Quiz thuộc user_id=1, nhưng user_id=2 đang cố truy cập
    quiz_owned_by_user_1 = FakeQuiz(id=1, user_id=1)
    service = QuizService(
        FakeSession(quiz_owned_by_user_1), DummyDocumentService(), DummyAIClient()
    )

    with pytest.raises(QuizNotFoundError):
        service.get_quiz_for_rendering(quiz_id=1, user_id=2)


def test_get_quiz_for_rendering_not_found_when_quiz_missing():
    service = QuizService(
        FakeSession(quiz_result=None), DummyDocumentService(), DummyAIClient()
    )

    with pytest.raises(QuizNotFoundError):
        service.get_quiz_for_rendering(quiz_id=999, user_id=1)


def test_save_single_answer_rejects_exam_mode():
    # Quiz mode="exam" không được phép gọi /answer từng câu
    quiz_exam_mode = FakeQuiz(id=1, user_id=1, mode="exam")
    service = QuizService(
        FakeSession(quiz_exam_mode), DummyDocumentService(), DummyAIClient()
    )

    with pytest.raises(InvalidQuizOperationError):
        service.save_single_answer_progress(
            quiz_id=1, question_id=1, user_id=1, user_answer="A"
        )


def test_submit_entire_quiz_rejects_study_mode():
    # Quiz mode="study" không được phép gọi /submit tổng hợp
    quiz_study_mode = FakeQuiz(id=1, user_id=1, mode="study")
    service = QuizService(
        FakeSession(quiz_study_mode), DummyDocumentService(), DummyAIClient()
    )

    with pytest.raises(InvalidQuizOperationError):
        service.submit_entire_quiz(
            quiz_id=1, user_id=1, answers_payload=[], submit_reason="manual"
        )
