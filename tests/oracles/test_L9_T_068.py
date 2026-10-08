"""L9-REQ-ORG-004 / L9-T-068: Knowledge/memory has source/provenance."""
from hyai.memory.record import create_memory_record, MemoryKind
from ._support import oracle


def test_l9_t_068_knowledge_memory_provenance():
    def _pos():
        rec = create_memory_record(
            memory_id="memory_kno_001",
            scope_type="WORKSTREAM",
            scope_ref="workstream_assurance",
            source_refs=("audit_report_v1",),
            provenance_refs=("provenance_run_99",),
            statement="Historical failure patterns in dependency resolution",
            authority_class="VERIFIED_KNOWLEDGE",
            lifecycle_state="ACTIVE",
            retention_class="PROJECT_LIFETIME",
            created_by={"principal_type": "ARCHITECT", "id": "arch_1"},
            kind=MemoryKind.LEARNING_MEMORY,
        )
        return len(rec["source_refs"]) > 0 and len(rec["provenance_refs"]) > 0

    def _neg():
        try:
            rec = create_memory_record(
                memory_id="memory_kno_002",
                scope_type="WORKSTREAM",
                scope_ref="workstream_assurance",
                source_refs=(),
                provenance_refs=(),
                statement="Unverified floating rumor",
                authority_class="UNVERIFIED",
                lifecycle_state="ACTIVE",
                retention_class="PROJECT_LIFETIME",
                created_by={"principal_type": "EXECUTOR", "id": "exec_1"},
                kind=MemoryKind.LEARNING_MEMORY,
            )
            return len(rec["provenance_refs"]) == 0
        except Exception:
            return False

    oracle("L9-REQ-ORG-004", "L9-T-068", _pos, _neg)
