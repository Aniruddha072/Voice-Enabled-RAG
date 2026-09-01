"""Wires speech-to-text, retrieval, generation, and all three
guardrails into one voice-in, grounded-answer-out flow.
"""

import asyncio
from typing import Any, Coroutine

import structlog

from voicerag.application.guardrails import Guardrails, check_relevance
from voicerag.application.latency_tracker import LatencyTracker
from voicerag.domain.entities import Answer, Query
from voicerag.domain.interfaces import Embedder, LLMProvider, SpeechToTextProvider, VectorStore

logger = structlog.get_logger()

_REFUSAL_MESSAGES = {
    "unsafe": {
        "en": "Sorry, I can't help with that request.",
        "hi": "क्षमा करें, मैं इस अनुरोध में मदद नहीं कर सकता।",
    },
    "no_context": {
        "en": "Sorry, I don't have enough information to answer that question.",
        "hi": "क्षमा करें, इस प्रश्न का उत्तर देने के लिए मेरे पास पर्याप्त जानकारी नहीं है।",
    },
}

# Generous headroom over real measured stage durations (see
# docs/phases/phase4.md's verification numbers), enough to comfortably
# cover the STT and LLM providers' own retry/backoff attempts without
# the timeout budget fighting the retry policy.
DEFAULT_STAGE_TIMEOUTS = {
    "stt": 20.0,
    "input_safety": 15.0,
    "embed": 15.0,
    "retrieve": 10.0,
    "generate": 30.0,
    "groundedness": 30.0,
}


class PipelineTimeoutError(Exception):
    def __init__(self, stage: str, budget_seconds: float) -> None:
        super().__init__(f"stage '{stage}' exceeded its {budget_seconds}s timeout budget")
        self.stage = stage
        self.budget_seconds = budget_seconds


def _refusal(kind: str, language: str) -> Answer:
    messages = _REFUSAL_MESSAGES[kind]
    resolved_language = language if language in messages else "en"
    return Answer(text=messages[resolved_language], language=resolved_language, citations=[], refused=True)


class VoiceRAGPipeline:
    def __init__(
        self,
        stt: SpeechToTextProvider,
        embedder: Embedder,
        vector_store: VectorStore,
        llm: LLMProvider,
        guardrails: Guardrails,
        retrieval_limit: int = 5,
        stage_timeouts: dict[str, float] | None = None,
    ) -> None:
        self._stt = stt
        self._embedder = embedder
        self._vector_store = vector_store
        self._llm = llm
        self._guardrails = guardrails
        self._retrieval_limit = retrieval_limit
        self._stage_timeouts = {**DEFAULT_STAGE_TIMEOUTS, **(stage_timeouts or {})}

    def _log_stage(self, tracker: LatencyTracker, stage: str, ok: bool) -> None:
        duration_ms = tracker.stages[-1].duration_ms
        logger.info(
            "stage_complete",
            correlation_id=tracker.correlation_id,
            stage=stage,
            duration_ms=round(duration_ms, 1),
            ok=ok,
        )

    async def _run_stage(self, tracker: LatencyTracker, stage: str, coro: Coroutine[Any, Any, Any]) -> Any:
        budget = self._stage_timeouts[stage]
        ok = True
        try:
            with tracker.track(stage):
                try:
                    return await asyncio.wait_for(coro, timeout=budget)
                except asyncio.TimeoutError as e:
                    raise PipelineTimeoutError(stage, budget) from e
        except Exception:
            ok = False
            raise
        finally:
            self._log_stage(tracker, stage, ok)

    async def answer(
        self, audio_path: str, language_hint: str | None = None, tracker: LatencyTracker | None = None
    ) -> Answer:
        tracker = tracker or LatencyTracker()

        transcript = await self._run_stage(tracker, "stt", self._stt.transcribe(audio_path, language_hint))
        if not transcript.text:
            return _refusal("no_context", transcript.language)

        safety = await self._run_stage(
            tracker, "input_safety", self._guardrails.check_input_safety(transcript.text)
        )
        if not safety.passed:
            return _refusal("unsafe", transcript.language)

        query = Query(text=transcript.text, language=transcript.language)
        vector = (await self._run_stage(tracker, "embed", self._embedder.embed([query.text])))[0]
        passages = await self._run_stage(
            tracker,
            "retrieve",
            self._vector_store.search(vector, language=query.language, limit=self._retrieval_limit),
        )

        with tracker.track("relevance"):
            relevance = check_relevance(passages)
        self._log_stage(tracker, "relevance", ok=True)
        if not relevance.passed:
            return _refusal("no_context", query.language)

        answer = await self._run_stage(tracker, "generate", self._llm.generate(query, passages))
        if answer.refused:
            return answer

        groundedness = await self._run_stage(
            tracker, "groundedness", self._guardrails.check_groundedness(answer.text, passages)
        )
        if not groundedness.passed:
            return _refusal("no_context", query.language)

        return answer
