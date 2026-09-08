from __future__ import annotations

import asyncio
import json
import logging

from app.ai.llm.base import LLMClient
from app.ai.prompts.assistant_action_prompt import AssistantActionPromptBuilder
from app.services.assistant.contracts import AssistantActionType, AssistantDecision

logger = logging.getLogger(__name__)
ROUTER_TIMEOUT_SECONDS = 10


class AssistantActionRouter:
    """
    Classifies a user message before the normal RAG flow.

    Fail-open policy:
    any malformed/failed classifier result becomes ANSWER so the existing chat
    experience continues to work instead of breaking.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def decide(self, *, user_message: str) -> AssistantDecision:
        message = user_message.strip()
        if not message:
            return AssistantDecision(
                action=AssistantActionType.ANSWER,
                confidence=1.0,
                reason="empty message",
            )

        try:
            async with asyncio.timeout(ROUTER_TIMEOUT_SECONDS):
                raw = await self.llm_client.generate(
                    prompt=AssistantActionPromptBuilder.build(user_message=message)
                )
            parsed = self._parse(raw)
            return parsed
        except Exception:
            logger.exception("Assistant action routing failed; falling back to ANSWER.")
            return AssistantDecision(
                action=AssistantActionType.ANSWER,
                confidence=0.0,
                reason="router failure",
            )

    @staticmethod
    def _parse(raw: str) -> AssistantDecision:
        text = (raw or "").strip()

        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        payload = json.loads(text)
        action = AssistantActionType(payload["action"])
        confidence = float(payload.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return AssistantDecision(
            action=action,
            confidence=confidence,
            reason=payload.get("reason"),
        )
