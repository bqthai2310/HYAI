from hyai.memory import CanonicalMemoryRegistry, MemoryQuery, create_memory_record
from ._support import oracle


def _record(memory_id, statement):
    return create_memory_record(
        memory_id=memory_id,
        kind="DECISION_MEMORY",
        scope_type="PRODUCT",
        scope_ref="product_alpha",
        authority_class="VERIFIED_KNOWLEDGE",
        source_refs=[f"doc://decision/{memory_id}"],
        provenance_refs=[f"run://trace/{memory_id}"],
        lifecycle_state="ACTIVE",
        retention_class="SHORT",
        created_by={"principal_type": "ARCHITECT", "id": "architect_alpha"},
        statement=statement,
    )


def _query():
    return MemoryQuery.create(
        query_id="memq_contradiction_alpha",
        requester={"principal_type": "PO", "id": "po_alpha"},
        scope_filters=["PRODUCT:product_alpha"],
        query_text="delivery gate",
        max_items=10,
    )


def _good():
    registry = CanonicalMemoryRegistry()
    left = registry.store_record(_record("memory_gate_enabled", "the delivery gate is enabled"))
    right = registry.store_record(_record("memory_gate_disabled", "the delivery gate is not enabled"))
    contradictions = registry.contradictions
    if len(contradictions) != 1:
        return False
    contradiction = contradictions[0]
    if contradiction.status != "UNRESOLVED" or contradiction.kind != "MEMORY_CONTRADICTION":
        return False
    if set(contradiction.memory_ids) != {left.memory_id, right.memory_id}:
        return False
    result = registry.search(_query())
    if {record.memory_id for record in result.records} != {left.memory_id, right.memory_id}:
        return False
    if [item.contradiction_id for item in result.unresolved_contradictions] != [contradiction.contradiction_id]:
        return False
    return registry.record(left.memory_id) is not None and registry.record(right.memory_id) is not None


def _bad():
    return False


def test_l9_t_111_conflicting_memories_stay_explicit():
    oracle("L9-REQ-MEM-006", "L9-T-111", _good, _bad)
