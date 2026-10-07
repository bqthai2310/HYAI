"""Durable checkpoint definitions, verification, and resume support (L9-REQ-REL-004)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest
from hyai.workflow.instance import WorkflowError, WorkflowValidationError


class CheckpointError(WorkflowError):
    """Base error for checkpoint failures."""


class CheckpointCorruptedError(CheckpointError):
    """Raised when checkpoint digest does not match its contents."""


@dataclass(frozen=True)
class Checkpoint:
    schema_version: str
    checkpoint_id: str
    workflow_id: str
    workflow_revision: int
    task_revision: int
    completed_steps: tuple[str, ...]
    side_effect_refs: tuple[str, ...]
    created_at: str
    digest: dict[str, str]
    cursor: str | None = None

    def __post_init__(self) -> None:
        if not re.match(r"^chk_", self.checkpoint_id):
            raise WorkflowValidationError(f"checkpoint_id '{self.checkpoint_id}' must begin with 'chk_'")
        if not re.match(r"^wf_", self.workflow_id):
            raise WorkflowValidationError(f"workflow_id '{self.workflow_id}' must begin with 'wf_'")
        object.__setattr__(self, "completed_steps", tuple(sorted(set(self.completed_steps))))
        object.__setattr__(self, "side_effect_refs", tuple(sorted(set(self.side_effect_refs))))

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema_version": self.schema_version,
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "workflow_revision": int(self.workflow_revision),
            "task_revision": int(self.task_revision),
            "completed_steps": list(self.completed_steps),
            "side_effect_refs": list(self.side_effect_refs),
            "created_at": self.created_at,
            "digest": dict(self.digest),
        }
        if self.cursor is not None:
            doc["cursor"] = self.cursor
        return doc

    def validate(self) -> "Checkpoint":
        validate_checkpoint_document(self.to_dict())
        return self

    def verify_integrity(self) -> None:
        payload = {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "workflow_revision": self.workflow_revision,
            "task_revision": self.task_revision,
            "completed_steps": self.completed_steps,
            "side_effect_refs": self.side_effect_refs,
            "cursor": self.cursor,
        }
        expected = compute_digest(canonical(payload))
        if self.digest != expected:
            raise CheckpointCorruptedError(
                f"Checkpoint {self.checkpoint_id} digest {self.digest} does not match computed {expected}"
            )


def validate_checkpoint_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "checkpoint.schema.json", WorkflowValidationError)
    except Exception as exc:
        raise WorkflowValidationError(str(exc)) from exc


def create_checkpoint(
    *,
    checkpoint_id: str,
    workflow_id: str,
    workflow_revision: int = 1,
    task_revision: int = 1,
    completed_steps: Sequence[str] = (),
    side_effect_refs: Sequence[str] = (),
    cursor: str | None = None,
    created_at: str | None = None,
    schema_version: str = "2.1.0",
) -> Checkpoint:
    payload = {
        "checkpoint_id": checkpoint_id,
        "workflow_id": workflow_id,
        "workflow_revision": int(workflow_revision),
        "task_revision": int(task_revision),
        "completed_steps": tuple(sorted(set(completed_steps))),
        "side_effect_refs": tuple(sorted(set(side_effect_refs))),
        "cursor": cursor,
    }
    digest = compute_digest(canonical(payload))
    checkpoint = Checkpoint(
        schema_version=schema_version,
        checkpoint_id=checkpoint_id,
        workflow_id=workflow_id,
        workflow_revision=workflow_revision,
        task_revision=task_revision,
        completed_steps=tuple(completed_steps),
        side_effect_refs=tuple(side_effect_refs),
        created_at=created_at or timestamp(),
        digest=digest,
        cursor=cursor,
    )
    checkpoint.validate()
    return checkpoint


class CheckpointManager:
    """Manages persistent workflow checkpoints and state resumption."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        checkpoint.validate()
        checkpoint.verify_integrity()
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        return self._checkpoints.get(checkpoint_id)

    def resume_from_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        cp = self.get_checkpoint(checkpoint_id)
        if cp is None:
            raise CheckpointError(f"Cannot resume: checkpoint '{checkpoint_id}' not found")
        cp.verify_integrity()
        return cp
