"""Oracle test for L9-REQ-EVO-006 / L9-T-064."""
from hyai.evolution.canary import EvolutionRolloutManager, HiddenNegativeEvidenceError
from hyai.evolution.proposal import create_promotion_approval
from ._support import oracle

def _good() -> bool:
    mgr = EvolutionRolloutManager()
    mgr.stage_candidate_in_sandbox("cand_risky", {"code": "new_code"})
    digest = {"algorithm": "sha256", "encoding": "hex", "value": "e" * 64}
    approval = create_promotion_approval(
        approval_id="promotionapproval_valid",
        proposal_ref="upgradeproposal_sample",
        candidate_subject_digest=digest,
        approved_scope=["sample"],
        tier="T1_MANAGED_COMPONENT",
        approver={"principal_type": "PO", "id": "po_main"},
        approval_authority_ref="auth_po_master",
    )
    # Cannot promote while hiding negative evidence
    try:
        mgr.promote_candidate(
            candidate_id="cand_risky",
            approval=approval,
            candidate_digest=digest,
            negative_signals=["regression_alert_high_memory_leak"],
        )
        return False
    except HiddenNegativeEvidenceError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_064():
    oracle("L9-REQ-EVO-006", "L9-T-064", _good, _bad)
