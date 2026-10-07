"""Federation node identity, placement, lease-bound commit, and quarantine (FED-001..005)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import timestamp, validate


class FederationError(Exception):
    """Base error for federation subsystem."""


class UntrustedPlacementError(FederationError):
    """Raised when task placement violates node trust or clearance bounds (L9-REQ-FED-002)."""


class ExpiredLeaseCommitError(FederationError):
    """Raised when an expired node lease attempts to commit mutations (L9-REQ-FED-003)."""


class CompetingWriterError(FederationError):
    """Raised when competing writers attempt concurrent canonical state mutation (L9-REQ-FED-004)."""


class NodeQuarantinedError(FederationError):
    """Raised when an unhealthy or untrusted node is quarantined (L9-REQ-FED-005)."""


class NodeState(str, Enum):
    DISCOVERED = "DISCOVERED"
    ATTESTING = "ATTESTING"
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


class NodeTrustClass(str, Enum):
    UNTRUSTED = "UNTRUSTED"
    LIMITED = "LIMITED"
    TRUSTED = "TRUSTED"
    HIGH_TRUST = "HIGH_TRUST"


class NodeHealth(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass(frozen=True)
class FederationNode:
    schema_version: str
    node_id: str
    state: str
    trust_class: str
    platform: str
    capabilities: tuple[str, ...]
    health: str
    registered_at: str
    attestation_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.match(r"^node_", self.node_id):
            raise FederationError(f"node_id '{self.node_id}' must begin with 'node_'")
        object.__setattr__(self, "state", NodeState(self.state).value)
        object.__setattr__(self, "trust_class", NodeTrustClass(self.trust_class).value)
        object.__setattr__(self, "health", NodeHealth(self.health).value)
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(self, "attestation_refs", tuple(self.attestation_refs))

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema_version": self.schema_version,
            "node_id": self.node_id,
            "state": self.state,
            "trust_class": self.trust_class,
            "platform": self.platform,
            "capabilities": list(self.capabilities),
            "health": self.health,
            "registered_at": self.registered_at,
        }
        if self.attestation_refs:
            doc["attestation_refs"] = list(self.attestation_refs)
        return doc

    def validate(self) -> "FederationNode":
        validate_federation_node_document(self.to_dict())
        return self


def validate_federation_node_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "federation_node.schema.json", FederationError)
    except Exception as exc:
        raise FederationError(str(exc)) from exc


def create_federation_node(
    *,
    node_id: str,
    state: NodeState | str = NodeState.ACTIVE,
    trust_class: NodeTrustClass | str = NodeTrustClass.TRUSTED,
    platform: str = "linux-x86_64",
    capabilities: Sequence[str] = (),
    health: NodeHealth | str = NodeHealth.HEALTHY,
    attestation_refs: Sequence[str] = (),
    registered_at: str | None = None,
    schema_version: str = "2.0.0",
) -> FederationNode:
    s = state.value if isinstance(state, NodeState) else str(state)
    tc = trust_class.value if isinstance(trust_class, NodeTrustClass) else str(trust_class)
    h = health.value if isinstance(health, NodeHealth) else str(health)
    node = FederationNode(
        schema_version=schema_version,
        node_id=node_id,
        state=s,
        trust_class=tc,
        platform=platform,
        capabilities=tuple(capabilities),
        health=h,
        attestation_refs=tuple(attestation_refs),
        registered_at=registered_at or timestamp(),
    )
    node.validate()
    return node


class FederationManager:
    """Coordinates federated node lifecycle, placement, and single-writer leases."""

    def __init__(self) -> None:
        self._nodes: dict[str, FederationNode] = {}
        self._active_writer: str | None = None
        self._node_leases: dict[str, tuple[str, bool]] = {}  # node_id -> (lease_id, is_active)

    def register_node(self, node: FederationNode) -> None:
        node.validate()
        self._nodes[node.node_id] = node

    def place_task(self, task_id: str, required_capability: str, min_trust: NodeTrustClass | str) -> FederationNode:
        # L9-REQ-FED-002: Placement respects trust, data, and capability
        min_tc = min_trust.value if isinstance(min_trust, NodeTrustClass) else str(min_trust)
        trust_levels = {
            NodeTrustClass.UNTRUSTED.value: 0,
            NodeTrustClass.LIMITED.value: 1,
            NodeTrustClass.TRUSTED.value: 2,
            NodeTrustClass.HIGH_TRUST.value: 3,
        }
        candidates = [
            n for n in self._nodes.values()
            if n.state == NodeState.ACTIVE.value
            and n.health == NodeHealth.HEALTHY.value
            and required_capability in n.capabilities
            and trust_levels[n.trust_class] >= trust_levels[min_tc]
        ]
        if not candidates:
            raise UntrustedPlacementError(f"No active node satisfies trust '{min_tc}' and capability '{required_capability}'")
        return candidates[0]

    def issue_writer_lease(self, node_id: str, lease_id: str) -> None:
        # L9-REQ-FED-004: No competing canonical writer
        if self._active_writer is not None and self._active_writer != node_id:
            raise CompetingWriterError(f"Cannot grant writer lease to '{node_id}': active writer '{self._active_writer}' exists")
        self._active_writer = node_id
        self._node_leases[node_id] = (lease_id, True)

    def commit_mutation(self, node_id: str, lease_id: str, is_expired: bool = False) -> None:
        # L9-REQ-FED-003: Expired node lease cannot commit
        if is_expired:
            raise ExpiredLeaseCommitError(f"Node '{node_id}' lease '{lease_id}' is expired; commit rejected")
        if self._active_writer != node_id:
            raise CompetingWriterError(f"Node '{node_id}' is not the active canonical writer")

    def quarantine_node(self, node_id: str, reason: str) -> FederationNode:
        # L9-REQ-FED-005: Untrusted/unhealthy nodes can be quarantined
        node = self._nodes.get(node_id)
        if not node:
            raise FederationError(f"Node '{node_id}' not found")
        updated = FederationNode(
            schema_version=node.schema_version,
            node_id=node.node_id,
            state=NodeState.QUARANTINED.value,
            trust_class=NodeTrustClass.UNTRUSTED.value,
            platform=node.platform,
            capabilities=node.capabilities,
            health=NodeHealth.UNHEALTHY.value,
            attestation_refs=node.attestation_refs,
            registered_at=node.registered_at,
        )
        self._nodes[node_id] = updated
        if self._active_writer == node_id:
            self._active_writer = None
        return updated

