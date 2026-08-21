# Design Decisions & Tradeoffs

Numbered, dated, and never rewritten after the fact. If a later decision changes course, it gets a new number that says so; the old entry stays as a record of what was actually done at the time.

### Decision 0.1

Date: 2026-08-20

Implemented:
Package name is `voicerag`, laid out under `src/voicerag/` (src layout, not a flat package at repo root).

Reason:
- Matches the build plan's own folder structure diagram, so nothing needs renaming later.
- Src layout means `import voicerag` only works against the installed package, not an accidental relative import from the repo root. Catches packaging mistakes early instead of at deploy time.

### Decision 0.2

Date: 2026-08-20

Implemented:
Dependency management via uv (`pyproject.toml` + committed `uv.lock`), not plain pip.

Reason:
- uv was already installed and resolves and installs the full dev environment in under two seconds.
- A committed lockfile means the exact dependency set is reproducible on a clean machine, which matters for a project meant to be shown to someone else.
- This is a deliberate departure from `ai-search-chatbot`, which uses plain pip. That project predates uv being the obvious default; there's no reason to carry the older tooling forward here.

### Decision 0.3

Date: 2026-08-20

Implemented:
`domain/interfaces.py` defines `SpeechToTextProvider`, `Embedder`, `VectorStore`, and `LLMProvider`. It does not define a `Guardrail` interface yet, even though the build plan's folder diagram lists one.

Reason:
- The three planned guardrail checks (relevance threshold, unsafe-input, groundedness) don't obviously share a method signature. One takes a similarity score, one takes raw text, one takes an answer plus its context.
- `guardrails.py` isn't built until Phase 4. Writing an abstract interface now would mean guessing its shape before any of the three checks exist, which is exactly the kind of speculative design this project is trying to avoid.
- Guardrail logic is also pure Python with no external SDK behind it, unlike the other four interfaces, so it may not need a provider-swapping abstraction at all. That gets decided in Phase 4, not now.

### Decision 0.4

Date: 2026-08-20

Implemented:
Qdrant runs self-hosted via Docker Compose, pinned to `qdrant/qdrant:v1.18.2`, with a single named volume for storage.

Reason:
- Self-hosted Qdrant is free with no usage ceiling, which matters under the project's $0 hard rule. A managed free tier would still risk a quota surprise later.
- Pinned to a specific tag rather than `latest` so a `docker compose up` next month pulls the same image as one run today. Confirmed the tag exists and pulls successfully before committing to it.

### Decision 0.5

Date: 2026-08-20

Implemented:
Configuration is one flat `Settings` class in `config.py`, built on `pydantic-settings`, loaded from `.env`.

Reason:
- Matches the pattern already proven in `ai-search-chatbot`: one place to look for every setting, with validation and clear startup errors for free from pydantic.
- Phase 0 only needs four fields (`environment`, `log_level`, `qdrant_url`, `qdrant_collection_name`). Settings for Sarvam, Groq, and the other providers get added to this same class as the phases that need them arrive, not stubbed in ahead of time.

### Decision 0.6

Date: 2026-08-21

Implemented:
Phase 0 was scoped narrower than the build plan's literal Phase 0 task list in three places, and the code stays as-is rather than being expanded to match the task list word for word.

Reason:
- The task list asked for `qdrant-client`, `sentence-transformers`, `groq`, `tenacity`, `structlog`, `ruff`, and `mypy` in `pyproject.toml` from day one. None of that code exists yet, so none of those dependencies are installed yet either. They get added in the phase that actually writes code against them. `ai-search-chatbot` was built the same way, its dependencies were added commit by commit, not declared all at once.
- The task list also asked for a `Guardrail` interface in `domain/interfaces.py`. Still deferred, per Decision 0.3.
- The task list named the Qdrant collection setting `QDRANT_COLLECTION`. The actual field is `qdrant_collection_name`, picked before this task list surfaced and more descriptive. No reason to rename it just to match.
- This is the project's own ground rule talking: "core loop before hardening." A task list written in one sitting before any code existed is a plan, not a spec, and the plan itself says not to build ahead of need.

### Decision 1.1

Date: 2026-08-21

Implemented:
Dataset loading bypasses `datasets.load_dataset` entirely. The ingestion script pulls the parquet file directly with `huggingface_hub.hf_hub_download` and reads it with `pandas`.

Reason:
- Tried the build plan's documented call, `load_dataset("ai4bharat/MSMARCO-XI", "hi", split="train")`. It fails: `BuilderConfig 'hi' not found. Available: ['default']`.
- Checked the repo directly with `HfApi().dataset_info(...)`. It ships a custom loading script, `ms_marco_translations.py`, and one parquet file per language under `train/` and `validation/` (`hintrain.parquet`, `hinval.parquet`, and so on), not per-language configs. Modern `datasets` versions no longer execute repo-provided loading scripts, so `load_dataset` only sees the generic `default` config and can't reach the language split logic the script defines.
- Since we're bypassing `load_dataset` anyway, there's no reason to depend on the `datasets` package at all. Dropped it in favor of `huggingface_hub` + `pandas` + `pyarrow` directly, see Decision 0.6's spirit: depend on what the code actually calls.

