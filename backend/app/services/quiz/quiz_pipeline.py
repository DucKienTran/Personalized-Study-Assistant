from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import logging
import re
from typing import Any

from app.ai.llm.base import LLMClient
from app.ai.output.quiz_parser import QuizParser
from app.ai.prompts.quiz_prompt import QuizPromptBuilder
from app.exceptions.quiz import QuizParseError, QuizPipelineError, QuizValidationError
from app.schemas.quiz_schema import QuizGenerateRequest
from app.services.quiz.chunk_selector import QuizChunk, QuizChunkSelector
from app.services.quiz.instruction_parser import QuizInstructionParser

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QuizPipelineResult:
    title: str
    questions: list[dict]
    chunks: list[QuizChunk]
    prompt: str
    raw_response: str
    final_request: QuizGenerateRequest | None = None


class QuizPipeline:
    """
    End-to-end quiz generation pipeline.

    Responsibilities:
    - Retrieve chunks
    - Build prompt
    - Call LLM
    - Parse response
    - Validate output
    - Retry when necessary

    NOT responsible for:
    - Saving database
    - Creating Quiz models
    - Business logic
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        *,
        llm: LLMClient,
        chunk_selector: QuizChunkSelector,
        prompt_builder: QuizPromptBuilder,
        instruction_parser: QuizInstructionParser | None = None,
    ):
        self.llm = llm
        self.chunk_selector = chunk_selector
        self.prompt_builder = prompt_builder
        self.instruction_parser = instruction_parser or QuizInstructionParser(llm)

    async def run(
        self,
        *,
        request: QuizGenerateRequest,
        merged_profile: Any,
        document_ids: list[int],
        query: str | None = None,
    ) -> QuizPipelineResult:

        parsed_instruction = await self.instruction_parser.parse(request)
        final_request = parsed_instruction.final_config
        custom_instruction = (request.custom_instruction or "").strip()
        retrieval_query = custom_instruction or query

        chunks = await self._select_chunks(
            request=final_request,
            merged_profile=merged_profile,
            document_ids=document_ids,
            query=retrieval_query,
        )

        if not chunks:
            raise QuizPipelineError("No suitable chunks were selected for quiz generation.")

        content = "\n\n".join(chunk.content for chunk in chunks)
        document_titles = {
            str(chunk.metadata.get("document_title"))
            for chunk in chunks
            if chunk.metadata.get("document_title")
        }
        prompt = self.prompt_builder.build(
            document_title=", ".join(sorted(document_titles)) or "Notebook sources",
            content=content,
            quiz_profile=merged_profile.model_dump(),
            total_questions=final_request.total_questions,
            question_types=final_request.question_types,
            difficulty_distribution=final_request.difficulty_distribution,
            target_total_points=final_request.target_total_points,
            mode=final_request.mode,
            generation_strategy=final_request.generation_strategy,
            generation_guidelines=custom_instruction or None,
            time_limit_minutes=final_request.time_limit_minutes,
        )

        return await self._generate_with_retry(
            prompt=prompt,
            request=final_request,
            chunks=chunks,
            final_request=final_request,
        )

    async def _generate_with_retry(
        self,
        *,
        prompt: str,
        request: QuizGenerateRequest,
        chunks: list[QuizChunk],
        final_request: QuizGenerateRequest,
    ) -> QuizPipelineResult:

        last_error: Exception | None = None
        last_error_message: str | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):

            logger.info("Attempt %d/%d", attempt, self.MAX_RETRIES)

            current_prompt = (
                prompt
                if attempt == 1 or not last_error_message
                else self._build_retry_prompt(
                    original_prompt=prompt,
                    error_message=last_error_message,
                    attempt=attempt,
                )
            )

            logger.info("Prompt length: %d chars", len(current_prompt))

            try:

                raw_response = await self._call_llm(current_prompt)
                logger.info("LLM response length: %d chars", len(raw_response))

                parsed = self._parse_response(raw_response)

                questions_count = (
                    len(parsed.get("questions", [])) if isinstance(parsed, dict) else 0
                )
                logger.info("Parsed %d questions", questions_count)

                self._validate_result(
                    parsed=parsed,
                    request=request,
                )
                logger.info("Validation passed")

                return QuizPipelineResult(
                    title=parsed["quiz_title"],
                    questions=parsed["questions"],
                    chunks=chunks,
                    prompt=current_prompt,
                    raw_response=raw_response,
                    final_request=final_request,
                )

            except (QuizValidationError, QuizParseError) as ex:
                logger.warning("Generation attempt %d failed: %s", attempt, ex)
                last_error, last_error_message = self._record_retry_error(ex)

            except QuizPipelineError:
                raise

            except Exception as ex:
                logger.warning(
                    "Unexpected error during quiz generation (attempt %d): %s",
                    attempt,
                    ex,
                )
                last_error, last_error_message = self._record_retry_error(ex)

            if attempt < self.MAX_RETRIES:
                logger.info("Retrying quiz generation...")

        raise QuizPipelineError(
            f"Quiz generation failed after {self.MAX_RETRIES} attempts. Last error: {last_error}"
        ) from last_error

    def _build_retry_prompt(
        self,
        *,
        original_prompt: str,
        error_message: str,
        attempt: int,
    ) -> str:

        return (
            f"Retry attempt: {attempt}/{self.MAX_RETRIES}\n\n"
            "Previous generation failed.\n\n"
            "Validation error:\n"
            f"<{error_message}>\n\n"
            "Correct every validation error exactly as stated, especially the required question count.\n"
            "Count the questions array before returning the response.\n"
            "Regenerate the complete quiz from scratch.\n"
            "Return ONLY valid JSON.\n\n"
            "--------------------------------\n\n"
            f"{original_prompt}"
        )

    async def _select_chunks(
        self,
        *,
        request: QuizGenerateRequest,
        merged_profile: Any,
        document_ids: list[int],
        query: str | None,
    ) -> list[QuizChunk]:

        return await self.chunk_selector.select(
            document_ids=document_ids,
            total_questions=request.total_questions,
            coverage=merged_profile.coverage,
            reasoning_depth=merged_profile.reasoning_depth,
            query=query,
        )

    async def _call_llm(
        self,
        prompt: str,
    ) -> str:

        response = await self.llm.generate(
            prompt=prompt,
        )

        if not response.strip():
            raise QuizPipelineError("LLM returned an empty response.")

        return response

    def _parse_response(
        self,
        raw_response: str,
    ) -> dict:

        try:
            return QuizParser.parse_quiz_response(
                raw_response,
            )
        except Exception as ex:
            raise QuizParseError(f"Failed to parse quiz response: {ex}") from ex

    def _record_retry_error(
        self,
        ex: Exception,
    ) -> tuple[Exception, str]:

        return ex, str(ex)

    # Class Constants
    TITLE_MAX_LENGTH = 200
    VALID_DIFFICULTIES = {"easy", "medium", "hard"}
    VALID_TRUE_FALSE = {"true", "false"}

    # Validation Methods (Refactored)

    def _validate_result(
        self,
        *,
        parsed: dict,
        request: QuizGenerateRequest,
    ) -> None:

        logger.info("Starting validation...")

        self._validate_quiz_title(parsed)

        questions = parsed.get("questions")
        if not isinstance(questions, list):
            raise QuizValidationError("Parsed output is missing 'questions' list.")

        if not questions:
            raise QuizValidationError("Questions list cannot be empty.")

        logger.info("Validating %d questions...", len(questions))

        for idx, question in enumerate(questions):
            self._validate_question(question, idx)

        self._check_question_count(
            questions=questions,
            expected=request.total_questions,
        )

        self._check_question_types(
            questions=questions,
            allowed_types=set(request.question_types),
            mode=request.mode,
        )

        self._check_points(
            questions=questions,
            target_total_points=request.target_total_points,
        )

        self._check_duplicate_questions(
            questions=questions,
        )

        logger.info("Validation completed successfully.")

    def _validate_quiz_title(
        self,
        parsed: dict,
    ) -> None:

        title = parsed.get("quiz_title")

        if not title or not isinstance(title, str) or not title.strip():
            raise QuizValidationError("Quiz title is missing or empty.")

        if len(title) >= self.TITLE_MAX_LENGTH:
            raise QuizValidationError(
                f"Quiz title length ({len(title)}) exceeds maximum limit of {self.TITLE_MAX_LENGTH} characters."
            )

        if not self._has_alphanumeric(title):
            raise QuizValidationError(
                "Quiz title must contain at least one alphanumeric character."
            )

    def _validate_question(
        self,
        question: dict,
        idx: int,
    ) -> None:

        self._validate_question_structure(question, idx)
        self._validate_question_common(question, idx)
        self._validate_question_type_specific(question, idx)

    def _validate_question_structure(
        self,
        question: dict,
        idx: int,
    ) -> None:

        if not isinstance(question, dict):
            raise QuizValidationError(f"Question {idx + 1} must be a dictionary.")

        q_text = question.get("question_text")
        if not q_text or not isinstance(q_text, str) or not q_text.strip():
            raise QuizValidationError(f"Question {idx + 1} is missing a valid 'question_text'.")

        if not self._has_alphanumeric(q_text):
            raise QuizValidationError(
                f"Question {idx + 1} 'question_text' must contain at least one alphanumeric character."
            )

        q_type = question.get("question_type")
        if not q_type or not isinstance(q_type, str) or not q_type.strip():
            raise QuizValidationError(f"Question {idx + 1} is missing a valid 'question_type'.")

    def _validate_question_common(
        self,
        question: dict,
        idx: int,
    ) -> None:

        if "points" in question and question["points"] is not None:
            points = question["points"]
            if isinstance(points, bool) or not isinstance(points, (int, float, Decimal)):
                raise QuizValidationError(
                    f"Question {idx + 1} points must be numeric, got {type(points).__name__}."
                )
            if Decimal(str(points)) <= 0:
                raise QuizValidationError(
                    f"Question {idx + 1} points must be greater than zero."
                )

        if "difficulty" in question and question["difficulty"] is not None:
            difficulty = question["difficulty"]
            if (
                not isinstance(difficulty, str)
                or self._normalize_text(difficulty) not in self.VALID_DIFFICULTIES
            ):
                raise QuizValidationError(
                    f"Question {idx + 1} difficulty must be 'easy', 'medium', or 'hard', got '{difficulty}'."
                )

    def _validate_question_type_specific(
        self,
        question: dict,
        idx: int,
    ) -> None:

        qtype = question["question_type"]

        if qtype == "multiple_choice":
            self._validate_multiple_choice(question, idx)

        elif qtype == "multiple_response":
            self._validate_multiple_response(question, idx)

        elif qtype == "true_false":
            self._validate_true_false(question, idx)

        elif qtype == "short_answer":
            self._validate_short_answer(question, idx)

        elif qtype == "fill_blank":
            self._validate_fill_blank(question, idx)

        elif qtype == "essay":
            rubric = question.get("correct_answer")
            if not isinstance(rubric, list) or not rubric:
                raise QuizValidationError(
                    f"Question {idx + 1} (essay) correct_answer must be a non-empty rubric list."
                )
            if any(not isinstance(point, str) or not point.strip() for point in rubric):
                raise QuizValidationError(
                    f"Question {idx + 1} (essay) rubric points must be non-empty strings."
                )

    def _validate_multiple_choice(
        self,
        question: dict,
        idx: int,
    ) -> None:

        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise QuizValidationError(
                f"Question {idx + 1} (multiple_choice) options must be a list with at least 2 items."
            )

        correct = question.get("correct_answer")
        if correct is None:
            raise QuizValidationError(
                f"Question {idx + 1} (multiple_choice) is missing 'correct_answer'."
            )

        seen_normalized_options: set[str] = set()
        valid_targets: set[str] = set()

        for opt_idx, opt in enumerate(options):
            if isinstance(opt, str):
                text = opt.strip()
                if not text:
                    raise QuizValidationError(
                        f"Question {idx + 1} option {opt_idx + 1} cannot be empty or blank."
                    )

                norm = self._normalize_text(text)
                if norm in seen_normalized_options:
                    raise QuizValidationError(f"Question {idx + 1} has duplicate option '{text}'.")

                seen_normalized_options.add(norm)
                valid_targets.add(text)
                valid_targets.add(norm)
                option_label = text.split(".", 1)[0].strip()
                if option_label:
                    valid_targets.add(option_label)
                    valid_targets.add(self._normalize_text(option_label))

            elif isinstance(opt, dict):
                if "text" not in opt:
                    raise QuizValidationError(
                        f"Question {idx + 1} option {opt_idx + 1} dict is missing required key 'text'."
                    )

                opt_text = opt.get("text")
                if not isinstance(opt_text, str) or not opt_text.strip():
                    raise QuizValidationError(
                        f"Question {idx + 1} option {opt_idx + 1} dict must have non-empty 'text'."
                    )

                text = opt_text.strip()
                norm = self._normalize_text(text)
                if norm in seen_normalized_options:
                    raise QuizValidationError(f"Question {idx + 1} has duplicate option '{text}'.")

                seen_normalized_options.add(norm)
                valid_targets.add(text)
                valid_targets.add(norm)

                opt_id = opt.get("id")
                if isinstance(opt_id, str) and opt_id.strip():
                    valid_targets.add(opt_id.strip())
                    valid_targets.add(self._normalize_text(opt_id))

            else:
                raise QuizValidationError(
                    f"Question {idx + 1} option {opt_idx + 1} must be a string or dict."
                )

        correct_str = str(correct).strip()
        correct_norm = self._normalize_text(correct_str)

        if correct_str not in valid_targets and correct_norm not in valid_targets:
            raise QuizValidationError(
                f"Question {idx + 1} (multiple_choice) correct_answer '{correct}' is not in options."
            )

    def _validate_multiple_response(self, question: dict, idx: int) -> None:
        options = question.get("options")
        correct = question.get("correct_answer")
        if not isinstance(options, list) or len(options) < 2:
            raise QuizValidationError(
                f"Question {idx + 1} (multiple_response) options must have at least 2 items."
            )
        if not isinstance(correct, list) or not correct:
            raise QuizValidationError(
                f"Question {idx + 1} (multiple_response) correct_answer must be a non-empty list."
            )

        valid_labels = {
            str(option.get("id", "")).strip().lower()
            if isinstance(option, dict)
            else str(option).split(".", 1)[0].strip().lower()
            for option in options
        }
        invalid = [answer for answer in correct if str(answer).strip().lower() not in valid_labels]
        if invalid:
            raise QuizValidationError(
                f"Question {idx + 1} (multiple_response) answers {invalid} are not in options."
            )

    def _validate_true_false(
        self,
        question: dict,
        idx: int,
    ) -> None:

        statements = question.get("statements")
        if not isinstance(statements, list) or not statements:
            raise QuizValidationError(
                f"Question {idx + 1} (true_false) statements must be a non-empty list."
            )
        for statement_idx, statement in enumerate(statements):
            if not isinstance(statement, dict) or not str(statement.get("text", "")).strip():
                raise QuizValidationError(
                    f"Question {idx + 1} statement {statement_idx + 1} needs non-empty text."
                )
            if not isinstance(statement.get("correct_answer"), bool):
                raise QuizValidationError(
                    f"Question {idx + 1} statement {statement_idx + 1} needs a Boolean answer."
                )

    def _validate_short_answer(
        self,
        question: dict,
        idx: int,
    ) -> None:

        correct = question.get("correct_answer")
        if not isinstance(correct, str) or not correct.strip():
            raise QuizValidationError(
                f"Question {idx + 1} (short_answer) correct_answer must be a non-empty string."
            )

    def _validate_fill_blank(self, question: dict, idx: int) -> None:
        correct = question.get("correct_answer")
        if not isinstance(correct, list) or not correct:
            raise QuizValidationError(
                f"Question {idx + 1} (fill_blank) correct_answer must be a non-empty list."
            )
        if any(not isinstance(answer, str) or not answer.strip() for answer in correct):
            raise QuizValidationError(
                f"Question {idx + 1} (fill_blank) accepted answers must be non-empty strings."
            )

    def _check_question_count(
        self,
        *,
        questions: list[dict],
        expected: int,
    ) -> None:

        actual = len(questions)

        if actual != expected:
            raise QuizValidationError(f"Expected {expected} questions, received {actual}.")

    def _check_question_types(
        self,
        *,
        questions: list[dict],
        allowed_types: set[str],
        mode: str,
    ) -> None:

        for idx, question in enumerate(questions):

            qtype = question.get("question_type")

            if qtype not in allowed_types:
                raise QuizValidationError(f"Question {idx + 1} has unsupported type '{qtype}'.")

    def _check_points(
        self,
        *,
        questions: list[dict],
        target_total_points: Decimal,
    ) -> None:

        total = sum(
            (Decimal(str(q.get("points", "1.00"))) for q in questions),
            start=Decimal("0.00"),
        )

        if total != target_total_points:
            raise QuizValidationError(
                f"Expected total points {target_total_points}, received {total}."
            )

    def _check_duplicate_questions(
        self,
        *,
        questions: list[dict],
    ) -> None:

        seen: set[str] = set()

        for idx, question in enumerate(questions):

            normalized = self._normalize_question(
                question["question_text"],
            )

            if normalized in seen:
                raise QuizValidationError(f"Duplicate question detected near question {idx + 1}.")

            seen.add(normalized)

    # Private Helpers

    def _normalize_text(
        self,
        text: str,
    ) -> str:

        return text.strip().lower()

    def _has_alphanumeric(
        self,
        text: str,
    ) -> bool:

        return any(c.isalnum() for c in text)

    def _normalize_question(
        self,
        text: str,
    ) -> str:

        text = text.lower().strip()

        text = re.sub(
            r"^(?:q\s*\d*\s*[:\.]?|question\s*\d*\s*[:\.]?|[\d\.\)\-\*•\s]+)+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"[^\w\s]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()
