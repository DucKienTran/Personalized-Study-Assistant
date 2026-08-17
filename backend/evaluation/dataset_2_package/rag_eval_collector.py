from __future__ import annotations
import argparse, csv, json, statistics
from pathlib import Path

def pct(x): return round(x*100,2)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--answers",default="output/answers.jsonl")
    ap.add_argument("--trace",default="../output/rag_traces.jsonl")
    ap.add_argument("--out",default="output/dataset_2_results.csv")
    args=ap.parse_args()

    answers=[json.loads(x) for x in Path(args.answers).read_text(encoding="utf-8").splitlines() if x.strip()]
    traces=[]
    tp=Path(args.trace)
    if tp.exists():
        traces=[json.loads(x) for x in tp.read_text(encoding="utf-8").splitlines() if x.strip()]

    trace_by_question={}
    for t in traces:
        q=(t.get("query") or {}).get("original")
        if q: trace_by_question.setdefault(q,[]).append(t)

    rows=[]
    for a in answers:
        q=a["question"]
        ts=trace_by_question.get(q,[])
        t=ts[-1] if ts else {}
        rer=((t.get("retrieval") or {}).get("reranker") or {}).get("output") or []
        citations=(t.get("citations") or {}).get("sources") or []
        rows.append({
            "question_id":a.get("question_id"),
            "question_type":a.get("question_type","followup"),
            "status":a.get("status"),
            "answer_chars":len(a.get("answer","")),
            "citation_count":len(citations),
            "retrieval_latency_s":round(((t.get("timings_ms") or {}).get("total_retrieval") or 0)/1000,3) if t else "",
            "ttft_s":round(((t.get("timings_ms") or {}).get("llm_ttft") or 0)/1000,3) if t else a.get("runner_ttft_s",""),
            "e2e_s":round(((t.get("timings_ms") or {}).get("end_to_end_stream") or 0)/1000,3) if t else a.get("runner_e2e_s",""),
            "top_chunk":rer[0]["chunk_id"] if rer else "",
            "answer":a.get("answer","")
        })

    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    md=out.with_suffix(".md")
    lat=[r["retrieval_latency_s"] for r in rows if isinstance(r["retrieval_latency_s"],float)]
    e2e=[r["e2e_s"] for r in rows if isinstance(r["e2e_s"],float)]
    with md.open("w",encoding="utf-8") as f:
        f.write("# Dataset 2 — Raw Run Summary\n\n")
        f.write(f"- Runs: {len(rows)}\n")
        if lat: f.write(f"- Retrieval median: {statistics.median(lat):.3f}s\n")
        if e2e: f.write(f"- E2E median: {statistics.median(e2e):.3f}s\n")
        f.write("\n> Retrieval quality metrics require resolving uploaded document IDs/chunk IDs to the manifest evidence after ingestion.\n\n")
        for r in rows:
            f.write(f"## {r['question_id']}\n\n")
            f.write(f"- Type: {r['question_type']}\n- Status: {r['status']}\n- Citations: {r['citation_count']}\n")
            f.write(f"- Retrieval: {r['retrieval_latency_s']} s\n- TTFT: {r['ttft_s']} s\n- E2E: {r['e2e_s']} s\n\n")
            f.write("**Answer**\n\n"+r["answer"]+"\n\n")
    print(out.resolve()); print(md.resolve())

if __name__=="__main__":
    main()
