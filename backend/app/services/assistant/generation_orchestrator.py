from __future__ import annotations

from app.exceptions.quiz import InvalidQuizOperationError
from app.schemas.user_schema import CurrentUser
from app.services.assistant.contracts import (
    AssistantActionResult,
    AssistantBackgroundJob,
    AssistantResource,
    AssistantResourceType,
)
from app.services.assistant.generation_request_factory import (
    build_assistant_flashcard_request,
    build_assistant_quiz_request,
)
from app.services.flashcard.flashcard_service import FlashcardService
from app.services.notebook.notebook_service import NotebookService
from app.services.quiz.personal_offset_service import PersonalOffsetService
from app.services.quiz.quiz_service import QuizService


class AssistantGenerationOrchestrator:
    def __init__(
        self,
        *,
        quiz_service: QuizService,
        flashcard_service: FlashcardService,
        notebook_service: NotebookService,
        personal_offset_service: PersonalOffsetService,
    ) -> None:
        self.quiz_service = quiz_service
        self.flashcard_service = flashcard_service
        self.notebook_service = notebook_service
        self.personal_offset_service = personal_offset_service

    def create_quiz(
        self, *, notebook_id: int, user_message: str, current_user: CurrentUser
    ) -> AssistantActionResult:
        request = build_assistant_quiz_request(
            notebook_id=notebook_id, user_message=user_message
        )
        source_document_ids = self.notebook_service.get_active_document_ids(
            notebook_id=notebook_id, user_id=current_user.id
        )
        if not source_document_ids:
            raise InvalidQuizOperationError(
                "Notebook phải có ít nhất một tài liệu đang hoạt động để tạo quiz."
            )

        quiz = self.quiz_service.create_quiz_placeholder(
            notebook_id=notebook_id,
            source_document_ids=source_document_ids,
            user_id=current_user.id,
            title="Đang tạo đề...",
            mode=request.mode,
            time_limit_minutes=request.time_limit_minutes,
            target_total_points=request.target_total_points,
            generation_strategy=request.generation_strategy,
            question_types=request.question_types,
            difficulty_distribution=request.difficulty_distribution,
            custom_instruction=request.custom_instruction,
            total_questions=request.total_questions,
        )
        merged_profile = self.personal_offset_service.get_merged_profile(current_user.id)

        return AssistantActionResult(
            message="Đang tạo quiz cho bạn.",
            resource=AssistantResource(
                type=AssistantResourceType.QUIZ,
                id=str(quiz.id),
                title=quiz.title,
                notebook_id=notebook_id,
                metadata={"generationStatus": quiz.generation_status},
            ),
            background_job=AssistantBackgroundJob(
                func=self.quiz_service.run_generation,
                args=(quiz.id, request, merged_profile),
            ),
        )

    def create_flashcards(
        self, *, notebook_id: int, user_message: str, current_user: CurrentUser
    ) -> AssistantActionResult:
        request = build_assistant_flashcard_request(
            notebook_id=notebook_id, user_message=user_message
        )
        source_document_ids = self.notebook_service.get_active_document_ids(
            notebook_id=notebook_id, user_id=current_user.id
        )
        deck = self.flashcard_service.create_generation_deck(
            user_id=current_user.id,
            data=request,
            source_document_ids=source_document_ids,
        )

        return AssistantActionResult(
            message="Đang tạo bộ flashcards cho bạn.",
            resource=AssistantResource(
                type=AssistantResourceType.FLASHCARDS,
                id=str(deck.id),
                title=deck.title,
                notebook_id=notebook_id,
                metadata={"generationStatus": deck.generation_status},
            ),
            background_job=AssistantBackgroundJob(
                func=self.flashcard_service.run_generation,
                args=(deck.id,),
                kwargs={
                    "total_cards": request.total_cards,
                    "custom_instruction": request.custom_instruction,
                },
            ),
        )
