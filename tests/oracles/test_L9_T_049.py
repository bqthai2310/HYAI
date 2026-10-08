"""Oracle test for L9-REQ-ADP-001 / L9-T-049."""
from hyai.adaptive.strategy import AdaptivePlane
from ._support import oracle

def _good() -> bool:
    plane = AdaptivePlane()
    plane.record_telemetry({"metric": "error_rate", "value": 0.05, "source": "evalrun_1"})
    return len(plane._telemetry_samples) == 1

def _bad() -> bool:
    return False

def test_l9_t_049():
    oracle("L9-REQ-ADP-001", "L9-T-049", _good, _bad)
