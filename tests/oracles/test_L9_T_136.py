"""Oracle test for L9-REQ-EVAL-001 / L9-T-136."""
from hyai.evaluation.spec import SubjectType, create_evaluation_spec
from ._support import oracle

def _good() -> bool:
    spec = create_evaluation_spec(
        evaluation_spec_id="evalspec_parser_benchmark",
        subject_type=SubjectType.SKILL,
        metric_definitions=["f1_score", "latency_ms"],
        thresholds={"f1_score": 0.90, "latency_ms": 250.0},
        benchmark_suite_ref="bench_parser_suite_v1",
        evaluator_ref="evaluator_exact_match",
    )
    return spec.thresholds == {"f1_score": 0.90, "latency_ms": 250.0}

def _bad() -> bool:
    return False

def test_l9_t_136():
    oracle("L9-REQ-EVAL-001", "L9-T-136", _good, _bad)
