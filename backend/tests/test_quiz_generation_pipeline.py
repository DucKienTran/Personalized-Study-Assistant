import json

import pytest

from app.ai.output.quiz_parser import QuizParser
from app.ai.prompts.quiz_prompt import QuizPromptBuilder
from app.schemas.quiz_profile_schema import MergedQuizProfileOut
from app.schemas.quiz_schema import QuizGenerateRequest
from app.services.quiz.chunk_selector import QuizChunk
from app.services.quiz.instruction_parser import ParsedQuizInstruction
from app.services.quiz.quiz_pipeline import QuizPipeline, QuizPipelineResult
from app.services.quiz.quiz_service import QuizService


class FakeChunkSelector:
    async def select(self, **_kwargs):
        return [
            QuizChunk(
                chunk_id="chunk-1",
                content="Paris is the capital city of France.",
                metadata={"document_title": "Geography"},
            )
        ]


class FakeLLM:
    async def generate(self, prompt: str):
        assert "Geography" in prompt
        assert "Paris is the capital city of France." in prompt
        assert "roughly 25% per key" in prompt
        assert 'Never prefix it with generic labels such as' in prompt
        assert '"(based on provided text)"' in prompt
        return json.dumps(
            {
                "quiz_title": "European Geography",
                "questions": [
                    {
                        "question_text": "What is the capital of France?",
                        "question_type": "multiple_choice",
                        "options": ["A. Paris", "B. Rome"],
                        "correct_answer": "A",
                        "explanations": {
                            "A": "Paris is the capital of France.",
                            "B": "Rome is the capital of Italy.",
                        },
                        "points": 10,
                        "hint": "It is stated in the source.",
                    }
                ],
            }
        )


def test_question_schema_contains_question_type_quality_rules():
    schema = QuizPromptBuilder._QUESTION_SCHEMA
    multiple_response_rules = " ".join(
        schema.split("2. multiple_response", 1)[1].split("3. true_false", 1)[0].split()
    )
    true_false_rules = " ".join(
        schema.split("3. true_false", 1)[1].split("4. fill_blank", 1)[0].split()
    )
    fill_blank_rules = " ".join(
        schema.split("4. fill_blank", 1)[1].split("5. short_answer", 1)[0].split()
    )
    short_answer_rules = " ".join(
        schema.split("5. short_answer", 1)[1].split("6. essay", 1)[0].split()
    )
    essay_rules = " ".join(schema.split("6. essay", 1)[1].split())

    assert "question_text MUST end with an explicit instruction" in multiple_response_rules
    assert "equivalent phrase in the question's own language" in multiple_response_rules
    assert "at least 2 elements and strictly fewer elements" in multiple_response_rules
    assert "MINIMUM of 2, not a fixed count" in multiple_response_rules
    assert "3 or more correct answers are equally valid" in multiple_response_rules
    assert "instead of always using exactly 2" in multiple_response_rules
    assert "between 1 and 5 statements" in true_false_rules
    assert "equally likely categories (approximately 20% each)" in true_false_rules
    assert "exactly 10 true_false questions MUST contain exactly" in true_false_rules
    assert "2 questions with each statement count" in true_false_rules
    assert "same coherent topic or subtopic" in true_false_rules
    assert "Never combine unrelated facts" in true_false_rules
    assert "Points MUST increase with the number of statements" in true_false_rules
    assert "more statements must be worth more" in true_false_rules
    assert "Audit the statement-count distribution" in true_false_rules
    assert "avoid making" in true_false_rules
    assert "all statements share the same correct_answer" in true_false_rules
    assert "MUST contain exactly ONE blank in the question_text" in fill_blank_rules
    assert "accepted phrasings/synonyms of THAT SINGLE blank" in fill_blank_rules
    assert "may contain any number of accepted variants" in fill_blank_rules
    assert "not how many accepted answers you provide" in fill_blank_rules
    assert "blank(s) MUST NOT appear anywhere else" in fill_blank_rules
    assert "exact correct_answer MUST NOT appear anywhere" in short_answer_rules
    assert "rephrase the question" in fill_blank_rules
    assert "rephrase the question" in short_answer_rules
    assert "typically contain 2-5 independently assessable expected" in essay_rules
    assert "partial-credit grading is" in essay_rules


def test_hard_constraints_vary_multiple_response_and_true_false_answers():
    constraints = QuizPromptBuilder._HARD_CONSTRAINTS

    assert "22.\nFor multiple_response questions" in constraints
    assert "vary the number and position of correct answers" in constraints
    assert "23.\nFor true_false questions" in constraints
    assert "balance the ratio of true vs false statements" in constraints


