from hyai.assurance import ReviewRequest, ReviewSubject, ReviewVerdict, validate_verdict
from hyai.constitution.authority import Principal
from ._support import oracle

def test_l9_t_039_verdict_semantics():
    subject = ReviewSubject("a" * 40, []) ; request = ReviewRequest("r", Principal("EXECUTOR", "e"), "a" * 40)
    good = ReviewVerdict("r", "a" * 40, subject.digest(), Principal("INDEPENDENT_REVIEWER", "i"), "PASS", [{"result": "PASS", "evidence_refs": ["ev"]}])
    bad = ReviewVerdict("r", "a" * 40, subject.digest(), Principal("INDEPENDENT_REVIEWER", "i"), "PASS", [])
    oracle("L9-REQ-ASS-003", "L9-T-039", lambda: validate_verdict(request, subject, good)[0], lambda: validate_verdict(request, subject, bad)[0])
