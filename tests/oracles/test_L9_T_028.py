from .test_L9_T_026 import Store, command
from hyai.kernel import PolicyDeniedError, SovereignKernel
from ._support import oracle

def test_l9_t_028_policy_hook():
    def rejected():
        try: SovereignKernel(Store(), lambda _: "DENY").execute_command(command(0, "deny"))
        except PolicyDeniedError: return False
        return True
    oracle("L9-REQ-KRN-005", "L9-T-028", lambda: SovereignKernel(Store(), lambda _: {"status": "ALLOW", "policy_snapshot_id": "p"}).execute_command(command(0, "allow"))["revision"] == 1, rejected)
