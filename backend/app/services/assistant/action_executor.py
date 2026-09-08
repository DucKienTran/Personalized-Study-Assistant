from __future__ import annotations

from app.schemas.mindmap_schema import MindmapCreate
from app.schemas.user_schema import CurrentUser
from app.services.assistant.contracts import (
    AssistantActionResult,
    AssistantActionType,
    AssistantResource,
    AssistantResourceType,
)
from app.services.assistant.generation_orchestrator import AssistantGenerationOrchestrator
from app.services.mindmap.mindmap_service import MindmapService
from app.services.summary.summary_service import GeneratedNotebookSummary, SummaryService


class AssistantActionExecutor:
    """
    Executes only Phase-1 side-effect actions.

    Existing feature services remain the source of truth. This class MUST NOT
    duplicate Summary/Mindmap generation logic.
    """

    def __init__(
        self,
        *,
        summary_service: SummaryService,
        mindmap_service: MindmapService,
        generation_orchestrator: AssistantGenerationOrchestrator,
    ) -> None:
        self.summary_service = summary_service
        self.mindmap_service = mindmap_service
        self.generation_orchestrator = generation_orchestrator

    async def execute(
        self,
        *,
        action: AssistantActionType,
        notebook_id: int,
        current_user: CurrentUser,
        user_message: str = "",
    ) -> AssistantActionResult:
        if action == AssistantActionType.CREATE_SUMMARY:
            message, resource = await self._create_summary(
                notebook_id=notebook_id,
                current_user=current_user,
            )
            return AssistantActionResult(message=message, resource=resource)

        if action == AssistantActionType.CREATE_MINDMAP:
            message, resource = await self._create_mindmap(
                notebook_id=notebook_id,
                current_user=current_user,
            )
            return AssistantActionResult(message=message, resource=resource)

        if action == AssistantActionType.CREATE_QUIZ:
            return self.generation_orchestrator.create_quiz(
                notebook_id=notebook_id,
                user_message=user_message,
                current_user=current_user,
            )

        if action == AssistantActionType.CREATE_FLASHCARDS:
            return self.generation_orchestrator.create_flashcards(
                notebook_id=notebook_id,
                user_message=user_message,
                current_user=current_user,
            )

        raise ValueError(f"Unsupported Assistant action: {action}")

    async def _create_summary(
        self,
        *,
        notebook_id: int,
        current_user: CurrentUser,
    ) -> tuple[str, AssistantResource]:
        summary = await self.summary_service.generate_notebook_summary(
            user_id=current_user.id,
            notebook_id=notebook_id,
            level="standard",
            format_type="markdown",
            instruction="",
            include_record=True,
        )
        if not isinstance(summary, GeneratedNotebookSummary):
            raise RuntimeError("Summary generation did not return a resource record.")

        resource = AssistantResource(
            type=AssistantResourceType.SUMMARY,
            id=str(summary.record.id),
            title=summary.record.title,
            notebook_id=notebook_id,
        )

        return "I've created a summary from your active sources.", resource

    async def _create_mindmap(
        self,
        *,
        notebook_id: int,
        current_user: CurrentUser,
    ) -> tuple[str, AssistantResource]:
        mindmap = await self.mindmap_service.create_mindmap(
            notebook_id=notebook_id,
            payload=MindmapCreate(title=None),
            current_user=current_user,
        )

        resource = AssistantResource(
            type=AssistantResourceType.MINDMAP,
            id=str(mindmap.id),
            title=mindmap.title,
            notebook_id=notebook_id,
        )

        return "I've created a mindmap from your active sources.", resource
