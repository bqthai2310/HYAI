"""WorkflowInstance definitions, lifecycle states, and validation (L9-REQ-REL-004)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from hyai._contracts import timestamp, validate


class WorkflowError(Exception):
    """Base exception for workflow subsystem."""


class WorkflowValidationError(WorkflowError):
    """Raised when a workflow document violates its schema."""


class WorkflowState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    RECOVERING = "RECOVERING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class WorkflowInstance:
    schema_version: str
    workflow_id: str
    task_id: str
    workflow_type: str
    revision: int
    state: str
    started_at: str
    updated_at: str | None = None
    checkpoint_ref: str | None = None

    def __post_init__(self) -> None:
        if not re.match(r"^wf_", self.workflow_id):
            raise WorkflowValidationError(f"workflow_id '{self.workflow_id}' must begin with 'wf_'")
        if not re.match(r"^task_", self.task_id):
            raise WorkflowValidationError(f"task_id '{self.task_id}' must begin with 'task_'")
        object.__setattr__(self, "state", WorkflowState(self.state).value)

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema_version": self.schema_version,
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
            "workflow_type": self.workflow_type,
            "revision": int(self.revision),
            "state": self.state,
            "started_at": self.started_at,
        }
        if self.updated_at is not None:
            doc["updated_at"] = self.updated_at
        if self.checkpoint_ref is not None:
            doc["checkpoint_ref"] = self.checkpoint_ref
        return doc

    def validate(self) -> "WorkflowInstance":
        validate_workflow_instance_document(self.to_dict())
        return self


def validate_workflow_instance_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "workflow_instance.schema.json", WorkflowValidationError)
    except Exception as exc:
        raise WorkflowValidationError(str(exc)) from exc


def create_workflow_instance(
    *,
    workflow_id: str,
    task_id: str,
    workflow_type: str,
    revision: int = 1,
    state: WorkflowState | str = WorkflowState.CREATED,
    started_at: str | None = None,
    updated_at: str | None = None,
    checkpoint_ref: str | None = None,
    schema_version: str = "2.1.0",
) -> WorkflowInstance:
    instance = WorkflowInstance(
        schema_version=schema_version,
        workflow_id=workflow_id,
        task_id=task_id,
        workflow_type=workflow_type,
        revision=revision,
        state=str(state if isinstance(state, str) else state.value),
        started_at=started_at or timestamp(),
        updated_at=updated_at,
        checkpoint_ref=checkpoint_ref,
    )
    instance.validate()
    return instance
