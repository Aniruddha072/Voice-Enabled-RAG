"""Grounded generation via Groq.

Model is openai/gpt-oss-120b, not the build plan's original Llama 3.3
70B. Groq deprecated Llama 3.3 70B off its free tier in August 2026,
confirmed by querying this account's actual model list, not just
reading docs. gpt-oss-120b is Groq's own recommended migration target,
still on the free tier, and supports strict JSON schema output, which
this client relies on for reliable citations, see Decision 4.1.
"""

import json

from groq import AsyncGroq

from voicerag.config import settings
from voicerag.domain.entities import Answer, Query, RetrievedPassage
from voicerag.domain.interfaces import LLMProvider

MODEL_NAME = "openai/gpt-oss-120b"
TEMPERATURE = 0.2

_SYSTEM_PROMPT = """You are a grounded question-answering assistant. You answer \
only using the passages you are given, tagged with an id, never from your own \
general knowledge.

Rules:
- Answer in the same language as the question. A Hindi question gets a Hindi \
answer, an English question gets an English answer.
- Use only information found in the given passages. Do not add outside facts, \
even ones you are confident about.
- If the passages do not contain enough information to answer the question, \
set refused to true and write a short, polite explanation in the question's \
own language that the answer isn't available in the given context, instead \
of guessing.
- List the id of every passage you actually relied on in citations. If \
refused is true, citations must be empty.
"""

_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "refused": {"type": "boolean"},
    },
    "required": ["answer", "citations", "refused"],
    "additionalProperties": False,
}


def _build_user_message(query: Query, context: list[RetrievedPassage]) -> str:
    passages = "\n\n".join(f"[{p.chunk.id}]\n{p.chunk.text}" for p in context)
    return f"Question ({query.language}): {query.text}\n\nPassages:\n{passages}"


class GroqLLMProvider(LLMProvider):
    def __init__(self, model: str = MODEL_NAME, temperature: float = TEMPERATURE) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = model
        self._temperature = temperature

    async def generate(self, query: Query, context: list[RetrievedPassage]) -> Answer:
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(query, context)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "grounded_answer", "strict": True, "schema": _ANSWER_SCHEMA},
            },
        )
        parsed = json.loads(response.choices[0].message.content)

        return Answer(
            text=parsed["answer"],
            language=query.language,
            citations=parsed["citations"],
            refused=parsed["refused"],
        )
