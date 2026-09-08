import json

import pytest

from app.services.assistant.action_router import AssistantActionRouter
from app.services.assistant.contracts import AssistantActionType


class FakeLLM:
    def __init__(self, response: str):
        self.response = response

    async def generate(self, prompt: str):
        return self.response


class MessageAwareLLM:
    async def generate(self, prompt: str):
        message = prompt.rsplit("User message:", 1)[-1].strip()
        if message in {"Mindmap là gì?", "Quiz hoạt động như thế nào?"}:
            action = "answer"
        elif message == "Flashcard là gì?":
            action = "answer"
        elif message == "Tạo mindmap cho tôi":
            action = "create_mindmap"
        elif message == "Tạo quiz cho tôi":
            action = "create_quiz"
        elif message == "Tạo flashcards cho tôi":
            action = "create_flashcards"
        else:
            action = "create_summary"
        return json.dumps({"action": action, "confidence": 0.99})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            json.dumps(
                {
                    "action": "answer",
                    "confidence": 0.98,
                    "reason": "feature question",
                }
            ),
            AssistantActionType.ANSWER,
        ),
        (
            json.dumps(
                {
                    "action": "create_summary",
                    "confidence": 0.99,
                    "reason": "explicit request",
                }
            ),
            AssistantActionType.CREATE_SUMMARY,
        ),
        (
            json.dumps(
                {
                    "action": "create_mindmap",
                    "confidence": 0.99,
                    "reason": "explicit request",
                }
            ),
            AssistantActionType.CREATE_MINDMAP,
        ),
    ],
)
async def test_router_parses_supported_actions(response, expected):
    router = AssistantActionRouter(FakeLLM(response))
    decision = await router.decide(user_message="test")
    assert decision.action == expected


@pytest.mark.asyncio
async def test_router_fails_open_to_answer():
    router = AssistantActionRouter(FakeLLM("not-json"))
    decision = await router.decide(user_message="hello")
    assert decision.action == AssistantActionType.ANSWER


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Mindmap là gì?", AssistantActionType.ANSWER),
        ("Tạo mindmap cho tôi", AssistantActionType.CREATE_MINDMAP),
        ("Tóm tắt notebook này", AssistantActionType.CREATE_SUMMARY),
        ("Tạo quiz cho tôi", AssistantActionType.CREATE_QUIZ),
        ("Quiz hoạt động như thế nào?", AssistantActionType.ANSWER),
        ("Tạo flashcards cho tôi", AssistantActionType.CREATE_FLASHCARDS),
        ("Flashcard là gì?", AssistantActionType.ANSWER),
    ],
)
async def test_router_routes_supported_intents(message, expected):
    decision = await AssistantActionRouter(MessageAwareLLM()).decide(
        user_message=message
    )
    assert decision.action == expected
