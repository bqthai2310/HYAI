from .test_L9_T_026 import Store
from hyai.kernel import HiddenWriteError, SovereignKernel
from ._support import oracle

def test_l9_t_030_no_hidden_writes():
    kernel = SovereignKernel(Store())
    def bypass():
        try: kernel.write_state("x", {})
        except HiddenWriteError: return False
        return True
    oracle("L9-REQ-KRN-007", "L9-T-030", lambda: hasattr(kernel, "execute_command"), bypass)
