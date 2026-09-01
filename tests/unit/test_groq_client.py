import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import groq
import pytest

from voicerag.domain.entities import Query
from voicerag.domain.interfaces import LLMError
from voicerag.infrastructure.llm.groq_client import GroqLLMProvider


def _fake_completion(payload: dict) -> SimpleNamespace:
    message = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


FAKE_SUCCESS = _fake_completion({"answer": "a grounded answer", "citations": ["c1"], "refused": False})


@pytest.mark.asyncio
async def test_generate_retries_on_transient_api_error_then_succeeds():
    provider = GroqLLMProvider()
    mock_create = AsyncMock(
        side_effect=[
            groq.APIConnectionError(request=None),
            groq.APIConnectionError(request=None),
            FAKE_SUCCESS,
        ]
    )
    provider._client.chat.completions.create = mock_create

    answer = await provider.generate(Query(text="what is a corporation", language="en"), [])

    assert answer.text == "a grounded answer"
    assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_generate_raises_llmerror_after_exhausting_retries():
    provider = GroqLLMProvider()
    mock_create = AsyncMock(side_effect=groq.APIConnectionError(request=None))
    provider._client.chat.completions.create = mock_create

    with pytest.raises(LLMError):
        await provider.generate(Query(text="what is a corporation", language="en"), [])

    assert mock_create.call_count == 3
