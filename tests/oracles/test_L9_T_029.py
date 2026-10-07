from .test_L9_T_026 import Store, command
from hyai.kernel import SovereignKernel
from ._support import oracle

def test_l9_t_029_durable_state():
    store = Store(); SovereignKernel(store).execute_command(command(0, "durable")); restarted = SovereignKernel(store)
    oracle("L9-REQ-KRN-006", "L9-T-029", lambda: restarted.read_state("x")["revision"] == 1, lambda: SovereignKernel(Store()).read_state("x")["revision"] == 1)
