from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class GeneratedFlashcard(BaseModel):
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)

    source_document_id: int
    source_chunk_id: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("front", "back")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Generated flashcard front/back must not be empty.")
        return text

    @field_validator("source_chunk_id")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class FlashcardGenerationOutput(BaseModel):
    cards: list[GeneratedFlashcard] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class FlashcardOutputParseError(ValueError):
    pass


_MARKDOWN_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
    re.IGNORECASE | re.DOTALL,
)


def parse_flashcard_generation_output(
    raw_output: str | dict[str, Any],
) -> FlashcardGenerationOutput:
    """Parse and strictly validate one model response.

    The prompt requests JSON-only output, but we defensively accept a single
    Markdown JSON fence because some providers/models may still emit one.
    We do not attempt heuristic repair of malformed JSON because silent repair
    can create unsupported study content.
    """

    if isinstance(raw_output, dict):
        payload = raw_output
    else:
        text = raw_output.strip()
        if not text:
            raise FlashcardOutputParseError("Flashcard generation returned empty output.")

        fence_match = _MARKDOWN_JSON_FENCE_RE.match(text)
        if fence_match:
            text = fence_match.group(1).strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise FlashcardOutputParseError(
                f"Flashcard generation returned invalid JSON: {exc.msg}"
            ) from exc

    try:
        return FlashcardGenerationOutput.model_validate(payload)
    except ValidationError as exc:
        raise FlashcardOutputParseError(
            f"Flashcard generation output failed schema validation: {exc}"
        ) from exc


__all__ = [
    "FlashcardGenerationOutput",
    "FlashcardOutputParseError",
    "GeneratedFlashcard",
    "parse_flashcard_generation_output",
]
