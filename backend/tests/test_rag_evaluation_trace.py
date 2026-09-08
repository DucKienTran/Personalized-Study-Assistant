import json

import pytest

from app.core.config import settings
from app.services.rag.evaluation_trace import create_evaluation_trace
from app.services.rag.rag_service import RAGService
from app.services.rag.retrieval_models import RetrievalResult
from app.services.rag.retrieval_service import (
    CANDIDATE_MULTIPLIER,
    RERANKER_MODEL,
    RRF_K,
    RetrievalService,
)


class FakeEmbeddingService:
    def generate_query_embedding(self, query: str):
        assert query == "alpha policy"
        return [0.1, 0.2]


class FakeCollection:
    chunks = [
        ("chunk-a", "alpha policy renewal", 1, 0.1),
        ("chunk-b", "alpha exception", 2, 0.2),
        ("chunk-c", "unrelated content", 3, 0.3),
    ]

    def query(self, **kwargs):
        assert kwargs["query_embeddings"] == [[0.1, 0.2]]
        return {
            "ids": [[chunk[0] for chunk in self.chunks]],
            "documents": [[chunk[1] for chunk in self.chunks]],
            "metadatas": [
                [
                    {
                        "document_id": chunk[2],
                        "page_start": 1,
                        "page_end": 1,
                    }
                    for chunk in self.chunks
                ]
            ],
            "distances": [[chunk[3] for chunk in self.chunks]],
        }

    def get(self, **kwargs):
        return {
            "ids": [chunk[0] for chunk in self.chunks],
            "documents": [chunk[1] for chunk in self.chunks],
            "metadatas": [
                {
                    "document_id": chunk[2],
                    "page_start": 1,
                    "page_end": 1,
                }
                for chunk in self.chunks
            ],
        }


class FakeRedis:
    async def get(self, key):
        return None

    async def set(self, key, value, ex=None):
        return True


class FakeRanker:
    def rerank(self, request):
        scores = {"chunk-a": 0.7, "chunk-b": 0.9, "chunk-c": 0.1}
        return sorted(
            ({"id": passage["id"], "score": scores[passage["id"]]} for passage in request.passages),
            key=lambda item: item["score"],
            reverse=True,
        )


class CapturingRanker:
    def __init__(self):
        self.passages = []

    def rerank(self, request):
        self.passages = request.passages
        return [{"id": passage["id"], "score": 1.0} for passage in request.passages]


def build_retrieval_service() -> RetrievalService:
    service = RetrievalService.__new__(RetrievalService)
    service.embedding_service = FakeEmbeddingService()
    service.redis = FakeRedis()
    service.chroma_collection = FakeCollection()
    service.ranker = FakeRanker()
    service._bm25_cache = {}
    return service


def build_trace():
    return create_evaluation_trace(
        original_query="alpha policy",
        top_k=2,
        streaming=True,
        reranker_model=RERANKER_MODEL,
        candidate_multiplier=CANDIDATE_MULTIPLIER,
        rrf_k=RRF_K,
    )


def test_reranker_passage_includes_header_path():
    service = build_retrieval_service()
    service.ranker = CapturingRanker()
    candidate = RetrievalResult(
        chunk_id="chunk-a",
        document_id=1,
        text="Renew within 30 days.",
        header_path=["ASTER ENTERPRISE - SERVICE POLICY 2026", "Renewal"],
    )

    assert service.rerank("renewal policy", [candidate], top_k=1) == [candidate]
    assert service.ranker.passages == [
        {
            "id": "chunk-a",
            "text": (
                "Section: ASTER ENTERPRISE - SERVICE POLICY 2026 > Renewal\n\n"
                "Renew within 30 days."
            ),
        }
    ]


