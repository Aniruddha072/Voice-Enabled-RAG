"""Builds the golden eval set: queries from the indexed 200-query
sample that have a real is_selected passage, in both languages.

Uses the same sample (seed 42, size 200) as scripts/ingest_dataset.py
so the golden set only references queries actually indexed in Qdrant.
Roughly half of queries have an is_selected passage per Decision 1.2,
so the golden set ends up smaller than the full 200-query sample.

Doesn't store a specific ground-truth chunk ID. Every chunk derived
from a passage inherits that passage's is_selected flag (see
ingest_dataset.py), so recall/MRR at eval time just checks whether a
retrieved chunk has the matching query_id and is_selected=True,
regardless of chunking strategy.

Run: uv run python scripts/build_golden_eval.py
"""

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import pandas as pd
from huggingface_hub import hf_hub_download

REPO_ID = "ai4bharat/MSMARCO-XI"
PARQUET_FILE = "validation/hinval.parquet"


def load_sample(sample_size: int, seed: int) -> pd.DataFrame:
    path = hf_hub_download(repo_id=REPO_ID, repo_type="dataset", filename=PARQUET_FILE)
    df = pd.read_parquet(path)
    return df.sample(n=sample_size, random_state=seed)


def golden_rows(row):
    passages = row["passages"]
    query_id = str(row["query_id"])
    if not any(bool(s) for s in passages["is_selected"]):
        return

    eng_query = row["Eng_Query"].strip().lstrip(".").strip()
    hi_query = row["query"]
    if eng_query:
        yield {"query_id": query_id, "language": "en", "query_text": eng_query}
    if hi_query:
        yield {"query_id": query_id, "language": "hi", "query_text": hi_query}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/eval/golden_set.jsonl"))
    args = parser.parse_args()

    print(f"Loading {args.sample_size} sampled queries (seed={args.seed}) from {REPO_ID}...")
    sample = load_sample(args.sample_size, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts = {"en": 0, "hi": 0}
    with args.output.open("w", encoding="utf-8") as f:
        for _, row in sample.iterrows():
            for record in golden_rows(row):
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[record["language"]] += 1

    print(f"Wrote golden eval set to {args.output}")
    for lang, count in counts.items():
        print(f"  {lang}: {count} queries with a real ground-truth passage")


if __name__ == "__main__":
    main()
