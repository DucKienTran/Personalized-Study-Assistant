from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.dependencies import (
    CurrentUserDep,
    FlashcardServiceDep,
    NotebookServiceDep,
    get_current_user,
)
from app.exceptions import BadRequestError
from app.schemas.flashcard_schema import (
    FlashcardCreate,
    FlashcardDeckCreate,
    FlashcardDeckDetailOut,
    FlashcardDeckGenerate,
    FlashcardDeckListItemOut,
    FlashcardDeckUpdate,
    FlashcardNotebookAnalyticsOut,
    FlashcardOut,
    FlashcardReviewRequest,
    FlashcardReviewResultOut,
    FlashcardStudyOverviewOut,
    FlashcardStudySessionCreate,
    FlashcardStudySessionOut,
    FlashcardUpdate,
)
from app.schemas.response_schema import BaseResponse

deck_router = APIRouter(
    prefix="/flashcard-decks",
    tags=["Flashcards"],
    dependencies=[Depends(get_current_user)],
)

card_router = APIRouter(
    prefix="/flashcards",
    tags=["Flashcards"],
    dependencies=[Depends(get_current_user)],
)

session_router = APIRouter(
    prefix="/flashcard-sessions",
    tags=["Flashcard Sessions"],
    dependencies=[Depends(get_current_user)],
)


# ---------------------------------------------------------------------------
# Deck
# ---------------------------------------------------------------------------


