"""Schema-backed CapabilitySpec definitions and validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest


class CapabilityError(ValueError):
    """Base error for capability subsystem."""


class CapabilityValidationError(CapabilityError):
    """Raised when a capability spec violates its schema contract."""


class QualityClass(str, Enum):
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class CapabilityParameter:
    name: str
    type_ref: str
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class CapabilitySpec:
    schema_version: str
    capability_id: str
    name: str
    input_contract: str
    output_contract: str
    permissions: tuple[str, ...]
    quality_class: str
    risk_class: str
    evidence_types: tuple[str, ...] = ()
    isolation_requirements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "permissions", tuple(sorted(set(self.permissions))))
        object.__setattr__(self, "evidence_types", tuple(sorted(set(self.evidence_types))))
        object.__setattr__(self, "isolation_requirements", tuple(sorted(set(self.isolation_requirements))))
        object.__setattr__(self, "quality_class", QualityClass(self.quality_class).value)
        object.__setattr__(self, "risk_class", RiskClass(self.risk_class).value)

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "name": self.name,
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "permissions": list(self.permissions),
            "quality_class": self.quality_class,
            "risk_class": self.risk_class,
        }
        if self.evidence_types:
            doc["evidence_types"] = list(self.evidence_types)
        if self.isolation_requirements:
            doc["isolation_requirements"] = list(self.isolation_requirements)
        return doc

    def validate(self) -> "CapabilitySpec":
        validate_capability_spec_document(self.to_dict())
        return self


@dataclass(frozen=True)
class DynamicCapabilityManifest:
    schema_version: str
    manifest_id: str
    capabilities: tuple[CapabilitySpec, ...]


def validate_capability_spec_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "capability_spec.schema.json", CapabilityValidationError)
    except Exception as exc:
        raise CapabilityValidationError(str(exc)) from exc


def validate_capability_spec(spec_or_doc: CapabilitySpec | Mapping[str, Any]) -> CapabilitySpec:
    if isinstance(spec_or_doc, CapabilitySpec):
        spec_or_doc.validate()
        return spec_or_doc
    validate_capability_spec_document(spec_or_doc)
    return CapabilitySpec(
        schema_version=str(spec_or_doc["schema_version"]),
        capability_id=str(spec_or_doc["capability_id"]),
        name=str(spec_or_doc["name"]),
        input_contract=str(spec_or_doc["input_contract"]),
        output_contract=str(spec_or_doc["output_contract"]),
        permissions=tuple(spec_or_doc.get("permissions", ())),
        quality_class=str(spec_or_doc["quality_class"]),
        risk_class=str(spec_or_doc["risk_class"]),
        evidence_types=tuple(spec_or_doc.get("evidence_types", ())),
        isolation_requirements=tuple(spec_or_doc.get("isolation_requirements", ())),
    )


def create_capability_spec(
    *,
    capability_id: str,
    name: str,
    input_contract: str = "contract_in_default",
    output_contract: str = "contract_out_default",
    permissions: Sequence[str] = (),
    quality_class: QualityClass | str = QualityClass.STANDARD,
    risk_class: RiskClass | str = RiskClass.LOW,
    evidence_types: Sequence[str] = (),
    isolation_requirements: Sequence[str] = (),
    schema_version: str = "2.1.0",
) -> CapabilitySpec:
    spec = CapabilitySpec(
        schema_version=schema_version,
        capability_id=capability_id,
        name=name,
        input_contract=input_contract,
        output_contract=output_contract,
        permissions=tuple(permissions),
        quality_class=str(quality_class if isinstance(quality_class, str) else quality_class.value),
        risk_class=str(risk_class if isinstance(risk_class, str) else risk_class.value),
        evidence_types=tuple(evidence_types),
        isolation_requirements=tuple(isolation_requirements),
    )
    spec.validate()
    return spec
