from hyai.constitution.authority import Principal
from hyai.executive import ExecutiveMandateManager
from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _mandate():
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build a report; never deploy it.", "directive://148", Principal("PO", "po"))
    goal = ingress.compile_goal(raw, "Build a report", ["Report exists"], out_of_scope=["Production release"])
    return ExecutiveMandateManager().create_mandate(goal, raw, "product_reports", ["implement staging"], ["approve release"], {"max_duration_seconds": 60}, "staging bundle", 10, "risk_env_default", "budget_env_default", Principal("PO", "po")), raw


def test_l9_t_148_preserves_raw_provenance():
    oracle("L9-REQ-EXE-001", "L9-T-148", lambda: _mandate()[0]["raw_directive_ref"] == _mandate()[1]["raw_directive_ref"], lambda: _mandate()[0]["raw_directive_ref"] == "paraphrase://148")
