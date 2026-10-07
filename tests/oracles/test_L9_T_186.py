"""Oracle test for L9-REQ-UPG-007 / L9-T-186."""
from hyai.evolution.canary import CanaryExecutionError, EvolutionRolloutManager, create_canary_plan
from ._support import oracle

def _good() -> bool:
    mgr = EvolutionRolloutManager()
    plan = create_canary_plan(
        canary_id="canary_upgrade_gated",
        subject_ref="subject_candidate",
        success_thresholds=["error_rate <= 0.02"],
        failure_thresholds=["error_rate > 0.05"],
        rollback_ref="rollback_procedure_revert",
    )
    # Canary failure triggers automated rollback
    try:
        mgr.evaluate_canary_and_execute(plan, measured_error_rate=0.08, error_rate_threshold=0.05)
        return False
    except CanaryExecutionError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_186():
    oracle("L9-REQ-UPG-007", "L9-T-186", _good, _bad)
