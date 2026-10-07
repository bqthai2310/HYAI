import pytest
from hyai.compatibility import CompatibilityProfile, compute_digest, is_stable_core_isolated, validate_breaking_change, validate_digest_spec


def test_algorithm_agile_digest_registry():
    assert validate_digest_spec(compute_digest(b"data", "sha384"))
    assert not validate_digest_spec({"sha256": "legacy"})
    with pytest.raises(ValueError): compute_digest(b"data", "md5")


def test_breaking_profile_needs_new_version_and_recovery_analysis():
    profile = CompatibilityProfile("2", "compat_x", "x", "2", "BREAKING", ["2"], ["migration"], compute_digest(b"x"))
    assert validate_breaking_change(profile, {"new_version":"3", "rollback":"yes", "invalidation":"yes"})[0]
    assert not validate_breaking_change(profile, {"new_version":"2", "rollback":"yes", "invalidation":"yes"})[0]
    assert is_stable_core_isolated("from hyai.kernel import EventEnvelope")
    assert not is_stable_core_isolated("from openai import OpenAI")
