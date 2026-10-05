from hyai.assurance.review import ReviewRequest, ReviewSubject, ReviewVerdict, validate_verdict
from hyai.constitution.authority import Principal
from ._support import oracle
def test_l9_t_002_no_self_approval():
    subject = ReviewSubject("a"*40, [{"path":"x.py","digest":"d"}],["c"],["a1"]); request = ReviewRequest("review_1", Principal("EXECUTOR","e1"), "a"*40)
    good = ReviewVerdict("review_1", "a"*40, subject.digest(), Principal("INDEPENDENT_REVIEWER","r1"), "PASS", [{"result":"PASS","evidence_refs":["e"]}])
    bad = ReviewVerdict("review_1", "a"*40, subject.digest(), Principal("EXECUTOR","e1"), "PASS", [{"result":"PASS","evidence_refs":["e"]}])
    oracle("L9-REQ-GOV-002", "L9-T-002", lambda: validate_verdict(request,subject,good)[0], lambda: validate_verdict(request,subject,bad)[0])
