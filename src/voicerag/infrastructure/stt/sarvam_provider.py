"""Sarvam Saaras v3 speech-to-text, used with mode="transcribe" so the
output stays in the spoken language instead of being translated to
English (Saaras also supports translation, which isn't what we want
here since retrieval and generation are both language-filtered).
"""

from sarvamai import AsyncSarvamAI

from voicerag.config import settings
from voicerag.domain.entities import Transcript
from voicerag.domain.interfaces import SpeechToTextProvider

MODEL_NAME = "saaras:v3"

_LANGUAGE_TO_SARVAM = {"en": "en-IN", "hi": "hi-IN"}


class SarvamSttProvider(SpeechToTextProvider):
    def __init__(self) -> None:
        self._client = AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)

    async def transcribe(self, audio_path: str, language_hint: str | None = None) -> Transcript:
        kwargs = {}
        if language_hint is not None:
            kwargs["language_code"] = _LANGUAGE_TO_SARVAM[language_hint]

        with open(audio_path, "rb") as audio_file:
            response = await self._client.speech_to_text.transcribe(
                file=audio_file, model=MODEL_NAME, mode="transcribe", **kwargs
            )

        detected = response.language_code or _LANGUAGE_TO_SARVAM.get(language_hint or "", "en-IN")
        language = detected.split("-")[0]

        return Transcript(text=response.transcript, language=language, stt_provider="sarvam")
