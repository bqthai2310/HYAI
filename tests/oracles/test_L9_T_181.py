"""Oracle test for L9-REQ-UPG-002 / L9-T-181."""
from hyai.evolution.proposal import UpgradeTier, create_upgrade_proposal
from ._support import oracle

def _good() -> bool:
    # Material signal cluster creates explicit UpgradeProposal with current/candidate subjects and risks
    proposal = create_upgrade_proposal(
        upgrade_proposal_id="upgradeproposal_switch_to_vector_v2",
        signal_refs=["upgradesignal_perf_drop", "upgradesignal_memory_leak"],
        tier=UpgradeTier.T1_MANAGED_COMPONENT,
        current_subject_refs=["component_vector_v1"],
        candidate_subject_refs=["component_vector_v2"],
        expected_benefit="2x recall speed and 50% memory footprint",
        material_risks=["Reindexing required", "Downtime during switch"],
        evaluation_refs=["evalrun_vector_v2_bench"],
    )
    return (
        proposal.tier == "T1_MANAGED_COMPONENT"
        and len(proposal.material_risks) == 2
        and proposal.current_subject_refs == ("component_vector_v1",)
    )

def _bad() -> bool:
    return False

def test_l9_t_181():
    oracle("L9-REQ-UPG-002", "L9-T-181", _good, _bad)
