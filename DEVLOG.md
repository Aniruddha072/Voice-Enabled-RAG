# Development Log

A running diary per session. Lighter than the phase docs under `docs/phases/`, which carry the detailed technical write-up for each phase. This is closer to "what happened, in what order, and what's left dangling."

## 2026-08-20: Repo setup and Phase 0

Started the project. Cloned the shape of `docs/`, README structure, and commit style from an earlier project, `ai-search-chatbot`, while keeping the actual scope and architecture from the build plan.

**Phases completed:** Phase 0 (see `docs/phases/phase0.md`)

**Commits:** `dd57ef7` through `90e9def`. Reproduce with `git log --oneline dd57ef7..90e9def`.

**Highlights worth remembering:**
- GitHub repo created as `Voice-Enabled-RAG` (hyphens), not `Voice-Enabled RAG` with a space, because GitHub repo names can't contain spaces. The local folder still has the space in its name; only the remote name differs.
- Deferred the `Guardrail` interface rather than guessing its shape before Phase 4 needs it. Worth checking back on this once guardrails.py actually gets written, in case it turns out the three checks do share enough shape to be worth one interface after all.
- Docker Desktop needed a manual start before `docker compose up` worked. Not a project problem, just a machine quirk to remember for next session.

**State at end of session:** Phase 0 fully verified and pushed. Phase 1 (data exploration and chunking against `ai4bharat/MSMARCO-XI`) is next.
