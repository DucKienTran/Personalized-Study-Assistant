from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

import chromadb

from app.core.config import settings
from app.services.document.embedding_service import EmbeddingService
from evaluation.beir.common import BEIR_DATA_ROOT, collection_name, git_commit, manifest_path
from evaluation.beir.loader import BeirCorpusRecord, BeirDataset

DATASET_URLS = {
    "scifact": "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip",
}


def _download_dataset(dataset: str, data_root: Path) -> Path:
    url = DATASET_URLS.get(dataset)
    if url is None:
        raise ValueError(f"No download URL configured for BEIR dataset '{dataset}'")
    data_root.mkdir(parents=True, exist_ok=True)
    archive = data_root / f"{dataset}.zip"
    urllib.request.urlretrieve(url, archive)
    with zipfile.ZipFile(archive) as bundle:
        root = data_root.resolve()
        for member in bundle.infolist():
            destination = (data_root / member.filename).resolve()
            if root not in destination.parents and destination != root:
                raise ValueError(f"Unsafe archive path: {member.filename}")
        bundle.extractall(data_root)
    archive.unlink()
    return data_root / dataset


def _chunk_id(dataset: str, corpus_id: str) -> str:
    digest = hashlib.sha256(corpus_id.encode("utf-8")).hexdigest()[:24]
    return f"beir_{dataset}_{digest}"


def _embedding_text(record: BeirCorpusRecord) -> str:
    if record.title:
        return f"Context: {record.title}\n\n{record.text}"
    return record.text


def prepare_index(
    *,
    dataset: str,
    dataset_root: Path,
    chroma_path: Path,
    batch_size: int,
    force: bool,
) -> dict:
    corpus = BeirDataset(dataset_root).load_corpus()
    client = chromadb.PersistentClient(path=str(chroma_path))
    name = collection_name(dataset)

    try:
        existing = client.get_collection(name)
    except Exception:
        existing = None

    manifest_file = manifest_path(dataset)
    if existing is not None and not force:
        if manifest_file.is_file() and existing.count() == len(corpus):
            return json.loads(manifest_file.read_text(encoding="utf-8"))
        raise RuntimeError(
            f"Benchmark collection '{name}' already exists but is incomplete or incompatible; "
            "rerun with --force to rebuild it."
        )
    if existing is not None:
        client.delete_collection(name)

    collection = client.create_collection(
        name=name,
        metadata={"benchmark": "BEIR", "dataset": dataset},
    )
    embedding_service = EmbeddingService()
    for start in range(0, len(corpus), batch_size):
        batch = corpus[start : start + batch_size]
        embeddings = embedding_service.client.embed_documents(
            [_embedding_text(record) for record in batch]
        )
        collection.add(
            ids=[_chunk_id(dataset, record.corpus_id) for record in batch],
            documents=[record.text for record in batch],
            embeddings=embeddings,
            metadatas=[
                {
                    "document_id": start + offset + 1,
                    "beir_corpus_id": record.corpus_id,
                    "document_title": record.title,
                    "page_start": 0,
                    "page_end": 0,
                }
                for offset, record in enumerate(batch)
            ],
        )

    manifest = {
        "benchmark": "BEIR",
        "dataset": dataset,
        "collection": name,
        "corpus_count": len(corpus),
        "embedding_model": settings.VOYAGE_MODEL,
        "chroma_path": str(chroma_path.resolve()),
        "prepared_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
        "representation": "one BEIR corpus record per Chroma chunk",
    }
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare an isolated BEIR Chroma index")
    parser.add_argument("--dataset", default="scifact")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--chroma-path", type=Path, default=Path(settings.CHROMA_PERSIST_DIR))
    parser.add_argument("--batch-size", type=int, default=settings.VOYAGE_EMBEDDING_BATCH_SIZE)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    dataset_root = args.data_root or BEIR_DATA_ROOT / args.dataset
    if not dataset_root.exists() and args.download:
        dataset_root = _download_dataset(args.dataset, BEIR_DATA_ROOT)
    if not dataset_root.exists():
        raise FileNotFoundError(
            f"BEIR dataset not found at {dataset_root}. Pass --download or --data-root."
        )

    manifest = prepare_index(
        dataset=args.dataset,
        dataset_root=dataset_root,
        chroma_path=args.chroma_path,
        batch_size=args.batch_size,
        force=args.force,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
