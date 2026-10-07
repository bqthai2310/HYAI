"""Oracle test for L9-REQ-FSG-006 / L9-T-201."""
import importlib.util
from ._support import ROOT, oracle

spec = importlib.util.spec_from_file_location("root_guard", ROOT / "scripts/root_guard.py")
root_guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_guard)

def _good() -> bool:
    # Material task records before/after RootGuardResult when filesystem mutation occurs
    snapshot = root_guard.take_snapshot()
    result = root_guard.verify_root(snapshot, task_ref="f08-task-verify")
    return (
        result.get("before_digest") is not None
        and result.get("after_digest") is not None
        and result.get("result") in ("PASS", "FAIL_QUARANTINED")
    )

def _bad() -> bool:
    return False

def test_l9_t_201():
    oracle("L9-REQ-FSG-006", "L9-T-201", _good, _bad)
