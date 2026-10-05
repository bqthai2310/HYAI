from ._support import ROOT, oracle
def test_l9_t_083_required_checks():
    workflow=(ROOT/".github/workflows/f00-acceptance-gate.yml").read_text()
    oracle("L9-REQ-GIT-003","L9-T-083",lambda:"pytest tests/" in workflow,lambda:"pytest tests/" not in workflow)
