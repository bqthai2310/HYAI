"""Tombstones and retention policies that make deletion auditable."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest, validate_digest_spec
from hyai.constitution.authority import Principal, PrincipalType
from hyai.memory.record import MemoryRecord, MemoryValidationError, RetentionClass, _principal_dict


class TombstoneValidationError(MemoryValidationError):
    """A tombstone or retention policy does not satisfy its schema contract."""


TombstoneError = TombstoneValidationError


TombstoneError = TombstoneValidationError


def _validate_schema(document: Mapping[str, Any], schema_name: str) -> None:
    try:
        validate(document, schema_name, TombstoneValidationError)
    except MemoryValidationError:
        raise
    except Exception as exc:
        raise TombstoneValidationError(str(exc)) from exc


def _verify_digest(document: Mapping[str, Any]) -> None:
    digest = document.get("content_digest")
    if not isinstance(digest, Mapping) or not validate_digest_spec(dict(digest)):
        raise TombstoneValidationError("content_digest must be a canonical supported digest")
    material = {key: value for key, value in dict(document).items() if key != "content_digest"}
    expected = compute_digest(canonical(material), algorithm=str(digest["algorithm"]))
    if expected.get("encoding") != digest.get("encoding") or expected.get("value") != digest.get("value"):
        raise TombstoneValidationError("content_digest does not match canonical material")


@dataclass(frozen=True)
class MemoryTombstone:
    schema_version: str
    tombstone_id: str
    memory_id: str
    reason: str
    authority: Principal | Mapping[str, Any]
    issued_at: str
    purge_required: bool = False

    @classmethod
    def create(
        cls,
        *,
        tombstone_id: str,
        memory_id: str,
        reason: str,
        authority: Principal | Mapping[str, Any],
        schema_version: str = "2.1.0",
        issued_at: str | None = None,
        purge_required: bool = False,
    ) -> "MemoryTombstone":
        tombstone = cls(
            schema_version=schema_version,
            tombstone_id=tombstone_id,
            memory_id=memory_id,
            reason=reason,
            authority=authority,
            issued_at=issued_at or timestamp(),
            purge_required=purge_required,
        )
        tombstone.validate()
        return tombstone

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tombstone_id": self.tombstone_id,
            "memory_id": self.memory_id,
            "reason": self.reason,
            "authority": _principal_dict(self.authority),
            "purge_required": bool(self.purge_required),
            "issued_at": self.issued_at,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "MemoryTombstone":
        validate_memory_tombstone_document(document)
        return cls(
            schema_version=str(document["schema_version"]),
            tombstone_id=str(document["tombstone_id"]),
            memory_id=str(document["memory_id"]),
            reason=str(document["reason"]),
            authority=dict(document["authority"]),
            issued_at=str(document["issued_at"]),
            purge_required=bool(document.get("purge_required", False)),
        )

    def requires_purge(self) -> bool:
        return bool(self.purge_required)

    def validate(self) -> "MemoryTombstone":
        validate_memory_tombstone_document(self.to_dict())
        return self


def validate_memory_tombstone_document(document: Mapping[str, Any]) -> None:
    _validate_schema(document, "memory_tombstone.schema.json")
    if not str(document.get("reason", "")).strip():
        raise TombstoneValidationError("tombstone reason is required")


def validate_memory_tombstone(document_or_tombstone: MemoryTombstone | Mapping[str, Any]) -> MemoryTombstone:
    if isinstance(document_or_tombstone, MemoryTombstone):
        validate_memory_tombstone_document(document_or_tombstone.to_dict())
        return document_or_tombstone
    validate_memory_tombstone_document(document_or_tombstone)
    return MemoryTombstone.from_dict(document_or_tombstone)


_RETENTION_DEFAULTS: dict[RetentionClass, tuple[str, str, bool, bool]] = {
    RetentionClass.EPHEMERAL: ("PT24H", "PURGE_AFTER_RETENTION", False, False),
    RetentionClass.SHORT: ("P30D", "PURGE_AFTER_RETENTION", False, False),
    RetentionClass.PROJECT_LIFETIME: ("UNTIL_SCOPE_CLOSE", "ARCHIVE_THEN_PURGE", True, True),
    RetentionClass.REGULATED: ("P7Y", "PURGE_AFTER_RETENTION", True, True),
    RetentionClass.LEGAL_HOLD: ("INDEFINITE_LEGAL_HOLD", "RETAIN_UNTIL_HOLD_RELEASED", True, True),
}


@dataclass(frozen=True)
class DataRetentionPolicy:
    schema_version: str
    policy_id: str
    data_class: str
    retention_period: str
    deletion_semantics: str
    backup_required: bool
    legal_hold_supported: bool | None
    content_digest: Mapping[str, str]

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        data_class: str,
        retention_period: str,
        deletion_semantics: str,
        backup_required: bool,
        legal_hold_supported: bool | None = None,
        schema_version: str = "2.1.0",
    ) -> "DataRetentionPolicy":
        """Build a digest-sealed retention policy from explicit fields."""
        material: dict[str, Any] = {
            "schema_version": schema_version,
            "policy_id": policy_id,
            "data_class": data_class,
            "retention_period": retention_period,
            "deletion_semantics": deletion_semantics,
            "backup_required": bool(backup_required),
        }
        hold = None if legal_hold_supported is None else bool(legal_hold_supported)
        if hold is not None:
            material["legal_hold_supported"] = hold
        return cls(
            schema_version=schema_version,
            policy_id=policy_id,
            data_class=data_class,
            retention_period=retention_period,
            deletion_semantics=deletion_semantics,
            backup_required=bool(backup_required),
            legal_hold_supported=hold,
            content_digest=compute_digest(canonical(material)),
        )

    @classmethod
    def for_retention_class(cls, retention_class: RetentionClass | str, *, schema_version: str = "2.1.0") -> "DataRetentionPolicy":
        resolved = RetentionClass(retention_class)
        period, semantics, backup, legal_hold = _RETENTION_DEFAULTS[resolved]
        material = {
            "schema_version": schema_version,
            "policy_id": f"retention_{resolved.value.lower()}",
            "data_class": f"MEMORY:{resolved.value}",
            "retention_period": period,
            "deletion_semantics": semantics,
            "backup_required": backup,
            "legal_hold_supported": legal_hold,
        }
        policy = cls(
            schema_version=schema_version,
            policy_id=str(material["policy_id"]),
            data_class=str(material["data_class"]),
            retention_period=period,
            deletion_semantics=semantics,
            backup_required=backup,
            legal_hold_supported=legal_hold,
            content_digest=compute_digest(canonical(material)),
        )
        policy.validate()
        return policy

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        data_class: str,
        retention_period: str,
        deletion_semantics: str,
        backup_required: bool,
        legal_hold_supported: bool | None = None,
        schema_version: str = "2.1.0",
    ) -> "DataRetentionPolicy":
        material = {
            "schema_version": schema_version,
            "policy_id": policy_id,
            "data_class": data_class,
            "retention_period": retention_period,
            "deletion_semantics": deletion_semantics,
            "backup_required": backup_required,
        }
        if legal_hold_supported is not None:
            material["legal_hold_supported"] = legal_hold_supported
        policy = cls(
            schema_version=schema_version,
            policy_id=policy_id,
            data_class=data_class,
            retention_period=retention_period,
            deletion_semantics=deletion_semantics,
            backup_required=backup_required,
            legal_hold_supported=legal_hold_supported,
            content_digest=compute_digest(canonical(material)),
        )
        policy.validate()
        return policy

    def to_dict(self) -> dict[str, Any]:
        document = {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "data_class": self.data_class,
            "retention_period": self.retention_period,
            "deletion_semantics": self.deletion_semantics,
            "backup_required": bool(self.backup_required),
            "content_digest": dict(self.content_digest),
        }
        if self.legal_hold_supported is not None:
            document["legal_hold_supported"] = bool(self.legal_hold_supported)
        return document

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "DataRetentionPolicy":
        validate_data_retention_policy_document(document)
        return cls(
            schema_version=str(document["schema_version"]),
            policy_id=str(document["policy_id"]),
            data_class=str(document["data_class"]),
            retention_period=str(document["retention_period"]),
            deletion_semantics=str(document["deletion_semantics"]),
            backup_required=bool(document["backup_required"]),
            legal_hold_supported=document.get("legal_hold_supported"),
            content_digest=dict(document["content_digest"]),
        )

    def covers(self, record: MemoryRecord) -> bool:
        return self.data_class == f"MEMORY:{record.retention_class}"

    def allows_purge(self, tombstone: MemoryTombstone | None = None) -> bool:
        if self.deletion_semantics.startswith("RETAIN"):
            return False
        if self.legal_hold_supported and self.data_class.endswith(RetentionClass.LEGAL_HOLD.value):
            return tombstone is not None and tombstone.requires_purge()
        return self.deletion_semantics.startswith("PURGE") or self.deletion_semantics.startswith("ARCHIVE_THEN_PURGE")

    def audit_entry(self, action: str, memory_id: str, when: str | None = None) -> dict[str, Any]:
        return {
            "action": action,
            "memory_id": memory_id,
            "policy_id": self.policy_id,
            "data_class": self.data_class,
            "retention_period": self.retention_period,
            "deletion_semantics": self.deletion_semantics,
            "policy_digest": dict(self.content_digest),
            "at": when or timestamp(),
        }

    def validate(self) -> "DataRetentionPolicy":
        validate_data_retention_policy_document(self.to_dict())
        return self


def validate_data_retention_policy_document(document: Mapping[str, Any]) -> None:
    _validate_schema(document, "data_retention_policy.schema.json")
    _verify_digest(document)


def validate_data_retention_policy(document_or_policy: DataRetentionPolicy | Mapping[str, Any]) -> DataRetentionPolicy:
    if isinstance(document_or_policy, DataRetentionPolicy):
        validate_data_retention_policy_document(document_or_policy.to_dict())
        return document_or_policy
    validate_data_retention_policy_document(document_or_policy)
    return DataRetentionPolicy.from_dict(document_or_policy)


def create_tombstone(**fields: Any) -> dict[str, Any]:
    """Build a canonical MemoryTombstone document from explicit fields."""
    return MemoryTombstone.create(**fields).to_dict()


def create_data_retention_policy(**fields: Any) -> dict[str, Any]:
    """Build a digest-sealed DataRetentionPolicy document from explicit fields."""
    return DataRetentionPolicy.create(**fields).to_dict()


def create_tombstone(**fields: Any) -> dict[str, Any]:
    return MemoryTombstone.create(**fields).to_dict()


def create_data_retention_policy(**fields: Any) -> dict[str, Any]:
    return DataRetentionPolicy.create(**fields).to_dict()
