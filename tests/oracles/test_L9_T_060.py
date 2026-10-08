"""Oracle test for L9-REQ-EVO-002 / L9-T-060."""
from hyai.evolution.canary import EvolutionRolloutManager
from ._support import oracle

def _good() -> bool:
    mgr = EvolutionRolloutManager()
    mgr.stage_candidate_in_sandbox("cand_kernel_opt", {"patch": "diff --git a..."})
    cand = mgr._isolated_candidates["cand_kernel_opt"]
    # Candidate isolated in sandbox before production
    return cand["is_sandboxed"] and not cand["is_promoted"]

def _bad() -> bool:
    return False

def test_l9_t_060():
    oracle("L9-REQ-EVO-002", "L9-T-060", _good, _bad)
