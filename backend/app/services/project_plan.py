"""Plan stage for Cursor-like project pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.settings import Settings
from app.models.project_pipeline import PlanProjectResponse
from app.services.llm.artifact_sources import (
    load_agent_system_prompt,
    load_project_plan_instruction,
)
from app.services.llm.responses_model_params import responses_api_supports_temperature
from app.services.project_init import load_init_context_manifest


class _PlanModelOutput(BaseModel):
    needs_clarification: bool
    questions: list[str] = Field(default_factory=list)
    project_understanding: str
    numbered_changes_md: str


_PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "needs_clarification": {"type": "boolean"},
        "questions": {"type": "array", "items": {"type": "string"}},
        "project_understanding": {"type": "string"},
        "numbered_changes_md": {"type": "string"},
    },
    "required": [
        "needs_clarification",
        "questions",
        "project_understanding",
        "numbered_changes_md",
    ],
    "additionalProperties": False,
}


def _build_plan_user_input(
    *,
    plan_instruction: str,
    user_instruction: str,
    qa_answers: list[str],
    context_blocks: list[str],
) -> str:
    answers = "\n".join(f"- {a}" for a in qa_answers) if qa_answers else "- (none)"
    context_joined = "\n\n".join(context_blocks) if context_blocks else "(no context loaded)"
    return (
        "## Plan instruction\n"
        f"{plan_instruction.strip()}\n\n"
        "## User instruction\n"
        f"{user_instruction.strip()}\n\n"
        "## Clarification answers from user (if any)\n"
        f"{answers}\n\n"
        "## Picked project context\n"
        f"{context_joined}\n"
    )


def _load_context_blocks(settings: Settings, selected_doc_ids: list[str] | None) -> list[str]:
    manifest = load_init_context_manifest(settings)
    selected = manifest.selected_docs(selected_doc_ids)
    if not selected:
        raise ValueError("No documents selected from init context.")
    blocks: list[str] = []
    for item in selected:
        extraction_path = Path(item.extraction_json_path)
        if not extraction_path.is_file():
            continue
        payload = json.loads(extraction_path.read_text(encoding="utf-8"))
        overview = str(payload.get("overview_markdown", "")).strip()
        rows = payload.get("content_sheet_rows", [])
        row_preview = rows[:20] if isinstance(rows, list) else []
        blocks.append(
            "\n".join(
                [
                    f"### Document {item.doc_id}",
                    f"- input_file: {item.input_file}",
                    f"- extraction_json_path: {item.extraction_json_path}",
                    "#### Overview",
                    overview or "(empty)",
                    "#### Content rows preview",
                    json.dumps(row_preview, ensure_ascii=False),
                ]
            )
        )
    return blocks


def run_project_plan(
    *,
    settings: Settings,
    user_instruction: str,
    selected_doc_ids: list[str] | None = None,
    qa_answers: list[str] | None = None,
) -> PlanProjectResponse:
    if not settings.openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is required for /project/plan.")

    system_prompt = load_agent_system_prompt(settings.project_paths.root)
    plan_instruction = load_project_plan_instruction(settings.project_paths.root)
    context_blocks = _load_context_blocks(settings, selected_doc_ids)
    user_input = _build_plan_user_input(
        plan_instruction=plan_instruction,
        user_instruction=user_instruction,
        qa_answers=qa_answers or [],
        context_blocks=context_blocks,
    )

    client = OpenAI(api_key=settings.openai_api_key)
    kwargs: dict = {
        "model": settings.model_name,
        "instructions": system_prompt,
        "input": user_input,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "project_plan",
                "schema": _PLAN_SCHEMA,
                "strict": True,
            }
        },
    }
    if responses_api_supports_temperature(settings.model_name):
        kwargs["temperature"] = settings.llm_temperature
    resp = client.responses.create(**kwargs)
    raw = (resp.output_text or "").strip()
    if not raw:
        raise ValueError("Plan model returned empty output.")
    parsed = _PlanModelOutput.model_validate(json.loads(raw))

    if parsed.needs_clarification:
        return PlanProjectResponse(
            status="needs_clarification",
            project_understanding=parsed.project_understanding,
            numbered_changes_md=parsed.numbered_changes_md,
            questions=parsed.questions,
            plan_path=None,
        )

    reports_dir = settings.project_paths.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    plan_path = settings.project_paths.plan_report_path
    plan_md = (
        "# Plan\n\n"
        "## Project Understanding\n"
        f"{parsed.project_understanding.strip()}\n\n"
        "## Planned Changes\n"
        f"{parsed.numbered_changes_md.strip()}\n\n"
        "## Questions\n"
        + ("\n".join(f"- {q}" for q in parsed.questions) if parsed.questions else "- None\n")
    )
    plan_path.write_text(plan_md, encoding="utf-8")
    return PlanProjectResponse(
        status="planned",
        project_understanding=parsed.project_understanding,
        numbered_changes_md=parsed.numbered_changes_md,
        questions=parsed.questions,
        plan_path=str(plan_path),
    )
