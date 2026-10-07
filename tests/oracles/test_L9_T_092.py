from hyai.product import ProductManager
from ._f03_support import product
from ._support import oracle
def test_l9_t_092():
    oracle("L9-REQ-PRD-001", "L9-T-092", lambda: ProductManager().create_product(product())["goal_refs"] == ["goal_demo"], lambda: _bad())
def _bad():
    value=product(); value["goal_refs"]=[]
    try: ProductManager().create_product(value)
    except ValueError: return False
    return True
