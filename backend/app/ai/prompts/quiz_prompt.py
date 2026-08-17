# app/ai/prompts/quiz_prompt.py

from __future__ import annotations

from decimal import Decimal
import json

from app.ai.constants.quiz_profile import (
    QUIZ_PROFILE_FIELDS,
    QUIZ_PROFILE_SEMANTICS,
)


class QuizPromptBuilder:
    """
    Build the LLM prompt used to generate quizzes.

    Responsibilities:
    - Inject quiz configuration.
    - Inject personalized quiz profile.
    - Enforce hard business rules.
    - Enforce output JSON schema.
    """

    _QUESTION_SCHEMA = """
Each question MUST follow one of the following schemas.

1. multiple_choice

{
    "question_text": "...",
    "question_type": "multiple_choice",
    "options": [
        "A. ...",
        "B. ...",
        "C. ...",
        "D. ..."
    ],
    "correct_answer": "A",
    "explanations": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
    },
    "points": 4,
    "hint": "..."
}

------------------------------------------------

2. multiple_response

{
    "question_text": "...",
    "question_type": "multiple_response",
    "options": [
        "A. ...",
        "B. ...",
        "C. ...",
        "D. ..."
    ],
    "correct_answer": [
        "A",
        "C"
    ],
    "explanations": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
    },
    "points": 4,
    "hint": "..."
}

Rules:
- Every question_text MUST end with an explicit instruction telling the student
  that multiple answers may be correct, such as "Select all that apply." in
  English or an equivalent phrase in the question's own language.
- correct_answer MUST contain at least 2 elements and strictly fewer elements
  than the total number of options - this is a MINIMUM of 2, not a fixed count.
  3 or more correct answers are equally valid whenever the source supports it.
  Vary the count across different multiple_response questions in the same quiz
  instead of always using exactly 2.

------------------------------------------------

3. true_false

{
    "question_text": "...",
    "question_type": "true_false",
    "options": null,
    "statements": [
        {
            "text": "Statement 1",
            "correct_answer": true,
            "explanation": "..."
        },
        {
            "text": "Statement 2",
            "correct_answer": false,
            "explanation": "..."
        }
    ],
    "correct_answer": null,
    "explanations": null,
    "points": 2,
    "hint": "..."
}

Rules:
- statements MUST contain one or more items.
- Each statement MUST have its own Boolean correct_answer.
- Use multiple statements whenever the source supports a meaningful grouped question.
- Do not put a single Boolean answer at the question level.
- Each true_false question MUST contain between 1 and 5 statements. Across all
  true_false questions in the same quiz, treat statement counts 1, 2, 3, 4 and
  5 as equally likely categories (approximately 20% each). Distribute these
  five counts as evenly as mathematically possible instead of defaulting to 2.
  For example, a quiz with exactly 10 true_false questions MUST contain exactly
  2 questions with each statement count: two with 1, two with 2, two with 3,
  two with 4 and two with 5. Audit the statement-count distribution before
  returning the JSON.
- All statements grouped inside one true_false question MUST assess the same
  coherent topic or subtopic introduced by that question. They should examine
  related aspects of one concept, process, comparison or case. Never combine
  unrelated facts merely to reach a higher statement count.
- Points MUST increase with the number of statements in a true_false question.
  Within the same quiz, a question with more statements must be worth more than
  one with fewer statements, while the points across all questions must still
  equal the required target total exactly.
- Within a single true_false question with multiple statements, avoid making
  all statements share the same correct_answer (all true or all false) unless
  the source content genuinely supports that. Vary the true/false distribution
  both within each question and across the quiz's true_false questions.

------------------------------------------------

4. fill_blank

{
    "question_text": "...[blank]...",
    "question_type": "fill_blank",
    "options": null,
    "correct_answer": [
        "...",
        "..."
    ],
    "explanations": {
        "general": "..."
    },
    "points": 3,
    "hint": "..."
}

Rules:
- Each fill_blank question MUST contain exactly ONE blank in the question_text,
  not multiple blanks in the same question. The correct_answer list is for
  accepted phrasings/synonyms of THAT SINGLE blank and may contain any number of
  accepted variants (2, 3, or more). This constraint only limits the number of
  blanks per question, not how many accepted answers you provide for it.
- The content that goes in the blank(s) MUST NOT appear anywhere else in the
  question_text. Do not restate the answer before or after the blank. If the
  source material's phrasing reveals the answer, rephrase the question so the
  blank is the only place that information appears.

------------------------------------------------

5. short_answer

{
    "question_text": "...",
    "question_type": "short_answer",
    "options": null,
    "correct_answer": "3.14",
    "explanations": {
        "general": "..."
    },
    "points": 3,
    "hint": "..."
}

Rules:
- correct_answer MUST contain at most four characters.
- Generate this type ONLY if the answer naturally fits this limit.
- The exact correct_answer MUST NOT appear anywhere in the question_text. Do
  not restate the answer elsewhere in the question. If the source material's
  phrasing reveals the answer, rephrase the question so it must be supplied by
  the student.

------------------------------------------------

6. essay

{
    "question_text": "...",
    "question_type": "essay",
    "options": null,
    "correct_answer": [
        "Expected point 1",
        "Expected point 2"
    ],
    "explanations": null,
    "points": 5,
    "hint": "..."
}

Rules:
- correct_answer MUST be a non-empty list of independently assessable expected points.
- Each expected point must be directly supported by the source.
- correct_answer should typically contain 2-5 independently assessable expected
  points whenever the source material supports it, so partial-credit grading is
  meaningful. Avoid reducing the rubric to a single all-or-nothing point unless
  the question is genuinely too narrow to split further.
"""

    _OUTPUT_SCHEMA = """
Return ONLY ONE valid JSON object.

{
    "quiz_title": "...",
    "questions": [
        ...
    ]
}

Rules:

- quiz_title must be a clean, concise, professional subject title in the
  dominant language of the source material, ideally 3-12 words.
- Output the title directly. Never prefix it with generic labels such as
  "Quiz:", "Quiz -", "Test:", "Assessment:", or equivalent wording.
- Never append parenthetical or contextual qualifiers such as
  "(based on provided text)", "(based on the source material)",
  "(dựa trên tài liệu đã cung cấp)", or equivalent phrases.
- Do not wrap quiz_title in quotation marks or add trailing explanatory text.
- No markdown.
- No code fences.
- No explanations.
- No additional keys.
- The JSON must be directly parseable.
"""

    _HARD_CONSTRAINTS = """
==============================
HARD REQUIREMENTS
==============================

1.
Generate EXACTLY {total_questions} questions.

2.
The questions array MUST contain exactly {total_questions} objects.
Never return fewer or more questions. Count the array items before responding.

3.
Never invent facts.

4.
Every question MUST be directly supported by the provided source.

5.
Every correct answer MUST be verifiable from the source.

6.
Every explanation MUST also be grounded in the source.

7.
Avoid duplicate questions.

8.
Avoid testing the same concept multiple times.

9.
Avoid answer leakage inside the question wording.

10.
Distractors must be plausible.

11.
Questions should naturally vary in wording.

12.
Questions should progressively cover different parts of the source.

13.
Do not copy long sentences verbatim unless necessary.

14.
Prefer conceptual understanding over trivial wording changes.

15.
Respect the requested question types.

16.
Respect the requested difficulty distribution.

17.
Respect the personalized quiz profile.

18.
If custom instructions conflict with the quiz profile,
custom instructions have higher priority.

19.
Business constraints always override everything else.

20.
The total points of all generated questions MUST equal:

{target_total_points}

Do not exceed or fall below this value.
Every question must have a positive point value with at most two decimal places.

21.
For multiple-choice questions, distribute correct_answer keys across A, B, C and D.
Aim for roughly 25% per key, with each key representing between 10% and 40%
of the multiple-choice answers whenever the question count makes that mathematically possible.
For smaller sets, maximize balance and avoid repeatedly using the same key.
Do not use predictable placement sequences such as A-B-C-D repeated in order.
Audit and rebalance the answer-key distribution before returning the final JSON.

22.
For multiple_response questions, vary the number and position of correct answers
across the quiz. Do not repeatedly use the same count, such as always exactly 2
correct answers, or the same key pattern.

23.
For true_false questions, balance the ratio of true vs false statements across
the whole quiz. Avoid a majority of statements sharing the same correct_answer
value across all true_false questions combined.
"""

    @staticmethod
    def _render_profile(profile: dict[str, float]) -> str:
        lines = []

        for field in QUIZ_PROFILE_FIELDS:
            lines.append(
                f"""
{field}: {profile[field]:.1f}/10

Meaning:
{QUIZ_PROFILE_SEMANTICS[field]}
""".strip()
            )

        return "\n\n".join(lines)
    @staticmethod
    def build(
        *,
        document_title: str,
        content: str,
        quiz_profile: dict[str, float],
        total_questions: int,
        question_types: list[str],
        difficulty_distribution: dict[str, float] | None,
        target_total_points: Decimal,
        mode: str,
        generation_strategy: str,
        generation_guidelines: str | None = None,
        time_limit_minutes: int | None = None,
    ) -> str:

        difficulty_distribution_text = (
            json.dumps(
                difficulty_distribution,
                indent=2,
                ensure_ascii=False,
            )
            if difficulty_distribution
            else "Model decides naturally."
        )

        generation_guidelines_text = (
            generation_guidelines.strip()
            if generation_guidelines
            else "None."
        )

        exam_section = ""

        if mode == "exam":
            exam_section = f"""
==============================
EXAM SETTINGS
==============================

Time limit:
{time_limit_minutes} minutes

The generated questions should be appropriate for a timed examination.

Keep wording concise.

Avoid unnecessary reading load.

Avoid excessively long scenarios unless they are essential.
"""

        profile_text = QuizPromptBuilder._render_profile(
            quiz_profile
        )

        return f"""
You are an expert assessment designer.

Your task is to generate a high-quality quiz based ONLY on the provided learning material.

The quiz must balance educational value, diversity, correctness and personalization.

==================================================
DOCUMENT
==================================================

Title

{document_title}

Source

{content}

==================================================
QUIZ CONFIGURATION
==================================================

Mode

{mode}

Generation strategy

{generation_strategy}

Target question count

{total_questions}

Allowed question types

{", ".join(question_types)}

Requested difficulty distribution

{difficulty_distribution_text}

Target total points

{target_total_points}

{exam_section}

==================================================
PERSONALIZED QUIZ PROFILE
==================================================

The following values describe the learner's long-term preferences inferred from previous quiz feedback.

These values are NOT hard constraints.

Instead, they should guide generation whenever possible.

Examples:

Higher difficulty
→ increase reasoning complexity.

Higher coverage
→ sample more topics across the document.

Higher anti_repetition
→ avoid asking about the same knowledge twice.

Higher reasoning_depth
→ prefer application, analysis and synthesis over recall.

Higher relevance
→ stay focused on the document's core concepts.

Higher time_per_question
→ allow longer and more demanding questions.

Higher strict_source_grounding
→ every question and explanation should be directly verifiable from the source.

Current learner profile

{profile_text}

==================================================
USER GENERATION GUIDELINES
==================================================

{generation_guidelines_text}

Priority order

1. Hard business constraints.

2. Parsed user generation guidelines.

3. Personalized quiz profile.

==================================================
QUESTION QUALITY GUIDELINES
==================================================

Generate questions that genuinely evaluate understanding.

Avoid superficial wording changes.

Prefer conceptual diversity.

Prefer covering different sections of the document.

Mix factual recall, understanding and reasoning naturally.

Create realistic distractors.

Hints should help without revealing the answer.

Explanations should explain WHY an answer is correct, not merely restate it.

If multiple question types are requested, distribute them as evenly as possible unless the requested difficulty distribution naturally suggests otherwise.

Do not force every question to have identical complexity.

Maintain a smooth progression of difficulty.

Hard questions should require combining multiple ideas from the document.

Easy questions should still test meaningful knowledge.

        {QuizPromptBuilder._HARD_CONSTRAINTS.format(
    target_total_points=target_total_points,
    total_questions=total_questions,
)}

==================================================
QUESTION JSON SCHEMA
==================================================

{QuizPromptBuilder._QUESTION_SCHEMA}

==================================================
OUTPUT FORMAT
==================================================

{QuizPromptBuilder._OUTPUT_SCHEMA}

FINAL CHECK: the questions array must contain exactly {total_questions} objects.
Do not return the JSON until you have counted all {total_questions} questions.

Begin generating the JSON now.
"""
