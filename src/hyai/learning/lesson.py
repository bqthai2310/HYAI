"""Organizational learning, evidence-backed promotion, negative knowledge, and scope boundaries (LRN-001..007)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest


class LearningError(Exception):
    """Base error for learning subsystem."""


class ConstitutionalOverrideForbiddenError(LearningError):
    """Raised when an organizational lesson attempts to override Constitution or Acceptance (L9-REQ-LRN-002)."""


class GlobalOvergeneralizationError(LearningError):
    """Raised when single-product learning is promoted globally without cross-product validation (L9-REQ-LRN-007)."""


class UnpromotedLessonError(LearningError):
    """Raised when execution outcome is treated as durable lesson without evidence promotion (L9-REQ-LRN-001)."""


class LessonAuthorityClass(str, Enum):
    OBSERVED = "OBSERVED"
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    NEGATIVE_KNOWLEDGE = "NEGATIVE_KNOWLEDGE"


class LessonLifecycleState(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class OrganizationalLesson:
    schema_version: str
    lesson_id: str
    authority_class: str
    statement: str
    applicability_scope: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    invalidation_triggers: tuple[str, ...]
    lifecycle_state: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^lesson_", self.lesson_id):
            raise LearningError(f"lesson_id '{self.lesson_id}' must begin with 'lesson_'")
        object.__setattr__(self, "authority_class", LessonAuthorityClass(self.authority_class).value)
        object.__setattr__(self, "lifecycle_state", LessonLifecycleState(self.lifecycle_state).value)
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "invalidation_triggers", tuple(self.invalidation_triggers))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lesson_id": self.lesson_id,
            "authority_class": self.authority_class,
            "statement": self.statement,
            "applicability_scope": self.applicability_scope,
            "source_refs": list(self.source_refs),
            "evidence_refs": list(self.evidence_refs),
            "invalidation_triggers": list(self.invalidation_triggers),
            "lifecycle_state": self.lifecycle_state,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "OrganizationalLesson":
        validate_organizational_lesson_document(self.to_dict())
        return self


def validate_organizational_lesson_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "organizational_lesson.schema.json", LearningError)
    except Exception as exc:
        raise LearningError(str(exc)) from exc


def create_organizational_lesson(
    *,
    lesson_id: str,
    authority_class: LessonAuthorityClass | str,
    statement: str,
    applicability_scope: str,
    source_refs: Sequence[str],
    evidence_refs: Sequence[str],
    invalidation_triggers: Sequence[str],
    lifecycle_state: LessonLifecycleState | str = LessonLifecycleState.ACTIVE,
    schema_version: str = "2.1.0",
) -> OrganizationalLesson:
    ac = authority_class.value if isinstance(authority_class, LessonAuthorityClass) else str(authority_class)
    ls = lifecycle_state.value if isinstance(lifecycle_state, LessonLifecycleState) else str(lifecycle_state)

    # L9-REQ-LRN-002: OrganizationalLesson never overrides Constitution/ProductContract/frozen Acceptance
    forbidden_terms = {"override constitution", "override product contract", "override acceptance"}
    if any(term in statement.lower() for term in forbidden_terms):
        raise ConstitutionalOverrideForbiddenError("Lessons cannot override Constitution or ProductContract (L9-REQ-LRN-002)")

    payload = {
        "lesson_id": lesson_id,
        "authority_class": ac,
        "statement": statement,
        "applicability_scope": applicability_scope,
        "source_refs": tuple(source_refs),
        "evidence_refs": tuple(evidence_refs),
        "invalidation_triggers": tuple(invalidation_triggers),
        "lifecycle_state": ls,
    }
    digest = compute_digest(canonical(payload))
    lesson = OrganizationalLesson(
        schema_version=schema_version,
        lesson_id=lesson_id,
        authority_class=ac,
        statement=statement,
        applicability_scope=applicability_scope,
        source_refs=tuple(source_refs),
        evidence_refs=tuple(evidence_refs),
        invalidation_triggers=tuple(invalidation_triggers),
        lifecycle_state=ls,
        content_digest=digest,
    )
    lesson.validate()
    return lesson


class LessonRegistry:
    """Manages organizational lessons, conflict tracking, and scope boundary checks."""

    def __init__(self) -> None:
        self._lessons: dict[str, OrganizationalLesson] = {}
        self._conflicts: list[tuple[str, str, str]] = []

    def register_lesson(self, lesson: OrganizationalLesson, product_scope: str | None = None) -> None:
        lesson.validate()
        # L9-REQ-LRN-007: One-product success cannot silently become organization-wide rule
        if product_scope and lesson.applicability_scope == "GLOBAL":
            raise GlobalOvergeneralizationError(
                f"Lesson '{lesson.lesson_id}' observed for product '{product_scope}' cannot be registered with GLOBAL scope without cross-product qualification (L9-REQ-LRN-007)"
            )
        self._lessons[lesson.lesson_id] = lesson

    def get_lesson(self, lesson_id: str) -> OrganizationalLesson | None:
        return self._lessons.get(lesson_id)

    def record_conflict(self, lesson_id_a: str, lesson_id_b: str, explanation: str) -> None:
        """L9-REQ-LRN-005: Conflicting lessons remain explicit until evidence/authority resolves them."""
        self._conflicts.append((lesson_id_a, lesson_id_b, explanation))

    def get_conflicts(self) -> list[tuple[str, str, str]]:
        return list(self._conflicts)
