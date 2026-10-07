from hyai.compatibility import compute_digest
from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def test_l9_t_009_exact_directive_capture():
    ingress = NaturalLanguageIngress()
    text = "Keep  exact\nPO wording."
    oracle("L9-REQ-ING-001", "L9-T-009",
           lambda: (item := ingress.capture_raw_directive(text, "directive://9", {"principal_type": "PO", "id": "po"}))["raw_text"] == text and item["digest"] == compute_digest(text.encode()),
           lambda: ingress.capture_raw_directive(text, "directive://9", {"principal_type": "PO", "id": "po"})["digest"] == compute_digest(b"paraphrased"))
