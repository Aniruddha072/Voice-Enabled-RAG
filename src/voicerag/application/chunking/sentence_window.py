"""Sentence-window chunking.

Splits a passage into sentences, then indexes overlapping windows of
a few sentences at a time. Finer granularity than passage-as-chunk,
which may help precision on queries that hinge on one specific fact
buried in an otherwise-irrelevant passage.

Sentence splitting matches English terminators (. ! ?) and the Hindi
danda (।), verified against real Answer text from the dataset, which
consistently ends sentences with । rather than a period.
"""

import re

_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


def split_sentences(text: str) -> list[str]:
    sentences = [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]
    return sentences or [text]


def chunk_sentence_window(text: str, window_sentences: int = 3, overlap_sentences: int = 1) -> list[str]:
    if overlap_sentences >= window_sentences:
        raise ValueError(
            f"overlap_sentences ({overlap_sentences}) must be less than window_sentences ({window_sentences})"
        )

    sentences = split_sentences(text)
    if len(sentences) <= window_sentences:
        return [text]

    step = window_sentences - overlap_sentences
    chunks = []
    start = 0
    while start < len(sentences):
        window = sentences[start : start + window_sentences]
        chunks.append(" ".join(window))
        if start + window_sentences >= len(sentences):
            break
        start += step
    return chunks
