from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.dependencies import CurrentUserDep, QuizServiceDep, get_current_user
from app.schemas.quiz_schema import (
    QuestionHintOut,
    QuizAnswerRequest,
    QuizGenerateRequest,
    QuizProcessingOut,
    QuizSubmitRequest,
)
from app.schemas.response_schema import BaseResponse

router = APIRouter(
    prefix="/quizzes", tags=["Quizzes"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=BaseResponse[List[Dict[str, Any]]])
def list_quizzes_for_document(
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
    document_id: int | None = None,
):
    """Danh sách đề thi của 1 tài liệu, kèm trạng thái suy ra:
    processing | failed | todo | in_progress | completed."""
    return BaseResponse(
        data=quiz_service.get_quizzes(user_id=current_user.id, document_id=document_id)
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
):
    quiz = quiz_service.create_quiz_placeholder(
        document_id=req.document_id,
        user_id=current_user.id,
        title=f"Đang tạo đề...",
        mode=req.mode,
        time_limit_minutes=req.time_limit_minutes,
        target_total_points=req.target_total_points,
        generation_mode=req.generation_mode,
        difficulty=req.difficulty,
        custom_instruction=req.custom_instruction,
        total_questions=req.total_questions,
    )
    background_tasks.add_task(
        quiz_service.run_generation, quiz.id, req.question_types, req.total_questions
    )
    return BaseResponse(
        data={"quiz_id": quiz.id, "generation_status": quiz.generation_status}
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


@router.get("/{quiz_id}", response_model=BaseResponse[Dict[str, Any]])
def get_quiz_detail(
    quiz_id: int, current_user: CurrentUserDep, quiz_service: QuizServiceDep
):
    """Trả đề + overlay tiến độ đang làm dở (chỉ mode study) — CỐ Ý giữ 1-call,
    không tách khỏi progress để không phá luồng resume offline-friendly."""
    return BaseResponse(
        data=quiz_service.get_quiz_for_rendering(quiz_id, current_user.id)
    )


@router.get("/{quiz_id}/attempts", response_model=BaseResponse[List[Dict[str, Any]]])
def list_quiz_attempts(
    quiz_id: int, current_user: CurrentUserDep, quiz_service: QuizServiceDep
):
    """Danh sách các lần làm (attempt) của 1 đề — dùng cho màn hình chọn lần làm để xem lại."""
    return BaseResponse(
        data=quiz_service.get_quiz_attempts_list(quiz_id, current_user.id)
    )


@router.post(
    "/{quiz_id}/questions/{question_id}/answer",
    response_model=BaseResponse[Dict[str, Any]],
)
def answer_single_question(
    quiz_id: int,
    question_id: int,
    req: QuizAnswerRequest,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.save_single_answer_progress(
            quiz_id, question_id, current_user.id, req.user_answer
        )
    )


@router.post("/{quiz_id}/submit", response_model=BaseResponse[Dict[str, Any]])
def submit_exam(
    quiz_id: int,
    req: QuizSubmitRequest,
    current_user: CurrentUserDep,
    quiz_service: QuizServiceDep,
):
    return BaseResponse(
        data=quiz_service.submit_entire_quiz(
            quiz_id, current_user.id, req.answers, req.submit_reason
        )
    )


@router.delete("/{quiz_id}/progress", response_model=BaseResponse[None])
def reset_study_progress(
    quiz_id: int, current_user: CurrentUserDep, quiz_service: QuizServiceDep
):
    quiz_service.clear_quiz_progress(quiz_id, current_user.id)
    return BaseResponse(message="Đã reset quá trình học, bạn có thể bắt đầu lại.")


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


# RESOURCE RIÊNG: QuizAttempt
attempts_router = APIRouter(
    prefix="/quiz-attempts",
    tags=["Quiz Attempts"],
    dependencies=[Depends(get_current_user)],
)


@attempts_router.get("/{attempt_id}", response_model=BaseResponse[Dict[str, Any]])
def get_attempt_detail(
    attempt_id: int, current_user: CurrentUserDep, quiz_service: QuizServiceDep
):
    """Chi tiết 1 lần làm cụ thể: câu hỏi + đáp án user đã chọn + đúng/sai + giải thích."""
    return BaseResponse(
        data=quiz_service.get_attempt_detail(attempt_id, current_user.id)
    )
