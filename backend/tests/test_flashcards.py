from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.core.dependencies import get_current_user, get_flashcard_service
from app.exceptions import BadRequestError, NotFoundError
from app.main import app
from app.models.document_model import Document
from app.models.flashcard_model import (
    Flashcard,
    FlashcardReviewLog,
    FlashcardReviewState,
    FlashcardSessionCard,
    FlashcardStudySession,
)
from app.models.notebook_model import Notebook, NotebookDocument
from app.models.user_model import Role, User
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
from app.schemas.user_schema import CurrentUser
from app.services.flashcard.flashcard_scheduler import FSRSScheduler, SchedulerCardState
from app.services.flashcard.flashcard_service import FlashcardService
from app.services.quiz.chunk_selector import QuizChunk

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def context(db):
    suffix = uuid4().hex
    role = Role(name=f"flashcard-{suffix}")
    db.add(role)
    db.flush()
    users = [
        User(
            email=f"flashcard-{index}-{suffix}@example.com",
            password_hash="test",
            role_id=role.id,
        )
        for index in range(2)
    ]
    db.add_all(users)
    db.flush()
    notebooks = [
        Notebook(user_id=user.id, title=f"Notebook {index}") for index, user in enumerate(users)
    ]
    db.add_all(notebooks)
    db.flush()
    return db, users, notebooks, FlashcardService(db, FSRSScheduler(enable_fuzzing=False))


def create_deck(service, user, notebook, title="Deck"):
    return service.create_deck(
        user_id=user.id,
        data=FlashcardDeckCreate(notebook_id=notebook.id, title=title),
    )


def create_card(service, user, deck, front="Front", position=None):
    return service.create_card(
        deck_id=deck.id,
        user_id=user.id,
        data=FlashcardCreate(front=front, back="Back", position=position),
    )


def test_deck_crud_and_response_models(context):
    _db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    listed = service.list_decks(user_id=users[0].id, notebook_id=notebooks[0].id)
    assert FlashcardDeckListItemOut.model_validate(listed[0]).card_count == 0
    service.update_deck(
        deck_id=deck.id,
        user_id=users[0].id,
        data=FlashcardDeckUpdate(title="Updated"),
    )
    detail = service.get_deck(deck_id=deck.id, user_id=users[0].id)
    assert FlashcardDeckDetailOut.model_validate(detail).title == "Updated"
    service.delete_deck(deck_id=deck.id, user_id=users[0].id)
    assert service.list_decks(user_id=users[0].id) == []


def test_notebook_analytics_counts_ratings_and_review_time(context):
    db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    card = create_card(service, users[0], deck)
    other_deck = create_deck(service, users[1], notebooks[1])
    other_card = create_card(service, users[1], other_deck)

    def review_log(card_id, user_id, rating, response_time_ms):
        return FlashcardReviewLog(
            card_id=card_id,
            user_id=user_id,
            rating=rating,
            state_before="new",
            state_after="review",
            scheduled_days=1,
            elapsed_days=0,
            response_time_ms=response_time_ms,
        )

    db.add_all(
        [
            review_log(card.id, users[0].id, "again", 1000),
            review_log(card.id, users[0].id, "good", 2000),
            review_log(card.id, users[0].id, "easy", None),
            review_log(other_card.id, users[1].id, "easy", 9000),
        ]
    )
    db.flush()

    analytics = FlashcardNotebookAnalyticsOut.model_validate(
        service.get_notebook_analytics(
            notebook_id=notebooks[0].id,
            user_id=users[0].id,
        )
    )
    assert analytics.deck_count == 1
    assert analytics.card_count == 1
    assert analytics.total_reviews == 3
    assert analytics.rating_counts == {"again": 1, "hard": 0, "good": 1, "easy": 1}
    assert analytics.success_rate == pytest.approx(66.67, rel=0.01)
    assert analytics.total_review_time_ms == 3000
    assert analytics.average_review_time_ms == 1000


