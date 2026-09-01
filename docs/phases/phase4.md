# Phase 4: Grounded Generation + Guardrails

**Commit(s):** `dc5aec9` (chore: add groq SDK dependency), `02248ce` (feat(llm): implement Groq grounded generation provider), `3c0da47` (feat(guardrails): implement relevance-threshold check), `f5e8cf6` (feat(guardrails): implement unsafe-input check), `6cec250` (feat(guardrails): implement groundedness check), `a79ba6f` (feat(pipeline): wire STT, retrieval, generation, and guardrails), `606dafa` (fix(guardrails): correct relevance threshold from 0.6 to 0.53).

## What we built

- `infrastructure/llm/groq_client.py`: `GroqLLMProvider`, grounded generation on `openai/gpt-oss-120b` with strict JSON schema output for the answer text, citations, and refusal flag.
- `application/guardrails.py`: three checks. `check_relevance` (pure Python, threshold against the top retrieval score), `Guardrails.check_input_safety` (Groq's dedicated prompt-guard model), `Guardrails.check_groundedness` (lexical overlap first, a Groq judge call only when that's ambiguous).
- `application/pipeline.py`: `VoiceRAGPipeline`, wiring STT through to a grounded, guardrailed answer.

## What we learned

- The build plan's named model, Llama 3.3 70B, was gone from Groq's free tier entirely by the time this phase started. Checking the account's real model list caught this before any code got written against a model that no longer existed.
- A relevance threshold calibrated from one example per language isn't real calibration. The first threshold (0.6, from a single English query) broke on the first real pipeline run against a known-good Hindi query, a genuine false rejection, not a hindsight worry. Recalibrating with 8 known in-sample queries and 3 genuinely absent topics per language, instead of one each, found a threshold (0.53) that separates almost every real case correctly in both languages, with one honestly unrecoverable English outlier.
- Lexical word-overlap is not equally reliable across languages. Hindi's frequent postpositions and function words inflate raw overlap even for a fabricated, wrong answer (~0.68 measured), while English's fabricated case scored clearly low (~0.32). The heuristic's ambiguous zone is wide on purpose so the Groq judge call catches what the heuristic can't decide alone, which happens more often for Hindi.

## Key design decisions

See `docs/decisions.md`, Decision 4.1 (model choice) and Decision 4.2 (no shared `Guardrail` interface, the relevance-threshold bug and its fix, the groundedness heuristic's language asymmetry).

## Challenges faced

One real bug, caught and fixed before anything was pushed: the first relevance threshold (0.6) rejected a real, answerable Hindi query. Not filed as a GitHub issue since nothing broken ever shipped, documented in Decision 4.2 and in the commit history instead (`3c0da47` introduces the original threshold, `606dafa` is the fix).

## Verification

```
=== English, in-sample: what are the functions of marketing
  refused: False
  citations: ['570191_en_sentence_window_2_0', '570191_en_passage_as_chunk_8_0']

=== Hindi, in-sample: ल्यूकेमिया क्या है?
  refused: False
  citations: ['765398_hi_sentence_window_0_0']

=== English, wildcard (not in the 200-query sample): what is a corporation
  refused: True
  text: Sorry, I don't have enough information to answer that question.
```

All three real recorded clips, run through the full `VoiceRAGPipeline`, not just the LLM step in isolation.
