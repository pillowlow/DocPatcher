"""Core document extraction engine used by the init pipeline."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.core.settings import Settings
from app.services.artifacts import write_json
from app.services.document_extraction import extract_overview_and_content_sheet
from app.services.docx_parser import (
    analyze_docx_xml_parts,
    parse_docx_to_blocks_and_structure,
)
from app.services.extract_progress import (
    ExtractProgressEvent,
    ExtractProgressKind,
    ProgressCallback,
    emit_batch_begin,
    emit_batch_done,
)


def _notify(on_progress: ProgressCallback | None, event: ExtractProgressEvent) -> None:
    if on_progress:
        on_progress(event)


def _require_openai_api_key(settings: Settings) -> None:
    if not settings.openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is required for extract / overview.")


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
    on_progress: ProgressCallback | None = None,
    batch_doc_index: int = 1,
    batch_doc_total: int = 1,
    task_instruction_filename: str | None = None,
) -> dict[str, str | int]:
    """Parse one document, run model extraction, and write per-doc artifacts."""
    _require_openai_api_key(settings)
    path = input_doc_path if input_doc_path.is_absolute() else input_doc_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input document not found: {path}")

    i, n = batch_doc_index, batch_doc_total
    _notify(
        on_progress,
        ExtractProgressEvent(
            ExtractProgressKind.DOC_BEGIN,
            i,
            n,
            path=path,
            doc_id=doc_id,
        ),
    )
    xml_stats = analyze_docx_xml_parts(path)
    _notify(
        on_progress,
        ExtractProgressEvent(
            ExtractProgressKind.XML_SCAN_START,
            i,
            n,
            path=path,
            doc_id=doc_id,
            xml_parts_total=xml_stats.xml_parts_total,
            xml_parts_compressed_bytes=xml_stats.xml_parts_compressed_bytes,
        ),
    )
    xml_done = 0

    def _on_xml_part_done(_: str) -> None:
        nonlocal xml_done
        xml_done += 1
        _notify(
            on_progress,
            ExtractProgressEvent(
                ExtractProgressKind.XML_PART_DONE,
                i,
                n,
                path=path,
                doc_id=doc_id,
                xml_parts_total=xml_stats.xml_parts_total,
                xml_parts_done=xml_done,
            ),
        )

    blocks, structure = parse_docx_to_blocks_and_structure(
        path,
        doc_id=doc_id,
        on_xml_part_done=_on_xml_part_done,
    )
    if xml_done < xml_stats.xml_parts_total:
        for _ in range(xml_done, xml_stats.xml_parts_total):
            _on_xml_part_done("unparsed")
    _notify(
        on_progress,
        ExtractProgressEvent(
            ExtractProgressKind.PARSE_DONE,
            i,
            n,
            path=path,
            doc_id=doc_id,
            block_count=len(blocks),
        ),
    )
    _notify(
        on_progress,
        ExtractProgressEvent(
            ExtractProgressKind.LLM_START,
            i,
            n,
            path=path,
            doc_id=doc_id,
            block_count=len(blocks),
        ),
    )
    parsed_result = extract_overview_and_content_sheet(
        blocks=blocks,
        settings=settings,
        project_paths=settings.project_paths,
        doc_id=doc_id,
        task_instruction_filename=task_instruction_filename,
    )
    _notify(
        on_progress,
        ExtractProgressEvent(
            ExtractProgressKind.LLM_DONE,
            i,
            n,
            path=path,
            doc_id=doc_id,
            row_count=int(parsed_result["rows"]),
        ),
    )

    # Per-doc blocks artifact avoids thread races in batch mode.
    blocks_path = settings.project_paths.intermediate_dir / f"{doc_id}_blocks.json"
    write_json(blocks_path, [block.model_dump() for block in blocks])
    structure_path = settings.project_paths.intermediate_dir / f"{doc_id}_structure.json"
    write_json(structure_path, structure.model_dump())
    _notify(
        on_progress,
        ExtractProgressEvent(
            ExtractProgressKind.DOC_DONE,
            i,
            n,
            path=path,
            doc_id=doc_id,
            row_count=int(parsed_result["rows"]),
        ),
    )
    return {
        **parsed_result,
        "blocks": len(blocks),
        "blocks_path": str(blocks_path),
        "structure_path": str(structure_path),
        "input_file": str(path),
        "doc_id": doc_id,
    }


def run_extract_overview_all_input_docs(
    *,
    settings: Settings,
    on_progress: ProgressCallback | None = None,
    task_instruction_filename: str | None = None,
) -> dict[str, Any]:
    """Process every ``*.docx`` in ``input_docs/`` (sorted)."""
    _require_openai_api_key(settings)

    paths = list_input_docx_files(settings.project_paths)
    if not paths:
        raise ValueError(
            "No .docx files found in input_docs/. Add documents or pass a concrete input path."
        )

    emit_batch_begin(on_progress, len(paths))
    ids = allocate_unique_doc_ids(paths)
    documents: list[dict[str, str | int]] = []
    indexed_jobs = list(enumerate(zip(paths, ids, strict=True), start=1))
    max_workers = min(4, len(indexed_jobs))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                run_extract_overview,
                input_doc_path=doc_path,
                doc_id=doc_id,
                settings=settings,
                on_progress=on_progress,
                batch_doc_index=idx,
                batch_doc_total=len(paths),
                task_instruction_filename=task_instruction_filename,
            ): idx
            for idx, (doc_path, doc_id) in indexed_jobs
        }
        results_by_idx: dict[int, dict[str, str | int]] = {}
        for future in as_completed(future_map):
            idx = future_map[future]
            results_by_idx[idx] = future.result()
        for idx in sorted(results_by_idx):
            documents.append(results_by_idx[idx])

    emit_batch_done(on_progress, len(paths))
    return {
        "documents": documents,
        "count": len(documents),
        "input_docs_dir": str(settings.project_paths.input_docs_dir.resolve()),
    }
