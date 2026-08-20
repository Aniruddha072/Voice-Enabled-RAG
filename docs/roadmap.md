# Roadmap & Task Checklist

See [architecture.md](architecture.md) for the system design and [decisions.md](decisions.md) for why specific choices were made. Each phase is meant to be testable on its own before the next one starts.

## Phase 0 — Bootstrap

Goal: a running skeleton, no pipeline logic yet.

- [x] Repo structure (`domain/`, `application/`, `infrastructure/`, `presentation/`)
- [x] `docker-compose.yml` for Qdrant
- [x] `.env.example`
- [x] `pyproject.toml`, `uv.lock`
- [x] `config.py`
- [x] Verified: `docker compose up -d` brings up Qdrant and it responds on `:6333`
- [x] Verified: `uv run python -c "from voicerag.config import settings; print(settings)"` works

## Phase 1 — Data Exploration + Chunking

Goal: the `hi` config of `ai4bharat/MSMARCO-XI` loaded, both `English_passages` and `Translated_passages` extracted, chunked three ways.

- [ ] `scripts/ingest_dataset.py` (chunking only, no embedding yet)
- [ ] Fixed-size, sentence-window, and passage-as-chunk strategies implemented
- [ ] Unit tests against fixture passages in both languages
- [ ] Chunk output visually inspected per strategy, per language

## Phase 2 — Embeddings + Vector Indexing

Goal: chunks embedded and searchable, both languages in one collection.

- [ ] `bge_m3_embedder.py`
- [ ] `qdrant_store.py`
- [ ] `ingest_dataset.py` finished (embed + index all three strategies, language as a filterable payload field)
- [ ] A raw query for a known phrase in either language, filtered to that language, returns sensible passages

## Phase 3 — Voice Input

Goal: real speech in either language becomes a text query.

- [ ] `sarvam_provider.py`
- [ ] `whisper_local_provider.py`, same interface as Sarvam
- [ ] Real recorded test clips in Hindi and English
- [ ] Speaking a question into a mic produces a correct(ish) transcript from both providers

## Phase 4 — Grounded Generation + Guardrails

Goal: full pipeline produces a cited, guardrailed answer in the question's own language.

- [ ] `groq_client.py`
- [ ] `guardrails.py` (relevance threshold, unsafe-input, groundedness)
- [ ] `pipeline.py` wiring every stage together
- [ ] End-to-end: speak a question, get a grounded answer with a citation, or a graceful refusal on low retrieval confidence

## Phase 5 — Harness + Latency Benchmarking

Goal: proof, not just a demo.

- [ ] `latency_tracker.py`
- [ ] `benchmark_latency.py`
- [ ] `compare_chunking.py`
- [ ] `docs/eval/` reports, broken out per language
- [ ] Real P50/P70/P100 numbers per stage, recall@k per chunking strategy per language, groundedness rate per language

## Phase 6 — Polish, Demo, README

Goal: something worth showing in an interview.

- [ ] `cli.py`
- [ ] `streamlit_app.py`, if time allows
- [ ] README updated with real bilingual numbers from Phase 5
- [ ] Demo recording that switches languages mid-demo

## Stretch (optional, does not block calling the project done)

- [ ] Hybrid retrieval (vector + Qdrant sparse/BM25)
- [ ] Light cross-encoder reranker
- [ ] Cross-lingual retrieval experiment: does a Hindi question retrieve relevant English passages, and vice versa, since bge-m3 embeds both into the same space
