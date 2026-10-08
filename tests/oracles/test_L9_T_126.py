"""Oracle test for L9-REQ-DAT-003 / L9-T-126."""
from hyai.workflow.data_governance import create_disaster_recovery_plan
from ._support import oracle

def _good() -> bool:
    plan = create_disaster_recovery_plan(
        dr_plan_id="drplan_core_state",
        system_scope=["CANONICAL", "EVIDENCE", "MEMORY"],
        rpo_seconds=60,
        rto_seconds=300,
        backup_refs=["backup_s3_worm_01", "backup_local_vault_01"],
        restore_procedure_ref="proc_full_restore_v2",
    )
    # Explicitly covers canonical state, evidence, and memory
    return set(plan.system_scope) == {"CANONICAL", "EVIDENCE", "MEMORY"} and len(plan.backup_refs) == 2

def _bad() -> bool:
    return False

def test_l9_t_126():
    oracle("L9-REQ-DAT-003", "L9-T-126", _good, _bad)
