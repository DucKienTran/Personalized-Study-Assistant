from decimal import Decimal

import pytest

from app.services.quiz.quiz_service import QuizService


class DummyDB:
    def query(self, *_args, **_kwargs):
        raise AssertionError("_grade_logic là pure logic, không được đụng DB")


class DummyPipeline:
    pass


def _service() -> QuizService:
    return QuizService(DummyDB(), DummyPipeline())


# ── multiple_choice ──────────────────────────────────────────────


def test_multiple_choice_correct():
    service = _service()
    assert service._grade_logic("multiple_choice", "A", "A") is True


def test_multiple_choice_case_insensitive():
    service = _service()
    assert service._grade_logic("multiple_choice", "A", "a") is True


def test_multiple_choice_wrong():
    service = _service()
    assert service._grade_logic("multiple_choice", "A", "B") is False


# ── multiple_response ────────────────────────────────────────────


def test_multiple_response_exact_match():
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], ["A", "C"]) is True


def test_multiple_response_order_does_not_matter():
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], ["C", "A"]) is True


def test_multiple_response_missing_one_answer_is_wrong():
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], ["A"]) is False


def test_multiple_response_extra_answer_is_wrong():
    service = _service()
    assert (
        service._grade_logic("multiple_response", ["A", "C"], ["A", "C", "D"]) is False
    )


def test_multiple_response_wrong_type_returns_false():
    # correct_answer là list nhưng user gửi string thay vì list -> phải False, không crash
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], "A") is False


def test_multiple_response_partial_score_subtracts_incorrect_selections():
    service = _service()
    assert service._calculate_question_score(
        "multiple_response", ["A", "C"], ["A", "B"], 4
    ) == Decimal("0.00")
    assert service._calculate_question_score(
        "multiple_response", ["A", "C"], ["A"], 4
    ) == Decimal("2.00")


def test_multiple_response_score_never_goes_below_zero():
    service = _service()
    assert service._calculate_question_score(
        "multiple_response", ["A", "C"], ["B", "D"], 4
    ) == Decimal("0.00")


# ── true_false ────────────────────────────────────────────────────


def test_true_false_boolean_match():
    service = _service()
    assert service._grade_logic("true_false", [True, False], [True, False]) is True


def test_true_false_string_variants():
    service = _service()
    assert service._grade_logic("true_false", [True, False], ["1", "false"]) is True


def test_true_false_unparseable_user_value_returns_false():
    service = _service()
    assert service._grade_logic("true_false", [True], ["khong_ro"]) is False


def test_true_false_awards_each_correct_statement_without_deduction():
    service = _service()
    assert service._calculate_question_score(
        "true_false", [True, False, True, False], [True, True, True, True], 8
    ) == Decimal("4.00")


# ── fill_blank ────────────────────────────────────────────────────


def test_fill_blank_matches_any_acceptable_answer():
    service = _service()
    acceptable = ["Hà Nội", "thủ đô Hà Nội"]
    assert service._grade_logic("fill_blank", acceptable, "Hà Nội") is True
    assert service._grade_logic("fill_blank", acceptable, "thủ đô Hà Nội") is True


def test_fill_blank_case_and_whitespace_insensitive():
    service = _service()
    assert service._grade_logic("fill_blank", ["Hà Nội"], "  hà nội  ") is True


def test_fill_blank_no_match():
    service = _service()
    assert service._grade_logic("fill_blank", ["Hà Nội"], "Hồ Chí Minh") is False


def test_fill_blank_does_not_split_comma_inside_single_answer():
    # correct_answer chỉ có 1 đáp án chứa dấu phẩy -> KHÔNG được tách thành 2 đáp án riêng
    service = _service()
    acceptable = ["TCP/IP, Internet Protocol Suite"]
    assert service._grade_logic("fill_blank", acceptable, "TCP/IP") is False
    assert (
        service._grade_logic(
            "fill_blank", acceptable, "TCP/IP, Internet Protocol Suite"
        )
        is True
    )


# ── short_answer ──────────────────────────────────────────────────


def test_short_answer_exact_match():
    service = _service()
    assert service._grade_logic("short_answer", "3.14", "3.14") is True


def test_short_answer_collapses_extra_whitespace():
    service = _service()
    assert service._grade_logic("short_answer", "New York", "  new   york ") is True


def test_short_answer_wrong_value():
    service = _service()
    assert service._grade_logic("short_answer", "3.14", "3.15") is False


# ── chung ─────────────────────────────────────────────────────────


def test_none_user_answer_always_false_regardless_of_type():
    service = _service()
    for q_type in [
        "multiple_choice",
        "multiple_response",
        "true_false",
        "fill_blank",
        "short_answer",
    ]:
        assert service._grade_logic(q_type, "A", None) is False


@pytest.mark.asyncio
async def test_essay_ai_returns_achieved_count_and_backend_calculates_score():
    class LLM:
        async def generate(self, prompt: str):
            assert "Do not calculate a score" in prompt
            assert "Never provide examples, a model answer" in prompt
            assert "same language as the question" in prompt
            return '{"achieved_points_count": 2, "feedback": "Two points met."}'

    pipeline = type("Pipeline", (), {"llm": LLM()})()
    service = QuizService(DummyDB(), pipeline)
    score, feedback = await service._grade_essay_answer(
        "Explain the topic", ["Point 1", "Point 2", "Point 3"], "Answer", 9
    )
    assert score == Decimal("6.00")
    assert feedback == "Two points met."


def test_unknown_question_type_returns_false():
    service = _service()
    assert service._grade_logic("essay", ["ý 1", "ý 2"], "bài làm tự luận") is False
