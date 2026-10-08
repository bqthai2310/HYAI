"""Oracle test for L9-REQ-REV-004 / L9-T-134."""
from hyai.assurance.review import (
    ReviewGateway,
    ReviewRequest,
    ReviewSubject,
    ReviewVerdict,
    StaleAttestationError,
)
from hyai.constitution.authority import Principal, PrincipalType
from ._support import oracle

def _good() -> bool:
    gateway = ReviewGateway()
    req = ReviewRequest("req_01", Principal(PrincipalType.EXECUTOR, "hermes"), "head_old")
    subject = ReviewSubject(head_commit_sha="head_old", files=())
    verdict = ReviewVerdict(
        review_request_id="req_01",
        reviewed_commit_sha="head_old",
        review_subject_digest=subject.digest(),
        reviewer=Principal(PrincipalType.INDEPENDENT_REVIEWER, "muse"),
        verdict="PASS",
        criterion_results=({"criterion_id": "c1", "result": "PASS", "evidence_refs": ["ev_1"]},),
    )
    gateway.ingest_attestation(req, subject, verdict, current_head_sha="head_old")
    assert gateway.get_current_attestation("head_old") is not None
    # Invalidation on new head SHA
    gateway.invalidate_for_new_head("head_new")
    return gateway.get_current_attestation("head_old") is None

def _bad() -> bool:
    return False

def test_l9_t_134():
    oracle("L9-REQ-REV-004", "L9-T-134", _good, _bad)

