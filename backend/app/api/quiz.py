from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.quiz_model import Quiz, QuizQuestion

from app.services.ai.quiz_service import QuizService
from app.core.dependencies import get_quiz_service

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


# SCHEMAS (VALIDATE REQUEST)
class QuizGenerateRequest(BaseModel):
    document_id: int
    question_types: List[str]
    total_questions: int
    level: str
    mode: str = "study"  # "study" | "exam"
    time_limit_minutes: Optional[int] = None


class QuizAnswerRequest(BaseModel):
    user_answer: Any  # Có thể là chuỗi "A", hoặc mảng ["3.14"], hoặc chuỗi tự luận


class QuizSubmitRequest(BaseModel):
    submit_reason: str  # "manual", "timeout", "disconnected", "tab_switch_violation"


# ENDPOINTS
@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    req: QuizGenerateRequest,
    db: Session = Depends(get_db),
    # quiz_service: QuizService = Depends(get_quiz_service),
    # current_user = Depends(get_current_user) # Cậu tự bọc Auth vào nhé
):
    """
    Sinh đề thi bằng AI. Chỉ trả về danh sách câu hỏi ĐÃ ẨN đáp án và giải thích.
    """
    # XÓA DÒNG NÀY VÀ MỞ COMMENT DÒNG DƯỚI KHI CẬU NỐI SERVICE VÀO
    # quiz = await quiz_service.generate_quiz_async(db, req.document_id, current_user.id, ...)

    return {"message": "Đã sinh đề thành công (Cần nối QuizService để chạy thật)"}


@router.get("/{quiz_id}")
def get_quiz_detail(
    quiz_id: int,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)
):
    """
    Lấy đề làm bài.
    - Ẩn correct_answer và explanations của tất cả câu.
    - Riêng mode 'study': Nối bảng QuizProgress để trả kèm đáp án cho những câu user ĐÃ LÀM (resume).
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài Quiz")

    # TODO: Logic ẩn đáp án (Dùng Pydantic response_model có exclude)
    # TODO: Logic query QuizProgress (nếu mode study) để map vào từng câu hỏi

    return {"quiz": quiz.title, "mode": quiz.mode, "questions": quiz.questions}


@router.post("/{quiz_id}/questions/{question_id}/answer")
def answer_single_question(
    quiz_id: int,
    question_id: int,
    req: QuizAnswerRequest,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)
):
    """
    [CHỈ STUDY MODE] Chấm 1 câu, lưu QuizProgress, trả về kết quả Đ/S và giải thích liền tay.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or quiz.mode != "study":
        raise HTTPException(status_code=400, detail="Chỉ mode Study mới được chấm từng câu")

    question = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()

    # TODO: Logic so sánh req.user_answer với question.correct_answer để ra is_correct
    # TODO: Upsert vào bảng QuizProgress

    return {
        "is_correct": True,  # Thay bằng biến thật
        "explanations": question.explanations,
        "ai_feedback": "Nhận xét động nếu có",
    }


@router.post("/{quiz_id}/submit")
def submit_exam(
    quiz_id: int,
    req: QuizSubmitRequest,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)
):
    """
    [CHỈ EXAM MODE] Nộp toàn bộ bài, chấm điểm trắc nghiệm, tạo QuizResult.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or quiz.mode != "exam":
        raise HTTPException(status_code=400, detail="Chỉ mode Exam mới dùng endpoint Submit này")

    # Nếu Frontend báo chuyển tab, cờ gian lận bật lên!
    flagged = req.submit_reason == "tab_switch_violation"

    # TODO: Duyệt toàn bộ QuizProgress của user cho đề này, đối chiếu correct_answer để chấm điểm.
    # TODO: Lưu điểm tổng vào bảng QuizResult với attempt_status="completed", submit_reason=req.submit_reason

    return {"message": "Đã nộp bài!", "score": 85.5, "flagged_for_review": flagged}


@router.get("/history")
def get_quiz_history(
    document_id: Optional[int] = None,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)
):
    """Lấy danh sách các đề thi đã tạo."""
    query = db.query(Quiz)
    if document_id:
        query = query.filter(Quiz.document_id == document_id)

    return query.all()


@router.delete("/{quiz_id}/progress")
def reset_study_progress(
    quiz_id: int,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)
):
    """[CHỈ STUDY MODE] Xóa toàn bộ Progress để user làm lại từ đầu."""
    # TODO: Xóa các dòng trong QuizProgress thuộc về quiz_id và user_id này
    return {"message": "Đã reset quá trình học, bạn có thể bắt đầu lại."}
