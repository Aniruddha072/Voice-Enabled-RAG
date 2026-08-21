"""Core domain entities shared across every layer.

Plain data contracts, not behavior. The pipeline stages pass these to
each other regardless of which concrete provider sits behind an
interface (Sarvam or local whisper, Groq or anything else).
"""

from __future__ import annotations

from pydantic import BaseModel


class Query(BaseModel):
    text: str
    language: str  # "en" or "hi"


class Transcript(BaseModel):
    text: str
    language: str
    stt_provider: str
    # Language-detection confidence from the provider, not a word-level
    # accuracy score. None if the provider doesn't expose one.
    confidence: float | None = None


class Chunk(BaseModel):
    id: str
    text: str
    language: str
    source_query_id: str
    is_selected: bool
    chunking_strategy: str


class RetrievedPassage(BaseModel):
    chunk: Chunk
    score: float


class Answer(BaseModel):
    text: str
    language: str
    citations: list[str]
    refused: bool = False


class EvalResult(BaseModel):
    query_id: str
    language: str
    chunking_strategy: str
    recall_at_5: float | None = None
    mrr: float | None = None
    groundedness_pass: bool | None = None
