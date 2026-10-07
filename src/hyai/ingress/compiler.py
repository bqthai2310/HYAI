"""Natural-language goal ingress with immutable source provenance."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker

from hyai.compatibility import compute_digest, validate_digest_spec
from hyai.constitution.authority import AuthorityClass, Principal, can_authorize


class GoalCompilationError(ValueError):
    """Raised when an input cannot be safely compiled into a GoalSpec."""


def _goal_schema() -> dict[str, Any]:
    schema_path = Path(__file__).resolve().parents[3] / "schemas" / "goal_spec.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _principal_dict(value: Principal | Mapping[str, Any]) -> dict[str, str]:
    principal = value if isinstance(value, Principal) else Principal(value["principal_type"], value["id"])
    return {"principal_type": principal.principal_type.value, "id": principal.id}


def _authority_claims(value: Mapping[str, Any]) -> list[str]:
    """Return explicit authority-class claims made by an untrusted directive."""
    claims: list[str] = []
    for field in ("authority_class", "authority_class_max", "required_class"):
        claimed = value.get(field)
        if isinstance(claimed, str):
            claims.append(claimed)

    authority = value.get("authority")
    if isinstance(authority, str):
        claims.append(authority)
    for container_name in ("authority", "authority_envelope", "principal"):
        container = value.get(container_name)
        if isinstance(container, Mapping):
            for field in ("authority_class", "authority_class_max", "required_class"):
                claimed = container.get(field)
                if isinstance(claimed, str):
                    claims.append(claimed)
    return claims


def _validate_authority(raw_directive: Mapping[str, Any], principal: Principal, authority_ref: str) -> None:
    """Reject authority escalation instead of silently interpreting it."""
    supplied_ref = raw_directive.get("authority_envelope_ref")
    if supplied_ref is not None and supplied_ref != authority_ref:
        raise GoalCompilationError("goal cannot elevate the directive authority envelope")

    for claim in _authority_claims(raw_directive):
        try:
            authority_class = AuthorityClass(claim)
        except ValueError as error:
            raise GoalCompilationError("invalid authority claim") from error
        if not can_authorize(principal, authority_class):
            raise GoalCompilationError("principal cannot claim the requested authority class")


class NaturalLanguageIngress:
    """Capture exact language before compiling a validated, bounded goal."""

    def capture_raw_directive(
        self, raw_text: str, source_ref: str, principal: Principal | dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(raw_text, str):
            raise GoalCompilationError("raw_text must be a string")
        if not isinstance(source_ref, str) or not source_ref:
            raise GoalCompilationError("source_ref is required")

        raw_directive_id = f"raw_dir_{uuid4().hex[:12]}"
        raw_digest = compute_digest(raw_text.encode("utf-8"))
        return {
            "schema_version": "2.1.0",
            "raw_directive_id": raw_directive_id,
            "raw_directive_ref": source_ref,
            "source_ref": source_ref,
            "digest": raw_digest,
            "source_digest": raw_digest,
            "raw_text": raw_text,
            "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "principal": _principal_dict(principal),
        }

    def compile_goal(
        self,
        raw_directive: dict[str, Any],
        objective: str,
        desired_outcomes: list[str],
        constraints: list[str] | None = None,
        out_of_scope: list[str] | None = None,
        assumptions: list[str] | None = None,
        ambiguity_flags: list[str] | None = None,
        success_metrics: list[dict[str, Any]] | None = None,
        acceptance_intent: list[str] | None = None,
        authority_envelope_ref: str = "auth_env_default",
        risk_envelope_ref: str = "risk_env_default",
        budget_envelope_ref: str = "budget_env_default",
        decomposition_policy: str = "AUTO_WITHIN_ENVELOPE",
    ) -> dict[str, Any]:
        if not isinstance(raw_directive, Mapping):
            raise GoalCompilationError("raw_directive must be an object")

        try:
            producer_value = raw_directive.get("principal", raw_directive.get("producer"))
            producer = producer_value if isinstance(producer_value, Principal) else Principal(
                producer_value["principal_type"], producer_value["id"]
            )
        except (KeyError, TypeError, ValueError) as error:
            raise GoalCompilationError("raw directive principal is required") from error
        _validate_authority(raw_directive, producer, authority_envelope_ref)

        raw_text = raw_directive.get("raw_text", "")
        if not isinstance(raw_text, str):
            raise GoalCompilationError("raw directive raw_text must be a string")
        original_digest = raw_directive.get(
            "digest", raw_directive.get("source_digest", compute_digest(raw_text.encode("utf-8")))
        )
        if not isinstance(original_digest, dict) or not validate_digest_spec(original_digest):
            raise GoalCompilationError("raw directive digest is invalid")
        expected_digest = compute_digest(raw_text.encode("utf-8"))
        for digest_field in ("digest", "source_digest"):
            if digest_field in raw_directive and raw_directive[digest_field] != expected_digest:
                raise GoalCompilationError(f"raw directive {digest_field} does not bind raw_text")

        goal = {
            "schema_version": "2.1.0",
            "goal_id": f"goal_{uuid4().hex[:12]}",
            "original_input_ref": raw_directive.get(
                "raw_directive_ref",
                raw_directive.get("raw_directive_id", raw_directive.get("source_ref", "raw_dir_default")),
            ),
            "original_input_digest": original_digest,
            "objective": objective,
            "desired_outcomes": list(desired_outcomes),
            "constraints": list(constraints or []),
            "out_of_scope": list(out_of_scope or []),
            "assumptions": list(assumptions or []),
            "ambiguity_flags": list(ambiguity_flags or []),
            "authority_envelope_ref": authority_envelope_ref,
            "risk_envelope_ref": risk_envelope_ref,
            "budget_envelope_ref": budget_envelope_ref,
            "success_metrics": list(success_metrics or []),
            "acceptance_intent": list(acceptance_intent or []),
            "decomposition_policy": decomposition_policy,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "producer": _principal_dict(producer),
        }
        errors = list(Draft202012Validator(_goal_schema(), format_checker=FormatChecker()).iter_errors(goal))
        if errors:
            raise GoalCompilationError("; ".join(error.message for error in errors))
        return goal

    def ambiguity_gate(self, candidate_goal: dict[str, Any]) -> tuple[bool, list[str]]:
        reasons = [f"ambiguity: {flag}" for flag in candidate_goal.get("ambiguity_flags", [])]
        exclusions = {
            item.strip().casefold()
            for item in candidate_goal.get("out_of_scope", [])
            if isinstance(item, str) and item.strip()
        }
        conflicts = [
            item
            for field in ("desired_outcomes", "constraints")
            for item in candidate_goal.get(field, [])
            if isinstance(item, str) and item.strip().casefold() in exclusions
        ]
        if conflicts:
            reasons.append(
                "desired outcomes conflict with explicit exclusions: " + ", ".join(conflicts)
            )
        if reasons:
            # This is workflow state, deliberately applied only after the
            # schema-valid GoalSpec has been compiled.
            candidate_goal["status"] = "CLARIFICATION_REQUIRED"
            return False, reasons
        return True, reasons

    def semantic_diff(self, prior_goal: dict[str, Any], new_goal: dict[str, Any]) -> dict[str, Any]:
        diff = {
            field: {"prior": prior_goal.get(field), "new": new_goal.get(field)}
            for field in ("objective", "desired_outcomes", "constraints", "out_of_scope")
            if prior_goal.get(field) != new_goal.get(field)
        }
        changed = bool(diff)
        material_changes = [
            field for field in ("objective", "desired_outcomes", "constraints") if field in diff
        ]
        return {
            "changed": changed,
            "diff": diff,
            "changes": diff,
            "material_changes": material_changes,
            "invalidates_downstream": bool(material_changes),
            "invalidates_downstream_assets": bool(material_changes),
            # Retained for callers of the earlier ingress contract.
            "invalidated_downstream": changed,
        }
