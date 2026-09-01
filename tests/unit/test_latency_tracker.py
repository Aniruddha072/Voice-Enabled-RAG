import time

from voicerag.application.latency_tracker import LatencyTracker


def test_generates_a_correlation_id_if_none_given():
    tracker = LatencyTracker()
    assert tracker.correlation_id


def test_uses_the_given_correlation_id():
    tracker = LatencyTracker(correlation_id="abc-123")
    assert tracker.correlation_id == "abc-123"


def test_track_records_stage_name_and_a_positive_duration():
    tracker = LatencyTracker()
    with tracker.track("embed"):
        time.sleep(0.01)

    assert len(tracker.stages) == 1
    assert tracker.stages[0].stage == "embed"
    assert tracker.stages[0].duration_ms >= 10


def test_total_ms_sums_every_recorded_stage():
    tracker = LatencyTracker()
    with tracker.track("a"):
        time.sleep(0.01)
    with tracker.track("b"):
        time.sleep(0.01)

    assert tracker.total_ms >= 20
    assert tracker.total_ms == sum(s.duration_ms for s in tracker.stages)
