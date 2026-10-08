"""Oracle test for L9-REQ-OBS-004 / L9-T-079."""
from hyai.observability.finops import BudgetChecker, BudgetExceededError, create_budget_envelope
from ._support import oracle

def _good() -> bool:
    envelope = create_budget_envelope(
        budget_envelope_id="budget_task_hard_cap",
        limits={"llm_tokens": 5000.0, "compute_dollars": 20.0},
        currency="USD",
        hard_stop_on_exceed=True,
    )
    checker = BudgetChecker(envelope)
    checker.check_and_reserve("llm_tokens", 3000.0)
    # Exceeding hard limit must raise BudgetExceededError
    try:
        checker.check_and_reserve("llm_tokens", 2500.0)
        return False
    except BudgetExceededError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_079():
    oracle("L9-REQ-OBS-004", "L9-T-079", _good, _bad)
