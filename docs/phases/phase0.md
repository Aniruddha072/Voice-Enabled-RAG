# Phase 0: Bootstrap

**Commit(s):** `5c21c8e` (chore: initialize project scaffold), `fdb974e` (feat(domain): define core domain entities and interfaces), `d93152c` (chore: add qdrant docker-compose and env config), `90e9def` (docs: add architecture, decisions, and roadmap docs)

## What we built

- Src-layout Python package `voicerag`, managed with uv, `uv.lock` committed for reproducible installs.
- `config.py`: a single `pydantic-settings` `Settings` class with the four fields Phase 0 needs.
- `domain/entities.py`: `Query`, `Transcript`, `Chunk`, `RetrievedPassage`, `Answer`, `EvalResult`.
- `domain/interfaces.py`: `SpeechToTextProvider`, `Embedder`, `VectorStore`, `LLMProvider`.
- `docker-compose.yml` bringing up Qdrant `v1.18.2` with a named volume.
- `.env.example` with every variable commented.
- `docs/architecture.md`, `docs/decisions.md`, `docs/roadmap.md`.

## What we learned

- Docker Desktop on this machine doesn't start its engine automatically; had to launch it and poll `docker info` before `docker compose up` would work. Worth remembering for anyone else running this project cold.
- `qdrant/qdrant:v1.18.2` was confirmed via web search rather than assumed, then verified it actually pulls and starts before committing the pin.

## Key design decisions

See `docs/decisions.md`, Decisions 0.1 through 0.5: package layout, uv over pip, deferring the Guardrail interface to Phase 4, self-hosted pinned Qdrant, and a single flat settings class.

## Challenges faced

None blocking. The only friction was Docker Desktop needing a manual start, which isn't a code problem.

## Reconciliation with the build plan (2026-08-21)

The build plan's own Phase 0 task list asked for more than what's above: the full dependency set (`qdrant-client`, `groq`, `tenacity`, `structlog`, an embeddings library, `ruff`) in `pyproject.toml` from the start, a `Guardrail` interface, and a `QDRANT_COLLECTION` setting name. Phase 0 as built stays narrower on all three, see Decision 0.6 for why. The plan (the artifact and `docs/roadmap.md`) was updated to match what was actually built rather than the other way around.

## Verification

```
$ uv sync --extra dev
Resolved 18 packages, installed 17

$ uv run python -c "from voicerag.config import settings; print(settings)"
environment='development' log_level='INFO' qdrant_url='http://localhost:6333' qdrant_collection_name='voicerag'

$ docker compose up -d
Container voice-enabledrag-qdrant-1 Started

$ curl -s http://localhost:6333/
{"title":"qdrant - vector search engine","version":"1.18.2", ...}
```
