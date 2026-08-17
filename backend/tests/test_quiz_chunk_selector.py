import pytest

from app.services.quiz.chunk_selector import QuizChunkSelector


class FakeEmbeddingService:
    def __init__(self):
        self.queries = []

    def generate_query_embedding(self, query: str):
        self.queries.append(query)
        return [0.25] * 1024


class FakeCollection:
    def __init__(self):
        self.query_kwargs = None
        self.get_kwargs = None

    def query(self, **kwargs):
        self.query_kwargs = kwargs
        return {
            "ids": [["chunk-1"]],
            "documents": [["Fourier transforms decompose signals into frequency components."]],
            "metadatas": [[{"document_id": 7, "document_title": "Signals"}]],
        }

    def get(self, **kwargs):
        self.get_kwargs = kwargs
        return {
            "ids": ["chunk-2"],
            "documents": ["Uniform sampling covers learning material across the source document."],
            "metadatas": [{"document_id": 7, "document_title": "Signals"}],
        }


class FakeChromaClient:
    def __init__(self, collection):
        self.collection = collection

    def get_or_create_collection(self, *, name: str):
        assert name == "document_chunks"
        return self.collection


@pytest.mark.asyncio
async def test_semantic_retrieval_uses_configured_query_embedding():
    collection = FakeCollection()
    embedding_service = FakeEmbeddingService()
    selector = QuizChunkSelector(
        chroma_client=FakeChromaClient(collection),
        collection_name="document_chunks",
        embedding_service=embedding_service,
    )

    chunks = await selector.select(
        document_ids=[7],
        total_questions=10,
        coverage=8.0,
        query="Fourier transform algorithms",
    )

    assert embedding_service.queries == ["Fourier transform algorithms"]
    assert collection.query_kwargs["query_embeddings"] == [[0.25] * 1024]
    assert "query_texts" not in collection.query_kwargs
    assert collection.query_kwargs["where"] == {"document_id": 7}
    assert [chunk.chunk_id for chunk in chunks] == ["chunk-1"]


@pytest.mark.asyncio
async def test_retrieval_without_query_keeps_coverage_fallback():
    collection = FakeCollection()
    embedding_service = FakeEmbeddingService()
    selector = QuizChunkSelector(
        chroma_client=FakeChromaClient(collection),
        collection_name="document_chunks",
        embedding_service=embedding_service,
    )

    chunks = await selector.select(
        document_ids=[7],
        total_questions=10,
        coverage=8.0,
        query=None,
    )

    assert embedding_service.queries == []
    assert collection.query_kwargs is None
    assert collection.get_kwargs == {"where": {"document_id": 7}}
    assert [chunk.chunk_id for chunk in chunks] == ["chunk-2"]
