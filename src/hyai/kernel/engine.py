"""A deliberately small control-plane kernel.

Domain decisions live outside this module.  The kernel only guards command
execution, optimistic state changes, durable idempotency, policy checks, and
the audit trail.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from hyai.compatibility.crypto import compute_digest
from hyai.ports.base import StoragePort

from .command import CommandEnvelope
from .event import EventEnvelope


class RevisionConflictError(RuntimeError):
    """The supplied expected revision is no longer current."""


class IdempotencyConflictError(RuntimeError):
    """One idempotency key was reused for a different command payload."""


class PolicyDeniedError(PermissionError):
    """A policy hook rejected a command or its snapshot."""


class HiddenWriteError(RuntimeError):
    """Mutation was attempted without a command envelope."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _actor_id(actor: Any) -> str:
    return actor.id if hasattr(actor, "id") else str(actor["id"])


class _ReadOnlyStorageView:
    """Expose reads without creating a second mutation route."""

    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage

    def get(self, key: str) -> Mapping[str, Any] | None:
        return self._storage.get(key)

    def put(self, *_: Any, **__: Any) -> None:
        raise HiddenWriteError("all material mutations must use execute_command")


class SovereignKernel:
    """The control-plane command gateway and the only mutation route."""

    _FORBIDDEN_CAPABILITIES = ("prompt", "llm", "model", "provider", "openai", "anthropic", "boto3")

    def __init__(self, storage: StoragePort, policy_hook: Callable[[CommandEnvelope], Any] | None = None) -> None:
        self._storage = storage
        self.policy_hook = policy_hook or (lambda _command: "ALLOW")

    @property
    def storage(self) -> _ReadOnlyStorageView:
        """A read-only view; durable writes are private to command execution."""
        return _ReadOnlyStorageView(self._storage)

    def is_small_kernel(self, capability: str | None = None) -> bool:
        """Return false for attempted model/provider intelligence requests."""
        if capability is None:
            return True
        return not any(term in capability.lower() for term in self._FORBIDDEN_CAPABILITIES)

    @staticmethod
    def _state_key(target: str) -> str:
        return f"kernel:state:{target}"

    @staticmethod
    def _idempotency_key(command: CommandEnvelope) -> str:
        return f"kernel:idempotency:{_actor_id(command.actor)}:{command.command_type}:{command.idempotency_key}"

    def _policy_allows(self, command: CommandEnvelope) -> bool:
        decision = self.policy_hook(command)
        if isinstance(decision, Mapping):
            status = str(decision.get("decision", decision.get("status", ""))).upper()
            snapshot = decision.get("policy_snapshot_id", command.policy_snapshot_id)
            return status in {"ALLOW", "APPROVED", "PASS"} and snapshot == command.policy_snapshot_id
        return str(decision).upper() in {"ALLOW", "APPROVED", "PASS", "TRUE"}

    def execute_command(
        self,
        envelope: CommandEnvelope,
        transition: Callable[[dict[str, Any], CommandEnvelope], Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Validate, authorize, atomically apply, persist, and audit a command."""
        envelope.validate()
        request_description = f"{envelope.command_type} {envelope.target} {_canonical(dict(envelope.payload)).decode('utf-8')}"
        if not self.is_small_kernel(request_description):
            raise ValueError("small kernel rejects model/provider capabilities")
        digest = compute_digest(_canonical(dict(envelope.payload)))
        idem_key = self._idempotency_key(envelope)
        previous = self._storage.get(idem_key)
        if previous is not None:
            if previous.get("payload_digest") != digest:
                raise IdempotencyConflictError("IDEMPOTENCY_CONFLICT")
            return dict(previous["result"])
        if not self._policy_allows(envelope):
            raise PolicyDeniedError("POLICY_DENIED")

        state_key = self._state_key(envelope.target)
        stored = self._storage.get(state_key) or {"revision": 0, "state": {}}
        revision = int(stored.get("revision", 0))
        if envelope.expected_revision != revision:
            raise RevisionConflictError("REVISION_CONFLICT")
        old_state = dict(stored.get("state", {}))
        new_state = dict(transition(old_state, envelope) if transition else {**old_state, **dict(envelope.payload)})
        new_revision = revision + 1
        record = {"revision": new_revision, "state": new_state}
        self._storage.put(state_key, record, expected_version=str(revision))
        event = EventEnvelope(
            event_id=f"evt_{uuid.uuid4().hex}", event_type=f"{envelope.command_type}.applied",
            producer=envelope.actor, aggregate_type="command_target", aggregate_id=envelope.target,
            aggregate_revision=new_revision, correlation_id=envelope.correlation_id, payload=new_state,
            payload_digest=compute_digest(_canonical(new_state)), causation_id=envelope.command_id,
            policy_snapshot_id=envelope.policy_snapshot_id,
        )
        event.validate()
        self._storage.put(f"kernel:event:{event.event_id}", event.to_dict())
        result = {"revision": new_revision, "state": new_state, "event": event.to_dict()}
        self._storage.put(idem_key, {"payload_digest": digest, "result": result})
        return result

    def read_state(self, target: str) -> dict[str, Any]:
        stored = self._storage.get(self._state_key(target)) or {"revision": 0, "state": {}}
        return {"revision": int(stored["revision"]), "state": dict(stored["state"])}

    def write_state(self, *_: Any, **__: Any) -> None:
        """Explicitly reject APIs that would bypass command execution."""
        raise HiddenWriteError("all material mutations must use execute_command")
