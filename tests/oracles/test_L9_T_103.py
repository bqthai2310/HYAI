from hyai.acceptance.compiler import AcceptanceCompilationError, build_oracle_result
from hyai.compatibility import compute_digest
from ._support import oracle


def test_l9_t_103():
    digest = compute_digest(b"oracle subject")
    oracle("L9-REQ-ORC-004", "L9-T-103", lambda: build_oracle_result("L9-T-103", digest, "PASS", [{"assertion": "bind subject", "result": "PASS"}], ["ev_raw"])["subject_digest"] == digest, lambda: _bad(digest))


def _bad(digest):
    try:
        build_oracle_result("L9-T-103", digest, "PASS", [{"assertion": "bind subject", "result": "FAIL"}], ["ev_raw"])
    except AcceptanceCompilationError:
        return False
    return True
