"""Canonical Adaptive Intelligence boundary."""
from hyai.adaptive.strategy import (
    AdaptiveError,
    AdaptivePlane,
    AdaptiveStrategy,
    ConstitutionImmutableError,
    ExplorationBudgetExceededError,
    IrreversibleAdaptationError,
    create_adaptive_strategy,
)

__all__ = [
    "AdaptiveError",
    "AdaptivePlane",
    "AdaptiveStrategy",
    "ConstitutionImmutableError",
    "ExplorationBudgetExceededError",
    "IrreversibleAdaptationError",
    "create_adaptive_strategy",
]
