import pytest

from hyai.constitution.authority import Principal
from hyai.executive import ExecutiveMandateManager, MandateError
from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _authority_escalation_rejected():
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build report.", "directive://150", Principal("PO", "po"))
    goal = ingress.compile_goal(raw, "Build report", ["Report exists"], out_of_scope=["Production"])
    with pytest.raises(MandateError):
        ExecutiveMandateManager().create_mandate(goal, raw, "product_reports", ["A4 authorize release"], ["approve release"], {"max_duration_seconds": 60}, "staging bundle", 10, "risk_env_default", "budget_env_default", Principal("PO", "po"))
    return True


def test_l9_t_150_no_hidden_delegation():
    oracle("L9-REQ-EXE-003", "L9-T-150", _authority_escalation_rejected, lambda: False)
