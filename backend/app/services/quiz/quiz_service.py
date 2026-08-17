from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.exceptions.quiz import InvalidQuizOperationError, QuizNotFoundError
from app.models.document_model import Document
from app.models.quiz_model import Quiz, QuizAttempt, QuizProgress, QuizQuestion
from app.schemas.quiz_schema import QuizGenerateRequest
from app.services.quiz.quiz_pipeline import QuizPipeline, QuizPipelineResult

logger = logging.getLogger(__name__)


class QuizService:
    def __init__(self, db: Session, quiz_pipeline: QuizPipeline):
        self.db = db
        self.quiz_pipeline = quiz_pipeline

    # TẠO ĐỀ
    def create_quiz_placeholder(
        self,
        notebook_id: int,
        source_document_ids: List[int],
        user_id: int,
        title: str,
        mode: str,  # study | exam
        time_limit_minutes: Optional[int],  # required for exam mode
        target_total_points: Decimal,
        generation_strategy: str,  # manual | ai_recommended
        question_types: List[str],
        difficulty_distribution: Optional[Dict[str, float]],
        custom_instruction: Optional[str],
        total_questions: int,
    ) -> Quiz:
        # Schema validation
        if mode == "exam" and not time_limit_minutes:
            raise InvalidQuizOperationError(
                "Chế độ kiểm tra yêu cầu thiết lập thời gian làm bài (time_limit_minutes)."
            )

        if generation_strategy == "manual" and not difficulty_distribution:
            raise InvalidQuizOperationError(
                "Chiến lược tạo thủ công yêu cầu cung cấp phân bổ độ khó (difficulty_distribution)."
            )

        minimum_total = Decimal("0.01") * total_questions
        if target_total_points < minimum_total:
            raise InvalidQuizOperationError(
                "Tổng điểm phải cho phép ít nhất 0.01 điểm cho mỗi câu hỏi."
            )

        # TODO: Verify notebook ownership and document access via NotebookService / DocumentService if needed

        quiz = Quiz(
            notebook_id=notebook_id,
            source_document_ids=source_document_ids,
            user_id=user_id,
            title=title,
            mode=mode,
            time_limit_minutes=time_limit_minutes,
            target_total_points=target_total_points,
            generation_strategy=generation_strategy,
            question_types=question_types,
            difficulty_distribution=difficulty_distribution,
            custom_instruction=custom_instruction,
            total_questions=total_questions,
            generation_status="processing",
        )
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    async def run_generation(
        self,
        quiz_id: int,
        request: QuizGenerateRequest,
        merged_profile: Any = None,
    ) -> None:
        """Chạy trong BackgroundTasks, không được raise ra ngoài, bắt lỗi và ghi generation_status."""
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            return

        try:
            if quiz.generation_strategy != "manual":
                raise NotImplementedError(
                    "Chiến lược tạo đề ai_recommended hiện chưa được hỗ trợ."
                )

            result: QuizPipelineResult = await self.quiz_pipeline.run(
                request=request,
                merged_profile=merged_profile,
                document_ids=quiz.source_document_ids or [],
                query=getattr(request, "query", None),
            )

            if result is None:
                raise ValueError("Mô hình AI không trả về dữ liệu bộ đề.")

            final_request = result.final_request or request
            quiz_title = result.title
            questions = result.questions or []

            if not questions:
                raise ValueError(
                    "AI không thể sinh được câu hỏi nào từ tài liệu này. "
                    "Tài liệu có thể quá ngắn hoặc không đủ nội dung để tạo đề."
                )

            if len(questions) > final_request.total_questions:
                raise ValueError(
                    f"Pipeline sinh {len(questions)} câu, vượt quá số lượng yêu cầu "
                    f"({final_request.total_questions})."
                )

            quiz.mode = final_request.mode
            quiz.time_limit_minutes = final_request.time_limit_minutes
            quiz.total_questions = final_request.total_questions
            quiz.target_total_points = final_request.target_total_points
            quiz.question_types = final_request.question_types
            quiz.difficulty_distribution = final_request.difficulty_distribution

            normalized_questions: list[dict] = []

            for q in questions:
                if isinstance(q, dict):
                    q_data = q
                elif hasattr(q, "model_dump"):
                    q_data = q.model_dump()
                else:
                    raise TypeError(f"Unsupported question type: {type(q).__name__}")

                required_fields = [
                    "question_text",
                    "question_type",
                    "correct_answer",
                    "points",
                ]
                if q_data.get("question_type") in (
                    "multiple_choice",
                    "multiple_response",
                ):
                    required_fields.append("options")

                missing = [
                    field
                    for field in required_fields
                    if q_data.get(field) is None
                ]

                if missing:
                    raise ValueError(
                        f"Câu hỏi AI sinh thiếu các trường bắt buộc: {', '.join(missing)}."
                    )

                normalized_questions.append(q_data)

            # Lớp bảo vệ cuối cùng của backend:
            # luôn vá tổng điểm trước khi lưu DB.
            normalized_questions = self._patch_points_distributed(
                normalized_questions,
                final_request.target_total_points,
            )

            for q_data in normalized_questions:
                question_kwargs = {
                    "quiz_id": quiz.id,
                    "question_text": q_data["question_text"],
                    "question_type": q_data["question_type"],
                    "options": q_data.get("options"),
                    "statements": q_data.get("statements"),
                    "correct_answer": q_data["correct_answer"],
                    "explanations": q_data.get("explanations")
                    or q_data.get("explanation"),
                    "points": q_data["points"],
                    "hint": q_data.get("hint"),
                }

                if "difficulty" in q_data and hasattr(QuizQuestion, "difficulty"):
                    question_kwargs["difficulty"] = q_data["difficulty"]

                if (
                    "adaptive_metadata" in q_data
                    and hasattr(QuizQuestion, "adaptive_metadata")
                ):
                    question_kwargs["adaptive_metadata"] = q_data[
                        "adaptive_metadata"
                    ]

                if "chunk_ids" in q_data and hasattr(QuizQuestion, "chunk_ids"):
                    question_kwargs["chunk_ids"] = q_data["chunk_ids"]

                self.db.add(QuizQuestion(**question_kwargs))

            actual_count = len(normalized_questions)

            if actual_count < final_request.total_questions:
                quiz.error_message = (
                    f"Tài liệu không đủ nội dung để sinh đủ "
                    f"{final_request.total_questions} câu — "
                    f"thực tế tạo ra {actual_count} câu."
                )

            if quiz_title:
                quiz.title = quiz_title

            quiz.generation_status = "completed"
            self.db.commit()

        except Exception as e:
            self.db.rollback()

            quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
            if quiz:
                quiz.generation_status = "failed"
                quiz.error_message = str(e)
                self.db.commit()

            logger.exception(
                "Lỗi tiến trình sinh đề tự động cho đề thi %s",
                quiz_id,
            )

    @staticmethod
    def _patch_points_distributed(
        questions: List[dict],
        target: Decimal,
    ) -> List[dict]:
        quantum = Decimal("0.01")
        target = Decimal(str(target)).quantize(quantum, rounding=ROUND_HALF_UP)
        if target <= 0:
            raise ValueError("target_total_points phải lớn hơn 0.")

        if questions and target < quantum * len(questions):
            raise ValueError(
                "target_total_points phải cho phép ít nhất 0.01 điểm cho mỗi câu hỏi."
            )

        for question in questions:
            question["points"] = Decimal(str(question["points"])).quantize(
                quantum, rounding=ROUND_HALF_UP
            )

        drift = target - sum(
            (question["points"] for question in questions),
            start=Decimal("0.00"),
        )
        if drift == 0 or not questions:
            return questions

        if drift > 0:
            units = int(drift / quantum)
            base_units, remainder = divmod(units, len(questions))
            for index, question in enumerate(
                sorted(questions, key=lambda item: item["points"])
            ):
                added_units = base_units + (1 if index < remainder else 0)
                question["points"] += quantum * added_units
        else:
            units_to_remove = int(abs(drift) / quantum)
            while units_to_remove > 0:
                candidates = sorted(
                    (
                        question
                        for question in questions
                        if question["points"] > quantum
                    ),
                    key=lambda item: item["points"],
                    reverse=True,
                )
                if not candidates:
                    break

                batch_units = max(1, units_to_remove // len(candidates))
                removed_in_round = 0
                for question in candidates:
                    removable_units = int(
                        (question["points"] - quantum) / quantum
                    )
                    removed_units = min(
                        removable_units, batch_units, units_to_remove
                    )
                    question["points"] -= quantum * removed_units
                    units_to_remove -= removed_units
                    removed_in_round += removed_units
                    if units_to_remove == 0:
                        break

                if removed_in_round == 0:
                    break

            if units_to_remove > 0:
                raise ValueError(
                    f"Không thể hiệu chỉnh tổng điểm về {target} vì mọi câu đều đã ở mức tối thiểu 0.01 điểm."
                )

        logger.warning(f"AI sinh lệch tổng điểm, đã tự vá lại cho khớp target={target}")
        return questions

    # LÀM BÀI
    def get_quiz_for_rendering(self, quiz_id: int, user_id: int) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()

        attempt_query = self.db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id,
        )
        if quiz.mode == "study":
            active_attempt = attempt_query.order_by(desc(QuizAttempt.created_at)).first()
        else:
            active_attempt = attempt_query.filter(
                QuizAttempt.attempt_status == "in_progress"
            ).first()

        ordered_questions = self._get_ordered_questions(quiz_id, active_attempt)
        source_document_ids = quiz.source_document_ids or []
        source_documents = []
        if source_document_ids:
            documents = (
                self.db.query(Document)
                .filter(
                    Document.id.in_(source_document_ids),
                    Document.user_id == user_id,
                )
                .all()
            )
            titles_by_id = {document.id: document.title for document in documents}
            source_documents = [
                {
                    "id": document_id,
                    "title": titles_by_id.get(document_id, "Unavailable source"),
                }
                for document_id in source_document_ids
            ]

        progress_map = {}
        if active_attempt:
            progress_records = (
                self.db.query(QuizProgress)
                .filter(QuizProgress.attempt_id == active_attempt.id)
                .all()
            )
            progress_map = {p.question_id: p for p in progress_records}

        quiz_data = {
            "id": quiz.id,
            "notebook_id": quiz.notebook_id,
            "title": quiz.title,
            "mode": quiz.mode,
            "time_limit_minutes": quiz.time_limit_minutes,
            "target_total_points": float(quiz.target_total_points),
            "generation_status": quiz.generation_status,
            "error_message": quiz.error_message,
            "source_document_ids": source_document_ids,
            "source_documents": source_documents,
            "questions": [],
        }

        for q in ordered_questions:
            user_progress = progress_map.get(q.id)
            formatted_options = self._format_options(q.options)

            q_dict = {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": formatted_options,
                "statements": self._statements_for_rendering(
                    q.statements,
                    reveal_answers=quiz.mode == "study" and user_progress is not None,
                ),
                "points": float(q.points),
                "hint": q.hint,
                "user_answer": user_progress.user_answer if user_progress else None,
            }

            if quiz.mode == "study" and user_progress is not None:
                q_dict["correct_answer"] = q.correct_answer
                q_dict["explanations"] = q.explanations
                q_dict["is_correct"] = user_progress.is_correct
                q_dict["ai_feedback"] = user_progress.ai_feedback
                q_dict["awarded_points"] = (
                    float(user_progress.awarded_points)
                    if user_progress.awarded_points is not None
                    else None
                )

            quiz_data["questions"].append(q_dict)

        return quiz_data

    def delete_quiz(self, quiz_id: int, user_id: int) -> None:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()

        self.db.delete(quiz)
        self.db.commit()

    def get_quizzes(
        self,
        user_id: int,
        notebook_id: int | None = None,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Quiz).filter(Quiz.user_id == user_id)

        if notebook_id is not None:
            query = query.filter(Quiz.notebook_id == notebook_id)

        quizzes = query.order_by(desc(Quiz.created_at)).all()
        result = []
        normalized_study_attempt = False

        for quiz in quizzes:
            if quiz.generation_status != "completed":
                derived_status = quiz.generation_status
            else:
                latest_attempt = (
                    self.db.query(QuizAttempt)
                    .filter(
                        QuizAttempt.quiz_id == quiz.id,
                        QuizAttempt.user_id == user_id,
                    )
                    .order_by(desc(QuizAttempt.created_at))
                    .first()
                )

                if latest_attempt is None:
                    derived_status = "todo"
                elif latest_attempt.attempt_status == "in_progress":
                    if quiz.mode == "study" and self._complete_study_attempt_if_ready(
                        quiz.id, latest_attempt
                    ):
                        derived_status = "completed"
                        normalized_study_attempt = True
                    elif quiz.mode == "study" and not self.db.query(
                        QuizProgress
                    ).filter(QuizProgress.attempt_id == latest_attempt.id).first():
                        derived_status = "todo"
                    else:
                        derived_status = "in_progress"
                else:
                    derived_status = "completed"

            result.append(
                {
                    "id": quiz.id,
                    "notebook_id": quiz.notebook_id,
                    "title": quiz.title,
                    "mode": quiz.mode,
                    "total_questions": quiz.total_questions,
                    "time_limit_minutes": quiz.time_limit_minutes,
                    "generation_strategy": quiz.generation_strategy,
                    "difficulty_distribution": quiz.difficulty_distribution,
                    "generation_status": quiz.generation_status,
                    "derived_status": derived_status,
                    "error_message": quiz.error_message,
                    "created_at": quiz.created_at,
                }
            )

        if normalized_study_attempt:
            self.db.commit()

        return result

    def get_quiz_attempts_list(self, quiz_id: int, user_id: int) -> List[Dict[str, Any]]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()

        attempts = (
            self.db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
            .order_by(desc(QuizAttempt.created_at))
            .all()
        )
        return [
            {
                "id": a.id,
                "score": float(a.score) if a.score is not None else None,
                "attempt_status": a.attempt_status,
                "submit_reason": a.submit_reason,
                "started_at": a.started_at,
                "submitted_at": a.submitted_at,
                "duration_seconds": a.duration_seconds,
                "created_at": a.created_at,
            }
            for a in attempts
        ]

    def start_quiz_attempt(self, quiz_id: int, user_id: int) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()

        active_attempt = (
            self.db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
                QuizAttempt.attempt_status == "in_progress",
            )
            .order_by(desc(QuizAttempt.created_at))
            .first()
        )
        if active_attempt:
            return {
                "attempt_id": active_attempt.id,
                "attempt_status": active_attempt.attempt_status,
                "question_order": active_attempt.question_order,
            }

        latest_attempt = (
            self.db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
            )
            .order_by(desc(QuizAttempt.created_at))
            .first()
        )
        if quiz.mode == "study" and latest_attempt:
            return {
                "attempt_id": latest_attempt.id,
                "attempt_status": latest_attempt.attempt_status,
                "question_order": latest_attempt.question_order,
            }

        attempt = self._create_attempt(
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_status="in_progress",
            previous_question_order=(
                latest_attempt.question_order if latest_attempt else None
            ),
        )
        self.db.commit()
        return {
            "attempt_id": attempt.id,
            "attempt_status": attempt.attempt_status,
            "question_order": attempt.question_order,
        }

    def get_attempt_detail(self, attempt_id: int, user_id: int) -> Dict[str, Any]:
        attempt = self.db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
        if not attempt or attempt.user_id != user_id:
            raise QuizNotFoundError()

        progresses = self.db.query(QuizProgress).filter(QuizProgress.attempt_id == attempt.id).all()
        progress_map = {p.question_id: p for p in progresses}

        ordered_questions = self._get_ordered_questions(attempt.quiz_id, attempt)

        question_details = []

        for q in ordered_questions:
            p = progress_map.get(q.id)
            formatted_options = self._format_options(q.options)

            question_details.append(
                {
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "options": formatted_options,
                    "statements": q.statements,
                    "correct_answer": q.correct_answer,
                    "explanations": q.explanations,
                    "points": float(q.points),
                    "user_answer": p.user_answer if p else None,
                    "is_correct": p.is_correct if p else None,
                    "ai_feedback": p.ai_feedback if p else None,
                    "awarded_points": (
                        float(p.awarded_points)
                        if p and p.awarded_points is not None
                        else None
                    ),
                    "mark_status": p.mark_status if p else None,
                }
            )

        return {
            "id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "score": float(attempt.score) if attempt.score is not None else None,
            "attempt_status": attempt.attempt_status,
            "submit_reason": attempt.submit_reason,
            "started_at": attempt.started_at,
            "submitted_at": attempt.submitted_at,
            "duration_seconds": attempt.duration_seconds,
            "created_at": attempt.created_at,
            "questions": question_details,
        }

    def get_quiz_hints(
        self,
        quiz_id: int,
        user_id: int,
    ) -> list[dict]:
        quiz = (
            self.db.query(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.user_id == user_id,
            )
            .first()
        )

        if quiz is None:
            raise QuizNotFoundError()

        questions = (
            self.db.query(QuizQuestion)
            .filter(
                QuizQuestion.quiz_id == quiz_id,
            )
            .order_by(QuizQuestion.id)
            .all()
        )

        return [
            {
                "question_id": q.id,
                "hint": q.hint,
            }
            for q in questions
        ]

    def get_processing_quizzes(
        self,
        user_id: int,
    ) -> list[dict]:
        quizzes = (
            self.db.query(Quiz)
            .filter(
                Quiz.user_id == user_id,
                Quiz.generation_status == "processing",
            )
            .order_by(desc(Quiz.created_at))
            .all()
        )

        return [
            {
                "id": quiz.id,
                "title": quiz.title,
                "notebook_id": quiz.notebook_id,
                "notebook_title": quiz.notebook.title,
                "generation_strategy": quiz.generation_strategy,
                "generation_status": quiz.generation_status,
                "total_questions": quiz.total_questions,
                "created_at": quiz.created_at,
            }
            for quiz in quizzes
        ]

    def save_single_answer_progress(
        self,
        quiz_id: int,
        question_id: int,
        user_id: int,
        user_answer: Any,
        essay_result: tuple[Decimal, str] | None = None,
    ) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()
        if quiz.mode != "study":
            raise InvalidQuizOperationError("Chế độ chấm từng câu chỉ áp dụng cho chế độ học tập.")

        question = (
            self.db.query(QuizQuestion)
            .filter(QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz_id)
            .first()
        )
        if not question:
            raise QuizNotFoundError("Không tìm thấy câu hỏi thuộc đề thi này.")

        active_attempt = (
            self.db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
            )
            .order_by(desc(QuizAttempt.created_at))
            .first()
        )

        if not active_attempt:
            active_attempt = self._create_attempt(
                quiz_id=quiz_id,
                user_id=user_id,
                attempt_status="in_progress",
            )

        if question.question_type == "essay":
            if essay_result is None:
                raise InvalidQuizOperationError("Essay answers require AI rubric grading.")
            awarded_points, ai_feedback = essay_result
            is_correct = awarded_points == question.points
        else:
            awarded_points = self._calculate_question_score(
                question.question_type,
                question.correct_answer,
                user_answer,
                question.points,
            )
            ai_feedback = None
            is_correct = awarded_points == question.points

        progress = (
            self.db.query(QuizProgress)
            .filter(
                QuizProgress.attempt_id == active_attempt.id,
                QuizProgress.question_id == question_id,
            )
            .first()
        )
        if progress:
            progress.user_answer = user_answer
            progress.is_correct = is_correct
            progress.awarded_points = awarded_points
            progress.ai_feedback = ai_feedback
        else:
            progress = QuizProgress(
                attempt_id=active_attempt.id,
                user_id=user_id,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
                awarded_points=awarded_points,
                ai_feedback=ai_feedback,
            )
            self.db.add(progress)

        self.db.flush()
        self._complete_study_attempt_if_ready(quiz_id, active_attempt)

        self.db.commit()

        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "explanations": question.explanations,
            "statements": question.statements,
            "awarded_points": float(awarded_points),
            "ai_feedback": ai_feedback,
        }

    async def grade_and_save_single_answer_progress(
        self, quiz_id: int, question_id: int, user_id: int, user_answer: Any
    ) -> Dict[str, Any]:
        question = (
            self.db.query(QuizQuestion)
            .filter(QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz_id)
            .first()
        )
        essay_result = None
        if question and question.question_type == "essay":
            essay_result = await self._grade_essay_answer(
                question.question_text,
                question.correct_answer,
                user_answer,
                question.points,
            )
        return self.save_single_answer_progress(
            quiz_id,
            question_id,
            user_id,
            user_answer,
            essay_result=essay_result,
        )

    def submit_entire_quiz(
        self,
        quiz_id: int,
        user_id: int,
        answers_payload: List[Dict[str, Any]],
        submit_reason: str,
        essay_results: Optional[Dict[int, tuple[Decimal, str]]] = None,
    ) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()
        if quiz.mode != "exam":
            raise InvalidQuizOperationError(
                "Chế độ nộp bài tổng hợp chỉ áp dụng cho chế độ kiểm tra."
            )

        questions = self.db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        submissions_by_qid = {
            item.get("question_id"): item for item in answers_payload
        }

        total_score = Decimal("0.00")
        correct_count = 0

        quiz_attempt = (
            self.db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
                QuizAttempt.attempt_status == "in_progress",
            )
            .first()
        )

        submitted_at = datetime.now(timezone.utc)

        if not quiz_attempt:
            quiz_attempt = self._create_attempt(
                quiz_id=quiz_id,
                user_id=user_id,
                attempt_status="completed",
                submit_reason=submit_reason,
            )
            quiz_attempt.submitted_at = submitted_at
            quiz_attempt.duration_seconds = 0
        else:
            quiz_attempt.attempt_status = "completed"
            quiz_attempt.submit_reason = submit_reason
            quiz_attempt.submitted_at = submitted_at

            start_time = quiz_attempt.started_at or submitted_at
            duration_end = (
                submitted_at.replace(tzinfo=None)
                if start_time.tzinfo is None
                else submitted_at
            )
            duration = (duration_end - start_time).total_seconds()
            quiz_attempt.duration_seconds = max(0, int(duration))

        response_details = []

        for question in questions:
            q_id = question.id
            submission = submissions_by_qid.get(q_id, {})
            u_ans = submission.get("user_answer")
            mark_status = submission.get("mark_status")
            ai_feedback = None
            if question.question_type == "essay":
                awarded_points, ai_feedback = (essay_results or {}).get(
                    q_id,
                    (Decimal("0.00"), "Essay grading was unavailable."),
                )
            else:
                awarded_points = self._calculate_question_score(
                    question.question_type,
                    question.correct_answer,
                    u_ans,
                    question.points,
                )
            is_correct = awarded_points == question.points
            total_score += awarded_points
            if is_correct:
                correct_count += 1

            progress = QuizProgress(
                attempt_id=quiz_attempt.id,
                user_id=user_id,
                question_id=q_id,
                user_answer=u_ans,
                is_correct=is_correct,
                awarded_points=awarded_points,
                ai_feedback=ai_feedback,
                mark_status=mark_status,
            )
            self.db.add(progress)

            response_details.append(
                {
                    "question_id": q_id,
                    "user_answer": u_ans,
                    "is_correct": is_correct,
                    "correct_answer": question.correct_answer,
                    "explanations": question.explanations,
                    "statements": question.statements,
                    "awarded_points": float(awarded_points),
                    "ai_feedback": ai_feedback,
                    "mark_status": mark_status,
                }
            )

        quiz_attempt.score = total_score
        self.db.commit()

        return {
            "attempt_id": quiz_attempt.id,
            "score": float(total_score),
            "score_scale": float(quiz.target_total_points),
            "gradable_max": float(quiz.target_total_points),
            "correct_answers_count": correct_count,
            "total_questions": len(questions),
            "submit_reason": submit_reason,
            "duration_seconds": quiz_attempt.duration_seconds,
            "details": response_details,
        }

    async def grade_and_submit_entire_quiz(
        self,
        quiz_id: int,
        user_id: int,
        answers_payload: List[Dict[str, Any]],
        submit_reason: str,
    ) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()
        if quiz.mode != "exam":
            raise InvalidQuizOperationError(
                "Chế độ nộp bài tổng hợp chỉ áp dụng cho chế độ kiểm tra."
            )

        submissions_by_qid = {
            item.get("question_id"): item for item in answers_payload
        }
        essay_results: Dict[int, tuple[Decimal, str]] = {}
        essay_questions = (
            self.db.query(QuizQuestion)
            .filter(
                QuizQuestion.quiz_id == quiz_id,
                QuizQuestion.question_type == "essay",
            )
            .all()
        )
        for question in essay_questions:
            user_answer = submissions_by_qid.get(question.id, {}).get("user_answer")
            essay_results[question.id] = await self._grade_essay_answer(
                question.question_text,
                question.correct_answer,
                user_answer,
                question.points,
            )

        return self.submit_entire_quiz(
            quiz_id,
            user_id,
            answers_payload,
            submit_reason,
            essay_results=essay_results,
        )

    def clear_quiz_progress(self, quiz_id: int, user_id: int) -> None:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()
        if quiz.mode != "study":
            raise InvalidQuizOperationError(
                "Chỉ có thể xóa tiến trình của quiz ở chế độ học tập."
            )

        attempts = (
            self.db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
            )
            .all()
        )
        if attempts:
            previous_question_order = attempts[0].question_order
            attempt_ids = [attempt.id for attempt in attempts]
            self.db.query(QuizProgress).filter(
                QuizProgress.attempt_id.in_(attempt_ids)
            ).delete(synchronize_session=False)
            for attempt in attempts:
                self.db.delete(attempt)
            self.db.flush()
            self._create_attempt(
                quiz_id=quiz_id,
                user_id=user_id,
                attempt_status="in_progress",
                previous_question_order=previous_question_order,
            )
            self.db.commit()

    def _create_attempt(
        self,
        quiz_id: int,
        user_id: int,
        attempt_status: str = "in_progress",
        submit_reason: Optional[str] = None,
        previous_question_order: Optional[List[int]] = None,
    ) -> QuizAttempt:
        questions = (
            self.db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.id)
            .all()
        )
        question_ids = [q.id for q in questions]
        if previous_question_order is None:
            latest_attempt = (
                self.db.query(QuizAttempt)
                .filter(
                    QuizAttempt.quiz_id == quiz_id,
                    QuizAttempt.user_id == user_id,
                )
                .order_by(desc(QuizAttempt.created_at))
                .first()
            )
            previous_question_order = (
                latest_attempt.question_order if latest_attempt else None
            )
        question_order = self._shuffle_question_order(
            question_ids,
            previous_question_order,
        )
        now = datetime.now(timezone.utc)
        attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_status=attempt_status,
            submit_reason=submit_reason,
            started_at=now,
            question_order=question_order,
        )
        self.db.add(attempt)
        self.db.flush()
        return attempt

    @staticmethod
    def _shuffle_question_order(
        question_ids: List[int],
        previous_question_order: Optional[List[int]] = None,
    ) -> List[int]:
        question_order = list(question_ids)
        random.shuffle(question_order)
        if (
            len(question_order) > 1
            and previous_question_order
            and question_order == list(previous_question_order)
        ):
            question_order = question_order[1:] + question_order[:1]
        return question_order

    def _complete_study_attempt_if_ready(
        self, quiz_id: int, attempt: QuizAttempt
    ) -> bool:
        if attempt.attempt_status == "completed":
            return True

        answered_count = (
            self.db.query(QuizProgress)
            .filter(QuizProgress.attempt_id == attempt.id)
            .count()
        )
        question_count = (
            self.db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz_id)
            .count()
        )
        if question_count == 0 or answered_count < question_count:
            return False

        attempt.attempt_status = "completed"
        attempt.submitted_at = datetime.now(timezone.utc)
        return True

    def _get_ordered_questions(
        self, quiz_id: int, attempt: Optional[QuizAttempt] = None
    ) -> List[QuizQuestion]:
        all_questions = self.db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        if attempt and attempt.question_order:
            questions_by_id = {q.id: q for q in all_questions}
            return [
                questions_by_id[qid] for qid in attempt.question_order if qid in questions_by_id
            ]
        return sorted(all_questions, key=lambda q: q.id)

    def _format_options(self, options: Optional[List[Any]]) -> Optional[List[Dict[str, Any]]]:
        if not options or not isinstance(options, list):
            return None

        formatted_options = []
        for idx, opt in enumerate(options):
            if isinstance(opt, str):
                if "." in opt:
                    parts = opt.split(".", 1)
                    opt_id = parts[0].strip()
                    opt_text = parts[1].strip()
                else:
                    opt_id = chr(65 + idx)
                    opt_text = opt

                formatted_options.append({"id": opt_id, "text": opt_text, "option_text": opt})
            elif isinstance(opt, dict):
                option = opt.copy()
                if "id" not in option:
                    option["id"] = option.get("key") or chr(65 + idx)
                formatted_options.append(option)

        return formatted_options

    @staticmethod
    def _statements_for_rendering(
        statements: Any, *, reveal_answers: bool
    ) -> Optional[List[Dict[str, Any]]]:
        if not isinstance(statements, list):
            return None
        if reveal_answers:
            return statements
        return [
            {"text": statement.get("text", "")}
            for statement in statements
            if isinstance(statement, dict)
        ]

    @staticmethod
    def _normalize_answer(value: Any) -> str:
        return " ".join(str(value).strip().casefold().split())

    @staticmethod
    def _parse_bool(value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().casefold()
        if normalized in {"true", "1", "t"}:
            return True
        if normalized in {"false", "0", "f"}:
            return False
        return None

    def _calculate_question_score(
        self,
        question_type: str,
        correct_val: Any,
        user_val: Any,
        question_points: Any,
    ) -> Decimal:
        points = Decimal(str(question_points))
        zero = Decimal("0.00")
        if user_val is None:
            return zero

        if question_type == "multiple_response":
            if not isinstance(correct_val, list) or not correct_val or not isinstance(user_val, list):
                return zero
            def clean(value: Any) -> str:
                return str(value).strip().split(".", 1)[0].strip().casefold()

            correct = {clean(value) for value in correct_val}
            selected = {clean(value) for value in user_val}
            correct_selected = len(correct & selected)
            incorrect_selected = len(selected - correct)
            earned_units = max(0, correct_selected - incorrect_selected)
            score = Decimal(earned_units) * (points / Decimal(len(correct)))
            return min(points, score).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if question_type == "true_false":
            if not isinstance(correct_val, list) or not correct_val or not isinstance(user_val, list):
                return zero
            matched = sum(
                1
                for index, correct in enumerate(correct_val)
                if index < len(user_val) and self._parse_bool(user_val[index]) == correct
            )
            score = Decimal(matched) * (points / Decimal(len(correct_val)))
            return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return points if self._grade_logic(question_type, correct_val, user_val) else zero

    async def _grade_essay_answer(
        self,
        question_text: str,
        rubric: Any,
        user_answer: Any,
        question_points: Any,
    ) -> tuple[Decimal, str]:
        expected_points = rubric if isinstance(rubric, list) else []
        if not expected_points:
            return Decimal("0.00"), "No rubric was available for grading."
        if not str(user_answer or "").strip():
            return Decimal("0.00"), "No answer was provided."

        llm = getattr(self.quiz_pipeline, "llm", None)
        if llm is None:
            raise InvalidQuizOperationError("Essay grading service is unavailable.")

        prompt = f"""You grade one essay against a fixed rubric.
Return ONLY valid JSON with this shape:
{{"achieved_points_count": 0, "feedback": "brief grounded feedback"}}

Rules:
- Count a rubric point only when the answer clearly demonstrates it.
- achieved_points_count must be an integer from 0 to {len(expected_points)}.
- Do not calculate a score.
- Write feedback in the same language as the question.
- Keep feedback concise: at most two short sentences.
- State only how many rubric points were achieved and give high-level guidance.
- Never quote, list, paraphrase, summarize, or reveal the rubric points.
- Never provide examples, a model answer, or a checklist of expected content.
- Do not repeat the question or instruct the student to include specific rubric content.

Question:
{question_text}

Rubric points:
{json.dumps(expected_points, ensure_ascii=False)}

Student answer:
{str(user_answer)}
"""
        raw_response = (await llm.generate(prompt=prompt)).strip()
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_response)
        payload = json.loads(fenced.group(1) if fenced else raw_response)
        achieved = payload.get("achieved_points_count", 0)
        if isinstance(achieved, bool) or not isinstance(achieved, int):
            raise ValueError("Essay grader returned a non-integer achieved_points_count.")
        achieved = max(0, min(len(expected_points), achieved))
        points = Decimal(str(question_points))
        score = (Decimal(achieved) * points / Decimal(len(expected_points))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return score, str(payload.get("feedback") or "")

    def _grade_logic(self, question_type: str, correct_val: Any, user_val: Any) -> bool:
        if user_val is None:
            return False

        def clean_option(val: Any) -> str:
            return str(val).strip().split(".")[0].strip().lower()

        if question_type == "multiple_choice":
            return clean_option(correct_val) == clean_option(user_val)

        elif question_type == "multiple_response":
            c_list = correct_val if isinstance(correct_val, list) else [correct_val]
            u_list = user_val if isinstance(user_val, list) else [user_val]

            set_correct = set(clean_option(x) for x in c_list if x is not None)
            set_user = set(clean_option(x) for x in u_list if x is not None)

            return set_correct == set_user

        elif question_type == "true_false":
            if not isinstance(correct_val, list) or not isinstance(user_val, list):
                return False
            return len(correct_val) == len(user_val) and all(
                self._parse_bool(user_val[index]) == correct
                for index, correct in enumerate(correct_val)
            )

        elif question_type == "fill_blank":
            acceptable = correct_val if isinstance(correct_val, list) else [correct_val]
            normalized_user = self._normalize_answer(user_val)
            return any(self._normalize_answer(answer) == normalized_user for answer in acceptable)

        elif question_type == "short_answer":
            return self._normalize_answer(correct_val) == self._normalize_answer(user_val)

        return False
