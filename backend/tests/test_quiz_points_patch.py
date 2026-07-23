import pytest

from app.services.ai.quiz_service import QuizService


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


def test_patch_raises_when_cannot_reduce_further():
    # 3 câu đều 1 điểm, tổng=3, target=1 -> không thể giảm thêm (mọi câu đã ở mức tối thiểu)
    questions = [{"points": 1}, {"points": 1}, {"points": 1}]
    with pytest.raises(ValueError):
        QuizService._patch_points_distributed(questions, target=1)


def test_patch_empty_questions_list_is_noop():
    result = QuizService._patch_points_distributed([], target=10)
    assert result == []
