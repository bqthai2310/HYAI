from hyai.constitution.authority import Principal
from hyai.security.governance import validate_protected_changes
from ._support import oracle
def test_l9_t_074_protected_paths():
    oracle("L9-REQ-SEC-005","L9-T-074",lambda:validate_protected_changes(["schemas/x.json"],Principal("ARCHITECT","a"))[0],lambda:validate_protected_changes([".github/workflows/x.yml"],Principal("EXECUTOR","e"))[0])
