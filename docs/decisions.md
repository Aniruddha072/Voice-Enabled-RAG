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

