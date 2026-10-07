from hyai.memory import (
    MemoryRecord,
    SecretMaterialError,
    classify,
    create_memory_record,
    validate_memory_record,
)
from hyai.memory.query import can_read
from ._support import oracle

SECRET_STATEMENTS = (
    "the deploy credential is AKIAIOSFODNN7EXAMPLE",
    "the archive uses -----BEGIN RSA PRIVATE KEY----- material",
    "the automation identity is ghp_0123456789ABCDEFGHIJKLMNOPQRSTUVWX",
)


def _secret_rejected(statement):
    try:
        document = create_memory_record(
            memory_id="memory_secret_material",
            kind="EVIDENCE_MEMORY",
            scope_type="TASK",
            scope_ref="task_alpha",
            authority_class="DERIVED_OBSERVATION",
            source_refs=["doc://evidence/alpha"],
            provenance_refs=["run://trace/alpha"],
            lifecycle_state="ACTIVE",
            retention_class="SHORT",
            created_by={"principal_type": "RUNTIME_WORKER", "id": "worker_alpha"},
            statement=statement,
        )
        validate_memory_record(document)
    except SecretMaterialError:
        return True
    return False


def _sensitive_record():
    return MemoryRecord.from_dict(
        create_memory_record(
            memory_id="memory_preference_beta",
            kind="USER_PREFERENCE_MEMORY",
            scope_type="PRINCIPAL",
            scope_ref="reader_beta",
            authority_class="USER_PREFERENCE",
            source_refs=["doc://preference/beta"],
            provenance_refs=["run://trace/reader_beta"],
            lifecycle_state="ACTIVE",
            retention_class="REGULATED",
            created_by={"principal_type": "PO", "id": "po_alpha"},
            statement="the beta principal prefers the dark theme",
        )
    )


def _acl_enforced():
    record = _sensitive_record()
    if classify(record) != "SENSITIVE":
        return False
    if can_read(record, {"principal_type": "RUNTIME_WORKER", "id": "worker_alpha"}):
        return False
    if not can_read(record, {"principal_type": "EXECUTOR", "id": "reader_beta"}):
        return False
    return can_read(record, {"principal_type": "PO", "id": "po_alpha"})


def _good():
    return all(_secret_rejected(statement) for statement in SECRET_STATEMENTS) and _acl_enforced()


def _bad():
    return False


def test_l9_t_113_secrets_rejected_and_acl_enforced():
    oracle("L9-REQ-MEM-008", "L9-T-113", _good, _bad)
