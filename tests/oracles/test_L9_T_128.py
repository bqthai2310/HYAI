"""Oracle test for L9-REQ-DAT-005 / L9-T-128."""
from hyai.workflow.data_governance import RestoreDrill, RestoreDrillVerificationError, create_disaster_recovery_plan
from ._support import oracle

def _good() -> bool:
    plan = create_disaster_recovery_plan(
        dr_plan_id="drplan_ledger",
        system_scope=["CANONICAL"],
        rpo_seconds=60,
        rto_seconds=300,
        backup_refs=["backup_snap_01"],
        restore_procedure_ref="proc_restore",
    )
    drill = RestoreDrill(plan)
    canonical_data = b"canonical_state_bytes_block_1000"
    # Successful restore drill with identical payload
    res = drill.execute_drill(canonical_data, canonical_data)
    assert res.get("status") == "PASS"
    # Corrupted restore must fail verification
    try:
        drill.execute_drill(canonical_data, b"corrupted_restore_payload")
        return False
    except RestoreDrillVerificationError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_128():
    oracle("L9-REQ-DAT-005", "L9-T-128", _good, _bad)
