"""L9-REQ-CMP-008 / L9-T-195: Technology exit drill demonstrates representative dependency replacement."""
from hyai.capabilities.adapters import DependencyReplacementDrill
from ._support import oracle


def test_l9_t_195_technology_exit_drill():
    def _pos():
        primary = lambda x: f"OUTPUT_{x}"
        substitute = lambda x: f"OUTPUT_{x}"
        return DependencyReplacementDrill.execute_drill(primary, substitute, "PAYLOAD_42")

    def _neg():
        primary = lambda x: f"OUTPUT_{x}"
        substitute = lambda x: f"DIFFERENT_{x}"
        return DependencyReplacementDrill.execute_drill(primary, substitute, "PAYLOAD_42")

    oracle("L9-REQ-CMP-008", "L9-T-195", _pos, _neg)
