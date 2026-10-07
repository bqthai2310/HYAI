"""Security governance controls used at trust and change boundaries."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

from hyai.constitution.authority import Principal, PrincipalType

_SECRET_KEY = re.compile(r"(?:api[_-]?key|secret|token|password|credential|private[_-]?key)", re.I)
_SECRET_VALUE = re.compile(
    r"(?:[spr]k-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]{8,})",
    re.I,
)
_PROTECTED = (".github", "ROOT_LAYOUT_MANIFEST.json", "schemas", "policies")


@dataclass(frozen=True)
class WorkerGrant:
    worker_id: str
    requested: frozenset[str]
    granted: frozenset[str]
    allowed: frozenset[str]


def enforce_least_privilege(grant: WorkerGrant) -> tuple[bool, str]:
    if not grant.granted <= grant.requested or not grant.granted <= grant.allowed:
        return False, "grant exceeds requested or allowed privileges"
    return True, "least privilege satisfied"


def contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_SECRET_VALUE.search(value))
    if isinstance(value, Mapping):
        # A sensitive field name is not itself a leak after its value has been
        # replaced with the explicit redaction marker.
        return any(
            (_SECRET_KEY.search(str(key)) is not None and item is not None and item != "" and item != "[REDACTED]")
            or contains_secret(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(contains_secret(item) for item in value)
    return False


def redact_secrets(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    if isinstance(value, Mapping):
        return {key: "[REDACTED]" if _SECRET_KEY.search(str(key)) else redact_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value


def validate_untrusted_boundary(content: Mapping[str, Any], trusted: bool = False) -> tuple[bool, str]:
    authority_keys = {"authority", "authority_request", "principal", "role", "system_instruction", "control"}
    def attempts_authority(value: Any) -> bool:
        if isinstance(value, Mapping):
            return bool(authority_keys.intersection(value)) or any(attempts_authority(item) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(attempts_authority(item) for item in value)
        return False
    if not trusted and attempts_authority(content):
        return False, "untrusted content cannot acquire control authority"
    return True, "trust boundary preserved"


def is_protected_path(path: str) -> bool:
    normalized = PurePosixPath(path.replace("\\", "/"))
    return any(str(normalized) == item or item in normalized.parts for item in _PROTECTED)


def validate_protected_changes(paths: Iterable[str], authority: Principal | Mapping[str, Any]) -> tuple[bool, str]:
    actor = authority if isinstance(authority, Principal) else Principal(authority["principal_type"], authority["id"])
    if any(is_protected_path(path) for path in paths) and actor.principal_type not in {PrincipalType.ARCHITECT, PrincipalType.PO}:
        return False, "protected paths require ARCHITECT or PO authority"
    return True, "protected path authority valid"


def validate_audit_record(record: Mapping[str, Any]) -> tuple[bool, str]:
    required = {"action", "actor", "timestamp", "evidence_refs"}
    if not required <= record.keys() or not record["evidence_refs"] or contains_secret(record):
        return False, "security action is not attributable or contains secret material"
    return True, "auditable"
