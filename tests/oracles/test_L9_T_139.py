"""Oracle test for L9-REQ-EVAL-004 / L9-T-139."""
from hyai.evaluation.spec import EvaluationEngine, SubjectType, ThresholdModificationForbiddenError, create_evaluation_spec
from ._support import oracle

def _good() -> bool:
    engine = EvaluationEngine()
    spec = create_evaluation_spec(
        evaluation_spec_id="evalspec_fixed_gates",
        subject_type=SubjectType.MODEL,
        metric_definitions=["precision"],
        thresholds={"precision": 0.95},
        benchmark_suite_ref="bench_suite_1",
        evaluator_ref="eval_exact",
    )
    engine.register_spec(spec)
    # Threshold modification post-observation must be rejected
    try:
        engine.assert_threshold_immutable("evalspec_fixed_gates", {"precision": 0.80})
        return False
    except ThresholdModificationForbiddenError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_139():
    oracle("L9-REQ-EVAL-004", "L9-T-139", _good, _bad)
