"""Oracle test for L9-REQ-ADP-003 / L9-T-051."""
from hyai.adaptive.strategy import AdaptivePlane, ConstitutionImmutableError, create_adaptive_strategy
from ._support import oracle

def _good() -> bool:
    plane = AdaptivePlane()
    base = create_adaptive_strategy(strategy_id="s1", version=1, parameters={"timeout": 100}, target_capability="cap_1")
    # Adaptation attempting to modify Constitution or acceptance baselines must be rejected
    try:
        plane.adapt_strategy(base, proposed_parameters={"timeout": 100, "constitution": "modified"})
        return False
    except ConstitutionImmutableError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_051():
    oracle("L9-REQ-ADP-003", "L9-T-051", _good, _bad)
