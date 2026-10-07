from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _goals():
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build a report.", "directive://12", {"principal_type": "PO", "id": "po"})
    old = ingress.compile_goal(raw, "Build a report", ["Report exists"], constraints=["internal only"], out_of_scope=["Production release"])
    new = dict(old, constraints=["no external service"])
    return ingress, old, new


def test_l9_t_012_semantic_invalidation():
    oracle("L9-REQ-ING-004", "L9-T-012", lambda: _goals()[0].semantic_diff(_goals()[1], _goals()[2])["invalidates_downstream_assets"], lambda: not _goals()[0].semantic_diff(_goals()[1], _goals()[2])["invalidates_downstream_assets"])
