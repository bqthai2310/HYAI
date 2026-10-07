from hyai.product import ProductManager
from ._f03_support import product
from ._support import oracle
def test_l9_t_095():
    manager=ProductManager(); manager.create_product(product())
    oracle("L9-REQ-PRD-004", "L9-T-095", lambda: "repo://demo@abc" in manager.bind_repository("product_demo","repo://demo@abc")["repository_bindings"], lambda: _bad(manager))
def _bad(manager):
    try: manager.bind_repository("product_demo","")
    except ValueError: return False
    return True
