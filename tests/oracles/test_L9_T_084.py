from ._support import ROOT, oracle
def test_l9_t_084_review_artifacts():
    workflow=(ROOT/".github/workflows/review-artifact-gate.yml").read_text()
    oracle("L9-REQ-GIT-004","L9-T-084",lambda:"--review-artifacts" in workflow,lambda:"--review-artifacts" not in workflow)