### Decision 1.2

Date: 2026-08-21

Implemented:
Chunking strategies split on word count (`fixed_size`) and sentence boundaries (`sentence_window`), both including the Hindi danda (`।`) as a sentence terminator alongside `. ! ?`.

Reason:
- Measured passage length on a 3,000-row sample of the real data: English passages average 54 words (median 49, p90 84), Hindi average 62 words (median 55, p90 92, with one 4,092-word outlier). Most passages sit well under the 150-word fixed-size window, confirming the build plan's expectation that fixed-size chunking is close to a no-op here, useful mainly for the long tail.
- Checked real Hindi `Answer` text directly rather than assuming punctuation: it consistently ends sentences with `।`, not a period. A sentence splitter that only matched `.!?` would silently treat entire Hindi passages as one sentence.

### Decision 1.3

Date: 2026-08-21

Implemented:
`scripts/ingest_dataset.py` sets `HF_HUB_DISABLE_XET=1` before importing `huggingface_hub`, forcing plain HTTPS transfer instead of the `hf-xet` fast-transfer backend.

Reason:
- `hf-xet` hung indefinitely on this machine partway through the 462MB validation file, reproduced twice (stalled at the same ~67MB point both times, then a third attempt sat at 0 bytes for 5+ minutes). Disabling it and retrying with classic HTTP transfer completed the same download in about 90 seconds at a steady ~5MB/s.
- Setting the flag in code rather than just this session's shell means the next person (or the next machine) to run ingestion doesn't hit the same silent hang.

### Decision 1.4

Date: 2026-08-21

Implemented:
The working sample for Phase 1 is 1,000 queries drawn (fixed seed 42) from the Hindi **validation** split of `ai4bharat/MSMARCO-XI`, not the train split, and not the full validation split.

Reason:
- Checked file sizes before downloading anything: each language's train parquet is roughly 3.7-4.0GB, validation is roughly 460-495MB. The full validation split alone is 97,941 queries, already far more than a personal project needs to index (this is the "10M+ rows, don't try to ingest all of it" the build plan warns about, just one order of magnitude smaller).
- 1,000 queries produces about 75,000 chunks total across all three strategies and both languages, see `docs/phases/phase1.md` for the exact counts. That's a size worth embedding and indexing without a long wait, and easy to re-sample larger if Phase 2's actual embedding throughput turns out faster than expected. The final embedding-scale sample size gets decided empirically in Phase 2, not guessed now.

### Decision 2.1

Date: 2026-08-21

Implemented:
The embedding/indexing sample is 200 queries (fixed seed 42), not the 1,000 queries used for Phase 1's chunking exploration. That's about 14,429 chunks across all three strategies and both languages.

Reason:
- Decision 1.4 deliberately deferred this number to be measured, not guessed. First real measurement, 50 identical short sentences embedded on CPU at 6.5/sec, turned out to be a bad benchmark: real, varied-length passage text embeds at roughly 1/sec on CPU, confirmed twice independently. At that rate, 1,000 queries (~75,000 chunks) would take over 3 hours and 200 queries alone would take about 4 hours.
- After switching to GPU (Decision 2.2), 200 queries takes under 5 minutes. 200 was picked before the GPU switch as a CPU-tractable size and kept afterward since it still comfortably covers Phase 5's eval needs: about 54% of queries have a ground-truth passage, so 200 queries yields roughly 108 with one, in the same range as the build plan's own suggested 50-100 test queries per language.
- Can be raised later with a single flag (`--sample-size`) now that indexing is fast; no reason to do that until a phase actually needs more data than this provides.

### Decision 2.2

Date: 2026-08-21

Implemented:
Embedding uses CUDA when available (`torch==2.13.0+cu130`) rather than the CPU-only PyTorch build that `sentence-transformers` pulls in by default. `BgeM3Embedder` auto-detects the device. Batch size is 32 and `max_seq_length` is capped at 512 tokens.

