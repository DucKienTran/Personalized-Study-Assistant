import json

from app.services.rag.retrieval_models import RetrievalResult
from evaluation.beir.loader import BeirDataset
from evaluation.beir.metrics import evaluate_beir
from evaluation.beir.ranking import collapse_chunk_rankings


def test_beir_loader_reads_standard_layout(tmp_path):
    dataset_root = tmp_path / "tiny"
    (dataset_root / "qrels").mkdir(parents=True)
    (dataset_root / "corpus.jsonl").write_text(
        json.dumps({"_id": "doc-1", "title": "Title", "text": "Evidence"}) + "\n",
        encoding="utf-8",
    )
    (dataset_root / "queries.jsonl").write_text(
        json.dumps({"_id": "query-1", "text": "Claim"}) + "\n",
        encoding="utf-8",
    )
    (dataset_root / "qrels" / "test.tsv").write_text(
        "query-id\tcorpus-id\tscore\nquery-1\tdoc-1\t1\n",
        encoding="utf-8",
    )

    dataset = BeirDataset(dataset_root)
    assert dataset.load_corpus()[0].corpus_id == "doc-1"
    assert dataset.load_queries()[0].text == "Claim"
    assert dataset.load_qrels() == {"query-1": {"doc-1": 1}}


def test_chunk_rankings_collapse_to_best_document_rank():
    chunks = [
        RetrievalResult(chunk_id="a-1", document_id=1, text="a", beir_corpus_id="a"),
        RetrievalResult(chunk_id="a-2", document_id=1, text="a2", beir_corpus_id="a"),
        RetrievalResult(chunk_id="b-1", document_id=2, text="b", beir_corpus_id="b"),
    ]

    assert collapse_chunk_rankings(chunks) == {"a": 2.0, "b": 1.0}


def test_local_metric_contract_for_perfect_ranking(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "beir", None)
    metrics, backend = evaluate_beir(
        {"q1": {"d1": 1}},
        {"q1": {"d1": 2.0, "d2": 1.0}},
    )

    assert backend == "local-compatible"
    assert metrics["Recall@5"] == 1.0
    assert metrics["Recall@10"] == 1.0
    assert metrics["MRR@10"] == 1.0
    assert metrics["nDCG@10"] == 1.0
