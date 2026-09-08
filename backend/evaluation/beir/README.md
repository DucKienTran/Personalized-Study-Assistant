# BEIR Retrieval Evaluation

This adapter evaluates the production retrieval pipeline without answer generation. The initial
target is the BEIR SciFact `test` split.

## Representation And Isolation

Each BEIR corpus record is stored as one Chroma chunk because BEIR corpus records are already
retrieval passages. The raw BEIR text is not rewritten or PDF/Markdown parsed. Its title is used
as the production-style embedding header and as document-aware FlashRank context.

Every record stores its untouched `beir_corpus_id`. Chroma uses a dedicated collection named
`<production collection>__beir_<dataset>`. Benchmark BM25 state is request-local and never uses
production Redis.

## Prepare

Use an already downloaded standard BEIR directory:

```powershell
python -m evaluation.beir.prepare --dataset scifact --data-root C:\path\to\scifact
```

Or explicitly download SciFact and prepare it:

```powershell
python -m evaluation.beir.prepare --dataset scifact --download
```

Preparation calls the configured production Voyage document embedding model. A complete existing
collection and manifest are reused. Use `--force` only to deliberately rebuild the index.

## Run Later

```powershell
python -m evaluation.beir.run --dataset scifact --split test --experiment improved
```

The experiment label is metadata and output separation only. It does not alter retrieval behavior.
No generation LLM is constructed or called.

Results are written without overwriting prior runs:

```text
evaluation/beir/results/scifact/<experiment>_<UTC timestamp>.json
```

Each result contains reproducibility metadata, aggregate metrics, retrieval latency, and raw
per-query document rankings. If the official `beir` package is installed, its evaluator is used.
Otherwise the adapter uses compatible deterministic implementations of Recall, MRR, nDCG,
Precision, and MAP at the requested cutoffs.