Reason:
- Measured CPU throughput on realistic text at roughly 1 chunk/sec (see Decision 2.1). This machine has an NVIDIA RTX 4050 laptop GPU (6GB VRAM) with working drivers, confirmed via `nvidia-smi`, sitting unused because the default `pip`/`uv` install of `torch` on Windows is CPU-only unless a CUDA-specific index is requested.
- Configured via `[tool.uv.sources]` pointing `torch` at `https://download.pytorch.org/whl/cu130` for `sys_platform == 'win32'`, rather than a one-off manual `pip install`, so `uv sync` on a fresh checkout gets the GPU build automatically instead of silently falling back to CPU.
- First attempt at batch size 128 crashed with `CUDA out of memory` partway through the real 200-query run (see issue #1 for the full trace and fix). Root cause: bge-m3's default sequence length is up to 8,192 tokens, so an unbounded outlier passage in the same batch as normal-length chunks forces the whole batch to pad to that outlier's length, and a few such batches exhausted 6GB of VRAM. Capped `max_seq_length` at 512 (this dataset's passages average 54-62 words, see Decision 1.2, so 512 tokens is generous headroom, not a real truncation risk) and dropped batch size to 32. Fixed run sustained about 54 chunks/sec with no further OOM across all 14,429 chunks, a roughly 50x speedup over CPU.

### Decision 2.3

Date: 2026-08-21

Implemented:
One Qdrant collection (`voicerag`), 1,024-dim vectors, cosine distance. Point IDs are a UUID5 hash of the chunk's own string ID (`uuid.uuid5(NAMESPACE, chunk.id)`), not the chunk ID itself.

Reason:
- Qdrant requires point IDs to be an unsigned integer or a UUID. This project's chunk IDs are descriptive strings (`"1099705_hi_sentence_window_3_3"`), useful for debugging and traceability, so they're kept in the payload rather than given up to satisfy Qdrant's ID format.
- Hashing deterministically (not a random UUID) means re-running ingestion on the same chunk upserts the same point instead of creating a duplicate, so `ingest_dataset.py` can be re-run safely.
- 1,024 dimensions and cosine distance match bge-m3's dense output directly, no projection or normalization step needed beyond what `sentence-transformers` already does internally.

### Decision 3.1

Date: 2026-08-21

Implemented:
Sarvam Saaras v3 (`mode="transcribe"`) is the default speech-to-text provider for both languages. The local faster-whisper provider (`small`, CPU-only) is kept as a last-resort fallback for when Sarvam is unreachable or its free tier is exhausted, not treated as an equally good alternative.

Reason:
- Ran the same 25 real recorded clips (12 English, 13 Hindi, one mispronounced on purpose) through both providers. Sarvam came back correct or near-perfect on all 25, with only two minor phonetic misses on uncommon words. Whisper's `small` model never produced a fully clean transcript on a single Hindi clip, ranging from several word-level errors to badly garbled output, and on one English clip it misdetected the language entirely and returned Devanagari script instead of English. Full transcripts aren't kept in the repo since they're just test data, but the pattern held across every clip, not one or two.
- `mode="transcribe"` (Saaras's default) keeps the output in the spoken language instead of translating to English, which matters here since retrieval and generation are both language-filtered, translating Hindi speech to English text would break that chain.
- The fallback provider runs on CPU only. `ctranslate2` (faster-whisper's backend) needs its own system-level cuBLAS/cuDNN, separate from the CUDA libraries torch bundles for itself, and getting those onto the path on Windows isn't worth it for clips a few seconds long.
- `Transcript.stt_provider` already records which provider handled a given query, so when the fallback does fire, that should surface, not fail silently: in Phase 5's structured per-stage logging, and in Phase 6's CLI output, not as a mid-conversation confirmation prompt, since a voice-in pipeline shouldn't stop to ask permission before answering. Given whisper's specific weakness on Hindi, the CLI should say more than "fallback used" when it fires on a Hindi query, something closer to a plain-language accuracy warning. Not built yet, tracked as an enhancement for whoever writes `presentation/cli.py`, see issue #3.

### Decision 3.2

Date: 2026-08-21

Implemented:
Both STT providers normalize their output the same way and share one failure mode. `Transcript` gained a `confidence: float | None` field, populated from whatever language-detection confidence each provider already exposes (Sarvam's `language_probability`, whisper's `TranscriptionInfo.language_probability`). Network, timeout, and provider API errors get caught at the provider boundary and re-raised as one new exception, `SttError`, defined in `domain/interfaces.py` next to `SpeechToTextProvider`.

Reason:
- Without this, a caller further up the pipeline would need to know about `httpx.HTTPError`, `sarvamai`'s `ApiError` hierarchy, and whatever faster-whisper/ctranslate2 raises internally, three different vocabularies for the same kind of failure. One `SttError` keeps the port abstraction honest: swapping providers should never mean the caller needs new exception-handling code.
- `SttError` doesn't retry anything itself, it just gives failures a clean, catchable shape. Actual retry/backoff policy is explicitly Phase 5's job (`tenacity` on the STT and LLM calls), not duplicated here.
- Confidence is language-detection confidence, not a word-level accuracy score, neither provider's REST response exposes true per-word confidence. Documented as such directly on the field rather than implying more precision than it has. Nothing consumes this value yet; Phase 4's guardrails or Phase 6's CLI are the more natural place to decide what "low confidence" should actually do, so it's captured now and acted on later, matching Decision 0.3's approach to `Guardrail`.
- Empty transcripts (silence, unintelligible audio) aren't treated as an error, the provider succeeded, there was just nothing there. Both providers now guard against `None` and normalize with `.strip()`, so a caller always gets a real string it can safely check with `if not transcript.text`, instead of one provider risking `None` and the other returning untrimmed whitespace.

