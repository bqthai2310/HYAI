from ._support import ROOT, oracle
def test_l9_t_082_pr_review():
    workflow=(ROOT/".github/workflows/review-artifact-gate.yml").read_text()
    oracle("L9-REQ-GIT-002","L9-T-082",lambda:(ROOT/".github/workflows/review-artifact-gate.yml").is_file() and "pull_request" in workflow and "permissions:" in workflow and "contents: read" in workflow,lambda:"pull_request" not in workflow)
