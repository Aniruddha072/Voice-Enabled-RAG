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
