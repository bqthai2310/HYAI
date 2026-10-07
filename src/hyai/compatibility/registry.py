"""Contract matrix loader and closure validation."""
from __future__ import annotations

import csv
from pathlib import Path


class ContractRegistry:
    """Read the frozen canonical object/schema/event matrix."""

    _HELPERS = {"common.digest.schema.json", "common.principal.schema.json"}

    def __init__(self, matrix_path: str | Path | None = None, schemas_path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[3]
        self.matrix_path = Path(matrix_path) if matrix_path else Path(__file__).with_name("contract_matrix.csv")
        self.schemas_path = Path(schemas_path) if schemas_path else root / "schemas"
        with self.matrix_path.open("r", encoding="utf-8", newline="") as source:
            self.entries = list(csv.DictReader(source))

    @staticmethod
    def _schema_name(schema_path: str) -> str:
        return Path(schema_path.replace("\\", "/")).name

    def validate_registry_closure(self) -> tuple[bool, str]:
        """Validate CTR-001 through CTR-005 and return an actionable result."""
        errors: list[str] = []
        names = [row.get("object_name", "") for row in self.entries]
        if any(not name for name in names) or len(names) != len(set(names)):
            errors.append("CTR-001: canonical object must have exactly one registry entry")
        if any(not row.get("owner", "").strip() for row in self.entries):
            errors.append("CTR-001: canonical object must have exactly one owner")
        for row in self.entries:
            schema_file = self.schemas_path / self._schema_name(row.get("schema_path", ""))
            if not schema_file.is_file():
                errors.append(f"CTR-002: missing schema {row.get('schema_path')}")
            if not row.get("writer_commands", "").strip():
                errors.append(f"CTR-003: missing writer_commands for {row.get('object_name')}")
            if not row.get("lifecycle_family", "").strip():
                errors.append(f"CTR-004: missing lifecycle_family for {row.get('object_name')}")
        registered = {self._schema_name(row.get("schema_path", "")) for row in self.entries}
        present = {path.name for path in self.schemas_path.glob("*.schema.json")} - self._HELPERS
        orphaned = present - registered
        if orphaned:
            errors.append("CTR-005: unregistered schema(s): " + ", ".join(sorted(orphaned)))
        return (not errors, "; ".join(errors) if errors else "registry closure valid")
