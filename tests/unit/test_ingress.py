from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from hyai.compatibility import compute_digest
from hyai.constitution.authority import Principal
from hyai.ingress import GoalCompilationError, NaturalLanguageIngress


def _directive() -> dict:
    return NaturalLanguageIngress().capture_raw_directive(
        "Deliver the reporting service; do not deploy it to production.", "directive://po/42", Principal("PO", "po-1")
    )


def _goal(ingress: NaturalLanguageIngress, **overrides: object) -> dict:
    values: dict[str, object] = {
        "objective": "Deliver the reporting service",
        "desired_outcomes": ["Service is available in staging"],
        "constraints": ["Use the approved budget"],
        "out_of_scope": ["Production deployment"],
    }
    values.update(overrides)
    return ingress.compile_goal(_directive(), **values)  # type: ignore[arg-type]


def test_capture_preserves_exact_text_and_digest():
    ingress = NaturalLanguageIngress()
    text = "Keep   this exact\nwording."
    directive = ingress.capture_raw_directive(text, "directive://po/exact", {"principal_type": "PO", "id": "po-1"})
    assert directive["raw_text"] == text
    assert directive["digest"] == compute_digest(text.encode("utf-8"))


def test_compile_goal_binds_provenance_and_validates_schema():
    ingress = NaturalLanguageIngress()
    directive = _directive()
    goal = _goal(ingress)
    assert goal["original_input_ref"] == directive["raw_directive_ref"]
    assert goal["original_input_digest"] == directive["digest"]
    schema = json.loads((Path(__file__).parents[2] / "schemas" / "goal_spec.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(goal))


def test_compile_refuses_tampered_directive_or_authority_elevation():
    ingress = NaturalLanguageIngress()
    bad = _directive()
    bad["raw_text"] = "paraphrased source"
    with pytest.raises(GoalCompilationError):
        ingress.compile_goal(bad, "Deliver the reporting service", ["Service is available in staging"], out_of_scope=["Production deployment"])
    directive = _directive()
    directive["authority_envelope_ref"] = "auth_env_low"
    with pytest.raises(GoalCompilationError):
        ingress.compile_goal(directive, "Deliver", ["Done"], authority_envelope_ref="auth_env_higher")


def test_ambiguity_gate_blocks_flags_and_scope_contradictions():
    ingress = NaturalLanguageIngress()
    flagged = _goal(ingress, ambiguity_flags=["deadline is unclear"])
    assert ingress.ambiguity_gate(flagged) == (False, ["ambiguity: deadline is unclear"])
    assert flagged["status"] == "CLARIFICATION_REQUIRED"
    contradictory = _goal(ingress, desired_outcomes=["Production deployment"], out_of_scope=["Production deployment"])
    cleared, reasons = ingress.ambiguity_gate(contradictory)
    assert not cleared and "explicit exclusions" in reasons[0]


def test_semantic_diff_invalidates_only_material_changes():
    ingress = NaturalLanguageIngress()
    prior = _goal(ingress)
    non_material = copy.deepcopy(prior)
    non_material["assumptions"] = ["The data is available"]
    assert not ingress.semantic_diff(prior, non_material)["invalidates_downstream_assets"]
    revised = copy.deepcopy(prior)
    revised["constraints"] = ["No external services"]
    diff = ingress.semantic_diff(prior, revised)
    assert diff["material_changes"] == ["constraints"]
    assert diff["invalidates_downstream_assets"]
