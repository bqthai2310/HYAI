from hyai.assurance import ReviewSubject, validate_adversarial_coverage
from ._support import oracle

def test_l9_t_041_adversarial_coverage():
    subject = ReviewSubject("a" * 40, [])
    oracle("L9-REQ-ASS-005", "L9-T-041", lambda: validate_adversarial_coverage(subject, [{"criterion_id":"negative-input", "result":"PASS"}], "high")[0], lambda: validate_adversarial_coverage(subject, [], "high")[0])
