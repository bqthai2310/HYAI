"""Technology lifecycle tracking and Evolution Radar upgrade signals (UPG-001, CMP-004)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest
from hyai.observability.telemetry import ObservabilityError


class LifecycleError(ObservabilityError):
    """Base error for technology lifecycle subsystem."""


class SignalType(str, Enum):
    EOL = "EOL"
    SECURITY = "SECURITY"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    REGRESSION = "REGRESSION"
    PROTOCOL_CHANGE = "PROTOCOL_CHANGE"
    COST_LATENCY = "COST_LATENCY"
    SCALE_PRESSURE = "SCALE_PRESSURE"
    BETTER_PROVEN_OPTION = "BETTER_PROVEN_OPTION"


class SignalSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalLifecycleState(str, Enum):
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    LINKED_TO_PROPOSAL = "LINKED_TO_PROPOSAL"
    DISMISSED = "DISMISSED"


class TechLifecycleState(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    TRIAL = "TRIAL"
    ADOPTED = "ADOPTED"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class UpgradeSignal:
    schema_version: str
    signal_id: str
    signal_type: str
    subject_ref: str
    evidence_refs: tuple[str, ...]
    severity: str
    detected_at: str
    lifecycle_state: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^upgradesignal_", self.signal_id):
            raise LifecycleError(f"signal_id '{self.signal_id}' must begin with 'upgradesignal_'")
        object.__setattr__(self, "signal_type", SignalType(self.signal_type).value)
        object.__setattr__(self, "severity", SignalSeverity(self.severity).value)
        object.__setattr__(self, "lifecycle_state", SignalLifecycleState(self.lifecycle_state).value)
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "subject_ref": self.subject_ref,
            "evidence_refs": list(self.evidence_refs),
            "severity": self.severity,
            "detected_at": self.detected_at,
            "lifecycle_state": self.lifecycle_state,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "UpgradeSignal":
        validate_upgrade_signal_document(self.to_dict())
        return self


def validate_upgrade_signal_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "upgrade_signal.schema.json", LifecycleError)
    except Exception as exc:
        raise LifecycleError(str(exc)) from exc


def create_upgrade_signal(
    *,
    signal_id: str,
    signal_type: SignalType | str,
    subject_ref: str,
    evidence_refs: Sequence[str],
    severity: SignalSeverity | str = SignalSeverity.MEDIUM,
    detected_at: str | None = None,
    lifecycle_state: SignalLifecycleState | str = SignalLifecycleState.DETECTED,
    schema_version: str = "2.1.0",
) -> UpgradeSignal:
    st = signal_type.value if isinstance(signal_type, SignalType) else str(signal_type)
    sev = severity.value if isinstance(severity, SignalSeverity) else str(severity)
    ls = lifecycle_state.value if isinstance(lifecycle_state, SignalLifecycleState) else str(lifecycle_state)
    payload = {
        "signal_id": signal_id,
        "signal_type": st,
        "subject_ref": subject_ref,
        "evidence_refs": tuple(evidence_refs),
        "severity": sev,
        "detected_at": detected_at or timestamp(),
        "lifecycle_state": ls,
    }
    digest = compute_digest(canonical(payload))
    signal = UpgradeSignal(
        schema_version=schema_version,
        signal_id=signal_id,
        signal_type=st,
        subject_ref=subject_ref,
        evidence_refs=tuple(evidence_refs),
        severity=sev,
        detected_at=detected_at or timestamp(),
        lifecycle_state=ls,
        content_digest=digest,
    )
    signal.validate()
    return signal


@dataclass(frozen=True)
class TechnologyLifecycleEntry:
    schema_version: str
    technology_id: str
    category: str
    lifecycle_state: str
    current_version: str
    supported_range: str
    criticality: str
    owner: dict[str, str]
    evaluation_refs: tuple[str, ...]
    exit_plan_ref: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^technology_", self.technology_id):
            raise LifecycleError(f"technology_id '{self.technology_id}' must begin with 'technology_'")
        object.__setattr__(self, "lifecycle_state", TechLifecycleState(self.lifecycle_state).value)
        object.__setattr__(self, "evaluation_refs", tuple(self.evaluation_refs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "technology_id": self.technology_id,
            "category": self.category,
            "lifecycle_state": self.lifecycle_state,
            "current_version": self.current_version,
            "supported_range": self.supported_range,
            "criticality": self.criticality,
            "owner": dict(self.owner),
            "evaluation_refs": list(self.evaluation_refs),
            "exit_plan_ref": self.exit_plan_ref,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "TechnologyLifecycleEntry":
        validate_technology_lifecycle_entry_document(self.to_dict())
        return self


def validate_technology_lifecycle_entry_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "technology_lifecycle_entry.schema.json", LifecycleError)
    except Exception as exc:
        raise LifecycleError(str(exc)) from exc


def create_technology_lifecycle_entry(
    *,
    technology_id: str,
    category: str,
    lifecycle_state: TechLifecycleState | str = TechLifecycleState.ADOPTED,
    current_version: str,
    supported_range: str,
    criticality: str = "HIGH",
    owner: Mapping[str, str] | None = None,
    evaluation_refs: Sequence[str] = (),
    exit_plan_ref: str,
    schema_version: str = "2.1.0",
) -> TechnologyLifecycleEntry:
    own = dict(owner or {"principal_type": "ARCHITECT", "id": "architect_lead"})
    ls = lifecycle_state.value if isinstance(lifecycle_state, TechLifecycleState) else str(lifecycle_state)
    payload = {
        "technology_id": technology_id,
        "category": category,
        "lifecycle_state": ls,
        "current_version": current_version,
        "supported_range": supported_range,
        "criticality": criticality,
        "owner": own,
        "evaluation_refs": tuple(evaluation_refs),
        "exit_plan_ref": exit_plan_ref,
    }
    digest = compute_digest(canonical(payload))
    entry = TechnologyLifecycleEntry(
        schema_version=schema_version,
        technology_id=technology_id,
        category=category,
        lifecycle_state=ls,
        current_version=current_version,
        supported_range=supported_range,
        criticality=criticality,
        owner=own,
        evaluation_refs=tuple(evaluation_refs),
        exit_plan_ref=exit_plan_ref,
        content_digest=digest,
    )
    entry.validate()
    return entry
