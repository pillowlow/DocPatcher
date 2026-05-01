"""Execute stage for Cursor-like project pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.settings import Settings
from app.models.project_pipeline import ExecuteDocResult, ExecuteProjectResponse
from app.services.docx_parser import parse_docx_to_blocks
from app.services.llm.artifact_sources import (
    load_agent_system_prompt,
    load_project_execute_instruction,
)
from app.services.llm.responses_model_params import responses_api_supports_temperature
from app.services.project_init import load_init_context_manifest


class _DocEdit(BaseModel):
    block_id: str
    revised_text: str


class _ExecuteModelOutput(BaseModel):
    edits: list[_DocEdit] = Field(default_factory=list)


_EXECUTE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "edits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string"},
                    "revised_text": {"type": "string"},
                },
                "required": ["block_id", "revised_text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["edits"],
    "additionalProperties": False,
}


def _render_blocks_for_model(doc_id: str, source: Path, blocks: list) -> str:
    rendered = []
    for block in blocks:
        rendered.append(
            f"[{block.block_id}] paragraph_index={block.position.paragraph_index}\n"
            f"{block.text}\n"
        )
    return (
        f"### Target document\n"
        f"- doc_id: {doc_id}\n"
        f"- source_path: {source}\n"
        "### Current paragraph blocks\n"
        + "\n".join(rendered)
    )


def _call_execute_model(
    *,
    settings: Settings,
    system_prompt: str,
    execute_instruction: str,
    plan_markdown: str,
    context_text: str,
    target_doc_text: str,
) -> _ExecuteModelOutput:
    user_input = (
        "## Execute instruction\n"
        f"{execute_instruction.strip()}\n\n"
        "## Approved plan markdown\n"
        f"{plan_markdown.strip()}\n\n"
        "## Picked project context\n"
        f"{context_text.strip()}\n\n"
        "## Target document blocks\n"
        f"{target_doc_text.strip()}\n"
    )
    client = OpenAI(api_key=settings.openai_api_key)
    kwargs: dict = {
        "model": settings.model_name,
        "instructions": system_prompt,
        "input": user_input,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "project_execute",
                "schema": _EXECUTE_SCHEMA,
                "strict": True,
            }
        },
    }
    if responses_api_supports_temperature(settings.model_name):
        kwargs["temperature"] = settings.llm_temperature
    resp = client.responses.create(**kwargs)
    raw = (resp.output_text or "").strip()
    if not raw:
        raise ValueError("Execute model returned empty output.")
    return _ExecuteModelOutput.model_validate(json.loads(raw))


def _apply_block_edits(source_doc: Path, output_doc: Path, block_index_to_text: dict[int, str]) -> int:
    doc = Document(source_doc)
    applied = 0
    for idx, paragraph in enumerate(doc.paragraphs):
        if idx not in block_index_to_text:
            continue
        paragraph.text = block_index_to_text[idx]
        applied += 1
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_doc)
    return applied


def run_project_execute(
    *,
    settings: Settings,
    selected_doc_ids: list[str] | None = None,
    plan_path: str | None = None,
) -> ExecuteProjectResponse:
    if not settings.openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is required for /project/execute.")

    manifest = load_init_context_manifest(settings)
    selected = manifest.selected_docs(selected_doc_ids)
    if not selected:
        raise ValueError("No documents selected from init context.")

    resolved_plan = Path(plan_path) if plan_path else settings.project_paths.plan_report_path
    if not resolved_plan.is_file():
        raise FileNotFoundError(
            f"Plan file not found: {resolved_plan}. Run /project/plan until status=planned."
        )
    plan_markdown = resolved_plan.read_text(encoding="utf-8")

    system_prompt = load_agent_system_prompt(settings.project_paths.root)
    execute_instruction = load_project_execute_instruction(settings.project_paths.root)

    context_chunks: list[str] = []
    for doc in selected:
        payload = json.loads(Path(doc.extraction_json_path).read_text(encoding="utf-8"))
        context_chunks.append(
            f"doc_id={doc.doc_id}\noverview=\n{payload.get('overview_markdown', '')}\n"
        )
    context_text = "\n\n".join(context_chunks)

    results: list[ExecuteDocResult] = []
    for doc in selected:
        source_path = Path(doc.input_file)
        blocks = parse_docx_to_blocks(source_path, doc_id=doc.doc_id)
        target_doc_text = _render_blocks_for_model(doc.doc_id, source_path, blocks)
        model_out = _call_execute_model(
            settings=settings,
            system_prompt=system_prompt,
            execute_instruction=execute_instruction,
            plan_markdown=plan_markdown,
            context_text=context_text,
            target_doc_text=target_doc_text,
        )

        by_block_id = {b.block_id: b for b in blocks}
        block_index_to_text: dict[int, str] = {}
        for edit in model_out.edits:
            block = by_block_id.get(edit.block_id)
            if not block:
                continue
            block_index_to_text[block.position.paragraph_index] = edit.revised_text

        output_name = f"{source_path.stem}_patched{source_path.suffix}"
        output_path = settings.project_paths.output_docs_dir / output_name
        applied = _apply_block_edits(source_path, output_path, block_index_to_text)
        results.append(
            ExecuteDocResult(
                doc_id=doc.doc_id,
                source_doc=str(source_path),
                output_doc=str(output_path),
                edits=applied,
            )
        )

    return ExecuteProjectResponse(count=len(results), documents=results)
