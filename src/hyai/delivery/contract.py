"""Versioned DeliveryContracts and release-readiness decisions."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence
from uuid import uuid4

from hyai._contracts import content_digest, timestamp, validate


class DeliveryError(ValueError):
    """Raised when delivery lineage or readiness requirements are incomplete."""


def _copy(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DeliveryError("delivery records must be JSON objects")
    return deepcopy(dict(value))


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


class DeliveryContractManager:
    """Own immutable DeliveryContract revisions bound to a ProductContract."""

    def __init__(self, product_contract_manager: Any | None = None) -> None:
        self._product_contract_manager = product_contract_manager
        self._contracts: dict[str, dict[str, Any]] = {}
        self._current_by_product: dict[str, str] = {}
        self._superseded: set[str] = set()

    def _resolve_product_contract(self, document: dict[str, Any], product_contract: str | Mapping[str, Any] | None) -> None:
        source: Mapping[str, Any] | None = None
        if product_contract is not None:
            if isinstance(product_contract, str):
                if self._product_contract_manager is None:
                    raise DeliveryError("a ProductContract manager is required to resolve product_contract_ref")
                source = self._product_contract_manager.get_contract(product_contract)
            else:
                source = product_contract
        elif self._product_contract_manager is not None:
            source = self._product_contract_manager.contract_for_product(document["product_ref"])
        if source is None:
            # A caller without a ProductContractManager may submit the already-bound
            # identity/digest tuple.  It is still validated by DeliveryContract schema.
            return
        contract = _copy(source)
        if contract.get("product_ref") != document.get("product_ref"):
            raise DeliveryError("DeliveryContract product_ref does not match its ProductContract")
        if contract.get("lifecycle_state") not in {"BASELINED", "ACTIVE"}:
            raise DeliveryError("DeliveryContract requires a baselined ProductContract")
        fields = {
            "product_contract_ref": contract.get("product_contract_id"),
            "product_contract_revision": contract.get("revision"),
            "product_contract_digest": contract.get("content_digest"),
        }
        for name, value in fields.items():
            supplied = document.get(name)
            if supplied is not None and supplied != value:
                raise DeliveryError(f"DeliveryContract {name} is not bound to the supplied ProductContract")
            document[name] = deepcopy(value)

    def create_delivery_contract(
        self, spec: Mapping[str, Any] | None = None, *,
        product_contract: str | Mapping[str, Any] | None = None, **fields: Any,
    ) -> dict[str, Any]:
        document = _copy(spec or {})
        document.update(fields)
        document.setdefault("schema_version", "2.1.0")
        document.setdefault("delivery_contract_id", _id("deliverycontract"))
        document.setdefault("revision", 1)
        if not document.get("product_ref"):
            raise DeliveryError("DeliveryContract requires product_ref")
        self._resolve_product_contract(document, product_contract)
        document["content_digest"] = content_digest(document)
        validate(document, "delivery_contract.schema.json", DeliveryError)
        existing = self._contracts.get(document["delivery_contract_id"])
        if existing is not None and existing != document:
            raise DeliveryError("DeliveryContract identifiers are immutable")
        current = self._current_by_product.get(document["product_ref"])
        if current is not None and current != document["delivery_contract_id"]:
            raise DeliveryError("supersede the existing DeliveryContract instead of creating a competing baseline")
        self._contracts[document["delivery_contract_id"]] = _copy(document)
        self._current_by_product[document["product_ref"]] = document["delivery_contract_id"]
        return _copy(document)

    def get_delivery_contract(self, contract_ref: str) -> dict[str, Any]:
        try:
            return _copy(self._contracts[contract_ref])
        except KeyError as error:
            raise DeliveryError(f"unknown DeliveryContract: {contract_ref}") from error

    def _assert_product_contract_binding(self, contract: Mapping[str, Any]) -> None:
        """Ensure a registered contract still targets the current product contract."""
        if self._product_contract_manager is None:
            return
        try:
            product_contract = self._product_contract_manager.contract_for_product(contract["product_ref"])
        except ValueError as error:
            raise DeliveryError("DeliveryContract has no baselined ProductContract binding") from error
        expected = {
            "product_contract_ref": product_contract["product_contract_id"],
            "product_contract_revision": product_contract["revision"],
            "product_contract_digest": product_contract["content_digest"],
        }
        if any(contract.get(name) != value for name, value in expected.items()):
            raise DeliveryError("DeliveryContract is not bound to the current baselined ProductContract")

    def baselined_contract_for_product(self, product_ref: str) -> dict[str, Any]:
        try:
            contract = self.get_delivery_contract(self._current_by_product[product_ref])
        except KeyError as error:
            raise DeliveryError(f"no baselined DeliveryContract is bound to {product_ref}") from error
        self._assert_product_contract_binding(contract)
        return contract

    def supersede_contract(
        self, contract_ref: str, replacement: Mapping[str, Any] | None = None, **changes: Any,
    ) -> dict[str, Any]:
        prior = self.get_delivery_contract(contract_ref)
        if contract_ref in self._superseded or self._current_by_product.get(prior["product_ref"]) != contract_ref:
            raise DeliveryError("only the current DeliveryContract may be superseded")
        candidate = _copy(prior)
        candidate.update(_copy(replacement or {}))
        candidate.update(changes)
        candidate.pop("content_digest", None)
        candidate["delivery_contract_id"] = _id("deliverycontract")
        candidate["revision"] = prior["revision"] + 1
        if candidate.get("product_ref") != prior["product_ref"]:
            raise DeliveryError("a superseding DeliveryContract must remain bound to the same product")
        # The successor must bind to the ProductContract currently bound to the
        # product.  Remove the predecessor tuple so resolution can populate the
        # current ID, revision, and digest (including after ProductContract
        # supersession).
        if self._product_contract_manager is not None:
            for field in ("product_contract_ref", "product_contract_revision", "product_contract_digest"):
                candidate.pop(field, None)
        self._current_by_product.pop(prior["product_ref"], None)
        try:
            successor = self.create_delivery_contract(candidate)
        except Exception:
            self._current_by_product[prior["product_ref"]] = contract_ref
            raise
        self._superseded.add(contract_ref)
        return successor


class DeliveryReadinessManager:
    """Issue readiness records only against a current, baselined DeliveryContract."""

    def __init__(self, contracts: DeliveryContractManager) -> None:
        self._contracts = contracts
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _required_criteria(contract: Mapping[str, Any]) -> set[str]:
        fields = (
            "required_acceptance_refs", "required_security_gates", "required_operational_gates",
            "required_recovery_gates", "required_bundle_items",
        )
        return {item for field in fields for item in contract[field]}

    def evaluate_readiness(
        self, product_ref: str, release_subject_digest: Mapping[str, Any],
        criterion_results: Sequence[Mapping[str, Any]], *, delivery_contract_ref: str | None = None,
        independent_review_ref: str | None = None, issued_by: Mapping[str, Any] | None = None,
        readiness_id: str | None = None, issued_at: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate all required delivery gates for a material product release."""
        contract = self._contracts.baselined_contract_for_product(product_ref)
        if delivery_contract_ref is not None and delivery_contract_ref != contract["delivery_contract_id"]:
            raise DeliveryError("readiness must use the current baselined DeliveryContract")
        results = [_copy(item) for item in criterion_results]
        required = self._required_criteria(contract)
        present = [item.get("criterion_id") for item in results]
        if len(present) != len(set(present)):
            raise DeliveryError("readiness criteria must not be duplicated")
        missing = required - set(present)
        if missing:
            raise DeliveryError(f"readiness evaluation is missing required criteria: {sorted(missing)}")
        all_pass = bool(results) and all(item.get("result") == "PASS" for item in results)
        review_ref = independent_review_ref or "pending://independent-review"
        if all_pass and independent_review_ref:
            state = "DELIVERY_READY"
        elif any(item.get("result") == "BLOCKED" for item in results):
            state = "BLOCKED"
        elif any(item.get("result") == "FAIL" for item in results):
            state = "CORRECTION_REQUIRED"
        else:
            state = "NOT_READY"
        document = {
            "schema_version": "2.1.0", "readiness_id": readiness_id or _id("deliveryready"),
            "product_ref": product_ref, "delivery_contract_ref": contract["delivery_contract_id"],
            "delivery_contract_revision": contract["revision"], "delivery_contract_digest": contract["content_digest"],
            "release_subject_digest": _copy(release_subject_digest), "state": state,
            "criterion_results": results, "independent_review_ref": review_ref,
            "issued_at": issued_at or timestamp(),
            "issued_by": _copy(issued_by or {"principal_type": "SYSTEM", "id": "delivery-readiness"}),
        }
        validate(document, "delivery_readiness_record.schema.json", DeliveryError)
        self._records[document["readiness_id"]] = _copy(document)
        return _copy(document)

    def get_readiness(self, readiness_id: str) -> dict[str, Any]:
        try:
            return _copy(self._records[readiness_id])
        except KeyError as error:
            raise DeliveryError(f"unknown DeliveryReadinessRecord: {readiness_id}") from error
