from hyai.security.governance import WorkerGrant, enforce_least_privilege
from ._support import oracle
def test_l9_t_070_least_privilege():
    oracle("L9-REQ-SEC-001","L9-T-070",lambda:enforce_least_privilege(WorkerGrant("w",frozenset({"read"}),frozenset({"read"}),frozenset({"read"})))[0],lambda:enforce_least_privilege(WorkerGrant("w",frozenset({"read"}),frozenset({"write"}),frozenset({"read"})))[0])
