"""Command envelope used by the small sovereign kernel."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from hyai.constitution.authority import Principal


def _principal(value: Principal | Mapping[str, Any]) -> dict[str, str]:
    if isinstance(value, Principal):
        return {"principal_type": value.principal_type.value, "id": value.id}
    return {"principal_type": str(value["principal_type"]), "id": str(value["id"])}


def _schema(name: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / "schemas" / name).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class CommandEnvelope:
    command_id: str
    command_type: str
    target: str
    expected_revision: int
    actor: Principal | Mapping[str, Any]
    authority_envelope_id: str
    policy_snapshot_id: str
    idempotency_key: str
    correlation_id: str
    payload: Mapping[str, Any]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["actor"] = _principal(self.actor)
        value["payload"] = dict(self.payload)
        return value

    def validate(self) -> bool:
        """Raise ``ValueError`` unless this is a valid frozen command contract."""
        errors = list(Draft202012Validator(_schema("command_envelope.schema.json")).iter_errors(self.to_dict()))
        if errors:
            raise ValueError("command envelope invalid: " + "; ".join(error.message for error in errors))
        return True
