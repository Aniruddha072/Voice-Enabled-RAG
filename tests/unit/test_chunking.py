import pytest

from voicerag.application.chunking.fixed_size import chunk_fixed_size
from voicerag.application.chunking.passage_as_chunk import chunk_passage_as_chunk
from voicerag.application.chunking.sentence_window import chunk_sentence_window, split_sentences

SHORT_EN = "A corporation is a company recognized as a single legal entity."
SHORT_HI = "निगम एक कंपनी है जो एक एकल कानूनी इकाई के रूप में मान्यता प्राप्त है।"

LONG_EN = " ".join(f"Sentence number {i} about corporations and their governance." for i in range(1, 40))
LONG_HI = " ".join(f"वाक्य संख्या {i} निगमों और उनके शासन के बारे में है।" for i in range(1, 40))


def test_passage_as_chunk_returns_single_chunk():
    assert chunk_passage_as_chunk(SHORT_EN) == [SHORT_EN]
    assert chunk_passage_as_chunk(SHORT_HI) == [SHORT_HI]


def test_fixed_size_short_passage_is_a_no_op():
    assert chunk_fixed_size(SHORT_EN, window_words=150, overlap_words=30) == [SHORT_EN]
    assert chunk_fixed_size(SHORT_HI, window_words=150, overlap_words=30) == [SHORT_HI]


def test_fixed_size_splits_long_passage_with_overlap():
    chunks = chunk_fixed_size(LONG_EN, window_words=20, overlap_words=5)
    assert len(chunks) > 1
    # every word in the source shows up in some chunk
    assert set(LONG_EN.split()) <= set(" ".join(chunks).split())
    # windows overlap: the last words of one chunk reappear at the start of the next
    first_tail = chunks[0].split()[-5:]
    second_head = chunks[1].split()[:5]
    assert first_tail == second_head


def test_fixed_size_handles_hindi_word_boundaries():
    chunks = chunk_fixed_size(LONG_HI, window_words=20, overlap_words=5)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.strip()


def test_split_sentences_handles_hindi_danda():
    sentences = split_sentences(SHORT_HI)
    assert sentences == [SHORT_HI]

    two_sentences = f"{SHORT_HI} {SHORT_HI}"
    assert split_sentences(two_sentences) == [SHORT_HI, SHORT_HI]


def test_sentence_window_short_passage_is_a_no_op():
    assert chunk_sentence_window(SHORT_EN, window_sentences=3, overlap_sentences=1) == [SHORT_EN]


def test_sentence_window_splits_long_passage_with_overlap():
    chunks = chunk_sentence_window(LONG_EN, window_sentences=3, overlap_sentences=1)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.strip()


def test_sentence_window_empty_text_returns_the_input():
    assert chunk_sentence_window("", window_sentences=3, overlap_sentences=1) == [""]


def test_fixed_size_raises_when_overlap_equals_window():
    with pytest.raises(ValueError):
        chunk_fixed_size(LONG_EN, window_words=10, overlap_words=10)


def test_fixed_size_raises_when_overlap_exceeds_window():
    with pytest.raises(ValueError):
        chunk_fixed_size(LONG_EN, window_words=10, overlap_words=15)


def test_sentence_window_raises_when_overlap_equals_window():
    with pytest.raises(ValueError):
        chunk_sentence_window(LONG_EN, window_sentences=3, overlap_sentences=3)


def test_sentence_window_raises_when_overlap_exceeds_window():
    with pytest.raises(ValueError):
        chunk_sentence_window(LONG_EN, window_sentences=3, overlap_sentences=5)
