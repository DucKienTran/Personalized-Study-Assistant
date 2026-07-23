import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMClient
from app.ai.output.quiz_parser import QuizParser
from app.ai.prompts.quiz_prompt import QuizPromptBuilder
from app.exceptions.quiz import InvalidQuizOperationError, QuizNotFoundError
from app.models.quiz_model import Quiz, QuizAttempt, QuizProgress, QuizQuestion
from app.services.document.document_service import DocumentService
from app.models.document_model import Document

logger = logging.getLogger(__name__)


class QuizService:
    def __init__(
        self, db: Session, document_service: DocumentService, ai_client: LLMClient
    ):
        self.db = db
        self.document_service = document_service
        self.ai_client = ai_client

    # TẠO ĐỀ
    def create_quiz_placeholder(
        self,
        document_id: int,
        user_id: int,
        title: str,
        mode: str,  # study | exam
        time_limit_minutes: Optional[int],  # only for exam
        target_total_points: int,  # only for custom gen mode
        generation_mode: str,  # simple | custome
        difficulty: Optional[str],  # easy | medium | hard | mixed
        custom_instruction: Optional[str],
        total_questions: int,
    ) -> Quiz:

        # Kiểm tra tài liệu có thuộc user này không
        doc = self.document_service.get_document(
            user_id=user_id, document_id=document_id
        )
        if not doc:
            raise QuizNotFoundError("Không tìm thấy tài liệu để tạo đề thi.")

        quiz = Quiz(
            document_id=document_id,
            user_id=user_id,
            title=title,
            mode=mode,
            time_limit_minutes=time_limit_minutes,
            target_total_points=target_total_points,
            generation_mode=generation_mode,
            difficulty=difficulty,
            custom_instruction=custom_instruction,
            total_questions=total_questions,
            generation_status="processing",
        )
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    async def run_generation(
        self, quiz_id: int, question_types: List[str], total_questions: int
    ) -> None:
        """Chạy trong BackgroundTasks, không được raise ra ngoài, bắt lỗi và ghi generation_status (trạng thái tạo đề)."""
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            return

        try:
            document_data = await self.document_service.get_document_content(
                quiz.document_id, quiz.user_id
            )
            if not document_data or "content_raw" not in document_data:
                raise ValueError("Không thể lấy nội dung thô từ tài liệu.")

            prompt = QuizPromptBuilder.build(
                generation_mode=quiz.generation_mode,
                content_raw=document_data["content_raw"],
                total_questions=total_questions,
                target_total_points=quiz.target_total_points,
                question_types=question_types,
                difficulty=quiz.difficulty,
                custom_instruction=quiz.custom_instruction,
            )

            ai_response_text = await self.ai_client.generate(prompt)
            if not ai_response_text:
                raise ValueError("Mô hình AI không trả về dữ liệu bộ đề.")

            parsed_result = QuizParser.parse_quiz_response(ai_response_text)

            questions = parsed_result["questions"]
            quiz_title = parsed_result["quiz_title"]
            if not questions:
                raise ValueError(
                    "AI không thể sinh được câu hỏi nào từ tài liệu này. "
                    "Tài liệu có thể quá ngắn hoặc không đủ nội dung để tạo đề."
                )

            questions = self._patch_points_distributed(
                questions,
                quiz.target_total_points,
            )
            for q_data in questions:
                question = QuizQuestion(
                    quiz_id=quiz_id,
                    question_text=q_data["question_text"],
                    question_type=q_data["question_type"],
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    explanations=q_data["explanations"],
                    points=q_data["points"],
                    hint=q_data["hint"],
                )
                self.db.add(question)

            # Gửi về thông báo nếu không thể sinh đủ số lượng câu so với đề
            actual_count = len(questions)
            if actual_count < total_questions:
                quiz.error_message = (
                    f"Tài liệu không đủ nội dung để sinh đủ {total_questions} câu — "
                    f"thực tế tạo ra {actual_count} câu."
                )
            quiz.title = quiz_title
            quiz.generation_status = "completed"
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            quiz.generation_status = "failed"
            quiz.error_message = str(e)
            self.db.commit()
            logger.error(
                f"Lỗi tiến trình sinh đề tự động cho đề thi {quiz_id}: {str(e)}"
            )

    @staticmethod
    def _patch_points_distributed(questions: List[dict], target: int) -> List[dict]:
        """Dùng để vá nếu tổng số điểm do AI sinh ra không bằng Quiz[target_total_points].
        Nếu tổng điểm các câu hỏi do AI sinh ra nhỏ hơn thì cộng lần lượt 1đ vào các
        câu hỏi có điểm cao nhất cho đến khi tổng điểm bằng target_total_points. Nếu lớn hơn
        thì trừ lần lượt, nếu mọi câu đều trừ về còn 1đ mà vẫn chưa bằng nhau thì báo lỗi
        """
        drift = target - sum(q["points"] for q in questions)
        if drift == 0 or not questions:
            return questions

        if drift > 0:
            while drift > 0:
                for q in sorted(questions, key=lambda x: x["points"]):
                    q["points"] += 1
                    drift -= 1
                    if drift == 0:
                        break
        else:
            drift = abs(drift)
            while drift > 0:
                candidates = [q for q in questions if q["points"] > 1]
                if not candidates:
                    raise ValueError(
                        f"Không thể hiệu chỉnh tổng điểm về {target} vì mọi câu đều đã ở mức tối thiểu 1 điểm. "
                        f"Hãy tăng target_total_points hoặc giảm total_questions."
                    )
                for q in sorted(candidates, key=lambda x: x["points"], reverse=True):
                    q["points"] -= 1
                    drift -= 1
                    if drift == 0:
                        break

        logger.warning(f"AI sinh lệch tổng điểm, đã tự vá lại cho khớp target={target}")
        return questions

    # LÀM BÀI
    def get_quiz_for_rendering(self, quiz_id: int, user_id: int) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()

        questions = (
            self.db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        )

        active_attempt = (
            self.db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
                QuizAttempt.attempt_status == "in_progress",
            )
            .first()
        )

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
            "title": quiz.title,
            "mode": quiz.mode,
            "time_limit_minutes": quiz.time_limit_minutes,
            "target_total_points": quiz.target_total_points,
            "generation_status": quiz.generation_status,
            "error_message": quiz.error_message,
            "questions": [],
        }

        for q in questions:
            user_progress = progress_map.get(q.id)

            # Chuẩn hóa danh sách options
            formatted_options = None
            if q.options and isinstance(q.options, list):
                formatted_options = []
                for idx, opt in enumerate(q.options):
                    if isinstance(opt, str):
                        if "." in opt:
                            parts = opt.split(".", 1)
                            opt_id = parts[0].strip()
                            opt_text = parts[1].strip()
                        else:
                            opt_id = chr(65 + idx)
                            opt_text = opt

                        formatted_options.append(
                            {"id": opt_id, "text": opt_text, "option_text": opt}
                        )
                    elif isinstance(opt, dict):
                        if "id" not in opt:
                            opt["id"] = opt.get("key") or chr(65 + idx)
                        formatted_options.append(opt)

            q_dict = {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": formatted_options,
                "points": q.points,
                "hint": q.hint,
                # Lấy câu trả lời đã lưu trong DB (nếu có) để khôi phục khi F5
                "user_answer": user_progress.user_answer if user_progress else None,
            }

            # Chế độ học tập (study): Luôn hiển thị giải thích và đáp án chuẩn
            if quiz.mode == "study":
                q_dict["correct_answer"] = q.correct_answer
                q_dict["explanations"] = q.explanations
                # Khôi phục trạng thái đúng/sai đã chấm trước đó khi tải lại trang
                q_dict["is_correct"] = (
                    user_progress.is_correct if user_progress else None
                )
                q_dict["ai_feedback"] = (
                    user_progress.ai_feedback if user_progress else None
                )

            quiz_data["questions"].append(q_dict)

        return quiz_data

    def get_quizzes(
        self,
        user_id: int,
        document_id: int | None = None,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Quiz).filter(Quiz.user_id == user_id)

        if document_id is not None:
            query = query.filter(Quiz.document_id == document_id)

        quizzes = query.order_by(desc(Quiz.created_at)).all()

        result = []

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
                    derived_status = "in_progress"
                else:
                    derived_status = "completed"

            result.append(
                {
                    "id": quiz.id,
                    "document_id": quiz.document_id,
                    "title": quiz.title,
                    "mode": quiz.mode,
                    "total_questions": quiz.total_questions,
                    "difficulty": quiz.difficulty,
                    "generation_status": quiz.generation_status,
                    "derived_status": derived_status,
                    "error_message": quiz.error_message,
                    "created_at": quiz.created_at,
                }
            )

        return result

    def get_quiz_attempts_list(
        self, quiz_id: int, user_id: int
    ) -> List[Dict[str, Any]]:
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
                "score": a.score,
                "attempt_status": a.attempt_status,
                "submit_reason": a.submit_reason,
                "created_at": a.created_at,
            }
            for a in attempts
        ]

    def get_attempt_detail(self, attempt_id: int, user_id: int) -> Dict[str, Any]:
        attempt = (
            self.db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
        )
        if not attempt or attempt.user_id != user_id:
            raise QuizNotFoundError()

        progresses = (
            self.db.query(QuizProgress)
            .filter(QuizProgress.attempt_id == attempt.id)
            .all()
        )
        progress_map = {p.question_id: p for p in progresses}

        questions = (
            self.db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == attempt.quiz_id)
            .all()
        )

        question_details = []

        for q in questions:
            p = progress_map.get(q.id)

            # Chuẩn hóa options
            formatted_options = None
            if q.options and isinstance(q.options, list):
                formatted_options = []

                for idx, opt in enumerate(q.options):
                    if isinstance(opt, str):
                        if "." in opt:
                            parts = opt.split(".", 1)
                            opt_id = parts[0].strip()
                            opt_text = parts[1].strip()
                        else:
                            opt_id = chr(65 + idx)
                            opt_text = opt

                        formatted_options.append(
                            {
                                "id": opt_id,
                                "text": opt_text,
                                "option_text": opt,
                            }
                        )

                    elif isinstance(opt, dict):
                        option = opt.copy()

                        if "id" not in option:
                            option["id"] = option.get("key") or chr(65 + idx)

                        formatted_options.append(option)

            question_details.append(
                {
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "options": formatted_options,  # <-- thêm dòng này
                    "correct_answer": q.correct_answer,
                    "explanations": q.explanations,
                    "points": q.points,
                    "user_answer": p.user_answer if p else None,
                    "is_correct": p.is_correct if p else None,
                    "ai_feedback": p.ai_feedback if p else None,
                }
            )

        return {
            "id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "score": attempt.score,
            "attempt_status": attempt.attempt_status,
            "submit_reason": attempt.submit_reason,
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
        """Hiển trị trạng thái tạo đề của Quiz"""

        quizzes = (
            self.db.query(Quiz)
            .join(Document, Quiz.document_id == Document.id)
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
                "document_title": quiz.document.title,
                "generation_mode": quiz.generation_mode,
                "difficulty": quiz.difficulty,
                "total_questions": quiz.total_questions,
                "created_at": quiz.created_at,
            }
            for quiz in quizzes
        ]

    def save_single_answer_progress(
        self, quiz_id: int, question_id: int, user_id: int, user_answer: Any
    ) -> Dict[str, Any]:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz or quiz.user_id != user_id:
            raise QuizNotFoundError()
        if quiz.mode != "study":
            raise InvalidQuizOperationError(
                "Chế độ chấm từng câu chỉ áp dụng cho chế độ học tập."
            )

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
                QuizAttempt.attempt_status == "in_progress",
            )
            .first()
        )
        if not active_attempt:
            active_attempt = QuizAttempt(
                quiz_id=quiz_id, user_id=user_id, attempt_status="in_progress"
            )
            self.db.add(active_attempt)
            self.db.flush()

        is_correct = None
        if question.question_type != "essay":
            is_correct = self._grade_logic(
                question.question_type, question.correct_answer, user_answer
            )

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
        else:
            progress = QuizProgress(
                attempt_id=active_attempt.id,
                user_id=user_id,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
            )
            self.db.add(progress)

        self.db.commit()

        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "explanations": question.explanations,
        }

    def submit_entire_quiz(
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

        questions = (
            self.db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        )
        answers_by_qid = {
            item.get("question_id"): item.get("user_answer") for item in answers_payload
        }

        total_score = 0.0
        correct_count = 0

        quiz_attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_status="completed",
            submit_reason=submit_reason,
        )
        self.db.add(quiz_attempt)
        self.db.flush()

        response_details = []

        for question in questions:
            q_id = question.id
            u_ans = answers_by_qid.get(q_id)
            is_correct = None

            if question.question_type != "essay":  # Hiện tại chưa có AI chấm essay
                is_correct = (
                    self._grade_logic(
                        question.question_type, question.correct_answer, u_ans
                    )
                    if u_ans is not None
                    else False
                )
                if is_correct:
                    correct_count += 1
                    total_score += float(question.points)

            progress = QuizProgress(
                attempt_id=quiz_attempt.id,
                user_id=user_id,
                question_id=q_id,
                user_answer=u_ans,
                is_correct=is_correct,
            )
            self.db.add(progress)

            response_details.append(
                {
                    "question_id": q_id,
                    "user_answer": u_ans,
                    "is_correct": is_correct,
                    "correct_answer": question.correct_answer,
                    "explanations": question.explanations,
                }
            )

        quiz_attempt.score = total_score
        self.db.commit()

        gradable_max = quiz.target_total_points - sum(
            q.points for q in questions if q.question_type == "essay"
        )

        return {
            "attempt_id": quiz_attempt.id,
            "score": total_score,
            "score_scale": quiz.target_total_points,
            "gradable_max": gradable_max,  # điểm tối đa của phần đã chấm được (hiện tạiloại trừ essay)
            "correct_answers_count": correct_count,
            "total_questions": len(questions),
            "submit_reason": submit_reason,
            "details": response_details,
        }

    def clear_quiz_progress(self, quiz_id: int, user_id: int) -> None:
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
            .first()
        )
        if active_attempt:
            self.db.query(QuizProgress).filter(
                QuizProgress.attempt_id == active_attempt.id
            ).delete()
            self.db.delete(active_attempt)
            self.db.commit()

    def _grade_logic(self, question_type: str, correct_val: Any, user_val: Any) -> bool:
        if user_val is None:
            return False

        # Hàm helper dùng chung để chuẩn hóa phương án (ví dụ: "A. static" -> "a")
        def clean_option(val: Any) -> str:
            return str(val).strip().split(".")[0].strip().lower()

        if question_type == "multiple_choice":
            return clean_option(correct_val) == clean_option(user_val)

        elif question_type == "multiple_response":
            # Đảm bảo cả đáp án đúng và đáp án chọn đều là list
            c_list = correct_val if isinstance(correct_val, list) else [correct_val]
            u_list = user_val if isinstance(user_val, list) else [user_val]

            # Làm sạch toàn bộ phần tử trong cả 2 list để đối chiếu không lệch nhãn đầu câu
            set_correct = set(clean_option(x) for x in c_list if x is not None)
            set_user = set(clean_option(x) for x in u_list if x is not None)

            return set_correct == set_user

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
