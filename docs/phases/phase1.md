# Phase 1: Data Exploration + Chunking

**Commit(s):** `8d50bc2` (feat(chunking): implement chunking strategies and dataset ingestion)

## What we built

- `scripts/ingest_dataset.py`: downloads the Hindi validation parquet, samples 1,000 queries at a fixed seed, runs all three chunking strategies over every passage in both languages, writes the result to `data/processed/chunks_sample.jsonl` (gitignored, not committed).
- `application/chunking/passage_as_chunk.py`, `fixed_size.py`, `sentence_window.py`: the three strategies, plus a `STRATEGIES` dict in `chunking/__init__.py` so the ingest script doesn't need to know their names.
- `tests/unit/test_chunking.py`: 8 tests covering short-passage no-ops, long-passage splitting with overlap, and Hindi sentence boundaries specifically.

## What we learned

- The build plan's `load_dataset("ai4bharat/MSMARCO-XI", "hi", split="train")` doesn't work. The dataset repo ships a custom loading script that modern `datasets` versions won't execute, so only a generic `default` config is visible. The real structure is one parquet file per language under `train/` and `validation/`. See Decision 1.1.
- Real numbers from a 3,000-row sample of the validation split: 97,941 total rows, ~10 passages per query (min 4), 46% of queries have zero `is_selected` passages (no confidently relevant passage in that query's candidate set, this is expected MS MARCO behavior, not a data quality problem), English passages average 54 words, Hindi averages 62 words with one 4,092-word outlier.
- `hf-xet`, the fast-transfer backend `huggingface_hub` uses by default, hung indefinitely on this network partway through a 462MB download, twice, at the same byte offset both times. `HF_HUB_DISABLE_XET=1` fixed it immediately, plain HTTPS finished the same file in about 90 seconds. See Decision 1.3.
- Hindi sentences in this dataset consistently end with `।` (danda), not a period. Checked real `Answer` text before writing the sentence splitter rather than assuming.

## Key design decisions

See `docs/decisions.md`, Decisions 1.1 through 1.4: bypassing `datasets.load_dataset`, chunking parameters grounded in measured passage lengths, the `hf-xet` workaround, and the 1,000-query working sample.

## Challenges faced

Two real ones, both resolved: the dataset loading approach documented in the build plan doesn't work against the actual repo structure, and the `hf-xet` download hang. Neither was a code bug, both were caught by actually running things against the real dataset instead of assuming the plan's documented API call would work.

## Verification

```
$ uv run pytest tests/unit -v
8 passed

$ uv run python scripts/ingest_dataset.py --sample-size 1000 --seed 42
Loading 1000 sampled queries (seed=42) from ai4bharat/MSMARCO-XI...
Wrote chunks to data\processed\chunks_sample.jsonl
  en/fixed_size: 9995
  en/passage_as_chunk: 9975
  en/sentence_window: 15656
  hi/fixed_size: 10212
  hi/passage_as_chunk: 9975
  hi/sentence_window: 18904
```

Spot-checked a random sample of the output by hand: sentence windows group coherent sentences, fixed-size windows overlap correctly, Hindi text renders intact with no mangled characters.
