"""Cost allocation mapping and hard budget envelope enforcement (OBS-003, OBS-004)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from hyai._contracts import timestamp, validate
from hyai.observability.telemetry import ObservabilityError


class FinOpsError(ObservabilityError):
    """Base error for FinOps and budget subsystem."""


class BudgetExceededError(FinOpsError):
    """Raised when hard budget limit is exceeded before or during resource consumption (L9-REQ-OBS-004)."""


class UnallocatedCostError(FinOpsError):
    """Raised when cost record lacks required goal/task/resource mappings (L9-REQ-OBS-003)."""


@dataclass(frozen=True)
class CostRecord:
    cost_id: str
    goal_id: str
    task_id: str
    resource_ref: str
    amount: float
    currency: str = "USD"
    recorded_at: str = ""

    def __post_init__(self) -> None:
        if not all((self.goal_id, self.task_id, self.resource_ref)):
            raise UnallocatedCostError("CostRecord must explicitly map to goal_id, task_id, and resource_ref (L9-REQ-OBS-003)")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cost_id": self.cost_id,
            "goal_id": self.goal_id,
            "task_id": self.task_id,
            "resource_ref": self.resource_ref,
            "amount": float(self.amount),
            "currency": self.currency,
            "recorded_at": self.recorded_at or timestamp(),
        }


@dataclass(frozen=True)
class BudgetEnvelope:
    schema_version: str
    budget_envelope_id: str
    limits: dict[str, float]
    currency: str = "USD"
    hard_stop_on_exceed: bool = True

    def __post_init__(self) -> None:
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.budget_envelope_id):
            raise FinOpsError("budget_envelope_id must be non-empty identifier")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "budget_envelope_id": self.budget_envelope_id,
            "limits": dict(self.limits),
            "currency": self.currency,
            "hard_stop_on_exceed": bool(self.hard_stop_on_exceed),
        }

    def validate(self) -> "BudgetEnvelope":
        validate_budget_envelope_document(self.to_dict())
        return self


def validate_budget_envelope_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "budget_envelope.schema.json", FinOpsError)
    except Exception as exc:
        raise FinOpsError(str(exc)) from exc


def create_budget_envelope(
    *,
    budget_envelope_id: str,
    limits: Mapping[str, float],
    currency: str = "USD",
    hard_stop_on_exceed: bool = True,
    schema_version: str = "2.1.0",
) -> BudgetEnvelope:
    envelope = BudgetEnvelope(
        schema_version=schema_version,
        budget_envelope_id=budget_envelope_id,
        limits={k: float(v) for k, v in limits.items()},
        currency=currency,
        hard_stop_on_exceed=hard_stop_on_exceed,
    )
    envelope.validate()
    return envelope


class BudgetChecker:
    """Checks hard budget envelopes prior to resource execution (L9-REQ-OBS-004)."""

    def __init__(self, envelope: BudgetEnvelope) -> None:
        self.envelope = envelope
        self.consumed: dict[str, float] = {k: 0.0 for k in envelope.limits}

    def check_and_reserve(self, dimension: str, requested_amount: float) -> None:
        limit = self.envelope.limits.get(dimension)
        if limit is None:
            return
        current = self.consumed.get(dimension, 0.0)
        if current + requested_amount > limit:
            if self.envelope.hard_stop_on_exceed:
                raise BudgetExceededError(
                    f"Hard budget exceeded for '{dimension}': requested {requested_amount} + current {current} > limit {limit}"
                )
        self.consumed[dimension] = current + requested_amount

