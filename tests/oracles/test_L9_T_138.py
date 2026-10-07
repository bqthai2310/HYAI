"""Oracle test for L9-REQ-EVAL-003 / L9-T-138."""
from hyai.evaluation.spec import RunResult, create_evaluation_run
from ._support import oracle

def _good() -> bool:
    digest = {"algorithm": "sha256", "encoding": "hex", "value": "f" * 64}
    run = create_evaluation_run(
        evaluation_run_id="evalrun_test_01",
        evaluation_spec_id="evalspec_standard",
        subject_digest=digest,
        suite_digest=digest,
        raw_evidence_refs=["ev_trace_log_01"],
        metrics={"accuracy": 0.98},
        result=RunResult.QUALIFIED,
    )
    return run.result == "QUALIFIED" and len(run.raw_evidence_refs) == 1

def _bad() -> bool:
    return False

def test_l9_t_138():
    oracle("L9-REQ-EVAL-003", "L9-T-138", _good, _bad)
