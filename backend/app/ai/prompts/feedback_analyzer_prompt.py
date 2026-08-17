from app.ai.constants.quiz_profile import (
    QUIZ_PROFILE_FIELDS,
    QUIZ_PROFILE_SEMANTICS,
)


class FeedbackAnalyzerPrompt:
    """
    Prompt builder cho việc phân tích learner feedback
    thành quiz profile delta.

    Output:
    {
        "field_name": delta
    }

    Delta:
    -3.0 -> giảm mạnh
     0.0 -> không thay đổi
    +3.0 -> tăng mạnh
    Giá trị thập phân thể hiện mức điều chỉnh trung gian.
    """

    @staticmethod
    def build(
        comment: str,
    ) -> str:

        fields_description = "\n\n".join(
            [
                f"""
Field: {field}

Meaning:
{QUIZ_PROFILE_SEMANTICS[field]}
"""
                for field in QUIZ_PROFILE_FIELDS
            ]
        )


        return f"""
You are an adaptive quiz feedback analyzer.

Your task is to analyze learner feedback after completing a quiz.

Based ONLY on the learner feedback, decide how the quiz generation
profile should be adjusted for future quizzes.

You do NOT generate questions.
You do NOT explain your reasoning.
You ONLY output JSON containing profile adjustment deltas.


Available profile fields:

{fields_description}


Delta rules:

Each field value must be a floating-point number between -3.0 and +3.0.
Use decimal values for nuanced adjustments when appropriate.

Meaning:

- Positive delta:
  Increase this characteristic in future quizzes.

- Negative delta:
  Decrease this characteristic in future quizzes.

- Zero:
  No adjustment needed.


Important interpretation rules:

1. Difficulty

Increase difficulty only when learner indicates:
- quiz was too easy
- questions were trivial
- learner wants more challenge

Decrease difficulty only when learner indicates:
- quiz was too difficult
- questions were overwhelming
- learner could not solve them


2. Reasoning depth

Increase reasoning_depth when learner wants:
- more analytical questions
- more application
- deeper thinking

Decrease reasoning_depth when learner wants:
- more direct questions
- less complicated reasoning


3. Coverage

Increase coverage when learner indicates:
- important topics were missing
- quiz did not cover enough material

Decrease coverage when learner indicates:
- quiz was too broad
- too many unrelated areas were included


4. Anti repetition

Increase anti_repetition when learner indicates:
- questions repeat the same concept
- many questions feel similar

Do not change it for normal difficulty complaints.


5. Relevance

Increase relevance when learner indicates:
- questions are unrelated
- questions are outside the document topic

Do not increase relevance just because questions are hard.


6. Time per question

Increase time_per_question when learner indicates:
- questions require too much time
- answers need too much work

Decrease time_per_question when learner indicates:
- questions are too short
- questions are too simple


7. Strict source grounding

Increase strict_source_grounding when learner indicates:
- questions contain information not in the material
- answers require external knowledge
- hallucinated content

Do not change it for normal difficulty.


General rules:

- Only adjust fields clearly supported by the feedback.
- Do not infer hidden learner preferences.
- Do not use external knowledge.
- Avoid large changes.
- If feedback is vague, return zero values.
- Multiple fields can be adjusted together.


Output format:

Return ONLY valid JSON.

Example:

Feedback:
"The quiz was too easy. Most questions were just copied definitions."

Output:

{{
    "difficulty": 2.0,
    "reasoning_depth": 1.5
}}


Feedback:
"Many questions repeated the same concept and some answers were not in my notes."

Output:

{{
    "anti_repetition": 2.0,
    "strict_source_grounding": 3.0
}}


Learner feedback:

{comment}
"""
