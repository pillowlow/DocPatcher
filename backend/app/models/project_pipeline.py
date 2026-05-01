from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


PlanStatus = Literal["needs_clarification", "planned"]


class InitProjectRequest(BaseModel):
    input_doc_path: str | None = Field(
        default=None,
        description="Optional single .docx path; omit to initialize from all input_docs/*.docx.",
    )


class InitProjectResponse(BaseModel):
    count: int
    input_docs_dir: str
    context_manifest_path: str
    documents: list[dict[str, str | int]]


class PlanProjectRequest(BaseModel):
    user_instruction: str
    selected_doc_ids: list[str] | None = None
    qa_answers: list[str] = Field(default_factory=list)


class PlanProjectResponse(BaseModel):
    status: PlanStatus
    project_understanding: str
    numbered_changes_md: str
    questions: list[str] = Field(default_factory=list)
    plan_path: str | None = None


class ExecuteProjectRequest(BaseModel):
    selected_doc_ids: list[str] | None = None
    plan_path: str | None = None


class ExecuteDocResult(BaseModel):
    doc_id: str
    source_doc: str
    output_doc: str
    edits: int


class ExecuteProjectResponse(BaseModel):
    count: int
    documents: list[ExecuteDocResult]


class InitContextDocument(BaseModel):
    doc_id: str
    input_file: str
    extraction_json_path: str
    overview_path: str
    content_sheet_csv_path: str


class InitContextManifest(BaseModel):
    project_root: str
    documents: list[InitContextDocument]

    def selected_docs(self, selected_doc_ids: list[str] | None) -> list[InitContextDocument]:
        if not selected_doc_ids:
            return self.documents
        wanted = set(selected_doc_ids)
        return [doc for doc in self.documents if doc.doc_id in wanted]

    @property
    def path_hint(self) -> Path:
        return Path(self.project_root) / "intermediate" / "init_context_manifest.json"
