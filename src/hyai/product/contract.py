"""Canonical Product and ProductContract lifecycle records."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
from uuid import uuid4

from hyai._contracts import content_digest, timestamp, validate


class ProductError(ValueError):
    pass


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def _as_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(value))


class ProductContractManager:
    """Owns versioned product contracts and their product binding."""

    def __init__(self) -> None:
        self._contracts: dict[str, dict[str, Any]] = {}
        self._product_contracts: dict[str, str] = {}

    def create_product_contract(self, spec: Mapping[str, Any] | None = None, **fields: Any) -> dict[str, Any]:
        document = _as_dict(spec or {})
        document.update(fields)
        document.setdefault("schema_version", "2.1.0")
        document.setdefault("product_contract_id", _id("productcontract"))
        document.setdefault("revision", 1)
        document.setdefault("lifecycle_state", "BASELINED")
        document["content_digest"] = content_digest(document)
        validate(document, "product_contract.schema.json", ProductError)
        existing = self._contracts.get(document["product_contract_id"])
        if existing is not None and existing != document:
            raise ProductError("product contract identifiers are immutable")
        self._contracts[document["product_contract_id"]] = _as_dict(document)
        return _as_dict(document)

    def get_contract(self, contract_ref: str) -> dict[str, Any]:
        try:
            return _as_dict(self._contracts[contract_ref])
        except KeyError as error:
            raise ProductError(f"unknown product contract: {contract_ref}") from error

    def bind_to_product(self, product_ref: str, contract: str | Mapping[str, Any]) -> dict[str, Any]:
        document = self.get_contract(contract) if isinstance(contract, str) else _as_dict(contract)
        validate(document, "product_contract.schema.json", ProductError)
        if document["product_ref"] != product_ref:
            raise ProductError("contract product_ref does not match the product being bound")
        if document["lifecycle_state"] not in {"BASELINED", "ACTIVE"}:
            raise ProductError("only a baselined or active ProductContract can be bound")
        self._contracts[document["product_contract_id"]] = _as_dict(document)
        self._product_contracts[product_ref] = document["product_contract_id"]
        return _as_dict(document)

    def contract_for_product(self, product_ref: str) -> dict[str, Any]:
        try:
            return self.get_contract(self._product_contracts[product_ref])
        except KeyError as error:
            raise ProductError(f"no canonical ProductContract is bound to {product_ref}") from error

    def supersede_contract(self, contract_ref: str, replacement: Mapping[str, Any] | None = None, **changes: Any) -> dict[str, Any]:
        prior = self.get_contract(contract_ref)
        if prior["lifecycle_state"] == "SUPERSEDED":
            raise ProductError("a superseded ProductContract cannot be superseded again")
        candidate = _as_dict(prior)
        candidate.update(_as_dict(replacement or {}))
        candidate.update(changes)
        candidate.update({
            "product_contract_id": _id("productcontract"),
            "revision": prior["revision"] + 1,
            "supersedes_ref": prior["product_contract_id"],
            "lifecycle_state": "BASELINED",
        })
        candidate.pop("content_digest", None)
        successor = self.create_product_contract(candidate)
        prior["lifecycle_state"] = "SUPERSEDED"
        prior["content_digest"] = content_digest(prior)
        self._contracts[contract_ref] = prior
        self.bind_to_product(successor["product_ref"], successor)
        return successor


class ProductManager:
    """Creates ProductSpec records and preserves component/release/retirement lineage."""

    def __init__(self) -> None:
        self._products: dict[str, dict[str, Any]] = {}
        self._components: dict[str, dict[str, Any]] = {}
        self._releases: dict[str, dict[str, Any]] = {}
        self._retirements: dict[str, dict[str, Any]] = {}
        self._retirements: dict[str, dict[str, Any]] = {}

    def create_product(self, spec: Mapping[str, Any] | None = None, **fields: Any) -> dict[str, Any]:
        document = _as_dict(spec or {})
        document.update(fields)
        document.setdefault("schema_version", "2.1.0")
        document.setdefault("product_id", _id("product"))
        document.setdefault("lifecycle_state", "DEFINED")
        document.setdefault("component_refs", [])
        document.setdefault("repository_bindings", [])
        document.setdefault("environment_refs", [])
        document.setdefault("acceptance_baseline_refs", [])
        document.setdefault("created_at", timestamp())
        document["content_digest"] = content_digest(document)
        validate(document, "product_spec.schema.json", ProductError)
        if document["product_id"] in self._products:
            raise ProductError("product identifiers are immutable")
        self._products[document["product_id"]] = _as_dict(document)
        return _as_dict(document)

    def get_product(self, product_ref: str) -> dict[str, Any]:
        try:
            return _as_dict(self._products[product_ref])
        except KeyError as error:
            raise ProductError(f"unknown product: {product_ref}") from error

    def _update_product(self, product: Mapping[str, Any]) -> dict[str, Any]:
        document = _as_dict(product)
        document["content_digest"] = content_digest(document)
        validate(document, "product_spec.schema.json", ProductError)
        self._products[document["product_id"]] = document
        return _as_dict(document)

    def bind_repository(self, product_ref: str, repository_ref: str) -> dict[str, Any]:
        if not isinstance(repository_ref, str) or not repository_ref:
            raise ProductError("repository binding requires a non-empty identity/provenance reference")
        product = self.get_product(product_ref)
        if repository_ref not in product["repository_bindings"]:
            product["repository_bindings"].append(repository_ref)
        return self._update_product(product)

    def register_component(self, product_ref: str, component: Mapping[str, Any] | None = None, **fields: Any) -> dict[str, Any]:
        if product_ref not in self._products:
            raise ProductError(f"unknown product: {product_ref}")
        document = _as_dict(component or {})
        document.update(fields)
        document.setdefault("schema_version", "2.1.0")
        document.setdefault("component_id", _id("component"))
        document["product_id"] = product_ref
        document["content_digest"] = content_digest(document)
        validate(document, "product_component.schema.json", ProductError)
        if document["component_id"] in self._components:
            raise ProductError("component identifiers are immutable")
        self._components[document["component_id"]] = _as_dict(document)
        product = self.get_product(product_ref)
        product["component_refs"].append(document["component_id"])
        self._update_product(product)
        return _as_dict(document)

    def record_release(self, product_ref: str, release: Mapping[str, Any] | None = None, **fields: Any) -> dict[str, Any]:
        if product_ref not in self._products:
            raise ProductError(f"unknown product: {product_ref}")
        document = _as_dict(release or {})
        document.update(fields)
        document.setdefault("schema_version", "2.1.0")
        document.setdefault("release_id", _id("release"))
        document["product_id"] = product_ref
        document.setdefault("created_at", timestamp())
        validate(document, "release_record.schema.json", ProductError)
        if document["release_id"] in self._releases:
            raise ProductError("release identifiers are immutable")
        self._releases[document["release_id"]] = _as_dict(document)
        return _as_dict(document)

    def retire_product(self, product_ref: str, decision_ref: str, evidence_refs: list[str], data_retention_ref: str) -> dict[str, Any]:
        if not decision_ref or not evidence_refs or not data_retention_ref:
            raise ProductError("retirement requires decision, evidence, and data-retention lineage")
        product = self.get_product(product_ref)
        product["lifecycle_state"] = "RETIRED"
        product["retirement"] = {"decision_ref": decision_ref, "evidence_refs": list(evidence_refs), "data_retention_ref": data_retention_ref}
        # ProductSpec has a closed vocabulary, so retention lineage is returned as a
        # companion record rather than inserted into its schema-governed body.
        schema_product = {key: value for key, value in product.items() if key != "retirement"}
        updated = self._update_product(schema_product)
        self._retirements[product_ref] = _as_dict(product["retirement"])
        updated["retirement"] = product["retirement"]
        self._retirements[product_ref] = _as_dict(product["retirement"])
        return updated

    def get_retirement_lineage(self, product_ref: str) -> dict[str, Any]:
        """Return the required retirement provenance without violating ProductSpec."""
        try:
            return _as_dict(self._retirements[product_ref])
        except KeyError as error:
            raise ProductError(f"product has no retirement lineage: {product_ref}") from error

    def get_retirement(self, product_ref: str) -> dict[str, Any]:
        """Return the immutable retirement decision/evidence/retention lineage."""
        try:
            return _as_dict(self._retirements[product_ref])
        except KeyError as error:
            raise ProductError(f"no retirement lineage exists for {product_ref}") from error

    def check_task_does_not_accept_product(self, task: Mapping[str, Any], product: Mapping[str, Any] | str) -> bool:
        candidate = self.get_product(product) if isinstance(product, str) else dict(product)
        task_marks_operating = task.get("product_lifecycle_state", task.get("product_state")) == "OPERATING"
        if task.get("state") in {"PASS", "COMPLETE", "COMPLETED"} and (candidate.get("lifecycle_state") == "OPERATING" or task_marks_operating):
            raise ProductError("task completion cannot set a Product to OPERATING")
        return True
