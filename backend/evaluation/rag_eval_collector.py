from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def load_manifest(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    by_question = {}
    for qid, item in data.items():
        by_question[item["question"].strip()] = (qid, item)
    return by_question


def first_relevant_rank(candidates, gold_chunks):
    gold = set(gold_chunks)
    for item in candidates:
        if item.get("chunk_id") in gold:
            return item.get("output_rank") or item.get("rank")
    return None


def compute_row(trace, qid, meta):
    retrieval = trace.get("retrieval", {})
    reranker = retrieval.get("reranker", {})
    final = reranker.get("output", [])
    gold_chunks = meta.get("gold_chunks", [])

    rank = first_relevant_rank(final, gold_chunks) if gold_chunks else None
    hit5 = (rank is not None and rank <= 5) if gold_chunks else None
    rr = (1.0 / rank) if rank else (0.0 if gold_chunks else None)

    citations = trace.get("citations", {}).get("sources", [])
    cited = [c.get("chunk_id") for c in citations if c.get("chunk_id")]

    t = trace.get("timings_ms", {})
    return {
        "qid": qid,
        "question": trace.get("query", {}).get("original", ""),
        "expected": meta.get("expected", ""),
        "gold_chunks": ",".join(gold_chunks),
        "retrieval_hit_at_5": "" if hit5 is None else ("PASS" if hit5 else "FAIL"),
        "first_relevant_rank": "" if rank is None else rank,
        "rr": "" if rr is None else round(rr, 4),
        "citation_chunks": ",".join(cited),
        "citation_hits_gold": "" if not gold_chunks else (
            "PASS" if any(c in set(gold_chunks) for c in cited) else "FAIL"
        ),
        "retrieval_latency_s": round((t.get("total_retrieval") or 0) / 1000, 3),
        "ttft_s": round((t.get("llm_ttft") or 0) / 1000, 3),
        "llm_total_s": round((t.get("llm_total") or 0) / 1000, 3),
        "e2e_s": round((t.get("end_to_end_stream") or 0) / 1000, 3),
        "trace_id": trace.get("trace_id", ""),
        "status": trace.get("outcome", {}).get("status", ""),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python rag_eval_collector.py <path-to-rag_traces.jsonl> [manifest.json] [output.csv]")
        sys.exit(1)

    trace_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path("rag_eval_manifest.json")
    output_path = Path(sys.argv[3]) if len(sys.argv) >= 4 else Path("rag_eval_results.csv")

    by_question = load_manifest(manifest_path)

    rows = []
    seen_trace_ids = set()
    if output_path.exists():
        with output_path.open("r", encoding="utf-8-sig", newline="") as f:
            for old in csv.DictReader(f):
                rows.append(old)
                if old.get("trace_id"):
                    seen_trace_ids.add(old["trace_id"])

    new_rows = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        trace = json.loads(line)
        trace_id = trace.get("trace_id")
        if trace_id in seen_trace_ids:
            continue

        question = trace.get("query", {}).get("original", "").strip()
        matched = by_question.get(question)
        if not matched:
            print(f"SKIP unknown question: {question}")
            continue

        qid, meta = matched
        row = compute_row(trace, qid, meta)
        rows.append(row)
        new_rows.append(row)
        seen_trace_ids.add(trace_id)

    fieldnames = [
        "qid", "question", "expected", "gold_chunks",
        "retrieval_hit_at_5", "first_relevant_rank", "rr",
        "citation_chunks", "citation_hits_gold",
        "retrieval_latency_s", "ttft_s", "llm_total_s", "e2e_s",
        "trace_id", "status",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    md_path = output_path.with_suffix(".md")
    with md_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(f"## {row['qid']}\n\n")
            f.write(f"**Question:** {row['question']}\n\n")
            f.write(f"**Expected:** {row['expected']}\n\n")
            f.write(f"- Retrieval Hit@5: {row['retrieval_hit_at_5'] or 'N/A'}\n")
            f.write(f"- First relevant rank: {row['first_relevant_rank'] or 'N/A'}\n")
            f.write(f"- RR: {row['rr'] if row['rr'] != '' else 'N/A'}\n")
            f.write(f"- Citation: {row['citation_chunks'] or 'None'}\n")
            f.write(f"- Citation hits gold: {row['citation_hits_gold'] or 'N/A'}\n")
            f.write(f"- Retrieval latency: {row['retrieval_latency_s']} s\n")
            f.write(f"- TTFT: {row['ttft_s']} s\n")
            f.write(f"- LLM total: {row['llm_total_s']} s\n")
            f.write(f"- E2E: {row['e2e_s']} s\n\n")

    print(f"Added {len(new_rows)} new result(s)")
    print(f"CSV: {output_path.resolve()}")
    print(f"Markdown: {md_path.resolve()}")


if __name__ == "__main__":
    main()
