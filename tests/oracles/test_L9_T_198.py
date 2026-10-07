from hyai.constitution.authority import Principal
from hyai.security.governance import validate_protected_changes
from ._support import oracle
def test_l9_t_198_executor_cannot_legalize_output():
    path=["ROOT_LAYOUT_MANIFEST.json"]
    oracle("L9-REQ-FSG-003","L9-T-198",lambda:validate_protected_changes(path,Principal("PO","p"))[0],lambda:validate_protected_changes(path,Principal("EXECUTOR","e"))[0])
