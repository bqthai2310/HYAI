"""Executive mandate creation and authority-bound decision checks."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from hyai.compatibility.crypto import compute_digest, validate_digest_spec
from hyai.constitution.authority import Principal, PrincipalType


class MandateError(ValueError):
    """Raised when a proposed mandate exceeds its constitutional scope."""


def _schema() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "schemas" / "executive_mandate.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _principal(value: Principal | Mapping[str, Any]) -> Principal:
    return value if isinstance(value, Principal) else Principal(value["principal_type"], value["id"])


def _principal_dict(value: Principal | Mapping[str, Any]) -> dict[str, str]:
    actor = _principal(value)
    return {"principal_type": actor.principal_type.value, "id": actor.id}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _protected_decision(decision: str) -> bool:
    return bool(re.search(r"(?<![\w-])(?:A3|A4|PO)(?![\w-])", decision, flags=re.IGNORECASE))


class ExecutiveMandateManager:
    """Issues versioned mandates without converting execution into authority."""

    def create_mandate(
        self,
        goal_spec: Mapping[str, Any],
        raw_directive: Mapping[str, Any],
        product_ref: str,
        delegated_decisions: list[str],
        reserved_decisions: list[str],
        time_ceiling: dict[str, Any],
        delivery_expectation: str,
        priority: int,
        risk_envelope_ref: str,
        budget_envelope_ref: str,
        issued_by: Principal | Mapping[str, Any],
        revision: int = 1,
        supersedes_mandate_ref: str | None = None,
    ) -> dict[str, Any]:
        issuer = _principal(issued_by)
        if issuer.principal_type is not PrincipalType.PO:
            raise MandateError("ExecutiveMandate must be issued by a PO")
        raw_ref = raw_directive.get(
            "raw_directive_ref",
            raw_directive.get("source_ref", raw_directive.get("raw_directive_id")),
        )
        raw_text, raw_digest = raw_directive.get("raw_text"), raw_directive.get("digest")
        if not isinstance(raw_ref, str) or not raw_ref or not isinstance(raw_text, str):
            raise MandateError("raw directive reference and exact text are required")
        if raw_digest != compute_digest(raw_text.encode("utf-8")) or not validate_digest_spec(dict(raw_digest)):
            raise MandateError("raw directive digest does not bind its exact text")
        if goal_spec.get("original_input_ref") != raw_ref or goal_spec.get("original_input_digest") != raw_digest:
            raise MandateError("goal provenance does not bind the supplied raw directive")
        exclusions = list(goal_spec.get("out_of_scope", []))
        if not exclusions:
            raise MandateError("explicit_exclusions from GoalSpec are required")
        delegated, reserved = list(delegated_decisions), list(reserved_decisions)
        if not reserved:
            raise MandateError("at least one PO reserved decision is required")
        overlap = set(delegated) & set(reserved)
        if overlap:
            raise MandateError("reserved PO decisions cannot be delegated: " + ", ".join(sorted(overlap)))
        protected = [decision for decision in delegated if _protected_decision(decision)]
        if protected:
            raise MandateError("A3/A4/PO decisions cannot be delegated: " + ", ".join(protected))
        if goal_spec.get("risk_envelope_ref") not in (None, risk_envelope_ref):
            raise MandateError("mandate cannot replace the goal risk envelope")
        if goal_spec.get("budget_envelope_ref") not in (None, budget_envelope_ref):
            raise MandateError("mandate cannot replace the goal budget envelope")

        material = {
            "schema_version": "2.1.0",
            "revision": revision,
            "raw_directive_ref": raw_ref,
            "goal_ref": goal_spec.get("goal_id"),
            "product_ref": product_ref,
            "objective": goal_spec.get("objective"),
            "explicit_exclusions": exclusions,
            "delegated_decisions": delegated,
            "reserved_decisions": reserved,
            "risk_envelope_ref": risk_envelope_ref,
            "budget_envelope_ref": budget_envelope_ref,
            "time_ceiling": dict(time_ceiling),
            "delivery_expectation": delivery_expectation,
            "priority": priority,
            "escalation_triggers": ["outside delegated decisions", "risk or budget envelope breach", "explicit exclusion would be affected"],
            "issued_by": _principal_dict(issuer),
            "lifecycle_state": "ACTIVE",
        }
        mandate_id = "mandate_" + compute_digest(_canonical({**material, "supersedes_mandate_ref": supersedes_mandate_ref}))["value"][:32]
        mandate = {"mandate_id": mandate_id, **material}
        if supersedes_mandate_ref is not None:
            mandate["supersedes_mandate_ref"] = supersedes_mandate_ref
        mandate["content_digest"] = compute_digest(_canonical(mandate))
        errors = list(Draft202012Validator(_schema(), format_checker=FormatChecker()).iter_errors(mandate))
        if errors:
            raise MandateError("; ".join(error.message for error in errors))
        return mandate

    def verify_mandate_authority(
        self, mandate: Mapping[str, Any], acting_principal: Principal | Mapping[str, Any], decision: str
    ) -> tuple[bool, str]:
        actor = _principal(acting_principal)
        if decision in mandate.get("reserved_decisions", []):
            if actor.principal_type is PrincipalType.PO:
                return True, "reserved PO decision"
            return False, "decision is reserved for PO"
        if decision not in mandate.get("delegated_decisions", []):
            return False, "decision is not delegated by this mandate"
        if actor.principal_type is not PrincipalType.PO and _protected_decision(decision):
            return False, "A3/A4/PO decisions cannot be delegated to a non-sovereign principal"
        return True, "decision is within delegated mandate authority"
