from ._support import ROOT, oracle
def test_l9_t_081_protected_main():
    workflow=(ROOT/".github/workflows/f00-acceptance-gate.yml").read_text()
    oracle("L9-REQ-GIT-001","L9-T-081",lambda:(ROOT/".github/workflows/f00-acceptance-gate.yml").is_file() and "pull_request" in workflow and "contents: read" in workflow and "pytest tests/" in workflow,lambda:"push:" in workflow and "main" in workflow)
