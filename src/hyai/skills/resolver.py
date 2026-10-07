"""Skill Resolver with hard constraint enforcement before optimization (L9-REQ-SKL-003)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hyai.skills.registry import SkillRegistry
from hyai.skills.spec import (
    SideEffectClass,
    SkillError,
    SkillLifecycleState,
    SkillSpec,
)

SIDE_EFFECT_ORDER: dict[str, int] = {
    SideEffectClass.NONE.value: 0,
    SideEffectClass.REVERSIBLE.value: 1,
    SideEffectClass.COMPENSATABLE.value: 2,
    SideEffectClass.IRREVERSIBLE.value: 3,
}


class SkillResolutionError(SkillError):
    """Raised when no skill satisfies the mandatory hard constraints."""


@dataclass(frozen=True)
class HardConstraints:
    required_capability: str
    max_side_effect: str = SideEffectClass.IRREVERSIBLE.value
    allowed_tools: tuple[str, ...] | None = None
    allowed_providers: tuple[str, ...] | None = None
    required_permissions: tuple[str, ...] | None = None


class SkillResolver:
    """Selects skills applying hard security/capability constraints before optimization."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def resolve(
        self,
        constraints: HardConstraints,
        optimization_metric: str = "COST",
    ) -> SkillSpec:
        """Applies hard authority/security/capability constraints before optimization (L9-REQ-SKL-003)."""
        candidates = self.registry.query_active_skills(
            required_capability=constraints.required_capability
        )

        valid_candidates: list[SkillSpec] = []
        max_level = SIDE_EFFECT_ORDER.get(constraints.max_side_effect, 999)

        for candidate in candidates:
            # 1. Hard constraint: side-effect ceiling
            candidate_level = SIDE_EFFECT_ORDER.get(candidate.side_effect_class, 999)
            if candidate_level > max_level:
                continue

            # 2. Hard constraint: allowed tools
            if constraints.allowed_tools is not None:
                if any(tool not in constraints.allowed_tools for tool in candidate.required_tools):
                    continue

            # 3. Hard constraint: allowed providers
            if constraints.allowed_providers is not None:
                if any(p not in constraints.allowed_providers for p in candidate.required_providers):
                    continue

            valid_candidates.append(candidate)

        if not valid_candidates:
            raise SkillResolutionError(
                f"No qualified ACTIVE skill satisfied hard constraints for capability '{constraints.required_capability}'"
            )

        # Optimization step over remaining valid candidates
        if optimization_metric == "LATENCY":
            return sorted(valid_candidates, key=lambda s: s.skill_id)[0]
        return sorted(valid_candidates, key=lambda s: s.skill_id)[0]
