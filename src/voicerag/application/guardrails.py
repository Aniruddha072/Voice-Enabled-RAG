"""Input, relevance, and groundedness guardrails for the RAG pipeline.

No shared Guardrail interface, per Decision 0.3: the three checks take
genuinely different inputs (retrieval results, raw query text, an
answer plus its source passages), and one is pure Python while the
other two call Groq. Forcing one abstract method signature over that
would mean either a lossy generic signature or a context object
nothing else needs, abstraction with no real swapping use case behind
it. Each check is a plain function or method returning the same
GuardrailResult shape instead.
"""

import json
import re

from groq import AsyncGroq
from pydantic import BaseModel

from voicerag.config import settings
from voicerag.domain.entities import RetrievedPassage

RELEVANCE_THRESHOLD = 0.6

PROMPT_GUARD_MODEL = "meta-llama/llama-prompt-guard-2-86m"
UNSAFE_THRESHOLD = 0.5

JUDGE_MODEL = "openai/gpt-oss-120b"
GROUNDEDNESS_HIGH = 0.75
GROUNDEDNESS_LOW = 0.35

_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "grounded": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["grounded", "reason"],
    "additionalProperties": False,
}


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


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _lexical_overlap(answer_text: str, passages: list[RetrievedPassage]) -> float:
    answer_tokens = _tokenize(answer_text)
    if not answer_tokens:
        return 0.0
    source_tokens = _tokenize(" ".join(p.chunk.text for p in passages))
    return len(answer_tokens & source_tokens) / len(answer_tokens)


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

    async def check_groundedness(self, answer_text: str, passages: list[RetrievedPassage]) -> GuardrailResult:
        """Lexical overlap first, cheap and instant. Only calls Groq
        to judge when the heuristic lands in the ambiguous middle.
        """
        overlap = _lexical_overlap(answer_text, passages)
        if overlap >= GROUNDEDNESS_HIGH:
            return GuardrailResult(passed=True, reason=f"lexical overlap {overlap:.2f}")
        if overlap <= GROUNDEDNESS_LOW:
            return GuardrailResult(passed=False, reason=f"lexical overlap {overlap:.2f}")

        passages_text = "\n\n".join(p.chunk.text for p in passages)
        prompt = (
            f"Answer:\n{answer_text}\n\nSource passages:\n{passages_text}\n\n"
            "Is every claim in the answer actually supported by the source "
            "passages? Judge only whether the passages contain this "
            "information, not whether it is true in general."
        )
        completion = await self._client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "groundedness_judgment", "strict": True, "schema": _JUDGE_SCHEMA},
            },
        )
        parsed = json.loads(completion.choices[0].message.content)
        return GuardrailResult(passed=parsed["grounded"], reason=parsed["reason"])
