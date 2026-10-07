from hyai.assurance import ReviewRequest, ReviewSubject, ReviewVerdict, validate_verdict
from hyai.constitution.authority import Principal
from ._support import oracle

def test_l9_t_040_stale_verdict():
    subject = ReviewSubject("a" * 40, []); request = ReviewRequest("r", Principal("EXECUTOR", "e"), "a" * 40)
    verdict = ReviewVerdict("r", "a" * 40, subject.digest(), Principal("INDEPENDENT_REVIEWER", "i"), "PASS", [{"result":"PASS", "evidence_refs":["ev"]}])
    oracle("L9-REQ-ASS-004", "L9-T-040", lambda: validate_verdict(request, subject, verdict)[0], lambda: validate_verdict(request, subject, verdict, "b" * 40)[0])
