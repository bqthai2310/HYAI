"""L9-REQ-DLV-008 / L9-T-171: Material delivery is represented by complete ProductDeliveryBundle bound exact release subject."""
from hyai.delivery.bundle import create_product_delivery_bundle
from ._support import oracle


def test_l9_t_171_product_delivery_bundle():
    def _pos():
        bundle = create_product_delivery_bundle(
            product_ref="product_f14",
            release_subject_digest={"algorithm": "sha256", "encoding": "hex", "value": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"},
            artifact_refs=["artifact_bin_v1"],
            config_refs=["config_prod_v1"],
            documentation_refs=["doc_runbook_v1"],
            evidence_refs=["evidence_test_run_v1"],
            delivery_readiness_ref="deliveryready_f14",
            rollback_ref="rollback_plan_v1",
        )
        return bundle["bundle_id"].startswith("deliverybundle_") and len(bundle["artifact_refs"]) > 0

    def _neg():
        try:
            create_product_delivery_bundle(
                product_ref="product_f14",
                release_subject_digest={"algorithm": "sha256", "encoding": "hex", "value": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"},
                artifact_refs=[],
                config_refs=["config_prod_v1"],
                documentation_refs=["doc_runbook_v1"],
                evidence_refs=["evidence_test_run_v1"],
                delivery_readiness_ref="deliveryready_f14",
                rollback_ref="rollback_plan_v1",
            )
            return True
        except ValueError:
            return False

    oracle("L9-REQ-DLV-008", "L9-T-171", _pos, _neg)
