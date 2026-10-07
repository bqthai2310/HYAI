from hyai.compatibility import CompatibilityProfile, compute_digest, validate_breaking_change
from ._support import oracle

def test_l9_t_190_breaking_change_migration():
    profile = CompatibilityProfile("2.0.0", "compat_change", "contract", "2.0.0", "BREAKING", ["2.0.0"], ["migrate"], compute_digest(b"profile"))
    plan = {"new_version":"3.0.0", "rollback_analysis":"documented", "invalidation_analysis":"documented"}
    oracle("L9-REQ-CMP-003", "L9-T-190", lambda: validate_breaking_change(profile, plan)[0], lambda: validate_breaking_change(profile, None)[0])
