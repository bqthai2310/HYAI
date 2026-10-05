from hyai.acceptance.compiler import AcceptanceCompilationError, compile_requirement
from ._support import ROOT, oracle
def test_l9_t_003_acceptance_first():
    oracle("L9-REQ-GOV-003", "L9-T-003", lambda: bool(compile_requirement("L9-REQ-GOV-003","L9-T-003","tests/oracles/test_L9_T_003.py",ROOT)), lambda: _missing())
def _missing():
    try: compile_requirement("L9-REQ-GOV-003","L9-T-003","tests/oracles/not-present.py",ROOT)
    except AcceptanceCompilationError: return False
    return True
