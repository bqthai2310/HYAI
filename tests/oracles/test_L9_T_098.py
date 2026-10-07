from hyai.product import ProductManager
from ._f03_support import product, task
from ._support import oracle
def test_l9_t_098():
    manager=ProductManager(); operating=product(); operating["lifecycle_state"]="OPERATING"
    oracle("L9-REQ-PRD-007", "L9-T-098", lambda: manager.check_task_does_not_accept_product(task(), operating), lambda: _bad(manager,operating))
def _bad(manager,operating):
    passed=task(); passed["state"]="PASS"
    try: manager.check_task_does_not_accept_product(passed,operating)
    except ValueError: return False
    return True
