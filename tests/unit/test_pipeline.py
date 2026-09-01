import pytest

from voicerag.application.guardrails import GuardrailResult
from voicerag.application.latency_tracker import LatencyTracker
from voicerag.application.pipeline import VoiceRAGPipeline
from voicerag.domain.entities import Answer, Chunk, RetrievedPassage, Transcript
from voicerag.domain.interfaces import Embedder, LLMProvider, SpeechToTextProvider, VectorStore


class FakeSttProvider(SpeechToTextProvider):
    async def transcribe(self, audio_path, language_hint=None):
        return Transcript(text="test query", language="en", stt_provider="fake")


class FakeEmbedder(Embedder):
    async def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore(VectorStore):
    async def upsert(self, chunks, vectors):
        pass

    async def search(self, vector, language, limit=5):
        chunk = Chunk(
            id="c1",
            text="relevant passage text",
            language=language,
            source_query_id="q1",
            is_selected=True,
            chunking_strategy="passage_as_chunk",
        )
        return [RetrievedPassage(chunk=chunk, score=0.9)]


class FakeLLMProvider(LLMProvider):
    async def generate(self, query, context):
        return Answer(text="a grounded answer", language=query.language, citations=[context[0].chunk.id], refused=False)


class FakeGuardrails:
    async def check_input_safety(self, text):
        return GuardrailResult(passed=True)

    async def check_groundedness(self, answer_text, passages):
        return GuardrailResult(passed=True)


def _build_pipeline():
    return VoiceRAGPipeline(
        stt=FakeSttProvider(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        llm=FakeLLMProvider(),
        guardrails=FakeGuardrails(),
    )


@pytest.mark.asyncio
async def test_answer_records_a_timing_for_every_stage():
    pipeline = _build_pipeline()
    tracker = LatencyTracker()

    await pipeline.answer("fake.wav", tracker=tracker)

    stage_names = [s.stage for s in tracker.stages]
    assert stage_names == ["stt", "input_safety", "embed", "retrieve", "relevance", "generate", "groundedness"]


@pytest.mark.asyncio
async def test_answer_works_without_a_tracker():
    pipeline = _build_pipeline()
    answer = await pipeline.answer("fake.wav")
    assert answer.refused is False
    assert answer.text == "a grounded answer"
