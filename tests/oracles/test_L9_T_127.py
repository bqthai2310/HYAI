"""Oracle test for L9-REQ-DAT-004 / L9-T-127."""
from hyai.workflow.data_governance import create_disaster_recovery_plan
from ._support import oracle

def _good() -> bool:
    plan = create_disaster_recovery_plan(
        dr_plan_id="drplan_prod_db",
        system_scope=["CANONICAL"],
        rpo_seconds=30,
        rto_seconds=120,
        backup_refs=["backup_stream_wal"],
        restore_procedure_ref="proc_pitr",
    )
    # Declares explicit non-zero bounded RPO and RTO
    return plan.rpo_seconds == 30 and plan.rto_seconds == 120

def _bad() -> bool:
    return False

def test_l9_t_127():
    oracle("L9-REQ-DAT-004", "L9-T-127", _good, _bad)
