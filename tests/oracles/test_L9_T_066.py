"""L9-REQ-ORG-002 / L9-T-066: Domain handoff via typed artifacts."""
from hyai.departments.charter import create_handoff_contract, DepartmentError
from ._support import oracle


def test_l9_t_066_domain_handoff_via_typed_artifacts():
    def _pos():
        contract = create_handoff_contract(
            handoff_id="handoff_eng_to_qa",
            source_department="department_engineering",
            destination_department="department_assurance",
            subject_refs=("sha256:hex:1234abcd",),
            input_contract="artifact_bundle_v1",
            output_acceptance_refs=("acceptance_baseline_1",),
        )
        return contract.input_contract == "artifact_bundle_v1" and len(contract.output_acceptance_refs) > 0

    def _neg():
        try:
            create_handoff_contract(
                handoff_id="bad_handoff",
                source_department="department_engineering",
                destination_department="department_assurance",
                subject_refs=(),
                input_contract="",
                output_acceptance_refs=(),
            )
            return True
        except DepartmentError:
            return False

    oracle("L9-REQ-ORG-002", "L9-T-066", _pos, _neg)
