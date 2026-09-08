from app.services.rag.retrieval_models import RetrievalResult


def collapse_chunk_rankings(chunks: list[RetrievalResult]) -> dict[str, float]:
    corpus_order = []
    seen = set()
    for chunk in chunks:
        corpus_id = chunk.beir_corpus_id
        if corpus_id is None or corpus_id in seen:
            continue
        seen.add(corpus_id)
        corpus_order.append(corpus_id)
    return {
        corpus_id: float(len(corpus_order) - rank)
        for rank, corpus_id in enumerate(corpus_order)
    }
