from hyai.assurance.review import ReviewRequest,ReviewSubject,ReviewVerdict,validate_verdict
from hyai.constitution.authority import Principal
from ._support import oracle
def test_l9_t_085_independent_review():
    s=ReviewSubject("a"*40,[{"path":"x","digest":"x"}],[],["v"]); r=ReviewRequest("review_85",Principal("EXECUTOR","e"),"a"*40); good=ReviewVerdict("review_85","a"*40,s.digest(),Principal("INDEPENDENT_REVIEWER","i"),"PASS",[{"result":"PASS","evidence_refs":["e"]}]); bad=ReviewVerdict("review_85","b"*40,s.digest(),Principal("INDEPENDENT_REVIEWER","i"),"PASS",[{"result":"PASS","evidence_refs":["e"]}])
    oracle("L9-REQ-GIT-005","L9-T-085",lambda:validate_verdict(r,s,good)[0],lambda:validate_verdict(r,s,bad)[0])
