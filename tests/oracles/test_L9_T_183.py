"""Oracle test for L9-REQ-UPG-004 / L9-T-183."""
from hyai.evolution.canary import EvolutionRolloutManager, PrematurePromotionError
from ._support import oracle

def _good() -> bool:
    mgr = EvolutionRolloutManager()
    mgr.stage_candidate_in_sandbox("cand_v2", {"files": ["new.py"]})
    # HYAI may build/sandbox candidate, but promoting without approval must be rejected
    try:
        mgr.promote_candidate("cand_v2", approval=None, candidate_digest={"algorithm": "sha256", "encoding": "hex", "value": "a"*64})
        return False
    except PrematurePromotionError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_183():
    oracle("L9-REQ-UPG-004", "L9-T-183", _good, _bad)
