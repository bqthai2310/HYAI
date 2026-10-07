from hyai.acceptance.compiler import AcceptanceCompilationError, compile_requirement
from ._support import ROOT, oracle


def test_l9_t_100():
    oracle("L9-REQ-ORC-001", "L9-T-100", lambda: bool(compile_requirement("L9-REQ-ORC-001", "L9-T-100", "tests/oracles/test_L9_T_100.py", ROOT)), _bad)


def _bad():
    try:
        compile_requirement("L9-REQ-ORC-001", "L9-T-100", "tests/oracles/not-present.py", ROOT)
    except AcceptanceCompilationError:
        return False
    return True
