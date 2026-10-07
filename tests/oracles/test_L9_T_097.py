from hyai.product import ProductManager
from ._f03_support import product
from ._support import oracle
def test_l9_t_097():
    manager=ProductManager(); manager.create_product(product()); digest={"algorithm":"sha256","encoding":"hex","value":"a"*64}
    oracle("L9-REQ-PRD-006", "L9-T-097", lambda: manager.record_release("product_demo",source_commits=["a"*40],artifact_digests=[digest],verdict_refs=["verdict_1"],environment_ref="env",status="PROMOTED")["product_id"] == "product_demo", lambda: _bad(manager,digest))
def _bad(manager,digest):
    try: manager.record_release("product_demo",source_commits=[],artifact_digests=[digest],verdict_refs=["verdict_1"],environment_ref="env",status="PROMOTED")
    except ValueError: return False
    return True
