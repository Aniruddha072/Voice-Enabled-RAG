from voicerag.application.chunking.fixed_size import chunk_fixed_size
from voicerag.application.chunking.passage_as_chunk import chunk_passage_as_chunk
from voicerag.application.chunking.sentence_window import chunk_sentence_window

STRATEGIES = {
    "passage_as_chunk": chunk_passage_as_chunk,
    "fixed_size": chunk_fixed_size,
    "sentence_window": chunk_sentence_window,
}
