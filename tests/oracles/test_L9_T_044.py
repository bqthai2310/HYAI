"""Oracle test for L9-REQ-REL-002 / L9-T-044."""
from hyai.workflow.recovery import FailureClass, RecoveryEngine, RetryBudgetExhaustedError
from ._support import oracle

def _good() -> bool:
    engine = RecoveryEngine(max_retries=2, max_budget_credits=5.0)
    # 1. Retry count exceeded
    try:
        engine.classify_and_decide("attempt_01", RuntimeError("err"), failure_class=FailureClass.TRANSIENT, retry_count=2)
        return False
    except RetryBudgetExhaustedError:
        pass
    # 2. Credit budget exceeded
    try:
        engine.classify_and_decide("attempt_02", RuntimeError("err"), failure_class=FailureClass.TRANSIENT, retry_count=1, credits_spent=5.5)
        return False
    except RetryBudgetExhaustedError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_044():
    oracle("L9-REQ-REL-002", "L9-T-044", _good, _bad)
