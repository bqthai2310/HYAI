"""L9-REQ-SCA-002 / L9-T-210: Material release has dependency/software/AI/data BOM metadata."""
from hyai.supply_chain import verify_bom_metadata, IncompleteBOMError
from ._support import oracle


def test_l9_t_210_bom_metadata():
    def _pos():
        return verify_bom_metadata(
            has_software_bom=True,
            has_dependency_bom=True,
            ai_model_deps_present=True,
            has_ai_model_bom=True,
        )

    def _neg():
        try:
            verify_bom_metadata(
                has_software_bom=True,
                has_dependency_bom=False,
                ai_model_deps_present=True,
                has_ai_model_bom=False,
            )
            return True
        except IncompleteBOMError:
            return False

    oracle("L9-REQ-SCA-002", "L9-T-210", _pos, _neg)
