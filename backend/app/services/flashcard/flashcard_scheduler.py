from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from fsrs import Card, Rating, Scheduler, State

FlashcardRating = Literal["again", "hard", "good", "easy"]
FlashcardLearningState = Literal["new", "learning", "review", "relearning"]


@dataclass(frozen=True, slots=True)
class SchedulerCardState:
    """Domain-facing scheduling state.

    This type deliberately contains no SQLAlchemy or third-party FSRS objects.
    A missing ReviewState row should be represented by state="new".
    """

    card_id: int
    state: FlashcardLearningState = "new"
    due: datetime | None = None
    stability: float | None = None
    difficulty: float | None = None
    step: int | None = None
    last_review: datetime | None = None
    reps: int = 0
    lapses: int = 0


@dataclass(frozen=True, slots=True)
class SchedulerResult:
    card_id: int

    state_before: FlashcardLearningState
    state_after: FlashcardLearningState
    rating: FlashcardRating

    due_before: datetime | None
    due_after: datetime

    stability_before: float | None
    stability_after: float | None

    difficulty_before: float | None
    difficulty_after: float | None

    step_before: int | None
    step_after: int | None

    elapsed_days: int
    scheduled_days: int

    reps: int
    lapses: int

    reviewed_at: datetime
    response_time_ms: int | None


class FlashcardScheduler(ABC):
    """Application-owned scheduler interface.

    Services should depend on this interface, never directly on py-fsrs.
    """

    @abstractmethod
    def review(
        self,
        state: SchedulerCardState,
        rating: FlashcardRating,
        *,
        reviewed_at: datetime,
        response_time_ms: int | None = None,
    ) -> SchedulerResult:
        raise NotImplementedError


class FSRSScheduler(FlashcardScheduler):
    """Adapter around the py-fsrs Scheduler.

    Defaults intentionally follow py-fsrs:
    - desired retention: 0.9
    - learning steps: 1 minute, 10 minutes
    - relearning step: 10 minutes
    - maximum interval: 36500 days

    `enable_fuzzing` is configurable. Disable it in deterministic tests.
    """

    _RATING_TO_FSRS = {
        "again": Rating.Again,
        "hard": Rating.Hard,
        "good": Rating.Good,
        "easy": Rating.Easy,
    }

    _STATE_TO_FSRS = {
        "learning": State.Learning,
        "review": State.Review,
        "relearning": State.Relearning,
    }

    _STATE_FROM_FSRS = {
        State.Learning: "learning",
        State.Review: "review",
        State.Relearning: "relearning",
    }

    def __init__(
        self,
        *,
        desired_retention: float = 0.9,
        maximum_interval: int = 36500,
        enable_fuzzing: bool = True,
        parameters: tuple[float, ...] | list[float] | None = None,
    ) -> None:
        kwargs = {
            "desired_retention": desired_retention,
            "maximum_interval": maximum_interval,
            "enable_fuzzing": enable_fuzzing,
        }
        if parameters is not None:
            kwargs["parameters"] = parameters

        self._scheduler = Scheduler(**kwargs)

    def review(
        self,
        state: SchedulerCardState,
        rating: FlashcardRating,
        *,
        reviewed_at: datetime,
        response_time_ms: int | None = None,
    ) -> SchedulerResult:
        reviewed_at = self._require_utc(reviewed_at)
        self._validate_state(state)
        self._validate_response_time(response_time_ms)

        fsrs_rating = self._rating_to_fsrs(rating)
        fsrs_card = self._to_fsrs_card(state, reviewed_at=reviewed_at)

        due_before = state.due
        stability_before = state.stability
        difficulty_before = state.difficulty
        step_before = state.step

        updated_card, _ = self._scheduler.review_card(
            card=fsrs_card,
            rating=fsrs_rating,
            review_datetime=reviewed_at,
            review_duration=response_time_ms,
        )

        state_after = self._STATE_FROM_FSRS[updated_card.state]

        elapsed_days = (
            max(0, (reviewed_at - state.last_review).days) if state.last_review is not None else 0
        )
        scheduled_days = max(0, (updated_card.due - reviewed_at).days)

        # A lapse means a previously graduated Review card was forgotten.
        lapses = state.lapses
        if state.state == "review" and rating == "again":
            lapses += 1

        return SchedulerResult(
            card_id=state.card_id,
            state_before=state.state,
            state_after=state_after,
            rating=rating,
            due_before=due_before,
            due_after=updated_card.due,
            stability_before=stability_before,
            stability_after=updated_card.stability,
            difficulty_before=difficulty_before,
            difficulty_after=updated_card.difficulty,
            step_before=step_before,
            step_after=updated_card.step,
            elapsed_days=elapsed_days,
            scheduled_days=scheduled_days,
            reps=state.reps + 1,
            lapses=lapses,
            reviewed_at=reviewed_at,
            response_time_ms=response_time_ms,
        )

    def _to_fsrs_card(
        self,
        state: SchedulerCardState,
        *,
        reviewed_at: datetime,
    ) -> Card:
        if state.state == "new":
            # py-fsrs models an unseen card as Learning(step=0), due immediately.
            return Card(
                card_id=state.card_id,
                state=State.Learning,
                step=0,
                due=reviewed_at,
                last_review=None,
            )

        fsrs_state = self._STATE_TO_FSRS[state.state]

        due = self._require_utc(state.due) if state.due is not None else reviewed_at
        last_review = (
            self._require_utc(state.last_review) if state.last_review is not None else None
        )

        return Card(
            card_id=state.card_id,
            state=fsrs_state,
            step=state.step,
            stability=state.stability,
            difficulty=state.difficulty,
            due=due,
            last_review=last_review,
        )

    @classmethod
    def _rating_to_fsrs(cls, rating: FlashcardRating) -> Rating:
        try:
            return cls._RATING_TO_FSRS[rating]
        except KeyError as exc:
            raise ValueError(f"Unsupported flashcard rating: {rating}") from exc

    @staticmethod
    def _require_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Scheduler datetimes must be timezone-aware UTC datetimes.")

        utc_value = value.astimezone(timezone.utc)
        return utc_value

    @staticmethod
    def _validate_response_time(response_time_ms: int | None) -> None:
        if response_time_ms is not None and response_time_ms < 0:
            raise ValueError("response_time_ms must be greater than or equal to zero.")

    @staticmethod
    def _validate_state(state: SchedulerCardState) -> None:
        if state.reps < 0 or state.lapses < 0:
            raise ValueError("reps and lapses must be greater than or equal to zero.")

        if state.state == "new":
            if state.last_review is not None:
                raise ValueError("A new card cannot have last_review.")
            return

        if state.due is None:
            raise ValueError("A non-new scheduling state must have a due datetime.")

        if state.state in {"learning", "relearning"} and state.step is None:
            raise ValueError(
                f"A card in state={state.state!r} must persist its FSRS learning step."
            )

        if state.state == "review":
            if state.step is not None:
                raise ValueError("A Review-state card must have step=None.")
            if state.stability is None or state.difficulty is None:
                raise ValueError("A Review-state card must have stability and difficulty.")


__all__ = [
    "FlashcardLearningState",
    "FlashcardRating",
    "FlashcardScheduler",
    "FSRSScheduler",
    "SchedulerCardState",
    "SchedulerResult",
]
