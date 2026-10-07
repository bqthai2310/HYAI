"""Constitutional authority checks for material HYAI actions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class PrincipalType(str, Enum):
    PO = "PO"
    ARCHITECT = "ARCHITECT"
    EXECUTOR = "EXECUTOR"
    INDEPENDENT_REVIEWER = "INDEPENDENT_REVIEWER"
    ASSURANCE_SERVICE = "ASSURANCE_SERVICE"
    RUNTIME_WORKER = "RUNTIME_WORKER"
    POLICY_ENGINE = "POLICY_ENGINE"
    EVOLUTION_CONTROLLER = "EVOLUTION_CONTROLLER"
    RELEASE_MANAGER = "RELEASE_MANAGER"
    SYSTEM = "SYSTEM"


class AuthorityClass(str, Enum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"


@dataclass(frozen=True)
class Principal:
    principal_type: PrincipalType | str
    id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "principal_type", PrincipalType(self.principal_type))
        if not self.id.strip():
            raise ValueError("principal id is required")


@dataclass(frozen=True)
class AuthorityDecision:
    decision_id: str
    authority: Principal
    action: str
    resource: str
    required_class: AuthorityClass | str
    status: str = "APPROVED"
    evidence_refs: tuple[str, ...] = ()
    supersedes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_class", AuthorityClass(self.required_class))


_MAX_CLASS = {
    PrincipalType.PO: AuthorityClass.A4,
    PrincipalType.ARCHITECT: AuthorityClass.A3,
    PrincipalType.RELEASE_MANAGER: AuthorityClass.A2,
    PrincipalType.EXECUTOR: AuthorityClass.A1,
}


def _principal(value: Principal | Mapping[str, Any]) -> Principal:
    return value if isinstance(value, Principal) else Principal(value["principal_type"], value["id"])


def can_authorize(principal: Principal | Mapping[str, Any], required_class: AuthorityClass | str) -> bool:
    """Return whether a principal may authorize a class of decision.

    PO is sovereign.  An executor is deliberately never an authorization source,
    even though it may implement an already-authorized A1 action.
    """
    actor = _principal(principal)
    required = AuthorityClass(required_class)
    if actor.principal_type is PrincipalType.EXECUTOR:
        return False
    maximum = _MAX_CLASS.get(actor.principal_type)
    return maximum is not None and list(AuthorityClass).index(required) <= list(AuthorityClass).index(maximum)


def can_implement(principal: Principal | Mapping[str, Any], required_class: AuthorityClass | str) -> bool:
    actor = _principal(principal)
    return actor.principal_type is PrincipalType.EXECUTOR and AuthorityClass(required_class) is AuthorityClass.A1


def verify_decision(
    action: str,
    resource: str,
    required_class: AuthorityClass | str,
    decision: AuthorityDecision | None,
) -> tuple[bool, str]:
    """Validate a decision's scope and constitutional authority."""
    required = AuthorityClass(required_class)
    if decision is None:
        return False, "missing authority decision"
    if decision.status != "APPROVED":
        return False, "authority decision is not approved"
    if (decision.action, decision.resource, decision.required_class) != (action, resource, required):
        return False, "authority decision does not bind the exact action, resource, and class"
    if not can_authorize(decision.authority, required):
        return False, "decision authority cannot authorize this action"
    return True, "authorized"


def verify_material_action(
    requester: Principal | Mapping[str, Any], action: str, resource: str,
    required_class: AuthorityClass | str, decision: AuthorityDecision | None,
) -> tuple[bool, str]:
    """Ensure material work is implementation, never self-granted authority."""
    actor = _principal(requester)
    required = AuthorityClass(required_class)
    allowed, reason = verify_decision(action, resource, required, decision)
    if not allowed:
        return False, reason
    if actor.principal_type is PrincipalType.EXECUTOR and not can_implement(actor, required):
        return False, "executor is implementer-only and may implement A1 only"
    return True, "authorized material action"
