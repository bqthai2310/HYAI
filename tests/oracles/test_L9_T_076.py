"""Oracle test for L9-REQ-OBS-001 / L9-T-076."""
from hyai.observability.telemetry import CorrelationError, TraceContext
from ._support import oracle

def _good() -> bool:
    ctx = TraceContext(
        goal_id="goal_100",
        program_id="program_alpha",
        task_id="task_build_binary",
        attempt_id="attempt_01",
        trace_id="tr_123456",
        span_id="sp_987654",
    )
    assert ctx.goal_id == "goal_100" and ctx.task_id == "task_build_binary"
    # Missing required correlation dimensions must be rejected
    try:
        TraceContext(
            goal_id="",
            program_id="program_alpha",
            task_id="task_build_binary",
            attempt_id="attempt_01",
            trace_id="tr_123456",
            span_id="sp_987654",
        )
        return False
    except CorrelationError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_076():
    oracle("L9-REQ-OBS-001", "L9-T-076", _good, _bad)
