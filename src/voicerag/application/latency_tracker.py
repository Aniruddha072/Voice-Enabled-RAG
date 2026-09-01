"""Per-request correlation ID and per-stage timing.

Just the timing/correlation primitive, not a logging system itself.
Structured logging (later in this phase) and the eventual latency
benchmark script both build on this rather than timing things
separately.
"""

import time
import uuid
from contextlib import contextmanager

from pydantic import BaseModel


class StageTiming(BaseModel):
    stage: str
    duration_ms: float


class LatencyTracker:
    def __init__(self, correlation_id: str | None = None) -> None:
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.stages: list[StageTiming] = []

    @contextmanager
    def track(self, stage: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.stages.append(StageTiming(stage=stage, duration_ms=duration_ms))

    @property
    def total_ms(self) -> float:
        return sum(s.duration_ms for s in self.stages)
