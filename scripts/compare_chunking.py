"""Compares the three chunking strategies head-to-head: recall@K and
MRR per strategy, per language, against the golden eval set.

Query embeddings are computed once per query and reused across all
three strategies, the query vector doesn't depend on chunking
strategy, only which chunks get searched does.

Run: uv run python scripts/compare_chunking.py
"""

import argparse
import asyncio
import json
from pathlib import Path

from voicerag.application.chunking import STRATEGIES
from voicerag.config import settings
from voicerag.infrastructure.embeddings.bge_m3_embedder import EMBEDDING_DIM, BgeM3Embedder
from voicerag.infrastructure.vectorstore.qdrant_store import QdrantStore

LANGUAGES = ("en", "hi")


def load_golden_set(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


async def embed_queries(golden_set: list[dict], embedder: BgeM3Embedder) -> dict[tuple[str, str], list[float]]:
    vectors = {}
    for record in golden_set:
        key = (record["query_id"], record["language"])
        vectors[key] = (await embedder.embed([record["query_text"]]))[0]
    return vectors


async def evaluate(
    golden_set: list[dict], vectors: dict[tuple[str, str], list[float]], store: QdrantStore, limit: int
) -> dict[tuple[str, str], dict]:
    results = {}
    for strategy in STRATEGIES:
        for language in LANGUAGES:
            queries = [r for r in golden_set if r["language"] == language]
            hits = 0
            reciprocal_ranks = []
            for record in queries:
                vector = vectors[(record["query_id"], record["language"])]
                passages = await store.search(vector, language=language, limit=limit, chunking_strategy=strategy)
                rank = next(
                    (
                        i
                        for i, p in enumerate(passages, start=1)
                        if p.chunk.source_query_id == record["query_id"] and p.chunk.is_selected
                    ),
                    None,
                )
                if rank is not None:
                    hits += 1
                    reciprocal_ranks.append(1 / rank)
                else:
                    reciprocal_ranks.append(0.0)
            results[(strategy, language)] = {
                "n": len(queries),
                "recall_at_k": hits / len(queries) if queries else 0.0,
                "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
            }
    return results


def render_report(results: dict[tuple[str, str], dict], limit: int, golden_set_path: Path) -> str:
    lines = [
        "# Chunking strategy comparison",
        "",
        f"recall@{limit} and MRR per strategy, per language, against the golden eval set (`{golden_set_path}`).",
        "",
        f"| Strategy | Language | N | Recall@{limit} | MRR |",
        "|---|---|---|---|---|",
    ]
    for (strategy, language), metrics in sorted(results.items()):
        lines.append(f"| {strategy} | {language} | {metrics['n']} | {metrics['recall_at_k']:.3f} | {metrics['mrr']:.3f} |")
    return "\n".join(lines) + "\n"


async def main_async(args: argparse.Namespace) -> None:
    golden_set = load_golden_set(args.golden_set)
    embedder = BgeM3Embedder()
    store = QdrantStore(settings.qdrant_url, settings.qdrant_collection_name, EMBEDDING_DIM)

    print(f"Embedding {len(golden_set)} golden-set queries...")
    vectors = await embed_queries(golden_set, embedder)

    print("Evaluating each strategy...")
    results = await evaluate(golden_set, vectors, store, args.limit)

    report = render_report(results, args.limit, args.golden_set)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-set", type=Path, default=Path("data/eval/golden_set.jsonl"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("docs/eval/chunking_comparison.md"))
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
