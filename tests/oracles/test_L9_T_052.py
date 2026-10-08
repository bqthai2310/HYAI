"""Oracle test for L9-REQ-ADP-004 / L9-T-052."""
from hyai.adaptive.strategy import AdaptivePlane, ExplorationBudgetExceededError, create_adaptive_strategy
from ._support import oracle

def _good() -> bool:
    plane = AdaptivePlane(max_exploration_budget=50.0)
    base = create_adaptive_strategy(strategy_id="s1", version=1, parameters={"p": 1}, target_capability="cap_1")
    # Exceeding exploration budget must be rejected
    try:
        plane.adapt_strategy(base, {"p": 2}, exploration_cost=75.0)
        return False
    except ExplorationBudgetExceededError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_052():
    oracle("L9-REQ-ADP-004", "L9-T-052", _good, _bad)
