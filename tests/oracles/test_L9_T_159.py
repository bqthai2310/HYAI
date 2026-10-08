"""L9-REQ-DPT-004 / L9-T-159: Cross-department work uses HandoffContract with exact subject/acceptance/risk."""
from hyai.departments.charter import create_handoff_contract, DepartmentError
from ._support import oracle


def test_l9_t_159_cross_department_handoff_contract():
    def _pos():
        c = create_handoff_contract(
            handoff_id="handoff_design_to_eng",
            source_department="department_architecture",
            destination_department="department_engineering",
            subject_refs=("sha256:hex:arch_spec_v1",),
            input_contract="architecture_spec_v1",
            output_acceptance_refs=("acceptance_baseline_arch",),
            unresolved_risks=("latency_under_load",),
        )
        return (
            c.handoff_id.startswith("handoff_")
            and len(c.subject_refs) > 0
            and len(c.output_acceptance_refs) > 0
            and len(c.unresolved_risks) == 1
        )

    def _neg():
        try:
            create_handoff_contract(
                handoff_id="invalid_handoff_id",
                source_department="department_architecture",
                destination_department="department_engineering",
                subject_refs=(),
                input_contract="spec",
                output_acceptance_refs=(),
            )
            return True
        except DepartmentError:
            return False

    oracle("L9-REQ-DPT-004", "L9-T-159", _pos, _neg)