def test_card_crud_suspend_and_positions(context):
    _db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    first = create_card(service, users[0], deck)
    second = create_card(service, users[0], deck, front="Second")
    assert (first.position, second.position) == (0, 1)
    updated = service.update_card(
        card_id=first.id,
        user_id=users[0].id,
        data=FlashcardUpdate(front="Changed", position=3),
    )
    assert FlashcardOut.model_validate(updated).front == "Changed"
    assert service.suspend_card(card_id=first.id, user_id=users[0].id).is_suspended
    assert not service.unsuspend_card(card_id=first.id, user_id=users[0].id).is_suspended
    service.delete_card(card_id=first.id, user_id=users[0].id)
    with pytest.raises(NotFoundError):
        service.update_card(
            card_id=first.id,
            user_id=users[0].id,
            data=FlashcardUpdate(front="No"),
        )


def test_ownership_for_deck_card_and_session(context):
    _db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    card = create_card(service, users[0], deck)
    session = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    with pytest.raises(NotFoundError):
        service.get_deck(deck_id=deck.id, user_id=users[1].id)
    with pytest.raises(NotFoundError):
        service.update_card(
            card_id=card.id,
            user_id=users[1].id,
            data=FlashcardUpdate(front="No"),
        )
    with pytest.raises(NotFoundError):
        service.get_session(session_id=session["id"], user_id=users[1].id, now=NOW)


def test_study_overview_counts_new_due_future_and_suspended(context):
    db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    unseen = create_card(service, users[0], deck, "Unseen")
    explicit_new = create_card(service, users[0], deck, "New")
    due = create_card(service, users[0], deck, "Due")
    future = create_card(service, users[0], deck, "Future")
    suspended = create_card(service, users[0], deck, "Suspended")
    suspended.is_suspended = True
    db.add_all(
        [
            FlashcardReviewState(card_id=explicit_new.id, user_id=users[0].id, state="new"),
            FlashcardReviewState(
                card_id=due.id,
                user_id=users[0].id,
                state="review",
                due=NOW - timedelta(minutes=1),
                stability=1,
                difficulty=5,
            ),
            FlashcardReviewState(
                card_id=future.id,
                user_id=users[0].id,
                state="review",
                due=NOW + timedelta(days=1),
                stability=1,
                difficulty=5,
            ),
        ]
    )
    db.commit()
    result = FlashcardStudyOverviewOut.model_validate(
        service.get_study_overview(deck_id=deck.id, user_id=users[0].id, now=NOW)
    )
    assert unseen.id
    assert (
        result.new_count,
        result.review_due_count,
        result.suspended_count,
        result.due_now_count,
    ) == (2, 1, 1, 3)


def test_session_create_resume_order_and_suspended_exclusion(context):
    db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    cards = [create_card(service, users[0], deck, str(index)) for index in range(3)]
    cards[1].is_suspended = True
    db.commit()
    first = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    resumed = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    rows = (
        db.query(FlashcardSessionCard)
        .filter(FlashcardSessionCard.session_id == first["id"])
        .order_by(FlashcardSessionCard.queue_position)
        .all()
    )
    assert resumed["id"] == first["id"]
    assert [row.card_id for row in rows] == [cards[0].id, cards[2].id]
    assert [row.queue_position for row in rows] == [0, 1]
    FlashcardStudySessionOut.model_validate(first)


def test_waiting_earlier_queue_item_does_not_block_available_card(context):
    db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    cards = [create_card(service, users[0], deck, str(index)) for index in range(2)]
    result = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    rows = (
        db.query(FlashcardSessionCard)
        .filter_by(session_id=result["id"])
        .order_by(FlashcardSessionCard.queue_position)
        .all()
    )
    rows[0].available_at = NOW + timedelta(minutes=10)
    db.commit()
    serialized = service.get_session(session_id=result["id"], user_id=users[0].id, now=NOW)
    assert serialized["current_card"]["card_id"] == cards[1].id


def test_complete_and_abandon_session_semantics(context):
    db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    create_card(service, users[0], deck)
    active = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    with pytest.raises(BadRequestError):
        service.complete_session(session_id=active["id"], user_id=users[0].id, now=NOW)
    row = db.query(FlashcardSessionCard).filter_by(session_id=active["id"]).one()
    row.completed = True
    db.commit()
    assert (
        service.complete_session(session_id=active["id"], user_id=users[0].id, now=NOW)["status"]
        == "completed"
    )

    second_deck = create_deck(service, users[0], notebooks[0], "Second")
    create_card(service, users[0], second_deck)
    second = service.start_or_resume_session(deck_id=second_deck.id, user_id=users[0].id, now=NOW)
    assert (
        service.abandon_session(session_id=second["id"], user_id=users[0].id, now=NOW)["status"]
        == "abandoned"
    )


