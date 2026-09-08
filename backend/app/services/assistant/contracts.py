from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable


class AssistantActionType(StrEnum):
    ANSWER = "answer"
    CREATE_SUMMARY = "create_summary"
    CREATE_MINDMAP = "create_mindmap"
    CREATE_QUIZ = "create_quiz"
    CREATE_FLASHCARDS = "create_flashcards"


class AssistantResourceType(StrEnum):
    SUMMARY = "summary"
    MINDMAP = "mindmap"
    QUIZ = "quiz"
    FLASHCARDS = "flashcards"


@dataclass(slots=True)
class AssistantDecision:
    action: AssistantActionType
    confidence: float
    reason: str | None = None


@dataclass(slots=True)
class AssistantResource:
    type: AssistantResourceType
    id: str
    title: str
    notebook_id: int
    metadata: dict[str, Any] | None = None

    def to_event(self) -> dict[str, Any]:
        return {
            "type": "resource",
            "data": {
                "resourceType": self.type.value,
                "resourceId": self.id,
                "title": self.title,
                "notebookId": self.notebook_id,
                "metadata": self.metadata or {},
            },
        }


BackgroundCallable = Callable[..., Awaitable[None]]


@dataclass(slots=True)
class AssistantBackgroundJob:
    func: BackgroundCallable
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssistantActionResult:
    message: str
    resource: AssistantResource
    background_job: AssistantBackgroundJob | None = None
