"""Department charters, typed handoffs, cycle rejection, and conflict authority (DPT-001..008, EXE-008)."""
from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest


class DepartmentError(Exception):
    """Base error for department subsystem."""


class CircularHandoffError(DepartmentError):
    """Raised when department handoff graph contains an uncontracted cycle (L9-REQ-DPT-005)."""


class SelfAuditingForbiddenError(DepartmentError):
    """Raised when Independent Assurance department attempts to approve an artifact it authored (L9-REQ-DPT-007)."""


class MajorityVoteForbiddenError(DepartmentError):
    """Raised when cross-department conflict attempts resolution via agent majority vote (L9-REQ-EXE-008)."""


class RouteInvalidationError(DepartmentError):
    """Raised when an invalidated route attempts execution without new provenance (L9-REQ-DPT-008)."""


class CharterLifecycleState(str, Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class DepartmentCharter:
    schema_version: str
    department_id: str
    version: str
    mission: str
    authority: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    escalation_conditions: tuple[str, ...]
    lifecycle_state: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^department_", self.department_id):
            raise DepartmentError(f"department_id '{self.department_id}' must begin with 'department_'")
        object.__setattr__(self, "lifecycle_state", CharterLifecycleState(self.lifecycle_state).value)
        object.__setattr__(self, "authority", tuple(self.authority))
        object.__setattr__(self, "required_capabilities", tuple(self.required_capabilities))
        object.__setattr__(self, "input_types", tuple(self.input_types))
        object.__setattr__(self, "output_types", tuple(self.output_types))
        object.__setattr__(self, "forbidden_actions", tuple(self.forbidden_actions))
        object.__setattr__(self, "escalation_conditions", tuple(self.escalation_conditions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "department_id": self.department_id,
            "version": self.version,
            "mission": self.mission,
            "authority": list(self.authority),
            "required_capabilities": list(self.required_capabilities),
            "input_types": list(self.input_types),
            "output_types": list(self.output_types),
            "forbidden_actions": list(self.forbidden_actions),
            "escalation_conditions": list(self.escalation_conditions),
            "lifecycle_state": self.lifecycle_state,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "DepartmentCharter":
        validate_department_charter_document(self.to_dict())
        return self


def validate_department_charter_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "department_charter.schema.json", DepartmentError)
    except Exception as exc:
        raise DepartmentError(str(exc)) from exc


def create_department_charter(
    *,
    department_id: str,
    version: str = "1.0.0",
    mission: str,
    authority: Sequence[str] = (),
    required_capabilities: Sequence[str] = (),
    input_types: Sequence[str] = (),
    output_types: Sequence[str] = (),
    forbidden_actions: Sequence[str] = ("direct_db_write",),
    escalation_conditions: Sequence[str] = ("invariant_violation",),
    lifecycle_state: CharterLifecycleState | str = CharterLifecycleState.ACTIVE,
    schema_version: str = "2.1.0",
) -> DepartmentCharter:
    if isinstance(lifecycle_state, CharterLifecycleState):
        ls = lifecycle_state.value
    else:
        ls = str(lifecycle_state)
    payload = {
        "department_id": department_id,
        "version": version,
        "mission": mission,
        "authority": tuple(authority),
        "required_capabilities": tuple(required_capabilities),
        "input_types": tuple(input_types),
        "output_types": tuple(output_types),
        "forbidden_actions": tuple(forbidden_actions),
        "escalation_conditions": tuple(escalation_conditions),
        "lifecycle_state": ls,
    }
    digest = compute_digest(canonical(payload))
    charter = DepartmentCharter(
        schema_version=schema_version,
        department_id=department_id,
        version=version,
        mission=mission,
        authority=tuple(authority),
        required_capabilities=tuple(required_capabilities),
        input_types=tuple(input_types),
        output_types=tuple(output_types),
        forbidden_actions=tuple(forbidden_actions),
        escalation_conditions=tuple(escalation_conditions),
        lifecycle_state=ls,
        content_digest=digest,
    )
    charter.validate()
    return charter


@dataclass(frozen=True)
class HandoffContract:
    schema_version: str
    handoff_id: str
    source_department: str
    destination_department: str
    subject_refs: tuple[str, ...]
    input_contract: str
    output_acceptance_refs: tuple[str, ...]
    unresolved_risks: tuple[str, ...]
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^handoff_", self.handoff_id):
            raise DepartmentError(f"handoff_id '{self.handoff_id}' must begin with 'handoff_'")
        object.__setattr__(self, "subject_refs", tuple(self.subject_refs))
        object.__setattr__(self, "output_acceptance_refs", tuple(self.output_acceptance_refs))
        object.__setattr__(self, "unresolved_risks", tuple(self.unresolved_risks))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "handoff_id": self.handoff_id,
            "source_department": self.source_department,
            "destination_department": self.destination_department,
            "subject_refs": list(self.subject_refs),
            "input_contract": self.input_contract,
            "output_acceptance_refs": list(self.output_acceptance_refs),
            "unresolved_risks": list(self.unresolved_risks),
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "HandoffContract":
        validate_handoff_contract_document(self.to_dict())
        return self


def validate_handoff_contract_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "handoff_contract.schema.json", DepartmentError)
    except Exception as exc:
        raise DepartmentError(str(exc)) from exc


def create_handoff_contract(
    *,
    handoff_id: str,
    source_department: str,
    destination_department: str,
    subject_refs: Sequence[str],
    input_contract: str,
    output_acceptance_refs: Sequence[str],
    unresolved_risks: Sequence[str] = (),
    schema_version: str = "2.1.0",
) -> HandoffContract:
    payload = {
        "handoff_id": handoff_id,
        "source_department": source_department,
        "destination_department": destination_department,
        "subject_refs": tuple(subject_refs),
        "input_contract": input_contract,
        "output_acceptance_refs": tuple(output_acceptance_refs),
        "unresolved_risks": tuple(unresolved_risks),
    }
    digest = compute_digest(canonical(payload))
    contract = HandoffContract(
        schema_version=schema_version,
        handoff_id=handoff_id,
        source_department=source_department,
        destination_department=destination_department,
        subject_refs=tuple(subject_refs),
        input_contract=input_contract,
        output_acceptance_refs=tuple(output_acceptance_refs),
        unresolved_risks=tuple(unresolved_risks),
        content_digest=digest,
    )
    contract.validate()
    return contract


class HandoffGraphValidator:
    """L9-REQ-DPT-005: Rejects cyclic department handoffs unless explicit bounded iterative contract exists."""

    @staticmethod
    def validate_acyclic(edges: Sequence[tuple[str, str]], allow_cycles: bool = False) -> None:
        if allow_cycles:
            return
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = defaultdict(int)
        nodes: set[str] = set()

        for u, v in edges:
            nodes.add(u)
            nodes.add(v)
            adj[u].append(v)
            in_degree[v] += 1
            if u not in in_degree:
                in_degree[u] = 0

        queue: deque[str] = deque([n for n in nodes if in_degree[n] == 0])
        visited = 0
        while queue:
            curr = queue.popleft()
            visited += 1
            for nbr in adj[curr]:
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    queue.append(nbr)

        if visited != len(nodes):
            raise CircularHandoffError("Department handoff graph contains an uncontracted cycle (L9-REQ-DPT-005)")


class IndependenceEnforcer:
    """L9-REQ-DPT-007: Independent Assurance cannot approve an exact subject it authored."""

    @staticmethod
    def assert_independent_approval(author_dept: str, approver_dept: str, subject_ref: str) -> None:
        if author_dept.lower() in ("assurance", "quality") and approver_dept.lower() in ("assurance", "quality"):
            raise SelfAuditingForbiddenError(
                f"Department '{approver_dept}' cannot independently approve subject '{subject_ref}' which it authored (L9-REQ-DPT-007)"
            )


class ConflictResolver:
    """L9-REQ-EXE-008: Cross-department conflict resolves by authority/evidence, never majority vote."""

    @staticmethod
    def resolve_conflict(
        resolution_mode: str,
        evidence_score_a: float,
        evidence_score_b: float,
        agent_votes: Mapping[str, str] | None = None,
    ) -> str:
        if resolution_mode.upper() == "MAJORITY_VOTE":
            raise MajorityVoteForbiddenError(
                "Cross-department conflicts cannot be resolved by agent majority vote; authority and evidence are required (L9-REQ-EXE-008)"
            )
        return "DEPT_A" if evidence_score_a >= evidence_score_b else "DEPT_B"
