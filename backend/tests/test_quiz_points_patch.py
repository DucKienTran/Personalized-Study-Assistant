from decimal import Decimal

from pydantic import ValidationError
import pytest

from app.schemas.quiz_schema import QuizGenerateRequest
from app.services.quiz.quiz_service import QuizService


def _request(**overrides):
    data = {
        "notebook_id": 1,
        "mode": "study",
        "generation_strategy": "manual",
        "difficulty_distribution": {"easy": 1.0},
        **overrides,
    }
    return QuizGenerateRequest(**data)


def test_target_total_points_defaults_when_null():
    assert _request(target_total_points=None).target_total_points == 100


def test_target_total_points_must_allow_one_cent_per_question():
    with pytest.raises(ValidationError):
        _request(total_questions=10, target_total_points=Decimal("0.09"))


def test_target_total_points_accepts_fractional_values():
    request = _request(total_questions=10, target_total_points=Decimal("5.50"))

    assert request.target_total_points == Decimal("5.50")


def test_target_total_points_rejects_more_than_two_decimal_places():
    with pytest.raises(ValidationError):
        _request(target_total_points=Decimal("10.555"))


def test_no_patch_needed_when_already_matching_target():
    questions = [{"points": 3}, {"points": 3}, {"points": 4}]
    result = QuizService._patch_points_distributed(questions, target=10)
    assert sum(q["points"] for q in result) == 10


def test_patch_positive_drift_distributes_across_lowest_points_first():
    # target=12, hiện tại tổng=10, thiếu 2 điểm -> rải vào 2 câu điểm thấp nhất trước
    questions = [{"points": 1}, {"points": 5}, {"points": 4}]
    result = QuizService._patch_points_distributed(questions, target=12)
    assert sum(q["points"] for q in result) == 12
    assert all(q["points"] >= 1 for q in result)


def test_patch_negative_drift_never_goes_below_one():
    # target=5, hiện tại tổng=10 -> phải giảm 5 điểm, không câu nào được về dưới 1
    questions = [{"points": 4}, {"points": 3}, {"points": 3}]
    result = QuizService._patch_points_distributed(questions, target=5)
    assert sum(q["points"] for q in result) == 5
    assert all(q["points"] >= 1 for q in result)


def test_patch_distributes_fractional_target_exactly():
    questions = [{"points": 1}, {"points": 1}, {"points": 1}]

    result = QuizService._patch_points_distributed(
        questions, target=Decimal("1.50")
    )

    assert sum(q["points"] for q in result) == Decimal("1.50")
    assert all(q["points"] >= Decimal("0.01") for q in result)


def test_patch_raises_when_cannot_reduce_further():
    questions = [
        {"points": Decimal("0.01")},
        {"points": Decimal("0.01")},
        {"points": Decimal("0.01")},
    ]
    with pytest.raises(ValueError):
        QuizService._patch_points_distributed(
            questions, target=Decimal("0.02")
        )


def test_patch_empty_questions_list_is_noop():
    result = QuizService._patch_points_distributed([], target=10)
    assert result == []
