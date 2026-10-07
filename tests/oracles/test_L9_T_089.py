from hyai.compatibility import ContractRegistry
from ._support import oracle

def test_l9_t_089_writer_closure():
    registry = ContractRegistry()
    oracle("L9-REQ-CTR-003", "L9-T-089", lambda: all(row["writer_commands"] for row in registry.entries), lambda: any(not row["writer_commands"] for row in registry.entries))
