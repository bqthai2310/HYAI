from hyai.bootstrap.runner import bootstrap
from ._support import ROOT, oracle
def test_l9_t_147_deterministic_bootstrap():
    oracle("L9-REQ-IMP-005","L9-T-147",lambda:bootstrap(ROOT)==bootstrap(ROOT) and bootstrap(ROOT)["result"]=="PASS" and not bootstrap(ROOT)["secrets_required"],lambda:bootstrap(ROOT)["secrets_required"])
