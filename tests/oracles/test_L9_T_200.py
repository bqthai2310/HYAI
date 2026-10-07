from pathlib import Path
from hyai.product import ProductWorkspaceManager
from ._support import ROOT, oracle
def test_l9_t_200():
    manager=ProductWorkspaceManager(ROOT)
    oracle("L9-REQ-FSG-005", "L9-T-200", lambda: manager.ensure_workspace_isolation("product_demo",ROOT/"workspaces"/"product_demo"/"src") == (ROOT/"workspaces"/"product_demo"/"src").resolve(), lambda: _bad(manager))
def _bad(manager):
    try: manager.ensure_workspace_isolation("product_demo",ROOT/"src"/"sprawl.py")
    except ValueError: return False
    return True
