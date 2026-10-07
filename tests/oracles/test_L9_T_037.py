import pytest
from hyai.assurance import ReviewSubject
from ._support import oracle

def test_l9_t_037_review_subject():
    subject = ReviewSubject("a" * 40, [{"path": "x", "digest": "1"}])
    def mutable():
        try: subject.files[0]["path"] = "changed"
        except TypeError: return False
        return True
    oracle("L9-REQ-ASS-001", "L9-T-037", lambda: subject.digest() == subject.digest(), mutable)
