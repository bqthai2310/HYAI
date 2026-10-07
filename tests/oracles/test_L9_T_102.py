from copy import deepcopy

from hyai.acceptance.compiler import AcceptanceCompilationError, compile_requirement, compile_test_spec
from ._support import ROOT, oracle


def test_l9_t_102():
    spec = compile_requirement("L9-REQ-ORC-003", "L9-T-102", "tests/oracles/test_L9_T_102.py", ROOT)
    oracle("L9-REQ-ORC-003", "L9-T-102", lambda: bool(spec["negative_cases"]), lambda: _bad(spec))


def _bad(spec):
    changed = deepcopy(spec); changed["negative_cases"][0]["fixture_id"] = changed["fixture_bindings"][0]["fixture_id"]
    try:
        compile_test_spec(changed, ROOT)
    except AcceptanceCompilationError:
        return False
    return True
