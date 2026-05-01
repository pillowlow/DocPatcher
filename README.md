# DocPatcher POC

Backend-first POC for controlled document revision with human-in-the-loop approvals.

## Setup

1. Install [uv](https://docs.astral.sh/uv/) if you do not already have it.
2. Install dependencies from `backend/pyproject.toml` (creates `backend/.venv`):
   - `cd backend`
   - `uv sync --all-groups`
3. Configure environment variables:
   - copy `backend/.env.example` to `backend/.env`
   - set `OPENAI_API_KEY` only for real LLM usage
   - default `LLM_PROVIDER=mock` works without API calls

## Run API

- `cd backend`
- `uv run uvicorn app.main:app --reload`

## Pipeline Endpoints

- `POST /parse` with `input_doc_path` and `doc_id`
- `POST /parse/extract-overview` with the same body (requires `OPENAI_API_KEY`) — loads system hints from `ARTIFACT_ROOT/prompts/full_document_extraction.txt`, then writes `{doc_id}_overview.md`, `{doc_id}_content_sheet.csv`, and `{doc_id}_extraction.json` under `ARTIFACT_ROOT/intermediate` (parse also saves `blocks.json`). Set `ARTIFACT_ROOT` so it points at your repo `example_project` folder (e.g. `../example_project` when running uvicorn from `backend/`).
- `POST /retrieve` with `requirement_text`
- `POST /propose` with `requirement_text`
- `GET /change-table`
- `PATCH /change-table/{change_id}` with `{ "status": "approved" | "rejected" }`
- `POST /apply` with `source_doc_path`, `output_doc_name`, `dry_run`
- `POST /report` with `run_id`

## Safety

- Original DOCX files are never overwritten.
- Only approved rows are applied.
- Dry-run mode is available for patch verification.

## Tests

From `backend`:

- `uv run pytest -q`
