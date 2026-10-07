"""Recovery decisions, failure classification, bounded retries, idempotency, and escalation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from hyai._contracts import timestamp, validate
from hyai.workflow.instance import WorkflowError, WorkflowValidationError


class ReliabilityError(WorkflowError):
    """Base error for reliability and recovery subsystem."""


class UnclassifiedFailureError(ReliabilityError):
    """Raised when recovery/correction is attempted without prior structured failure classification (L9-REQ-REL-001)."""


class RetryBudgetExhaustedError(ReliabilityError):
    """Raised when retries exceed configured max attempts or cost/token budget (L9-REQ-REL-002)."""


class DuplicateMutationError(ReliabilityError):
    """Raised when a retry attempts to duplicate a non-idempotent material mutation (L9-REQ-REL-003)."""


class UncompensatedRiskError(ReliabilityError):
    """Raised when a high-risk mutation lacks a registered compensation/rollback plan (L9-REQ-REL-005)."""


class NoProgressDetectedError(ReliabilityError):
    """Raised when cyclical execution or stagnation is detected without progress (L9-REQ-REL-006)."""


class FailureClass(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    CONFIG = "CONFIG"
    AUTH = "AUTH"
    NETWORK = "NETWORK"
    DEPENDENCY = "DEPENDENCY"
    CODE = "CODE"
    TEST = "TEST"
    EVIDENCE = "EVIDENCE"
    PERMISSION = "PERMISSION"
    PROVIDER = "PROVIDER"
    CAPACITY = "CAPACITY"
    NO_PROGRESS = "NO_PROGRESS"
    DATA_CORRUPTION = "DATA_CORRUPTION"
    EXTERNAL_BLOCKER = "EXTERNAL_BLOCKER"


class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    RESUME = "RESUME"
    ROLLBACK = "ROLLBACK"
    COMPENSATE = "COMPENSATE"
    ESCALATE = "ESCALATE"
    ABORT = "ABORT"


@dataclass(frozen=True)
class RecoveryDecision:
    schema_version: str
    recovery_id: str
    attempt_id: str
    failure_class: str
    action: str
    reason: str
    retry_count: int
    policy_snapshot_id: str
    producer: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^attempt_", self.attempt_id):
            raise WorkflowValidationError(f"attempt_id '{self.attempt_id}' must begin with 'attempt_'")
        object.__setattr__(self, "failure_class", FailureClass(self.failure_class).value)
        object.__setattr__(self, "action", RecoveryAction(self.action).value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recovery_id": self.recovery_id,
            "attempt_id": self.attempt_id,
            "failure_class": self.failure_class,
            "action": self.action,
            "reason": self.reason,
            "retry_count": int(self.retry_count),
            "policy_snapshot_id": self.policy_snapshot_id,
            "producer": dict(self.producer),
        }

    def validate(self) -> "RecoveryDecision":
        validate_recovery_decision_document(self.to_dict())
        return self


def validate_recovery_decision_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "recovery_decision.schema.json", WorkflowValidationError)
    except Exception as exc:
        raise WorkflowValidationError(str(exc)) from exc


def create_recovery_decision(
    *,
    recovery_id: str,
    attempt_id: str,
    failure_class: FailureClass | str,
    action: RecoveryAction | str,
    reason: str,
    retry_count: int = 0,
    policy_snapshot_id: str = "pol_snap_default",
    producer: Mapping[str, str] | None = None,
    schema_version: str = "2.1.0",
) -> RecoveryDecision:
    prod = dict(producer or {"principal_type": "EXECUTOR", "id": "hermes"})
    decision = RecoveryDecision(
        schema_version=schema_version,
        recovery_id=recovery_id,
        attempt_id=attempt_id,
        failure_class=str(failure_class if isinstance(failure_class, str) else failure_class.value),
        action=str(action if isinstance(action, str) else action.value),
        reason=reason,
        retry_count=retry_count,
        policy_snapshot_id=policy_snapshot_id,
        producer=prod,
    )
    decision.validate()
    return decision


class RecoveryEngine:
    """Enforces reliability invariants: classification, bounded budget, idempotency, compensation, and progress."""

    def __init__(self, max_retries: int = 3, max_budget_credits: float = 10.0) -> None:
        self.max_retries = max_retries
        self.max_budget_credits = max_budget_credits
        self.executed_mutations: set[str] = set()
        self.compensation_handlers: dict[str, Callable[[], None]] = {}
        self.state_history: list[str] = []

    def classify_and_decide(
        self,
        attempt_id: str,
        error: Exception | None,
        failure_class: FailureClass | str | None,
        retry_count: int,
        credits_spent: float = 0.0,
    ) -> RecoveryDecision:
        # L9-REQ-REL-001: Failure must be classified before correction
        if failure_class is None:
            raise UnclassifiedFailureError("Cannot decide recovery action: failure class is unclassified")

        fc = FailureClass(failure_class).value

        # L9-REQ-REL-002: Bounded retry + budget limit
        if retry_count >= self.max_retries or credits_spent >= self.max_budget_credits:
            raise RetryBudgetExhaustedError(
                f"Retry budget exhausted: retry_count={retry_count}/{self.max_retries}, credits={credits_spent}/{self.max_budget_credits}"
            )

        action = RecoveryAction.RETRY.value if fc in (FailureClass.TRANSIENT.value, FailureClass.NETWORK.value) else RecoveryAction.ESCALATE.value
        return create_recovery_decision(
            recovery_id=f"rec_{attempt_id}_{retry_count}",
            attempt_id=attempt_id,
            failure_class=fc,
            action=action,
            reason=f"Recovery decision for {fc}: {str(error) if error else 'No exception'}",
            retry_count=retry_count,
        )

    def execute_mutation(self, mutation_id: str, is_high_risk: bool = False, has_compensation: bool = False) -> None:
        # L9-REQ-REL-003: Retry cannot duplicate material mutation (idempotency enforcement)
        if mutation_id in self.executed_mutations:
            raise DuplicateMutationError(f"Duplicate material mutation '{mutation_id}' rejected by idempotency check")

        # L9-REQ-REL-005: High-risk change requires rollback/compensation
        if is_high_risk and not has_compensation:
            raise UncompensatedRiskError(f"High-risk mutation '{mutation_id}' lacks registered compensation or rollback plan")

        self.executed_mutations.add(mutation_id)

    def record_progress_state(self, state_fingerprint: str) -> None:
        # L9-REQ-REL-006: Detect no-progress and escalate (e.g. repeated identical state 3 times)
        self.state_history.append(state_fingerprint)
        if len(self.state_history) >= 3 and len(set(self.state_history[-3:])) == 1:
            raise NoProgressDetectedError(
                f"No-progress detected: identical state '{state_fingerprint}' repeated across 3 consecutive iterations"
            )
