"""Structured telemetry, trace correlation, and evidence-backed SLO evaluation (OBS-001, 002, 005)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import timestamp


class ObservabilityError(Exception):
    """Base error for observability subsystem."""


class CorrelationError(ObservabilityError):
    """Raised when trace context lacks required correlation dimensions (L9-REQ-OBS-001)."""


class SLOBreachError(ObservabilityError):
    """Raised when measured evidence fails defined SLO threshold (L9-REQ-OBS-005)."""


@dataclass(frozen=True)
class TraceContext:
    goal_id: str
    program_id: str
    task_id: str
    attempt_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    def __post_init__(self) -> None:
        if not all((self.goal_id, self.program_id, self.task_id, self.attempt_id)):
            raise CorrelationError("TraceContext must correlate goal_id, program_id, task_id, and attempt_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "program_id": self.program_id,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
        }


@dataclass(frozen=True)
class StructuredLogRecord:
    timestamp: str
    level: str
    message: str
    trace_context: TraceContext
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "trace_context": self.trace_context.to_dict(),
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class StructuredMetricRecord:
    metric_name: str
    metric_type: str
    value: float
    timestamp: str
    trace_context: TraceContext
    dimensions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "value": float(self.value),
            "timestamp": self.timestamp,
            "trace_context": self.trace_context.to_dict(),
            "dimensions": dict(self.dimensions),
        }


@dataclass(frozen=True)
class SLOSpec:
    slo_id: str
    metric_name: str
    target_threshold: float
    comparison_operator: str = "<="
    evaluation_window: str = "24h"


@dataclass(frozen=True)
class SLOEvaluation:
    slo_id: str
    measured_value: float
    threshold: float
    is_compliant: bool
    sample_count: int
    evaluated_at: str


def evaluate_slo_compliance(
    spec: SLOSpec,
    measurements: Sequence[float],
) -> SLOEvaluation:
    """Evaluates SLO based on measured telemetry evidence (L9-REQ-OBS-005)."""
    if not measurements:
        raise ObservabilityError(f"Cannot evaluate SLO '{spec.slo_id}': no measured evidence provided")

    avg_value = sum(measurements) / len(measurements)
    if spec.comparison_operator == "<=":
        compliant = avg_value <= spec.target_threshold
    elif spec.comparison_operator == ">=":
        compliant = avg_value >= spec.target_threshold
    else:
        compliant = avg_value == spec.target_threshold

    return SLOEvaluation(
        slo_id=spec.slo_id,
        measured_value=avg_value,
        threshold=spec.target_threshold,
        is_compliant=compliant,
        sample_count=len(measurements),
        evaluated_at=timestamp(),
    )
