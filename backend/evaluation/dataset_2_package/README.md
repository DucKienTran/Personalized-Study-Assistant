# Dataset 2 — Aster Confusion / Multi-document / Distractor

## Mục tiêu
Dataset 2 tăng độ khó so với Orion baseline bằng:
- version conflict 2025/2026;
- customer-specific contract override;
- entity gần giống: Enterprise / Lite / Enterprise Plus;
- semantic distractor / incident exception / marketing wording;
- multi-document 2–3 nguồn;
- threshold reasoning;
- hard no-answer;
- cross-language;
- follow-up 3 lượt.

## Chạy
1. Upload toàn bộ file trong `documents/` vào cùng một notebook và chờ completed.
2. Bật evaluation tracing ở backend.
3. Cung cấp auth:
   - Bearer: `$env:RAG_EVAL_BEARER_TOKEN="..."`, hoặc
   - Cookie: `$env:RAG_EVAL_COOKIE="name=value; ..."`
4. Chạy:

```powershell
python rag_eval_runner.py --notebook-id <ID> --include-followups
```

Nếu API không ở `http://localhost:8000`:

```powershell
python rag_eval_runner.py --notebook-id <ID> --api-base http://localhost:<PORT> --include-followups
```

5. Tổng hợp raw output:

```powershell
python rag_eval_collector.py --answers output/answers.jsonl --trace ../output/rag_traces.jsonl
```

## Lưu ý
Runner giữ cùng `conversation_id` và history tối đa 8 messages cho follow-up, tương ứng behavior FE.
Các câu độc lập không truyền conversation_id nên endpoint tạo conversation mới.
Sau ingestion cần dump chunks/document IDs và resolve gold evidence → chunk IDs trước khi tính Recall@5/MRR chính thức.
