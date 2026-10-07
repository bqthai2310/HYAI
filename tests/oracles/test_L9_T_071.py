from hyai.security.governance import contains_secret, redact_secrets
from ._support import oracle
def test_l9_t_071_secret_hygiene():
    safe={"event":"ok"}; leaked={"api_key":"sk-abcdefghijklmnop"}
    oracle("L9-REQ-SEC-002","L9-T-071",lambda:not contains_secret(safe) and not contains_secret(redact_secrets(leaked)),lambda:not contains_secret(leaked))
