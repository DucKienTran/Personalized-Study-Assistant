from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.ai.llm.base import LLMClient
from app.ai.output.flashcard_output import (
    FlashcardOutputParseError,
    parse_flashcard_generation_output,
)
from app.ai.prompts.flashcard_prompt import (
    FLASHCARD_GENERATION_SYSTEM_PROMPT,
    build_flashcard_generation_prompt,
)
from app.exceptions import BadRequestError, NotFoundError
from app.models.flashcard_model import (
    Flashcard,
    FlashcardDeck,
    FlashcardReviewLog,
    FlashcardReviewState,
    FlashcardSessionCard,
    FlashcardStudySession,
)
from app.models.notebook_model import Notebook
from app.schemas.flashcard_schema import (
    FlashcardCreate,
    FlashcardDeckCreate,
    FlashcardDeckGenerate,
    FlashcardDeckUpdate,
    FlashcardReviewRequest,
    FlashcardStudySessionCreate,
    FlashcardUpdate,
)
from app.services.flashcard.flashcard_scheduler import (
    FlashcardScheduler,
    SchedulerCardState,
    SchedulerResult,
)
from app.services.quiz.chunk_selector import QuizChunk, QuizChunkSelector

logger = logging.getLogger(__name__)


class FlashcardService:
    """Business logic for manual Flashcard CRUD and spaced-repetition study.

    Important responsibilities:
    - enforce ownership for all user-owned resources;
    - keep scheduler implementation behind FlashcardScheduler;
    - persist review state separately from append-only review history;
    - maintain a resumable per-session queue;
    - commit each submitted review atomically.
    """

    def __init__(
        self,
        db: Session,
        scheduler: FlashcardScheduler,
        chunk_selector: QuizChunkSelector | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.db = db
        self.scheduler = scheduler
        self.chunk_selector = chunk_selector
        self.llm_client = llm_client

    # ------------------------------------------------------------------
    # Deck CRUD
    # ------------------------------------------------------------------

    def create_deck(
        self,
        *,
        user_id: int,
        data: FlashcardDeckCreate,
    ) -> FlashcardDeck:
        self._get_owned_notebook(data.notebook_id, user_id)

        deck = FlashcardDeck(
            notebook_id=data.notebook_id,
            user_id=user_id,
            title=data.title,
            description=data.description,
            generation_status="manual",
            source_document_ids=[],
        )
        self.db.add(deck)
        self._commit_refresh(deck)
        return deck

    def list_decks(
        self,
        *,
        user_id: int,
        notebook_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = self.db.query(FlashcardDeck).filter(FlashcardDeck.user_id == user_id)

        if notebook_id is not None:
            self._get_owned_notebook(notebook_id, user_id)
            query = query.filter(FlashcardDeck.notebook_id == notebook_id)

        decks = query.order_by(FlashcardDeck.updated_at.desc(), FlashcardDeck.id.desc()).all()

        if not decks:
            return []

        deck_ids = [deck.id for deck in decks]

        card_counts = dict(
            self.db.query(
                Flashcard.deck_id,
                func.count(Flashcard.id),
            )
            .filter(Flashcard.deck_id.in_(deck_ids))
            .group_by(Flashcard.deck_id)
            .all()
        )

        suspended_counts = dict(
            self.db.query(
                Flashcard.deck_id,
                func.count(Flashcard.id),
            )
            .filter(
                Flashcard.deck_id.in_(deck_ids),
                Flashcard.is_suspended.is_(True),
            )
            .group_by(Flashcard.deck_id)
            .all()
        )

        return [
            {
                "id": deck.id,
                "notebook_id": deck.notebook_id,
                "user_id": deck.user_id,
                "title": deck.title,
                "description": deck.description,
                "generation_status": deck.generation_status,
                "source_document_ids": deck.source_document_ids or [],
                "card_count": int(card_counts.get(deck.id, 0)),
                "suspended_card_count": int(suspended_counts.get(deck.id, 0)),
                "created_at": deck.created_at,
                "updated_at": deck.updated_at,
            }
            for deck in decks
        ]

    def list_processing_decks(self, *, user_id: int) -> list[dict[str, Any]]:
        decks = (
            self.db.query(FlashcardDeck)
            .filter(
                FlashcardDeck.user_id == user_id,
                FlashcardDeck.generation_status == "processing",
            )
            .order_by(FlashcardDeck.created_at.desc(), FlashcardDeck.id.desc())
            .all()
        )
        return [self.serialize_deck_list_item(deck) for deck in decks]

    def get_notebook_analytics(
        self,
        *,
        notebook_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        self._get_owned_notebook(notebook_id, user_id)

        deck_count = (
            self.db.query(func.count(FlashcardDeck.id))
            .filter(
                FlashcardDeck.notebook_id == notebook_id,
                FlashcardDeck.user_id == user_id,
            )
            .scalar()
        )
        card_count = (
            self.db.query(func.count(Flashcard.id))
            .join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
            .filter(
                FlashcardDeck.notebook_id == notebook_id,
                FlashcardDeck.user_id == user_id,
            )
            .scalar()
        )
        review_rows = (
            self.db.query(
                FlashcardReviewLog.rating,
                func.count(FlashcardReviewLog.id),
                func.coalesce(func.sum(FlashcardReviewLog.response_time_ms), 0),
            )
            .join(Flashcard, Flashcard.id == FlashcardReviewLog.card_id)
            .join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
            .filter(
                FlashcardDeck.notebook_id == notebook_id,
                FlashcardDeck.user_id == user_id,
                FlashcardReviewLog.user_id == user_id,
            )
            .group_by(FlashcardReviewLog.rating)
            .all()
        )

        rating_counts = {rating: 0 for rating in ("again", "hard", "good", "easy")}
        total_review_time_ms = 0
        for rating, count, response_time_ms in review_rows:
            if rating in rating_counts:
                rating_counts[rating] = int(count)
            total_review_time_ms += int(response_time_ms or 0)

        total_reviews = sum(rating_counts.values())
        successful_reviews = rating_counts["good"] + rating_counts["easy"]
        return {
            "notebook_id": notebook_id,
            "deck_count": int(deck_count or 0),
            "card_count": int(card_count or 0),
            "total_reviews": total_reviews,
            "rating_counts": rating_counts,
            "success_rate": successful_reviews / total_reviews * 100 if total_reviews else 0.0,
            "total_review_time_ms": total_review_time_ms,
            "average_review_time_ms": (
                total_review_time_ms / total_reviews if total_reviews else 0.0
            ),
        }

    def create_generation_deck(
        self,
        *,
        user_id: int,
        data: FlashcardDeckGenerate,
        source_document_ids: list[int],
    ) -> FlashcardDeck:
        self._get_owned_notebook(data.notebook_id, user_id)
        if not source_document_ids:
            raise BadRequestError(
                "At least one active, processed document is required to generate flashcards."
            )

        deck = FlashcardDeck(
            notebook_id=data.notebook_id,
            user_id=user_id,
            title=data.title,
            description=data.description,
            generation_status="processing",
            source_document_ids=list(source_document_ids),
        )
        self.db.add(deck)
        self._commit_refresh(deck)
        return deck

    async def run_generation(
        self,
        deck_id: int,
        *,
        total_cards: int,
        custom_instruction: str | None = None,
    ) -> None:
        deck = self.db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()
        if deck is None or deck.generation_status != "processing":
            return

        try:
            if self.chunk_selector is None or self.llm_client is None:
                raise RuntimeError("Flashcard generation dependencies are unavailable.")

            source_document_ids = [int(value) for value in (deck.source_document_ids or [])]
            chunks = await self.chunk_selector.select(
                document_ids=source_document_ids,
                total_questions=total_cards,
                coverage=5.0,
                reasoning_depth=1.0,
                query=(custom_instruction or "").strip() or None,
            )
            if not chunks:
                raise ValueError("No usable source content was found.")

            source_context = self._build_generation_source_context(
                chunks=chunks,
                allowed_document_ids=set(source_document_ids),
            )
            user_prompt = build_flashcard_generation_prompt(
                source_context=source_context,
                total_cards=total_cards,
                custom_instruction=custom_instruction,
            )
            raw_output = await self.llm_client.generate(
                prompt=f"{FLASHCARD_GENERATION_SYSTEM_PROMPT}\n\n{user_prompt}"
            )
            output = parse_flashcard_generation_output(raw_output)
            if not output.cards:
                raise FlashcardOutputParseError("Flashcard generation returned no cards.")
            generated_cards = output.cards
            if len(generated_cards) > total_cards:
                logger.warning(
                    "Flashcard generation returned %s cards for deck_id=%s; truncating to %s.",
                    len(generated_cards),
                    deck_id,
                    total_cards,
                )
                generated_cards = generated_cards[:total_cards]

            allowed_document_ids = set(source_document_ids)
            for position, generated in enumerate(generated_cards):
                if generated.source_document_id not in allowed_document_ids:
                    raise FlashcardOutputParseError(
                        "Generated flashcard references a document outside the deck sources."
                    )
                self.db.add(
                    Flashcard(
                        deck_id=deck.id,
                        front=generated.front,
                        back=generated.back,
                        source_document_id=generated.source_document_id,
                        source_chunk_id=generated.source_chunk_id,
                        position=position,
                    )
                )

            deck.generation_status = "completed"
            deck.error_message = None
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception("Flashcard generation failed for deck_id=%s", deck_id)
            failed_deck = self.db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()
            if failed_deck is not None:
                failed_deck.generation_status = "failed"
                failed_deck.error_message = self._safe_generation_error(exc)
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    logger.exception("Could not persist failure status for deck_id=%s", deck_id)

    def get_deck(
        self,
        *,
        deck_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        deck = (
            self.db.query(FlashcardDeck)
            .options(joinedload(FlashcardDeck.cards))
            .filter(
                FlashcardDeck.id == deck_id,
                FlashcardDeck.user_id == user_id,
            )
            .first()
        )
        if deck is None:
            raise NotFoundError("Flashcard deck not found.")

        cards = sorted(deck.cards, key=lambda card: (card.position, card.id))

        return {
            "id": deck.id,
            "notebook_id": deck.notebook_id,
            "user_id": deck.user_id,
            "title": deck.title,
            "description": deck.description,
            "generation_status": deck.generation_status,
            "source_document_ids": deck.source_document_ids or [],
            "card_count": len(cards),
            "suspended_card_count": sum(1 for card in cards if card.is_suspended),
            "created_at": deck.created_at,
            "updated_at": deck.updated_at,
            "cards": cards,
        }

    def update_deck(
        self,
        *,
        deck_id: int,
        user_id: int,
        data: FlashcardDeckUpdate,
    ) -> FlashcardDeck:
        deck = self._get_owned_deck(deck_id, user_id)

        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(deck, field, value)

        self._commit_refresh(deck)
        return deck

    def delete_deck(
        self,
        *,
        deck_id: int,
        user_id: int,
    ) -> None:
        deck = self._get_owned_deck(deck_id, user_id)
        self.db.delete(deck)
        self._commit()

    # ------------------------------------------------------------------
    # Card CRUD
    # ------------------------------------------------------------------

    def create_card(
        self,
        *,
        deck_id: int,
        user_id: int,
        data: FlashcardCreate,
    ) -> Flashcard:
        self._get_owned_deck(deck_id, user_id)

        if data.source_document_id is not None:
            self._validate_source_document_in_deck_notebook(
                deck_id=deck_id,
                document_id=data.source_document_id,
                user_id=user_id,
            )

        position = data.position
        if position is None:
            max_position = (
                self.db.query(func.max(Flashcard.position))
                .filter(Flashcard.deck_id == deck_id)
                .scalar()
            )
            position = 0 if max_position is None else int(max_position) + 1

        card = Flashcard(
            deck_id=deck_id,
            front=data.front,
            back=data.back,
            source_document_id=data.source_document_id,
            source_chunk_id=data.source_chunk_id,
            source_metadata=data.source_metadata,
            position=position,
        )

        self.db.add(card)
        self._commit_refresh(card)
        return card

    def update_card(
        self,
        *,
        card_id: int,
        user_id: int,
        data: FlashcardUpdate,
    ) -> Flashcard:
        card = self._get_owned_card(card_id, user_id)

        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(card, field, value)

        self._commit_refresh(card)
        return card

    def delete_card(
        self,
        *,
        card_id: int,
        user_id: int,
    ) -> None:
        card = self._get_owned_card(card_id, user_id)
        self.db.delete(card)
        self._commit()

    def suspend_card(
        self,
        *,
        card_id: int,
        user_id: int,
    ) -> Flashcard:
        card = self._get_owned_card(card_id, user_id)
        card.is_suspended = True

        # Remove the card from any active study queue for this user.
        active_rows = (
            self.db.query(FlashcardSessionCard)
            .join(
                FlashcardStudySession,
                FlashcardStudySession.id == FlashcardSessionCard.session_id,
            )
            .filter(
                FlashcardSessionCard.card_id == card.id,
                FlashcardStudySession.user_id == user_id,
                FlashcardStudySession.status == "active",
                FlashcardSessionCard.completed.is_(False),
            )
            .all()
        )
        for row in active_rows:
            row.completed = True

        self._commit_refresh(card)
        return card

    def unsuspend_card(
        self,
        *,
        card_id: int,
        user_id: int,
    ) -> Flashcard:
        card = self._get_owned_card(card_id, user_id)
        card.is_suspended = False
        self._commit_refresh(card)
        return card

    # ------------------------------------------------------------------
    # Study overview
    # ------------------------------------------------------------------

    def get_study_overview(
        self,
        *,
        deck_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc_now(now)
        self._get_owned_deck(deck_id, user_id)

        cards = self.db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()

        total_cards = len(cards)
        suspended_count = sum(1 for card in cards if card.is_suspended)

        active_cards = [card for card in cards if not card.is_suspended]
        active_card_ids = [card.id for card in active_cards]

        states_by_card: dict[int, FlashcardReviewState] = {}
        if active_card_ids:
            states_by_card = {
                state.card_id: state
                for state in (
                    self.db.query(FlashcardReviewState)
                    .filter(
                        FlashcardReviewState.user_id == user_id,
                        FlashcardReviewState.card_id.in_(active_card_ids),
                    )
                    .all()
                )
            }

        new_count = 0
        learning_count = 0
        review_due_count = 0
        relearning_count = 0

        for card in active_cards:
            state = states_by_card.get(card.id)

            if state is None or state.state == "new":
                new_count += 1
            elif state.state == "learning":
                if state.due is None or self._as_utc(state.due) <= now:
                    learning_count += 1
            elif state.state == "review":
                if state.due is not None and self._as_utc(state.due) <= now:
                    review_due_count += 1
            elif state.state == "relearning":
                if state.due is None or self._as_utc(state.due) <= now:
                    relearning_count += 1

        due_now_count = new_count + learning_count + review_due_count + relearning_count

        return {
            "deck_id": deck_id,
            "total_cards": total_cards,
            "new_count": new_count,
            "learning_count": learning_count,
            "review_due_count": review_due_count,
            "relearning_count": relearning_count,
            "suspended_count": suspended_count,
            "due_now_count": due_now_count,
        }

    # ------------------------------------------------------------------
    # Study sessions
    # ------------------------------------------------------------------

    def start_or_resume_session(
        self,
        *,
        deck_id: int,
        user_id: int,
        options: FlashcardStudySessionCreate | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc_now(now)
        self._get_owned_deck(deck_id, user_id)

        existing = (
            self.db.query(FlashcardStudySession)
            .filter(
                FlashcardStudySession.deck_id == deck_id,
                FlashcardStudySession.user_id == user_id,
                FlashcardStudySession.status == "active",
            )
            .order_by(FlashcardStudySession.started_at.desc())
            .first()
        )

        if existing is not None:
            return self.get_session(
                session_id=existing.id,
                user_id=user_id,
                now=now,
            )

        options = options or FlashcardStudySessionCreate()

        cards = (
            self.db.query(Flashcard)
            .filter(
                Flashcard.deck_id == deck_id,
                Flashcard.is_suspended.is_(False),
            )
            .order_by(Flashcard.position.asc(), Flashcard.id.asc())
            .all()
        )

        card_ids = [card.id for card in cards]
        states_by_card: dict[int, FlashcardReviewState] = {}

        if card_ids:
            states_by_card = {
                state.card_id: state
                for state in (
                    self.db.query(FlashcardReviewState)
                    .filter(
                        FlashcardReviewState.user_id == user_id,
                        FlashcardReviewState.card_id.in_(card_ids),
                    )
                    .all()
                )
            }

        new_candidates: list[tuple[Flashcard, FlashcardReviewState | None]] = []
        review_candidates: list[tuple[Flashcard, FlashcardReviewState]] = []

        for card in cards:
            state = states_by_card.get(card.id)

            if state is None or state.state == "new":
                new_candidates.append((card, state))
                continue

            if state.due is None:
                continue

            if self._as_utc(state.due) <= now:
                review_candidates.append((card, state))

        if options.new_card_limit is not None:
            new_candidates = new_candidates[: options.new_card_limit]

        review_candidates.sort(
            key=lambda item: (
                self._as_utc(item[1].due),
                item[0].position,
                item[0].id,
            )
        )
        if options.review_card_limit is not None:
            review_candidates = review_candidates[: options.review_card_limit]

        session = FlashcardStudySession(
            deck_id=deck_id,
            user_id=user_id,
            status="active",
            new_cards_count=len(new_candidates),
            review_cards_count=len(review_candidates),
            reviewed_count=0,
        )

        self.db.add(session)
        self.db.flush()

        queue_position = 0

        # Due learning/relearning/review cards come before unseen cards.
        for card, state in review_candidates:
            self.db.add(
                FlashcardSessionCard(
                    session_id=session.id,
                    card_id=card.id,
                    queue_type=state.state,
                    queue_position=queue_position,
                    available_at=now,
                    completed=False,
                )
            )
            queue_position += 1

        for card, _state in new_candidates:
            self.db.add(
                FlashcardSessionCard(
                    session_id=session.id,
                    card_id=card.id,
                    queue_type="new",
                    queue_position=queue_position,
                    available_at=now,
                    completed=False,
                )
            )
            queue_position += 1

        self._commit()

        return self.get_session(
            session_id=session.id,
            user_id=user_id,
            now=now,
        )

    def get_session(
        self,
        *,
        session_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc_now(now)

        session = self._get_owned_session(session_id, user_id)

        return self._serialize_session(session=session, now=now)

    def complete_session(
        self,
        *,
        session_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc_now(now)
        session = self._get_owned_session(session_id, user_id)

        if session.status == "completed":
            return self._serialize_session(session=session, now=now)

        if session.status != "active":
            raise BadRequestError("Only an active flashcard session can be completed.")

        remaining = (
            self.db.query(FlashcardSessionCard.id)
            .filter(
                FlashcardSessionCard.session_id == session.id,
                FlashcardSessionCard.completed.is_(False),
            )
            .first()
        )
        if remaining is not None:
            raise BadRequestError("The study session still contains unfinished cards.")

        session.status = "completed"
        session.completed_at = now
        self._commit_refresh(session)

        return self._serialize_session(session=session, now=now)

    def abandon_session(
        self,
        *,
        session_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = self._utc_now(now)
        session = self._get_owned_session(session_id, user_id)

        if session.status == "completed":
            raise BadRequestError("A completed flashcard session cannot be abandoned.")

        session.status = "abandoned"
        session.completed_at = now
        self._commit_refresh(session)

        return self._serialize_session(session=session, now=now)

    # ------------------------------------------------------------------
    # Review pipeline
    # ------------------------------------------------------------------

    def review_card(
        self,
        *,
        session_id: int,
        user_id: int,
        request: FlashcardReviewRequest,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Review one queued card as one logical DB transaction."""

        now = self._utc_now(now)

        try:
            session = self._get_owned_session(session_id, user_id)

            if session.status != "active":
                raise BadRequestError("Flashcard session is not active.")

            session_card = (
                self.db.query(FlashcardSessionCard)
                .join(Flashcard, Flashcard.id == FlashcardSessionCard.card_id)
                .filter(
                    FlashcardSessionCard.session_id == session.id,
                    FlashcardSessionCard.card_id == request.card_id,
                )
                .with_for_update()
                .first()
            )

            if session_card is None:
                raise BadRequestError("The requested card does not belong to this study session.")

            if session_card.completed:
                raise BadRequestError("This flashcard has already been completed in this session.")

            if self._as_utc(session_card.available_at) > now:
                raise BadRequestError("This flashcard is not available for review yet.")

            card = self._get_owned_card(request.card_id, user_id)

            if card.deck_id != session.deck_id:
                raise BadRequestError("The requested card does not belong to the session deck.")

            if card.is_suspended:
                raise BadRequestError("Suspended flashcards cannot be reviewed.")

            review_state = (
                self.db.query(FlashcardReviewState)
                .filter(
                    FlashcardReviewState.card_id == card.id,
                    FlashcardReviewState.user_id == user_id,
                )
                .with_for_update()
                .first()
            )

            state_before = self._to_scheduler_state(
                card_id=card.id,
                review_state=review_state,
            )

            result = self.scheduler.review(
                state_before,
                request.rating,
                reviewed_at=now,
                response_time_ms=request.response_time_ms,
            )

            if review_state is None:
                review_state = FlashcardReviewState(
                    card_id=card.id,
                    user_id=user_id,
                )
                self.db.add(review_state)

            self._apply_scheduler_result(
                review_state=review_state,
                result=result,
            )

            review_log = FlashcardReviewLog(
                card_id=card.id,
                user_id=user_id,
                session_id=session.id,
                rating=result.rating,
                state_before=result.state_before,
                state_after=result.state_after,
                due_before=result.due_before,
                due_after=result.due_after,
                stability_before=result.stability_before,
                stability_after=result.stability_after,
                difficulty_before=result.difficulty_before,
                difficulty_after=result.difficulty_after,
                scheduled_days=result.scheduled_days,
                elapsed_days=result.elapsed_days,
                reviewed_at=result.reviewed_at,
                response_time_ms=result.response_time_ms,
            )
            self.db.add(review_log)

            session.reviewed_count += 1
            session_card.review_count += 1
            session_card.queue_type = result.state_after

            if result.state_after in {"learning", "relearning"}:
                # Keep the card in this SAME session and delay it until FSRS says
                # its next learning/relearning step becomes available.
                session_card.completed = False
                session_card.available_at = result.due_after
                session_card.queue_position = self._next_queue_position(session.id)
            else:
                # Once FSRS graduates/keeps the card in Review state, its next due
                # belongs to a future study session.
                session_card.completed = True
                session_card.available_at = result.due_after

            self.db.flush()

            pending = (
                self.db.query(FlashcardSessionCard.id)
                .filter(
                    FlashcardSessionCard.session_id == session.id,
                    FlashcardSessionCard.completed.is_(False),
                )
                .first()
            )

            if pending is None:
                session.status = "completed"
                session.completed_at = now

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        serialized_session = self.get_session(
            session_id=session_id,
            user_id=user_id,
            now=now,
        )

        return {
            "reviewed_card_id": request.card_id,
            "rating": request.rating,
            "state_before": result.state_before,
            "state_after": result.state_after,
            "next_due": result.due_after,
            "current_card": serialized_session["current_card"],
            "next_available_at": serialized_session["next_available_at"],
            "remaining_new": serialized_session["remaining_new"],
            "remaining_learning": serialized_session["remaining_learning"],
            "remaining_review": serialized_session["remaining_review"],
            "remaining_relearning": serialized_session["remaining_relearning"],
            "session_completed": serialized_session["status"] == "completed",
        }

    # ------------------------------------------------------------------
    # Internal ownership helpers
    # ------------------------------------------------------------------

    def _get_owned_notebook(self, notebook_id: int, user_id: int) -> Notebook:
        notebook = (
            self.db.query(Notebook)
            .filter(
                Notebook.id == notebook_id,
                Notebook.user_id == user_id,
            )
            .first()
        )
        if notebook is None:
            raise NotFoundError("Notebook not found.")
        return notebook

    def _get_owned_deck(self, deck_id: int, user_id: int) -> FlashcardDeck:
        deck = (
            self.db.query(FlashcardDeck)
            .filter(
                FlashcardDeck.id == deck_id,
                FlashcardDeck.user_id == user_id,
            )
            .first()
        )
        if deck is None:
            raise NotFoundError("Flashcard deck not found.")
        return deck

    def _get_owned_card(self, card_id: int, user_id: int) -> Flashcard:
        card = (
            self.db.query(Flashcard)
            .join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
            .filter(
                Flashcard.id == card_id,
                FlashcardDeck.user_id == user_id,
            )
            .first()
        )
        if card is None:
            raise NotFoundError("Flashcard not found.")
        return card

    def _get_owned_session(
        self,
        session_id: int,
        user_id: int,
    ) -> FlashcardStudySession:
        session = (
            self.db.query(FlashcardStudySession)
            .filter(
                FlashcardStudySession.id == session_id,
                FlashcardStudySession.user_id == user_id,
            )
            .first()
        )
        if session is None:
            raise NotFoundError("Flashcard study session not found.")
        return session

    def _validate_source_document_in_deck_notebook(
        self,
        *,
        deck_id: int,
        document_id: int,
        user_id: int,
    ) -> None:
        # Manual cards may optionally reference a source document, but that source
        # should belong to the same notebook. Import locally to avoid introducing
        # an unnecessary top-level model dependency.
        from app.models.notebook_model import NotebookDocument

        deck = self._get_owned_deck(deck_id, user_id)

        exists = (
            self.db.query(NotebookDocument.id)
            .filter(
                NotebookDocument.notebook_id == deck.notebook_id,
                NotebookDocument.document_id == document_id,
            )
            .first()
        )

        if exists is None:
            raise BadRequestError(
                "source_document_id must belong to the flashcard deck's notebook."
            )

    @staticmethod
    def serialize_deck_list_item(deck: FlashcardDeck) -> dict[str, Any]:
        return {
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

    @staticmethod
    def _build_generation_source_context(
        *,
        chunks: list[QuizChunk],
        allowed_document_ids: set[int],
    ) -> str:
        blocks: list[str] = []
        for chunk in chunks:
            try:
                document_id = int(chunk.metadata.get("document_id"))
            except (TypeError, ValueError):
                continue
            if document_id not in allowed_document_ids:
                continue
            blocks.append(
                "\n".join(
                    [
                        f"source_document_id: {document_id}",
                        f"source_chunk_id: {chunk.chunk_id}",
                        "content:",
                        chunk.content,
                    ]
                )
            )
        if not blocks:
            raise ValueError("No valid source context was found.")
        return "\n\n---\n\n".join(blocks)

    @staticmethod
    def _safe_generation_error(exc: Exception) -> str:
        if isinstance(exc, FlashcardOutputParseError):
            return "AI returned invalid flashcard data. Please try again."
        if isinstance(exc, ValueError):
            return str(exc)[:500]
        return "Flashcard generation failed. Please try again."

    # ------------------------------------------------------------------
    # Internal scheduler mapping
    # ------------------------------------------------------------------

    def _to_scheduler_state(
        self,
        *,
        card_id: int,
        review_state: FlashcardReviewState | None,
    ) -> SchedulerCardState:
        if review_state is None:
            return SchedulerCardState(card_id=card_id)

        return SchedulerCardState(
            card_id=card_id,
            state=review_state.state,
            due=self._as_utc(review_state.due) if review_state.due else None,
            stability=review_state.stability,
            difficulty=review_state.difficulty,
            step=review_state.step,
            last_review=(
                self._as_utc(review_state.last_review) if review_state.last_review else None
            ),
            reps=review_state.reps,
            lapses=review_state.lapses,
        )

    @staticmethod
    def _apply_scheduler_result(
        *,
        review_state: FlashcardReviewState,
        result: SchedulerResult,
    ) -> None:
        review_state.state = result.state_after
        review_state.due = result.due_after
        review_state.stability = result.stability_after
        review_state.difficulty = result.difficulty_after
        review_state.step = result.step_after
        review_state.elapsed_days = result.elapsed_days
        review_state.scheduled_days = result.scheduled_days
        review_state.reps = result.reps
        review_state.lapses = result.lapses
        review_state.last_review = result.reviewed_at

    # ------------------------------------------------------------------
    # Internal queue/session helpers
    # ------------------------------------------------------------------

    def _serialize_session(
        self,
        *,
        session: FlashcardStudySession,
        now: datetime,
    ) -> dict[str, Any]:
        rows = (
            self.db.query(FlashcardSessionCard)
            .options(joinedload(FlashcardSessionCard.card))
            .filter(FlashcardSessionCard.session_id == session.id)
            .order_by(
                FlashcardSessionCard.queue_position.asc(),
                FlashcardSessionCard.id.asc(),
            )
            .all()
        )

        unfinished = [row for row in rows if not row.completed]

        current_row = next(
            (
                row
                for row in unfinished
                if self._as_utc(row.available_at) <= now and not row.card.is_suspended
            ),
            None,
        )

        waiting_times = [
            self._as_utc(row.available_at)
            for row in unfinished
            if not row.card.is_suspended and self._as_utc(row.available_at) > now
        ]
        next_available_at = min(waiting_times) if waiting_times else None

        remaining = {
            "new": 0,
            "learning": 0,
            "review": 0,
            "relearning": 0,
        }
        for row in unfinished:
            if row.card.is_suspended:
                continue
            if row.queue_type in remaining:
                remaining[row.queue_type] += 1

        current_card = (
            self._serialize_session_card(current_row) if current_row is not None else None
        )

        return {
            "id": session.id,
            "deck_id": session.deck_id,
            "user_id": session.user_id,
            "status": session.status,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "new_cards_count": session.new_cards_count,
            "review_cards_count": session.review_cards_count,
            "reviewed_count": session.reviewed_count,
            "current_card": current_card,
            "remaining_new": remaining["new"],
            "remaining_learning": remaining["learning"],
            "remaining_review": remaining["review"],
            "remaining_relearning": remaining["relearning"],
            "next_available_at": next_available_at,
        }

    @staticmethod
    def _serialize_session_card(
        row: FlashcardSessionCard,
    ) -> dict[str, Any]:
        return {
            "card_id": row.card_id,
            "queue_type": row.queue_type,
            "queue_position": row.queue_position,
            "available_at": row.available_at,
            "review_count": row.review_count,
            "completed": row.completed,
            "card": row.card,
        }

    def _next_queue_position(self, session_id: int) -> int:
        max_position = (
            self.db.query(func.max(FlashcardSessionCard.queue_position))
            .filter(FlashcardSessionCard.session_id == session_id)
            .scalar()
        )
        return 0 if max_position is None else int(max_position) + 1

    # ------------------------------------------------------------------
    # Transaction / datetime helpers
    # ------------------------------------------------------------------

    def _commit_refresh(self, obj: Any) -> None:
        try:
            self.db.commit()
            self.db.refresh(obj)
        except Exception:
            self.db.rollback()
            raise

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    @classmethod
    def _utc_now(cls, value: datetime | None = None) -> datetime:
        return cls._as_utc(value or datetime.now(timezone.utc))

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        """Normalize DB/application datetimes to aware UTC.

        MySQL frequently returns naive datetimes even for SQLAlchemy
        DateTime(timezone=True). We interpret those DB values as UTC because
        Flashcard scheduling is persisted in UTC.
        """

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
