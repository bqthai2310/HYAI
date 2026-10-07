from hyai.kernel import SovereignKernel
from ._support import oracle

def test_l9_t_024_kernel_small():
    kernel = SovereignKernel.__new__(SovereignKernel)
    oracle("L9-REQ-KRN-001", "L9-T-024", lambda: kernel.is_small_kernel(), lambda: kernel.is_small_kernel("LLM prompt"))
