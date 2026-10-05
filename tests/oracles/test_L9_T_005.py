from hyai.constitution.authority import AuthorityDecision, Principal, verify_decision
from ._support import oracle
def test_l9_t_005_change_control():
    good=AuthorityDecision("adr-1",Principal("ARCHITECT","a"),"change","architecture/core","A3",evidence_refs=("adr","impact")); bad=AuthorityDecision("adr-2",Principal("EXECUTOR","e"),"change","architecture/core","A3")
    oracle("L9-REQ-GOV-005","L9-T-005",lambda:bool(good.evidence_refs) and verify_decision("change","architecture/core","A3",good)[0],lambda:verify_decision("change","architecture/core","A3",bad)[0])
