from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.schemas.dashboard_schema import CandidateStatForPrompt
from app.services.dashboard.dashboard_insight_service import DashboardInsightService


class FailLLM:
    async def generate(self, _prompt):
        raise AssertionError("LLM should not be called")


class SuccessLLM:
    def __init__(self):
        self.calls = 0

    async def generate(self, _prompt):
        self.calls += 1
        return '{"text":"Overall accuracy: 28%. Keep practicing!","selected_keys":["overall_accuracy"]}'


class QueryResult:
    def __init__(self, value):
        self.value = value

    def filter(self, *_args):
        return self

    def first(self):
        return self.value


class QueuedDB:
    def __init__(self, values):
        self.values = iter(values)

    def query(self, *_args):
        return QueryResult(next(self.values))

    def add(self, _value):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


def test_cache_requires_fresh_timestamp_and_unchanged_attempt_watermark():
    now = datetime.now(timezone.utc)
    cache = SimpleNamespace(
        generated_at=now - timedelta(hours=1),
        source_attempt_id=10,
        source_attempt_updated_at=now - timedelta(hours=2),
    )

    assert DashboardInsightService._is_cache_valid(
        cache, 10, now - timedelta(hours=2), now
    )
    assert not DashboardInsightService._is_cache_valid(cache, 11, now, now)

    cache.generated_at = now - timedelta(hours=25)
    assert not DashboardInsightService._is_cache_valid(
        cache, 10, now - timedelta(hours=2), now
    )


def test_parser_rejects_numbers_not_present_in_selected_stats():
    candidates = [
        CandidateStatForPrompt(
            key="accuracy_trend",
            label="Recent accuracy trend",
            value="+12 pts",
            context={},
        )
    ]

    parsed = DashboardInsightService._parse_output(
        '{"text":"Recent accuracy trend: +12 pts. Keep it up!","selected_keys":["accuracy_trend"]}',
        candidates,
    )
    assert parsed.selected_keys == ["accuracy_trend"]

    with pytest.raises(ValueError, match="unsupported numbers"):
        DashboardInsightService._parse_output(
            '{"text":"Recent accuracy trend: +20 pts.","selected_keys":["accuracy_trend"]}',
            candidates,
        )


@pytest.mark.asyncio
async def test_insufficient_data_does_not_call_llm(monkeypatch):
    monkeypatch.setattr(
        "app.services.dashboard_insight_service.DashboardService.get_analytics",
        lambda *_args, **_kwargs: SimpleNamespace(
            aggregate=SimpleNamespace(completed_attempts=2)
        ),
    )

    result = await DashboardInsightService(SimpleNamespace(), FailLLM()).get_insight(
        SimpleNamespace(id=1)
    )

    assert result.has_meaningful_data is False
    assert result.selected_stats == []


@pytest.mark.asyncio
async def test_manual_refresh_during_cooldown_uses_cache_without_calling_llm(
    monkeypatch,
):
    now = datetime.now(timezone.utc)
    analytics = SimpleNamespace(aggregate=SimpleNamespace(completed_attempts=3))
    candidate = CandidateStatForPrompt(
        key="overall_accuracy",
        label="Overall accuracy",
        value="28%",
        context={},
    )
    cache = SimpleNamespace(
        insight_text="Overall accuracy: 28%. Keep practicing.",
        selected_stats=[
            {"key": "overall_accuracy", "label": "Overall accuracy", "value": "28%"}
        ],
        source_attempt_id=10,
        source_attempt_updated_at=now - timedelta(minutes=1),
        generated_at=now - timedelta(minutes=1),
    )
    watermark = SimpleNamespace(id=10, updated_at=cache.source_attempt_updated_at)
    monkeypatch.setattr(
        "app.services.dashboard_insight_service.DashboardService.get_analytics",
        lambda *_args, **_kwargs: analytics,
    )
    monkeypatch.setattr(
        DashboardInsightService,
        "_format_candidates",
        staticmethod(lambda _analytics: [candidate]),
    )

    result = await DashboardInsightService(
        QueuedDB([watermark, cache]), FailLLM()
    ).get_insight(SimpleNamespace(id=99), force_refresh=True)

    assert result.cached is True
    assert result.refresh_available_at > now


@pytest.mark.asyncio
async def test_manual_refresh_after_cooldown_regenerates_and_resets_timestamp(
    monkeypatch,
):
    now = datetime.now(timezone.utc)
    analytics = SimpleNamespace(aggregate=SimpleNamespace(completed_attempts=3))
    candidate = CandidateStatForPrompt(
        key="overall_accuracy",
        label="Overall accuracy",
        value="28%",
        context={},
    )
    cache = SimpleNamespace(
        insight_text="Overall accuracy: 28%. Keep practicing.",
        selected_stats=[
            {"key": "overall_accuracy", "label": "Overall accuracy", "value": "28%"}
        ],
        source_attempt_id=10,
        source_attempt_updated_at=now - timedelta(minutes=10),
        generated_at=now - timedelta(minutes=6),
    )
    watermark = SimpleNamespace(id=10, updated_at=cache.source_attempt_updated_at)
    monkeypatch.setattr(
        "app.services.dashboard_insight_service.DashboardService.get_analytics",
        lambda *_args, **_kwargs: analytics,
    )
    monkeypatch.setattr(
        DashboardInsightService,
        "_format_candidates",
        staticmethod(lambda _analytics: [candidate]),
    )
    llm = SuccessLLM()

    result = await DashboardInsightService(
        QueuedDB([watermark, cache]), llm
    ).get_insight(SimpleNamespace(id=100), force_refresh=True)

    assert llm.calls == 1
    assert result.cached is False
    assert result.generated_at > now - timedelta(seconds=2)
    assert result.refresh_available_at - result.generated_at == timedelta(minutes=5)
