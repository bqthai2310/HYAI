from hyai.assurance.review import ReviewRequest, ReviewSubject, ReviewVerdict, validate_verdict
from hyai.constitution.authority import Principal
from ._support import oracle
def test_l9_t_007_stop_rule():
    s=ReviewSubject("d"*40,[{"path":"x","digest":"d"}],[],["v"]); r=ReviewRequest("review_7",Principal("PO","p"),"d"*40); reviewer=Principal("INDEPENDENT_REVIEWER","r")
    done=ReviewVerdict("review_7","d"*40,s.digest(),reviewer,"PASS",[{"result":"PASS","evidence_refs":["proof"]}]); open_work=ReviewVerdict("review_7","d"*40,s.digest(),reviewer,"PASS",[{"result":"FAIL","evidence_refs":["proof"]}])
    oracle("L9-REQ-GOV-007","L9-T-007",lambda:validate_verdict(r,s,done)[0],lambda:validate_verdict(r,s,open_work)[0])
