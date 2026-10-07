"""Capability resolver, hard constraint matching, context minimization, and explicit fallback."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hyai._contracts import timestamp, validate
from hyai.capabilities.spec import CapabilityError, CapabilitySpec, QualityClass, RiskClass


class ResolverError(CapabilityError):
    """Base error for capability resolution failures."""


class HardcodedModelIdentityError(ResolverError):
    """Tasks must request abstract capabilities, not hard-coded model or worker identities (L9-REQ-CAP-001)."""


class ConstraintSatisfactionError(ResolverError):
    """No candidate satisfies declared hard constraints (L9-REQ-CAP-002)."""


class SilentDowngradeForbiddenError(ResolverError):
    """Silent capability downgrade without explicit event and permissions is forbidden (L9-REQ-CAP-006)."""


_FORBIDDEN_MODEL_PATTERNS = re.compile(
    r"^(gpt-|claude-|gemini-|llama-|mistral-|qwen-|worker-|node-|agent-)",
    re.IGNORECASE,
)

_QUALITY_RANK = {
    QualityClass.STANDARD.value: 1,
    QualityClass.HIGH.value: 2,
    QualityClass.CRITICAL.value: 3,
}

_RISK_RANK = {
    RiskClass.LOW.value: 1,
    RiskClass.MEDIUM.value: 2,
    RiskClass.HIGH.value: 3,
    RiskClass.CRITICAL.value: 4,
}


@dataclass(frozen=True)
class CapabilityRequest:
    task_id: str
    capability_id: str
    required_permissions: tuple[str, ...] = ()
    min_quality_class: str = QualityClass.STANDARD.value
    max_risk_class: str = RiskClass.HIGH.value
    context_payload: Mapping[str, Any] | None = None
    allow_explicit_fallback: bool = False
    fallback_reason: str | None = None

    def __post_init__(self) -> None:
        if _FORBIDDEN_MODEL_PATTERNS.match(self.capability_id.strip()):
            raise HardcodedModelIdentityError(
                f"Requested capability '{self.capability_id}' appears to be a hard-coded model/worker identity. Tasks must request abstract capabilities."
            )
        object.__setattr__(self, "required_permissions", tuple(sorted(set(self.required_permissions))))
        object.__setattr__(self, "min_quality_class", QualityClass(self.min_quality_class).value)
        object.__setattr__(self, "max_risk_class", RiskClass(self.max_risk_class).value)


@dataclass(frozen=True)
class ImplementationCandidate:
    implementation_ref: str
    provided_capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    quality_class: str
    risk_class: str
    estimated_latency_ms: int = 1000
    estimated_cost: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "provided_capabilities", tuple(sorted(set(self.provided_capabilities))))
        object.__setattr__(self, "permissions", tuple(sorted(set(self.permissions))))
        object.__setattr__(self, "quality_class", QualityClass(self.quality_class).value)
        object.__setattr__(self, "risk_class", RiskClass(self.risk_class).value)

    def satisfies_hard_constraints(self, request: CapabilityRequest) -> bool:
        if request.capability_id not in self.provided_capabilities:
            return False
        if not set(request.required_permissions).issubset(set(self.permissions)):
            return False
        if _RISK_RANK[self.risk_class] > _RISK_RANK[request.max_risk_class]:
            return False
        return True


@dataclass(frozen=True)
class FallbackRecord:
    is_fallback: bool
    reason: str
    requested_quality: str
    delivered_quality: str
    authorized_permissions: tuple[str, ...]
    timestamp: str


@dataclass(frozen=True)
class CapabilityPlan:
    schema_version: str
    task_id: str
    plan_id: str
    bindings: tuple[dict[str, Any], ...]
    resolver_revision: str
    policy_snapshot_id: str
    minimized_context: Mapping[str, Any]
    fallback_record: FallbackRecord | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "bindings": list(self.bindings),
            "resolver_revision": self.resolver_revision,
            "policy_snapshot_id": self.policy_snapshot_id,
        }

    def validate(self) -> "CapabilityPlan":
        validate(self.to_dict(), "capability_plan.schema.json", ResolverError)
        return self


class CapabilityResolver:
    """Resolves capabilities to implementations with hard constraints before optimization."""

    def __init__(self, resolver_revision: str = "resolver_v2.1", policy_snapshot_id: str = "pol_snap_default") -> None:
        self.resolver_revision = resolver_revision
        self.policy_snapshot_id = policy_snapshot_id

    def minimize_context(self, context_payload: Mapping[str, Any] | None, capability_id: str) -> dict[str, Any]:
        """Context minimization: worker receives only minimum required context for its capability (L9-REQ-CAP-005)."""
        if not context_payload:
            return {}
        minimized: dict[str, Any] = {}
        for key, value in context_payload.items():
            if "secret" in key.lower() or "password" in key.lower() or "credential" in key.lower():
                continue
            if key in {"task_id", "capability_id", "inputs", "payload", "prompt", capability_id}:
                minimized[key] = value
            elif key.startswith("scope_") and not key.endswith("_unrelated"):
                minimized[key] = value
        return minimized

    def resolve(
        self,
        request: CapabilityRequest,
        candidates: Sequence[ImplementationCandidate],
    ) -> CapabilityPlan:
        matching = [c for c in candidates if c.satisfies_hard_constraints(request)]
        if not matching:
            raise ConstraintSatisfactionError(
                f"No implementation candidate satisfies hard constraints for capability '{request.capability_id}'"
            )

        ideal = [c for c in matching if _QUALITY_RANK[c.quality_class] >= _QUALITY_RANK[request.min_quality_class]]
        fallback_record: FallbackRecord | None = None

        if ideal:
            ideal.sort(key=lambda c: (c.estimated_latency_ms, c.estimated_cost))
            selected = ideal[0]
        else:
            if not request.allow_explicit_fallback:
                raise SilentDowngradeForbiddenError(
                    f"Cannot achieve requested quality class '{request.min_quality_class}'. Silent downgrade is forbidden (L9-REQ-CAP-006)."
                )
            matching.sort(key=lambda c: (c.estimated_latency_ms, c.estimated_cost))
            selected = matching[0]
            fallback_record = FallbackRecord(
                is_fallback=True,
                reason=request.fallback_reason or "Quality degradation fallback authorized",
                requested_quality=request.min_quality_class,
                delivered_quality=selected.quality_class,
                authorized_permissions=tuple(selected.permissions),
                timestamp=timestamp(),
            )

        minimized = self.minimize_context(request.context_payload, request.capability_id)
        plan_id = f"cplan_{request.task_id}_{request.capability_id}"
        bindings = (
            {
                "capability_id": request.capability_id,
                "implementation_ref": selected.implementation_ref,
                "fallback_refs": [c.implementation_ref for c in matching if c != selected],
            },
        )

        plan = CapabilityPlan(
            schema_version="2.1.0",
            task_id=request.task_id,
            plan_id=plan_id,
            bindings=bindings,
            resolver_revision=self.resolver_revision,
            policy_snapshot_id=self.policy_snapshot_id,
            minimized_context=minimized,
            fallback_record=fallback_record,
        )
        plan.validate()
        return plan
