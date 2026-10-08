"""Oracle test for L9-REQ-EVO-001 / L9-T-059."""
from hyai.evolution.proposal import create_evolution_proposal
from ._support import oracle

def _good() -> bool:
    prop = create_evolution_proposal(
        proposal_id="evo_upgrade_memory_retrieval",
        problem="Context saturation causes recall degradation",
        evidence_refs=["ev_memory_saturation_log"],
        affected_invariants=["MEM-003", "MEM-005"],
        proposed_change="Add hierarchical indexing to memory registry",
        expected_benefit="3x faster recall with sub-linear memory growth",
        blast_radius="MEMORY_SUBSYSTEM_ONLY",
        acceptance_ref="acc_evalspec_hierarchical_mem",
        rollback_ref="rollback_revert_index_patch",
    )
    return prop.proposal_id == "evo_upgrade_memory_retrieval" and prop.reversibility == "REVERSIBLE"

def _bad() -> bool:
    return False

def test_l9_t_059():
    oracle("L9-REQ-EVO-001", "L9-T-059", _good, _bad)
