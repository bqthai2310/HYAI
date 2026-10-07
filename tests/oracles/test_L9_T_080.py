"""Oracle test for L9-REQ-OBS-005 / L9-T-080."""
from hyai.observability.telemetry import SLOSpec, evaluate_slo_compliance
from ._support import oracle

def _good() -> bool:
    spec = SLOSpec(
        slo_id="slo_latency_p95",
        metric_name="http_request_duration_ms",
        target_threshold=100.0,
        comparison_operator="<=",
    )
    # Measured evidence: all within bound
    evaluation = evaluate_slo_compliance(spec, [45.0, 52.0, 60.0, 85.0])
    return evaluation.is_compliant and evaluation.measured_value <= 100.0

def _bad() -> bool:
    return False

def test_l9_t_080():
    oracle("L9-REQ-OBS-005", "L9-T-080", _good, _bad)
