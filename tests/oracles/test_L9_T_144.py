from hyai.ports.base import ProviderPort, ReviewPort, StoragePort
from ._support import oracle
def test_l9_t_144_dependency_direction():
    oracle("L9-REQ-IMP-002","L9-T-144",lambda:all(hasattr(p,"__abstractmethods__") for p in (StoragePort,ProviderPort,ReviewPort)),lambda:bool(getattr(StoragePort,"canonical_state",None)))
