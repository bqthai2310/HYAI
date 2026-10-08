"""Adaptive plane, immutable versioned strategies, exploration limits, and rollback."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp
from hyai.compatibility.crypto import compute_digest


class AdaptiveError(Exception):
    """Base error for adaptive plane."""


class ConstitutionImmutableError(AdaptiveError):
    """Raised when an adaptation attempts to modify Constitution or acceptance baselines (L9-REQ-ADP-003)."""


class ExplorationBudgetExceededError(AdaptiveError):
    """Raised when exploratory adaptation exceeds authorized risk or budget bounds (L9-REQ-ADP-004)."""


class IrreversibleAdaptationError(AdaptiveError):
    """Raised when an adaptation lacks a registered rollback mechanism (L9-REQ-ADP-005)."""


@dataclass(frozen=True)
class AdaptiveStrategy:
    strategy_id: str
    version: int
    parameters: dict[str, Any]
    target_capability: str
    content_digest: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "version": int(self.version),
            "parameters": dict(self.parameters),
            "target_capability": self.target_capability,
            "content_digest": dict(self.content_digest),
        }


def create_adaptive_strategy(
    *,
    strategy_id: str,
    version: int = 1,
    parameters: Mapping[str, Any],
    target_capability: str,
) -> AdaptiveStrategy:
    payload = {
        "strategy_id": strategy_id,
        "version": int(version),
        "parameters": dict(parameters),
        "target_capability": target_capability,
    }
    digest = compute_digest(canonical(payload))
    return AdaptiveStrategy(
        strategy_id=strategy_id,
        version=version,
        parameters=dict(parameters),
        target_capability=target_capability,
        content_digest=digest,
    )


class AdaptivePlane:
    """Manages telemetry-driven strategy adaptation under constitutional guards."""

    def __init__(self, max_exploration_budget: float = 100.0) -> None:
        self.max_exploration_budget = max_exploration_budget
        self._history: list[AdaptiveStrategy] = []
        self._telemetry_samples: list[dict[str, Any]] = []

    def record_telemetry(self, telemetry: Mapping[str, Any]) -> None:
        """L9-REQ-ADP-001: Adaptive plane learns from execution and review telemetry."""
        self._telemetry_samples.append(dict(telemetry))

    def adapt_strategy(
        self,
        base_strategy: AdaptiveStrategy,
        proposed_parameters: Mapping[str, Any],
        exploration_cost: float = 0.0,
        reversible: bool = True,
    ) -> AdaptiveStrategy:
        # L9-REQ-ADP-003: Adaptation cannot change Constitution or acceptance criteria
        forbidden_keys = {"constitution", "acceptance_criteria", "core_invariants", "root_guard"}
        if any(k in proposed_parameters for k in forbidden_keys):
            raise ConstitutionImmutableError(
                "Adaptation cannot modify Constitution or frozen acceptance criteria (L9-REQ-ADP-003)"
            )

        # L9-REQ-ADP-004: Exploration controlled by risk and budget
        if exploration_cost > self.max_exploration_budget:
            raise ExplorationBudgetExceededError(
                f"Exploration cost {exploration_cost} exceeds authorized budget {self.max_exploration_budget}"
            )

        # L9-REQ-ADP-005: Adaptive change must be reversible
        if not reversible:
            raise IrreversibleAdaptationError("All adaptive strategy changes must have an explicit rollback mechanism")

        self._history.append(base_strategy)
        return create_adaptive_strategy(
            strategy_id=base_strategy.strategy_id,
            version=base_strategy.version + 1,
            parameters=proposed_parameters,
            target_capability=base_strategy.target_capability,
        )

    def rollback(self) -> AdaptiveStrategy:
        if not self._history:
            raise AdaptiveError("No prior strategy version available for rollback")
        return self._history.pop()
