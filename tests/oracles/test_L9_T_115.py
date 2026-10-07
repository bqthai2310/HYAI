from hyai.memory import CanonicalMemoryRegistry, MemoryQuery, RegistryError, create_memory_record
from ._support import oracle


def _record(memory_id):
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
        statement="the deployment pipeline runs nightly",
    )


def _query():
    return MemoryQuery.create(
        query_id="memq_restore_index",
        requester={"principal_type": "ASSURANCE_SERVICE", "id": "assurance_alpha"},
        scope_filters=["WORKSTREAM:workstream_alpha"],
        query_text="*",
        max_items=10,
    )


def _good():
    registry = CanonicalMemoryRegistry()
    kept = registry.store_record(_record("memory_restore_kept"))
    removed = registry.store_record(_record("memory_restore_removed"))
    registry.tombstone(removed.memory_id, "erasure request", {"principal_type": "PO", "id": "po_alpha"})
    before = [record.memory_id for record in registry.query(_query())]

    state = registry.export_state()
    if not isinstance(state, dict) or not isinstance(state["records"], list):
        return False
    if "state_digest" not in state or state["derived_index_included"] is not False:
        return False

    restored = CanonicalMemoryRegistry().restore_state(state)
    if [record.memory_id for record in restored.query(_query())] != before:
        return False
    if {record.memory_id for record in restored.active_records()} != {kept.memory_id}:
        return False
    if restored.record(removed.memory_id).lifecycle_state != "TOMBSTONED":
        return False
    if {item.memory_id for item in restored.tombstones} != {item.memory_id for item in registry.tombstones}:
        return False
    if restored.record(kept.memory_id).content_digest != kept.content_digest:
        return False
    try:
        restored.store_record(_record(removed.memory_id))
    except RegistryError:
        return True
    return False


def _bad():
    return False


def test_l9_t_115_canonical_memory_survives_restore_without_resurrection():
    oracle("L9-REQ-MEM-010", "L9-T-115", _good, _bad)
