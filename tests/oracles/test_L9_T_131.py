"""Oracle test for L9-REQ-REV-001 / L9-T-131."""
from hyai.assurance.review import ReviewRequest, ReviewSubject, ReviewVerdict, validate_verdict
from hyai.constitution.authority import Principal, PrincipalType
from ._support import oracle

def _good() -> bool:
    req = ReviewRequest("req_01", Principal(PrincipalType.EXECUTOR, "hermes"), "head_commit_sha_123")
    subject = ReviewSubject(head_commit_sha="head_commit_sha_123", files=())
    verdict_self = ReviewVerdict(
        review_request_id="req_01",
        reviewed_commit_sha="head_commit_sha_123",
        review_subject_digest=subject.digest(),
        reviewer=Principal(PrincipalType.EXECUTOR, "hermes"),
        verdict="PASS",
    )
    # Self-approval by executor must be rejected
    valid, reason = validate_verdict(req, subject, verdict_self)
    assert not valid and "NO_SELF_APPROVAL" in reason
    # Independent review by PO or INDEPENDENT_REVIEWER is permitted
    verdict_indep = ReviewVerdict(
        review_request_id="req_01",
        reviewed_commit_sha="head_commit_sha_123",
        review_subject_digest=subject.digest(),
        reviewer=Principal(PrincipalType.INDEPENDENT_REVIEWER, "muse"),
        verdict="PASS",
        criterion_results=({"criterion_id": "c1", "result": "PASS", "evidence_refs": ["ev_1"]},),
    )
    valid_indep, _ = validate_verdict(req, subject, verdict_indep)
    return valid_indep

def _bad() -> bool:
    return False

def test_l9_t_131():
    oracle("L9-REQ-REV-001", "L9-T-131", _good, _bad)

