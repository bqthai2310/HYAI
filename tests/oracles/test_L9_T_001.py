from hyai.constitution.authority import AuthorityClass, AuthorityDecision, Principal, verify_material_action
from ._support import oracle
def test_l9_t_001_authority_hierarchy():
    po = Principal("PO", "po-1"); executor = Principal("EXECUTOR", "worker-1")
    decision = AuthorityDecision("d1", po, "implement", "component/x", AuthorityClass.A1)
    oracle("L9-REQ-GOV-001", "L9-T-001", lambda: verify_material_action(executor, "implement", "component/x", "A1", decision)[0], lambda: verify_material_action(executor, "implement", "component/x", "A1", None)[0])
