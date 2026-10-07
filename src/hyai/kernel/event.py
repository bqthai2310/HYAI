"""Audit event envelope emitted by the sovereign kernel."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from hyai.constitution.authority import Principal


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _principal(value: Principal | Mapping[str, Any]) -> dict[str, str]:
    if isinstance(value, Principal):
        return {"principal_type": value.principal_type.value, "id": value.id}
    return {"principal_type": str(value["principal_type"]), "id": str(value["id"])}


def _schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / "schemas" / "event_envelope.schema.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    producer: Principal | Mapping[str, Any]
    aggregate_type: str
    aggregate_id: str
    aggregate_revision: int
    correlation_id: str
    payload: Mapping[str, Any]
    payload_digest: Mapping[str, str]
    schema_version: str = "2.0.0"
    occurred_at: str = field(default_factory=_utc_now)
    causation_id: str | None = None
    policy_snapshot_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["producer"] = _principal(self.producer)
        value["payload"] = dict(self.payload)
        value["payload_digest"] = dict(self.payload_digest)
        return value

    def validate(self) -> bool:
        errors = list(Draft202012Validator(_schema(), format_checker=FormatChecker()).iter_errors(self.to_dict()))
        if errors:
            raise ValueError("event envelope invalid: " + "; ".join(error.message for error in errors))
        return True
