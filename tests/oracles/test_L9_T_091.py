from hyai.compatibility import ContractRegistry
from ._support import oracle

def test_l9_t_091_no_orphan_schema():
    registry = ContractRegistry()
    registered = {registry._schema_name(row["schema_path"]) for row in registry.entries}
    oracle("L9-REQ-CTR-005", "L9-T-091", lambda: all(path.name in registered or path.name in registry._HELPERS for path in registry.schemas_path.glob("*.schema.json")), lambda: "not_registered.schema.json" in registered)
