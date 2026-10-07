"""Bounded escalation policy for executive decisions."""
from __future__ import annotations

from typing import Any, Mapping


class EscalationController:
    MATERIAL_TRIGGERS = {"AUTHORITY_BREACH", "RISK_BREACH", "BUDGET_BREACH", "SCOPE_CHANGE", "IRREVERSIBLE", "EXTERNAL_COMMITMENT"}

    def evaluate_escalation(self, event: Mapping[str, Any] | None = None, **fields: Any) -> dict[str, Any]:
        candidate = dict(event or {}); candidate.update(fields)
        trigger = str(candidate.get("trigger", "")).upper()
        material = bool(candidate.get("material")) or trigger in self.MATERIAL_TRIGGERS
        routine_reversible = candidate.get("routine", False) and candidate.get("reversible", False) and not material
        escalate = material and not routine_reversible
        return {"escalate": escalate, "decision": "ESCALATE" if escalate else "HANDLE_ROUTINELY", "reason": "material trigger" if escalate else "routine reversible correction", "trigger": trigger or None}
