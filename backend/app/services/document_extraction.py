import csv
import json
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.settings import Settings
from app.models.block import Block
from app.services.artifacts import write_json
from app.services.llm.example_project_sources import (
    load_agent_system_prompt,
    load_task_instruction,
)
from app.services.llm.openai_responses_composition import (
    compose_input_document_section,
    compose_openai_responses_user_input,
)

# JSON schema for Responses API structured output (minimal strict shape).
DOCUMENT_EXTRACTION_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "overview_markdown": {"type": "string"},
        "content_sheet_rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string"},
                    "paragraph_index": {"type": "integer"},
                    "verbatim_text": {"type": "string"},
                    "topic_or_heading": {"type": "string"},
                },
                "required": ["block_id", "paragraph_index", "verbatim_text", "topic_or_heading"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["overview_markdown", "content_sheet_rows"],
    "additionalProperties": False,
}


class ContentSheetRow(BaseModel):
    block_id: str
    paragraph_index: int
    verbatim_text: str = Field(description="Must match INPUT block text exactly.")
    topic_or_heading: str = ""


class DocumentExtractionResult(BaseModel):
    overview_markdown: str
    content_sheet_rows: list[ContentSheetRow]


def format_paragraph_block_listing(blocks: list[Block]) -> tuple[str, str]:
    """Turn parsed DOCX blocks into a stable multiline listing + source filename."""
    lines: list[str] = []
    source_file_name = blocks[0].file_name if blocks else ""
    for b in sorted(blocks, key=lambda x: x.position.paragraph_index):
        pid = b.position.paragraph_index
        lines.append(
            f"[{b.block_id}] paragraph_index={pid}\n<<<BLOCK>>>\n{b.text}\n<<<END BLOCK>>>\n"
        )
    return ("\n".join(lines), source_file_name)


def run_openai_document_extraction(
    client: OpenAI,
    *,
    agent_system_prompt: str,
    user_input: str,
    model_name: str,
    temperature: float,
) -> DocumentExtractionResult:
    """Call Responses API: ``instructions`` = agent system prompt; ``input`` = task + document."""
    resp = client.responses.create(
        model=model_name,
        instructions=agent_system_prompt,
        input=user_input,
        temperature=temperature,
        text={
            "format": {
                "type": "json_schema",
                "name": "document_extraction",
                "schema": DOCUMENT_EXTRACTION_JSON_SCHEMA,
                "strict": True,
            }
        },
    )
    raw = (resp.output_text or "").strip()
    if not raw:
        raise ValueError("OpenAI extraction returned empty output.")
    parsed = DocumentExtractionResult.model_validate(json.loads(raw))
    return parsed


def write_extraction_csv(path: Path, rows: list[ContentSheetRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["block_id", "paragraph_index", "topic_or_heading", "verbatim_text"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda x: x.paragraph_index):
            w.writerow(
                {
                    "block_id": r.block_id,
                    "paragraph_index": r.paragraph_index,
                    "topic_or_heading": r.topic_or_heading,
                    "verbatim_text": r.verbatim_text,
                }
            )


def write_overview_markdown(path: Path, markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.strip() + "\n", encoding="utf-8")


def extract_overview_and_content_sheet(
    *,
    blocks: list[Block],
    settings: Settings,
    artifact_root: Path,
    doc_id: str,
) -> dict[str, str | int]:
    if not blocks:
        raise ValueError("No paragraphs to extract; DOCX appears empty.")

    agent_system_prompt = load_agent_system_prompt(artifact_root)
    task_instruction = load_task_instruction(artifact_root)
    paragraph_listing, source_file_name = format_paragraph_block_listing(blocks)
    document_section = compose_input_document_section(
        doc_id=doc_id,
        source_file_name=source_file_name,
        paragraph_block_listing=paragraph_listing,
    )
    user_input = compose_openai_responses_user_input(
        task_instruction=task_instruction,
        document_section=document_section,
    )

    client = OpenAI(api_key=settings.openai_api_key)
    extraction = run_openai_document_extraction(
        client,
        agent_system_prompt=agent_system_prompt,
        user_input=user_input,
        model_name=settings.model_name,
        temperature=settings.llm_temperature,
    )

    intermediate = artifact_root / "intermediate"
    overview_path = intermediate / f"{doc_id}_overview.md"
    csv_path = intermediate / f"{doc_id}_content_sheet.csv"
    raw_json_path = intermediate / f"{doc_id}_extraction.json"

    write_overview_markdown(overview_path, extraction.overview_markdown)
    write_extraction_csv(csv_path, extraction.content_sheet_rows)
    write_json(
        raw_json_path,
        extraction.model_dump(),
    )

    return {
        "doc_id": doc_id,
        "overview_path": str(overview_path),
        "content_sheet_csv_path": str(csv_path),
        "extraction_json_path": str(raw_json_path),
        "rows": len(extraction.content_sheet_rows),
    }
