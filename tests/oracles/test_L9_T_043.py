"""Oracle test for L9-REQ-REL-001 / L9-T-043."""
from hyai.workflow.recovery import FailureClass, RecoveryEngine, UnclassifiedFailureError
from ._support import oracle

def _good() -> bool:
    engine = RecoveryEngine()
    # Unclassified failure must raise UnclassifiedFailureError
    try:
        engine.classify_and_decide("attempt_01", RuntimeError("fail"), failure_class=None, retry_count=0)
        return False
    except UnclassifiedFailureError:
        pass
    # Classified failure succeeds and yields structured decision
    decision = engine.classify_and_decide("attempt_01", RuntimeError("timeout"), failure_class=FailureClass.TRANSIENT, retry_count=0)
    return decision.failure_class == "TRANSIENT" and decision.action == "RETRY"

def _bad() -> bool:
    return False

def test_l9_t_043():
    oracle("L9-REQ-REL-001", "L9-T-043", _good, _bad)
