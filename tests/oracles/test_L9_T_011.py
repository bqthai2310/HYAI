from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _candidate(flags):
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build a report.", "directive://11", {"principal_type": "PO", "id": "po"})
    return ingress, ingress.compile_goal(raw, "Build a report", ["Report exists"], ambiguity_flags=flags, out_of_scope=["Production release"])


def test_l9_t_011_ambiguity_gate():
    oracle("L9-REQ-ING-003", "L9-T-011", lambda: not _candidate(["deadline unknown"])[0].ambiguity_gate(_candidate(["deadline unknown"])[1])[0], lambda: _candidate(["deadline unknown"])[0].ambiguity_gate(_candidate(["deadline unknown"])[1])[0])
