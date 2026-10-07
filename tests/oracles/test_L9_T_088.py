from hyai.compatibility import ContractRegistry
from ._support import oracle

def test_l9_t_088_schema_closure():
    registry = ContractRegistry()
    oracle("L9-REQ-CTR-002", "L9-T-088", lambda: all((registry.schemas_path / registry._schema_name(row["schema_path"])).is_file() for row in registry.entries), lambda: all(row["schema_path"] == "missing.schema.json" for row in registry.entries))
