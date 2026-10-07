from copy import deepcopy

from hyai.acceptance.compiler import AcceptanceCompilationError, build_oracle_result, compile_requirement
from hyai.compatibility import compute_digest
from ._support import ROOT, oracle


def test_l9_t_105():
    spec = compile_requirement("L9-REQ-ORC-006", "L9-T-105", "tests/oracles/test_L9_T_105.py", ROOT)
    spec["verification_kind"] = "EXTERNAL_REVIEW"
    digest = compute_digest(b"external review subject")
    oracle("L9-REQ-ORC-006", "L9-T-105", lambda: build_oracle_result("L9-T-105", digest, "BLOCKED", [{"assertion": spec["expected_assertions"][0], "result": "FAIL"}], ["ev_review"], test_spec=spec)["result"] == "BLOCKED", lambda: _bad(spec, digest))


def _bad(spec, digest):
    try:
        build_oracle_result("L9-T-105", digest, "PASS", [{"assertion": spec["expected_assertions"][0], "result": "PASS"}], ["ev_review"], test_spec=spec)
    except AcceptanceCompilationError:
        return False
    return True
