"""Resolve the active project directory from ``WORKSPACE_ROOT`` plus project selection."""

from __future__ import annotations

import os
from pathlib import Path

from app.models.workspace import DEFAULT_WORKSPACE_LAYOUT, ResolvedProjectPaths, WorkspaceLayout


def repo_root() -> Path:
    """Repository root (parent of ``backend/``) when running from a checkout."""
    # backend/app/services/workspace.py -> parents[3] == repo root
    return Path(__file__).resolve().parents[3]


def resolve_active_project_root() -> Path:
    """Return the filesystem root of the active DocPatcher project.

    Computes ``WORKSPACE_ROOT / project_key``, where:

    - ``WORKSPACE_ROOT`` comes from env, else ``<repository>/workspace``.
    - ``project_key`` comes from ``PROJECT_NAME`` env, else the first line of
      ``WORKSPACE_ROOT/.current_project``, else ``example_project``.
    ``project_key`` may contain slashes for nested folders (e.g. ``project1/example_project``).
    """
    ws_env = os.getenv("WORKSPACE_ROOT", "").strip()
    workspace_root = (
        Path(ws_env).expanduser().resolve()
        if ws_env
        else (repo_root() / "workspace").resolve()
    )

    proj = os.getenv("PROJECT_NAME", "").strip()
    if not proj:
        marker = workspace_root / ".current_project"
        if marker.is_file():
            lines = [
                ln.strip()
                for ln in marker.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            if lines:
                proj = lines[0]
    if not proj:
        proj = "example_project"

    return (workspace_root / proj).resolve()


def resolve_active_project(
    subdirs: WorkspaceLayout | None = None,
) -> ResolvedProjectPaths:
    """Resolved paths for the active project (root + standard subdirectories)."""
    return ResolvedProjectPaths(
        root=resolve_active_project_root(),
        subdirs=subdirs or DEFAULT_WORKSPACE_LAYOUT,
    )
