"""Oracle test for L9-REQ-DPT-006 / L9-T-161."""
from hyai.capabilities.worker import DynamicDepartmentWorkerPool, create_worker_descriptor
from ._support import oracle

def _good() -> bool:
    pool = DynamicDepartmentWorkerPool(department_id="dept_engineering")
    w1 = create_worker_descriptor(
        worker_id="worker_agent_alpha",
        node_id="node_01",
        capabilities=["cap_compile", "cap_test"],
    )
    w2 = create_worker_descriptor(
        worker_id="worker_agent_beta",
        node_id="node_02",
        capabilities=["cap_compile"],
    )
    pool.register_worker(w1)
    pool.register_worker(w2)
    # Department dynamically allocates without fixed binding to worker alpha
    alloc = pool.allocate_worker_for_task("cap_compile", exclude_worker_ids=[w1.worker_id])
    return alloc.worker_id == "worker_agent_beta"

def _bad() -> bool:
    return False

def test_l9_t_161():
    oracle("L9-REQ-DPT-006", "L9-T-161", _good, _bad)
