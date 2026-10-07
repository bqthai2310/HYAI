"""Oracle test for L9-REQ-EVAL-002 / L9-T-137."""
from hyai.evaluation.spec import create_benchmark_suite
from ._support import oracle

def _good() -> bool:
    suite = create_benchmark_suite(
        suite_id="bench_reasoning_gold",
        case_refs=["case_01", "case_02"],
        fixture_digests=[{"algorithm": "sha256", "encoding": "hex", "value": "a" * 64}],
        leakage_policy="ZERO_LEAKAGE_HASH_SALTED",
    )
    return suite.leakage_policy == "ZERO_LEAKAGE_HASH_SALTED" and len(suite.fixture_digests) == 1

def _bad() -> bool:
    return False

def test_l9_t_137():
    oracle("L9-REQ-EVAL-002", "L9-T-137", _good, _bad)
