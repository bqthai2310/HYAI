"""Workspace isolation guard for product source and generated output."""
from __future__ import annotations

from pathlib import Path
from typing import Union


class WorkspaceError(ValueError):
    pass


class ProductWorkspaceManager:
    def __init__(self, repository_root: str | Path | None = None) -> None:
        self.repository_root = Path(repository_root) if repository_root else Path(__file__).resolve().parents[3]

    def ensure_workspace_isolation(self, product_ref: str, path: str | Path, *, external_repo: bool = False) -> Path:
        if not isinstance(product_ref, str) or not product_ref.startswith("product_"):
            raise WorkspaceError("a canonical product identity is required")
        candidate = Path(path).resolve()
        root = self.repository_root.resolve()
        if external_repo:
            if candidate == root or root in candidate.parents:
                raise WorkspaceError("an explicit external repository must be outside the HYAI root")
            return candidate
        workspace_root = (root / "workspaces" / product_ref).resolve()
        if candidate != workspace_root and workspace_root not in candidate.parents:
            raise WorkspaceError("product source/output must be under its managed workspaces/<product> directory or an explicit external repo")
        return candidate
