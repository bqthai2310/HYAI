"""Oracle test for L9-REQ-CMP-007 / L9-T-194."""
from hyai.interoperability.adapter import InteropError, VendorExitContract
from ._support import oracle

def _good() -> bool:
    contract = VendorExitContract(
        dependency_id="dep_vector_pinecone",
        vendor_name="Pinecone",
        exit_migration_path="export_parquet_to_self_hosted_qdrant",
        export_format="PARQUET_COMPRESSED_V2",
        alternative_vendor="Qdrant",
        is_tested=True,
    )
    contract.validate()
    # Contract missing exit path must be rejected
    invalid_contract = VendorExitContract(
        dependency_id="dep_locked_in",
        vendor_name="LockInCorp",
        exit_migration_path="",
        export_format="",
        alternative_vendor="",
    )
    try:
        invalid_contract.validate()
        return False
    except InteropError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_194():
    oracle("L9-REQ-CMP-007", "L9-T-194", _good, _bad)