@pytest.mark.asyncio
async def test_evaluation_tracing_does_not_change_retrieval_order(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RAG_EVALUATION_OUTPUT_DIR", str(tmp_path))

    monkeypatch.setattr(settings, "RAG_EVALUATION_ENABLED", False)
    without_trace = await build_retrieval_service().hybrid_search(
        query="alpha policy", user_id=9, document_ids=[1, 2, 3], top_k=2
    )

    monkeypatch.setattr(settings, "RAG_EVALUATION_ENABLED", True)
    trace = build_trace()
    assert trace is not None
    with_trace = await build_retrieval_service().hybrid_search(
        query="alpha policy",
        user_id=9,
        document_ids=[1, 2, 3],
        top_k=2,
        trace=trace,
    )

    assert [result.chunk_id for result in with_trace] == [
        result.chunk_id for result in without_trace
    ]
    assert [result.chunk_id for result in with_trace] == ["chunk-b", "chunk-a"]
    assert [item["chunk_id"] for item in trace.data["retrieval"]["vector_candidates"]] == [
        "chunk-a",
        "chunk-b",
        "chunk-c",
    ]
    assert trace.data["retrieval"]["reranker"]["fallback"] is False


def test_evaluation_trace_is_opt_in_and_writes_jsonl(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RAG_EVALUATION_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "RAG_EVALUATION_ENABLED", False)

    assert build_trace() is None
    assert not (tmp_path / "rag_traces.jsonl").exists()

    monkeypatch.setattr(settings, "RAG_EVALUATION_ENABLED", True)
    trace = build_trace()
    assert trace is not None
    trace.set_query_details(
        rewritten_query="alpha renewal policy",
        notebook_id=4,
        active_document_ids=[1, 2],
    )
    trace.finish(status="completed", answer_characters=42)

    output_file = tmp_path / "rag_traces.jsonl"
    records = [json.loads(line) for line in output_file.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["schema_version"] == "1.0"
    assert records[0]["query"]["active_document_ids"] == [1, 2]
    assert records[0]["configuration"]["chunk_size"] == 1000
    assert records[0]["configuration"]["candidate_counts"]["vector_requested"] == 8
    assert records[0]["outcome"]["status"] == "completed"


class FakeRow:
    def __init__(self, *, document_id=None, document_id_value=None, title=None):
        self.document_id = document_id
        self.id = document_id_value
        self.title = title


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self):
        self.query_count = 0

    def query(self, *columns):
        self.query_count += 1
        if self.query_count == 1:
            return FakeQuery([FakeRow(document_id=7)])
        return FakeQuery([FakeRow(document_id_value=7, title="Alpha Policy")])


class FakeHybridRetrieval:
    async def hybrid_search(self, *, trace=None, **kwargs):
        if trace:
            trace.set_retrieval_stage(
                "vector_candidates",
                [
                    {
                        "chunk_id": "chunk-7",
                        "document_id": 7,
                        "rank": 1,
                        "score": 0.91,
                        "distance": 0.09,
                    }
                ],
            )
            trace.set_retrieval_stage(
                "bm25_candidates",
                [
                    {
                        "chunk_id": "chunk-7",
                        "document_id": 7,
                        "rank": 1,
                        "score": 2.4,
                    }
                ],
            )
            trace.set_retrieval_stage(
                "rrf_candidates",
                [
                    {
                        "chunk_id": "chunk-7",
                        "document_id": 7,
                        "rank": 1,
                        "score": 0.032,
                        "vector_rank": 1,
                        "bm25_rank": 1,
                    }
                ],
            )
            trace.set_reranker(
                inputs=[{"chunk_id": "chunk-7", "document_id": 7, "input_rank": 1}],
                outputs=[
                    {
                        "chunk_id": "chunk-7",
                        "document_id": 7,
                        "input_rank": 1,
                        "output_rank": 1,
                        "score": 0.98,
                    }
                ],
                fallback=False,
            )
        return [
            RetrievalResult(
                chunk_id="chunk-7",
                document_id=7,
                text="The Alpha renewal period is 30 days.",
                rank=1,
                rerank_score=0.98,
                page_start=2,
                page_end=2,
            )
        ]


class FakeLLM:
    async def generate(self, prompt):
        return "unused"

    async def generate_stream(self, prompt):
        yield "The renewal period is "
        yield "30 days [1]."


@pytest.mark.asyncio
async def test_evaluation_mode_stream_smoke_records_context_and_citations(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RAG_EVALUATION_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "RAG_EVALUATION_ENABLED", True)
    service = RAGService(FakeHybridRetrieval(), FakeLLM())

    events = [
        event
        async for event in service.stream_answer_question(
            query="What is the Alpha renewal period?",
            user_id=3,
            sql_db=FakeDB(),
            notebook_id=11,
            top_k=1,
        )
    ]

    assert [event["type"] for event in events] == [
        "metadata",
        "token",
        "token",
        "citation_map",
        "sources",
        "done",
    ]
    record = json.loads((tmp_path / "rag_traces.jsonl").read_text(encoding="utf-8").strip())
    assert record["query"]["notebook_id"] == 11
    assert record["context"]["final_order"][0]["chunk_id"] == "chunk-7"
    assert record["citations"]["sources"] == [
        {"citation_index": 1, "chunk_id": "chunk-7", "document_id": 7}
    ]
    assert record["timings_ms"]["llm_ttft"] is not None
    assert record["timings_ms"]["llm_total"] is not None
    assert record["timings_ms"]["end_to_end_stream"] is not None
