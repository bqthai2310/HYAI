"""Oracle test for L9-REQ-CMP-004 / L9-T-191."""
from hyai.observability.lifecycle import TechLifecycleState, create_technology_lifecycle_entry
from ._support import oracle

def _good() -> bool:
    entry = create_technology_lifecycle_entry(
        technology_id="technology_postgres_ha",
        category="DATABASE",
        lifecycle_state=TechLifecycleState.STABLE,
        current_version="16.4",
        supported_range=">=15.0 <17.0",
        criticality="CRITICAL",
        exit_plan_ref="plan_exit_aurora_pg",
    )
    return entry.lifecycle_state == "STABLE" and entry.criticality == "CRITICAL"

def _bad() -> bool:
    return False

def test_l9_t_191():
    oracle("L9-REQ-CMP-004", "L9-T-191", _good, _bad)
