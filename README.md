# DocPatcher

Backend service for controlled document revision with human-in-the-loop approvals.

## Backend setup with uv (first time)

Do this before running the API or scripts that import `app.*`.

1. **Install uv** (one-time on your machine): see [Installing uv](https://docs.astral.sh/uv/getting-started/installation/).

2. **Install Python dependencies** into `backend/.venv` and lockfile:
   ```bash
   cd backend
   uv sync --all-groups
   ```
   This reads `backend/pyproject.toml` and `backend/uv.lock`.

3. **Environment file** — from `backend/`:
   ```bash
   copy .env.example .env
   ```
   (On macOS/Linux: `cp .env.example .env`.)  
   Edit **`.env`**: set **`OPENAI_API_KEY`** for real LLM calls; set **`PROJECT_NAME`** if your project folder is not the default (see below). **`LLM_PROVIDER=mock`** skips live OpenAI for `/propose` unless you change it.

4. **Run the API**
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

5. **Tests (optional)**
   ```bash
   cd backend
   uv run pytest -q
   ```

All later commands in this README assume **`uv`** is on your **`PATH`** and you use **`uv run …`** from **`backend/`** when executing Python entrypoints there, or **`python scripts/…`** from the **repository root** for repo-level scripts.

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

**Which folder is the project root?** It is always **`WORKSPACE_ROOT / project_key`**. If you do nothing, defaults are the **`workspace`** directory next to **`backend/`** and **`project_key`** from **`PROJECT_NAME`** in **`backend/.env`**, else **`workspace/.current_project`**, else **`example_project`**.

Run the staged project pipeline from shell using **`backend/scripts/execute_project.py`** — **`cd backend`** first so workspace-relative paths behave like the API:

```bash
cd backend

# 1) Init stage: extract once to reusable context artifacts
python scripts/execute_project.py init --project project1

# Optional single-file init
python scripts/execute_project.py init --project project1 --input ../workspace/project1/input_docs/your.docx

# 2) Plan stage: produce reports/plan.md (or return clarification questions)
python scripts/execute_project.py plan --project project1 --instruction "Update consent wording and reviewer response alignment."

# Optional iterative answers from user
python scripts/execute_project.py plan --project project1 --instruction "..." --answer "Use formal tone" --answer "Keep section order"

# 3) Execute stage: run model-guided edits and output *_patched.docx
python scripts/execute_project.py execute --project project1
```

Or equivalently **`uv run python scripts/execute_project.py <stage> …`** from **`backend/`**.

The script prints the resolved **project root** line to **stderr** after JSON on stdout.

Implementation:
- Init stage: **`backend/app/services/project_init.py`**
- Plan stage: **`backend/app/services/project_plan.py`**
- Execute stage: **`backend/app/services/project_patching.py`**
- API route: **`backend/app/api/routers/project_pipeline.py`**

When init processes multiple files, per-document extraction outputs are distinct and now include structure preservation:
- **`{doc_id}_structure.json`** (full structure blocks from body/header/footer/tables including blank placeholders)
  - includes formatting metadata (font, size, color, emphasis, paragraph alignment/spacing, and table/cell style hints)
- **`{doc_id}_overview.md`**, **`{doc_id}_content_sheet.csv`**, **`{doc_id}_extraction.json`**

Project-level artifacts written by init:
- **`intermediate/init_context_manifest.json`** (machine-readable context index)
- **`intermediate/project_overview.md`** (human-readable summary across all initialized documents)

Progress reporting:
- init now reports quick XML scan stats per document (`xml parts` + compressed size).
- parse progress updates when each XML part is processed.
- batch mode processes documents in parallel (one document per thread, up to 4 workers).

Set **`PROJECT_NAME`** in **`backend/.env`** when you do not rely on **`workspace/.current_project`**. Restart the API after changing env or **`.current_project`** (`get_settings()` is cached).

### Example project: **`workspace/project1/`**

Prompt/instruction artifacts live here:

- **System prompt:** **`workspace/project1/prompts/agent_system.md`** (global system prompt used by init, plan, and execute).
- **Init instruction:** **`workspace/project1/instructions/init.txt`** (optional override; builtin template used if missing). Init is extraction/overview only.
- **Plan instruction:** **`workspace/project1/instructions/plan.txt`** (optional override; builtin template used if missing).
- **Execute instruction:** **`workspace/project1/instructions/execute.txt`** (optional override; builtin template used if missing).

Use **`PROJECT_NAME=project1`** or, from **`backend/`**, run a stage command such as **`python scripts/execute_project.py init --project project1`**. Put **`.docx`** files under **`workspace/project1/input_docs/`**.

(See **[Backend setup with uv](#backend-setup-with-uv-first-time)** above for **`uv sync`**, **`.env`**, and **`uv run uvicorn …`**.)

## Pipeline Endpoints

- `POST /parse` with `input_doc_path` and `doc_id`
- `POST /project/init` (**requires `OPENAI_API_KEY`**): run extraction once and write reusable init context manifest plus `intermediate/project_overview.md`.
- `POST /project/plan` (**requires `OPENAI_API_KEY`**): create or iterate `reports/plan.md`; may return clarification questions first.
- `POST /plan` alias for `/project/plan`.
- `POST /project/execute` (**requires `OPENAI_API_KEY`**): use approved plan + picked context to generate patched outputs in `output_docs/` as `<original>_patched.docx`.

- `POST /retrieve` with `requirement_text`
- `POST /propose` with `requirement_text`
- `GET /change-table`
- `PATCH /change-table/{change_id}` with `{ "status": "approved" | "rejected" }`
- `POST /apply` with `source_doc_path`, `output_doc_name`, `dry_run`
- `POST /report` with `run_id`

Deprecated:
- `POST /parse/extract-overview` is removed from the default workflow in favor of `/project/init`.

## Safety

- Original DOCX files are never overwritten.
- Only approved rows are applied.
- Dry-run mode is available for patch verification.

## Tests

From `backend`:

```bash
uv run pytest -q
```
