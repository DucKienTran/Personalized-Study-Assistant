import inspect

import pytest

from app.ai.constants.quiz_profile import (
    DEFAULT_QUIZ_PROFILE,
    PRESET_TAG_DELTAS,
    QUIZ_PROFILE_BOUNDS,
)
from app.ai.prompts.feedback_analyzer_prompt import FeedbackAnalyzerPrompt
from app.services.quiz.personal_offset_service import PersonalOffsetService


def test_quiz_profile_constants_use_float_values():
    assert all(isinstance(value, float) for value in DEFAULT_QUIZ_PROFILE.values())
    assert all(
        isinstance(bound, float)
        for bounds in QUIZ_PROFILE_BOUNDS.values()
        for bound in bounds.values()
    )
    assert all(
        isinstance(value, float)
        for delta in PRESET_TAG_DELTAS.values()
        for value in delta.values()
    )


def test_feedback_prompt_allows_fractional_deltas():
    prompt = FeedbackAnalyzerPrompt.build("Make the next quiz slightly harder.")

    assert "floating-point number" in prompt
    assert '"reasoning_depth": 1.5' in prompt


def test_personal_offset_service_is_sync_and_preserves_fractional_ema():
    assert not inspect.iscoroutinefunction(PersonalOffsetService.get_or_create_offset)
    assert not inspect.iscoroutinefunction(PersonalOffsetService.get_merged_profile)
    assert not inspect.iscoroutinefunction(PersonalOffsetService.apply_delta)

    class Offset:
        difficulty_offset = 0.0
        coverage_offset = 0.0
        reasoning_depth_offset = 0.0
        anti_repetition_offset = 0.0
        relevance_offset = 0.0
        time_per_question_offset = 0.0
        strict_source_grounding_offset = 0.0

    class DB:
        def commit(self):
            pass

        def refresh(self, _offset):
            pass

    offset = Offset()
    service = PersonalOffsetService(DB())
    service.get_or_create_offset = lambda _user_id: offset

    service.apply_delta(user_id=1, delta={"difficulty": 1.5})

    assert offset.difficulty_offset == pytest.approx(0.3)
    assert service.get_merged_profile(user_id=1).difficulty == pytest.approx(6.3)
