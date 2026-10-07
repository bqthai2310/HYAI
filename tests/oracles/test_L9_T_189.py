from hyai.compatibility import CompatibilityProfile, compute_digest
from ._support import oracle

def test_l9_t_189_compatibility_profile():
    good = CompatibilityProfile("2.0.0", "compat_kernel", "kernel", "2.1.0", "BACKWARD_COMPATIBLE", ["2.0.0"], [], compute_digest(b"profile"))
    bad = CompatibilityProfile("2.0.0", "bad", "kernel", "2.1.0", "UNKNOWN", [], [], compute_digest(b"profile"))
    def invalid():
        try: return bad.validate()
        except ValueError: return False
    oracle("L9-REQ-CMP-002", "L9-T-189", lambda: good.validate(), invalid)
