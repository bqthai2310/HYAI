"""Component ABI Manifest for runtime-neutral skill/component packaging (L9-REQ-CMP-006)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import validate
from hyai.skills.spec import SkillError, SkillValidationError


class EntrypointKind(str, Enum):
    NATIVE = "NATIVE"
    PROCESS = "PROCESS"
    CONTAINER = "CONTAINER"
    WASM_COMPONENT = "WASM_COMPONENT"
    REMOTE_SERVICE = "REMOTE_SERVICE"
    OTHER = "OTHER"


@dataclass(frozen=True)
class ComponentABIManifest:
    schema_version: str
    abi_manifest_id: str
    component_id: str
    component_version: str
    entrypoint_kind: str
    exported_capabilities: tuple[str, ...]
    input_schema_refs: tuple[str, ...]
    output_schema_refs: tuple[str, ...]
    permission_refs: tuple[str, ...]
    compatibility_ref: str
    artifact_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^abi_", self.abi_manifest_id):
            raise SkillValidationError(f"abi_manifest_id '{self.abi_manifest_id}' must begin with 'abi_'")
        if not re.match(r"^compat_", self.compatibility_ref):
            raise SkillValidationError(f"compatibility_ref '{self.compatibility_ref}' must begin with 'compat_'")
        object.__setattr__(self, "entrypoint_kind", EntrypointKind(self.entrypoint_kind).value)
        object.__setattr__(self, "exported_capabilities", tuple(sorted(set(self.exported_capabilities))))
        object.__setattr__(self, "input_schema_refs", tuple(self.input_schema_refs))
        object.__setattr__(self, "output_schema_refs", tuple(self.output_schema_refs))
        object.__setattr__(self, "permission_refs", tuple(sorted(set(self.permission_refs))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "abi_manifest_id": self.abi_manifest_id,
            "component_id": self.component_id,
            "component_version": self.component_version,
            "entrypoint_kind": self.entrypoint_kind,
            "exported_capabilities": list(self.exported_capabilities),
            "input_schema_refs": list(self.input_schema_refs),
            "output_schema_refs": list(self.output_schema_refs),
            "permission_refs": list(self.permission_refs),
            "compatibility_ref": self.compatibility_ref,
            "artifact_digest": dict(self.artifact_digest),
        }

    def validate(self) -> "ComponentABIManifest":
        validate_abi_manifest_document(self.to_dict())
        return self


def validate_abi_manifest_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "component_abi_manifest.schema.json", SkillValidationError)
    except Exception as exc:
        raise SkillValidationError(str(exc)) from exc


def create_component_abi_manifest(
    *,
    abi_manifest_id: str,
    component_id: str,
    component_version: str,
    entrypoint_kind: EntrypointKind | str,
    exported_capabilities: Sequence[str],
    input_schema_refs: Sequence[str] = (),
    output_schema_refs: Sequence[str] = (),
    permission_refs: Sequence[str] = (),
    compatibility_ref: str,
    artifact_digest: dict[str, str],
    schema_version: str = "2.1.0",
) -> ComponentABIManifest:
    manifest = ComponentABIManifest(
        schema_version=schema_version,
        abi_manifest_id=abi_manifest_id,
        component_id=component_id,
        component_version=component_version,
        entrypoint_kind=entrypoint_kind.value if isinstance(entrypoint_kind, EntrypointKind) else str(entrypoint_kind),
        exported_capabilities=tuple(exported_capabilities),
        input_schema_refs=tuple(input_schema_refs),
        output_schema_refs=tuple(output_schema_refs),
        permission_refs=tuple(permission_refs),
        compatibility_ref=compatibility_ref,
        artifact_digest=dict(artifact_digest),
    )
    manifest.validate()
    return manifest
