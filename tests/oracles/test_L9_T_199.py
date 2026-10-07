import json
from pathlib import PurePosixPath
from ._support import ROOT, oracle
def _runtime_ok(path, zones): return any(str(PurePosixPath(path)).startswith(zone) for zone in zones)
def test_l9_t_199_runtime_write_zones():
    zones=json.loads((ROOT/"ROOT_LAYOUT_MANIFEST.json").read_text())["runtime_write_zones"]
    oracle("L9-REQ-FSG-004","L9-T-199",lambda:_runtime_ok(".hyai/cache/x",zones) and _runtime_ok("artifacts/x",zones),lambda:_runtime_ok("src/generated.py",zones))
