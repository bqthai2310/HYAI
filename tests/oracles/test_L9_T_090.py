from hyai.compatibility import ContractRegistry
from ._support import oracle

def test_l9_t_090_event_closure():
    registry = ContractRegistry()
    oracle("L9-REQ-CTR-004", "L9-T-090", lambda: all(row["lifecycle_family"] for row in registry.entries), lambda: any(not row["lifecycle_family"] for row in registry.entries))
