"""Oracle test for L9-REQ-EVAL-006 / L9-T-141."""
from hyai.evaluation.spec import EvaluationEngine, NarrativeScoreRejectedError, SubjectType, create_benchmark_suite, create_evaluation_spec
from ._support import oracle

def _good() -> bool:
    engine = EvaluationEngine()
    spec = create_evaluation_spec(
        evaluation_spec_id="evalspec_reasoning",
        subject_type=SubjectType.STRATEGY,
        metric_definitions=["accuracy"],
        thresholds={"accuracy": 0.90},
        benchmark_suite_ref="bench_cases",
        evaluator_ref="eval_exact",
    )
    suite = create_benchmark_suite(
        suite_id="bench_cases",
        case_refs=["c1"],
        fixture_digests=[{"algorithm": "sha256", "encoding": "hex", "value": "c" * 64}],
    )
    # Narrative score without evidence must be rejected
    try:
        engine.evaluate_candidate(
            candidate_id="strat_narrative_only",
            spec=spec,
            suite=suite,
            raw_evidence=["ev_1"],
            measured_metrics={},
            narrative_only=True,
        )
        return False
    except NarrativeScoreRejectedError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_141():
    oracle("L9-REQ-EVAL-006", "L9-T-141", _good, _bad)
