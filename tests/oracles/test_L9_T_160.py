"""L9-REQ-DPT-005 / L9-T-160: Department handoff graph rejects cycles unless explicit bounded iterative contract exists."""
from hyai.departments.charter import HandoffGraphValidator, CircularHandoffError
from ._support import oracle


def test_l9_t_160_handoff_graph_rejects_cycles():
    def _pos():
        edges = [
            ("department_product", "department_engineering"),
            ("department_engineering", "department_assurance"),
            ("department_assurance", "department_operations"),
        ]
        HandoffGraphValidator.validate_acyclic(edges)
        return True

    def _neg():
        edges = [
            ("department_product", "department_engineering"),
            ("department_engineering", "department_product"),
        ]
        try:
            HandoffGraphValidator.validate_acyclic(edges)
            return True
        except CircularHandoffError:
            return False

    oracle("L9-REQ-DPT-005", "L9-T-160", _pos, _neg)
