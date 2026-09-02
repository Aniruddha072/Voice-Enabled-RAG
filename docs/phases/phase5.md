# Phase 5: Harness + Latency Benchmarking

**Commit(s):** `a3f321b` (fix(chunking): raise ValueError when overlap >= window), `979d644` (feat(latency): implement per-stage timer and correlation ID), `1761114` (feat(pipeline): wire latency tracker into every stage), `3a646d0` (chore: add tenacity dependency), `0a49a1e` (feat(stt): retry Sarvam transcription with exponential backoff), `71ea51e` (feat(llm): retry Groq generation with exponential backoff), `7e6f7f1` (feat(pipeline): add per-stage timeout budgets), `44d68eb` (chore: add structlog dependency), `5a123c7` (feat(logging): configure structlog for pretty/JSON output), `6a5b233` (feat(pipeline): log one structured line per stage per query), `d958450` (feat(eval): build the golden eval set), `db4c806` (feat(eval): compare chunking strategies against the golden eval set), `436e063` (feat(pipeline): retrieve only passage_as_chunk chunks), `e29d13a` (docs: sync roadmap checkboxes with Phase 5 progress), `25855ed` (chore: add piper-tts dependency), `16d858b` (feat(eval): synthesize test audio with Piper TTS).

## What we built

- `application/latency_tracker.py`: `LatencyTracker`, a correlation ID plus a per-stage timer, wired into every stage of `VoiceRAGPipeline.answer()`.
- `tenacity` retry/backoff on the two real network calls that matter most, Sarvam transcription and Groq generation, 3 attempts with exponential backoff, deliberately not applied to local whisper or the guardrail Groq calls.
- Per-stage timeout budgets (`asyncio.wait_for`, `PipelineTimeoutError` naming the stage) and structured logging (`structlog`, one line per stage per query, correlation ID, pretty console in development / JSON otherwise).
- Fixed issue #2 first: `chunk_fixed_size`/`chunk_sentence_window` hung forever when `overlap >= window`, via TDD.
- `scripts/build_golden_eval.py`: 101 EN + 101 HI queries with a real ground-truth passage, drawn from the same 200-query indexed sample.
- `scripts/compare_chunking.py`: recall@5 and MRR for all three chunking strategies, per language, against the golden set.
- Pipeline retrieval filtered to the winning strategy, `passage_as_chunk`, resolving Decision 5.1's open question.
- `scripts/synthesize_test_audio.py`: 100 EN + 100 HI clips synthesized locally and for free with Piper TTS.
- `scripts/benchmark_latency.py`: all 200 clips run through the real, live `VoiceRAGPipeline`, raw per-query results and a summary report saved to `docs/eval/`.

## What we learned

- This dataset's chunking strategy barely matters on retrieval quality (`passage_as_chunk` and `fixed_size` tied), but `sentence_window` loses uniformly, not on some query subset, so a multi-granularity hybrid wasn't worth building, there's no complementary signal to fuse.
- Structured per-stage logging and a latency tracker earn their keep the moment you run something at real volume: this benchmark's own `generate` stage numbers would have been unreadable noise without per-stage timing to isolate where the slowdown actually was.
- Running 200 real queries back-to-back with no throttling is enough to hit Sarvam's and Groq's free-tier rate limits. The pipeline's own retry/backoff absorbed almost all of it silently (a rate-limited call just shows up as one slow stage), but not always, one Sarvam call exhausted its retries and failed cleanly. Re-running the slowest queries in isolation right after the batch confirmed this was transient load, not a regression.
- A synthesized-audio benchmark measures something real but narrower than it looks: TTS mispronouncing an uncommon proper noun, and Sarvam then transcribing that mispronunciation, shifts a query's embedding enough to trigger a false guardrail refusal that would likely not happen on real human speech. Spot-checking actual transcripts against the original query text was the only way to tell that apart from Decision 4.2's already-known relevance-threshold blind spot, both turned out to be real and both contribute to this benchmark's refusal rate.

## Key design decisions

See `docs/decisions.md`, Decision 5.1 (chunking-strategy comparison), Decision 5.2 (filtering retrieval to `passage_as_chunk`), Decision 5.3 (synthesizing test audio with Piper TTS), and Decision 5.4 (the full latency benchmark, its rate-limit artifact, and its refusal-rate spot check).

## Challenges faced

- Issue #2, filed and fixed via TDD before starting the rest of Phase 5, see the commit history (`a3f321b`).
- The `generate` stage's inflated latency in the full 200-query run looked like a regression at first. Root-caused instead of assumed: re-ran the 3 slowest queries' `generate` call in isolation immediately after the batch, all completed in 1.2-2.2s (matching the earlier smoke test), and the one real failure carried an explicit Sarvam `429 rate_limit_exceeded_error` in its error message. Not filed as a GitHub issue, the code behaved correctly under a real external constraint.
- The 24% guardrail refusal rate on a golden set that's supposed to always have a ground-truth passage. Traced with a targeted spot check (re-transcribing 6 refused clips) rather than guessed at: partly TTS/STT round-trip drift on uncommon words, partly the same relevance-threshold limitation Decision 4.2 already documented and accepted.

## Verification

```
Chunking comparison (docs/eval/chunking_comparison.md):
| Strategy         | Language | N   | Recall@5 | MRR   |
| fixed_size       | en       | 101 | 0.950    | 0.614 |
| fixed_size       | hi       | 101 | 0.871    | 0.539 |
| passage_as_chunk | en       | 101 | 0.950    | 0.614 |
| passage_as_chunk | hi       | 101 | 0.871    | 0.537 |
| sentence_window  | en       | 101 | 0.941    | 0.589 |
| sentence_window  | hi       | 101 | 0.822    | 0.530 |

Latency benchmark (docs/eval/latency_benchmark.md), 200 real queries:
  retrieve: 26.1ms mean / 31.9ms P90 -- sub-200ms, confirmed
  199/200 completed without a pipeline error
  47/199 refused by a guardrail (see Decision 5.4 for why)
```
