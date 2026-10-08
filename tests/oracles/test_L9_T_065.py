"""L9-REQ-ORG-001 / L9-T-065: Organization domains are capabilities/authority, not forced agents."""
from hyai.departments.charter import create_department_charter, DepartmentError
from ._support import oracle


def test_l9_t_065_domains_are_capabilities_authority():
    def _pos():
        charter = create_department_charter(
            department_id="department_engineering",
            mission="Deliver high-quality software artifacts",
            authority=("code_execution", "artifact_authoring"),
            required_capabilities=("python_programming", "testing"),
        )
        return len(charter.authority) > 0 and len(charter.required_capabilities) > 0

    def _neg():
        try:
            create_department_charter(
                department_id="invalid_dept",
                mission="",
                authority=(),
            )
            return True
        except DepartmentError:
            return False

    oracle("L9-REQ-ORG-001", "L9-T-065", _pos, _neg)
