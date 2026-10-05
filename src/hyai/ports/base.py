"""Ports owned by the domain; adapters implement these boundaries only."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class StoragePort(ABC):
    """Canonical state is addressed through this port, never adapter globals."""
    @abstractmethod
    def get(self, key: str) -> Mapping[str, Any] | None: ...
    @abstractmethod
    def put(self, key: str, value: Mapping[str, Any], *, expected_version: str | None = None) -> str: ...


class ProviderPort(ABC):
    @abstractmethod
    def invoke(self, capability: str, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


class ReviewPort(ABC):
    @abstractmethod
    def submit(self, review: Mapping[str, Any]) -> Mapping[str, Any]: ...
    @abstractmethod
    def verdict(self, review_request_id: str) -> Mapping[str, Any] | None: ...
