"""L9-REQ-ORG-003 / L9-T-067: Material decisions canonical."""
from hyai.memory.record import create_memory_record, MemoryKind
from ._support import oracle


def test_l9_t_067_material_decisions_canonical():
    def _pos():
        rec = create_memory_record(
            memory_id="memory_dec_001",
            scope_type="WORKSTREAM",
            scope_ref="workstream_engineering",
            source_refs=("mandate_demo",),
            provenance_refs=("prov_001",),
            statement="Adopted typed contracts for cross-department handoffs",
            authority_class="CANONICAL_REFERENCE",
            lifecycle_state="ACTIVE",
            retention_class="PROJECT_LIFETIME",
            created_by={"principal_type": "PO", "id": "po_1"},
            kind=MemoryKind.DECISION_MEMORY,
        )
        return rec["kind"] == MemoryKind.DECISION_MEMORY.value and len(rec["provenance_refs"]) > 0

    def _neg():
        try:
            rec = create_memory_record(
                memory_id="memory_dec_002",
                scope_type="WORKSTREAM",
                scope_ref="workstream_engineering",
                source_refs=(),
                provenance_refs=(),
                statement="Ad hoc unprovenanced decision",
                authority_class="UNVERIFIED",
                lifecycle_state="ACTIVE",
                retention_class="PROJECT_LIFETIME",
                created_by={"principal_type": "EXECUTOR", "id": "exec_1"},
                kind=MemoryKind.DECISION_MEMORY,
            )
            return len(rec["provenance_refs"]) == 0
        except Exception:
            return False

    oracle("L9-REQ-ORG-003", "L9-T-067", _pos, _neg)
