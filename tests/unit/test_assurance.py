from hyai.assurance import EvidenceItem, ReviewRequest, ReviewSubject, ReviewVerdict, can_promote_to_production, validate_adversarial_coverage, validate_evidence_item, validate_verdict
from hyai.compatibility import compute_digest
from hyai.constitution.authority import Principal


def test_subject_evidence_and_verdict_bind_exact_commit():
    subject = ReviewSubject("a" * 40, [{"path":"x"}]); request = ReviewRequest("review", Principal("EXECUTOR", "e"), "a" * 40)
    evidence = EvidenceItem("ev_unit", Principal("ASSURANCE_SERVICE", "a"), "subject", compute_digest(b"e"))
    verdict = ReviewVerdict("review", "a" * 40, subject.digest(), Principal("INDEPENDENT_REVIEWER", "r"), "PASS", [{"result":"PASS", "evidence_refs":["ev_unit"]}])
    assert validate_evidence_item(evidence)[0]
    assert validate_verdict(request, subject, verdict)[0]
    assert not validate_verdict(request, subject, verdict, "b" * 40)[0]


def test_high_risk_needs_adversarial_coverage_and_promotion_is_separate():
    subject = ReviewSubject("a" * 40, [])
    verdict = ReviewVerdict("review", "a" * 40, {}, Principal("INDEPENDENT_REVIEWER", "r"), "PASS")
    assert validate_adversarial_coverage(subject, [{"criterion_id":"negative test", "result":"PASS"}], "high")[0]
    assert not validate_adversarial_coverage(subject, [], "high")[0]
    assert not can_promote_to_production(verdict, None)
    assert can_promote_to_production(verdict, Principal("PO", "po"))
