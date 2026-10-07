"""Evaluation specifications, benchmark suites, runs, and regression gating (EVAL-001..007)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest


class EvaluationError(Exception):
    """Base error for evaluation subsystem."""


class RegressionQuarantineError(EvaluationError):
    """Raised when candidate has material regression and is quarantined (L9-REQ-EVAL-005)."""


class ThresholdModificationForbiddenError(EvaluationError):
    """Raised when thresholds are modified post-observation without new evaluation version (L9-REQ-EVAL-004)."""


class NarrativeScoreRejectedError(EvaluationError):
    """Raised when optimization uses narrative scores rather than raw evaluation evidence (L9-REQ-EVAL-006)."""


class MissingRawEvidenceError(EvaluationError):
    """Raised when aggregate metric replaces or omits raw evaluation evidence (L9-REQ-EVAL-007)."""


class SubjectType(str, Enum):
    SKILL = "SKILL"
    MODEL = "MODEL"
    TOOL = "TOOL"
    STRATEGY = "STRATEGY"
    RESOLVER = "RESOLVER"
    WORKFLOW = "WORKFLOW"


class RunResult(str, Enum):
    QUALIFIED = "QUALIFIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class BenchmarkSuite:
    schema_version: str
    suite_id: str
    case_refs: tuple[str, ...]
    fixture_digests: tuple[dict[str, str], ...]
    leakage_policy: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^bench_", self.suite_id):
            raise EvaluationError(f"suite_id '{self.suite_id}' must begin with 'bench_'")
        object.__setattr__(self, "case_refs", tuple(self.case_refs))
        object.__setattr__(self, "fixture_digests", tuple(self.fixture_digests))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "suite_id": self.suite_id,
            "case_refs": list(self.case_refs),
            "fixture_digests": list(self.fixture_digests),
            "leakage_policy": self.leakage_policy,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "BenchmarkSuite":
        validate_benchmark_suite_document(self.to_dict())
        return self


def validate_benchmark_suite_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "benchmark_suite.schema.json", EvaluationError)
    except Exception as exc:
        raise EvaluationError(str(exc)) from exc


def create_benchmark_suite(
    *,
    suite_id: str,
    case_refs: Sequence[str],
    fixture_digests: Sequence[Mapping[str, str]],
    leakage_policy: str = "ZERO_LEAKAGE_STRICT",
    schema_version: str = "2.1.0",
) -> BenchmarkSuite:
    payload = {
        "suite_id": suite_id,
        "case_refs": tuple(case_refs),
        "fixture_digests": tuple(dict(d) for d in fixture_digests),
        "leakage_policy": leakage_policy,
    }
    digest = compute_digest(canonical(payload))
    suite = BenchmarkSuite(
        schema_version=schema_version,
        suite_id=suite_id,
        case_refs=tuple(case_refs),
        fixture_digests=tuple(dict(d) for d in fixture_digests),
        leakage_policy=leakage_policy,
        content_digest=digest,
    )
    suite.validate()
    return suite


@dataclass(frozen=True)
class EvaluationSpec:
    schema_version: str
    evaluation_spec_id: str
    subject_type: str
    metric_definitions: tuple[str, ...]
    thresholds: dict[str, Any]
    benchmark_suite_ref: str
    evaluator_ref: str
    content_digest: dict[str, str]

    def __post_init__(self) -> None:
        if not re.match(r"^evalspec_", self.evaluation_spec_id):
            raise EvaluationError(f"evaluation_spec_id '{self.evaluation_spec_id}' must begin with 'evalspec_'")
        object.__setattr__(self, "subject_type", SubjectType(self.subject_type).value)
        object.__setattr__(self, "metric_definitions", tuple(self.metric_definitions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evaluation_spec_id": self.evaluation_spec_id,
            "subject_type": self.subject_type,
            "metric_definitions": list(self.metric_definitions),
            "thresholds": dict(self.thresholds),
            "benchmark_suite_ref": self.benchmark_suite_ref,
            "evaluator_ref": self.evaluator_ref,
            "content_digest": dict(self.content_digest),
        }

    def validate(self) -> "EvaluationSpec":
        validate_evaluation_spec_document(self.to_dict())
        return self


def validate_evaluation_spec_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "evaluation_spec.schema.json", EvaluationError)
    except Exception as exc:
        raise EvaluationError(str(exc)) from exc


def create_evaluation_spec(
    *,
    evaluation_spec_id: str,
    subject_type: SubjectType | str,
    metric_definitions: Sequence[str],
    thresholds: Mapping[str, Any],
    benchmark_suite_ref: str,
    evaluator_ref: str,
    schema_version: str = "2.1.0",
) -> EvaluationSpec:
    st = subject_type.value if isinstance(subject_type, SubjectType) else str(subject_type)
    payload = {
        "evaluation_spec_id": evaluation_spec_id,
        "subject_type": st,
        "metric_definitions": tuple(metric_definitions),
        "thresholds": dict(thresholds),
        "benchmark_suite_ref": benchmark_suite_ref,
        "evaluator_ref": evaluator_ref,
    }
    digest = compute_digest(canonical(payload))
    spec = EvaluationSpec(
        schema_version=schema_version,
        evaluation_spec_id=evaluation_spec_id,
        subject_type=st,
        metric_definitions=tuple(metric_definitions),
        thresholds=dict(thresholds),
        benchmark_suite_ref=benchmark_suite_ref,
        evaluator_ref=evaluator_ref,
        content_digest=digest,
    )
    spec.validate()
    return spec


@dataclass(frozen=True)
class EvaluationRun:
    schema_version: str
    evaluation_run_id: str
    evaluation_spec_id: str
    subject_digest: dict[str, str]
    suite_digest: dict[str, str]
    raw_evidence_refs: tuple[str, ...]
    metrics: dict[str, Any]
    result: str
    created_at: str

    def __post_init__(self) -> None:
        if not re.match(r"^evalrun_", self.evaluation_run_id):
            raise EvaluationError(f"evaluation_run_id '{self.evaluation_run_id}' must begin with 'evalrun_'")
        if not re.match(r"^evalspec_", self.evaluation_spec_id):
            raise EvaluationError(f"evaluation_spec_id '{self.evaluation_spec_id}' must begin with 'evalspec_'")
        object.__setattr__(self, "result", RunResult(self.result).value)
        object.__setattr__(self, "raw_evidence_refs", tuple(self.raw_evidence_refs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evaluation_run_id": self.evaluation_run_id,
            "evaluation_spec_id": self.evaluation_spec_id,
            "subject_digest": dict(self.subject_digest),
            "suite_digest": dict(self.suite_digest),
            "raw_evidence_refs": list(self.raw_evidence_refs),
            "metrics": dict(self.metrics),
            "result": self.result,
            "created_at": self.created_at,
        }

    def validate(self) -> "EvaluationRun":
        validate_evaluation_run_document(self.to_dict())
        return self


def validate_evaluation_run_document(document: Mapping[str, Any]) -> None:
    try:
        validate(document, "evaluation_run.schema.json", EvaluationError)
    except Exception as exc:
        raise EvaluationError(str(exc)) from exc


def create_evaluation_run(
    *,
    evaluation_run_id: str,
    evaluation_spec_id: str,
    subject_digest: Mapping[str, str],
    suite_digest: Mapping[str, str],
    raw_evidence_refs: Sequence[str],
    metrics: Mapping[str, Any],
    result: RunResult | str,
    created_at: str | None = None,
    schema_version: str = "2.1.0",
) -> EvaluationRun:
    run = EvaluationRun(
        schema_version=schema_version,
        evaluation_run_id=evaluation_run_id,
        evaluation_spec_id=evaluation_spec_id,
        subject_digest=dict(subject_digest),
        suite_digest=dict(suite_digest),
        raw_evidence_refs=tuple(raw_evidence_refs),
        metrics=dict(metrics),
        result=result.value if isinstance(result, RunResult) else str(result),
        created_at=created_at or timestamp(),
    )
    run.validate()
    return run


class EvaluationEngine:
    """Orchestrates candidate evaluation, threshold enforcement, and regression gating."""

    def __init__(self) -> None:
        self._specs: dict[str, EvaluationSpec] = {}

    def register_spec(self, spec: EvaluationSpec) -> None:
        spec.validate()
        self._specs[spec.evaluation_spec_id] = spec

    def assert_threshold_immutable(self, spec_id: str, proposed_thresholds: Mapping[str, Any]) -> None:
        spec = self._specs.get(spec_id)
        if spec and spec.thresholds != proposed_thresholds:
            raise ThresholdModificationForbiddenError(
                f"Thresholds for spec '{spec_id}' are immutable post-observation (L9-REQ-EVAL-004)"
            )

    def evaluate_candidate(
        self,
        candidate_id: str,
        spec: EvaluationSpec,
        suite: BenchmarkSuite,
        raw_evidence: Sequence[str],
        measured_metrics: Mapping[str, float],
        narrative_only: bool = False,
    ) -> EvaluationRun:
        # L9-REQ-EVAL-006: Optimization requires evaluation evidence, not narrative score
        if narrative_only or not measured_metrics:
            raise NarrativeScoreRejectedError("Candidate optimization cannot use narrative score without evidence (L9-REQ-EVAL-006)")

        # L9-REQ-EVAL-007: Aggregate metric does not replace raw evaluation evidence
        if not raw_evidence:
            raise MissingRawEvidenceError("Evaluation requires raw evidence refs; aggregate metrics cannot replace them (L9-REQ-EVAL-007)")

        # L9-REQ-EVAL-005: Material regression blocks/quarantines candidate
        has_regression = any(
            measured_metrics.get(metric, 0.0) < spec.thresholds.get(metric, 0.0)
            for metric in spec.thresholds
        )
        run_result = RunResult.FAILED if has_regression else RunResult.QUALIFIED

        run = create_evaluation_run(
            evaluation_run_id=f"evalrun_{candidate_id}_{spec.evaluation_spec_id[:8]}",
            evaluation_spec_id=spec.evaluation_spec_id,
            subject_digest=compute_digest(candidate_id.encode()),
            suite_digest=suite.content_digest,
            raw_evidence_refs=raw_evidence,
            metrics=dict(measured_metrics),
            result=run_result,
        )
        if has_regression:
            raise RegressionQuarantineError(f"Candidate '{candidate_id}' failed thresholds: quarantined (L9-REQ-EVAL-005)")
        return run
