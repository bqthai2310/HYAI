"""Oracle test for L9-REQ-CMP-006 / L9-T-193."""
from hyai._contracts import sha256_digest
from hyai.skills.abi import EntrypointKind, create_component_abi_manifest
from ._support import oracle

def _good() -> bool:
    digest = sha256_digest(b"component_wasm_binary_payload")
    manifest = create_component_abi_manifest(
        abi_manifest_id="abi_component_wasm_01",
        component_id="comp_text_tokenizer",
        component_version="2.0.1",
        entrypoint_kind=EntrypointKind.WASM_COMPONENT,
        exported_capabilities=["cap_tokenize"],
        compatibility_ref="compat_standard_wasm_v1",
        artifact_digest=digest,
    )
    return manifest.entrypoint_kind == "WASM_COMPONENT" and manifest.exported_capabilities == ("cap_tokenize",)

def _bad() -> bool:
    return False

def test_l9_t_193():
    oracle("L9-REQ-CMP-006", "L9-T-193", _good, _bad)
