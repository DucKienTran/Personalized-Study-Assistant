import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.exceptions import NotFoundError, BadRequestError
from app.models.quiz_model import Quiz, QuizQuestion, QuizResult, QuizProgress
from app.ai.prompt.quiz_prompt import QuizPrompt
from app.ai.output.quiz_parser import QuizParser
from app.ai.llm.base import LLMClient

logger = logging.getLogger(__name__)

class QuizNotFoundError(NotFoundError):
    error_code = "quiz_not_found"
    def __init__(self, message: str = "Không tìm thấy đề thi phù hợp."):
        super().__init__(message)

class InvalidQuizOperationError(BadRequestError):
    error_code = "invalid_quiz_operation"
    def __init__(self, message: str = "Hành động không hợp lệ với chế độ của đề thi."):
        super().__init__(message)


class QuizService:
    def __init__(self, db: Session, document_service: Any, ai_client: LLMClient):
        self.db = db
        self.document_service = document_service
        self.ai_client = ai_client

    def create_quiz_placeholder(self, document_id: int, user_id: int, title: str, mode: str, time_limit: Optional[int]) -> Quiz:
        quiz = Quiz(
            document_id=document_id,
            user_id=user_id,
            title=title,
            mode=mode,
            time_limit_minutes=time_limit,
            status="processing"
        )
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    async def run_generation(self, quiz_id: int, question_types: List[str], total_questions: int, level: str) -> None:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            return
        
        try:
            document_data = await self.document_service.get_document_content(quiz.document_id)
            if not document_data or "content_raw" not in document_data:
                raise ValueError("Không thể lấy nội dung thô từ tài liệu.")

            prompt = QuizPrompt.generate_quiz_prompt(
                content_raw=document_data["content_raw"],
                question_types=question_types,
                total_questions=total_questions,
                level=level
            )
            
            ai_response_text = await self.ai_client.generate(prompt)
            if not ai_response_text:
                raise ValueError("Mô hình ai không trả về dữ liệu bộ đề.")

            questions_parsed = QuizParser.parse_quiz_response(ai_response_text)
            
            for q_data in questions_parsed:
                question = QuizQuestion(
                    quiz_id=quiz_id,
                    question_text=q_data["question_text"],
                    question_type=q_data["question_type"],
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    explanations=q_data["explanations"],
                    points=q_data["points"],
                    hint=q_data["hint"]
                )
                self.db.add(question)
            
            quiz.status = "completed"
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            quiz.status = "failed"
            self.db.commit()
            logger.error(f"Lỗi tiến trình sinh đề tự động cho đề thi {quiz_id}: {str(e)}")

    def get_quiz_for_rendering(self, quiz_id: int, user_id: int) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise QuizNotFoundError()

        questions = self.db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        
        active_result = self.db.query(QuizResult).filter(
            QuizResult.quiz_id == quiz_id,
            QuizResult.user_id == user_id,
            QuizResult.attempt_status == "in_progress"
        ).first()

        progress_map = {}
        if active_result:
            progress_records = self.db.query(QuizProgress).filter(
                QuizProgress.result_id == active_result.id
            ).all()
            progress_map = {p.question_id: p for p in progress_records}

        quiz_data = {
            "id": quiz.id,
            "title": quiz.title,
            "mode": quiz.mode,
            "time_limit_minutes": quiz.time_limit_minutes,
            "status": quiz.status,
            "questions": []
        }

        for q in questions:
            user_progress = progress_map.get(q.id)
            q_dict = {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options,
                "points": q.points,
                "hint": q.hint if quiz.mode == "study" else None,
                "user_answer": user_progress.user_answer if user_progress else None
            }
            
            if quiz.mode == "study" and user_progress:
                q_dict["correct_answer"] = q.correct_answer
                q_dict["explanations"] = q.explanations
                q_dict["is_correct"] = user_progress.is_correct
                q_dict["ai_feedback"] = user_progress.ai_feedback
                
            quiz_data["questions"].append(q_dict)

        return quiz_data

    def save_single_answer_progress(self, quiz_id: int, question_id: int, user_id: int, user_answer: Any) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise QuizNotFoundError()
        if quiz.mode != "study":
            raise InvalidQuizOperationError("Chế độ chấm từng câu chỉ áp dụng cho chế độ học tập.")

        question = self.db.query(QuizQuestion).filter(
            QuizQuestion.id == question_id, 
            QuizQuestion.quiz_id == quiz_id
        ).first()
        if not question:
            raise QuizNotFoundError("Không tìm thấy câu hỏi thuộc đề thi này.")

        active_result = self.db.query(QuizResult).filter(
            QuizResult.quiz_id == quiz_id,
            QuizResult.user_id == user_id,
            QuizResult.attempt_status == "in_progress"
        ).first()

        if not active_result:
            active_result = QuizResult(
                quiz_id=quiz_id,
                user_id=user_id,
                attempt_status="in_progress"
            )
            self.db.add(active_result)
            self.db.flush()

        is_correct = None
        q_type = question.question_type

        if q_type != "essay":
            is_correct = self._grade_logic(q_type, question.correct_answer, user_answer)

        progress = self.db.query(QuizProgress).filter(
            QuizProgress.result_id == active_result.id,
            QuizProgress.question_id == question_id
        ).first()

        if progress:
            progress.user_answer = user_answer
            progress.is_correct = is_correct
        else:
            progress = QuizProgress(
                result_id=active_result.id,
                user_id=user_id,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct
            )
            self.db.add(progress)

        self.db.commit()

        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "explanations": question.explanations
        }

    def submit_entire_quiz(self, quiz_id: int, user_id: int, answers_payload: List[Dict[str, Any]], submit_reason: str) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise QuizNotFoundError()
        if quiz.mode != "exam":
            raise InvalidQuizOperationError("Chế độ nộp bài tổng hợp chỉ áp dụng cho chế độ thi cử.")

        questions = self.db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        answers_by_qid = {item.get("question_id"): item.get("user_answer") for item in answers_payload}

        total_score = 0.0
        correct_count = 0
        total_questions = len(questions)
        max_possible_points = sum(q.points for q in questions if q.question_type != "essay")

        quiz_result = QuizResult(
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_status="completed",
            submit_reason=submit_reason
        )
        self.db.add(quiz_result)
        self.db.flush()

        response_details = []

        for question in questions:
            q_id = question.id
            u_ans = answers_by_qid.get(q_id)
            q_type = question.question_type
            is_correct = None

            if q_type != "essay":
                is_correct = self._grade_logic(q_type, question.correct_answer, u_ans) if u_ans is not None else False
                if is_correct:
                    correct_count += 1
                    total_score += float(question.points)
            
            progress = QuizProgress(
                result_id=quiz_result.id,
                user_id=user_id,
                question_id=q_id,
                user_answer=u_ans,
                is_correct=is_correct
            )
            self.db.add(progress)

            response_details.append({
                "question_id": q_id,
                "user_answer": u_ans,
                "is_correct": is_correct,
                "correct_answer": question.correct_answer,
                "explanations": question.explanations
            })

        quiz_result.score = (total_score / max_possible_points * 100) if max_possible_points > 0 else 0.0
        self.db.commit()

        return {
            "result_id": quiz_result.id,
            "score": quiz_result.score,
            "correct_answers_count": correct_count,
            "total_questions": total_questions,
            "submit_reason": submit_reason,
            "details": response_details
        }

    def clear_quiz_progress(self, quiz_id: int, user_id: int) -> None:
        active_result = self.db.query(QuizResult).filter(
            QuizResult.quiz_id == quiz_id,
            QuizResult.user_id == user_id,
            QuizResult.attempt_status == "in_progress"
        ).first()
        
        if active_result:
            self.db.query(QuizProgress).filter(QuizProgress.result_id == active_result.id).delete()
            self.db.delete(active_result)
            self.db.commit()

    def get_user_quiz_history(self, user_id: int, document_id: Optional[int] = None) -> List[QuizResult]:
        query = self.db.query(QuizResult).filter(QuizResult.user_id == user_id)
        if document_id:
            query = query.join(Quiz).filter(Quiz.document_id == document_id)
        return query.order_by(desc(QuizResult.created_at)).all()

    def _grade_logic(self, question_type: str, correct_val: Any, user_val: Any) -> bool:
        if user_val is None:
            return False

        if question_type == "multiple_choice":
            return str(correct_val).strip().lower() == str(user_val).strip().lower()

        elif question_type == "multiple_response":
            if not isinstance(correct_val, list) or not isinstance(user_val, list):
                return False
            return set(str(x).strip().lower() for x in correct_val) == set(str(x).strip().lower() for x in user_val)

        elif question_type == "true_false":
            def parse_bool(v: Any) -> Optional[bool]:
                if isinstance(v, bool):
                    return v
                s = str(v).strip().lower()
                if s in ["true", "1", "t"]:
                    return True
                if s in ["false", "0", "f"]:
                    return False
                return None
            return parse_bool(correct_val) == parse_bool(user_val)

        elif question_type == "fill_blank":
            acceptable = correct_val if isinstance(correct_val, list) else [correct_val]
            u_str = str(user_val).strip().lower()
            return any(str(c).strip().lower() == u_str for c in acceptable)

        elif question_type == "short_answer":
            c_str = str(correct_val).replace(",", ".").strip().lower()
            u_str = str(user_val).replace(",", ".").strip().lower()
            return c_str == u_str

        return False