from ._support import ROOT, oracle
def test_l9_t_143_canonical_source_tree():
    required=["src/hyai","tests","schemas","config","evidence"]
    oracle("L9-REQ-IMP-001","L9-T-143",lambda:all((ROOT/p).exists() for p in required),lambda:(ROOT/"unapproved-root").exists())
