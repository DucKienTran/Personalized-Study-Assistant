import json
import logging
from typing import Dict

from app.ai.constants.quiz_profile import (
    PRESET_TAG_DELTAS,
    QUIZ_PROFILE_FIELDS,
    zero_delta,
)
from app.ai.llm.base import LLMClient
from app.ai.prompts.feedback_analyzer_prompt import FeedbackAnalyzerPrompt
from app.schemas.quiz_profile_schema import FeedbackIn
from app.services.quiz.personal_offset_service import PersonalOffsetService

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service quản lý adaptive quiz profile.

    Responsibilities:
    - Merge DEFAULT_QUIZ_PROFILE + personal offset.
    - Apply user feedback -> update personal offset.
    - Handle EMA smoothing.
    - Clamp profile values.

    Current scope:
    - Global user offset only.
    - Future:
        User + Notebook offset
        User + Question offset
    """

    def __init__(
        self,
        llm: LLMClient,
        personal_offset_service: PersonalOffsetService,
    ):
        self.llm = llm
        self.personal_offset_service = personal_offset_service
        self.prompt_builder = FeedbackAnalyzerPrompt()

    async def apply_feedback(
        self,
        user_id: int,
        feedback: FeedbackIn,
    ) -> Dict[str, float]:

        preset_delta = self._map_preset_feedback(feedback)

        ai_delta = await self._analyze_feedback(
            feedback
        )

        total_delta = self._merge_feedback_delta(
            preset_delta,
            ai_delta,
        )

        self.personal_offset_service.apply_delta(
            user_id=user_id,
            delta=total_delta,
        )

        profile = self.personal_offset_service.get_merged_profile(
            user_id=user_id,
        )

        return profile.model_dump()
    def _merge_feedback_delta(
        self,
        preset_delta: Dict[str, float],
        ai_delta: Dict[str, float],
    ) -> Dict[str, float]:

        total = zero_delta()


        for field in QUIZ_PROFILE_FIELDS:

            total[field] = (
                preset_delta.get(field, 0.0)
                +
                ai_delta.get(field, 0.0)
            )


        return total

    def _map_preset_feedback(
        self,
        feedback: FeedbackIn,
    ) -> Dict[str, float]:

        delta = zero_delta()

        # checkbox tags
        for tag in feedback.tags:

            tag_delta = PRESET_TAG_DELTAS.get(
                tag.value,
                {},
            )

            for field, value in tag_delta.items():
                delta[field] += value

        return delta

    async def _analyze_feedback(
        self,
        feedback: FeedbackIn,
    ) -> Dict[str, float]:

        if not feedback.comment:
            return zero_delta()


        prompt = self.prompt_builder.build(
             comment=feedback.comment,
        )


        response = await self.llm.generate(
            prompt
        )


        try:
            result = json.loads(response)

        except Exception:
            logger.exception(
                "Failed parsing feedback AI delta"
            )
            return zero_delta()


        delta = zero_delta()


        for field in QUIZ_PROFILE_FIELDS:

            value = result.get(
                field,
                0.0,
            )

            delta[field] = float(value)
            delta[field] = max(
                -3.0,
                min(
                    3.0,
                    float(value)
                )
            )


        return delta
