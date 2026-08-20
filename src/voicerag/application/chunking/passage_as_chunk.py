"""Passage-as-chunk, the baseline strategy.

Indexes each passage exactly as retrieved, no splitting. MS MARCO
passages are already short (a sentence or two on average, see
docs/decisions.md Decision 1.2), so this is the floor the other two
strategies get compared against.
"""


def chunk_passage_as_chunk(text: str) -> list[str]:
    return [text]
