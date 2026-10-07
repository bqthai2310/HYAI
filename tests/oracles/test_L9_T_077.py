"""Oracle test for L9-REQ-OBS-002 / L9-T-077."""
from hyai.observability.telemetry import StructuredLogRecord, StructuredMetricRecord, TraceContext
from ._support import oracle

def _good() -> bool:
    ctx = TraceContext("goal_1", "prog_1", "task_1", "att_1", "tr_1", "sp_1")
    log = StructuredLogRecord("2026-10-08T00:00:00Z", "INFO", "service started", ctx, {"env": "prod"})
    metric = StructuredMetricRecord("latency_ms", "HISTOGRAM", 45.2, "2026-10-08T00:00:00Z", ctx, {"endpoint": "/v1/run"})
    return log.to_dict()["trace_context"]["goal_id"] == "goal_1" and metric.to_dict()["value"] == 45.2

def _bad() -> bool:
    return False

def test_l9_t_077():
    oracle("L9-REQ-OBS-002", "L9-T-077", _good, _bad)
