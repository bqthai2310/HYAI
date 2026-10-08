"""Tests for the rolling latency statistics tracker."""

import pytest

from metrics.latency_stats import RollingLatencyTracker


def test_empty_tracker_raises_value_error():
    tracker = RollingLatencyTracker()

    assert tracker.count == 0
    with pytest.raises(
        ValueError, match="^Cannot compute statistics on empty buffer$"
    ):
        tracker.get_stats()


def test_single_sample_stats():
    tracker = RollingLatencyTracker()
    tracker.record(12.5)

    assert tracker.count == 1
    assert tracker.get_stats() == {
        "min": 12.5,
        "max": 12.5,
        "mean": 12.5,
        "p50": 12.5,
        "p95": 12.5,
        "p99": 12.5,
    }


@pytest.mark.parametrize(
    ("samples", "expected"),
    [
        (
            list(range(100, 0, -1)),
            {"min": 1.0, "max": 100.0, "mean": 50.5,
             "p50": 50.5, "p95": 95.05, "p99": 99.01},
        ),
        (
            [40.0, 10.0, 30.0, 20.0],
            {"min": 10.0, "max": 40.0, "mean": 25.0,
             "p50": 25.0, "p95": 38.5, "p99": 39.7},
        ),
        (
            [10.0, 0.0],
            {"min": 0.0, "max": 10.0, "mean": 5.0,
             "p50": 5.0, "p95": 9.5, "p99": 9.9},
        ),
        (
            [8.0, 2.0, 4.0],
            {"min": 2.0, "max": 8.0, "mean": 14.0 / 3,
             "p50": 4.0, "p95": 7.6, "p99": 7.92},
        ),
    ],
)
def test_multiple_samples_percentiles_accuracy(samples, expected):
    tracker = RollingLatencyTracker()
    for sample in samples:
        tracker.record(sample)

    assert tracker.get_stats() == pytest.approx(expected)
    assert tracker.count == len(samples)


def test_window_capacity_eviction_fifo():
    tracker = RollingLatencyTracker(window_size=3)
    for sample in [100.0, 1.0, 50.0]:
        tracker.record(sample)

    assert tracker.count == 3
    tracker.record(10.0)
    assert tracker.count == 3
    assert tracker.get_stats() == pytest.approx({
        "min": 1.0,
        "max": 50.0,
        "mean": 61.0 / 3,
        "p50": 10.0,
        "p95": 46.0,
        "p99": 49.2,
    })

    tracker.record(20.0)
    assert tracker.count == 3
    assert tracker.get_stats() == pytest.approx({
        "min": 10.0,
        "max": 50.0,
        "mean": 80.0 / 3,
        "p50": 20.0,
        "p95": 47.0,
        "p99": 49.4,
    })


def test_invalid_inputs_raise_value_error():
    for window_size in [0, -1, -100]:
        with pytest.raises(ValueError):
            RollingLatencyTracker(window_size=window_size)

    tracker = RollingLatencyTracker(window_size=1)
    tracker.record(5.0)
    for latency_ms in [-0.001, -1.0, -100.0]:
        with pytest.raises(ValueError):
            tracker.record(latency_ms)
        assert tracker.count == 1
        assert tracker.get_stats()["mean"] == 5.0


def test_clear_resets_tracker():
    tracker = RollingLatencyTracker(window_size=2)
    tracker.record(1.0)
    tracker.record(2.0)
    tracker.clear()

    assert tracker.count == 0
    with pytest.raises(
        ValueError, match="^Cannot compute statistics on empty buffer$"
    ):
        tracker.get_stats()

    tracker.clear()
    tracker.record(3.0)
    tracker.record(4.0)
    tracker.record(5.0)
    assert tracker.count == 2
    assert tracker.get_stats()["mean"] == 4.5


@pytest.mark.parametrize("sample", [0.0, 0.125, 7])
def test_repeated_samples_and_float_results(sample):
    tracker = RollingLatencyTracker()
    for _ in range(5):
        tracker.record(sample)

    stats = tracker.get_stats()
    assert stats == {key: float(sample) for key in [
        "min", "max", "mean", "p50", "p95", "p99"
    ]}
    assert all(isinstance(value, float) for value in stats.values())


def test_window_size_one_keeps_latest_sample():
    tracker = RollingLatencyTracker(window_size=1)
    tracker.record(10.0)
    tracker.record(0.25)

    assert tracker.count == 1
    assert all(value == 0.25 for value in tracker.get_stats().values())


def test_default_window_capacity():
    tracker = RollingLatencyTracker()
    for sample in range(1001):
        tracker.record(sample)

    assert tracker.count == 1000
    assert tracker.get_stats()["min"] == 1.0
    assert tracker.get_stats()["max"] == 1000.0


def test_get_stats_preserves_fifo_order_and_returns_independent_dict():
    tracker = RollingLatencyTracker(window_size=3)
    for sample in [100.0, 1.0, 50.0]:
        tracker.record(sample)

    stats = tracker.get_stats()
    expected = stats.copy()
    stats["min"] = -1.0
    assert tracker.get_stats() == expected
    assert tracker.count == 3

    tracker.record(10.0)
    assert tracker.get_stats()["max"] == 50.0


def test_trackers_have_independent_buffers():
    first = RollingLatencyTracker()
    second = RollingLatencyTracker()
    first.record(1.0)
    second.record(2.0)
    first.clear()

    assert first.count == 0
    assert second.count == 1
    assert second.get_stats()["mean"] == 2.0
