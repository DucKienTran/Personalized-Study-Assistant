# app/ai/output/conversation_title_parser.py

from __future__ import annotations

import json
import re
from typing import Any


class ConversationTitleParseError(ValueError):
    """Raised when an LLM conversation-title response cannot be parsed."""


class ConversationTitleParser:
    """
    Parse and validate the LLM response used for conversation titles.

    Expected schema:

    {
        "title": "..."
    }
    """

    MAX_TITLE_LENGTH = 100

    @classmethod
    def parse(cls, raw_response: str) -> str:
        if not isinstance(raw_response, str) or not raw_response.strip():
            raise ConversationTitleParseError(
                "Conversation title response is empty."
            )

        cleaned = cls._strip_code_fence(raw_response.strip())

        try:
            parsed: Any = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ConversationTitleParseError(
                f"Conversation title response is not valid JSON: {exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ConversationTitleParseError(
                "Conversation title response must be a JSON object."
            )

        # Be strict so accidental schema changes are caught immediately.
        unexpected_keys = set(parsed.keys()) - {"title"}
        if unexpected_keys:
            raise ConversationTitleParseError(
                "Conversation title response contains unexpected keys: "
                + ", ".join(sorted(unexpected_keys))
            )

        title = parsed.get("title")

        if not isinstance(title, str):
            raise ConversationTitleParseError(
                "Conversation title must be a string."
            )

        title = cls._normalize_title(title)

        if not title:
            raise ConversationTitleParseError(
                "Conversation title cannot be empty."
            )

        if len(title) > cls.MAX_TITLE_LENGTH:
            raise ConversationTitleParseError(
                "Conversation title exceeds "
                f"{cls.MAX_TITLE_LENGTH} characters."
            )

        if not any(char.isalnum() for char in title):
            raise ConversationTitleParseError(
                "Conversation title must contain at least one "
                "alphanumeric character."
            )

        return title

    @staticmethod
    def _strip_code_fence(value: str) -> str:
        """
        Defensive normalization.

        The prompt explicitly forbids Markdown fences, but a model may still
        occasionally return:

            ```json
            {"title": "..."}
            ```

        Accepting that harmless formatting error makes this secondary feature
        more resilient without weakening the JSON schema itself.
        """
        match = re.fullmatch(
            r"```(?:json)?\s*(.*?)\s*```",
            value,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match:
            return match.group(1).strip()

        return value

    @staticmethod
    def _normalize_title(title: str) -> str:
        # Collapse accidental newlines/repeated spaces into one space.
        title = " ".join(title.split()).strip()

        # Model is instructed not to add unnecessary trailing punctuation.
        # Remove only harmless sentence-ending punctuation.
        title = title.rstrip(" \t\r\n.!?;:")

        return title.strip()
