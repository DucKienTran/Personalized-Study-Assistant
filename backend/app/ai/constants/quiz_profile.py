"""
Single source of truth cho hệ thống adaptive quiz profile — bộ tham số
điều khiển cách sinh quiz (độ khó, coverage, reasoning depth, ...).

- DEFAULT_QUIZ_PROFILE: profile baseline áp cho mọi user trước khi
  merge với personal offset.
- QUIZ_PROFILE_BOUNDS: khoảng giá trị hợp lệ (clamp) cho từng field.
- QUIZ_PROFILE_SEMANTICS: mô tả ý nghĩa từng field bằng ngôn ngữ tự nhiên,
  nhét vào prompt để LLM không phải tự đoán số 6/10 nghĩa là gì.
- DIFFICULTY_RANGES: các khoảng con của scalar `difficulty` duy nhất,
  chỉ dùng để mô tả ngữ nghĩa trong prompt — không phải field riêng,
  không được offset độc lập.
- SMOOTHING_FACTOR: trọng số delta mới trong công thức EMA
  offset = offset * (1 - SMOOTHING_FACTOR) + delta * SMOOTHING_FACTOR.
- PRESET_TAG_DELTAS: delta cố định (không qua AI) ứng với tag preset
  user chọn trong popup feedback.
"""

from typing import Dict, Tuple, TypedDict


class QuizProfileBounds(TypedDict):
    min: float
    max: float


QUIZ_PROFILE_FIELDS: Tuple[str, ...] = (
    "difficulty",
    "coverage",
    "reasoning_depth",
    "anti_repetition",
    "relevance",
    "time_per_question",
    "strict_source_grounding",
)

DEFAULT_QUIZ_PROFILE: Dict[str, float] = {
    "difficulty": 6.0,
    "coverage": 9.0,
    "reasoning_depth": 6.0,
    "anti_repetition": 8.0,
    "relevance": 8.0,
    "time_per_question": 2.0,
    "strict_source_grounding": 10.0,
}

# Tất cả field đều nằm trên thang 0-10.
QUIZ_PROFILE_BOUNDS: Dict[str, QuizProfileBounds] = {
    field: {"min": 0.0, "max": 10.0} for field in QUIZ_PROFILE_FIELDS
}

# EMA: offset_moi = offset_cu * (1 - SMOOTHING_FACTOR) + delta * SMOOTHING_FACTOR
# Vd delta = -2, SMOOTHING_FACTOR = 0.2, offset_cu = 0
#   -> offset_moi = 0 * 0.8 + (-2) * 0.2 = -0.4 (đã clamp sau đó).
SMOOTHING_FACTOR: float = 0.2

# Các khoảng con của `difficulty` — chỉ để giải thích ngữ nghĩa trong
# prompt, KHÔNG phải field riêng, KHÔNG được offset độc lập.
DIFFICULTY_RANGES: Dict[str, Tuple[int, int]] = {
    "easy": (0, 3),
    "medium": (4, 7),
    "hard": (8, 10),
}

# Mô tả ngữ nghĩa từng field, dùng để render vào prompt (qua
# app/ai/prompts/quiz_profile_prompt.py) thay vì đưa số thô cho LLM.
QUIZ_PROFILE_SEMANTICS: Dict[str, str] = {
    "difficulty": (
        "Overall difficulty on a 0-10 scale. "
        "0-3 (easy): answerable directly from a single fact/sentence in "
        "the source document, no inference required. "
        "4-7 (medium): requires connecting 2-3 pieces of information from "
        "the source, or a single reasoning step. "
        "8-10 (hard): requires multi-step reasoning, synthesis across "
        "multiple parts of the source, or applying a concept to a new "
        "situation."
    ),
    "coverage": (
        "How broadly the quiz should sample the source material, 0-10. "
        "Low = concentrate on a narrow, most-important subset of the "
        "content. High = spread questions across as much of the source "
        "as possible."
    ),
    "reasoning_depth": (
        "How much multi-step reasoning a question should demand beyond "
        "simple recall, 0-10. Low = mostly recall/definition questions. "
        "High = mostly application/analysis/synthesis questions."
    ),
    "anti_repetition": (
        "How aggressively to avoid generating questions that test the "
        "same fact or concept more than once, 0-10. Low = some overlap "
        "between questions is acceptable. High = every question must "
        "test a distinct fact or concept."
    ),
    "relevance": (
        "How strictly generated questions must stay tied to the core "
        "topics of the source material, 0-10. Low = tangential or "
        "loosely related questions are acceptable. High = only "
        "questions directly about the source's main content."
    ),
    "time_per_question": (
        "Target time in minutes a learner should need per question, "
        "used to calibrate question length/complexity — not a hard "
        "quiz timer."
    ),
    "strict_source_grounding": (
        "How strictly every question and answer must be grounded in "
        "the provided source chunks, 0-10. Low = the model may draw on "
        "general knowledge to fill gaps. High = every question/answer "
        "must be directly verifiable from the provided source chunks, "
        "with no outside knowledge."
    ),
}

# Delta cố định cho các tag preset (checkbox, tích được nhiều cái cùng
# lúc, mỗi tag cộng dồn độc lập). KHÔNG qua AI.
#
# Chiều dấu: "too_hard" nghĩa là quiz VỪA RỒI khó quá -> phải GIẢM
# difficulty cho lần sau (-), "too_easy" thì ngược lại phải TĂNG (+).
PRESET_TAG_DELTAS: Dict[str, Dict[str, float]] = {
    "too_hard": {"difficulty": -2.0},
    "too_easy": {"difficulty": 2.0},
    "repetitive": {"anti_repetition": 2.0},
    "not_relevant": {"relevance": 2.0},
    "too_shallow": {"reasoning_depth": 2.0},
    "too_long": {"time_per_question": 1.0},
    "too_short": {"time_per_question": -1.0},
    "not_enough_source_coverage": {"coverage": 2.0},
    "hallucinated": {"strict_source_grounding": 3.0},
}


def zero_delta() -> Dict[str, float]:
    """Trả về delta rỗng (0) cho đủ mọi field — dùng làm điểm khởi đầu
    khi cộng dồn preset_delta + ai_delta trong feedback_service."""
    return {field: 0.0 for field in QUIZ_PROFILE_FIELDS}
