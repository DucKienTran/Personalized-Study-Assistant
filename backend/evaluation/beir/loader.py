from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BeirCorpusRecord:
    corpus_id: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class BeirQuery:
    query_id: str
    text: str


class BeirDataset:
    def __init__(self, root: Path | str, split: str = "test") -> None:
        self.root = Path(root)
        self.split = split

    def validate(self) -> None:
        required = [
            self.root / "corpus.jsonl",
            self.root / "queries.jsonl",
            self.root / "qrels" / f"{self.split}.tsv",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing BEIR dataset files: {', '.join(missing)}")

    def load_corpus(self) -> list[BeirCorpusRecord]:
        self.validate()
        records = []
        with (self.root / "corpus.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                records.append(
                    BeirCorpusRecord(
                        corpus_id=str(item["_id"]),
                        title=str(item.get("title") or ""),
                        text=str(item.get("text") or ""),
                    )
                )
        return records

    def load_queries(self) -> list[BeirQuery]:
        self.validate()
        queries = []
        with (self.root / "queries.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                queries.append(BeirQuery(query_id=str(item["_id"]), text=str(item["text"])))
        return queries

    def load_qrels(self) -> dict[str, dict[str, int]]:
        self.validate()
        qrels: dict[str, dict[str, int]] = {}
        with (self.root / "qrels" / f"{self.split}.tsv").open(encoding="utf-8") as handle:
            header = next(handle, None)
            if header is None:
                return qrels
            for line in handle:
                query_id, corpus_id, score = line.rstrip("\n").split("\t")[:3]
                qrels.setdefault(str(query_id), {})[str(corpus_id)] = int(score)
        return qrels
