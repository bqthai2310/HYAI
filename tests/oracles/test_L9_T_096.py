from hyai.product import ProductManager
from ._f03_support import product
from ._support import oracle
def test_l9_t_096():
    manager=ProductManager(); manager.create_product(product())
    oracle("L9-REQ-PRD-005", "L9-T-096", lambda: manager.register_component("product_demo",name="api",component_type="service",owner_boundary="team")["product_id"] == "product_demo", lambda: _bad(manager))
def _bad(manager):
    try: manager.register_component("product_demo",name="api",component_type="service")
    except ValueError: return False
    return True
