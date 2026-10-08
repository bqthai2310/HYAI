"""Skill specification, lifecycle states, side effects, and validation errors."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import sha256_digest, validate


class SkillError(Exception):
    """Base error for skill subsystem."""


class SkillValidationError(SkillError):
    """Raised when a skill fails structural or schema validation."""


class SkillIntegrityError(SkillError):
    """Raised when skill content digest does not match actual bytes."""


class SkillLifecycleError(SkillError):
    """Raised when a skill is in an invalid lifecycle state for the requested operation."""


class SkillEvaluationError(SkillError):
    """Raised when a skill fails evaluation policy criteria."""


class AuthorityElevationError(SkillError):
    """Raised when a skill attempts to elevate authority or exceed granted privileges."""


class SkillCycleError(SkillError):
    """Raised when composite skill composition contains cycles."""


class RecursionLimitExceededError(SkillError):
    """Raised when recursive skill invocation exceeds the configured bound."""


class SkillLifecycleState(str, Enum):
    DRAFT = "DRAFT"
    REGISTERED = "REGISTERED"
    EVALUATING = "EVALUATING"
    QUALIFIED = "QUALIFIED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"


class SideEffectClass(str, Enum):
    NONE = "NONE"
    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    IRREVERSIBLE = "IRREVERSIBLE"


@dataclass(frozen=True)
class SkillSpec:
    schema_version: str
    skill_id: str
    semantic_version: str
    content_digest: dict[str, str]
    provided_capabilities: tuple[str, ...]
    input_schema_refs: tuple[str, ...]
    output_schema_refs: tuple[str, ...]
    permission_profile: tuple[str, ...]
    side_effect_class: str
    failure_semantics: str
    evaluation_policy_ref: str
    lifecycle_state: str
    required_tools: tuple[str, ...] = ()
    required_providers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.match(r"^skill_", self.skill_id):
            raise SkillValidationError(f"skill_id '{self.skill_id}' must begin with 'skill_'")
        if not re.match(r"^\d+\.\d+\.\d+$", self.semantic_version):
            raise SkillValidationError(f"semantic_version '{self.semantic_version}' must match semantic version pattern")
        object.__setattr__(self, "provided_capabilities", tuple(sorted(set(self.provided_capabilities))))
        object.__setattr__(self, "input_schema_refs", tuple(self.input_schema_refs))
        object.__setattr__(self, "output_schema_refs", tuple(self.output_schema_refs))
        object.__setattr__(self, "permission_profile", tuple(sorted(set(self.permission_profile))))
        object.__setattr__(self, "required_tools", tuple(sorted(set(self.required_tools))))
        object.__setattr__(self, "required_providers", tuple(sorted(set(self.required_providers))))
        object.__setattr__(self, "side_effect_class", SideEffectClass(self.side_effect_class).value)
        object.__setattr__(self, "lifecycle_state", SkillLifecycleState(self.lifecycle_state).value)

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "semantic_version": self.semantic_version,
            "content_digest": dict(self.content_digest),
            "provided_capabilities": list(self.provided_capabilities),
            "input_schema_refs": list(self.input_schema_refs),
            "output_schema_refs": list(self.output_schema_refs),
            "permission_profile": list(self.permission_profile),
            "side_effect_class": self.side_effect_class,
            "failure_semantics": self.failure_semantics,
            "evaluation_policy_ref": self.evaluation_policy_ref,
            "lifecycle_state": self.lifecycle_state,
        }
        if self.required_tools:
            doc["required_tools"] = list(self.required_tools)
        if self.required_providers:
            doc["required_providers"] = list(self.required_providers)
        return doc

    def validate(self) -> "SkillSpec":
        validate_skill_spec_document(self.to_dict())
        return self


def validate_skill_spec_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "skill_spec.schema.json", SkillValidationError)
    except Exception as exc:
        raise SkillValidationError(str(exc)) from exc


def create_skill_spec(
    *,
    skill_id: str,
    semantic_version: str,
    content_digest: dict[str, str],
    provided_capabilities: Sequence[str],
    input_schema_refs: Sequence[str] = (),
    output_schema_refs: Sequence[str] = (),
    permission_profile: Sequence[str] = (),
    side_effect_class: SideEffectClass | str = SideEffectClass.NONE,
    failure_semantics: str = "FAIL_FAST",
    evaluation_policy_ref: str = "eval_standard_v1",
    lifecycle_state: SkillLifecycleState | str = SkillLifecycleState.ACTIVE,
    required_tools: Sequence[str] = (),
    required_providers: Sequence[str] = (),
    schema_version: str = "2.1.0",
) -> SkillSpec:
    spec = SkillSpec(
        schema_version=schema_version,
        skill_id=skill_id,
        semantic_version=semantic_version,
        content_digest=content_digest,
        provided_capabilities=tuple(provided_capabilities),
        input_schema_refs=tuple(input_schema_refs),
        output_schema_refs=tuple(output_schema_refs),
        permission_profile=tuple(permission_profile),
        side_effect_class=str(side_effect_class if isinstance(side_effect_class, str) else side_effect_class.value),
        failure_semantics=failure_semantics,
        evaluation_policy_ref=evaluation_policy_ref,
        lifecycle_state=str(lifecycle_state if isinstance(lifecycle_state, str) else lifecycle_state.value),
        required_tools=tuple(required_tools),
        required_providers=tuple(required_providers),
    )
    spec.validate()
    return spec
