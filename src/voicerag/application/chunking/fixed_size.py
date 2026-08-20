"""Fixed-size chunking with overlap.

Splits by word count, not characters, so it behaves consistently
across English and Hindi even though the two scripts differ in bytes
per word. On this dataset it's close to a no-op (median passage is
~50-55 words, well under the window), but it matters for the small
number of unusually long passages and keeps the three-way comparison
fair, see docs/decisions.md Decision 1.2.
"""


def chunk_fixed_size(text: str, window_words: int = 150, overlap_words: int = 30) -> list[str]:
    words = text.split()
    if len(words) <= window_words:
        return [text]

    step = window_words - overlap_words
    chunks = []
    start = 0
    while start < len(words):
        window = words[start : start + window_words]
        chunks.append(" ".join(window))
        if start + window_words >= len(words):
            break
        start += step
    return chunks
