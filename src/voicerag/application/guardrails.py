"""Input, relevance, and groundedness guardrails for the RAG pipeline."""

from groq import AsyncGroq
from pydantic import BaseModel

from voicerag.config import settings
from voicerag.domain.entities import RetrievedPassage

RELEVANCE_THRESHOLD = 0.6

PROMPT_GUARD_MODEL = "meta-llama/llama-prompt-guard-2-86m"
UNSAFE_THRESHOLD = 0.5


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


class Guardrails:
    """Checks that need an LLM call, unlike check_relevance above."""

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)

    async def check_input_safety(self, text: str) -> GuardrailResult:
        """meta-llama/llama-prompt-guard-2-86m is a small model purpose-
        built for jailbreak/prompt-injection detection, cheaper and
        more reliable here than asking the big generation model to
        classify safety itself. It returns a plain probability score
        as its response text.
        """
        completion = await self._client.chat.completions.create(
            model=PROMPT_GUARD_MODEL,
            messages=[{"role": "user", "content": text}],
        )
        score = float(completion.choices[0].message.content)
        if score >= UNSAFE_THRESHOLD:
            return GuardrailResult(passed=False, reason=f"prompt-guard score {score:.3f}")
        return GuardrailResult(passed=True)
