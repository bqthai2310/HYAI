"""Schema-backed durable memory records with secret and poisoning defenses."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest, validate_digest_spec
from hyai.constitution.authority import Principal, PrincipalType


__all__ = [
    "AUTHORITY_RANK",
    "AuthorityClass",
    "AuthorityPromotionError",
    "LifecycleState",
    "MemoryAuthority",
    "MemoryError",
    "MemoryKind",
    "MemoryLifecycle",
    "MemoryPoisoningError",
    "MemoryRecord",
    "MemoryScope",
    "MemorySecurityError",
    "MemoryValidationError",
    "PoisoningError",
    "RetentionClass",
    "ScopeType",
    "SecretMaterialError",
    "assert_authority_allowed",
    "authority_allowed",
    "authority_rank",
    "contains_secret",
    "create_memory_record",
    "document_contains_secret",
    "document_has_authority_escalation",
    "document_is_poisoned",
    "find_injection_markers",
    "find_secret_markers",
    "is_working_context",
    "validate_memory_record",
    "validate_memory_record_document",
]


class MemoryError(ValueError):
    """Base error for memory contract failures."""


class MemoryValidationError(MemoryError):
    """A memory contract is structurally invalid or unsafe to persist."""


class SecretMaterialError(MemoryValidationError):
    """Memory payloads must not embed credentials or secrets."""


MemorySecurityError = SecretMaterialError


class MemoryPoisoningError(MemoryValidationError):
    """Instruction-like adversarial content must not impersonate memory."""


class PoisoningError(MemoryPoisoningError):
    """Instruction-like adversarial content must not impersonate memory."""


class AuthorityPromotionError(MemoryPoisoningError):
    """Untrusted content may not elevate its own authority."""


class MemoryKind(str, Enum):
    TASK_MEMORY = "TASK_MEMORY"
    PRODUCT_PROJECT_KNOWLEDGE = "PRODUCT_PROJECT_KNOWLEDGE"
    USER_PREFERENCE_MEMORY = "USER_PREFERENCE_MEMORY"
    LEARNING_MEMORY = "LEARNING_MEMORY"
    NEGATIVE_KNOWLEDGE = "NEGATIVE_KNOWLEDGE"
    DECISION_MEMORY = "DECISION_MEMORY"
    EVIDENCE_MEMORY = "EVIDENCE_MEMORY"


class MemoryScope(str, Enum):
    GLOBAL_PLATFORM = "GLOBAL_PLATFORM"
    PRINCIPAL = "PRINCIPAL"
    PRODUCT = "PRODUCT"
    PROGRAM = "PROGRAM"
    WORKSTREAM = "WORKSTREAM"
    TASK = "TASK"
    EXECUTION_ATTEMPT = "EXECUTION_ATTEMPT"


ScopeType = MemoryScope


class MemoryAuthority(str, Enum):
    CANONICAL_REFERENCE = "CANONICAL_REFERENCE"
    VERIFIED_KNOWLEDGE = "VERIFIED_KNOWLEDGE"
    USER_PREFERENCE = "USER_PREFERENCE"
    DERIVED_OBSERVATION = "DERIVED_OBSERVATION"
    UNVERIFIED = "UNVERIFIED"
    QUARANTINED = "QUARANTINED"


AuthorityClass = MemoryAuthority


class MemoryLifecycle(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    TOMBSTONED = "TOMBSTONED"
    QUARANTINED = "QUARANTINED"


LifecycleState = MemoryLifecycle


class RetentionClass(str, Enum):
    EPHEMERAL = "EPHEMERAL"
    SHORT = "SHORT"
    PROJECT_LIFETIME = "PROJECT_LIFETIME"
    REGULATED = "REGULATED"
    LEGAL_HOLD = "LEGAL_HOLD"


AUTHORITY_RANK: dict[str, int] = {
    MemoryAuthority.CANONICAL_REFERENCE.value: 6,
    MemoryAuthority.VERIFIED_KNOWLEDGE.value: 5,
    MemoryAuthority.USER_PREFERENCE.value: 4,
    MemoryAuthority.DERIVED_OBSERVATION.value: 3,
    MemoryAuthority.UNVERIFIED.value: 2,
    MemoryAuthority.QUARANTINED.value: 1,
}


def authority_rank(authority: MemoryAuthority | str) -> int:
    return AUTHORITY_RANK[MemoryAuthority(authority).value]


def is_working_context(kind: str) -> bool:
    return str(kind).strip().upper() in {"WORKING", "WORKING_CONTEXT"}


_ALLOWED_AUTHORITIES: dict[PrincipalType, frozenset[MemoryAuthority]] = {
    PrincipalType.PO: frozenset(MemoryAuthority),
    PrincipalType.ARCHITECT: frozenset({
        MemoryAuthority.VERIFIED_KNOWLEDGE,
        MemoryAuthority.USER_PREFERENCE,
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.EXECUTOR: frozenset({
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.INDEPENDENT_REVIEWER: frozenset({
        MemoryAuthority.CANONICAL_REFERENCE,
        MemoryAuthority.VERIFIED_KNOWLEDGE,
        MemoryAuthority.USER_PREFERENCE,
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.ASSURANCE_SERVICE: frozenset({
        MemoryAuthority.CANONICAL_REFERENCE,
        MemoryAuthority.VERIFIED_KNOWLEDGE,
        MemoryAuthority.USER_PREFERENCE,
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.RUNTIME_WORKER: frozenset({
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.POLICY_ENGINE: frozenset({
        MemoryAuthority.CANONICAL_REFERENCE,
        MemoryAuthority.VERIFIED_KNOWLEDGE,
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.EVOLUTION_CONTROLLER: frozenset({
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.RELEASE_MANAGER: frozenset({
        MemoryAuthority.VERIFIED_KNOWLEDGE,
        MemoryAuthority.USER_PREFERENCE,
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
    PrincipalType.SYSTEM: frozenset({
        MemoryAuthority.DERIVED_OBSERVATION,
        MemoryAuthority.UNVERIFIED,
        MemoryAuthority.QUARANTINED,
    }),
}


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", re.I)),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("database_uri", re.compile(r"\b(?:mysql|postgres|postgresql|mongodb|redis)://[^\s]+", re.I)),
    ("generic_secret", re.compile(r"\b(?:api[_-]?key|secret|token|password|passwd|private_key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.~]{8,}", re.I)),
)


_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_instructions", re.compile(r"\b(?:ignore|disregard|override)\b.{0,80}\b(?:previous|above|system|policy|instructions)\b", re.I)),
    ("system_prompt_claim", re.compile(r"\b(?:you are|act as|pretend to be)\b.{0,120}\b(?:system|admin|root|canonical|verified authority)\b", re.I)),
    ("authority_escalation", re.compile(r"\b(?:promote|elevate|upgrade)\b.{0,120}\b(?:authority|verified|canonical|system|admin|policy)\b", re.I)),
    ("exfiltration", re.compile(r"\b(?:reveal|print|dump|exfiltrate)\b.{0,120}\b(?:secret|token|credential|private key|system prompt)\b", re.I)),
    ("tool_override", re.compile(r"\b(?:do not call|bypass|disable)\b.{0,120}\b(?:tool|policy|approval|review|assurance)\b", re.I)),
)


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_strings(item)


def _payload_text(document: Mapping[str, Any]) -> str:
    return "\n".join(_iter_strings(document))


def find_secret_markers(text: str) -> tuple[str, ...]:
    markers: set[str] = set()
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            markers.add(name)
    return tuple(sorted(markers))


def contains_secret(text: str) -> bool:
    """True when a memory payload appears to embed credential material."""
    return bool(find_secret_markers(text))


def find_injection_markers(text: str) -> tuple[str, ...]:
    markers: set[str] = set()
    for name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            markers.add(name)
    return tuple(sorted(markers))


def document_contains_secret(document: Mapping[str, Any]) -> bool:
    return contains_secret(_payload_text(document))


def document_is_poisoned(document: Mapping[str, Any]) -> bool:
    return bool(find_injection_markers(_payload_text(document)))


def document_has_authority_escalation(document: Mapping[str, Any]) -> bool:
    markers = find_injection_markers(_payload_text(document))
    return bool(markers) and MemoryAuthority(document.get("authority_class", "UNVERIFIED")) in {
        MemoryAuthority.CANONICAL_REFERENCE,
        MemoryAuthority.VERIFIED_KNOWLEDGE,
        MemoryAuthority.USER_PREFERENCE,
    }


is_poisoned = document_is_poisoned
has_authority_escalation = document_has_authority_escalation


def _principal_type_name(value: Principal | Mapping[str, Any] | str) -> PrincipalType:
    if isinstance(value, Principal):
        return PrincipalType(value.principal_type)
    if isinstance(value, Mapping):
        return PrincipalType(value["principal_type"])
    return PrincipalType(value)


def _principal_dict(value: Principal | Mapping[str, Any]) -> dict[str, str]:
    if isinstance(value, Principal):
        principal_type = value.principal_type
        return {
            "principal_type": principal_type.value if isinstance(principal_type, Enum) else str(principal_type),
            "id": str(value.id),
        }
    principal_type = value["principal_type"]
    return {
        "principal_type": principal_type.value if isinstance(principal_type, Enum) else str(principal_type),
        "id": str(value["id"]),
    }


def authority_allowed(created_by: Principal | Mapping[str, Any], authority_class: MemoryAuthority | str) -> bool:
    actor = _principal_type_name(created_by)
    allowed = _ALLOWED_AUTHORITIES.get(actor, frozenset())
    return MemoryAuthority(authority_class) in allowed


def assert_authority_allowed(created_by: Principal | Mapping[str, Any], authority_class: MemoryAuthority | str) -> None:
    if not authority_allowed(created_by, authority_class):
        actor = _principal_type_name(created_by).value
        raise AuthorityPromotionError(f"{actor} may not assert {MemoryAuthority(authority_class).value}")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class MemoryRecord:
    schema_version: str
    memory_id: str
    kind: str
    scope_type: str
    scope_ref: str
    authority_class: str
    source_refs: Sequence[str]
    provenance_refs: Sequence[str]
    lifecycle_state: str
    retention_class: str
    content_digest: Mapping[str, str]
    created_at: str
    created_by: Principal | Mapping[str, Any]
    statement: str | None = None
    content_ref: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    supersedes: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", MemoryKind(self.kind).value)
        object.__setattr__(self, "scope_type", MemoryScope(self.scope_type).value)
        object.__setattr__(self, "authority_class", MemoryAuthority(self.authority_class).value)
        object.__setattr__(self, "lifecycle_state", MemoryLifecycle(self.lifecycle_state).value)
        object.__setattr__(self, "retention_class", RetentionClass(self.retention_class).value)
        object.__setattr__(self, "source_refs", tuple(str(item) for item in self.source_refs))
        object.__setattr__(self, "provenance_refs", tuple(str(item) for item in self.provenance_refs))
        object.__setattr__(self, "supersedes", tuple(str(item) for item in self.supersedes))

    @classmethod
    def create(cls, **fields: Any) -> "MemoryRecord":
        material = dict(fields)
        material.pop("content_digest", None)
        material.setdefault("schema_version", "2.1.0")
        material.setdefault("supersedes", [])
        material["created_at"] = material.get("created_at") or timestamp()
        material["created_by"] = _principal_dict(material["created_by"])
        material = {key: value for key, value in material.items() if value is not None}
        assert_authority_allowed(material["created_by"], material["authority_class"])
        digest = compute_digest(canonical(material))
        record = cls(**material, content_digest=digest)
        record.validate()
        return record

    def to_dict(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema_version": self.schema_version,
            "memory_id": self.memory_id,
            "kind": self.kind,
            "scope_type": self.scope_type,
            "scope_ref": self.scope_ref,
            "authority_class": self.authority_class,
            "source_refs": list(self.source_refs),
            "provenance_refs": list(self.provenance_refs),
            "lifecycle_state": self.lifecycle_state,
            "retention_class": self.retention_class,
            "content_digest": dict(self.content_digest),
            "created_at": self.created_at,
            "created_by": _principal_dict(self.created_by),
            "supersedes": list(self.supersedes),
        }
        for name in ("statement", "content_ref", "valid_from", "valid_until"):
            value = getattr(self, name)
            if value is not None:
                document[name] = value
        return document

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "MemoryRecord":
        validate_memory_record_document(document)
        return cls(
            schema_version=str(document["schema_version"]),
            memory_id=str(document["memory_id"]),
            kind=str(document["kind"]),
            scope_type=str(document["scope_type"]),
            scope_ref=str(document["scope_ref"]),
            authority_class=str(document["authority_class"]),
            source_refs=tuple(str(item) for item in document["source_refs"]),
            provenance_refs=tuple(str(item) for item in document["provenance_refs"]),
            lifecycle_state=str(document["lifecycle_state"]),
            retention_class=str(document["retention_class"]),
            content_digest=dict(document["content_digest"]),
            created_at=str(document["created_at"]),
            created_by=dict(document["created_by"]),
            statement=document.get("statement"),
            content_ref=document.get("content_ref"),
            valid_from=document.get("valid_from"),
            valid_until=document.get("valid_until"),
            supersedes=tuple(str(item) for item in document.get("supersedes", ())),
        )

    def replace_state(self, **changes: Any) -> "MemoryRecord":
        updated = replace(self, **changes)
        material = updated.to_dict()
        material.pop("content_digest", None)
        return replace(updated, content_digest=compute_digest(canonical(material)))

    def mark_superseded(self, when: str | None = None) -> "MemoryRecord":
        return self.replace_state(lifecycle_state=MemoryLifecycle.SUPERSEDED.value, valid_until=when or timestamp())

    def mark_expired(self, when: str | None = None) -> "MemoryRecord":
        return self.replace_state(lifecycle_state=MemoryLifecycle.EXPIRED.value, valid_until=when or timestamp())

    def mark_tombstoned(self, when: str | None = None) -> "MemoryRecord":
        return self.replace_state(lifecycle_state=MemoryLifecycle.TOMBSTONED.value, valid_until=when or timestamp())

    def mark_quarantined(self) -> "MemoryRecord":
        return self.replace_state(lifecycle_state=MemoryLifecycle.QUARANTINED.value, authority_class=MemoryAuthority.QUARANTINED.value)

    @property
    def revision(self) -> str:
        return str(self.content_digest["value"])

    def compute_digest(self) -> dict[str, str]:
        material = self.to_dict()
        material.pop("content_digest", None)
        return compute_digest(canonical(material))

    def validate(self) -> "MemoryRecord":
        validate_memory_record_document(self.to_dict())
        return self

    @property
    def text(self) -> str:
        return str(self.statement or self.content_ref or "")

    def is_active_at(self, moment: str | None = None) -> bool:
        if self.lifecycle_state != MemoryLifecycle.ACTIVE.value:
            return False
        now = _parse_datetime(moment or timestamp())
        if self.valid_from is not None and now < _parse_datetime(self.valid_from):
            return False
        if self.valid_until is not None and now > _parse_datetime(self.valid_until):
            return False
        return True


def validate_memory_record_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "memory_record.schema.json", MemoryValidationError)
    except MemoryValidationError:
        raise
    except Exception as exc:
        raise MemoryValidationError(str(exc)) from exc
    digest = document.get("content_digest")
    if not isinstance(digest, Mapping) or not validate_digest_spec(dict(digest)):
        raise MemoryValidationError("content_digest must be a canonical supported digest")
    material = {key: value for key, value in dict(document).items() if key != "content_digest"}
    expected = compute_digest(canonical(material), algorithm=str(digest["algorithm"]))
    if expected.get("encoding") != digest.get("encoding") or expected.get("value") != digest.get("value"):
        raise MemoryValidationError("content_digest does not match canonical record material")
    text = _payload_text(document)
    secrets = find_secret_markers(text)
    if secrets:
        raise SecretMaterialError("secret material detected: " + ", ".join(secrets))
    injections = find_injection_markers(text)
    if injections and str(document.get("lifecycle_state")) not in {MemoryLifecycle.QUARANTINED.value, MemoryLifecycle.TOMBSTONED.value}:
        raise PoisoningError("instruction-like poisoning markers detected: " + ", ".join(injections))
    assert_authority_allowed(document["created_by"], str(document["authority_class"]))
    if document.get("valid_from") and document.get("valid_until"):
        if _parse_datetime(str(document["valid_until"])) < _parse_datetime(str(document["valid_from"])):
            raise MemoryValidationError("valid_until must not precede valid_from")
    if str(document["memory_id"]) in set(document.get("supersedes", ())):
        raise MemoryValidationError("memory_id must not supersede itself")


def validate_memory_record(document_or_record: MemoryRecord | Mapping[str, Any]) -> MemoryRecord:
    if isinstance(document_or_record, MemoryRecord):
        validate_memory_record_document(document_or_record.to_dict())
        return document_or_record
    validate_memory_record_document(document_or_record)
    return MemoryRecord.from_dict(document_or_record)


def create_memory_record(**fields: Any) -> dict[str, Any]:
    material = dict(fields)
    for k in ("kind", "scope_type", "authority_class", "lifecycle_state", "retention_class"):
        if k in material and hasattr(material[k], "value"):
            material[k] = material[k].value
    record = MemoryRecord.create(**material)
    return record.to_dict()
