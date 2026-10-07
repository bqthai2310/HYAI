"""Canonical Interoperability and Protocol boundary."""
from hyai.interoperability.adapter import (
    AdapterLifecycleState,
    ExternalDirectWriteForbiddenError,
    InteropError,
    InteropGateway,
    LossyTranslationError,
    ProtocolAdapterDescriptor,
    SilentProtocolDowngradeError,
    VendorExitContract,
    create_protocol_adapter_descriptor,
    validate_protocol_adapter_descriptor_document,
)

__all__ = [
    "AdapterLifecycleState",
    "ExternalDirectWriteForbiddenError",
    "InteropError",
    "InteropGateway",
    "LossyTranslationError",
    "ProtocolAdapterDescriptor",
    "SilentProtocolDowngradeError",
    "VendorExitContract",
    "create_protocol_adapter_descriptor",
    "validate_protocol_adapter_descriptor_document",
]
