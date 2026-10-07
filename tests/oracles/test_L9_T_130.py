"""Oracle test for L9-REQ-DAT-007 / L9-T-130."""
from hyai.workflow.data_governance import InvalidBackupSourceError, create_disaster_recovery_plan
from ._support import oracle

def _good() -> bool:
    # Attempting to declare a derived search/vector/cache projection as canonical backup must fail
    try:
        create_disaster_recovery_plan(
            dr_plan_id="drplan_invalid",
            system_scope=["CANONICAL"],
            rpo_seconds=60,
            rto_seconds=300,
            backup_refs=["vector_store_embedding_backup"],
            restore_procedure_ref="proc_restore",
        )
        return False
    except InvalidBackupSourceError:
        pass
    try:
        create_disaster_recovery_plan(
            dr_plan_id="drplan_invalid_2",
            system_scope=["CANONICAL"],
            rpo_seconds=60,
            rto_seconds=300,
            backup_refs=["cache_redis_dump"],
            restore_procedure_ref="proc_restore",
        )
        return False
    except InvalidBackupSourceError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_130():
    oracle("L9-REQ-DAT-007", "L9-T-130", _good, _bad)
