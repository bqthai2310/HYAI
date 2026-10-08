"""Oracle test for L9-REQ-DAT-001 / L9-T-124."""
from hyai.workflow.data_governance import DataClass, DataRecordDescriptor
from ._support import oracle

def _good() -> bool:
    classes = [c.value for c in DataClass]
    # Exactly 6 explicit classes: CANONICAL, EVIDENCE, MEMORY, TELEMETRY, SECRETS, TRANSIENT
    assert len(classes) == 6
    desc = DataRecordDescriptor(
        record_id="rec_state_001",
        data_class="CANONICAL",
        owner="subsystem_ledger",
        storage_tier="HOT",
    )
    return desc.data_class == "CANONICAL" and desc.owner == "subsystem_ledger"

def _bad() -> bool:
    return False

def test_l9_t_124():
    oracle("L9-REQ-DAT-001", "L9-T-124", _good, _bad)
