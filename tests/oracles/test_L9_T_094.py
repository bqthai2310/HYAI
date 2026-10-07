from hyai.product import ProductManager
from ._f03_support import product
from ._support import oracle
def test_l9_t_094():
    oracle("L9-REQ-PRD-003", "L9-T-094", lambda: ProductManager().create_product(product())["owner"]["principal_type"] == "PO", lambda: _bad())
def _bad():
    value=product(); value.pop("owner")
    try: ProductManager().create_product(value)
    except ValueError: return False
    return True