@pytest.mark.parametrize(
    ("question_type", "question_data", "expected_answer"),
    [
        (
            "multiple_response",
            {
                "options": ["A. Paris", "B. Lyon", "C. France"],
                "correct_answer": ["A", "C"],
                "explanations": {"A": "Correct", "B": "Incorrect", "C": "Correct"},
            },
            ["A", "C"],
        ),
        (
            "true_false",
            {
                "options": None,
                "statements": [
                    {"text": "Paris is a city.", "correct_answer": True},
                    {"text": "Paris is in Italy.", "correct_answer": False},
                ],
                "correct_answer": None,
                "explanations": None,
            },
            [True, False],
        ),
        (
            "fill_blank",
            {"options": None, "correct_answer": ["Paris", "paris city"]},
            ["Paris", "paris city"],
        ),
        (
            "short_answer",
            {"options": None, "correct_answer": "3.14"},
            "3.14",
        ),
        (
            "essay",
            {"options": None, "correct_answer": ["Names France", "Explains capital status"]},
            ["Names France", "Explains capital status"],
        ),
    ],
)
def test_parser_accepts_each_new_question_shape(question_type, question_data, expected_answer):
    raw = json.dumps(
        {
            "quiz_title": "Geography",
            "questions": [
                {
                    "question_text": "A supported question [blank]",
                    "question_type": question_type,
                    "points": 5,
                    "hint": None,
                    **question_data,
                }
            ],
        }
    )

    parsed = QuizParser.parse_quiz_response(raw)

    assert parsed["questions"][0]["correct_answer"] == expected_answer


def test_exam_mode_accepts_essay_questions():
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="exam",
        time_limit_minutes=30,
        generation_strategy="manual",
        total_questions=1,
        question_types=["essay"],
        difficulty_distribution={"medium": 1},
        target_total_points=10,
    )

    assert request.question_types == ["essay"]


def _true_false_quiz(question_count: int) -> str:
    return json.dumps(
        {
            "quiz_title": "Generated assessment",
            "questions": [
                {
                    "question_text": f"Supported statement number {index + 1} is correct.",
                    "question_type": "true_false",
                    "options": None,
                    "statements": [{
                        "text": f"Supported statement {index + 1}",
                        "correct_answer": True,
                        "explanation": "The statement is supported by the source."
                    }],
                    "correct_answer": None,
                    "explanations": None,
                    "points": 1,
                    "hint": None,
                }
                for index in range(question_count)
            ],
        }
    )


@pytest.mark.asyncio
async def test_multiple_choice_generation_pipeline_end_to_end():
    pipeline = QuizPipeline(
        llm=FakeLLM(),
        chunk_selector=FakeChunkSelector(),
        prompt_builder=QuizPromptBuilder(),
    )
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="study",
        generation_strategy="manual",
        total_questions=1,
        question_types=["multiple_choice"],
        difficulty_distribution={"easy": 1.0},
        target_total_points=10,
    )
    profile = MergedQuizProfileOut(
        difficulty=6.0,
        coverage=9.0,
        reasoning_depth=6.0,
        anti_repetition=8.0,
        relevance=8.0,
        time_per_question=2.0,
        strict_source_grounding=10.0,
    )

    result = await pipeline.run(
        request=request,
        merged_profile=profile,
        document_ids=[1],
    )

    assert result.title == "European Geography"
    assert len(result.questions) == 1
    assert result.questions[0]["question_type"] == "multiple_choice"
    assert result.questions[0]["points"] == 10


@pytest.mark.asyncio
async def test_generation_retries_when_model_returns_only_ten_of_fifteen_questions():
    class CountAwareLLM:
        def __init__(self):
            self.prompts = []

        async def generate(self, prompt: str):
            self.prompts.append(prompt)
            return _true_false_quiz(10 if len(self.prompts) == 1 else 15)

    llm = CountAwareLLM()
    pipeline = QuizPipeline(
        llm=llm,
        chunk_selector=FakeChunkSelector(),
        prompt_builder=QuizPromptBuilder(),
    )
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="study",
        generation_strategy="manual",
        total_questions=15,
        question_types=["true_false"],
        difficulty_distribution={"easy": 15},
        target_total_points=15,
    )
    profile = MergedQuizProfileOut(
        difficulty=6.0,
        coverage=9.0,
        reasoning_depth=6.0,
        anti_repetition=8.0,
        relevance=8.0,
        time_per_question=2.0,
        strict_source_grounding=10.0,
    )

    result = await pipeline.run(
        request=request,
        merged_profile=profile,
        document_ids=[1],
    )

    assert len(result.questions) == 15
    assert len(llm.prompts) == 2
    assert "Generate EXACTLY 15 questions" in llm.prompts[0]
    assert "exactly 15 objects" in llm.prompts[0]
    assert "Expected 15 questions, received 10" in llm.prompts[1]
    assert "Count the questions array" in llm.prompts[1]


