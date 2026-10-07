"""Oracle test for L9-REQ-UPG-006 / L9-T-185."""
from hyai.evolution.proposal import SelfPromotionForbiddenError, create_promotion_approval
from ._support import oracle

def _good() -> bool:
    # Evolution creator/controller cannot issue its own material PromotionApproval
    try:
        create_promotion_approval(
            approval_id="promotionapproval_self_blocked",
            proposal_ref="upgradeproposal_sample",
            candidate_subject_digest={"algorithm": "sha256", "encoding": "hex", "value": "c" * 64},
            approved_scope=["scope_1"],
            tier="T1_MANAGED_COMPONENT",
            approver={"principal_type": "EVOLUTION_CONTROLLER", "id": "evo_creator_01"},
            approval_authority_ref="auth_self",
            creator_principal_id="evo_creator_01",
        )
        return False
    except SelfPromotionForbiddenError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_185():
    oracle("L9-REQ-UPG-006", "L9-T-185", _good, _bad)
