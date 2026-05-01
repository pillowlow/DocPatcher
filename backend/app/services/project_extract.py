"""Run document extract / overview pipeline for the configured workspace project."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.settings import Settings
from app.services.artifacts import write_json
from app.services.document_extraction import extract_overview_and_content_sheet
from app.services.docx_parser import parse_docx_to_blocks


def list_input_docx_files(project_paths) -> list[Path]:
    """Sorted ``*.docx`` under the project's ``input_docs/``."""
    directory = project_paths.input_docs_dir
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.docx"), key=lambda p: p.name.casefold())


def stable_doc_id_from_filename(doc_path: Path, fallback_index: int) -> str:
    """Prefer the file stem as ``doc_id``; sanitized and bounded."""
    stem = doc_path.stem.strip()
    if not stem:
        return f"DOC{fallback_index:04d}"
    safe = re.sub(r"[^\w\-]+", "_", stem).strip("_")
    return safe[:200] if safe else f"DOC{fallback_index:04d}"


def allocate_unique_doc_ids(paths: list[Path]) -> list[str]:
    """One stable id per path; avoids duplicates when filenames collide."""
    seen: set[str] = set()
    out: list[str] = []
    for idx, path in enumerate(paths, start=1):
        base = stable_doc_id_from_filename(path, idx)
        candidate = base
        suffix = 1
        while candidate in seen:
            candidate = f"{base}_{suffix}"
            suffix += 1
        seen.add(candidate)
        out.append(candidate)
    return out


def run_extract_overview(
    *,
    input_doc_path: Path,
    doc_id: str,
    settings: Settings,
) -> dict[str, str | int]:
    """Parse ``input_doc_path``, call the model, write overview + sheet + JSON under ``intermediate/``.

    Same behaviour as ``POST /parse/extract-overview`` for one file.
    Writes ``blocks.json`` (overwrite) for compatibility with downstream steps.
    """
    if not settings.openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is required for extract / overview.")
    path = input_doc_path if input_doc_path.is_absolute() else input_doc_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input document not found: {path}")

    blocks = parse_docx_to_blocks(path, doc_id=doc_id)
    parsed_result = extract_overview_and_content_sheet(
        blocks=blocks,
        settings=settings,
        project_paths=settings.project_paths,
        doc_id=doc_id,
    )
    blocks_path = settings.project_paths.intermediate_dir / "blocks.json"
    write_json(blocks_path, [block.model_dump() for block in blocks])
    return {
        **parsed_result,
        "blocks": len(blocks),
        "blocks_path": str(blocks_path),
        "input_file": str(path),
        "doc_id": doc_id,
    }


def run_extract_overview_all_input_docs(*, settings: Settings) -> dict[str, Any]:
    """Process every ``*.docx`` in ``input_docs/`` (sorted). Last file determines ``blocks.json``."""

    if not settings.openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is required for extract / overview.")

    paths = list_input_docx_files(settings.project_paths)
    if not paths:
        raise ValueError(
            "No .docx files found in input_docs/. Add documents or pass a concrete input path."
        )

    ids = allocate_unique_doc_ids(paths)
    documents: list[dict[str, str | int]] = []
    for doc_path, doc_id in zip(paths, ids, strict=True):
        documents.append(
            run_extract_overview(
                input_doc_path=doc_path,
                doc_id=doc_id,
                settings=settings,
            )
        )

    return {
        "documents": documents,
        "count": len(documents),
        "input_docs_dir": str(settings.project_paths.input_docs_dir.resolve()),
    }
