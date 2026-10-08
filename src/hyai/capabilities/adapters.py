"""Adapter abstractions for models, tools, and external providers (L9-REQ-CAP-004)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Mapping

from hyai.capabilities.spec import CapabilityError
from hyai.ports.base import ProviderPort


class ProviderKind(str, Enum):
    ANTHROPIC = "ANTHROPIC"
    OPENAI = "OPENAI"
    GOOGLE = "GOOGLE"
    LOCAL = "LOCAL"
    OTHER = "OTHER"


class AdapterError(CapabilityError):
    """Base error for adapter access boundary violations."""


class DirectAccessForbiddenError(AdapterError):
    """Direct unmediated model or provider invocation is strictly forbidden."""


class ModelAdapter(ProviderPort):
    """Model adapter wrapping an LLM provider via explicit ProviderPort."""

    def __init__(
        self,
        model_id: str,
        handler: Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
        supported_capabilities: tuple[str, ...] = (),
    ) -> None:
        self.model_id = model_id
        self._handler = handler
        self.supported_capabilities = supported_capabilities

    def invoke(self, capability: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.supported_capabilities and capability not in self.supported_capabilities:
            raise AdapterError(f"Capability '{capability}' not supported by model adapter {self.model_id}")
        return self._handler(capability, dict(request))


class ToolAdapter:
    """Explicit adapter boundary for tool execution."""

    def __init__(
        self,
        tool_id: str,
        executor: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        required_permissions: tuple[str, ...] = (),
    ) -> None:
        self.tool_id = tool_id
        self._executor = executor
        self.required_permissions = required_permissions

    def execute(self, params: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._executor(dict(params))


class ProviderAdapter(ProviderPort):
    """Generic provider adapter mediating capability execution."""

    def __init__(
        self,
        provider_id: str,
        target_port: ProviderPort,
    ) -> None:
        self.provider_id = provider_id
        self._target_port = target_port

    def invoke(self, capability: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(self._target_port, ProviderPort):
            raise DirectAccessForbiddenError("Providers must implement ProviderPort abstraction")
        return self._target_port.invoke(capability, request)


def verify_adapter_access(provider: Any) -> bool:
    """Verify that model or provider access complies with adapter boundary port requirements."""
    return isinstance(provider, ProviderPort)


class DependencyReplacementDrill:
    """L9-REQ-CMP-008: F15 demonstrates representative dependency replacement without loss of canonical truth."""

    @staticmethod
    def execute_drill(
        primary_adapter: Any,
        substitute_adapter: Any,
        sample_workload: Any,
    ) -> bool:
        r1 = primary_adapter(sample_workload)
        r2 = substitute_adapter(sample_workload)
        return r1 == r2
