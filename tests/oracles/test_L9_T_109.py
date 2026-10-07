from hyai.memory import CanonicalMemoryRegistry, MemoryQuery, RegistryError, create_memory_record
from ._support import oracle


def _record(memory_id, statement, supersedes=()):
    return create_memory_record(
        memory_id=memory_id,
        kind="LEARNING_MEMORY",
        scope_type="WORKSTREAM",
        scope_ref="workstream_alpha",
        authority_class="DERIVED_OBSERVATION",
        source_refs=[f"doc://learning/{memory_id}"],
        provenance_refs=[f"run://trace/{memory_id}"],
        lifecycle_state="ACTIVE",
        retention_class="SHORT",
        created_by={"principal_type": "EXECUTOR", "id": "worker_alpha"},
        statement=statement,
        supersedes=list(supersedes),
    )


def _query():
    return MemoryQuery.create(
        query_id="memq_lifecycle_states",
        requester={"principal_type": "PO", "id": "po_alpha"},
        scope_filters=["WORKSTREAM:workstream_alpha"],
        query_text="*",
        max_items=20,
    )


def _good():
    registry = CanonicalMemoryRegistry()
    first = registry.store_record(_record("memory_lifecycle_first", "the rollout window opens on friday"))
    second = registry.supersede(first.memory_id, _record("memory_lifecycle_second", "the rollout window opens on monday", ["memory_lifecycle_first"]))
    expired = registry.store_record(_record("memory_lifecycle_third", "the sandbox quota is shared by every team"))
    registry.expire_record(expired.memory_id)
    quarantined = registry.store_record(_record("memory_lifecycle_fourth", "the vendor contract is pending signature"))
    registry.quarantine_record(quarantined.memory_id)
    deleted = registry.store_record(_record("memory_lifecycle_fifth", "the archive bucket stays private"))
    registry.tombstone(deleted.memory_id, "data subject erasure request", {"principal_type": "PO", "id": "po_alpha"})

    expected = {
        first.memory_id: "SUPERSEDED",
        second.memory_id: "ACTIVE",
        expired.memory_id: "EXPIRED",
        quarantined.memory_id: "QUARANTINED",
        deleted.memory_id: "TOMBSTONED",
    }
    if any(registry.record(memory_id).lifecycle_state != state for memory_id, state in expected.items()):
        return False
    if {record.memory_id for record in registry.active_records()} != {second.memory_id}:
        return False
    if [record.memory_id for record in registry.query(_query())] != [second.memory_id]:
        return False
    if not registry.record(deleted.memory_id).valid_until:
        return False
    for memory_id in (first.memory_id, expired.memory_id, quarantined.memory_id, deleted.memory_id):
        try:
            registry.store_record(_record(memory_id, "resurrection attempt"))
        except RegistryError:
            continue
        return False
    return True


def _bad():
    return False


def test_l9_t_109_lifecycle_transitions_without_silent_resurrection():
    oracle("L9-REQ-MEM-004", "L9-T-109", _good, _bad)
