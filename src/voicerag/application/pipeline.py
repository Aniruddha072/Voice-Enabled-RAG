"""Wires speech-to-text, retrieval, generation, and all three
guardrails into one voice-in, grounded-answer-out flow.
"""

from voicerag.application.guardrails import Guardrails, check_relevance
from voicerag.application.latency_tracker import LatencyTracker
from voicerag.domain.entities import Answer, Query
from voicerag.domain.interfaces import Embedder, LLMProvider, SpeechToTextProvider, VectorStore

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
    ) -> None:
        self._stt = stt
        self._embedder = embedder
        self._vector_store = vector_store
        self._llm = llm
        self._guardrails = guardrails
        self._retrieval_limit = retrieval_limit

    async def answer(
        self, audio_path: str, language_hint: str | None = None, tracker: LatencyTracker | None = None
    ) -> Answer:
        tracker = tracker or LatencyTracker()

        with tracker.track("stt"):
            transcript = await self._stt.transcribe(audio_path, language_hint)
        if not transcript.text:
            return _refusal("no_context", transcript.language)

        with tracker.track("input_safety"):
            safety = await self._guardrails.check_input_safety(transcript.text)
        if not safety.passed:
            return _refusal("unsafe", transcript.language)

        query = Query(text=transcript.text, language=transcript.language)
        with tracker.track("embed"):
            vector = (await self._embedder.embed([query.text]))[0]
        with tracker.track("retrieve"):
            passages = await self._vector_store.search(vector, language=query.language, limit=self._retrieval_limit)

        with tracker.track("relevance"):
            relevance = check_relevance(passages)
        if not relevance.passed:
            return _refusal("no_context", query.language)

        with tracker.track("generate"):
            answer = await self._llm.generate(query, passages)
        if answer.refused:
            return answer

        with tracker.track("groundedness"):
            groundedness = await self._guardrails.check_groundedness(answer.text, passages)
        if not groundedness.passed:
            return _refusal("no_context", query.language)

        return answer
