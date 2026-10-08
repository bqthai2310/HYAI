"""Oracle test for L9-REQ-REL-003 / L9-T-045."""
from hyai.workflow.recovery import DuplicateMutationError, RecoveryEngine
from ._support import oracle

def _good() -> bool:
    engine = RecoveryEngine()
    engine.execute_mutation("mut_payment_auth_101")
    # Duplicate mutation with same idempotency key must be rejected
    try:
        engine.execute_mutation("mut_payment_auth_101")
        return False
    except DuplicateMutationError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_045():
    oracle("L9-REQ-REL-003", "L9-T-045", _good, _bad)
