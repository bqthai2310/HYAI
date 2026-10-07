from copy import deepcopy

from hyai.acceptance.compiler import AcceptanceCompilationError, OracleRegistry, compile_requirement
from ._support import ROOT, oracle


def test_l9_t_101():
    registry = OracleRegistry(ROOT)
    spec = compile_requirement("L9-REQ-ORC-002", "L9-T-101", "tests/oracles/test_L9_T_101.py", ROOT)
    registry.register_test_spec(spec)
    oracle("L9-REQ-ORC-002", "L9-T-101", lambda: registry.get_test_spec("L9-T-101")["expected_assertions"] == spec["expected_assertions"], lambda: _bad(registry, spec))


def _bad(registry, spec):
    changed = deepcopy(spec); changed["expected_assertions"] = ["post-execution assertion"]
    try:
        registry.register_test_spec(changed)
    except AcceptanceCompilationError:
        return False
    return True
