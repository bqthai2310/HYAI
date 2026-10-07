from .test_L9_T_026 import Store, command
from hyai.kernel import SovereignKernel
from ._support import oracle

def test_l9_t_027_audit_event():
    store = Store(); result = SovereignKernel(store).execute_command(command(0, "event"))
    oracle("L9-REQ-KRN-004", "L9-T-027", lambda: result["event"]["causation_id"] == "event", lambda: "event" not in result)
