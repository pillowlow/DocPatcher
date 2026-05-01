# DocPatcher

Backend service for controlled document revision with human-in-the-loop approvals.

## Workspace and projects

All file I/O runs under **one active project directory**:

**`WORKSPACE_ROOT` / `project_key`**

- **`WORKSPACE_ROOT`** — from env if set; otherwise the **`workspace`** directory at your repository root (parent of **`backend/`**).
- **`project_key`** — from **`PROJECT_NAME`** env if set; otherwise the first line of **`WORKSPACE_ROOT/.current_project`**; otherwise **`example_project`**. Slash-separated values are supported (nested folders).

Code: resolve **`backend/app/services/workspace.py`**. Subfolder naming and **`project_paths`** (``ResolvedProjectPaths``) live in **`backend/app/models/workspace.py`**. **`backend/app/core/settings.py`** attaches **`settings.project_paths`**.

Structure (repeat per project):

```text
workspace/
  .current_project
  project_key.../
    instructions/
    prompts/
    input_docs/
    intermediate/
    change_tables/
    reports/
    output_docs/
```

Set the default **`project_key`** (writes **`workspace/.current_project`**):

```bash
python scripts/set_current_project.py project_key...
```

Create a new project tree (empty scaffold):

```bash
python scripts/init_workspace_project.py nested/new_project
```

Set **`PROJECT_NAME`** in **`backend/.env`** when you do not rely on **``.current_project`**. Restart the API after changing env or **``.current_project`** (`get_settings()` is cached).

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
- `POST /parse/extract-overview` with the same body (requires `OPENAI_API_KEY`): loads from the active project (**agent** prompt `prompts/agent_system.md` as OpenAI **`instructions`**; task file `instructions/full_document_extraction.txt` plus parsed DOCX in **`input`**). Writes artefacts under the active project **`intermediate/`** subtree. Paths in JSON bodies must be valid from the server process cwd (typically run from **`backend/`**, e.g. **`../workspace/.../input_docs/file.docx`**).

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
