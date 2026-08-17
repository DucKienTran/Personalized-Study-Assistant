from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
import json
import logging
from pathlib import Path
import subprocess
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.services.document.chunk_builder import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
)

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_WRITE_LOCK = Lock()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@lru_cache(maxsize=1)
def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_BACKEND_ROOT,
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _output_file() -> Path:
    output_dir = Path(settings.RAG_EVALUATION_OUTPUT_DIR)
    if not output_dir.is_absolute():
        output_dir = _BACKEND_ROOT / output_dir
    return output_dir / "rag_traces.jsonl"


class EvaluationTrace:
    """Thread-safe, request-scoped trace written only in evaluation mode."""

    def __init__(
        self,
        *,
        original_query: str,
        top_k: int,
        streaming: bool,
        reranker_model: str,
        candidate_multiplier: int,
        rrf_k: int,
    ) -> None:
        timestamp = _utc_now()
        self._lock = Lock()
        self._written = False
        self.data: dict[str, Any] = {
            "schema_version": "1.0",
            "trace_id": str(uuid4()),
            "timestamp": timestamp,
            "configuration": {
                "captured_at": timestamp,
                "git_commit": _git_commit(),
                "embedding_model": settings.VOYAGE_MODEL,
                "reranker_model": reranker_model,
                "llm_model": settings.AZURE_OPENAI_CHAT_MODEL,
                "chunk_size": DEFAULT_CHUNK_SIZE,
                "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
                "top_k": top_k,
                "candidate_counts": {
                    "vector_requested": top_k * candidate_multiplier,
                    "bm25_requested": top_k * candidate_multiplier,
                    "rrf_requested": top_k * candidate_multiplier,
                    "reranker_requested": top_k,
                    "candidate_multiplier": candidate_multiplier,
                    "rrf_k": rrf_k,
                },
                "generation": {
                    "streaming": streaming,
                    "max_output_tokens": (
                        None if streaming else settings.AZURE_OPENAI_MAX_OUTPUT_TOKENS
                    ),
                    "temperature": None,
                    "top_p": None,
                    "seed": None,
                    "null_parameter_meaning": "provider default/not explicitly configured",
                },
            },
            "query": {
                "original": original_query,
                "rewritten": None,
                "notebook_id": None,
                "active_document_ids": [],
                "top_k": top_k,
            },
            "retrieval": {
                "vector_candidates": [],
                "bm25_candidates": [],
                "rrf_candidates": [],
                "reranker": {
                    "input": [],
                    "output": [],
                    "fallback": False,
                },
            },
            "context": {"final_order": []},
            "generation": {"answer_characters": 0},
            "citations": {"sources": []},
            "timings_ms": {
                "query_rewrite": None,
                "query_embedding": None,
                "vector_search": None,
                "bm25_load": None,
                "bm25_search": None,
                "rrf": None,
                "reranking": None,
                "context_building": None,
                "total_retrieval": None,
                "llm_ttft": None,
                "llm_total": None,
                "end_to_end_stream": None,
            },
            "outcome": {
                "status": "running",
                "error_type": None,
                "error_message": None,
            },
        }

    def set_query_details(
        self,
        *,
        rewritten_query: str,
        notebook_id: int,
        active_document_ids: list[int],
    ) -> None:
        with self._lock:
            self.data["query"]["rewritten"] = rewritten_query
            self.data["query"]["notebook_id"] = notebook_id
            self.data["query"]["active_document_ids"] = list(active_document_ids)

    def set_timing(self, stage: str, duration_ms: float) -> None:
        with self._lock:
            self.data["timings_ms"][stage] = round(duration_ms, 3)

    def set_retrieval_stage(self, stage: str, value: Any) -> None:
        with self._lock:
            self.data["retrieval"][stage] = deepcopy(value)

    def set_reranker(self, *, inputs: list[dict], outputs: list[dict], fallback: bool) -> None:
        with self._lock:
            self.data["retrieval"]["reranker"] = {
                "input": deepcopy(inputs),
                "output": deepcopy(outputs),
                "fallback": fallback,
            }

    def set_context_order(self, chunks: list[dict]) -> None:
        with self._lock:
            self.data["context"]["final_order"] = deepcopy(chunks)

    def set_citations(self, sources: list[dict]) -> None:
        with self._lock:
            self.data["citations"]["sources"] = deepcopy(sources)

    def finish(
        self,
        *,
        status: str,
        answer_characters: int = 0,
        error: BaseException | None = None,
    ) -> None:
        with self._lock:
            if self._written:
                return
            self.data["generation"]["answer_characters"] = answer_characters
            self.data["outcome"]["status"] = status
            if error is not None:
                self.data["outcome"]["error_type"] = type(error).__name__
                self.data["outcome"]["error_message"] = str(error)
            payload = deepcopy(self.data)
            self._written = True

        output_file = _output_file()
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            with _WRITE_LOCK, output_file.open("a", encoding="utf-8") as handle:
                handle.write(serialized + "\n")
        except Exception:
            logger.exception("Failed to write RAG evaluation trace to %s", output_file)


def create_evaluation_trace(
    *,
    original_query: str,
    top_k: int,
    streaming: bool,
    reranker_model: str,
    candidate_multiplier: int,
    rrf_k: int,
) -> EvaluationTrace | None:
    if not settings.RAG_EVALUATION_ENABLED:
        return None
    return EvaluationTrace(
        original_query=original_query,
        top_k=top_k,
        streaming=streaming,
        reranker_model=reranker_model,
        candidate_multiplier=candidate_multiplier,
        rrf_k=rrf_k,
    )
