from hyai.assurance.review import ReviewRequest, ReviewSubject, ReviewVerdict, validate_verdict
from hyai.constitution.authority import Principal
from ._support import oracle
def test_l9_t_004_evidence_binding():
    subject=ReviewSubject("b"*40,[{"path":"a","digest":"1"}],["c"],["v"]); request=ReviewRequest("review_4",Principal("PO","p"),"b"*40)
    good=ReviewVerdict("review_4","b"*40,subject.digest(),Principal("ASSURANCE_SERVICE","s"),"PASS",[{"result":"PASS","evidence_refs":["e"]}]); bad=ReviewVerdict("review_4","c"*40,subject.digest(),Principal("ASSURANCE_SERVICE","s"),"PASS",[{"result":"PASS","evidence_refs":["e"]}])
    oracle("L9-REQ-GOV-004","L9-T-004",lambda:validate_verdict(request,subject,good)[0],lambda:validate_verdict(request,subject,bad)[0])
