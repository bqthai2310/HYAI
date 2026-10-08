"""Statistics for a bounded window of latency measurements."""

from collections import deque
from statistics import fmean


class RollingLatencyTracker:
    """Track the most recent latency samples, measured in milliseconds."""

    def __init__(self, window_size: int = 1000) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be greater than zero")
        self._buffer: deque[float] = deque(maxlen=window_size)

    def record(self, latency_ms: float) -> None:
        """Add a sample, evicting the oldest one when the window is full."""
        if latency_ms < 0:
            raise ValueError("latency_ms must be nonnegative")
        self._buffer.append(float(latency_ms))

    def get_stats(self) -> dict[str, float]:
        """Return statistics using linearly interpolated percentiles.

        For percentile fraction p, interpolate at index (n - 1) * p in
        the sorted samples (the standard inclusive, or type 7, definition).
        """
        if not self._buffer:
            raise ValueError("Cannot compute statistics on empty buffer")

        samples = sorted(self._buffer)

        def percentile(fraction: float) -> float:
            position = (len(samples) - 1) * fraction
            lower = int(position)
            upper = min(lower + 1, len(samples) - 1)
            weight = position - lower
            return samples[lower] + (samples[upper] - samples[lower]) * weight

        return {
            "min": samples[0],
            "max": samples[-1],
            "mean": fmean(samples),
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        }

    @property
    def count(self) -> int:
        """Return the number of samples currently in the window."""
        return len(self._buffer)

    def clear(self) -> None:
        """Remove all recorded samples."""
        self._buffer.clear()
