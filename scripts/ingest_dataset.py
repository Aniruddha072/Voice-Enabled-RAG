"""Download, sample, chunk, embed, and index into Qdrant.

Downloads the Hindi validation split of ai4bharat/MSMARCO-XI (each row
already carries the English original alongside the Hindi translation,
see docs/decisions.md Decision 1.1), draws a fixed-seed sample of
queries, runs all three chunking strategies over every passage in both
languages, embeds every chunk with bge-m3, and upserts into a single
Qdrant collection filterable by language.

Default sample size is 200 queries, not the 1,000 used for Phase 1's
chunking-only exploration. On CPU, realistic varied-length text
embeds at roughly 1 chunk/sec, which would have made 200 queries
(~14,400 chunks) take about 4 hours. This machine has a usable CUDA
GPU, and embedding on it runs at roughly 54 chunks/sec instead, about
4.5 minutes for the same 200 queries. See docs/decisions.md Decisions
2.1 and 2.2.

Run: uv run python scripts/ingest_dataset.py
Chunking only, no embedding: add --skip-embed
"""

import argparse
import asyncio
import os
import time
from pathlib import Path

# The hf-xet fast-transfer backend hangs indefinitely on this machine's
# network partway through large files, reproduced twice. Plain HTTPS
# transfer works reliably, see docs/decisions.md Decision 1.3.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import pandas as pd
from huggingface_hub import hf_hub_download

from voicerag.application.chunking import STRATEGIES
from voicerag.config import settings
from voicerag.domain.entities import Chunk
from voicerag.infrastructure.embeddings.bge_m3_embedder import EMBEDDING_DIM, BgeM3Embedder
from voicerag.infrastructure.vectorstore.qdrant_store import QdrantStore

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


async def embed_and_index(chunks: list[Chunk], batch_size: int) -> None:
    embedder = BgeM3Embedder()
    store = QdrantStore(settings.qdrant_url, settings.qdrant_collection_name, EMBEDDING_DIM)
    await store.ensure_collection()

    total = len(chunks)
    start = time.time()
    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        vectors = await embedder.embed([c.text for c in batch])
        await store.upsert(batch, vectors)

        done = min(i + batch_size, total)
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        print(f"  indexed {done}/{total} ({rate:.1f} chunks/sec, ETA {eta/60:.1f} min)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/processed/chunks_sample.jsonl"))
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    print(f"Loading {args.sample_size} sampled queries (seed={args.seed}) from {REPO_ID}...")
    sample = load_sample(args.sample_size, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    all_chunks: list[Chunk] = []

    with args.output.open("w", encoding="utf-8") as f:
        for _, row in sample.iterrows():
            for chunk in chunk_row(row):
                f.write(chunk.model_dump_json() + "\n")
                all_chunks.append(chunk)
                key = f"{chunk.language}/{chunk.chunking_strategy}"
                counts[key] = counts.get(key, 0) + 1

    print(f"Wrote {len(all_chunks)} chunks to {args.output}")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")

    if args.skip_embed:
        return

    print(f"Embedding and indexing into Qdrant collection '{settings.qdrant_collection_name}'...")
    asyncio.run(embed_and_index(all_chunks, args.batch_size))
    print("Done.")


if __name__ == "__main__":
    main()
