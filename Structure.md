# DocPatcher Architecture Memory

## Purpose
This file tracks architecture and pipeline structure. Keep end-user usage details in `README.md`.

## Project Root Resolution
- Active project root is resolved as `WORKSPACE_ROOT / PROJECT_NAME`.
- If env values are missing, resolution falls back to `workspace/.current_project` and then `example_project`.
- Path model lives in `backend/app/models/workspace.py`.
- Resolver lives in `backend/app/services/workspace.py`.

## Pipeline Overview
The primary workflow is now three explicit stages:

1. `POST /project/init`
2. `POST /project/plan`
3. `POST /project/execute`

Route implementation: `backend/app/api/routers/project_pipeline.py`.

## Stage Responsibilities

### 1) Init Stage
- Service: `backend/app/services/project_init.py`
- Calls extraction (`project_extract` + `document_extraction`) once.
- Purpose: extraction/overview context build only (no planning or editing actions).
- Writes per-document extraction artifacts in `intermediate/`.
- Writes a reusable manifest: `intermediate/init_context_manifest.json`.
- Writes a project-level summary markdown: `intermediate/project_overview.md`.

### 2) Plan Stage
- Service: `backend/app/services/project_plan.py`
- Uses:
  - global system prompt from `prompts/agent_system.md` (or fallback),
  - plan instruction from `instructions/plan.txt` (or fallback),
  - selected context from init manifest/extraction outputs.
- Returns either:
  - `needs_clarification` + questions, or
  - `planned` + persisted `reports/plan.md`.

### 3) Execute Stage
- Service: `backend/app/services/project_execute.py`
- Uses:
  - global system prompt,
  - execute instruction from `instructions/execute.txt` (or fallback),
  - approved plan markdown (`reports/plan.md` by default),
  - selected context and target document blocks.
- LLM returns block-level edits.
- Writes patched documents to `output_docs/` as `<original>_patched.docx`.

## Prompt Artifacts
Loader: `backend/app/services/llm/artifact_sources.py`.

Expected files under each project:
- `prompts/agent_system.md`
- `instructions/init.txt`
- `instructions/plan.txt`
- `instructions/execute.txt`

If stage-specific files are missing, builtin fallback text is used.

## Deprecated Flow
- `POST /parse/extract-overview` has been removed from default workflow.
- Keep `POST /parse` for low-level parsing utility only.

## Notes for Future Changes
- Preserve stage boundaries (`init` context cache, `plan` intent generation, `execute` concrete edits).
- Keep `plan.md` as approval checkpoint before execute.
- Avoid hidden side effects in plan stage; doc writes should happen in execute stage.
