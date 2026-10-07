"""Small shared helpers for schema-backed, content-addressed records."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from hyai.compatibility.crypto import compute_digest


class ContractValidationError(ValueError):
    """Raised when a kernel record does not satisfy its declared contract."""


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def schema(name: str) -> dict[str, Any]:
    return json.loads((repository_root() / "schemas" / name).read_text(encoding="utf-8"))


def validate(document: Mapping[str, Any], schema_name: str, error_type: type[ValueError] = ContractValidationError) -> None:
    errors = list(Draft202012Validator(schema(schema_name), format_checker=FormatChecker()).iter_errors(dict(document)))
    if errors:
        raise error_type("; ".join(error.message for error in errors))


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_digest(document: Mapping[str, Any]) -> dict[str, str]:
    material = {key: value for key, value in document.items() if key != "content_digest"}
    return compute_digest(canonical(material))


def timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


sha256_digest = compute_digest
