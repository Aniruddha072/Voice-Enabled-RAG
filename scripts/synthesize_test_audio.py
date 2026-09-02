"""Synthesizes test audio for the Phase 5 latency benchmark: real
speech for golden-set queries, generated locally and for free with
Piper TTS instead of recording more clips by hand.

Voice models are Piper's own ONNX voices from rhasspy/piper-voices,
pulled with huggingface_hub, matching how the rest of this project
fetches remote files (see Decision 1.1), rather than Piper's own
auto-download mechanism.

Run: uv run python scripts/synthesize_test_audio.py
"""

import argparse
import json
import wave
from pathlib import Path

from huggingface_hub import hf_hub_download
from piper.voice import PiperVoice

VOICE_REPO = "rhasspy/piper-voices"
VOICE_PATHS = {
    "en": "en/en_US/lessac/medium/en_US-lessac-medium",
    "hi": "hi/hi_IN/pratham/medium/hi_IN-pratham-medium",
}


def load_voice(language: str) -> PiperVoice:
    voice_path = VOICE_PATHS[language]
    onnx_path = hf_hub_download(repo_id=VOICE_REPO, filename=f"{voice_path}.onnx")
    hf_hub_download(repo_id=VOICE_REPO, filename=f"{voice_path}.onnx.json")
    return PiperVoice.load(onnx_path)


def load_golden_set(path: Path, per_language: int) -> dict[str, list[dict]]:
    queries: dict[str, list[dict]] = {"en": [], "hi": []}
    with path.open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            bucket = queries[record["language"]]
            if len(bucket) < per_language:
                bucket.append(record)
    return queries


def synthesize_batch(queries: dict[str, list[dict]], audio_dir: Path) -> list[dict]:
    manifest = []
    for language, records in queries.items():
        voice = load_voice(language)
        lang_dir = audio_dir / language
        lang_dir.mkdir(parents=True, exist_ok=True)
        for record in records:
            audio_path = lang_dir / f"{record['query_id']}.wav"
            with wave.open(str(audio_path), "wb") as wav_file:
                voice.synthesize_wav(record["query_text"], wav_file)
            manifest.append({**record, "audio_path": audio_path.as_posix()})
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-set", type=Path, default=Path("data/eval/golden_set.jsonl"))
    parser.add_argument("--per-language", type=int, default=100)
    parser.add_argument("--audio-dir", type=Path, default=Path("data/eval/audio"))
    parser.add_argument("--manifest", type=Path, default=Path("data/eval/tts_manifest.jsonl"))
    args = parser.parse_args()

    queries = load_golden_set(args.golden_set, args.per_language)
    print(f"Synthesizing {len(queries['en'])} EN + {len(queries['hi'])} HI queries...")

    manifest = synthesize_batch(queries, args.audio_dir)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", encoding="utf-8") as f:
        for record in manifest:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(manifest)} clips to {args.audio_dir}, manifest at {args.manifest}")


if __name__ == "__main__":
    main()
