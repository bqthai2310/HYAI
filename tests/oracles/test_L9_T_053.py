"""Oracle test for L9-REQ-ADP-005 / L9-T-053."""
from hyai.adaptive.strategy import AdaptivePlane, IrreversibleAdaptationError, create_adaptive_strategy
from ._support import oracle

def _good() -> bool:
    plane = AdaptivePlane()
    base = create_adaptive_strategy(strategy_id="s1", version=1, parameters={"k": 10}, target_capability="cap_1")
    # Irreversible adaptation must be rejected
    try:
        plane.adapt_strategy(base, {"k": 20}, reversible=False)
        return False
    except IrreversibleAdaptationError:
        pass
    # Reversible adaptation allows rollback
    adapted = plane.adapt_strategy(base, {"k": 20}, reversible=True)
    rolled_back = plane.rollback()
    return rolled_back.version == 1 and rolled_back.parameters == {"k": 10}

def _bad() -> bool:
    return False

def test_l9_t_053():
    oracle("L9-REQ-ADP-005", "L9-T-053", _good, _bad)
