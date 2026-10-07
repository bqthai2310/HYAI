from hyai.product import ProductManager
from ._f03_support import product
from ._support import oracle
def test_l9_t_099():
    manager=ProductManager(); manager.create_product(product())
    oracle("L9-REQ-PRD-008", "L9-T-099", lambda: manager.retire_product("product_demo","decision_1",["evidence_1"],"retention_1")["lifecycle_state"] == "RETIRED", lambda: _bad(manager))
def _bad(manager):
    try: manager.retire_product("product_demo","",[],"")
    except ValueError: return False
    return True
