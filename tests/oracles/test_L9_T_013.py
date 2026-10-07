import pytest

from hyai.ingress import GoalCompilationError, NaturalLanguageIngress
from ._support import oracle


def _elevation_rejected():
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build a report.", "directive://13", {"principal_type": "PO", "id": "po"})
    raw["authority_envelope_ref"] = "auth_env_low"
    with pytest.raises(GoalCompilationError):
        ingress.compile_goal(raw, "Build a report", ["Report exists"], authority_envelope_ref="auth_env_high")
    return True


def test_l9_t_013_no_authority_inference():
    oracle("L9-REQ-ING-005", "L9-T-013", _elevation_rejected, lambda: False)
