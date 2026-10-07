"""Oracle test for L9-REQ-EVO-005 / L9-T-063."""
from hyai.evolution.proposal import create_evolution_proposal
from ._support import oracle

def _good() -> bool:
    prop = create_evolution_proposal(
        proposal_id="evo_audit_invariants",
        problem="Optimize telemetry ingestion",
        evidence_refs=["ev_telemetry_load"],
        affected_invariants=["OBS-001", "OBS-002", "SEC-004"],
        proposed_change="Batch log serialization",
        expected_benefit="Reduced I/O contention",
        blast_radius="TELEMETRY_PIPELINE",
        acceptance_ref="acc_perf",
        rollback_ref="rollback_disable_batching",
    )
    # Proposal assesses affected invariants
    return set(prop.affected_invariants) == {"OBS-001", "OBS-002", "SEC-004"}

def _bad() -> bool:
    return False

def test_l9_t_063():
    oracle("L9-REQ-EVO-005", "L9-T-063", _good, _bad)
