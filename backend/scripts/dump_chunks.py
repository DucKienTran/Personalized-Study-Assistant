import argparse
import json
from pathlib import Path

import chromadb


DEFAULT_CHROMA_PATH = "/app/chroma_data"


def dump_document_chunks(
    document_id: int,
    chroma_path: str = DEFAULT_CHROMA_PATH,
    output_path: str | None = None,
) -> int:
    print("=" * 70)
    print("CHROMA DOCUMENT CHUNK DUMP")
    print("=" * 70)
    print(f"Chroma path : {chroma_path}")
    print(f"Document ID : {document_id}")

    client = chromadb.PersistentClient(path=chroma_path)
    collections = client.list_collections()

    if not collections:
        print("No Chroma collections found.")
        return 1

    matched_chunks = []

    for collection_info in collections:
        collection_name = collection_info.name
        collection = client.get_collection(collection_name)

        try:
            result = collection.get(
                where={"document_id": document_id},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            print(f"[WARN] Could not query collection '{collection_name}': {exc}")
            continue

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        for idx, chunk_id in enumerate(ids):
            text = documents[idx] if idx < len(documents) else None
            metadata = metadatas[idx] if idx < len(metadatas) else {}

            matched_chunks.append(
                {
                    "collection": collection_name,
                    "chunk_id": chunk_id,
                    "document_id": metadata.get("document_id", document_id),
                    "text": text,
                    "metadata": metadata,
                }
            )

    if not matched_chunks:
        print(f"No chunks found for document_id={document_id}.")
        print("\nAvailable collections:")
        for collection_info in collections:
            try:
                collection = client.get_collection(collection_info.name)
                print(f"  - {collection_info.name}: {collection.count()} vectors")
            except Exception:
                print(f"  - {collection_info.name}")
        return 2

    def chunk_sort_key(item):
        chunk_id = str(item.get("chunk_id", ""))
        suffix = chunk_id.rsplit("_", 1)[-1]
        try:
            return (0, int(suffix))
        except ValueError:
            return (1, chunk_id)

    matched_chunks.sort(key=chunk_sort_key)

    if output_path is None:
        output_path = f"evaluation/document_{document_id}_chunks.json"

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "document_id": document_id,
        "chroma_path": chroma_path,
        "chunk_count": len(matched_chunks),
        "chunks": matched_chunks,
    }

    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nFound {len(matched_chunks)} chunk(s).")
    print(f"Saved to: {output.resolve()}")

    print("\nChunk summary:")
    for chunk in matched_chunks:
        text = (chunk.get("text") or "").replace("\n", " ").strip()
        preview = text[:140] + ("..." if len(text) > 140 else "")
        print(f"\n[{chunk['chunk_id']}]")
        print(f"Collection : {chunk['collection']}")
        print(f"Metadata   : {chunk['metadata']}")
        print(f"Preview    : {preview}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Dump all Chroma chunks belonging to a document_id."
    )
    parser.add_argument(
        "document_id",
        type=int,
        nargs="?",
        default=21,
        help="Document ID to inspect. Default: 21",
    )
    parser.add_argument(
        "--chroma-path",
        default=DEFAULT_CHROMA_PATH,
        help=f"Chroma persistent directory. Default: {DEFAULT_CHROMA_PATH}",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Default: evaluation/document_<id>_chunks.json",
    )

    args = parser.parse_args()

    raise SystemExit(
        dump_document_chunks(
            document_id=args.document_id,
            chroma_path=args.chroma_path,
            output_path=args.output,
        )
    )


if __name__ == "__main__":
    main()
