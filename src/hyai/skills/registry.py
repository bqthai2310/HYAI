"""Canonical Skill Registry, lifecycle management, evaluation gates, and discovery."""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from hyai.skills.spec import (
    SkillEvaluationError,
    SkillLifecycleError,
    SkillLifecycleState,
    SkillSpec,
    SkillValidationError,
    validate_skill_spec_document,
)


class SkillRegistry:
    """Manages skill definitions, lifecycle transitions, and active candidate discovery."""

    def __init__(self) -> None:
        self._skills: dict[tuple[str, str], SkillSpec] = {}
        self._evaluation_results: dict[str, dict[str, Any]] = {}

    def register_skill(self, skill: SkillSpec) -> None:
        key = (skill.skill_id, skill.semantic_version)
        if key in self._skills:
            raise SkillValidationError(f"Skill '{skill.skill_id}@{skill.semantic_version}' is already registered")
        skill.validate()
        self._skills[key] = skill

    def get_skill(self, skill_id: str, semantic_version: str | None = None) -> SkillSpec | None:
        if semantic_version is not None:
            return self._skills.get((skill_id, semantic_version))
        matching = [s for (s_id, _), s in self._skills.items() if s_id == skill_id]
        if not matching:
            return None
        return sorted(matching, key=lambda s: s.semantic_version, reverse=True)[0]

    def record_evaluation(self, policy_ref: str, passed: bool, details: Mapping[str, Any] | None = None) -> None:
        self._evaluation_results[policy_ref] = {
            "passed": passed,
            "details": dict(details or {}),
        }

    def transition_lifecycle(self, skill_id: str, semantic_version: str, target_state: SkillLifecycleState | str) -> SkillSpec:
        current = self.get_skill(skill_id, semantic_version)
        if current is None:
            raise SkillLifecycleError(f"Skill '{skill_id}@{semantic_version}' not found")

        target = SkillLifecycleState(target_state).value

        # Qualification / Activation requires passing evaluation policy (L9-REQ-SKL-004)
        if target in (SkillLifecycleState.QUALIFIED.value, SkillLifecycleState.ACTIVE.value):
            eval_res = self._evaluation_results.get(current.evaluation_policy_ref)
            if not eval_res or not eval_res.get("passed", False):
                raise SkillEvaluationError(
                    f"Skill '{skill_id}' cannot transition to '{target}': "
                    f"evaluation policy '{current.evaluation_policy_ref}' not satisfied"
                )

        updated = SkillSpec(
            schema_version=current.schema_version,
            skill_id=current.skill_id,
            semantic_version=current.semantic_version,
            content_digest=current.content_digest,
            provided_capabilities=current.provided_capabilities,
            input_schema_refs=current.input_schema_refs,
            output_schema_refs=current.output_schema_refs,
            permission_profile=current.permission_profile,
            side_effect_class=current.side_effect_class,
            failure_semantics=current.failure_semantics,
            evaluation_policy_ref=current.evaluation_policy_ref,
            lifecycle_state=target,
            required_tools=current.required_tools,
            required_providers=current.required_providers,
        )
        self._skills[(skill_id, semantic_version)] = updated
        return updated

    def query_active_skills(
        self,
        required_capability: str | None = None,
        max_side_effect: str | None = None,
    ) -> list[SkillSpec]:
        """Returns only ACTIVE skills (excluding QUARANTINED, REVOKED, DRAFT, etc.) (L9-REQ-SKL-007)."""
        candidates: list[SkillSpec] = []
        for skill in self._skills.values():
            if skill.lifecycle_state != SkillLifecycleState.ACTIVE.value:
                continue
            if required_capability is not None and required_capability not in skill.provided_capabilities:
                continue
            candidates.append(skill)
        return candidates
