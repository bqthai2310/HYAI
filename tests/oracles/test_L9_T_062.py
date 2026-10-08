"""Oracle test for L9-REQ-EVO-004 / L9-T-062."""
from hyai.evolution.proposal import SelfPromotionForbiddenError, create_promotion_approval
from ._support import oracle

def _good() -> bool:
    # Evolution controller cannot self-promote
    try:
        create_promotion_approval(
            approval_id="promotionapproval_self_01",
            proposal_ref="upgradeproposal_core_v2",
            candidate_subject_digest={"algorithm": "sha256", "encoding": "hex", "value": "a" * 64},
            approved_scope=["core"],
            tier="T1_MANAGED_COMPONENT",
            approver={"principal_type": "EVOLUTION_CONTROLLER", "id": "evo_lead"},
            approval_authority_ref="auth_po_delegated",
            creator_principal_id="evo_lead",
        )
        return False
    except SelfPromotionForbiddenError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_062():
    oracle("L9-REQ-EVO-004", "L9-T-062", _good, _bad)
