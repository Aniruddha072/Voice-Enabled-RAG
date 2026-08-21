# Roadmap & Task Checklist

See [architecture.md](architecture.md) for the system design and [decisions.md](decisions.md) for why specific choices were made. Each phase is meant to be testable on its own before the next one starts.

## Phase 0: Bootstrap

Goal: a running skeleton, no pipeline logic yet.

- [x] Create the repo root, initialize git, add `.gitignore`
- [x] `pyproject.toml` with Phase 0 dependencies (`pydantic`, `pydantic-settings`, `python-dotenv`). Everything else (`qdrant-client`, `groq`, `tenacity`, `structlog`, embeddings library, `ruff`) gets added in the phase that needs it, see Decision 0.6.
- [x] `src/voicerag/` package skeleton: `domain/`, `application/`, `infrastructure/`, `presentation/`, each with `__init__.py`
- [x] `domain/entities.py`: `Query`, `Transcript`, `Chunk`, `RetrievedPassage`, `Answer`, `EvalResult`
- [x] `domain/interfaces.py`: `SpeechToTextProvider`, `Embedder`, `VectorStore`, `LLMProvider`. `Guardrail` deferred to Phase 4, see Decision 0.3.
- [x] `config.py`: `environment`, `log_level`, `qdrant_url`, `qdrant_collection_name`. Provider API keys get added when the phase that uses them arrives.
- [x] `docker-compose.yml` for Qdrant, pinned version, named volume
- [x] `.env.example`, every variable commented
- [x] Starter `README.md`
- [x] Verified: `docker compose up -d` brings up Qdrant and it responds on `:6333`
- [x] Verified: `uv run python -c "from voicerag.config import settings; print(settings)"` works
- [x] Initial commits, conventional style

## Phase 1: Data Exploration + Chunking

Goal: the Hindi config of `ai4bharat/MSMARCO-XI` loaded, both `English_passages` and `Translated_passages` extracted, chunked three ways.

- [x] Pull the Hindi split. Not via `datasets.load_dataset("hi")`, that config doesn't exist, see Decision 1.1. Downloaded `validation/hinval.parquet` directly instead.
- [x] Explore the schema hands-on: 97,941 rows, ~10 passages per query, ~46% of queries have zero `is_selected` passages, passage length averages 54 words (EN) / 62 words (HI), see Decision 1.2 and `docs/phases/phase1.md` for the full numbers
- [x] Pick a manageable working sample size: 1,000 queries, fixed seed, from the validation split rather than train, see Decision 1.4
- [x] `domain/entities.py`'s `Chunk` fields, unchanged from Phase 0, verified against real data
- [x] `chunking/fixed_size.py`: fixed-size window, configurable overlap
- [x] `chunking/sentence_window.py`: sentence split (including the Hindi danda `।`), overlapping N-sentence windows
- [x] `chunking/passage_as_chunk.py`: passage-as-chunk baseline
- [x] Unit tests for each chunker against fixture passages in both languages
- [x] `scripts/ingest_dataset.py`, chunking pass only: load sample, run all three chunkers, write chunks with metadata to `data/processed/chunks_sample.jsonl`
- [x] Spot-check a sample of chunks per strategy per language by hand: windows reasonable, Hindi text intact
- [x] Commit

## Phase 2: Embeddings + Vector Indexing

Goal: chunks embedded and searchable, both languages in one collection.

- [x] `infrastructure/embeddings/bge_m3_embedder.py`: load once, batch-embed, CUDA when available (see Decision 2.2)
- [x] Decide and document the Qdrant collection schema: 1,024-dim, cosine distance, UUID5 point IDs, see Decision 2.3
- [x] `infrastructure/vectorstore/qdrant_store.py`: create collection, batched upsert, filtered search
- [x] Finish `ingest_dataset.py`: embed every chunk, upsert into Qdrant. 200-query sample, ~14,429 chunks, see Decision 2.1
- [x] Run full ingestion on the working sample, confirm point count matches expected chunk count: 14,429 = 14,429
- [x] Manually query a known Hindi phrase filtered to `language="hi"`, confirm sensible results: known-correct passage returned as top hit, score 0.765
- [x] Manually query a known English phrase filtered to `language="en"`, confirm sensible results: known-correct passage returned as top hit, score 0.730
- [x] Commit. Also hit and fixed a real CUDA OOM crash along the way, see issue #1 and Decision 2.2

## Phase 3: Voice Input

