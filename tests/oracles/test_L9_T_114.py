from hyai.memory import (
    CanonicalMemoryRegistry,
    DataRetentionPolicy,
    MemoryTombstone,
    RegistryError,
    RetentionClass,
    create_memory_record,
    create_tombstone,
    validate_memory_tombstone,
)
from ._support import oracle


def _record(memory_id, retention_class):
    return create_memory_record(
        memory_id=memory_id,
        kind="EVIDENCE_MEMORY",
        scope_type="TASK",
        scope_ref="task_alpha",
        authority_class="DERIVED_OBSERVATION",
        source_refs=[f"doc://evidence/{memory_id}"],
        provenance_refs=[f"run://trace/{memory_id}"],
        lifecycle_state="ACTIVE",
        retention_class=retention_class,
        created_by={"principal_type": "RUNTIME_WORKER", "id": "worker_alpha"},
        statement="the evidence bundle is archived for audit",
    )


def _good():
    registry = CanonicalMemoryRegistry()
    policy = registry.register_policy(DataRetentionPolicy.for_retention_class(RetentionClass.EPHEMERAL))
    ephemeral = registry.store_record(_record("memory_retention_ephemeral", RetentionClass.EPHEMERAL.value))
    held = registry.store_record(_record("memory_retention_held", RetentionClass.LEGAL_HOLD.value))
    if not policy.covers(registry.record(ephemeral.memory_id)) or not policy.allows_purge():
        return False
    legal_hold = DataRetentionPolicy.for_retention_class(RetentionClass.LEGAL_HOLD)
    if legal_hold.allows_purge() or not legal_hold.covers(registry.record(held.memory_id)):
        return False

    tombstone = registry.tombstone(ephemeral.memory_id, "retention window elapsed", {"principal_type": "PO", "id": "po_alpha"}, purge_required=True)
    validate_memory_tombstone(tombstone)
    if registry.record(ephemeral.memory_id).lifecycle_state != "TOMBSTONED":
        return False
    held_tombstone = registry.tombstone(held.memory_id, "legal hold review", {"principal_type": "PO", "id": "po_alpha"}, purge_required=True)
    try:
        registry.purge(held.memory_id, {"principal_type": "PO", "id": "po_alpha"})
    except RegistryError:
        pass
    else:
        return False

    entry = create_tombstone(
        tombstone_id="memtomb_standalone_alpha",
        memory_id="memory_retention_standalone",
        reason="user erasure request",
        authority={"principal_type": "PO", "id": "po_alpha"},
        purge_required=True,
    )
    validate_memory_tombstone(entry)
    if not MemoryTombstone.from_dict(entry).requires_purge():
        return False

    registry.purge(ephemeral.memory_id, {"principal_type": "PO", "id": "po_alpha"})
    tombstoned_entry = next(item for item in registry.audit_log if item.get("event") == "TOMBSTONE" and item.get("memory_id") == ephemeral.memory_id)
    purged_entry = next(item for item in registry.audit_log if item.get("event") == "PURGE" and item.get("memory_id") == ephemeral.memory_id)
    if tombstoned_entry.get("policy_id") != policy.policy_id or purged_entry.get("policy_id") != policy.policy_id:
        return False
    if tombstoned_entry.get("policy_digest") != dict(policy.content_digest):
        return False
    if held_tombstone.requires_purge() and registry.record(held.memory_id).lifecycle_state != "TOMBSTONED":
        return False
    return registry.record(ephemeral.memory_id) is None and {item.memory_id for item in registry.tombstones} == {held.memory_id, ephemeral.memory_id}


def _bad():
    return False


def test_l9_t_114_retention_tombstone_and_purge_are_auditable():
    oracle("L9-REQ-MEM-009", "L9-T-114", _good, _bad)
