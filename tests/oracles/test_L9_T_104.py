from copy import deepcopy

from hyai.acceptance.compiler import AcceptanceCompilationError, compile_requirement, compile_test_spec
from ._support import ROOT, oracle


def test_l9_t_104():
    spec = compile_requirement("L9-REQ-ORC-005", "L9-T-104", "tests/oracles/test_L9_T_104.py", ROOT)
    oracle("L9-REQ-ORC-005", "L9-T-104", lambda: bool(compile_test_spec(spec, ROOT)), lambda: _bad(spec))


def _bad(spec):
    changed = deepcopy(spec); changed["fixture_bindings"][0]["digest"]["value"] = "0" * 64
    try:
        compile_test_spec(changed, ROOT)
    except AcceptanceCompilationError:
        return False
    return True
