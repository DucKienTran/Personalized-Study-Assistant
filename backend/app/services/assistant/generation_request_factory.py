from __future__ import annotations

from decimal import Decimal
import re

from app.schemas.flashcard_schema import FlashcardDeckGenerate
from app.schemas.quiz_schema import QuizGenerateRequest

DEFAULT_FLASHCARD_COUNT = 20
MIN_FLASHCARD_COUNT = 1
MAX_FLASHCARD_COUNT = 100

_FLASHCARD_COUNT_PATTERNS = (
    re.compile(
        r"(?<!\d)(?P<count>\d{1,3})\s*(?:flash\s*cards?|flashcards?|cards?|thẻ(?:\s+ghi\s+nhớ)?)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:flash\s*cards?|flashcards?|cards?|thẻ(?:\s+ghi\s+nhớ)?)\s*[:=-]?\s*(?P<count>\d{1,3})(?!\d)",
        flags=re.IGNORECASE,
    ),
)


def extract_flashcard_count(user_message: str) -> int:
    text = user_message.strip()
    if not text:
        return DEFAULT_FLASHCARD_COUNT

    matches: list[int] = []
    for pattern in _FLASHCARD_COUNT_PATTERNS:
        for match in pattern.finditer(text):
            count = int(match.group("count"))
            if count not in matches:
                matches.append(count)

    if len(matches) != 1:
        return DEFAULT_FLASHCARD_COUNT

    count = matches[0]
    if not MIN_FLASHCARD_COUNT <= count <= MAX_FLASHCARD_COUNT:
        return DEFAULT_FLASHCARD_COUNT
    return count


def build_assistant_quiz_request(
    *, notebook_id: int, user_message: str
) -> QuizGenerateRequest:
    return QuizGenerateRequest(
        notebook_id=notebook_id,
        mode="study",
        generation_strategy="manual",
        total_questions=10,
        question_types=["multiple_choice"],
        difficulty_distribution={"easy": 0.0, "medium": 1.0, "hard": 0.0},
        custom_instruction=user_message.strip() or None,
        target_total_points=Decimal("100.00"),
        time_limit_minutes=None,
    )


def build_assistant_flashcard_request(
    *, notebook_id: int, user_message: str
) -> FlashcardDeckGenerate:
    return FlashcardDeckGenerate(
        notebook_id=notebook_id,
        title="Flashcards",
        description=None,
        total_cards=extract_flashcard_count(user_message),
        custom_instruction=user_message.strip() or None,
    )
