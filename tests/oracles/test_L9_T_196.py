import json
from ._support import ROOT, oracle
def test_l9_t_196_root_manifest_lock():
    manifest=json.loads((ROOT/"ROOT_LAYOUT_MANIFEST.json").read_text())
    oracle("L9-REQ-FSG-001","L9-T-196",lambda:manifest["protected"] and "ARCHITECTURE_AUTHORITY" in manifest["authority_to_change"],lambda:manifest.get("executor_may_modify_manifest",True))
