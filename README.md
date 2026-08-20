# Voice-Enabled RAG — Hindi + English

A voice-in, grounded-answer-out RAG pipeline over the Hindi and English content in
[`ai4bharat/MSMARCO-XI`](https://huggingface.co/datasets/ai4bharat/MSMARCO-XI), built at **$0 cost**.

Speak a question in Hindi or English → speech-to-text → retrieval over a bilingual vector
index → grounded answer generation with citations, guardrails, and honest per-stage
latency numbers.

> **Status:** bootstrapping. Full build plan lives in `docs/roadmap.md` (coming in the next
> commit). This repo currently just establishes the project scaffold.

## Ground rules

- **$0 spend, guaranteed** — every component is free-tier or fully local/open-source.
- **Two languages, done properly** — Hindi and English are both first-class in V1.
- **Lean architecture** — one domain/application/infrastructure/presentation layering,
  no duplicated scaffolding.
- **Core loop before hardening** — no auth, no Postgres, no Kubernetes until the RAG loop
  works end to end.
- **Honest numbers over impressive-sounding ones** — latency is reported per stage.

## License

MIT — see [LICENSE](LICENSE).
