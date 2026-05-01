import pytest

from app.core.settings import Settings, get_settings
from app.services.workspace import repo_root, resolve_active_project_root


def test_repo_root_is_backend_parent() -> None:
    backend_dir = repo_root() / "backend"
    assert backend_dir.is_dir()
    assert (backend_dir / "app" / "core" / "settings.py").is_file()


def test_resolve_active_project_root_uses_workspace_root_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    ws = tmp_path / "ws"
    proj = ws / "only"
    proj.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("PROJECT_NAME", "only")
    get_settings.cache_clear()
    assert resolve_active_project_root() == proj.resolve()


def test_resolve_active_project_root_workspace_default_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    fake_repo = tmp_path / "repo"
    ws = fake_repo / "workspace"
    proj = ws / "alpha"
    proj.mkdir(parents=True)
    monkeypatch.setattr("app.services.workspace.repo_root", lambda: fake_repo)
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.setenv("PROJECT_NAME", "alpha")
    get_settings.cache_clear()
    assert resolve_active_project_root() == proj.resolve()


def test_resolve_active_project_root_nested_project_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    fake_repo = tmp_path / "repo"
    ws = fake_repo / "workspace"
    nested = ws / "project1" / "example_project"
    nested.mkdir(parents=True)
    monkeypatch.setattr("app.services.workspace.repo_root", lambda: fake_repo)
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.setenv("PROJECT_NAME", "project1/example_project")
    get_settings.cache_clear()
    assert resolve_active_project_root() == nested.resolve()


def test_resolve_active_project_root_reads_dot_current_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    fake_repo = tmp_path / "repo"
    ws = fake_repo / "workspace"
    proj = ws / "beta"
    proj.mkdir(parents=True)
    (ws / ".current_project").write_text("beta\n", encoding="utf-8")
    monkeypatch.setattr("app.services.workspace.repo_root", lambda: fake_repo)
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    get_settings.cache_clear()
    assert resolve_active_project_root() == proj.resolve()


def test_resolve_active_project_root_defaults_to_example_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    fake_repo = tmp_path / "repo"
    ws = fake_repo / "workspace"
    example = ws / "example_project"
    example.mkdir(parents=True)
    monkeypatch.setattr("app.services.workspace.repo_root", lambda: fake_repo)
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    get_settings.cache_clear()
    assert resolve_active_project_root() == example.resolve()


def test_settings_project_paths_matches_resolved_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    ws = tmp_path / "ws"
    proj = ws / "p"
    proj.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("PROJECT_NAME", "p")
    get_settings.cache_clear()
    s = Settings()
    expected = proj.resolve()
    assert s.project_paths.root == expected
    assert resolve_active_project_root() == expected
