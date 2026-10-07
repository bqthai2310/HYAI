"""Protocol adapter descriptors, protocol neutrality, version negotiation, and exit contracts (INT-001..007, CMP-007)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest


class InteropError(Exception):
    """Base error for interoperability and protocol subsystem."""


class SilentProtocolDowngradeError(InteropError):
    """Raised when protocol negotiation silently downgrades capabilities (L9-REQ-INT-003)."""


class LossyTranslationError(InteropError):
    """Raised when protocol translation loses required semantics without explicit handling (L9-REQ-INT-004)."""


class ExternalDirectWriteForbiddenError(InteropError):
    """Raised when an external agent attempts direct-write to canonical state (L9-REQ-INT-005)."""


class AdapterLifecycleState(str, Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class ProtocolAdapterDescriptor:
    schema_version: str
    adapter_id: str
    protocol_name: str
    protocol_version: str
    capabilities: tuple[str, ...]
    security_profile: str
    compatibility_ref: str
    lifecycle_state: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^protocoladapter_", self.adapter_id):
            raise InteropError(f"adapter_id '{self.adapter_id}' must begin with 'protocoladapter_'")
        if not re.match(r"^compat_", self.compatibility_ref):
            raise InteropError(f"compatibility_ref '{self.compatibility_ref}' must begin with 'compat_'")
        object.__setattr__(self, "lifecycle_state", AdapterLifecycleState(self.lifecycle_state).value)
        object.__setattr__(self, "capabilities", tuple(self.capabilities))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "adapter_id": self.adapter_id,
            "protocol_name": self.protocol_name,
            "protocol_version": self.protocol_version,
            "capabilities": list(self.capabilities),
            "security_profile": self.security_profile,
            "compatibility_ref": self.compatibility_ref,
            "lifecycle_state": self.lifecycle_state,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "ProtocolAdapterDescriptor":
        validate_protocol_adapter_descriptor_document(self.to_dict())
        return self


def validate_protocol_adapter_descriptor_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "protocol_adapter_descriptor.schema.json", InteropError)
    except Exception as exc:
        raise InteropError(str(exc)) from exc


def create_protocol_adapter_descriptor(
    *,
    adapter_id: str,
    protocol_name: str,
    protocol_version: str,
    capabilities: Sequence[str],
    security_profile: str = "SEC_STRICT_TLS",
    compatibility_ref: str = "compat_standard_v1",
    lifecycle_state: AdapterLifecycleState | str = AdapterLifecycleState.ACTIVE,
    schema_version: str = "2.1.0",
) -> ProtocolAdapterDescriptor:
    ls = lifecycle_state.value if isinstance(lifecycle_state, AdapterLifecycleState) else str(lifecycle_state)
    payload = {
        "adapter_id": adapter_id,
        "protocol_name": protocol_name,
        "protocol_version": protocol_version,
        "capabilities": tuple(capabilities),
        "security_profile": security_profile,
        "compatibility_ref": compatibility_ref,
        "lifecycle_state": ls,
    }
    digest = compute_digest(canonical(payload))
    descriptor = ProtocolAdapterDescriptor(
        schema_version=schema_version,
        adapter_id=adapter_id,
        protocol_name=protocol_name,
        protocol_version=protocol_version,
        capabilities=tuple(capabilities),
        security_profile=security_profile,
        compatibility_ref=compatibility_ref,
        lifecycle_state=ls,
        content_digest=digest,
    )
    descriptor.validate()
    return descriptor


class InteropGateway:
    """Manages protocol adapter registry, negotiation, external agent trust, and translation."""

    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], ProtocolAdapterDescriptor] = {}
        self._conformance_records: dict[str, bool] = {}

    def register_adapter(self, descriptor: ProtocolAdapterDescriptor) -> None:
        descriptor.validate()
        self._adapters[(descriptor.protocol_name, descriptor.protocol_version)] = descriptor

    def record_conformance_test(self, adapter_id: str, passed: bool) -> None:
        """L9-REQ-INT-006: Protocol adapters have conformance/contract tests."""
        self._conformance_records[adapter_id] = passed

    def is_conformant(self, adapter_id: str) -> bool:
        return self._conformance_records.get(adapter_id, False)

    def negotiate_version(
        self,
        protocol_name: str,
        requested_version: str,
        supported_versions: Sequence[str],
        allow_silent_downgrade: bool = False,
    ) -> str:
        # L9-REQ-INT-003: Version negotiation explicit; no silent downgrade
        if requested_version not in supported_versions:
            if not allow_silent_downgrade:
                raise SilentProtocolDowngradeError(
                    f"Requested protocol '{protocol_name}' version '{requested_version}' not supported; silent downgrade forbidden"
                )
        return requested_version if requested_version in supported_versions else supported_versions[0]

    def translate_message(
        self,
        source_protocol: str,
        target_protocol: str,
        payload: Mapping[str, Any],
        required_semantics: Sequence[str] = (),
    ) -> dict[str, Any]:
        # L9-REQ-INT-004: Translation loss declares lossy semantics and fails closed
        unsupported = [s for s in required_semantics if s not in payload]
        if unsupported:
            raise LossyTranslationError(
                f"Translation from {source_protocol} to {target_protocol} cannot preserve required semantics: {unsupported}"
            )
        return {"source": source_protocol, "target": target_protocol, "data": dict(payload)}

    def execute_external_agent_call(
        self,
        agent_id: str,
        action: str,
        is_direct_write: bool = False,
    ) -> dict[str, Any]:
        # L9-REQ-INT-005: External agent cannot direct-write HYAI canonical state
        if is_direct_write:
            raise ExternalDirectWriteForbiddenError(
                f"External agent '{agent_id}' attempted forbidden direct write to canonical state (L9-REQ-INT-005)"
            )
        return {"agent_id": agent_id, "action": action, "status": "MEDIATED_BY_ADAPTER"}

    def supports_coexistence(self, protocol_name: str) -> bool:
        # L9-REQ-INT-007: Multiple protocol versions can coexist through isolated adapters
        versions = [ver for (name, ver) in self._adapters if name == protocol_name]
        return len(versions) >= 2


@dataclass(frozen=True)
class VendorExitContract:
    """L9-REQ-CMP-007: Critical vendor/runtime dependency declares exit/migration path."""
    dependency_id: str
    vendor_name: str
    exit_migration_path: str
    export_format: str
    alternative_vendor: str
    is_tested: bool = True

    def validate(self) -> None:
        if not self.exit_migration_path or not self.export_format:
            raise InteropError(f"VendorExitContract for '{self.dependency_id}' must declare migration path and export format")
