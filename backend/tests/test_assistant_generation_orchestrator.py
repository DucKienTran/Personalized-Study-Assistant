from types import SimpleNamespace
from unittest.mock import Mock

from app.services.assistant.contracts import AssistantResourceType
from app.services.assistant.generation_orchestrator import AssistantGenerationOrchestrator


def build_orchestrator():
    quiz_service = Mock()
    quiz_service.create_quiz_placeholder.return_value = SimpleNamespace(
        id=41,
        title="Đang tạo đề...",
        generation_status="processing",
    )
    flashcard_service = Mock()
    flashcard_service.create_generation_deck.return_value = SimpleNamespace(
        id=52,
        title="Flashcards",
        generation_status="processing",
    )
    notebook_service = Mock()
    notebook_service.get_active_document_ids.return_value = [3, 8]
    personal_offset_service = Mock()
    personal_offset_service.get_merged_profile.return_value = SimpleNamespace(
        difficulty=0.2
    )
    return (
        AssistantGenerationOrchestrator(
            quiz_service=quiz_service,
            flashcard_service=flashcard_service,
            notebook_service=notebook_service,
            personal_offset_service=personal_offset_service,
        ),
        quiz_service,
        flashcard_service,
        notebook_service,
        personal_offset_service,
    )


def test_create_quiz_creates_one_placeholder_and_one_job():
    orchestrator, quiz_service, _, notebook_service, offsets = build_orchestrator()
    user = SimpleNamespace(id=9)

    result = orchestrator.create_quiz(
        notebook_id=7,
        user_message="Tạo quiz khó cho tôi",
        current_user=user,
    )

    notebook_service.get_active_document_ids.assert_called_once_with(
        notebook_id=7, user_id=9
    )
    quiz_service.create_quiz_placeholder.assert_called_once()
    placeholder = quiz_service.create_quiz_placeholder.call_args.kwargs
    assert placeholder["source_document_ids"] == [3, 8]
    assert placeholder["custom_instruction"] == "Tạo quiz khó cho tôi"
    assert placeholder["difficulty_distribution"] == {
        "easy": 0.0,
        "medium": 1.0,
        "hard": 0.0,
    }
    offsets.get_merged_profile.assert_called_once_with(9)
    assert result.resource.type == AssistantResourceType.QUIZ
    assert result.resource.id == "41"
    assert result.background_job is not None
    assert result.background_job.func is quiz_service.run_generation
    assert result.background_job.args[0] == 41


def test_create_flashcards_creates_one_deck_and_one_job():
    orchestrator, _, flashcard_service, notebook_service, _ = build_orchestrator()
    user = SimpleNamespace(id=9)

    result = orchestrator.create_flashcards(
        notebook_id=7,
        user_message="Tạo 30 flashcards về simplex",
        current_user=user,
    )

    notebook_service.get_active_document_ids.assert_called_once_with(
        notebook_id=7, user_id=9
    )
    flashcard_service.create_generation_deck.assert_called_once()
    deck_call = flashcard_service.create_generation_deck.call_args.kwargs
    assert deck_call["source_document_ids"] == [3, 8]
    assert deck_call["data"].total_cards == 30
    assert deck_call["data"].custom_instruction == "Tạo 30 flashcards về simplex"
    assert result.resource.type == AssistantResourceType.FLASHCARDS
    assert result.resource.id == "52"
    assert result.background_job is not None
    assert result.background_job.func is flashcard_service.run_generation
    assert result.background_job.args == (52,)
    assert result.background_job.kwargs == {
        "total_cards": 30,
        "custom_instruction": "Tạo 30 flashcards về simplex",
    }
