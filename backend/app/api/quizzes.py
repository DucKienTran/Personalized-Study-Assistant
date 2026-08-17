from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.dependencies import (
    CurrentUserDep,
    FeedbackServiceDep,
    NotebookServiceDep,
    PersonalOffsetServiceDep,
    QuizServiceDep,
    get_current_user,
)
from app.exceptions.quiz import InvalidQuizOperationError
from app.schemas.quiz_profile_schema import (
    FeedbackIn,
    MergedQuizProfileOut,
)
from app.schemas.quiz_schema import (
    QuestionHintOut,
    QuizAnswerRequest,
    QuizGenerateRequest,
    QuizProcessingOut,
    QuizSubmitRequest,
)
from app.schemas.response_schema import BaseResponse

router = APIRouter(
    prefix="/quizzes",
    tags=["Quizzes"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "",
    response_model=BaseResponse[List[Dict[str, Any]]],
)
def list_quizzes_for_notebook(
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
    notebook_id: int | None = None,
):
    return BaseResponse(
        data=quiz_service.get_quizzes(
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    )


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[Dict[str, Any]],
)
async def generate_quiz(
    req: QuizGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
    notebook_service: NotebookServiceDep,
    personal_offset_service: PersonalOffsetServiceDep,
):
    source_document_ids = notebook_service.get_active_document_ids(
        notebook_id=req.notebook_id,
        user_id=current_user.id,
    )
    if not source_document_ids:
        raise InvalidQuizOperationError(
            "Notebook phải có ít nhất một tài liệu đang hoạt động để tạo quiz."
        )

    quiz = quiz_service.create_quiz_placeholder(
        notebook_id=req.notebook_id,
        source_document_ids=source_document_ids,
        user_id=current_user.id,
        title="Đang tạo đề...",
        mode=req.mode,
        time_limit_minutes=req.time_limit_minutes,
        target_total_points=req.target_total_points,
        generation_strategy=req.generation_strategy,
        question_types=req.question_types,
        difficulty_distribution=req.difficulty_distribution,
        custom_instruction=req.custom_instruction,
        total_questions=req.total_questions,
    )
    merged_profile = (
        personal_offset_service.get_merged_profile(
            current_user.id
        )
    )
    background_tasks.add_task(
        quiz_service.run_generation,
        quiz.id,
        req,
        merged_profile,
    )

    return BaseResponse(
        data={
            "quiz_id": quiz.id,
            "generation_status": quiz.generation_status,
        }
    )


@router.get(
    "/processing",
    response_model=BaseResponse[list[QuizProcessingOut]],
)
def get_processing_quizzes(
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.get_processing_quizzes(
            current_user.id,
        )
    )


@router.get(
    "/{quiz_id}",
    response_model=BaseResponse[Dict[str, Any]],
)
def get_quiz_detail(
    quiz_id: int,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.get_quiz_for_rendering(
            quiz_id,
            current_user.id,
        )
    )


@router.get(
    "/{quiz_id}/attempts",
    response_model=BaseResponse[List[Dict[str, Any]]],
)
def list_quiz_attempts(
    quiz_id: int,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.get_quiz_attempts_list(
            quiz_id,
            current_user.id,
        )
    )


@router.post(
    "/{quiz_id}/questions/{question_id}/answer",
    response_model=BaseResponse[Dict[str, Any]],
)
async def answer_single_question(
    quiz_id: int,
    question_id: int,
    req: QuizAnswerRequest,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=await quiz_service.grade_and_save_single_answer_progress(
            quiz_id,
            question_id,
            current_user.id,
            req.user_answer,
        )
    )


@router.post(
    "/{quiz_id}/submit",
    response_model=BaseResponse[Dict[str, Any]],
)
async def submit_exam(
    quiz_id: int,
    req: QuizSubmitRequest,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=await quiz_service.grade_and_submit_entire_quiz(
            quiz_id,
            current_user.id,
            [answer.model_dump() for answer in req.answers],
            req.submit_reason,
        )
    )


@router.post(
    "/{quiz_id}/feedback",
    response_model=BaseResponse[MergedQuizProfileOut],
)
async def submit_quiz_feedback(
    feedback: FeedbackIn,
    current_user: CurrentUserDep,
    feedback_service: FeedbackServiceDep,
):
    """
    Submit feedback after completing quiz.

    Current:
    - Update global user quiz profile offset.

    Future:
    - Save quiz_id
    - Save attempt_id
    - Notebook-level offset
    """

    profile = await feedback_service.apply_feedback(
        user_id=current_user.id,
        feedback=feedback,
    )

    return BaseResponse(
        data=profile,
    )


@router.delete(
    "/{quiz_id}/progress",
    response_model=BaseResponse[None],
)
def reset_study_progress(
    quiz_id: int,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    quiz_service.clear_quiz_progress(
        quiz_id,
        current_user.id,
    )

    return BaseResponse(
        message="Đã reset quá trình học, bạn có thể bắt đầu lại."
    )


@router.get(
    "/{quiz_id}/hints",
    response_model=BaseResponse[list[QuestionHintOut]],
)
def get_quiz_hints(
    quiz_id: int,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.get_quiz_hints(
            quiz_id,
            current_user.id,
        )
    )


# =====================================================
# Quiz Attempt Resource
# =====================================================

attempts_router = APIRouter(
    prefix="/quiz-attempts",
    tags=["Quiz Attempts"],
    dependencies=[Depends(get_current_user)],
)


@attempts_router.get(
    "/{attempt_id}",
    response_model=BaseResponse[Dict[str, Any]],
)
def get_attempt_detail(
    attempt_id: int,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.get_attempt_detail(
            attempt_id,
            current_user.id,
        )
    )


@router.post(
    "/{quiz_id}/attempts/start",
    response_model=BaseResponse[Dict[str, Any]],
)
def start_quiz_attempt(
    quiz_id: int,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.start_quiz_attempt(
            quiz_id,
            current_user.id,
        )
    )


@router.delete(
    "/{quiz_id}",
    response_model=BaseResponse[None],
)
def delete_quiz(
    quiz_id: int,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    quiz_service.delete_quiz(quiz_id, current_user.id)
    return BaseResponse(message="Quiz deleted successfully.")
