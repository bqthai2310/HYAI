"""Oracle test for L9-REQ-REV-003 / L9-T-133."""
from hyai.assurance.review import (
    NonIndependentAttestationError,
    ReviewGateway,
    ReviewRequest,
    ReviewSubject,
    ReviewVerdict,
    SelfApprovalError,
)
from hyai.constitution.authority import Principal, PrincipalType
from ._support import oracle

def _good() -> bool:
    gateway = ReviewGateway()
    req = ReviewRequest("req_01", Principal(PrincipalType.EXECUTOR, "hermes"), "head_123")
    subject = ReviewSubject(head_commit_sha="head_123", files=())
    verdict_executor = ReviewVerdict(
        review_request_id="req_01",
        reviewed_commit_sha="head_123",
        review_subject_digest=subject.digest(),
        reviewer=Principal(PrincipalType.EXECUTOR, "hermes"),
        verdict="PASS",
    )
    # Gateway rejects non-independent attestation
    try:
        gateway.ingest_attestation(req, subject, verdict_executor, current_head_sha="head_123")
        return False
    except (SelfApprovalError, NonIndependentAttestationError):
        pass
    verdict_valid = ReviewVerdict(
        review_request_id="req_01",
        reviewed_commit_sha="head_123",
        review_subject_digest=subject.digest(),
        reviewer=Principal(PrincipalType.INDEPENDENT_REVIEWER, "muse"),
        verdict="PASS",
        criterion_results=({"criterion_id": "c1", "result": "PASS", "evidence_refs": ["ev_1"]},),
    )
    att = gateway.ingest_attestation(req, subject, verdict_valid, current_head_sha="head_123")
    return att["reviewer_id"] == "muse"

def _bad() -> bool:
    return False

def test_l9_t_133():
    oracle("L9-REQ-REV-003", "L9-T-133", _good, _bad)

