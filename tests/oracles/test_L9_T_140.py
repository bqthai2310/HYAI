"""Oracle test for L9-REQ-EVAL-005 / L9-T-140."""
from hyai.evaluation.spec import EvaluationEngine, RegressionQuarantineError, SubjectType, create_benchmark_suite, create_evaluation_spec
from ._support import oracle

def _good() -> bool:
    engine = EvaluationEngine()
    spec = create_evaluation_spec(
        evaluation_spec_id="evalspec_latency_floor",
        subject_type=SubjectType.SKILL,
        metric_definitions=["throughput"],
        thresholds={"throughput": 100.0},
        benchmark_suite_ref="bench_perf",
        evaluator_ref="eval_timer",
    )
    suite = create_benchmark_suite(
        suite_id="bench_perf",
        case_refs=["c1"],
        fixture_digests=[{"algorithm": "sha256", "encoding": "hex", "value": "b" * 64}],
    )
    # Candidate regression (measured 50.0 < threshold 100.0) must trigger quarantine error
    try:
        engine.evaluate_candidate(
            candidate_id="skill_regressed_v2",
            spec=spec,
            suite=suite,
            raw_evidence=["ev_perf_log"],
            measured_metrics={"throughput": 50.0},
        )
        return False
    except RegressionQuarantineError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_140():
    oracle("L9-REQ-EVAL-005", "L9-T-140", _good, _bad)
