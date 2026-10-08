"""Executive plane goal-product continuous traceability checking (L9-REQ-EXE-007)."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


class UntraceableWorkGraphError(ValueError):
    """Raised when a work graph node is disconnected from the ProductContract or Goal."""


class GoalProductAlignmentChecker:
    """Continuously checks that work graph nodes remain traceable to ProductContract."""

    @staticmethod
    def check_alignment(
        nodes: Sequence[Mapping[str, Any]],
        expected_product_contract_ref: str,
        expected_goal_ref: str,
    ) -> bool:
        for node in nodes:
            contract_ref = node.get("product_contract_ref")
            goal_ref = node.get("goal_ref")
            if contract_ref != expected_product_contract_ref or goal_ref != expected_goal_ref:
                raise UntraceableWorkGraphError(
                    f"Work graph node '{node.get('node_id')}' is not traceable to "
                    f"ProductContract '{expected_product_contract_ref}' and Goal '{expected_goal_ref}'"
                )
        return True
