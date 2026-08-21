# Phase 3: Voice Input

**Commit(s):** `70c2a90` (chore: add sarvamai and faster-whisper for STT), `d54661a` (feat(stt): implement Sarvam Saaras v3 provider), `a0fc3a2` (feat(stt): implement local faster-whisper fallback provider), plus the failure-handling and docs commits that close out the phase.

## What we built

- `infrastructure/stt/sarvam_provider.py`: `SarvamSttProvider`, wraps the `sarvamai` SDK's async client, `mode="transcribe"` so output stays in the spoken language instead of translating to English.
- `infrastructure/stt/whisper_local_provider.py`: `WhisperLocalSttProvider`, wraps `faster-whisper`'s `small` model, CPU-only.
- `domain/interfaces.py` gained `SttError`, one exception both providers raise on network/timeout/API failure instead of leaking SDK-specific exception types.
- `domain/entities.py`'s `Transcript` gained an optional `confidence` field, populated from each provider's language-detection confidence.
- 25 real recorded test clips (12 English, 13 Hindi), read from actual queries in the indexed 200-query sample, run through both providers to compare transcript quality.

## What we learned

- Sarvam Saaras v3 was correct or near-perfect on all 25 real clips in both languages.
- `faster-whisper`'s `small` model held up reasonably on English (11/12 clean, one clip where it misdetected the language entirely and returned Devanagari script for an English question) but never produced a fully clean transcript on a single Hindi clip. See Decision 3.1 and issue #3.
- `ctranslate2` (faster-whisper's backend) needs its own system-level cuBLAS/cuDNN, separate from the CUDA libraries torch already has working for embeddings. Not worth chasing down on Windows for clips a few seconds long, so this provider runs CPU-only on purpose.
- Both providers needed the same defensive normalization: guard against `None` transcript text, strip whitespace, and translate provider-specific errors into one shared exception, otherwise the port abstraction leaks SDK details up through the interface.

## Key design decisions

See `docs/decisions.md`, Decisions 3.1 (Sarvam as default provider, whisper-local as last-resort fallback only) and 3.2 (shared `SttError` and `Transcript.confidence`).

## Challenges faced

No crashes this phase. One transient network read error mid-batch while collecting the Hindi comparison data, which is exactly the kind of failure `SttError` and Phase 5's planned `tenacity` retry/backoff exist for; the batch was simply re-run by hand this time.

## Verification

```
# English, query "what is a corporation?" (Recording.m4a)
sarvam : What is a corporation?
whisper: What is a corporation?

# Hindi, query "भारत की राजधानी क्या है?" (Recording (2).m4a)
sarvam : भारत की राजधानी क्या है?
whisper: बारत की राज्टानी क्या है?   <- garbled

# 12 more English clips from the indexed sample: 12/12 correct on Sarvam,
# 11/12 correct on whisper (1 misdetected as Hindi)

# 13 more Hindi clips from the indexed sample: 13/13 correct or
# near-perfect on Sarvam, 0/13 fully clean on whisper
```

Full per-clip transcripts aren't kept in the repo since they're just test data, not a fixture the code depends on; the pattern is what mattered, and it held across every clip.
