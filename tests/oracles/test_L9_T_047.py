"""Oracle test for L9-REQ-REL-005 / L9-T-047."""
from hyai.workflow.recovery import RecoveryEngine, UncompensatedRiskError
from ._support import oracle

def _good() -> bool:
    engine = RecoveryEngine()
    # High-risk mutation without compensation must be rejected
    try:
        engine.execute_mutation("mut_delete_customer_shard", is_high_risk=True, has_compensation=False)
        return False
    except UncompensatedRiskError:
        pass
    # High-risk mutation with registered compensation succeeds
    engine.execute_mutation("mut_delete_customer_shard", is_high_risk=True, has_compensation=True)
    return True

def _bad() -> bool:
    return False

def test_l9_t_047():
    oracle("L9-REQ-REL-005", "L9-T-047", _good, _bad)
