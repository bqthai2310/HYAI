from hyai.compatibility import compute_digest, validate_digest_spec
from ._support import oracle

def test_l9_t_192_crypto_agility():
    oracle("L9-REQ-CMP-005", "L9-T-192", lambda: validate_digest_spec(compute_digest(b"crypto", "sha512")), lambda: validate_digest_spec({"sha256": "legacy"}))
