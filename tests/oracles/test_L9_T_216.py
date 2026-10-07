from hyai.organization import OrganizationRouter
from hyai.product import ProductContractManager
from ._f03_support import contract
from ._support import oracle
def test_l9_t_216():
    manager=ProductContractManager(); value=manager.create_product_contract(contract()); manager.bind_to_product("product_demo",value)
    oracle("L9-REQ-PRD-009", "L9-T-216", lambda: OrganizationRouter().route_product("product_demo",contract_manager=manager)["product_contract_ref"] == "productcontract_demo", lambda: _bad())
def _bad():
    try: OrganizationRouter().route_product("product_demo", contract())
    except ValueError: return False
    return True
