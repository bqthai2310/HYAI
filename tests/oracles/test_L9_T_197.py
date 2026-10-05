import importlib.util
from ._support import ROOT, oracle
spec=importlib.util.spec_from_file_location("root_guard",ROOT/"scripts/root_guard.py"); root_guard=importlib.util.module_from_spec(spec); spec.loader.exec_module(root_guard)
def test_l9_t_197_no_undeclared_root_entry(tmp_path):
    manifest=(ROOT/"ROOT_LAYOUT_MANIFEST.json").read_text(); (tmp_path/"ROOT_LAYOUT_MANIFEST.json").write_text(manifest); (tmp_path/"src").mkdir()
    allowed=__import__("json").loads(manifest)["allowed_root_directories"]
    for item in allowed:
        p=tmp_path/item
        if not p.exists(): p.mkdir()
    for item in __import__("json").loads(manifest)["allowed_root_files"]:
        if item!="ROOT_LAYOUT_MANIFEST.json": (tmp_path/item).write_text("")
    snap=root_guard.take_snapshot(tmp_path); baseline=root_guard.verify_root(snap,"t",tmp_path)["result"] == "PASS"; (tmp_path/"rogue").mkdir()
    oracle("L9-REQ-FSG-002","L9-T-197",lambda:baseline,lambda:root_guard.verify_root(snap,"t",tmp_path)["result"]=="PASS")