@pytest.mark.parametrize("rating", ["again", "hard", "good", "easy"])
def test_fsrs_ratings_are_deterministic_and_persist_step(rating):
    scheduler = FSRSScheduler(enable_fuzzing=False)
    result = scheduler.review(
        SchedulerCardState(card_id=1),
        rating,
        reviewed_at=NOW,
        response_time_ms=250,
    )
    assert result.rating == rating
    assert result.due_after > NOW
    assert result.reps == 1
    assert result.state_after in {"learning", "review"}
    assert (result.step_after is not None) == (result.state_after == "learning")


def test_relearning_requeues_same_card_and_appends_history(context):
    db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    card = create_card(service, users[0], deck)
    db.add(
        FlashcardReviewState(
            card_id=card.id,
            user_id=users[0].id,
            state="review",
            due=NOW,
            stability=10,
            difficulty=5,
            step=None,
            reps=3,
            lapses=0,
            last_review=NOW - timedelta(days=10),
        )
    )
    db.commit()
    session = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    first = service.review_card(
        session_id=session["id"],
        user_id=users[0].id,
        request=FlashcardReviewRequest(card_id=card.id, rating="again"),
        now=NOW,
    )
    state = db.query(FlashcardReviewState).filter_by(card_id=card.id, user_id=users[0].id).one()
    row = db.query(FlashcardSessionCard).filter_by(session_id=session["id"], card_id=card.id).one()
    assert first["state_after"] == "relearning"
    assert state.lapses == 1 and state.step is not None
    assert not row.completed and row.available_at == state.due
    old_log = db.query(FlashcardReviewLog).filter_by(card_id=card.id).one()
    old_values = (old_log.rating, old_log.reviewed_at)

    service.review_card(
        session_id=session["id"],
        user_id=users[0].id,
        request=FlashcardReviewRequest(card_id=card.id, rating="good"),
        now=first["next_due"],
    )
    logs = (
        db.query(FlashcardReviewLog)
        .filter_by(card_id=card.id)
        .order_by(FlashcardReviewLog.id)
        .all()
    )
    assert len(logs) == 2
    assert (logs[0].rating, logs[0].reviewed_at) == old_values


def test_review_transaction_rolls_back_all_changes(context, monkeypatch):
    db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    card = create_card(service, users[0], deck)
    session = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    original_commit = db.commit

    def fail_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="simulated"):
        service.review_card(
            session_id=session["id"],
            user_id=users[0].id,
            request=FlashcardReviewRequest(card_id=card.id, rating="good"),
            now=NOW,
        )
    monkeypatch.setattr(db, "commit", original_commit)
    assert db.query(FlashcardReviewState).filter_by(card_id=card.id).first() is None
    assert db.query(FlashcardReviewLog).filter_by(card_id=card.id).count() == 0
    row = db.query(FlashcardSessionCard).filter_by(session_id=session["id"], card_id=card.id).one()
    persisted_session = db.query(FlashcardStudySession).filter_by(id=session["id"]).one()
    assert row.review_count == 0 and not row.completed
    assert persisted_session.reviewed_count == 0


def test_suspended_card_cannot_be_reviewed(context):
    _db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    card = create_card(service, users[0], deck)
    session = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    service.suspend_card(card_id=card.id, user_id=users[0].id)
    with pytest.raises(BadRequestError):
        service.review_card(
            session_id=session["id"],
            user_id=users[0].id,
            request=FlashcardReviewRequest(card_id=card.id, rating="good"),
            now=NOW,
        )


def test_api_response_models_invalid_rating_and_authentication():
    class FakeService:
        def list_decks(self, **_kwargs):
            return []

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=1,
        email="flashcard@example.com",
        role="client",
        permissions=[],
    )
    app.dependency_overrides[get_flashcard_service] = lambda: FakeService()
    try:
        client = TestClient(app)
        response = client.get("/api/flashcard-decks")
        assert response.status_code == 200 and response.json()["data"] == []
        invalid = client.post(
            "/api/flashcard-sessions/1/review",
            json={"card_id": 1, "rating": "invalid"},
        )
        assert invalid.status_code == 422
    finally:
        app.dependency_overrides.clear()

    unauthenticated = TestClient(app).get("/api/flashcard-decks")
    assert unauthenticated.status_code in {401, 403}


