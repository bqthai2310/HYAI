from hyai.compatibility import ContractRegistry
from ._support import oracle

def test_l9_t_087_contract_registry():
    registry = ContractRegistry()
    oracle("L9-REQ-CTR-001", "L9-T-087", lambda: registry.validate_registry_closure()[0], lambda: len({row["object_name"] for row in registry.entries}) != len(registry.entries))
