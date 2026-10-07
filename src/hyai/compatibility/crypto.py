"""Algorithm-agile digest support for canonical contracts."""
from __future__ import annotations

import hashlib
from typing import ClassVar


class CryptoRegistry:
    """The explicitly supported digest/signature algorithm registry."""

    supported_algorithms: ClassVar[frozenset[str]] = frozenset({"sha256", "sha384", "sha512"})

    @classmethod
    def supports(cls, algorithm: str) -> bool:
        return algorithm.lower() in cls.supported_algorithms


def compute_digest(data: bytes, algorithm: str = "sha256") -> dict[str, str]:
    algorithm = algorithm.lower()
    if not CryptoRegistry.supports(algorithm):
        raise ValueError(f"unsupported digest algorithm: {algorithm}")
    return {"algorithm": algorithm, "encoding": "hex", "value": hashlib.new(algorithm, data).hexdigest()}


def validate_digest_spec(digest_dict: dict) -> bool:
    """Validate the canonical three-field digest representation only."""
    if not isinstance(digest_dict, dict) or set(digest_dict) != {"algorithm", "encoding", "value"}:
        return False
    algorithm, encoding, value = digest_dict["algorithm"], digest_dict["encoding"], digest_dict["value"]
    if not isinstance(algorithm, str) or not CryptoRegistry.supports(algorithm):
        return False
    if encoding != "hex" or not isinstance(value, str):
        return False
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return False
    return len(raw) == hashlib.new(algorithm).digest_size
