"""L9-REQ-DLV-005 / L9-T-168: Delivery includes environment/config/deploy/start verification appropriate to Product."""
from hyai.delivery.bundle import verify_runnable_deployment, DeploymentVerificationError
from ._support import oracle


def test_l9_t_168_runnable_deployment_verification():
    def _pos():
        return verify_runnable_deployment(
            environment_verified=True,
            config_verified=True,
            deploy_verified=True,
            start_verified=True,
        )

    def _neg():
        try:
            verify_runnable_deployment(
                environment_verified=True,
                config_verified=True,
                deploy_verified=False,
                start_verified=False,
            )
            return True
        except DeploymentVerificationError:
            return False

    oracle("L9-REQ-DLV-005", "L9-T-168", _pos, _neg)
