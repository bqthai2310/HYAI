from hyai.organization import OrganizationRouter
from hyai.product import ProductContractManager
from ._f03_support import contract
from ._support import oracle
def test_l9_t_157():
    manager=ProductContractManager(); manager.bind_to_product("product_demo",manager.create_product_contract(contract()))
    oracle("L9-REQ-DPT-002", "L9-T-157", lambda: "security" not in OrganizationRouter().route_product("product_demo",contract_manager=manager,risk_class="LOW")["department_nodes"] and "security" in OrganizationRouter().route_product("product_demo",contract_manager=manager,risk_class="HIGH")["department_nodes"], lambda: False)
