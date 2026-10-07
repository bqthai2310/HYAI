from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _goal():
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build a report.", "directive://10", {"principal_type": "PO", "id": "po"})
    return ingress.compile_goal(raw, "Build a report", ["Report exists"], out_of_scope=["Production release"])


def test_l9_t_010_goal_compilation():
    oracle("L9-REQ-ING-002", "L9-T-010", lambda: _goal()["goal_id"].startswith("goal_"), lambda: not _goal()["goal_id"].startswith("goal_"))
