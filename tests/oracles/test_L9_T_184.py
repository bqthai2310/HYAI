"""Oracle test for L9-REQ-UPG-005 / L9-T-184."""
from hyai.evolution.proposal import StaleApprovalError, create_promotion_approval
from ._support import oracle

def _good() -> bool:
    digest_original = {"algorithm": "sha256", "encoding": "hex", "value": "a" * 64}
    digest_modified = {"algorithm": "sha256", "encoding": "hex", "value": "b" * 64}
    approval = create_promotion_approval(
        approval_id="promotionapproval_candidate_digest",
        proposal_ref="upgradeproposal_sample",
        candidate_subject_digest=digest_original,
        approved_scope=["module_a"],
        tier="T1_MANAGED_COMPONENT",
        approver={"principal_type": "PO", "id": "po_main"},
        approval_authority_ref="auth_po_master",
    )
    # Binds exact candidate digest: becomes stale on changed candidate digest
    approval.assert_valid_for_candidate(digest_original)
    try:
        approval.assert_valid_for_candidate(digest_modified)
        return False
    except StaleApprovalError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_184():
    oracle("L9-REQ-UPG-005", "L9-T-184", _good, _bad)
