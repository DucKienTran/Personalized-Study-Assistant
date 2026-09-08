from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.assistant.action_executor import AssistantActionExecutor
from app.services.assistant.contracts import AssistantActionType
from app.services.summary.summary_service import GeneratedNotebookSummary


@pytest.mark.asyncio
async def test_create_summary_calls_service_once_and_returns_real_resource():
    record = SimpleNamespace(id=42, title="Optimization Summary")
    summary_service = SimpleNamespace(
        generate_notebook_summary=AsyncMock(
            return_value=GeneratedNotebookSummary(text="Summary", record=record)
        )
    )
    mindmap_service = SimpleNamespace(create_mindmap=AsyncMock())
    executor = AssistantActionExecutor(
        summary_service=summary_service,
        mindmap_service=mindmap_service,
        generation_orchestrator=Mock(),
    )

    result = await executor.execute(
        action=AssistantActionType.CREATE_SUMMARY,
        notebook_id=6,
        current_user=SimpleNamespace(id=9),
    )

    summary_service.generate_notebook_summary.assert_awaited_once_with(
        user_id=9,
        notebook_id=6,
        level="standard",
        format_type="markdown",
        instruction="",
        include_record=True,
    )
    assert result.resource.id == "42"
    assert result.resource.title == "Optimization Summary"
    assert result.message == "I've created a summary from your active sources."


@pytest.mark.asyncio
async def test_create_mindmap_calls_service_once_and_returns_real_resource():
    summary_service = SimpleNamespace(generate_notebook_summary=AsyncMock())
    mindmap_service = SimpleNamespace(
        create_mindmap=AsyncMock(
            return_value=SimpleNamespace(id=73, title="Optimization Mindmap")
        )
    )
    executor = AssistantActionExecutor(
        summary_service=summary_service,
        mindmap_service=mindmap_service,
        generation_orchestrator=Mock(),
    )
    user = SimpleNamespace(id=9)

    result = await executor.execute(
        action=AssistantActionType.CREATE_MINDMAP,
        notebook_id=6,
        current_user=user,
    )

    mindmap_service.create_mindmap.assert_awaited_once()
    call = mindmap_service.create_mindmap.await_args.kwargs
    assert call["notebook_id"] == 6
    assert call["current_user"] is user
    assert call["payload"].title is None
    assert result.resource.id == "73"
    assert result.resource.title == "Optimization Mindmap"
    assert result.message == "I've created a mindmap from your active sources."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "method_name"),
    [
        (AssistantActionType.CREATE_QUIZ, "create_quiz"),
        (AssistantActionType.CREATE_FLASHCARDS, "create_flashcards"),
    ],
)
async def test_phase_two_actions_delegate_to_orchestrator(action, method_name):
    expected = SimpleNamespace(message="creating", resource=SimpleNamespace(id="9"))
    orchestrator = Mock()
    getattr(orchestrator, method_name).return_value = expected
    executor = AssistantActionExecutor(
        summary_service=SimpleNamespace(generate_notebook_summary=AsyncMock()),
        mindmap_service=SimpleNamespace(create_mindmap=AsyncMock()),
        generation_orchestrator=orchestrator,
    )
    user = SimpleNamespace(id=3)

    result = await executor.execute(
        action=action,
        notebook_id=7,
        current_user=user,
        user_message="original request",
    )

    assert result is expected
    getattr(orchestrator, method_name).assert_called_once_with(
        notebook_id=7,
        user_message="original request",
        current_user=user,
    )
