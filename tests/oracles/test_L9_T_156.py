"""L9-REQ-DPT-001 / L9-T-156: Every active department has versioned charter defining responsibility/authority/capability/forbidden actions."""
from hyai.departments.charter import create_department_charter, DepartmentError
from ._support import oracle


def test_l9_t_156_department_charter_definition():
    def _pos():
        c = create_department_charter(
            department_id="department_assurance",
            version="1.0.0",
            mission="Provide independent assurance and review gates",
            authority=("independent_review", "block_release"),
            required_capabilities=("audit", "verification"),
            forbidden_actions=("author_and_approve", "direct_db_write"),
        )
        return (
            c.department_id.startswith("department_")
            and len(c.authority) > 0
            and "author_and_approve" in c.forbidden_actions
        )

    def _neg():
        try:
            create_department_charter(
                department_id="bad_name",
                version="1.0.0",
                mission="",
            )
            return True
        except DepartmentError:
            return False

    oracle("L9-REQ-DPT-001", "L9-T-156", _pos, _neg)
