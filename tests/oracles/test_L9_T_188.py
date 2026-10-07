from hyai.compatibility import is_stable_core_isolated
from ._support import oracle

def test_l9_t_188_stable_core_isolation():
    oracle("L9-REQ-CMP-001", "L9-T-188", lambda: is_stable_core_isolated("from hyai.kernel import CommandEnvelope"), lambda: is_stable_core_isolated("import boto3"))
