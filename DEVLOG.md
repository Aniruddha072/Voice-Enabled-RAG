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

## 2026-08-20 (continued): Phase 2

Also polished the repo a bit before starting Phase 2: set a real GitHub description and topics, cleaned up an irrelevant auto-added label, and added a standing rule to open a GitHub issue for genuinely significant bugs found along the way.

Phase 2 had a real detour. First throughput benchmark said 6.5 chunks/sec on CPU; that number was wrong; it used 50 identical sentences, which isn't representative. Real varied text measured at roughly 1/sec, confirmed twice. At that rate the 200-query sample would have taken about 4 hours, so we checked whether this machine has a GPU. It does, an RTX 4050 with 6GB VRAM, just sitting unused because the default PyTorch install on Windows is CPU-only. Configured `uv` to pull the CUDA build instead.

First GPU attempt crashed with a CUDA out-of-memory error at batch size 128, tracked as GitHub issue #1. Root cause was an unbounded sequence length letting one long outlier passage blow up an entire batch's memory footprint. Capped `max_seq_length` at 512 and dropped batch size to 32, then the full 200-query / 14,429-chunk run completed in under 5 minutes at a sustained ~54 chunks/sec.

**Phases completed:** Phase 2 (see `docs/phases/phase2.md`)

**Highlights worth remembering:**
- Never benchmark embedding throughput with identical or near-identical inputs, it does not reflect real varied-text cost. Should have caught this the first time.
- Check for a GPU before assuming a CPU-only ML pipeline is as fast as it'll get. This one had a 50x speedup sitting unused.
- GPU memory is a hard ceiling in a way CPU memory usually isn't for this kind of workload; an unbounded sequence length is a real crash risk on a 6GB card, not just a performance concern.
- Verifying retrieval quality needs a query actually answerable from what's indexed. Testing an arbitrary phrase not covered by the 200-query sample briefly looked like a quality problem; it wasn't, it was a bad test.

**State at end of session:** Phase 2 done, verified, both languages retrieving correctly. Phase 3 (voice input, Sarvam + local whisper) is next.

## 2026-08-20 (continued): commit style correction, one more bug, wrap-up

Revisited the commit granularity rule. The flat "1 feat + 1 docs per phase" pattern used for Phases 0-2 doesn't match how `ai-search-chatbot` actually did it, that project's real per-phase count ranged 2-6 depending on real seams, real bugs, and real mid-phase corrections. Not rewriting the pushed history for Phases 0-2, but applying the finer pattern from Phase 3 on: split by component, separate `chore:` commits for real dependency changes, separate `fix:` commits for bugs, docs commits allowed to land more than once per phase.

Did a deliberate bug-hunting pass across everything built so far before ending the session. Found one real issue: `chunk_fixed_size` and `chunk_sentence_window` both loop forever if `overlap >= window` (step becomes zero or negative, the loop's termination condition never gets hit). Verified with a bounded repro rather than just reading the code and assuming. Not triggered by any current code path, both functions only ever get called with the safe defaults, but a real, reachable defect worth having on record before Phase 5's chunking-parameter comparisons might hit it. Filed as issue #2, not fixed tonight.

**State at end of session:** Phases 0-2 complete, pushed, both languages verified retrieving correctly. One open bug (#2, low urgency). See `docs/session-handoff.md` for exact resume state, environment notes, and what Phase 3 needs first (a Sarvam account and API key, and recording real test voice clips).

## 2026-08-21: Phase 3

Got the Sarvam account and API key set up, then built both STT providers. `SarvamSttProvider` wraps the official `sarvamai` SDK, `mode="transcribe"` so a Hindi question stays Hindi text instead of getting translated to English. `WhisperLocalSttProvider` wraps `faster-whisper`, no account needed, though it turned out CUDA wasn't a real option for it: `ctranslate2` needs its own system-level cuBLAS/cuDNN that torch's bundled CUDA libraries don't satisfy, not worth fighting on Windows for clips this short, so it runs CPU-only.

Recorded 25 real test clips, 12 English and 13 Hindi, using actual queries pulled from the 200-query sample already indexed in Qdrant, and ran all of them through both providers. Sarvam came back correct or near-perfect across the board in both languages. Whisper held up fine on English (one clip aside, where it misdetected the language entirely and transcribed an English question in Devanagari script) but never produced a single fully clean Hindi transcript, errors ranged from a few garbled words to one clip that repeated itself. That's a real, repeatable pattern, not a fluke from one bad clip, so Sarvam is now the default provider for both languages and whisper is a true last-resort fallback, not a peer. Filed as issue #3 and Decision 3.1.

Also added proper failure handling: both providers now guard against `None`/empty transcript text, expose a language-detection confidence score, and translate their own network/API errors into one shared `SttError` instead of leaking `httpx` or `sarvamai` exception types up through the interface. Decision 3.2.

**Phases completed:** Phase 3 (see `docs/phases/phase3.md`)

**Highlights worth remembering:**
- When comparing STT providers, use real recorded clips against real dataset queries, not synthetic text. The Hindi quality gap only showed up because we tested with an actual accent and actual mispronunciations, not clean TTS audio.
- A provider auto-detecting the wrong language entirely (whisper on the "moscato wine" clip) is a different, worse failure mode than just lower accuracy. Worth watching for specifically, not just spot-checking overall correctness.
- `ctranslate2` and `torch` don't share CUDA libraries on Windows even when both claim GPU support. Confirmed by hitting a `cublas64_12.dll` load failure despite CUDA already working fine for embeddings.

**State at end of session:** Phase 3 done, pushed. Phase 4 (grounded generation + guardrails, needs a Groq API key) is next.
