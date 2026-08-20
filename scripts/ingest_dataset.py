"""Phase 1 ingestion: download, sample, and chunk. No embedding yet.

Downloads the Hindi validation split of ai4bharat/MSMARCO-XI (each row
already carries the English original alongside the Hindi translation,
see docs/decisions.md Decision 1.1), draws a fixed-seed sample of
queries, and runs all three chunking strategies over every passage in
both languages. Output is a JSON-lines file of Chunk records, one line
per chunk, for the embedding step in Phase 2 to consume.

Run: uv run python scripts/ingest_dataset.py
"""

import argparse
import os
from pathlib import Path

# The hf-xet fast-transfer backend hangs indefinitely on this machine's
# network partway through large files, reproduced twice. Plain HTTPS
# transfer works reliably, see docs/decisions.md Decision 1.3.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import pandas as pd
from huggingface_hub import hf_hub_download

from voicerag.application.chunking import STRATEGIES
from voicerag.domain.entities import Chunk

REPO_ID = "ai4bharat/MSMARCO-XI"
PARQUET_FILE = "validation/hinval.parquet"


def load_sample(sample_size: int, seed: int) -> pd.DataFrame:
    path = hf_hub_download(repo_id=REPO_ID, repo_type="dataset", filename=PARQUET_FILE)
    df = pd.read_parquet(path)
    return df.sample(n=sample_size, random_state=seed)


def chunk_row(row) -> list[Chunk]:
    query_id = str(row["query_id"])
    passages = row["passages"]
    chunks: list[Chunk] = []

    for i in range(len(passages["English_passages"])):
        is_selected = bool(passages["is_selected"][i])
        texts = {
            "en": passages["English_passages"][i],
            "hi": passages["Translated_passages"][i],
        }
        for language, text in texts.items():
            if not text or not text.strip():
                continue
            for strategy_name, chunk_fn in STRATEGIES.items():
                for j, chunk_text in enumerate(chunk_fn(text)):
                    chunks.append(
                        Chunk(
                            id=f"{query_id}_{language}_{strategy_name}_{i}_{j}",
                            text=chunk_text,
                            language=language,
                            source_query_id=query_id,
                            is_selected=is_selected,
                            chunking_strategy=strategy_name,
                        )
                    )
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/processed/chunks_sample.jsonl"))
    args = parser.parse_args()

    print(f"Loading {args.sample_size} sampled queries (seed={args.seed}) from {REPO_ID}...")
    sample = load_sample(args.sample_size, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    with args.output.open("w", encoding="utf-8") as f:
        for _, row in sample.iterrows():
            for chunk in chunk_row(row):
                f.write(chunk.model_dump_json() + "\n")
                key = f"{chunk.language}/{chunk.chunking_strategy}"
                counts[key] = counts.get(key, 0) + 1

    print(f"Wrote chunks to {args.output}")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")


if __name__ == "__main__":
    main()
