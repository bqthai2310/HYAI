"""ProductContract-gated organization routing."""
from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from hyai._contracts import content_digest, validate
from hyai.product.contract import ProductContractManager, ProductError


class OrganizationRoutingError(ValueError):
    pass


class OrganizationRouter:
    """Activates only the departments needed by the contract, risk, and complexity."""

    _BASE = ["product", "engineering", "quality"]
    _RISK = {"HIGH": ["security", "assurance"], "CRITICAL": ["security", "assurance", "executive"]}

    def _canonical_contract(self, product_ref: str, contract: Mapping[str, Any] | str, manager: ProductContractManager | None) -> dict[str, Any]:
        if manager is None:
            # A stand-alone document can be schema-valid, but cannot prove it is
            # the current contract actually bound to this Product.
            raise OrganizationRoutingError("routing requires a canonical ProductContract manager binding")
        try:
            document = manager.contract_for_product(product_ref)
        except ProductError as error:
            raise OrganizationRoutingError(str(error)) from error
        if document.get("product_ref") != product_ref:
            raise OrganizationRoutingError("ProductContract is not bound to this Product")
        if contract and (contract if isinstance(contract, str) else contract.get("product_contract_id")) != document.get("product_contract_id"):
            raise OrganizationRoutingError("ProductContract is not the canonical product binding")
        if document.get("lifecycle_state") not in {"BASELINED", "ACTIVE"}:
            raise OrganizationRoutingError("routing requires a canonical valid ProductContract")
        if document.get("content_digest") != content_digest(document):
            raise OrganizationRoutingError("ProductContract content digest is invalid")
        try:
            validate(document, "product_contract.schema.json", OrganizationRoutingError)
        except ValueError as error:
            raise OrganizationRoutingError(str(error)) from error
        return document

    def route_product(
        self,
        product: Mapping[str, Any] | str,
        contract: Mapping[str, Any] | str | None = None,
        *,
        contract_manager: ProductContractManager | None = None,
        risk_class: str = "LOW",
        complexity: str | int = "LOW",
        version: int = 1,
    ) -> dict[str, Any]:
        product_ref = product if isinstance(product, str) else product.get("product_id")
        if not isinstance(product_ref, str) or not product_ref.startswith("product_"):
            raise OrganizationRoutingError("a canonical ProductSpec identity is required for routing")
        if contract is None and contract_manager is None:
            raise OrganizationRoutingError("routing requires a canonical valid ProductContract")
        contract_doc = self._canonical_contract(product_ref, contract or "", contract_manager)
        nodes = list(self._BASE)
        normalized_risk = risk_class.upper()
        nodes.extend(self._RISK.get(normalized_risk, []))
        complex_product = complexity in {"MEDIUM", "HIGH", "COMPLEX", "CRITICAL"} or (isinstance(complexity, int) and complexity > 1)
        if complex_product:
            nodes.append("architecture")
        if normalized_risk in {"HIGH", "CRITICAL"} or complex_product:
            nodes.append("operations")
        nodes = list(dict.fromkeys(nodes))
        handoffs = [
            {"from": nodes[index], "to": nodes[index + 1], "contract_ref": contract_doc["product_contract_id"]}
            for index in range(len(nodes) - 1)
        ]
        route = {
            "schema_version": "2.1.0",
            "route_id": f"orgroute_{uuid4().hex[:16]}",
            "product_ref": product_ref,
            "product_contract_digest": contract_doc["content_digest"],
            "product_contract_revision": contract_doc["revision"],
            "product_contract_ref": contract_doc["product_contract_id"],
            "mandate_ref": contract_doc["executive_mandate_ref"],
            "department_nodes": nodes,
            "handoff_edges": handoffs,
            "risk_class": normalized_risk,
            "version": version,
        }
        route["content_digest"] = content_digest(route)
        validate(route, "organization_route.schema.json", OrganizationRoutingError)
        return route
