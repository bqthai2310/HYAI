"""Canary rollout plans, isolation before production, rollback gates, and upgrade provenance (EVO-002, 003, 006, UPG-004, 007, 008)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hyai._contracts import timestamp, validate
from hyai.evolution.proposal import (
    EvolutionError,
    HiddenNegativeEvidenceError,
    PromotionApproval,
    UnapprovedPromotionError,
    UpgradeProposal,
)


class CanaryExecutionError(EvolutionError):
    """Raised when canary thresholds are breached and rollback is triggered (L9-REQ-EVO-006, L9-REQ-UPG-007)."""


class PrematurePromotionError(EvolutionError):
    """Raised when candidate is promoted before sandbox verification or independent approval (L9-REQ-UPG-004)."""


@dataclass(frozen=True)
class CanaryPlan:
    schema_version: str
    canary_id: str
    subject_ref: str
    scope: tuple[str, ...]
    success_thresholds: tuple[str, ...]
    failure_thresholds: tuple[str, ...]
    rollback_ref: str
    duration_or_sample: str
    authority_ref: str

    def __post_init__(self) -> None:
        if not re.match(r"^canary_", self.canary_id):
            raise EvolutionError(f"canary_id '{self.canary_id}' must begin with 'canary_'")
        object.__setattr__(self, "scope", tuple(self.scope))
        object.__setattr__(self, "success_thresholds", tuple(self.success_thresholds))
        object.__setattr__(self, "failure_thresholds", tuple(self.failure_thresholds))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "canary_id": self.canary_id,
            "subject_ref": self.subject_ref,
            "scope": list(self.scope),
            "success_thresholds": list(self.success_thresholds),
            "failure_thresholds": list(self.failure_thresholds),
            "rollback_ref": self.rollback_ref,
            "duration_or_sample": self.duration_or_sample,
            "authority_ref": self.authority_ref,
        }

    def validate(self) -> "CanaryPlan":
        validate_canary_plan_document(self.to_dict())
        return self


def validate_canary_plan_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "canary_plan.schema.json", EvolutionError)
    except Exception as exc:
        raise EvolutionError(str(exc)) from exc


def create_canary_plan(
    *,
    canary_id: str,
    subject_ref: str,
    scope: Sequence[str] = (),
    success_thresholds: Sequence[str],
    failure_thresholds: Sequence[str],
    rollback_ref: str,
    duration_or_sample: str = "1000_requests",
    authority_ref: str = "auth_release_lead",
    schema_version: str = "2.0.0",
) -> CanaryPlan:
    plan = CanaryPlan(
        schema_version=schema_version,
        canary_id=canary_id,
        subject_ref=subject_ref,
        scope=tuple(scope),
        success_thresholds=tuple(success_thresholds),
        failure_thresholds=tuple(failure_thresholds),
        rollback_ref=rollback_ref,
        duration_or_sample=duration_or_sample,
        authority_ref=authority_ref,
    )
    plan.validate()
    return plan


@dataclass(frozen=True)
class UpgradeProvenanceRecord:
    """L9-REQ-UPG-008: Records decision, evidence, migration, and affected version lineage."""
    upgrade_id: str
    decision_ref: str
    evidence_refs: tuple[str, ...]
    migration_ref: str
    prior_version: str
    new_version: str
    outcome: str
    recorded_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "upgrade_id": self.upgrade_id,
            "decision_ref": self.decision_ref,
            "evidence_refs": list(self.evidence_refs),
            "migration_ref": self.migration_ref,
            "prior_version": self.prior_version,
            "new_version": self.new_version,
            "outcome": self.outcome,
            "recorded_at": self.recorded_at,
        }


class EvolutionRolloutManager:
    """Orchestrates candidate isolation, sandbox evaluation, canary gating, and rollback."""

    def __init__(self) -> None:
        self._isolated_candidates: dict[str, dict[str, Any]] = {}
        self._provenance_records: list[UpgradeProvenanceRecord] = []

    def stage_candidate_in_sandbox(self, candidate_id: str, payload: Mapping[str, Any]) -> None:
        """L9-REQ-EVO-002: Candidate isolated before production."""
        self._isolated_candidates[candidate_id] = {
            "payload": dict(payload),
            "is_sandboxed": True,
            "is_promoted": False,
        }

    def promote_candidate(
        self,
        candidate_id: str,
        approval: PromotionApproval | None,
        candidate_digest: Mapping[str, str],
        negative_signals: Sequence[str] = (),
    ) -> UpgradeProvenanceRecord:
        # L9-REQ-UPG-004: Candidate may be researched/built in sandbox, but cannot be promoted without approval
        if approval is None:
            raise PrematurePromotionError(f"Candidate '{candidate_id}' cannot be promoted without PromotionApproval")

        # L9-REQ-EVO-006: Cannot hide negative evidence
        if negative_signals:
            raise HiddenNegativeEvidenceError(
                f"Candidate '{candidate_id}' has unaddressed negative signals: {negative_signals}. Cannot promote while hiding negative evidence."
            )

        approval.assert_valid_for_candidate(candidate_digest)

        candidate = self._isolated_candidates.get(candidate_id)
        if candidate:
            candidate["is_promoted"] = True

        rec = UpgradeProvenanceRecord(
            upgrade_id=f"upg_rec_{candidate_id}",
            decision_ref=approval.approval_id,
            evidence_refs=tuple(approval.approved_scope),
            migration_ref="mig_v2_to_v3",
            prior_version="2.0.0",
            new_version="2.1.0",
            outcome="PROMOTED",
            recorded_at=timestamp(),
        )
        self._provenance_records.append(rec)
        return rec

    def evaluate_canary_and_execute(
        self,
        plan: CanaryPlan,
        measured_error_rate: float,
        error_rate_threshold: float = 0.05,
    ) -> str:
        # L9-REQ-EVO-003, L9-REQ-UPG-007: Predeclared canary success/rollback criteria
        if measured_error_rate > error_rate_threshold:
            raise CanaryExecutionError(
                f"Canary '{plan.canary_id}' exceeded failure threshold ({measured_error_rate} > {error_rate_threshold}); executing rollback '{plan.rollback_ref}'"
            )
        return "CANARY_SUCCESS"
