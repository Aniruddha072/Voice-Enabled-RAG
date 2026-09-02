"""Runs the synthesized TTS batch through the full VoiceRAGPipeline
and records real per-stage latency for every query.

Uses the real, live providers (Sarvam, Groq, Qdrant, bge-m3), not
fakes, so this measures actual network latency, not mocked timings.
Consumes real Sarvam/Groq free-tier quota, see Decision 5.3.

Run: uv run python scripts/benchmark_latency.py
"""

import argparse
import asyncio
import json
import statistics
from pathlib import Path

from voicerag.application.guardrails import Guardrails
from voicerag.application.latency_tracker import LatencyTracker
from voicerag.application.pipeline import PipelineTimeoutError, VoiceRAGPipeline
from voicerag.config import settings
from voicerag.domain.interfaces import LLMError, SttError
from voicerag.infrastructure.embeddings.bge_m3_embedder import EMBEDDING_DIM, BgeM3Embedder
from voicerag.infrastructure.llm.groq_client import GroqLLMProvider
from voicerag.infrastructure.stt.sarvam_provider import SarvamSttProvider
from voicerag.infrastructure.vectorstore.qdrant_store import QdrantStore

STAGES = ("stt", "input_safety", "embed", "retrieve", "relevance", "generate", "groundedness")


def load_manifest(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def build_pipeline() -> VoiceRAGPipeline:
    return VoiceRAGPipeline(
        stt=SarvamSttProvider(),
        embedder=BgeM3Embedder(),
        vector_store=QdrantStore(settings.qdrant_url, settings.qdrant_collection_name, EMBEDDING_DIM),
        llm=GroqLLMProvider(),
        guardrails=Guardrails(),
    )


async def run_one(pipeline: VoiceRAGPipeline, record: dict) -> dict:
    tracker = LatencyTracker()
    result = {
        "query_id": record["query_id"],
        "language": record["language"],
        "correlation_id": tracker.correlation_id,
        "refused": None,
        "error": None,
    }
    try:
        answer = await pipeline.answer(record["audio_path"], tracker=tracker)
        result["refused"] = answer.refused
    except (SttError, LLMError, PipelineTimeoutError) as e:
        result["error"] = f"{type(e).__name__}: {e}"
    result["stages"] = {s.stage: round(s.duration_ms, 1) for s in tracker.stages}
    result["total_ms"] = round(tracker.total_ms, 1)
    return result


async def run_batch(pipeline: VoiceRAGPipeline, records: list[dict]) -> list[dict]:
    results = []
    for i, record in enumerate(records, start=1):
        result = await run_one(pipeline, record)
        status = f"ERROR: {result['error']}" if result["error"] else f"refused={result['refused']}"
        print(f"[{i}/{len(records)}] {record['language']} {record['query_id']}: {result['total_ms']}ms ({status})")
        results.append(result)
    return results


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * pct))
    return ordered[index]


def render_summary(results: list[dict]) -> str:
    lines = ["# Latency benchmark", ""]
    languages = ["en", "hi"]
    ok_results = [r for r in results if r["error"] is None]

    lines.append(f"{len(results)} queries run, {len(ok_results)} completed without a pipeline error.")
    errors = [r for r in results if r["error"] is not None]
    if errors:
        lines.append(f"{len(errors)} raised an error (see `latency_results.jsonl` for details).")
    refusals = [r for r in ok_results if r["refused"]]
    lines.append(f"{len(refusals)} of the completed queries were refused by a guardrail.")
    lines.append("")

    lines.append("## Per-stage latency (ms), all languages combined")
    lines.append("")
    lines.append("| Stage | Mean | P50 | P90 |")
    lines.append("|---|---|---|---|")
    for stage in STAGES:
        durations = [r["stages"][stage] for r in ok_results if stage in r["stages"]]
        if not durations:
            continue
        lines.append(
            f"| {stage} | {statistics.mean(durations):.1f} | {statistics.median(durations):.1f} | {_percentile(durations, 0.9):.1f} |"
        )
    total_durations = [r["total_ms"] for r in ok_results]
    if total_durations:
        lines.append(
            f"| **total** | {statistics.mean(total_durations):.1f} | {statistics.median(total_durations):.1f} | {_percentile(total_durations, 0.9):.1f} |"
        )
    lines.append("")

    lines.append("## Per-stage latency (ms), by language")
    lines.append("")
    lines.append("| Stage | EN Mean | EN P90 | HI Mean | HI P90 |")
    lines.append("|---|---|---|---|---|")
    for stage in (*STAGES, "total"):
        row = [stage]
        for language in languages:
            durations = [
                r["stages"][stage] if stage in STAGES else r["total_ms"]
                for r in ok_results
                if r["language"] == language and (stage in r["stages"] if stage in STAGES else True)
            ]
            if durations:
                row.append(f"{statistics.mean(durations):.1f}")
                row.append(f"{_percentile(durations, 0.9):.1f}")
            else:
                row.append("-")
                row.append("-")
        lines.append(f"| {' | '.join(row)} |")
    lines.append("")

    retrieve_durations = [r["stages"]["retrieve"] for r in ok_results if "retrieve" in r["stages"]]
    if retrieve_durations:
        retrieve_p90 = _percentile(retrieve_durations, 0.9)
        verdict = "yes" if retrieve_p90 < 200 else "no"
        lines.append(
            f"Retrieval latency sub-200ms at P90: **{verdict}** (mean {statistics.mean(retrieve_durations):.1f}ms, P90 {retrieve_p90:.1f}ms)."
        )
    lines.append("")

    return "\n".join(lines) + "\n"


async def main_async(args: argparse.Namespace) -> None:
    records = load_manifest(args.manifest)
    print(f"Loaded {len(records)} clips from {args.manifest}")

    pipeline = build_pipeline()
    results = await run_batch(pipeline, records)

    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    with args.raw_output.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"Wrote raw results to {args.raw_output}")

    summary = render_summary(results)
    args.summary_output.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Wrote summary to {args.summary_output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/eval/tts_manifest.jsonl"))
    parser.add_argument("--raw-output", type=Path, default=Path("docs/eval/latency_results.jsonl"))
    parser.add_argument("--summary-output", type=Path, default=Path("docs/eval/latency_benchmark.md"))
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
