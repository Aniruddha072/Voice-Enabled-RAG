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

## 2026-08-21: Build plan update, gitignore cleanup, commit hygiene

The build plan got a real revision: every phase now carries a granular task checklist instead of just goal/deliverables/outcome. Republished it as an editable artifact instead of the original read-only one, so it can be kept in sync going forward instead of drifting.

Reconciled Phase 0 against the updated plan's task list. Three things the task list asked for that Phase 0 doesn't have: the full dependency set up front, a `Guardrail` interface, and a `QDRANT_COLLECTION` setting name. Decided to keep Phase 0 as built and update the plan to match, see Decision 0.6. `docs/roadmap.md` now carries the same granular tasks per phase as the artifact.

Moved `.claude/` out of the tracked `.gitignore` and into `.git/info/exclude`, which never leaves the local machine. The project's own `.gitignore` shouldn't name any AI tooling, even to ignore it.

Also corrected course on commit granularity: Phase 0 shipped as five small commits, more granular than `ai-search-chatbot`'s real pattern of roughly one implementation commit plus one docs commit per phase. Not rewriting the pushed history, but sticking to the tighter pattern from here on.

**State at end of session:** plan reconciled, Phase 0 docs updated, ready to start Phase 1.

## 2026-08-21 (continued): Phase 1

Started Phase 1 and immediately hit two real problems the build plan didn't anticipate: `load_dataset("ai4bharat/MSMARCO-XI", "hi", ...)` doesn't work (the repo uses per-language parquet files and a legacy loading script, not per-language configs), and `hf-xet` hung twice partway through the same download. Both documented in Decisions 1.1 and 1.3 rather than papering over them.

Ended up depending on `huggingface_hub` + `pandas` + `pyarrow` directly instead of the `datasets` package, since we're not calling anything from it anymore. Working sample settled at 1,000 queries from the validation split, about 75,000 chunks across all three strategies and both languages once chunked.

**Phases completed:** Phase 1 (see `docs/phases/phase1.md`)

**Highlights worth remembering:**
- The build plan's exact dataset loading call is wrong. Anyone picking this project back up should read Decision 1.1 before assuming the plan's Tech Stack section is accurate on that point.
- 46% of queries in this dataset have no `is_selected` passage at all. Worth remembering for Phase 5's golden eval set, it should bootstrap only from rows that do have one.
- One Hindi passage in the sample ran to 4,092 words, a translation outlier. Not a problem for chunking (fixed-size handles it fine), but worth knowing about if anything downstream assumes passages are always short.

**State at end of session:** Phase 1 chunking done and verified against real data. Phase 2 (embeddings and Qdrant indexing) is next.
