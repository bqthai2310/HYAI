from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _goal():
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build a report.", "directive://14", {"principal_type": "PO", "id": "po"})
    return ingress.compile_goal(raw, "Build a report", ["Report exists"], out_of_scope=["Production release", "Data deletion"])


def test_l9_t_014_explicit_exclusions():
    oracle("L9-REQ-ING-006", "L9-T-014", lambda: _goal()["out_of_scope"] == ["Production release", "Data deletion"], lambda: _goal()["out_of_scope"] == [])
