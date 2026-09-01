"""Input, relevance, and groundedness guardrails for the RAG pipeline."""

from pydantic import BaseModel

from voicerag.domain.entities import RetrievedPassage

RELEVANCE_THRESHOLD = 0.6


class GuardrailResult(BaseModel):
    passed: bool
    reason: str | None = None


def check_relevance(passages: list[RetrievedPassage]) -> GuardrailResult:
    """Off-topic check: is the top retrieval score even close to the
    question, before spending an LLM call trying to answer it.
    Threshold picked from a real relevant query (~0.73) against a
    couple of clearly off-topic ones (~0.44-0.53).
    """
    if not passages or passages[0].score < RELEVANCE_THRESHOLD:
        return GuardrailResult(passed=False, reason="top retrieval score below relevance threshold")
    return GuardrailResult(passed=True)