Goal: real speech in either language becomes a text query.

- [x] Sarvam account, API key, confirm free credits active
- [x] `infrastructure/stt/sarvam_provider.py` implementing `SpeechToTextProvider`
- [x] `infrastructure/stt/whisper_local_provider.py` (`faster-whisper`), same interface, CPU-only, see Decision 3.1
- [x] Record ~10-15 real Hindi voice clips asking questions from the dataset (13 recorded)
- [x] Record ~10-15 real English voice clips asking questions from the dataset (12 recorded)
- [x] Run both providers against every clip, informally compare transcript quality per language: Sarvam correct/near-perfect on all 25, whisper never clean on a single Hindi clip, see Decision 3.1 and issue #3
- [x] Handle empty transcript, low-confidence result, network/timeout error: both providers normalize to a clean empty string instead of crashing on `None`, `Transcript.confidence` carries language-detection confidence, and provider-specific network/API exceptions get wrapped in one domain-level `SttError`, see Decision 3.2
- [x] Decide the default-provider vs. fallback-trigger condition: Sarvam default for both languages, whisper-local last-resort fallback only, see Decision 3.1
- [x] Commit

## Phase 4: Grounded Generation + Guardrails

Goal: full pipeline produces a cited, guardrailed answer in the question's own language.

- [ ] Groq API key in `.env`
- [ ] `infrastructure/llm/groq_client.py`: configurable model/temperature
- [ ] Grounded system prompt: cite the source passage, answer in the question's language, refuse when context is insufficient
- [ ] `application/guardrails.py`, and decide then whether the three checks share enough shape for a `Guardrail` interface, see Decision 0.3:
  - [ ] Off-topic / relevance-threshold check against top retrieval score
  - [ ] Unsafe-input pre-check via a short Groq classification call
  - [ ] Groundedness post-check, lexical-overlap heuristic first
  - [ ] Groundedness post-check, Groq judge call, only if the heuristic isn't enough
- [ ] `application/pipeline.py`: `VoiceRAGPipeline` wiring STT, input guardrail, embed, retrieve, relevance guardrail, generate, groundedness guardrail
- [ ] Manual test: Hindi question, verify grounded Hindi answer with citation
- [ ] Manual test: English question, verify grounded English answer with citation
- [ ] Manual test: off-topic/unanswerable question, verify graceful refusal
- [ ] Commit

## Phase 5: Harness + Latency Benchmarking

Goal: proof, not just a demo.

- [ ] Fix issue #2 first (`chunk_fixed_size`/`chunk_sentence_window` hang forever if `overlap >= window`) before passing any custom window/overlap values during the chunking-strategy comparison below

- [ ] `application/latency_tracker.py`: per-stage timer, correlation ID
- [ ] Wire the tracker into every pipeline stage
- [ ] `tenacity` retry/backoff on the STT and LLM calls
- [ ] Timeout budget per stage
- [ ] Structured logging, one line per stage per query, tagged with correlation ID
- [ ] Golden eval set from `is_selected == 1` rows, both languages, spot-checked by hand
- [ ] `scripts/compare_chunking.py`: recall@5 and MRR per strategy, per language
- [ ] Synthesize test audio (free local TTS) from 50-100 queries per language
- [ ] `scripts/benchmark_latency.py`: run the synthesized batch through the full pipeline
- [ ] Save raw results and a summary report to `docs/eval/`
- [ ] Confirm retrieval latency is sub-200ms, note honestly where any stage isn't
- [ ] Commit

## Phase 6: Polish, Demo, README

Goal: something worth showing in an interview.

- [ ] `presentation/cli.py`: interactive voice-in loop, prints transcript, answer, citation, latency
- [ ] `presentation/streamlit_app.py`, if time allows
- [ ] Final README: overview, architecture diagram, real per-language numbers from `docs/eval/`, setup, tech-stack rationale, free-tier cost breakdown
- [ ] `docs/decisions.md` updated with any late calls
- [ ] Demo recording that switches languages mid-demo
- [ ] Verify zero-dollar spend against the Sarvam and Groq usage dashboards
- [ ] Tag a release

## Stretch (optional, does not block calling the project done)

- [ ] Sparse/BM25 vectors alongside dense vectors, fused with Reciprocal Rank Fusion
- [ ] A light cross-encoder reranker over the fused top-K
- [ ] Cross-lingual retrieval experiment: does a Hindi question retrieve relevant English passages, and vice versa
