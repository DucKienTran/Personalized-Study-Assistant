from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
from typing import Any
import requests

def sse_events(resp):
    event = None
    data_lines = []
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        line = raw.rstrip("\r")
        if line == "":
            if event is not None:
                payload = "\n".join(data_lines)
                try:
                    payload = json.loads(payload)
                except Exception:
                    pass
                yield event, payload
            event, data_lines = None, []
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())

def auth_headers():
    headers = {"Accept":"text/event-stream","Content-Type":"application/json"}
    token = os.getenv("RAG_EVAL_BEARER_TOKEN")
    cookie = os.getenv("RAG_EVAL_COOKIE")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if cookie:
        headers["Cookie"] = cookie
    return headers

def run_query(session, url, notebook_id, question, top_k=8, conversation_id=None, chat_history=None, timeout=180):
    payload = {
        "query": question,
        "notebook_id": notebook_id,
        "top_k": top_k,
        "chat_history": chat_history or None,
        "conversation_id": conversation_id,
    }
    started = time.perf_counter()
    with session.post(url, headers=auth_headers(), json=payload, stream=True, timeout=timeout) as resp:
        status = resp.status_code
        if status >= 400:
            text = resp.text
            return {"status":"http_error","http_status":status,"error":text,"question":question}
        answer_parts, sources, metadata = [], [], None
        conv_id = conversation_id
        first_token_s = None
        events = []
        for ev, data in sse_events(resp):
            events.append(ev)
            if ev == "conversation_id" and isinstance(data, dict):
                conv_id = data.get("id")
            elif ev == "token":
                if first_token_s is None:
                    first_token_s = time.perf_counter() - started
                if isinstance(data, str):
                    answer_parts.append(data)
            elif ev == "sources" and isinstance(data, list):
                sources = data
            elif ev == "metadata":
                metadata = data
        elapsed = time.perf_counter() - started
    return {
        "status":"completed","http_status":status,"question":question,
        "conversation_id":conv_id,"answer":"".join(answer_parts),
        "sources":sources,"metadata":metadata,"runner_ttft_s":first_token_s,
        "runner_e2e_s":elapsed,"events":events
    }

def append_jsonl(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(record,ensure_ascii=False)+"\n")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",default="dataset_2_manifest.json")
    ap.add_argument("--api-base",default=os.getenv("RAG_EVAL_API_BASE","http://localhost:8000"))
    ap.add_argument("--notebook-id",type=int,required=True)
    ap.add_argument("--top-k",type=int,default=5)
    ap.add_argument("--output",default="output/answers.jsonl")
    ap.add_argument("--only",default=None,help="Comma-separated question ids")
    ap.add_argument("--include-followups",action="store_true")
    args=ap.parse_args()
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    url=args.api_base.rstrip("/")+"/api/rag/stream"
    selected=set(x.strip() for x in args.only.split(",")) if args.only else None
    out=Path(args.output)
    session=requests.Session()

    for q in manifest["questions"]:
        if selected and q["id"] not in selected: continue
        print(f"[RUN] {q['id']} {q['question']}")
        result=run_query(session,url,args.notebook_id,q["question"],args.top_k)
        record={"dataset_id":manifest["dataset_id"],"question_id":q["id"],
                "question_type":q["type"],"expected":q["expected"],
                "required_documents":q.get("required_documents",[]),
                "required_facts":q.get("required_facts",[]),
                "forbidden_facts":q.get("forbidden_facts",[]),**result}
        append_jsonl(out,record)
        print(f"  -> {result['status']} e2e={result.get('runner_e2e_s')}")

    if args.include_followups:
        for seq in manifest.get("followup_sequences",[]):
            print(f"[FOLLOWUP] {seq['sequence_id']}")
            conv_id=None
            history=[]
            for turn in seq["turns"]:
                result=run_query(session,url,args.notebook_id,turn["question"],args.top_k,conv_id,history)
                conv_id=result.get("conversation_id")
                record={"dataset_id":manifest["dataset_id"],"sequence_id":seq["sequence_id"],
                        "question_id":turn["id"],"expected":turn["expected"],**result}
                append_jsonl(out,record)
                if result.get("status")=="completed":
                    history.append({"role":"user","content":turn["question"]})
                    history.append({"role":"ai","content":result.get("answer","")})
                    history=history[-8:]
                print(f"  {turn['id']} -> {result['status']}")

if __name__=="__main__":
    main()
