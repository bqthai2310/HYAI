from hyai.memory import (
    CanonicalMemoryRegistry,
    MemoryContextItem,
    MemoryQuery,
    create_memory_record,
    validate_memory_context_bundle,
)
from ._support import oracle


def _record(memory_id, statement):
    return create_memory_record(
        memory_id=memory_id,
        kind="EVIDENCE_MEMORY",
        scope_type="WORKSTREAM",
        scope_ref="workstream_alpha",
        authority_class="VERIFIED_KNOWLEDGE",
        source_refs=[f"doc://evidence/{memory_id}"],
        provenance_refs=[f"run://trace/{memory_id}"],
        lifecycle_state="ACTIVE",
        retention_class="SHORT",
        created_by={"principal_type": "ARCHITECT", "id": "architect_alpha"},
        statement=statement,
    )


def _query():
    return MemoryQuery.create(
        query_id="memq_context_receipt",
        requester={"principal_type": "PO", "id": "po_alpha"},
        scope_filters=["WORKSTREAM:workstream_alpha"],
        query_text="*",
        max_items=10,
    )


def _good():
    registry = CanonicalMemoryRegistry()
    registry.store_record(_record("memory_context_alpha", "the sandbox cluster runs in region alpha"))
    registry.store_record(_record("memory_context_beta", "the release checklist has five gates"))
    records = registry.query(_query())
    if len(records) != 2:
        return False

    bundle = registry.assemble_context_bundle(_query(), records, created_at="2026-01-02T03:04:05Z")
    if validate_memory_context_bundle(bundle).bundle_id != bundle.bundle_id:
        return False
    items = {item.memory_id: item.revision_or_digest for item in bundle.memory_items}
    if len(items) != len(records):
        return False
    for record in records:
        if items.get(record.memory_id) != record.content_digest["value"]:
            return False
        if MemoryContextItem.for_record(record).revision_or_digest != record.revision:
            return False
    if any(item["memory_id"] not in items or item["revision_or_digest"] != items[item["memory_id"]] for item in bundle.receipt()):
        return False
    return True


def _bad():
    return False


def test_l9_t_110_context_bundle_tracks_exact_refs_and_revisions():
    oracle("L9-REQ-MEM-005", "L9-T-110", _good, _bad)
