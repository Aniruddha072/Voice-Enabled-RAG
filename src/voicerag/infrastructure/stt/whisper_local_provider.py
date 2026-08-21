"""Local speech-to-text via faster-whisper. Runs entirely on this
machine, no account or network call needed. This is the fallback path
if Sarvam is ever down, slow, or over its free tier, and the baseline
to compare Sarvam's transcript quality against.

CPU only, on purpose: the backend (ctranslate2) needs its own
system-level cuBLAS/cuDNN, separate from the CUDA libraries torch
bundles for itself, and getting those onto the path on Windows isn't
worth it for clips a few seconds long. GPU is reserved for the
embedding step, where it actually matters at scale.
"""

import asyncio

from faster_whisper import WhisperModel

from voicerag.domain.entities import Transcript
from voicerag.domain.interfaces import SpeechToTextProvider

MODEL_SIZE = "small"


class WhisperLocalSttProvider(SpeechToTextProvider):
    def __init__(self) -> None:
        self._model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

    async def transcribe(self, audio_path: str, language_hint: str | None = None) -> Transcript:
        return await asyncio.to_thread(self._transcribe_sync, audio_path, language_hint)

    def _transcribe_sync(self, audio_path: str, language_hint: str | None) -> Transcript:
        segments, info = self._model.transcribe(audio_path, language=language_hint)
        text = "".join(segment.text for segment in segments).strip()
        return Transcript(text=text, language=info.language, stt_provider="whisper_local")