@pytest.mark.asyncio
async def test_custom_instruction_overrides_config_and_drives_semantic_retrieval():
    class RecordingChunkSelector:
        def __init__(self):
            self.select_kwargs = None

        async def select(self, **kwargs):
            self.select_kwargs = kwargs
            return [
                QuizChunk(
                    chunk_id="chunk-fourier",
                    content="The Fourier transform decomposes a signal into frequencies.",
                    metadata={"document_title": "Signal Processing"},
                )
            ]

    class InstructionAndQuizLLM:
        def __init__(self):
            self.calls = []

        async def generate(self, prompt: str):
            self.calls.append(prompt)
            if "You parse user instructions" in prompt:
                return json.dumps(
                    {
                        "config_overrides": {
                            "total_questions": 2,
                            "question_types": ["true_false"],
                            "difficulty_distribution": {
                                "easy": 0,
                                "medium": 0,
                                "hard": 1,
                            },
                        },
                        # Legacy/extra parser output must not break generation,
                        # even when the LLM returns a list instead of a string.
                        "retrieval_query": ["Fourier transform algorithms Chapter 3"],
                        "generation_guidelines": "Use real-world signal processing scenarios.",
                    }
                )

            assert "Target question count\n\n2" in prompt
            assert "Requested difficulty distribution" in prompt
            assert "Create 2 hard true/false questions" in prompt
            return json.dumps(
                {
                    "quiz_title": "Fourier Transform Applications",
                    "questions": [
                        {
                            "question_text": "A Fourier transform decomposes a signal into frequencies.",
                            "question_type": "true_false",
                            "options": None,
                            "statements": [{"text": "It decomposes a signal into frequencies.", "correct_answer": True}],
                            "correct_answer": None,
                            "explanations": None,
                            "points": 5,
                            "hint": None,
                        },
                        {
                            "question_text": "A Fourier transform only represents time-domain values.",
                            "question_type": "true_false",
                            "options": None,
                            "statements": [{"text": "It only represents time-domain values.", "correct_answer": False}],
                            "correct_answer": None,
                            "explanations": None,
                            "points": 5,
                            "hint": None,
                        },
                    ],
                }
            )

    selector = RecordingChunkSelector()
    llm = InstructionAndQuizLLM()
    pipeline = QuizPipeline(
        llm=llm,
        chunk_selector=selector,
        prompt_builder=QuizPromptBuilder(),
    )
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="study",
        total_questions=1,
        question_types=["multiple_choice"],
        difficulty_distribution={"easy": 1.0},
        custom_instruction=(
            "Create 2 hard true/false questions about Fourier transform algorithms "
            "in Chapter 3 using real-world scenarios."
        ),
        target_total_points=10,
    )
    profile = MergedQuizProfileOut(
        difficulty=6.0,
        coverage=9.0,
        reasoning_depth=6.0,
        anti_repetition=8.0,
        relevance=8.0,
        time_per_question=2.0,
        strict_source_grounding=10.0,
    )

    result = await pipeline.run(
        request=request,
        merged_profile=profile,
        document_ids=[7],
    )

    assert len(llm.calls) == 2
    assert selector.select_kwargs["query"] == request.custom_instruction
    assert selector.select_kwargs["total_questions"] == 2
    assert result.final_request.total_questions == 2
    assert result.final_request.question_types == ["true_false"]
    assert result.final_request.difficulty_distribution["hard"] == 1


@pytest.mark.asyncio
async def test_empty_custom_instruction_skips_parser_and_uses_fallback_retrieval():
    class RecordingChunkSelector(FakeChunkSelector):
        def __init__(self):
            self.query = "not-called"

        async def select(self, **kwargs):
            self.query = kwargs["query"]
            return await super().select(**kwargs)

    selector = RecordingChunkSelector()
    pipeline = QuizPipeline(
        llm=FakeLLM(),
        chunk_selector=selector,
        prompt_builder=QuizPromptBuilder(),
    )
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="study",
        total_questions=1,
        question_types=["multiple_choice"],
        difficulty_distribution={"easy": 1.0},
        custom_instruction="   ",
        target_total_points=10,
    )
    profile = MergedQuizProfileOut(
        difficulty=6.0,
        coverage=9.0,
        reasoning_depth=6.0,
        anti_repetition=8.0,
        relevance=8.0,
        time_per_question=2.0,
        strict_source_grounding=10.0,
    )

    await pipeline.run(request=request, merged_profile=profile, document_ids=[1])

    assert selector.query is None


