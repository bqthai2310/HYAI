"""L9-REQ-SCA-007 / L9-T-215: AI model/dataset dependencies carry provenance, version, license, and integrity."""
from hyai.supply_chain import verify_ai_model_provenance, IncompleteModelProvenanceError
from ._support import oracle


def test_l9_t_215_ai_model_provenance():
    def _pos():
        return verify_ai_model_provenance(
            model_id="model_foundation_v1",
            version="1.0.0",
            license_id="apache-2.0",
            integrity_digest="sha256:hex:1234567890abcdef",
            source_origin="https://huggingface.co/org/model_foundation_v1",
        )

    def _neg():
        try:
            verify_ai_model_provenance(
                model_id="unlicensed_anonymous_model",
                version="",
                license_id="",
                integrity_digest="",
                source_origin="",
            )
            return True
        except IncompleteModelProvenanceError:
            return False

    oracle("L9-REQ-SCA-007", "L9-T-215", _pos, _neg)
