from hyai.constitution.authority import Principal
from hyai.security.governance import validate_protected_changes
from ._support import oracle
def test_l9_t_086_protected_workflows():
    oracle("L9-REQ-GIT-006","L9-T-086",lambda:validate_protected_changes([".github/workflows/gate.yml"],Principal("PO","p"))[0],lambda:validate_protected_changes([".github/workflows/gate.yml"],Principal("EXECUTOR","e"))[0])
