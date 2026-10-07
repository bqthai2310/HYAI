from hyai.ports.base import ProviderPort, ReviewPort, StoragePort
from ._support import oracle
def test_l9_t_145_required_ports():
    oracle("L9-REQ-IMP-003","L9-T-145",lambda:all(bool(p.__abstractmethods__) for p in (StoragePort,ProviderPort,ReviewPort)),lambda:hasattr(ProviderPort,"direct_database"))
