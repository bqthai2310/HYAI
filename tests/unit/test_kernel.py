from hyai.constitution.authority import Principal
from hyai.kernel import CommandEnvelope, IdempotencyConflictError, RevisionConflictError, SovereignKernel
from hyai.ports.base import StoragePort
import pytest


class MemoryStorage(StoragePort):
    def __init__(self): self.records = {}
    def get(self, key): return self.records.get(key)
    def put(self, key, value, *, expected_version=None): self.records[key] = dict(value); return str(len(self.records))


def command(revision=0, key="k", payload=None):
    return CommandEnvelope(key, "SetValue", "aggregate", revision, Principal("EXECUTOR", "worker"), "authority", "policy", key, "correlation", payload or {"value": 1}, "unit test")


def test_kernel_durable_idempotent_mutation_and_audit():
    storage = MemoryStorage(); result = SovereignKernel(storage).execute_command(command())
    replay = SovereignKernel(storage).execute_command(command())
    assert replay == result and result["event"]["aggregate_revision"] == 1


def test_kernel_rejects_lost_update_and_changed_idempotency_payload():
    kernel = SovereignKernel(MemoryStorage()); kernel.execute_command(command())
    with pytest.raises(RevisionConflictError, match="REVISION_CONFLICT"):
        kernel.execute_command(command(0, "new"))
    with pytest.raises(IdempotencyConflictError):
        kernel.execute_command(command(1, "k", {"value": 2}))
