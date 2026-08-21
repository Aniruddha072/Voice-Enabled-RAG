"""Ports the application layer depends on, implemented by infrastructure.

Every external system sits behind one of these, so the pipeline never
imports a concrete SDK directly and any provider can be swapped without
touching application code.

Guardrail isn't defined here yet. The three guardrail checks (relevance
threshold, unsafe-input, groundedness) don't share an obvious method
signature, and this codebase doesn't build guardrails.py until Phase 4 -
see docs/decisions.md, Decision 0.3.
"""

from abc import ABC, abstractmethod

from voicerag.domain.entities import Answer, Chunk, Query, RetrievedPassage, Transcript


class SttError(Exception):
    """A speech-to-text provider failed to produce a transcript, whether
    from a network/timeout problem or the provider's own API rejecting
    the request. Callers see one exception type regardless of which
    provider raised it, instead of provider-specific SDK exceptions
    leaking through the interface. Retry/backoff policy is the caller's
    decision, not this exception's, see Decision 3.1 and the Phase 5
    tenacity work.
    """


class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: str, language_hint: str | None = None) -> Transcript: ...


class Embedder(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    @abstractmethod
    async def search(self, vector: list[float], language: str, limit: int = 5) -> list[RetrievedPassage]: ...


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, query: Query, context: list[RetrievedPassage]) -> Answer: ...
