"""Oracle test for L9-REQ-OBS-003 / L9-T-078."""
from hyai.observability.finops import CostRecord, UnallocatedCostError
from ._support import oracle

def _good() -> bool:
    rec = CostRecord(
        cost_id="cost_eval_99",
        goal_id="goal_model_eval",
        task_id="task_benchmark_10",
        resource_ref="res_gpu_h100_node_3",
        amount=14.50,
        currency="USD",
    )
    assert rec.amount == 14.50
    # Cost record lacking explicit mapping must be rejected
    try:
        CostRecord(
            cost_id="cost_unmapped",
            goal_id="",
            task_id="task_1",
            resource_ref="res_cpu",
            amount=1.0,
        )
        return False
    except UnallocatedCostError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_078():
    oracle("L9-REQ-OBS-003", "L9-T-078", _good, _bad)
