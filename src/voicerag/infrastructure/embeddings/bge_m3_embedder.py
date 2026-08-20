"""bge-m3 dense embeddings.

Loads the model once at construction, not per call, model load is the
slow part (downloading + reading ~2GB of weights). Only the dense
vector is used here; bge-m3 can also produce sparse and multi-vector
(ColBERT-style) representations, but hybrid retrieval is a stretch
goal, not in scope for Phase 2.

Uses CUDA when available. Measured throughput on CPU for realistic,
varied-length text was about 1 chunk/sec, which would have made
indexing this project's working sample take hours; on this machine's
6GB laptop GPU it's roughly 45 chunks/sec, see docs/decisions.md
Decision 2.2. sentence-transformers' encode() is synchronous and can
run for a while over a large batch, so it's offloaded to a thread
rather than blocking the event loop.

max_seq_length is capped at 512 tokens (bge-m3 supports up to 8,192,
but nothing in this dataset needs that much, see Decision 1.2's
passage length stats) so a rare very long passage can't blow past
available VRAM. Batch size is 32, not higher, after a batch of 128
ran a 6GB GPU out of memory partway through Phase 2 ingestion.
"""

import asyncio

import torch
from sentence_transformers import SentenceTransformer

from voicerag.domain.interfaces import Embedder

MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
MAX_SEQ_LENGTH = 512
ENCODE_BATCH_SIZE = 32


class BgeM3Embedder(Embedder):
    def __init__(self) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = SentenceTransformer(MODEL_NAME, device=device)
        self._model.max_seq_length = MAX_SEQ_LENGTH

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = await asyncio.to_thread(
            self._model.encode, texts, batch_size=ENCODE_BATCH_SIZE, show_progress_bar=False
        )
        return vectors.tolist()
