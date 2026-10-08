"""Oracle test for L9-REQ-UPG-008 / L9-T-187."""
from hyai.evolution.canary import EvolutionRolloutManager
from hyai.evolution.proposal import create_promotion_approval
from ._support import oracle

def _good() -> bool:
    mgr = EvolutionRolloutManager()
    digest = {"algorithm": "sha256", "encoding": "hex", "value": "d" * 64}
    approval = create_promotion_approval(
        approval_id="promotionapproval_provenance_check",
        proposal_ref="upgradeproposal_v3",
        candidate_subject_digest=digest,
        approved_scope=["scope_v3"],
        tier="T1_MANAGED_COMPONENT",
        approver={"principal_type": "PO", "id": "po_main"},
        approval_authority_ref="auth_po_master",
    )
    mgr.stage_candidate_in_sandbox("cand_v3", {"version": "3.0.0"})
    provenance = mgr.promote_candidate("cand_v3", approval=approval, candidate_digest=digest)
    # Promoted upgrade records decision, evidence, migration, and version lineage
    return (
        provenance.decision_ref == "promotionapproval_provenance_check"
        and provenance.outcome == "PROMOTED"
        and provenance.prior_version == "2.0.0"
        and provenance.new_version == "2.1.0"
    )

def _bad() -> bool:
    return False

def test_l9_t_187():
    oracle("L9-REQ-UPG-008", "L9-T-187", _good, _bad)
