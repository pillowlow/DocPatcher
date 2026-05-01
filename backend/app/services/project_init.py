"""Init stage for the project pipeline: parse/extract once and persist reusable context."""

from __future__ import annotations

from pathlib import Path

from app.core.settings import Settings
from app.models.project_pipeline import (
    InitContextDocument,
    InitContextManifest,
    InitProjectResponse,
)
from app.services.artifacts import write_json
from app.services.project_extract import (
    run_extract_overview,
    run_extract_overview_all_input_docs,
    stable_doc_id_from_filename,
)
from app.services.llm.artifact_sources import DEFAULT_PROJECT_INIT_INSTRUCTION_FILE


def _manifest_path(settings: Settings) -> Path:
    return settings.project_paths.intermediate_dir / "init_context_manifest.json"


def run_project_init(
    *,
    settings: Settings,
    input_doc_path: str | None = None,
) -> InitProjectResponse:
    if input_doc_path:
        path = Path(input_doc_path)
        doc_id = stable_doc_id_from_filename(path, 1)
        result = run_extract_overview(
            input_doc_path=path,
            doc_id=doc_id,
            settings=settings,
            task_instruction_filename=DEFAULT_PROJECT_INIT_INSTRUCTION_FILE,
        )
        raw_documents = [result]
    else:
        batch = run_extract_overview_all_input_docs(
            settings=settings,
            task_instruction_filename=DEFAULT_PROJECT_INIT_INSTRUCTION_FILE,
        )
        raw_documents = list(batch["documents"])

    documents = [
        InitContextDocument(
            doc_id=str(doc["doc_id"]),
            input_file=str(doc["input_file"]),
            extraction_json_path=str(doc["extraction_json_path"]),
            overview_path=str(doc["overview_path"]),
            content_sheet_csv_path=str(doc["content_sheet_csv_path"]),
        )
        for doc in raw_documents
    ]
    manifest = InitContextManifest(
        project_root=str(settings.project_paths.root),
        documents=documents,
    )
    manifest_path = _manifest_path(settings)
    write_json(manifest_path, manifest.model_dump())
    return InitProjectResponse(
        count=len(documents),
        input_docs_dir=str(settings.project_paths.input_docs_dir.resolve()),
        context_manifest_path=str(manifest_path),
        documents=raw_documents,
    )


def load_init_context_manifest(settings: Settings) -> InitContextManifest:
    path = _manifest_path(settings)
    if not path.is_file():
        raise FileNotFoundError(
            f"Init context manifest not found: {path}. Run POST /project/init first."
        )
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return InitContextManifest.model_validate(payload)
