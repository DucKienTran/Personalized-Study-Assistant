import asyncio
from datetime import datetime, timedelta, timezone
import json
import re

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMClient
from app.ai.prompts.dashboard_insight_prompt import DashboardInsightPromptBuilder
from app.models.dashboard_insight_model import DashboardInsightCache
from app.models.quiz_model import QuizAttempt
from app.schemas.dashboard_schema import (
    CandidateStatForPrompt,
    DashboardAnalyticsOut,
    DashboardInsightLLMOutput,
    DashboardInsightOut,
    InsightStatOut,
)
from app.services.dashboard.dashboard_service import DashboardService


class DashboardInsightService:
    CACHE_TTL = timedelta(hours=24)
    MANUAL_REFRESH_COOLDOWN = timedelta(minutes=5)
    MIN_COMPLETED_ATTEMPTS = 3
    FALLBACK_TEXT = "Keep learning consistently. Your progress insights will become clearer as you complete more quizzes."
    _user_locks: dict[int, asyncio.Lock] = {}

    def __init__(self, db: Session, llm_client: LLMClient):
        self.db = db
        self.llm_client = llm_client

    async def get_insight(
        self, current_user, force_refresh: bool = False
    ) -> DashboardInsightOut:
        lock = self._user_locks.setdefault(current_user.id, asyncio.Lock())
        async with lock:
            return await self._get_insight_locked(current_user, force_refresh)

    async def _get_insight_locked(
        self, current_user, force_refresh: bool
    ) -> DashboardInsightOut:
        analytics = DashboardService(self.db).get_analytics(current_user)
        if analytics.aggregate.completed_attempts < self.MIN_COMPLETED_ATTEMPTS:
            return DashboardInsightOut(
                text=self.FALLBACK_TEXT,
                selected_stats=[],
                has_meaningful_data=False,
            )

        attempt_watermark = (
            self.db.query(
                func.max(QuizAttempt.id).label("id"),
                func.max(QuizAttempt.updated_at).label("updated_at"),
            )
            .filter(QuizAttempt.user_id == current_user.id)
            .first()
        )
        latest_attempt_id = attempt_watermark.id if attempt_watermark else None
        latest_attempt_update = attempt_watermark.updated_at if attempt_watermark else None
        cache = (
            self.db.query(DashboardInsightCache)
            .filter(DashboardInsightCache.user_id == current_user.id)
            .first()
        )
        now = datetime.now(timezone.utc)
        candidates = self._format_candidates(analytics)
        cache_is_valid = (
            cache
            and self._is_cache_valid(
                cache, latest_attempt_id, latest_attempt_update, now
            )
            and self._cached_text_is_supported(cache, candidates)
        )
        if cache_is_valid:
            refresh_available_at = self._refresh_available_at(cache)
            if not force_refresh or now < refresh_available_at:
                return DashboardInsightOut(
                    text=cache.insight_text,
                    selected_stats=cache.selected_stats,
                    has_meaningful_data=True,
                    cached=True,
                    generated_at=self._as_utc(cache.generated_at),
                    refresh_available_at=refresh_available_at,
                )

        prompt = DashboardInsightPromptBuilder.build(candidates)
        try:
            raw_output = await self.llm_client.generate(prompt)
            parsed = self._parse_output(raw_output, candidates)
        except Exception:
            if cache:
                return DashboardInsightOut(
                    text=cache.insight_text,
                    selected_stats=cache.selected_stats,
                    has_meaningful_data=True,
                    cached=True,
                    generated_at=self._as_utc(cache.generated_at),
                    refresh_available_at=self._refresh_available_at(cache),
                )
            return DashboardInsightOut(
                text=self.FALLBACK_TEXT,
                selected_stats=[],
                has_meaningful_data=True,
            )
        selected_by_key = {candidate.key: candidate for candidate in candidates}
        selected_stats = [
            InsightStatOut(
                key=key,
                label=selected_by_key[key].label,
                value=selected_by_key[key].value,
            )
            for key in parsed.selected_keys
        ]

        if cache is None:
            cache = DashboardInsightCache(user_id=current_user.id)
            self.db.add(cache)
        cache.insight_text = parsed.text
        cache.selected_stats = [stat.model_dump() for stat in selected_stats]
        cache.source_attempt_id = latest_attempt_id
        cache.source_attempt_updated_at = latest_attempt_update
        cache.generated_at = now
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            winner = (
                self.db.query(DashboardInsightCache)
                .filter(DashboardInsightCache.user_id == current_user.id)
                .first()
            )
            if winner and self._is_cache_valid(
                winner, latest_attempt_id, latest_attempt_update, now
            ) and self._cached_text_is_supported(winner, candidates):
                return DashboardInsightOut(
                    text=winner.insight_text,
                    selected_stats=winner.selected_stats,
                    has_meaningful_data=True,
                    cached=True,
                    generated_at=self._as_utc(winner.generated_at),
                    refresh_available_at=self._refresh_available_at(winner),
                )
            raise

        return DashboardInsightOut(
            text=parsed.text,
            selected_stats=selected_stats,
            has_meaningful_data=True,
            generated_at=now,
            refresh_available_at=now + self.MANUAL_REFRESH_COOLDOWN,
        )

    @classmethod
    def _refresh_available_at(cls, cache) -> datetime:
        return cls._as_utc(cache.generated_at) + cls.MANUAL_REFRESH_COOLDOWN

    @classmethod
    def _is_cache_valid(
        cls, cache, latest_attempt_id, latest_attempt_update, now: datetime
    ) -> bool:
        generated_at = cls._as_utc(cache.generated_at)
        source_update = cls._as_utc(cache.source_attempt_updated_at)
        latest_update = cls._as_utc(latest_attempt_update)
        fresh = now - generated_at < cls.CACHE_TTL
        unchanged = cache.source_attempt_id == latest_attempt_id and (
            latest_update is None
            or (source_update is not None and latest_update <= source_update)
        )
        return fresh and unchanged

    @staticmethod
    def _cached_text_is_supported(cache, candidates: list[CandidateStatForPrompt]) -> bool:
        available = {candidate.key: candidate for candidate in candidates}
        selected = cache.selected_stats or []
        return bool(selected) and all(
            item.get("key") in available
            and f'{item.get("label")}: {item.get("value")}'.lower()
            in cache.insight_text.lower()
            for item in selected
        )

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @staticmethod
    def _format_candidates(analytics: DashboardAnalyticsOut) -> list[CandidateStatForPrompt]:
        aggregate = analytics.aggregate
        stats = analytics.candidates
        candidates = [
            CandidateStatForPrompt(
                key="completed_attempts",
                label="Completed attempts",
                value=str(aggregate.completed_attempts),
                context={"count": aggregate.completed_attempts},
            ),
            CandidateStatForPrompt(
                key="overall_accuracy",
                label="Overall accuracy",
                value=f"{aggregate.overall_accuracy or 0:g}%",
                context={"percent": aggregate.overall_accuracy},
            ),
            CandidateStatForPrompt(
                key="current_streak_days",
                label="Current streak",
                value=f"{stats.current_streak_days} days",
                context={"days": stats.current_streak_days},
            ),
        ]

        if stats.time_spent_trend:
            delta = stats.time_spent_trend.delta
            candidates.append(
                CandidateStatForPrompt(
                    key="time_spent_trend",
                    label="Time per question trend",
                    value=f"{abs(delta):g}s {'faster' if delta < 0 else 'slower'}",
                    context=stats.time_spent_trend.model_dump(),
                )
            )
        weekly = stats.weekly_activity_change
        candidates.append(
            CandidateStatForPrompt(
                key="weekly_activity_change",
                label="Weekly activity",
                value=(
                    f"{weekly.percent_change:+g}%"
                    if weekly.percent_change is not None
                    else f"{weekly.current_count} activities this week"
                ),
                context=weekly.model_dump(),
            )
        )
        return candidates

    @staticmethod
    def _parse_output(
        raw_output: str, candidates: list[CandidateStatForPrompt]
    ) -> DashboardInsightLLMOutput:
        cleaned = raw_output.strip()
        fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1)
        try:
            parsed = DashboardInsightLLMOutput.model_validate(json.loads(cleaned))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError("Invalid dashboard insight response") from exc

        allowed = {candidate.key: candidate for candidate in candidates}
        selected_keys = list(dict.fromkeys(parsed.selected_keys))
        if not 1 <= len(selected_keys) <= 3 or any(key not in allowed for key in selected_keys):
            raise ValueError("Dashboard insight selected invalid candidate keys")

        allowed_numbers = {
            number
            for key in selected_keys
            for number in re.findall(r"-?\d+(?:\.\d+)?", allowed[key].value)
        }
        text_numbers = set(re.findall(r"-?\d+(?:\.\d+)?", parsed.text))
        if not text_numbers.issubset(allowed_numbers):
            raise ValueError("Dashboard insight introduced unsupported numbers")
        if any(
            f"{allowed[key].label}: {allowed[key].value}".lower()
            not in parsed.text.lower()
            for key in selected_keys
        ):
            raise ValueError("Dashboard insight did not preserve label-value pairs")
        return DashboardInsightLLMOutput(text=parsed.text.strip(), selected_keys=selected_keys)
