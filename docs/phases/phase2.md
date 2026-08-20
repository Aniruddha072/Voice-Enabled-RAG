# Phase 2: Embeddings + Vector Indexing

**Commit(s):** `6107abc` (feat(retrieval): implement bge-m3 embedder and qdrant vector store)

## What we built

- `infrastructure/embeddings/bge_m3_embedder.py`: wraps `sentence-transformers`' bge-m3 dense embeddings, auto-detects CUDA, capped at 512 tokens / batch size 32 after a real OOM crash (see below).
- `infrastructure/vectorstore/qdrant_store.py`: creates the `voicerag` collection (1,024-dim, cosine), batched upsert with deterministic UUID5 point IDs, language-filtered search.
- `scripts/ingest_dataset.py` extended to embed and index every chunk it produces, not just write them to a file.
- `pyproject.toml` gained `[tool.uv.sources]`/`[[tool.uv.index]]` entries pointing `torch` at the CUDA 13.0 wheel index on Windows, so a fresh `uv sync` gets the GPU build automatically.

## What we learned

- The first throughput benchmark (50 identical short sentences, 6.5/sec) was misleading. Real, varied-length text on the same CPU ran at roughly 1/sec, confirmed by two independent clean tests. Identical inputs are not a representative benchmark for a transformer forward pass.
- This machine has a real NVIDIA RTX 4050 (6GB VRAM) sitting unused, because `sentence-transformers`' default install pulls in CPU-only PyTorch on Windows unless a CUDA-specific package index is configured. Switching to it turned a projected 4-6 hour CPU run into under 5 minutes.
- GPU memory is a hard limit CPU memory mostly isn't: a batch size that's merely slow on CPU can hard-crash on a 6GB GPU. The crash came from an unbounded outlier passage forcing an entire batch to pad to its length. Full writeup and fix in GitHub issue #1.
- Retrieval sanity-checking needs a query that's actually answerable from what's indexed. An arbitrary test phrase not covered by the 200-query sample returned mediocre results and briefly looked like a retrieval quality problem; testing against a query pulled from the actual sample, with a known ground-truth passage, confirmed retrieval works correctly (the ground-truth passage came back as the top hit in both languages).

## Key design decisions

See `docs/decisions.md`, Decisions 2.1 through 2.3: the 200-query embedding sample size, the CUDA switch and the OOM fix, and the Qdrant collection/point-ID scheme.

## Challenges faced

One real crash (CUDA OOM at batch size 128), root-caused and fixed, tracked in GitHub issue #1. Otherwise straightforward once the throughput numbers were understood.

## Verification

```
$ uv run python scripts/ingest_dataset.py --sample-size 200 --seed 42
Wrote 14429 chunks to data\processed\chunks_sample.jsonl
...
  indexed 14429/14429 (54.0 chunks/sec, ETA 0.0 min)
Done.

$ curl -s http://localhost:6333/collections/voicerag
points_count: 14429

# query: "how are landforms typically formed" (lang=en)
#   score=0.730 strategy=fixed_size selected=True qid=1099705
#     Landforms are defined as the natural physical features found on the surface of the earth...

# query: "भूमि-आकृतियाँ आमतौर पर कैसे बनती हैं?" (lang=hi)
#   score=0.765 strategy=fixed_size selected=True qid=1099705
#     भू-आकृतियों को पृथ्वी की सतह पर पाए जाने वाली प्राकृतिक भौतिक विशेषताओं...
```

Both languages correctly return the known ground-truth passage for the same underlying query as the top-scored result, filtered to the right language.
