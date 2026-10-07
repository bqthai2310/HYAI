import hashlib
from hyai.assurance.review import ReviewSubject
from ._support import oracle
def test_l9_t_072_supply_chain_binding():
    s=ReviewSubject("e"*40,[{"path":"artifact","digest":hashlib.sha256(b"a").hexdigest()}],[],["v"])
    oracle("L9-REQ-SEC-003","L9-T-072",lambda:s.digest()["algorithm"]=="sha256" and bool(s.digest()["value"]),lambda:s.digest()==ReviewSubject("f"*40,[{"path":"artifact","digest":"x"}],[],["v"]).digest())
