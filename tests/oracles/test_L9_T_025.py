from hyai.constitution.authority import Principal
from hyai.kernel import CommandEnvelope
from ._support import oracle

def _command(key="key"):
    return CommandEnvelope("cmd", "Update", "thing", 0, Principal("EXECUTOR", "worker"), "auth", "policy", key, "corr", {"x": 1}, "change")

def test_l9_t_025_command_envelope():
    def invalid():
        try:
            CommandEnvelope("", "Update", "thing", -1, Principal("EXECUTOR", "worker"), "auth", "policy", "key", "corr", {}, "change").validate()
        except ValueError:
            return False
        return True
    oracle("L9-REQ-KRN-002", "L9-T-025", lambda: _command().validate(), invalid)
