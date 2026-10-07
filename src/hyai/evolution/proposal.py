"""Evolution proposals, upgrade tiers, promotion approval, and self-authorization guards (EVO-001, 004, 005, UPG-002..006)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest


class EvolutionError(Exception):
    """Base error for evolution subsystem."""


class SelfPromotionForbiddenError(EvolutionError):
    """Raised when evolution creator/controller attempts to issue its own PromotionApproval (L9-REQ-EVO-004, L9-REQ-UPG-006)."""


class StaleApprovalError(EvolutionError):
    """Raised when PromotionApproval is evaluated against a changed/tampered candidate digest (L9-REQ-UPG-005)."""


class MisclassifiedTierError(EvolutionError):
    """Raised when a material architecture upgrade is misclassified as minor runtime adaptation (L9-REQ-UPG-003)."""


class UnapprovedPromotionError(EvolutionError):
    """Raised when candidate is promoted before obtaining independent approval (L9-REQ-UPG-004)."""


class HiddenNegativeEvidenceError(EvolutionError):
    """Raised when negative evidence or failure signals are omitted from proposal (L9-REQ-EVO-006)."""


class UpgradeTier(str, Enum):
    T1_MANAGED_COMPONENT = "T1_MANAGED_COMPONENT"
    T2_ARCHITECTURE = "T2_ARCHITECTURE"
    T3_CONSTITUTIONAL = "T3_CONSTITUTIONAL"


class UpgradeLifecycleState(str, Enum):
    RESEARCHING = "RESEARCHING"
    PROPOSED = "PROPOSED"
    CANDIDATE_BUILT = "CANDIDATE_BUILT"
    VERIFIED = "VERIFIED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True)
class EvolutionProposal:
    schema_version: str
    proposal_id: str
    problem: str
    evidence_refs: tuple[str, ...]
    affected_invariants: tuple[str, ...]
    proposed_change: str
    expected_benefit: str
    blast_radius: str
    acceptance_ref: str
    rollback_ref: str
    reversibility: str
    required_authority: str
    status: str
    producer: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^evo_", self.proposal_id):
            raise EvolutionError(f"proposal_id '{self.proposal_id}' must begin with 'evo_'")
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "affected_invariants", tuple(self.affected_invariants))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "problem": self.problem,
            "evidence_refs": list(self.evidence_refs),
            "affected_invariants": list(self.affected_invariants),
            "proposed_change": self.proposed_change,
            "expected_benefit": self.expected_benefit,
            "blast_radius": self.blast_radius,
            "acceptance_ref": self.acceptance_ref,
            "rollback_ref": self.rollback_ref,
            "reversibility": self.reversibility,
            "required_authority": self.required_authority,
            "status": self.status,
            "producer": dict(self.producer),
        }

    def validate(self) -> "EvolutionProposal":
        validate_evolution_proposal_document(self.to_dict())
        return self


def validate_evolution_proposal_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "evolution_proposal.schema.json", EvolutionError)
    except Exception as exc:
        raise EvolutionError(str(exc)) from exc


def create_evolution_proposal(
    *,
    proposal_id: str,
    problem: str,
    evidence_refs: Sequence[str],
    affected_invariants: Sequence[str],
    proposed_change: str,
    expected_benefit: str,
    blast_radius: str,
    acceptance_ref: str,
    rollback_ref: str,
    reversibility: str = "REVERSIBLE",
    required_authority: str = "A3",
    status: str = "DRAFT",
    producer: Mapping[str, str] | None = None,
    schema_version: str = "2.0.0",
) -> EvolutionProposal:
    prod = dict(producer or {"principal_type": "EVOLUTION_CONTROLLER", "id": "evo_agent_01"})
    proposal = EvolutionProposal(
        schema_version=schema_version,
        proposal_id=proposal_id,
        problem=problem,
        evidence_refs=tuple(evidence_refs),
        affected_invariants=tuple(affected_invariants),
        proposed_change=proposed_change,
        expected_benefit=expected_benefit,
        blast_radius=blast_radius,
        acceptance_ref=acceptance_ref,
        rollback_ref=rollback_ref,
        reversibility=reversibility,
        required_authority=required_authority,
        status=status,
        producer=prod,
    )
    proposal.validate()
    return proposal


@dataclass(frozen=True)
class UpgradeProposal:
    schema_version: str
    upgrade_proposal_id: str
    signal_refs: tuple[str, ...]
    tier: str
    current_subject_refs: tuple[str, ...]
    candidate_subject_refs: tuple[str, ...]
    expected_benefit: str
    material_risks: tuple[str, ...]
    evaluation_refs: tuple[str, ...]
    lifecycle_state: str
    created_by: dict[str, str]
    content_digest: dict[str, str]
    approval_required: bool = True

    def __post_init__(self) -> None:
        if not re.match(r"^upgradeproposal_", self.upgrade_proposal_id):
            raise EvolutionError(f"upgrade_proposal_id '{self.upgrade_proposal_id}' must begin with 'upgradeproposal_'")
        object.__setattr__(self, "tier", UpgradeTier(self.tier).value)
        object.__setattr__(self, "lifecycle_state", UpgradeLifecycleState(self.lifecycle_state).value)
        object.__setattr__(self, "signal_refs", tuple(self.signal_refs))
        object.__setattr__(self, "current_subject_refs", tuple(self.current_subject_refs))
        object.__setattr__(self, "candidate_subject_refs", tuple(self.candidate_subject_refs))
        object.__setattr__(self, "material_risks", tuple(self.material_risks))
        object.__setattr__(self, "evaluation_refs", tuple(self.evaluation_refs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "upgrade_proposal_id": self.upgrade_proposal_id,
            "signal_refs": list(self.signal_refs),
            "tier": self.tier,
            "current_subject_refs": list(self.current_subject_refs),
            "candidate_subject_refs": list(self.candidate_subject_refs),
            "expected_benefit": self.expected_benefit,
            "material_risks": list(self.material_risks),
            "evaluation_refs": list(self.evaluation_refs),
            "approval_required": True,
            "lifecycle_state": self.lifecycle_state,
            "created_by": dict(self.created_by),
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "UpgradeProposal":
        validate_upgrade_proposal_document(self.to_dict())
        return self


def validate_upgrade_proposal_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "upgrade_proposal.schema.json", EvolutionError)
    except Exception as exc:
        raise EvolutionError(str(exc)) from exc


def create_upgrade_proposal(
    *,
    upgrade_proposal_id: str,
    signal_refs: Sequence[str],
    tier: UpgradeTier | str,
    current_subject_refs: Sequence[str],
    candidate_subject_refs: Sequence[str] = (),
    expected_benefit: str,
    material_risks: Sequence[str] = (),
    evaluation_refs: Sequence[str] = (),
    lifecycle_state: UpgradeLifecycleState | str = UpgradeLifecycleState.PROPOSED,
    created_by: Mapping[str, str] | None = None,
    schema_version: str = "2.1.0",
) -> UpgradeProposal:
    t = tier.value if isinstance(tier, UpgradeTier) else str(tier)
    ls = lifecycle_state.value if isinstance(lifecycle_state, UpgradeLifecycleState) else str(lifecycle_state)
    creator = dict(created_by or {"principal_type": "EVOLUTION_CONTROLLER", "id": "evo_lead"})

    payload = {
        "upgrade_proposal_id": upgrade_proposal_id,
        "signal_refs": tuple(signal_refs),
        "tier": t,
        "current_subject_refs": tuple(current_subject_refs),
        "candidate_subject_refs": tuple(candidate_subject_refs),
        "expected_benefit": expected_benefit,
        "material_risks": tuple(material_risks),
        "evaluation_refs": tuple(evaluation_refs),
        "lifecycle_state": ls,
        "created_by": creator,
    }
    digest = compute_digest(canonical(payload))
    proposal = UpgradeProposal(
        schema_version=schema_version,
        upgrade_proposal_id=upgrade_proposal_id,
        signal_refs=tuple(signal_refs),
        tier=t,
        current_subject_refs=tuple(current_subject_refs),
        candidate_subject_refs=tuple(candidate_subject_refs),
        expected_benefit=expected_benefit,
        material_risks=tuple(material_risks),
        evaluation_refs=tuple(evaluation_refs),
        lifecycle_state=ls,
        created_by=creator,
        content_digest=digest,
    )
    proposal.validate()
    return proposal


@dataclass(frozen=True)
class PromotionApproval:
    schema_version: str
    approval_id: str
    proposal_ref: str
    candidate_subject_digest: dict[str, str]
    approved_scope: tuple[str, ...]
    tier: str
    approver: dict[str, str]
    approval_authority_ref: str
    decision: str
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        if not re.match(r"^promotionapproval_", self.approval_id):
            raise EvolutionError(f"approval_id '{self.approval_id}' must begin with 'promotionapproval_'")
        if not re.match(r"^upgradeproposal_", self.proposal_ref):
            raise EvolutionError(f"proposal_ref '{self.proposal_ref}' must begin with 'upgradeproposal_'")
        object.__setattr__(self, "approved_scope", tuple(self.approved_scope))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "approval_id": self.approval_id,
            "proposal_ref": self.proposal_ref,
            "candidate_subject_digest": dict(self.candidate_subject_digest),
            "approved_scope": list(self.approved_scope),
            "tier": self.tier,
            "approver": dict(self.approver),
            "approval_authority_ref": self.approval_authority_ref,
            "decision": self.decision,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    def validate(self) -> "PromotionApproval":
        validate_promotion_approval_document(self.to_dict())
        return self

    def assert_valid_for_candidate(self, candidate_digest: Mapping[str, str]) -> None:
        # L9-REQ-UPG-005: Stale on changed candidate digest
        if dict(self.candidate_subject_digest) != dict(candidate_digest):
            raise StaleApprovalError(
                f"PromotionApproval '{self.approval_id}' is stale: bound candidate digest does not match current candidate"
            )


def validate_promotion_approval_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "promotion_approval.schema.json", EvolutionError)
    except Exception as exc:
        raise EvolutionError(str(exc)) from exc


def create_promotion_approval(
    *,
    approval_id: str,
    proposal_ref: str,
    candidate_subject_digest: Mapping[str, str],
    approved_scope: Sequence[str],
    tier: UpgradeTier | str,
    approver: Mapping[str, str],
    approval_authority_ref: str,
    decision: str = "APPROVE",
    issued_at: str | None = None,
    expires_at: str = "2099-01-01T00:00:00Z",
    creator_principal_id: str | None = None,
    schema_version: str = "2.1.0",
) -> PromotionApproval:
    t = tier.value if isinstance(tier, UpgradeTier) else str(tier)
    appr = dict(approver)

    # L9-REQ-EVO-004 / L9-REQ-UPG-006: Evolution creator cannot issue its own PromotionApproval
    if creator_principal_id and appr.get("id") == creator_principal_id:
        raise SelfPromotionForbiddenError(
            f"Evolution creator/controller '{creator_principal_id}' cannot issue its own PromotionApproval (L9-REQ-UPG-006)"
        )
    if appr.get("principal_type") == "EVOLUTION_CONTROLLER":
        raise SelfPromotionForbiddenError("EVOLUTION_CONTROLLER cannot approve promotions")

    approval = PromotionApproval(
        schema_version=schema_version,
        approval_id=approval_id,
        proposal_ref=proposal_ref,
        candidate_subject_digest=dict(candidate_subject_digest),
        approved_scope=tuple(approved_scope),
        tier=t,
        approver=appr,
        approval_authority_ref=approval_authority_ref,
        decision=decision,
        issued_at=issued_at or timestamp(),
        expires_at=expires_at,
    )
    approval.validate()
    return approval
