"""Skill execution binding to exact immutable versions and resource leases."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hyai._contracts import timestamp, validate
from hyai.capabilities.worker import LeaseExpiredError, ResourceLease, UnpermittedActionError
from hyai.skills.spec import (
    SkillError,
    SkillIntegrityError,
    SkillSpec,
    SkillValidationError,
)


class BindingError(SkillError):
    """Base error for skill binding failures."""


class UnboundExecutionError(BindingError):
    """Execution attempted without an active, verified skill binding (L9-REQ-SKL-002)."""


@dataclass(frozen=True)
class SkillBinding:
    schema_version: str
    binding_id: str
    task_id: str
    attempt_id: str
    skill_id: str
    skill_version: str
    skill_digest: dict[str, str]
    resolved_capabilities: tuple[str, ...]
    created_at: str
    lease: ResourceLease | None = None

    def __post_init__(self) -> None:
        if not re.match(r"^skillbind_", self.binding_id):
            raise SkillValidationError(f"binding_id '{self.binding_id}' must begin with 'skillbind_'")
        if not re.match(r"^skill_", self.skill_id):
            raise SkillValidationError(f"skill_id '{self.skill_id}' must begin with 'skill_'")
        object.__setattr__(self, "resolved_capabilities", tuple(sorted(set(self.resolved_capabilities))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "binding_id": self.binding_id,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "skill_digest": dict(self.skill_digest),
            "resolved_capabilities": list(self.resolved_capabilities),
            "created_at": self.created_at,
        }

    def validate(self) -> "SkillBinding":
        validate_skill_binding_document(self.to_dict())
        return self

    def assert_bound_to(self, skill: SkillSpec) -> None:
        if self.skill_id != skill.skill_id:
            raise UnboundExecutionError(
                f"Binding skill_id '{self.skill_id}' does not match requested skill '{skill.skill_id}'"
            )
        if self.skill_version != skill.semantic_version:
            raise UnboundExecutionError(
                f"Binding version '{self.skill_version}' does not match requested skill version '{skill.semantic_version}'"
            )
        if self.skill_digest != skill.content_digest:
            raise SkillIntegrityError(
                f"Binding content digest {self.skill_digest} does not match skill digest {skill.content_digest}"
            )

    def assert_executable(self, skill: SkillSpec, action: str) -> None:
        self.assert_bound_to(skill)
        if self.lease is not None:
            self.lease.assert_valid_for(action)


def validate_skill_binding_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "skill_binding.schema.json", SkillValidationError)
    except Exception as exc:
        raise SkillValidationError(str(exc)) from exc


def create_skill_binding(
    *,
    binding_id: str,
    task_id: str,
    attempt_id: str,
    skill_id: str,
    skill_version: str,
    skill_digest: dict[str, str],
    resolved_capabilities: Sequence[str],
    created_at: str | None = None,
    lease: ResourceLease | None = None,
    schema_version: str = "2.1.0",
) -> SkillBinding:
    binding = SkillBinding(
        schema_version=schema_version,
        binding_id=binding_id,
        task_id=task_id,
        attempt_id=attempt_id,
        skill_id=skill_id,
        skill_version=skill_version,
        skill_digest=dict(skill_digest),
        resolved_capabilities=tuple(resolved_capabilities),
        created_at=created_at or timestamp(),
        lease=lease,
    )
    binding.validate()
    return binding
