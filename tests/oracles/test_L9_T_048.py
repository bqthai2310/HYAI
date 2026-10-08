"""Oracle test for L9-REQ-REL-006 / L9-T-048."""
from hyai.workflow.recovery import NoProgressDetectedError, RecoveryEngine
from ._support import oracle

def _good() -> bool:
    engine = RecoveryEngine()
    engine.record_progress_state("hash_state_alpha")
    engine.record_progress_state("hash_state_beta")
    engine.record_progress_state("hash_state_stuck")
    engine.record_progress_state("hash_state_stuck")
    # 3 consecutive identical states must detect no-progress and escalate
    try:
        engine.record_progress_state("hash_state_stuck")
        return False
    except NoProgressDetectedError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_048():
    oracle("L9-REQ-REL-006", "L9-T-048", _good, _bad)
