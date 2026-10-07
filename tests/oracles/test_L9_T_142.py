"""Oracle test for L9-REQ-EVAL-007 / L9-T-142."""
from hyai.evaluation.spec import EvaluationEngine, MissingRawEvidenceError, SubjectType, create_benchmark_suite, create_evaluation_spec
from ._support import oracle

def _good() -> bool:
    engine = EvaluationEngine()
    spec = create_evaluation_spec(
        evaluation_spec_id="evalspec_evidence_check",
        subject_type=SubjectType.TOOL,
        metric_definitions=["score"],
        thresholds={"score": 1.0},
        benchmark_suite_ref="bench_tool",
        evaluator_ref="eval_tool",
    )
    suite = create_benchmark_suite(
        suite_id="bench_tool",
        case_refs=["c1"],
        fixture_digests=[{"algorithm": "sha256", "encoding": "hex", "value": "d" * 64}],
    )
    # Missing raw evidence must be rejected
    try:
        engine.evaluate_candidate(
            candidate_id="tool_no_evidence",
            spec=spec,
            suite=suite,
            raw_evidence=[],
            measured_metrics={"score": 1.0},
        )
        return False
    except MissingRawEvidenceError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_142():
    oracle("L9-REQ-EVAL-007", "L9-T-142", _good, _bad)
