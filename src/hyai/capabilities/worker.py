"""Worker descriptors, bounded resource leases, and department worker allocation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import timestamp, validate
from hyai.capabilities.spec import CapabilityError


class WorkerError(CapabilityError):
    """Base error for worker and lease failures."""


class WorkerValidationError(WorkerError):
    """Validation error for worker or lease contracts."""


class LeaseExpiredError(WorkerError):
    """Raised when an operation is attempted with an expired lease."""


class UnpermittedActionError(WorkerError):
    """Raised when an action is not permitted by the resource lease."""


class WorkerStatus(str, Enum):
    READY = "READY"
    BUSY = "BUSY"
    DRAINING = "DRAINING"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"


class TrustClass(str, Enum):
    UNTRUSTED = "UNTRUSTED"
    LIMITED = "LIMITED"
    TRUSTED = "TRUSTED"
    HIGH_TRUST = "HIGH_TRUST"


@dataclass(frozen=True)
class ResourceLease:
    schema_version: str
    lease_id: str
    task_id: str
    task_revision: int
    worker_id: str
    permitted_actions: tuple[str, ...]
    expires_at: str
    issued_at: str
    budget_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "permitted_actions", tuple(sorted(set(self.permitted_actions))))

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema_version": self.schema_version,
            "lease_id": self.lease_id,
            "task_id": self.task_id,
            "task_revision": int(self.task_revision),
            "worker_id": self.worker_id,
            "permitted_actions": list(self.permitted_actions),
            "expires_at": self.expires_at,
            "issued_at": self.issued_at,
        }
        if self.budget_ref is not None:
            doc["budget_ref"] = self.budget_ref
        return doc

    def validate(self) -> "ResourceLease":
        validate_resource_lease_document(self.to_dict())
        return self

    def is_expired(self, moment: str | datetime | None = None) -> bool:
        if moment is None:
            current_dt = datetime.now(UTC)
        elif isinstance(moment, datetime):
            current_dt = moment.astimezone(UTC)
        else:
            current_dt = datetime.fromisoformat(moment.replace("Z", "+00:00")).astimezone(UTC)
        exp_dt = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00")).astimezone(UTC)
        return current_dt >= exp_dt

    def allows_action(self, action: str) -> bool:
        return action in self.permitted_actions or "*" in self.permitted_actions

    def assert_valid_for(self, action: str, moment: str | datetime | None = None) -> None:
        if self.is_expired(moment):
            raise LeaseExpiredError(f"Lease {self.lease_id} expired at {self.expires_at}")
        if not self.allows_action(action):
            raise UnpermittedActionError(f"Action '{action}' not permitted by lease {self.lease_id} actions: {self.permitted_actions}")


def validate_resource_lease_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "resource_lease.schema.json", WorkerValidationError)
    except Exception as exc:
        raise WorkerValidationError(str(exc)) from exc


def create_resource_lease(
    *,
    lease_id: str,
    task_id: str,
    task_revision: int,
    worker_id: str,
    permitted_actions: Sequence[str],
    expires_at: str,
    issued_at: str | None = None,
    budget_ref: str | None = None,
    schema_version: str = "2.1.0",
) -> ResourceLease:
    lease = ResourceLease(
        schema_version=schema_version,
        lease_id=lease_id,
        task_id=task_id,
        task_revision=task_revision,
        worker_id=worker_id,
        permitted_actions=tuple(permitted_actions),
        expires_at=expires_at,
        issued_at=issued_at or timestamp(),
        budget_ref=budget_ref,
    )
    lease.validate()
    return lease


@dataclass(frozen=True)
class WorkerDescriptor:
    schema_version: str
    worker_id: str
    node_id: str
    capabilities: tuple[str, ...]
    status: str
    trust_class: str
    registered_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", tuple(sorted(set(self.capabilities))))
        object.__setattr__(self, "status", WorkerStatus(self.status).value)
        object.__setattr__(self, "trust_class", TrustClass(self.trust_class).value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "worker_id": self.worker_id,
            "node_id": self.node_id,
            "capabilities": list(self.capabilities),
            "status": self.status,
            "trust_class": self.trust_class,
            "registered_at": self.registered_at,
        }

    def validate(self) -> "WorkerDescriptor":
        validate_worker_descriptor_document(self.to_dict())
        return self


def validate_worker_descriptor_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "worker_descriptor.schema.json", WorkerValidationError)
    except Exception as exc:
        raise WorkerValidationError(str(exc)) from exc


def create_worker_descriptor(
    *,
    worker_id: str,
    node_id: str,
    capabilities: Sequence[str],
    status: WorkerStatus | str = WorkerStatus.READY,
    trust_class: TrustClass | str = TrustClass.TRUSTED,
    registered_at: str | None = None,
    schema_version: str = "2.1.0",
) -> WorkerDescriptor:
    worker = WorkerDescriptor(
        schema_version=schema_version,
        worker_id=worker_id,
        node_id=node_id,
        capabilities=tuple(capabilities),
        status=status.value if isinstance(status, WorkerStatus) else str(status),
        trust_class=trust_class.value if isinstance(trust_class, TrustClass) else str(trust_class),
        registered_at=registered_at or timestamp(),
    )
    worker.validate()
    return worker


class DynamicDepartmentWorkerPool:
    """Department worker pool that dynamically assigns workers without fixed binding (L9-REQ-DPT-006)."""

    def __init__(self, department_id: str) -> None:
        self.department_id = department_id
        self._workers: dict[str, WorkerDescriptor] = {}

    def register_worker(self, worker: WorkerDescriptor) -> None:
        self._workers[worker.worker_id] = worker

    def unregister_worker(self, worker_id: str) -> None:
        self._workers.pop(worker_id, None)

    def allocate_worker_for_task(
        self,
        required_capability: str,
        exclude_worker_ids: Sequence[str] = (),
    ) -> WorkerDescriptor:
        available = [
            w for w in self._workers.values()
            if w.status == WorkerStatus.READY.value
            and required_capability in w.capabilities
            and w.worker_id not in exclude_worker_ids
        ]
        if not available:
            raise WorkerError(f"No available worker in department {self.department_id} for capability {required_capability}")
        return available[0]
