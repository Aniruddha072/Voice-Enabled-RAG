from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from voicerag.domain.interfaces import SttError
from voicerag.infrastructure.stt.sarvam_provider import SarvamSttProvider

FAKE_SUCCESS = SimpleNamespace(transcript="hello world", language_code="en-IN", language_probability=0.99)


@pytest.fixture
def audio_path(tmp_path):
    path = tmp_path / "clip.wav"
    path.write_bytes(b"fake audio bytes")
    return str(path)


@pytest.mark.asyncio
async def test_transcribe_retries_on_transient_network_error_then_succeeds(audio_path):
    provider = SarvamSttProvider()
    mock_transcribe = AsyncMock(
        side_effect=[
            httpx.ConnectError("boom"),
            httpx.ConnectError("boom"),
            FAKE_SUCCESS,
        ]
    )
    provider._client.speech_to_text.transcribe = mock_transcribe

    transcript = await provider.transcribe(audio_path)

    assert transcript.text == "hello world"
    assert mock_transcribe.call_count == 3


@pytest.mark.asyncio
async def test_transcribe_raises_stt_error_after_exhausting_retries(audio_path):
    provider = SarvamSttProvider()
    mock_transcribe = AsyncMock(side_effect=httpx.ConnectError("boom"))
    provider._client.speech_to_text.transcribe = mock_transcribe

    with pytest.raises(SttError):
        await provider.transcribe(audio_path)

    assert mock_transcribe.call_count == 3
