from hyai.security.governance import validate_audit_record
from ._support import oracle
def test_l9_t_075_auditability():
    good={"action":"change","actor":"a","timestamp":"2026-01-01T00:00:00Z","evidence_refs":["e"]}; bad={"action":"change","actor":"a","timestamp":"x","evidence_refs":[]}
    oracle("L9-REQ-SEC-006","L9-T-075",lambda:validate_audit_record(good)[0],lambda:validate_audit_record(bad)[0])
