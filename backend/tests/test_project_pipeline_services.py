import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.settings import Settings
from app.models.project_pipeline import InitContextManifest
from app.models.workspace import ResolvedProjectPaths
from app.services.llm.artifact_sources import (
    DEFAULT_PROJECT_EXECUTE_INSTRUCTION_FILE,
    DEFAULT_PROJECT_INIT_INSTRUCTION_FILE,
    DEFAULT_PROJECT_PLAN_INSTRUCTION_FILE,
    load_project_execute_instruction,
    load_project_init_instruction,
    load_project_plan_instruction,
)
from app.services.project_execute import run_project_execute
from app.services.project_init import load_init_context_manifest, run_project_init
from app.services.project_plan import run_project_plan


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        openai_api_key="sk-test",
        model_name="gpt-test",
        project_paths=ResolvedProjectPaths(root=tmp_path),
    )


def test_run_project_init_writes_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _make_settings(tmp_path)
    seen: dict[str, object] = {}
    intermediate = tmp_path / "intermediate"
    intermediate.mkdir(parents=True)
    (intermediate / "doc_a_overview.md").write_text("# A overview\nDetails", encoding="utf-8")

    monkeypatch.setattr(
        "app.services.project_init.run_extract_overview_all_input_docs",
        lambda **kwargs: seen.update(kwargs)
        or {
            "documents": [
                {
                    "doc_id": "doc_a",
                    "input_file": str(tmp_path / "input_docs" / "a.docx"),
                    "extraction_json_path": str(tmp_path / "intermediate" / "doc_a_extraction.json"),
                    "overview_path": str(tmp_path / "intermediate" / "doc_a_overview.md"),
                    "content_sheet_csv_path": str(tmp_path / "intermediate" / "doc_a_content_sheet.csv"),
                    "rows": 3,
                }
            ]
        },
    )
    out = run_project_init(settings=settings)
    assert out.count == 1
    assert seen["task_instruction_filename"] == DEFAULT_PROJECT_INIT_INSTRUCTION_FILE
    assert Path(out.project_overview_path).is_file()
    merged = Path(out.project_overview_path).read_text(encoding="utf-8")
    assert "Project Overview" in merged
    assert "doc_a" in merged
    manifest = load_init_context_manifest(settings)
    assert isinstance(manifest, InitContextManifest)
    assert manifest.documents[0].doc_id == "doc_a"


def test_stage_instruction_default_filenames_are_fixed() -> None:
    assert DEFAULT_PROJECT_INIT_INSTRUCTION_FILE == "init.txt"
    assert DEFAULT_PROJECT_PLAN_INSTRUCTION_FILE == "plan.txt"
    assert DEFAULT_PROJECT_EXECUTE_INSTRUCTION_FILE == "execute.txt"


def test_stage_instruction_fallback_templates_when_missing(tmp_path: Path) -> None:
    project_root = tmp_path
    (project_root / "instructions").mkdir(parents=True)
    assert load_project_init_instruction(project_root)
    assert load_project_plan_instruction(project_root)
    assert load_project_execute_instruction(project_root)


def test_run_project_plan_needs_clarification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _make_settings(tmp_path)
    intermediate = tmp_path / "intermediate"
    intermediate.mkdir(parents=True)
    extraction = {
        "overview_markdown": "# Doc",
        "content_sheet_rows": [{"block_id": "D-B0000", "paragraph_index": 0, "verbatim_text": "x", "topic_or_heading": "y"}],
    }
    (intermediate / "doc_a_extraction.json").write_text(json.dumps(extraction), encoding="utf-8")
    manifest = {
        "project_root": str(tmp_path),
        "documents": [
            {
                "doc_id": "doc_a",
                "input_file": str(tmp_path / "input_docs" / "a.docx"),
                "extraction_json_path": str(intermediate / "doc_a_extraction.json"),
                "overview_path": str(intermediate / "doc_a_overview.md"),
                "content_sheet_csv_path": str(intermediate / "doc_a_content_sheet.csv"),
            }
        ],
    }
    (intermediate / "init_context_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    fake_resp = MagicMock()
    fake_resp.output_text = json.dumps(
        {
            "needs_clarification": True,
            "questions": ["What tone should be used?"],
            "project_understanding": "The project updates consent language.",
            "numbered_changes_md": "1. Draft rewrite.",
        }
    )
    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_resp
    monkeypatch.setattr("app.services.project_plan.OpenAI", lambda api_key: fake_client)

    out = run_project_plan(settings=settings, user_instruction="Improve wording")
    assert out.status == "needs_clarification"
    assert out.questions
    assert out.plan_path is None


def test_run_project_execute_writes_patched_doc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from docx import Document

    settings = _make_settings(tmp_path)
    input_docs = tmp_path / "input_docs"
    intermediate = tmp_path / "intermediate"
    reports = tmp_path / "reports"
    input_docs.mkdir(parents=True)
    intermediate.mkdir(parents=True)
    reports.mkdir(parents=True)

    src = input_docs / "a.docx"
    d = Document()
    d.add_paragraph("Original paragraph")
    d.save(src)

    (reports / "plan.md").write_text("# Plan\n1. Rewrite paragraph.", encoding="utf-8")
    extraction = {"overview_markdown": "# A", "content_sheet_rows": []}
    (intermediate / "doc_a_extraction.json").write_text(json.dumps(extraction), encoding="utf-8")
    manifest = {
        "project_root": str(tmp_path),
        "documents": [
            {
                "doc_id": "doc_a",
                "input_file": str(src),
                "extraction_json_path": str(intermediate / "doc_a_extraction.json"),
                "overview_path": str(intermediate / "doc_a_overview.md"),
                "content_sheet_csv_path": str(intermediate / "doc_a_content_sheet.csv"),
            }
        ],
    }
    (intermediate / "init_context_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    fake_resp = MagicMock()
    fake_resp.output_text = json.dumps(
        {"edits": [{"block_id": "doc_a-B0000", "revised_text": "Updated paragraph"}]}
    )
    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_resp
    monkeypatch.setattr("app.services.project_execute.OpenAI", lambda api_key: fake_client)

    out = run_project_execute(settings=settings)
    assert out.count == 1
    patched = Path(out.documents[0].output_doc)
    assert patched.name == "a_patched.docx"
    assert patched.is_file()
