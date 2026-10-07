from hyai.constitution.authority import AuthorityDecision, Principal, verify_decision
from ._support import oracle
def test_l9_t_008_decision_provenance():
    good=AuthorityDecision("decision-1",Principal("PO","p"),"release","r","A4",evidence_refs=("evidence",)); bad=AuthorityDecision("decision-2",Principal("EXECUTOR","e"),"release","r","A4")
    oracle("L9-REQ-GOV-008","L9-T-008",lambda:bool(good.evidence_refs) and verify_decision("release","r","A4",good)[0],lambda:verify_decision("release","r","A4",bad)[0])