@pytest.mark.asyncio
async def test_all_non_empty_custom_instructions_drive_semantic_retrieval():
    class VagueInstructionParser:
        async def parse(self, request):
            return ParsedQuizInstruction(final_config=request)

    class RecordingChunkSelector(FakeChunkSelector):
        def __init__(self):
            self.query = "not-called"

        async def select(self, **kwargs):
            self.query = kwargs["query"]
            return await super().select(**kwargs)

    selector = RecordingChunkSelector()
    pipeline = QuizPipeline(
        llm=FakeLLM(),
        chunk_selector=selector,
        prompt_builder=QuizPromptBuilder(),
        instruction_parser=VagueInstructionParser(),
    )
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="study",
        total_questions=1,
        question_types=["multiple_choice"],
        difficulty_distribution={"easy": 1.0},
        custom_instruction="Make it fun",
        target_total_points=10,
    )
    profile = MergedQuizProfileOut(
        difficulty=6.0,
        coverage=9.0,
        reasoning_depth=6.0,
        anti_repetition=8.0,
        relevance=8.0,
        time_per_question=2.0,
        strict_source_grounding=10.0,
    )

    result = await pipeline.run(
        request=request,
        merged_profile=profile,
        document_ids=[1],
        query="legacy query must not override custom instruction",
    )

    assert selector.query == "Make it fun"
    assert "Make it fun" in result.prompt


@pytest.mark.asyncio
async def test_vietnamese_focus_instruction_is_passed_verbatim_to_retrieval():
    class ConfigOnlyInstructionParser:
        async def parse(self, request):
            return ParsedQuizInstruction(final_config=request)

    class RecordingChunkSelector(FakeChunkSelector):
        def __init__(self):
            self.query = None

        async def select(self, **kwargs):
            self.query = kwargs["query"]
            return await super().select(**kwargs)

    selector = RecordingChunkSelector()
    pipeline = QuizPipeline(
        llm=FakeLLM(),
        chunk_selector=selector,
        prompt_builder=QuizPromptBuilder(),
        instruction_parser=ConfigOnlyInstructionParser(),
    )
    instruction = "Tập trung vào các vấn đề cơ bản của Triết học"
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="study",
        total_questions=1,
        question_types=["multiple_choice"],
        difficulty_distribution={"easy": 1.0},
        custom_instruction=instruction,
        target_total_points=10,
    )
    profile = MergedQuizProfileOut(
        difficulty=6.0,
        coverage=9.0,
        reasoning_depth=6.0,
        anti_repetition=8.0,
        relevance=8.0,
        time_per_question=2.0,
        strict_source_grounding=10.0,
    )

    await pipeline.run(request=request, merged_profile=profile, document_ids=[1])

    assert selector.query == instruction


@pytest.mark.asyncio
async def test_generation_persists_true_false_without_options():
    class QuizRecord:
        id = 1
        generation_strategy = "manual"
        mode = "study"
        source_document_ids = [1]
        target_total_points = 10
        generation_status = "processing"
        error_message = None
        title = "Pending"

    class Query:
        def __init__(self, quiz):
            self.quiz = quiz

        def filter(self, *_args):
            return self

        def first(self):
            return self.quiz

    class DB:
        def __init__(self, quiz):
            self.quiz = quiz
            self.added = []

        def query(self, _model):
            return Query(self.quiz)

        def add(self, value):
            self.added.append(value)

        def commit(self):
            pass

        def rollback(self):
            pass

    class Pipeline:
        async def run(self, **_kwargs):
            return QuizPipelineResult(
                title="True or False",
                questions=[
                    {
                        "question_text": "Paris is the capital of France.",
                        "question_type": "true_false",
                        "options": None,
                        "statements": [{"text": "Paris is the capital of France.", "correct_answer": True}],
                        "correct_answer": [True],
                        "explanations": None,
                        "points": 10,
                        "hint": None,
                    }
                ],
                chunks=[],
                prompt="",
                raw_response="",
            )

    quiz = QuizRecord()
    db = DB(quiz)
    service = QuizService(db=db, quiz_pipeline=Pipeline())
    request = QuizGenerateRequest(
        notebook_id=1,
        mode="study",
        generation_strategy="manual",
        total_questions=1,
        question_types=["true_false"],
        difficulty_distribution={"easy": 1.0},
        target_total_points=10,
    )

    await service.run_generation(quiz_id=1, request=request)

    assert quiz.generation_status == "completed"
    assert len(db.added) == 1
    assert db.added[0].options is None
    assert db.added[0].statements[0]["correct_answer"] is True