@deck_router.get(
    "",
    response_model=BaseResponse[list[FlashcardDeckListItemOut]],
)
def list_flashcard_decks(
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
    notebook_id: int | None = None,
):
    return BaseResponse(
        data=flashcard_service.list_decks(
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    )


@deck_router.get(
    "/processing",
    response_model=BaseResponse[list[FlashcardDeckListItemOut]],
)
def get_processing_flashcard_decks(
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(data=flashcard_service.list_processing_decks(user_id=current_user.id))


@deck_router.get(
    "/notebooks/{notebook_id}/analytics",
    response_model=BaseResponse[FlashcardNotebookAnalyticsOut],
)
def get_notebook_flashcard_analytics(
    notebook_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.get_notebook_analytics(
            notebook_id=notebook_id,
            user_id=current_user.id,
        )
    )


@deck_router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[FlashcardDeckListItemOut],
)
def generate_flashcard_deck(
    req: FlashcardDeckGenerate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
    notebook_service: NotebookServiceDep,
):
    source_document_ids = notebook_service.get_active_document_ids(
        notebook_id=req.notebook_id,
        user_id=current_user.id,
    )
    if not source_document_ids:
        raise BadRequestError(
            "At least one active, processed document is required to generate flashcards."
        )

    deck = flashcard_service.create_generation_deck(
        user_id=current_user.id,
        data=req,
        source_document_ids=source_document_ids,
    )
    background_tasks.add_task(
        flashcard_service.run_generation,
        deck.id,
        total_cards=req.total_cards,
        custom_instruction=req.custom_instruction,
    )
    return BaseResponse(data=flashcard_service.serialize_deck_list_item(deck))


@deck_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[FlashcardDeckListItemOut],
)
def create_flashcard_deck(
    req: FlashcardDeckCreate,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    deck = flashcard_service.create_deck(
        user_id=current_user.id,
        data=req,
    )

    return BaseResponse(
        data={
            "id": deck.id,
            "notebook_id": deck.notebook_id,
            "user_id": deck.user_id,
            "title": deck.title,
            "description": deck.description,
            "generation_status": deck.generation_status,
            "source_document_ids": deck.source_document_ids or [],
            "card_count": 0,
            "suspended_card_count": 0,
            "created_at": deck.created_at,
            "updated_at": deck.updated_at,
        }
    )


@deck_router.get(
    "/{deck_id}",
    response_model=BaseResponse[FlashcardDeckDetailOut],
)
def get_flashcard_deck(
    deck_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.get_deck(
            deck_id=deck_id,
            user_id=current_user.id,
        )
    )


@deck_router.patch(
    "/{deck_id}",
    response_model=BaseResponse[FlashcardDeckListItemOut],
)
def update_flashcard_deck(
    deck_id: int,
    req: FlashcardDeckUpdate,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    flashcard_service.update_deck(
        deck_id=deck_id,
        user_id=current_user.id,
        data=req,
    )

    # Reuse the canonical list/detail serialization from the service instead of
    # rebuilding counters in the router.
    deck = flashcard_service.get_deck(
        deck_id=deck_id,
        user_id=current_user.id,
    )

    deck.pop("cards", None)
    return BaseResponse(data=deck)


@deck_router.delete(
    "/{deck_id}",
    response_model=BaseResponse[None],
)
def delete_flashcard_deck(
    deck_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    flashcard_service.delete_deck(
        deck_id=deck_id,
        user_id=current_user.id,
    )
    return BaseResponse(message="Flashcard deck deleted successfully.")


# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------


@deck_router.post(
    "/{deck_id}/cards",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[FlashcardOut],
)
def create_flashcard(
    deck_id: int,
    req: FlashcardCreate,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.create_card(
            deck_id=deck_id,
            user_id=current_user.id,
            data=req,
        )
    )


@card_router.patch(
    "/{card_id}",
    response_model=BaseResponse[FlashcardOut],
)
def update_flashcard(
    card_id: int,
    req: FlashcardUpdate,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.update_card(
            card_id=card_id,
            user_id=current_user.id,
            data=req,
        )
    )


@card_router.delete(
    "/{card_id}",
    response_model=BaseResponse[None],
)
def delete_flashcard(
    card_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    flashcard_service.delete_card(
        card_id=card_id,
        user_id=current_user.id,
    )
    return BaseResponse(message="Flashcard deleted successfully.")


@card_router.post(
    "/{card_id}/suspend",
    response_model=BaseResponse[FlashcardOut],
)
def suspend_flashcard(
    card_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.suspend_card(
            card_id=card_id,
            user_id=current_user.id,
        )
    )


@card_router.post(
    "/{card_id}/unsuspend",
    response_model=BaseResponse[FlashcardOut],
)
def unsuspend_flashcard(
    card_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.unsuspend_card(
            card_id=card_id,
            user_id=current_user.id,
        )
    )


# ---------------------------------------------------------------------------
# Study overview
# ---------------------------------------------------------------------------


@deck_router.get(
    "/{deck_id}/study-overview",
    response_model=BaseResponse[FlashcardStudyOverviewOut],
)
def get_flashcard_study_overview(
    deck_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.get_study_overview(
            deck_id=deck_id,
            user_id=current_user.id,
        )
    )


# ---------------------------------------------------------------------------
# Study session
# ---------------------------------------------------------------------------


@deck_router.post(
    "/{deck_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[FlashcardStudySessionOut],
)
def start_or_resume_flashcard_session(
    deck_id: int,
    req: FlashcardStudySessionCreate,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.start_or_resume_session(
            deck_id=deck_id,
            user_id=current_user.id,
            options=req,
        )
    )


@session_router.get(
    "/{session_id}",
    response_model=BaseResponse[FlashcardStudySessionOut],
)
def get_flashcard_session(
    session_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.get_session(
            session_id=session_id,
            user_id=current_user.id,
        )
    )


@session_router.post(
    "/{session_id}/review",
    response_model=BaseResponse[FlashcardReviewResultOut],
)
def review_flashcard(
    session_id: int,
    req: FlashcardReviewRequest,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.review_card(
            session_id=session_id,
            user_id=current_user.id,
            request=req,
        )
    )


@session_router.post(
    "/{session_id}/complete",
    response_model=BaseResponse[FlashcardStudySessionOut],
)
def complete_flashcard_session(
    session_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.complete_session(
            session_id=session_id,
            user_id=current_user.id,
        )
    )


@session_router.post(
    "/{session_id}/abandon",
    response_model=BaseResponse[FlashcardStudySessionOut],
)
def abandon_flashcard_session(
    session_id: int,
    current_user: CurrentUserDep,
    flashcard_service: FlashcardServiceDep,
):
    return BaseResponse(
        data=flashcard_service.abandon_session(
            session_id=session_id,
            user_id=current_user.id,
        )
    )


__all__ = [
    "card_router",
    "deck_router",
    "session_router",
]
