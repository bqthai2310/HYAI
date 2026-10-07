"""Oracle test for L9-REQ-REV-002 / L9-T-132."""
from hyai.assurance.review import ReviewRequest, ReviewSubject, ReviewVerdict, validate_verdict
from hyai.constitution.authority import Principal, PrincipalType
from ._support import oracle

def _good() -> bool:
    req = ReviewRequest("req_01", Principal(PrincipalType.EXECUTOR, "hermes"), "head_123")
    subject = ReviewSubject(head_commit_sha="head_123", files=())
    # Tampered commit SHA must fail canonicalization
    verdict_tampered = ReviewVerdict(
        review_request_id="req_01",
        reviewed_commit_sha="head_tampered_456",
        review_subject_digest=subject.digest(),
        reviewer=Principal(PrincipalType.INDEPENDENT_REVIEWER, "muse"),
        verdict="PASS",
        criterion_results=({"criterion_id": "c1", "result": "PASS", "evidence_refs": ["ev_1"]},),
    )
    valid, reason = validate_verdict(req, subject, verdict_tampered)
    return not valid and "exact head commit" in reason

def _bad() -> bool:
    return False

def test_l9_t_132():
    oracle("L9-REQ-REV-002", "L9-T-132", _good, _bad)

