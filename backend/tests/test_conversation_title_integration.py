from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import BackgroundTasks
import pytest

from app.api import rag as rag_api
from app.schemas.rag_schema import RAGQueryRequest
from app.services.rag.conversation_service import DEFAULT_CONVERSATION_TITLE
from app.services.rag.conversation_title_ai_service import ConversationTitleAIService


class FakeDb:
    def __init__(self):
        self.rollback_calls = 0

    def rollback(self):
        self.rollback_calls += 1


class FakeConversationService:
    def __init__(self, *, title=DEFAULT_CONVERSATION_TITLE, has_user_messages=False):
        self.conversation = SimpleNamespace(id=7, title=title, notebook_id=3)
        self.has_existing_user_message = has_user_messages
        self.messages = []
        self.saved_title = None

    def get_conversation(self, db, user_id, conversation_id):
        return self.conversation

    def create_conversation(self, db, user_id, notebook_id, title):
        assert title == DEFAULT_CONVERSATION_TITLE
        return self.conversation

    def has_user_messages(self, db, conversation_id):
        return self.has_existing_user_message

    def add_message(
        self, db, conversation_id, sender, content, sources_json=None, resource_json=None
    ):
        self.messages.append((sender, content))

    def update_title_if_default(self, db, user_id, conversation_id, title):
        if self.conversation.title != DEFAULT_CONVERSATION_TITLE:
            return False
        self.saved_title = title
        self.conversation.title = title
        self.conversation.updated_at = datetime.now(timezone.utc)
        return self.conversation


class FakeRAGService:
    async def stream_answer_question(self, **kwargs):
        yield {"type": "token", "content": "Answer"}
        yield {"type": "sources", "data": []}


class FakeTitleService:
    def __init__(self, result="Generated title", error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def generate_title(self, *, first_user_message):
        self.calls.append(first_user_message)
        if self.error:
            raise self.error
        return self.result


class FakeActionRouter:
    async def decide(self, **kwargs):
        return SimpleNamespace(action="answer")


class FakeActionExecutor:
    async def execute(self, **kwargs):
        raise AssertionError("Answer flow must not execute an action")


class FakeLLM:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    async def generate(self, prompt):
        if self.error:
            raise self.error
        return self.response


async def run_stream(monkeypatch, conversation_service, title_service):
    monkeypatch.setattr(rag_api, "conversation_service", conversation_service)
    db = FakeDb()
    response = await rag_api.stream_query_rag(
        payload=RAGQueryRequest(
            query="Explain Java assignment",
            notebook_id=3,
            conversation_id=7,
        ),
        background_tasks=BackgroundTasks(),
        current_user=SimpleNamespace(id=11),
        db=db,
        rag_service=FakeRAGService(),
        conversation_title_ai_service=title_service,
        assistant_action_router=FakeActionRouter(),
        assistant_action_executor=FakeActionExecutor(),
    )
    events = [chunk async for chunk in response.body_iterator]
    return events, db


@pytest.mark.asyncio
async def test_first_message_with_default_title_generates_and_persists_once(monkeypatch):
    conversations = FakeConversationService()
    titles = FakeTitleService()

    events, _ = await run_stream(monkeypatch, conversations, titles)

    assert titles.calls == ["Explain Java assignment"]
    assert conversations.saved_title == "Generated title"
    assert conversations.messages == [("user", "Explain Java assignment"), ("ai", "Answer")]
    assert events


@pytest.mark.asyncio
async def test_second_user_message_does_not_generate_title(monkeypatch):
    conversations = FakeConversationService(has_user_messages=True)
    titles = FakeTitleService()

    await run_stream(monkeypatch, conversations, titles)

    assert titles.calls == []
    assert conversations.saved_title is None


@pytest.mark.asyncio
async def test_manually_renamed_first_message_does_not_generate_title(monkeypatch):
    conversations = FakeConversationService(title="My Java Notes")
    titles = FakeTitleService()

    await run_stream(monkeypatch, conversations, titles)

    assert titles.calls == []
    assert conversations.saved_title is None


@pytest.mark.asyncio
async def test_title_generation_failure_does_not_fail_chat(monkeypatch):
    conversations = FakeConversationService()
    titles = FakeTitleService(error=RuntimeError("LLM unavailable"))

    events, db = await run_stream(monkeypatch, conversations, titles)

    assert events
    assert conversations.messages[-1] == ("ai", "Answer")
    assert conversations.saved_title is None
    assert db.rollback_calls == 1


@pytest.mark.asyncio
async def test_invalid_title_response_does_not_fail_chat(monkeypatch):
    conversations = FakeConversationService()
    titles = ConversationTitleAIService(llm_client=FakeLLM(response="not json"))

    events, _ = await run_stream(monkeypatch, conversations, titles)

    assert events
    assert conversations.messages[-1] == ("ai", "Answer")
    assert conversations.saved_title is None


@pytest.mark.asyncio
async def test_generated_title_is_persisted_before_stream_closes(monkeypatch):
    conversations = FakeConversationService()
    titles = ConversationTitleAIService(
        llm_client=FakeLLM(response='{"title": "Java assignment"}')
    )

    events, _ = await run_stream(monkeypatch, conversations, titles)

    assert conversations.saved_title == "Java assignment"
    assert any("event: conversation_updated" in event for event in events)
    assert any('"title": "Java assignment"' in event for event in events)
