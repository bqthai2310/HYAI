"""L9-REQ-DPT-007 / L9-T-162: Independent Assurance department cannot independently approve exact subject it authored."""
from hyai.departments.charter import IndependenceEnforcer, SelfAuditingForbiddenError
from ._support import oracle


def test_l9_t_162_independent_assurance_cannot_self_audit():
    def _pos():
        IndependenceEnforcer.assert_independent_approval(
            author_dept="department_engineering",
            approver_dept="department_assurance",
            subject_ref="release_candidate_bundle",
        )
        return True

    def _neg():
        try:
            IndependenceEnforcer.assert_independent_approval(
                author_dept="assurance",
                approver_dept="assurance",
                subject_ref="assurance_report_bundle",
            )
            return True
        except SelfAuditingForbiddenError:
            return False

    oracle("L9-REQ-DPT-007", "L9-T-162", _pos, _neg)
