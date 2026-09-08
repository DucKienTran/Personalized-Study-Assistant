from app.services.assistant.generation_request_factory import (
    build_assistant_flashcard_request,
    build_assistant_quiz_request,
    extract_flashcard_count,
)


def test_flashcard_count_defaults_to_20():
    assert extract_flashcard_count("Tạo flashcards cho tôi") == 20


def test_flashcard_count_extracts_attached_counts():
    assert extract_flashcard_count("Tạo 30 flashcards về simplex") == 30
    assert extract_flashcard_count("Create 15 cards about duality") == 15


def test_flashcard_count_ignores_unrelated_or_ambiguous_numbers():
    assert extract_flashcard_count("Tạo flashcards về chương 3") == 20
    assert extract_flashcard_count("Create 15 cards and 30 flashcards") == 20
    assert extract_flashcard_count("Tạo 150 flashcards") == 20


def test_quiz_request_uses_safe_base_and_preserves_instruction():
    request = build_assistant_quiz_request(
        notebook_id=7,
        user_message="Tạo 15 câu quiz khó gồm multiple choice và true/false",
    )

    assert request.notebook_id == 7
    assert request.mode == "study"
    assert request.total_questions == 10
    assert request.question_types == ["multiple_choice"]
    assert request.difficulty_distribution == {
        "easy": 0.0,
        "medium": 1.0,
        "hard": 0.0,
    }
    assert request.custom_instruction == (
        "Tạo 15 câu quiz khó gồm multiple choice và true/false"
    )


def test_flashcard_request_preserves_instruction_and_count():
    request = build_assistant_flashcard_request(
        notebook_id=9,
        user_message="Tạo 30 flashcards về complementary slackness",
    )

    assert request.notebook_id == 9
    assert request.total_cards == 30
    assert request.title == "Flashcards"
    assert request.custom_instruction == (
        "Tạo 30 flashcards về complementary slackness"
    )
