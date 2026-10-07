from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from hyai.constitution.authority import Principal
from hyai.executive import ExecutiveMandateManager, MandateError
from hyai.ingress import NaturalLanguageIngress


def _goal_and_directive() -> tuple[dict, dict]:
    ingress = NaturalLanguageIngress()
    directive = ingress.capture_raw_directive("Deliver analytics; no production deployment.", "directive://po/7", Principal("PO", "po-1"))
    goal = ingress.compile_goal(directive, "Deliver analytics", ["Staging analytics"], out_of_scope=["Production deployment"])
    return goal, directive


def _mandate(**overrides: object) -> dict:
    goal, directive = _goal_and_directive()
    values: dict[str, object] = {
        "goal_spec": goal,
        "raw_directive": directive,
        "product_ref": "product_analytics",
        "delegated_decisions": ["implement approved staging deployment"],
        "reserved_decisions": ["approve production release"],
        "time_ceiling": {"max_duration_seconds": 3600},
        "delivery_expectation": "Provide a staging-ready bundle",
        "priority": 50,
        "risk_envelope_ref": "risk_env_default",
        "budget_envelope_ref": "budget_env_default",
        "issued_by": Principal("PO", "po-1"),
    }
    values.update(overrides)
    return ExecutiveMandateManager().create_mandate(**values)  # type: ignore[arg-type]


def test_mandate_preserves_goal_and_raw_directive_provenance():
    goal, directive = _goal_and_directive()
    mandate = _mandate(goal_spec=goal, raw_directive=directive)
    assert mandate["goal_ref"] == goal["goal_id"]
    assert mandate["raw_directive_ref"] == directive["raw_directive_ref"]
    schema = json.loads((Path(__file__).parents[2] / "schemas" / "executive_mandate.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(mandate))


def test_mandate_requires_po_reservations_and_disallows_hidden_authority():
    with pytest.raises(MandateError, match="reserved"):
        _mandate(reserved_decisions=[])
    with pytest.raises(MandateError, match="A3/A4/PO"):
        _mandate(delegated_decisions=["A3 architecture approval"])
    with pytest.raises(MandateError, match="issued by a PO"):
        _mandate(issued_by=Principal("ARCHITECT", "arch-1"))


def test_mandate_authority_routes_reserved_and_delegated_decisions():
    manager = ExecutiveMandateManager()
    mandate = _mandate()
    assert manager.verify_mandate_authority(mandate, Principal("PO", "po-1"), "approve production release")[0]
    assert not manager.verify_mandate_authority(mandate, Principal("EXECUTOR", "e-1"), "approve production release")[0]
    assert manager.verify_mandate_authority(mandate, Principal("EXECUTOR", "e-1"), "implement approved staging deployment")[0]
    changed = copy.deepcopy(mandate)
    changed["delegated_decisions"] = ["A4 release authorization"]
    assert not manager.verify_mandate_authority(changed, Principal("EXECUTOR", "e-1"), "A4 release authorization")[0]