def test_review_result_schema_accepts_service_shape(context):
    _db, users, notebooks, service = context
    deck = create_deck(service, users[0], notebooks[0])
    card = create_card(service, users[0], deck)
    session = service.start_or_resume_session(deck_id=deck.id, user_id=users[0].id, now=NOW)
    result = service.review_card(
        session_id=session["id"],
        user_id=users[0].id,
        request=FlashcardReviewRequest(card_id=card.id, rating="easy"),
        now=NOW,
    )
    assert FlashcardReviewResultOut.model_validate(result).reviewed_card_id == card.id


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/flashcard-decks"),
        ("post", "/api/flashcard-decks"),
        ("get", "/api/flashcard-decks/{deck_id}"),
        ("patch", "/api/flashcard-decks/{deck_id}"),
        ("delete", "/api/flashcard-decks/{deck_id}"),
        ("post", "/api/flashcard-decks/{deck_id}/cards"),
        ("patch", "/api/flashcards/{card_id}"),
        ("delete", "/api/flashcards/{card_id}"),
        ("post", "/api/flashcards/{card_id}/suspend"),
        ("post", "/api/flashcards/{card_id}/unsuspend"),
        ("get", "/api/flashcard-decks/{deck_id}/study-overview"),
        ("post", "/api/flashcard-decks/{deck_id}/sessions"),
        ("get", "/api/flashcard-sessions/{session_id}"),
        ("post", "/api/flashcard-sessions/{session_id}/review"),
        ("post", "/api/flashcard-sessions/{session_id}/complete"),
        ("post", "/api/flashcard-sessions/{session_id}/abandon"),
    ],
)
def test_required_api_surface_is_registered(method, path):
    assert method in app.openapi()["paths"][path]


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (FlashcardDeckCreate, {"notebook_id": 1, "title": "   "}),
        (FlashcardCreate, {"front": "", "back": "Back"}),
        (FlashcardStudySessionCreate, {"new_card_limit": -1}),
        (FlashcardReviewRequest, {"card_id": 1, "rating": "invalid"}),
    ],
)
def test_request_schema_rejects_invalid_input(schema, payload):
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


class FakeChunkSelector:
    def __init__(self, document_id):
        self.document_id = document_id

    async def select(self, **_kwargs):
        return [
            QuizChunk(
                chunk_id="chunk-1",
                content="A sufficiently detailed source chunk about spaced repetition.",
                metadata={"document_id": self.document_id},
            )
        ]


class FakeLLM:
    def __init__(self, output):
        self.output = output
        self.prompt = None

    async def generate(self, prompt):
        self.prompt = prompt
        return self.output


def generation_service(db, document_id, output):
    llm = FakeLLM(output)
    return (
        FlashcardService(
            db,
            FSRSScheduler(enable_fuzzing=False),
            chunk_selector=FakeChunkSelector(document_id),
            llm_client=llm,
        ),
        llm,
    )


def generation_request(notebook_id):
    return FlashcardDeckGenerate(
        notebook_id=notebook_id,
        title="Generated deck",
        total_cards=2,
    )


def create_active_source(db, user, notebook):
    document = Document(
        user_id=user.id,
        title="Source",
        file_path=f"flashcard-source-{uuid4().hex}.txt",
        file_type="text/plain",
        status="completed",
        file_size=10,
    )
    db.add(document)
    db.flush()
    db.add(
        NotebookDocument(
            notebook_id=notebook.id,
            document_id=document.id,
            is_active=True,
        )
    )
    db.commit()
    return document


@pytest.mark.asyncio
async def test_successful_ai_generation_uses_prompt_and_completes(context):
    db, users, notebooks, _service = context
    document = create_active_source(db, users[0], notebooks[0])
    service, llm = generation_service(
        db,
        document.id,
        json.dumps(
            {
                "cards": [
                    {
                        "front": "Question?",
                        "back": "Answer.",
                        "source_document_id": document.id,
                        "source_chunk_id": "chunk-1",
                    }
                ]
            }
        ),
    )
    deck = service.create_generation_deck(
        user_id=users[0].id,
        data=generation_request(notebooks[0].id),
        source_document_ids=[document.id],
    )
    await service.run_generation(deck.id, total_cards=2)
    db.refresh(deck)
    assert deck.generation_status == "completed"
    assert "SOURCE CONTEXT" in llm.prompt
    assert f"source_document_id: {document.id}" in llm.prompt


