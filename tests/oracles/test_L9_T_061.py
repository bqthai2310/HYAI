"""Oracle test for L9-REQ-EVO-003 / L9-T-061."""
from hyai.evolution.canary import create_canary_plan
from ._support import oracle

def _good() -> bool:
    plan = create_canary_plan(
        canary_id="canary_fast_parser",
        subject_ref="subject_parser_v2",
        scope=["dept_analysis"],
        success_thresholds=["error_rate <= 0.01", "p95_latency <= 200ms"],
        failure_thresholds=["error_rate > 0.05", "5xx_count > 10"],
        rollback_ref="rollback_revert_fast_parser",
    )
    # Canary has explicit predeclared metrics and rollback ref
    return len(plan.success_thresholds) == 2 and plan.rollback_ref == "rollback_revert_fast_parser"

def _bad() -> bool:
    return False

def test_l9_t_061():
    oracle("L9-REQ-EVO-003", "L9-T-061", _good, _bad)
