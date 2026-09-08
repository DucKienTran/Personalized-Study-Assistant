import json
from types import SimpleNamespace

from fastapi import BackgroundTasks
import pytest

from app.api import rag as rag_api
from app.schemas.conversation_schema import MessageOut
from app.schemas.rag_schema import RAGQueryRequest
from app.services.assistant.contracts import (
    AssistantActionResult,
    AssistantActionType,
    AssistantBackgroundJob,
    AssistantResource,
    AssistantResourceType,
)


class FakeConversationService:
    def __init__(self):
        self.conversation = SimpleNamespace(
            id=7, title="Existing chat", notebook_id=3
        )
        self.messages = []

    def get_conversation(self, *args):
        return self.conversation

    def has_user_messages(self, *args):
        return True

    def add_message(self, db, conversation_id, sender, content, **kwargs):
        self.messages.append(
            SimpleNamespace(
                id=len(self.messages) + 1,
                sender=sender,
                content=content,
                sources_json=kwargs.get("sources_json"),
                resource_json=kwargs.get("resource_json"),
                created_at="2026-08-24T00:00:00Z",
            )
        )


class FakeRouter:
    async def decide(self, **kwargs):
        return SimpleNamespace(action=AssistantActionType.CREATE_MINDMAP)


class FakeExecutor:
    async def execute(self, **kwargs):
        return AssistantActionResult(
            message="I've created a mindmap from your active sources.",
            resource=AssistantResource(
                type=AssistantResourceType.MINDMAP,
                id="73",
                title="Optimization Mindmap",
                notebook_id=3,
            ),
        )


class UnusedService:
    async def __getattr__(self, name):
        raise AssertionError(f"Unexpected service call: {name}")


async def fake_generation(resource_id):
    return None


class FakePhaseTwoExecutor:
    async def execute(self, **kwargs):
        return AssistantActionResult(
            message="Đang tạo quiz cho bạn.",
            resource=AssistantResource(
                type=AssistantResourceType.QUIZ,
                id="91",
                title="Đang tạo đề...",
                notebook_id=3,
                metadata={"generationStatus": "processing"},
            ),
            background_job=AssistantBackgroundJob(
                func=fake_generation,
                args=(91,),
            ),
        )


@pytest.mark.asyncio
async def test_resource_event_is_persisted_and_hydrates(monkeypatch):
    conversations = FakeConversationService()
    monkeypatch.setattr(rag_api, "conversation_service", conversations)

    response = await rag_api.stream_query_rag(
        payload=RAGQueryRequest(query="Tạo mindmap", notebook_id=3, conversation_id=7),
        background_tasks=BackgroundTasks(),
        current_user=SimpleNamespace(id=11),
        db=SimpleNamespace(rollback=lambda: None),
        rag_service=UnusedService(),
        conversation_title_ai_service=UnusedService(),
        assistant_action_router=FakeRouter(),
        assistant_action_executor=FakeExecutor(),
    )
    events = "".join([chunk async for chunk in response.body_iterator])

    assert "event: resource" in events
    assert '"resourceId": "73"' in events
    assistant_message = conversations.messages[-1]
    persisted_resource = json.loads(assistant_message.resource_json)
    assert persisted_resource["resourceType"] == "mindmap"
    assert persisted_resource["resourceId"] == "73"

    hydrated = MessageOut.model_validate(assistant_message, from_attributes=True)
    assert json.loads(hydrated.resource_json)["resourceId"] == "73"


@pytest.mark.asyncio
async def test_phase_two_resource_schedules_one_job_and_preserves_event_order(
    monkeypatch,
):
    conversations = FakeConversationService()
    monkeypatch.setattr(rag_api, "conversation_service", conversations)
    tasks = BackgroundTasks()

    response = await rag_api.stream_query_rag(
        payload=RAGQueryRequest(query="Tạo quiz", notebook_id=3, conversation_id=7),
        background_tasks=tasks,
        current_user=SimpleNamespace(id=11),
        db=SimpleNamespace(rollback=lambda: None),
        rag_service=UnusedService(),
        conversation_title_ai_service=UnusedService(),
        assistant_action_router=FakeRouter(),
        assistant_action_executor=FakePhaseTwoExecutor(),
    )
    events = "".join([chunk async for chunk in response.body_iterator])

    assert events.index("event: token") < events.index("event: resource")
    assert events.index("event: resource") < events.index("event: done")
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is fake_generation
    assert tasks.tasks[0].args == (91,)
    persisted = json.loads(conversations.messages[-1].resource_json)
    assert persisted["resourceType"] == "quiz"
    assert persisted["resourceId"] == "91"
