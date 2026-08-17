from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.ai.llm.base import LLMClient
from app.ai.prompts.quiz_instruction_prompt import QuizInstructionPromptBuilder
from app.exceptions.quiz import QuizPipelineError
from app.schemas.quiz_schema import QuizGenerateRequest

QuestionType = Literal[
    "multiple_choice",
    "multiple_response",
    "true_false",
    "fill_blank",
    "short_answer",
    "essay",
]


class QuizConfigOverrides(BaseModel):
    mode: Literal["study", "exam"] | None = None
    total_questions: int | None = Field(default=None, ge=1, le=50)
    question_types: list[QuestionType] | None = None
    difficulty_distribution: dict[Literal["easy", "medium", "hard"], float] | None = None
    target_total_points: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    time_limit_minutes: int | None = Field(default=None, ge=1)

    @field_validator("question_types")
    @classmethod
    def validate_question_types(cls, value: list[str] | None):
        if value is not None and not value:
            raise ValueError("question_types cannot be empty")
        return value

    @field_validator("difficulty_distribution")
    @classmethod
    def validate_difficulty_distribution(cls, value: dict[str, float] | None):
        if value is not None and (not value or any(weight < 0 for weight in value.values())):
            raise ValueError("difficulty_distribution must contain non-negative weights")
        if value is not None and sum(value.values()) <= 0:
            raise ValueError("difficulty_distribution must have a positive total weight")
        return value


class InstructionParserOutput(BaseModel):
    config_overrides: QuizConfigOverrides = Field(default_factory=QuizConfigOverrides)


class ParsedQuizInstruction(BaseModel):
    final_config: QuizGenerateRequest


class QuizInstructionParser:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def parse(self, request: QuizGenerateRequest) -> ParsedQuizInstruction:
        instruction = (request.custom_instruction or "").strip()
        if not instruction:
            return ParsedQuizInstruction(final_config=request)

        prompt = QuizInstructionPromptBuilder.build(
            request=request,
            instruction=instruction,
        )
        raw_response = await self.llm.generate(prompt=prompt)

        try:
            parsed = InstructionParserOutput.model_validate(
                self._parse_json_response(raw_response)
            )
            merged_config = request.model_dump()
            override_values = parsed.config_overrides.model_dump(exclude_none=True)
            merged_config.update(override_values)
            final_config = QuizGenerateRequest.model_validate(merged_config)
        except (ValueError, ValidationError) as ex:
            raise QuizPipelineError(
                f"Failed to parse or validate custom quiz instruction: {ex}"
            ) from ex

        return ParsedQuizInstruction(final_config=final_config)

    @staticmethod
    def _parse_json_response(raw_response: str) -> dict:
        clean_text = raw_response.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
        if match:
            clean_text = match.group(1).strip()

        parsed = json.loads(clean_text)
        if not isinstance(parsed, dict):
            raise ValueError("Instruction parser must return a JSON object")
        return parsed
