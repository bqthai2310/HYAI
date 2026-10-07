from hyai.assurance import EvidenceItem, validate_evidence_item
from hyai.compatibility import compute_digest
from hyai.constitution.authority import Principal
from ._support import oracle

def test_l9_t_038_evidence_schema():
    good = EvidenceItem("ev_one", Principal("ASSURANCE_SERVICE", "assurance"), "subject", compute_digest(b"evidence"))
    bad = EvidenceItem("ev_two", Principal("ASSURANCE_SERVICE", "assurance"), "", compute_digest(b"evidence"))
    oracle("L9-REQ-ASS-002", "L9-T-038", lambda: validate_evidence_item(good)[0], lambda: validate_evidence_item(bad)[0])
