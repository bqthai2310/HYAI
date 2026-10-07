"""Oracle test for L9-REQ-ADP-002 / L9-T-050."""
from hyai.adaptive.strategy import create_adaptive_strategy
from ._support import oracle

def _good() -> bool:
    strat = create_adaptive_strategy(
        strategy_id="strat_routing_heuristic",
        version=1,
        parameters={"timeout_ms": 500, "retry_limit": 2},
        target_capability="cap_codegen",
    )
    return strat.version == 1 and bool(strat.content_digest)

def _bad() -> bool:
    return False

def test_l9_t_050():
    oracle("L9-REQ-ADP-002", "L9-T-050", _good, _bad)
