from hyai.constitution.authority import AuthorityDecision, Principal, verify_material_action
from ._support import oracle
def test_l9_t_006_scope_lock():
    d=AuthorityDecision("d",Principal("PO","p"),"implement","scope/a","A1")
    oracle("L9-REQ-GOV-006","L9-T-006",lambda:verify_material_action(Principal("EXECUTOR","e"),"implement","scope/a","A1",d)[0],lambda:verify_material_action(Principal("EXECUTOR","e"),"implement","scope/b","A1",d)[0])
