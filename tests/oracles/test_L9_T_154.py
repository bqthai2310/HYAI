"""L9-REQ-EXE-007 / L9-T-154: Executive plane continuously checks work graph remains traceable to ProductContract."""
from hyai.executive.traceability import GoalProductAlignmentChecker, UntraceableWorkGraphError
from ._support import oracle


def test_l9_t_154_goal_product_alignment_traceability():
    def _pos():
        nodes = [
            {"node_id": "task_1", "product_contract_ref": "productcontract_f14", "goal_ref": "goal_po_autonomous"},
            {"node_id": "task_2", "product_contract_ref": "productcontract_f14", "goal_ref": "goal_po_autonomous"},
        ]
        return GoalProductAlignmentChecker.check_alignment(nodes, "productcontract_f14", "goal_po_autonomous")

    def _neg():
        nodes = [
            {"node_id": "task_1", "product_contract_ref": "productcontract_f14", "goal_ref": "goal_po_autonomous"},
            {"node_id": "task_orphan", "product_contract_ref": "other_contract", "goal_ref": "unknown_goal"},
        ]
        try:
            GoalProductAlignmentChecker.check_alignment(nodes, "productcontract_f14", "goal_po_autonomous")
            return True
        except UntraceableWorkGraphError:
            return False

    oracle("L9-REQ-EXE-007", "L9-T-154", _pos, _neg)
