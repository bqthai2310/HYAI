"""Oracle test for L9-REQ-UPG-003 / L9-T-182."""
from hyai.evolution.proposal import MisclassifiedTierError, UpgradeTier, create_upgrade_proposal
from ._support import oracle

def _good() -> bool:
    # Upgrade must be classified into explicit tiers T1/T2/T3
    tiers = [t.value for t in UpgradeTier]
    assert set(tiers) == {"T1_MANAGED_COMPONENT", "T2_ARCHITECTURE", "T3_CONSTITUTIONAL"}
    proposal = create_upgrade_proposal(
        upgrade_proposal_id="upgradeproposal_t2_arch",
        signal_refs=["sig_scale"],
        tier=UpgradeTier.T2_ARCHITECTURE,
        current_subject_refs=["subj_curr"],
        expected_benefit="Architecture decoupling",
    )
    return proposal.tier == "T2_ARCHITECTURE"

def _bad() -> bool:
    return False

def test_l9_t_182():
    oracle("L9-REQ-UPG-003", "L9-T-182", _good, _bad)
