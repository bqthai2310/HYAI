"""Data classification, retention policies, backup/DR, and projection sanitization (DAT-001..007)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest
from hyai.workflow.instance import WorkflowError, WorkflowValidationError


class DataGovernanceError(WorkflowError):
    """Base error for data governance subsystem."""


class InvalidBackupSourceError(DataGovernanceError):
    """Raised when derived projection/cache is specified as canonical backup (L9-REQ-DAT-007)."""


class RestoreDrillVerificationError(DataGovernanceError):
    """Raised when restore drill verification fails against canonical digest (L9-REQ-DAT-005)."""


class DataClass(str, Enum):
    CANONICAL = "CANONICAL"
    EVIDENCE = "EVIDENCE"
    MEMORY = "MEMORY"
    TELEMETRY = "TELEMETRY"
    SECRETS = "SECRETS"
    TRANSIENT = "TRANSIENT"


@dataclass(frozen=True)
class DataRecordDescriptor:
    record_id: str
    data_class: str
    owner: str
    storage_tier: str = "HOT"

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_class", DataClass(self.data_class).value)


@dataclass(frozen=True)
class DataRetentionPolicy:
    schema_version: str
    policy_id: str
    data_class: str
    retention_period: str
    deletion_semantics: str
    backup_required: bool
    content_digest: dict[str, str]
    legal_hold_supported: bool = True

    def __post_init__(self) -> None:
        if not re.match(r"^retention_", self.policy_id):
            raise WorkflowValidationError(f"policy_id '{self.policy_id}' must begin with 'retention_'")
        object.__setattr__(self, "data_class", DataClass(self.data_class).value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "data_class": self.data_class,
            "retention_period": self.retention_period,
            "deletion_semantics": self.deletion_semantics,
            "backup_required": bool(self.backup_required),
            "legal_hold_supported": bool(self.legal_hold_supported),
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "DataRetentionPolicy":
        validate_data_retention_policy_document(self.to_dict())
        return self


def validate_data_retention_policy_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "data_retention_policy.schema.json", WorkflowValidationError)
    except Exception as exc:
        raise WorkflowValidationError(str(exc)) from exc


def create_data_retention_policy(
    *,
    policy_id: str,
    data_class: DataClass | str,
    retention_period: str,
    deletion_semantics: str,
    backup_required: bool = True,
    legal_hold_supported: bool = True,
    schema_version: str = "2.1.0",
) -> DataRetentionPolicy:
    dc = str(data_class if isinstance(data_class, str) else data_class.value)
    payload = {
        "policy_id": policy_id,
        "data_class": dc,
        "retention_period": retention_period,
        "deletion_semantics": deletion_semantics,
        "backup_required": backup_required,
    }
    digest = compute_digest(canonical(payload))
    policy = DataRetentionPolicy(
        schema_version=schema_version,
        policy_id=policy_id,
        data_class=dc,
        retention_period=retention_period,
        deletion_semantics=deletion_semantics,
        backup_required=backup_required,
        legal_hold_supported=legal_hold_supported,
        content_digest=digest,
    )
    policy.validate()
    return policy


@dataclass(frozen=True)
class DisasterRecoveryPlan:
    schema_version: str
    dr_plan_id: str
    system_scope: tuple[str, ...]
    rpo_seconds: int
    rto_seconds: int
    backup_refs: tuple[str, ...]
    restore_procedure_ref: str
    drill_frequency: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^drplan_", self.dr_plan_id):
            raise WorkflowValidationError(f"dr_plan_id '{self.dr_plan_id}' must begin with 'drplan_'")
        object.__setattr__(self, "system_scope", tuple(self.system_scope))
        object.__setattr__(self, "backup_refs", tuple(self.backup_refs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dr_plan_id": self.dr_plan_id,
            "system_scope": list(self.system_scope),
            "rpo_seconds": int(self.rpo_seconds),
            "rto_seconds": int(self.rto_seconds),
            "backup_refs": list(self.backup_refs),
            "restore_procedure_ref": self.restore_procedure_ref,
            "drill_frequency": self.drill_frequency,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "DisasterRecoveryPlan":
        validate_disaster_recovery_plan_document(self.to_dict())
        return self


def validate_disaster_recovery_plan_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "disaster_recovery_plan.schema.json", WorkflowValidationError)
    except Exception as exc:
        raise WorkflowValidationError(str(exc)) from exc


def create_disaster_recovery_plan(
    *,
    dr_plan_id: str,
    system_scope: Sequence[str],
    rpo_seconds: int,
    rto_seconds: int,
    backup_refs: Sequence[str],
    restore_procedure_ref: str,
    drill_frequency: str = "QUARTERLY",
    schema_version: str = "2.1.0",
) -> DisasterRecoveryPlan:
    # L9-REQ-DAT-007: Projections cannot be canonical backup sources
    for ref in backup_refs:
        if any(prefix in ref.lower() for prefix in ("cache_", "vector_", "projection_", "search_index_")):
            raise InvalidBackupSourceError(f"Backup ref '{ref}' is a derived projection, which cannot be a canonical backup source")

    payload = {
        "dr_plan_id": dr_plan_id,
        "system_scope": tuple(system_scope),
        "rpo_seconds": int(rpo_seconds),
        "rto_seconds": int(rto_seconds),
        "backup_refs": tuple(backup_refs),
        "restore_procedure_ref": restore_procedure_ref,
        "drill_frequency": drill_frequency,
    }
    digest = compute_digest(canonical(payload))
    plan = DisasterRecoveryPlan(
        schema_version=schema_version,
        dr_plan_id=dr_plan_id,
        system_scope=tuple(system_scope),
        rpo_seconds=rpo_seconds,
        rto_seconds=rto_seconds,
        backup_refs=tuple(backup_refs),
        restore_procedure_ref=restore_procedure_ref,
        drill_frequency=drill_frequency,
        content_digest=digest,
    )
    plan.validate()
    return plan


class RestoreDrill:
    """Simulates disaster recovery restore and verifies data integrity (L9-REQ-DAT-005)."""

    def __init__(self, plan: DisasterRecoveryPlan) -> None:
        self.plan = plan

    def execute_drill(self, canonical_payload: bytes, restored_payload: bytes) -> dict[str, Any]:
        expected = compute_digest(canonical_payload)
        actual = compute_digest(restored_payload)
        if expected != actual:
            raise RestoreDrillVerificationError(
                f"Restore drill failed: restored digest {actual} does not match canonical digest {expected}"
            )
        return {
            "status": "PASS",
            "dr_plan_id": self.plan.dr_plan_id,
            "digest": actual,
            "verified_at": timestamp(),
        }


class TombstonePropagationManager:
    """Propagates tombstones and purges across derived read projections and vector indices (L9-REQ-DAT-006)."""

    def __init__(self) -> None:
        self.projections: dict[str, set[str]] = {
            "search_index": set(),
            "vector_store": set(),
            "read_cache": set(),
        }

    def register_item(self, projection_name: str, item_id: str) -> None:
        if projection_name in self.projections:
            self.projections[projection_name].add(item_id)

    def propagate_tombstone(self, item_id: str) -> None:
        for proj in self.projections.values():
            proj.discard(item_id)

    def is_purged_everywhere(self, item_id: str) -> bool:
        return not any(item_id in items for items in self.projections.values())
