import pytest
from hyai.constitution.authority import Principal
from hyai.kernel import CommandEnvelope, RevisionConflictError, SovereignKernel
from hyai.ports.base import StoragePort
from ._support import oracle

class Store(StoragePort):
    def __init__(self): self.data = {}
    def get(self, key): return self.data.get(key)
    def put(self, key, value, *, expected_version=None): self.data[key] = dict(value); return "1"

def command(revision, key): return CommandEnvelope(key, "Change", "x", revision, Principal("EXECUTOR", "e"), "a", "p", key, "c", {"v": key}, "r")
def test_l9_t_026_optimistic_concurrency():
    store = Store(); kernel = SovereignKernel(store); kernel.execute_command(command(0, "one"))
    def bad():
        try: kernel.execute_command(command(0, "two"))
        except RevisionConflictError: return False
        return True
    oracle("L9-REQ-KRN-003", "L9-T-026", lambda: kernel.read_state("x")["revision"] == 1, bad)