def test_ai_generation_requires_active_documents(context):
    _db, users, notebooks, service = context
    with pytest.raises(BadRequestError, match="active, processed document"):
        service.create_generation_deck(
            user_id=users[0].id,
            data=generation_request(notebooks[0].id),
            source_document_ids=[],
        )


@pytest.mark.asyncio
async def test_malformed_ai_output_marks_deck_failed(context):
    db, users, notebooks, _service = context
    document = create_active_source(db, users[0], notebooks[0])
    service, _llm = generation_service(db, document.id, "not valid json")
    deck = service.create_generation_deck(
        user_id=users[0].id,
        data=generation_request(notebooks[0].id),
        source_document_ids=[document.id],
    )
    await service.run_generation(deck.id, total_cards=2)
    db.refresh(deck)
    assert deck.generation_status == "failed"
    assert deck.error_message == "AI returned invalid flashcard data. Please try again."


@pytest.mark.asyncio
async def test_invalid_generated_source_document_is_rejected(context):
    db, users, notebooks, _service = context
    document = create_active_source(db, users[0], notebooks[0])
    service, _llm = generation_service(
        db,
        document.id,
        '{"cards":[{"front":"Question?","back":"Answer.",'
        '"source_document_id":999,"source_chunk_id":"chunk-1"}]}',
    )
    deck = service.create_generation_deck(
        user_id=users[0].id,
        data=generation_request(notebooks[0].id),
        source_document_ids=[document.id],
    )
    await service.run_generation(deck.id, total_cards=2)
    db.refresh(deck)
    assert deck.generation_status == "failed"
    assert db.query(Flashcard).filter(Flashcard.deck_id == deck.id).count() == 0


@pytest.mark.asyncio
async def test_generated_cards_are_persisted_with_provenance(context):
    db, users, notebooks, _service = context
    document = create_active_source(db, users[0], notebooks[0])
    service, _llm = generation_service(
        db,
        document.id,
        json.dumps(
            {
                "cards": [
                    {
                        "front": "One?",
                        "back": "First",
                        "source_document_id": document.id,
                        "source_chunk_id": "chunk-1",
                    },
                    {
                        "front": "Two?",
                        "back": "Second",
                        "source_document_id": document.id,
                        "source_chunk_id": None,
                    },
                ]
            }
        ),
    )
    deck = service.create_generation_deck(
        user_id=users[0].id,
        data=generation_request(notebooks[0].id),
        source_document_ids=[document.id],
    )
    await service.run_generation(deck.id, total_cards=2)
    cards = (
        db.query(Flashcard).filter(Flashcard.deck_id == deck.id).order_by(Flashcard.position).all()
    )
    db.refresh(deck)
    assert deck.generation_status == "completed"
    assert [(card.front, card.source_document_id) for card in cards] == [
        ("One?", document.id),
        ("Two?", document.id),
    ]
    assert cards[0].source_chunk_id == "chunk-1"


@pytest.mark.asyncio
async def test_ai_generation_truncates_cards_over_requested_limit(context, caplog):
    db, users, notebooks, _service = context
    document = create_active_source(db, users[0], notebooks[0])
    service, _llm = generation_service(
        db,
        document.id,
        json.dumps(
            {
                "cards": [
                    {
                        "front": f"Question {index}?",
                        "back": f"Answer {index}",
                        "source_document_id": document.id,
                        "source_chunk_id": "chunk-1",
                    }
                    for index in range(3)
                ]
            }
        ),
    )
    deck = service.create_generation_deck(
        user_id=users[0].id,
        data=generation_request(notebooks[0].id),
        source_document_ids=[document.id],
    )

    with caplog.at_level("WARNING"):
        await service.run_generation(deck.id, total_cards=2)

    db.refresh(deck)
    cards = (
        db.query(Flashcard).filter(Flashcard.deck_id == deck.id).order_by(Flashcard.position).all()
    )
    assert deck.generation_status == "completed"
    assert [card.front for card in cards] == ["Question 0?", "Question 1?"]
    assert "truncating to 2" in caplog.text
