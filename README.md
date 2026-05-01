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

Run **extract / summarize** from the shell (same behaviour as **`POST /parse/extract-overview`**):

```bash
# Point at a project for this run only (overrides .env for this process)
python scripts/execute_project.py --project project1
python scripts/execute_project.py -p project1/example_project ../workspace/project1/example_project/input_docs/your.docx

# Rely on backend/.env / workspace/.current_project
python scripts/execute_project.py

# Batch: every *.docx in that project’s input_docs/
python scripts/execute_project.py --project project1

# Single file path (still set --project if not in .env)
python scripts/execute_project.py --project project1 ../workspace/project1/input_docs/your.docx
```

The script prints the resolved **project root** line to **stderr** after the JSON on stdout.

Implementation: **`backend/app/services/project_extract.py`** (`run_extract_overview`, `run_extract_overview_all_input_docs`). **`POST /parse/extract-overview`** calls the same service; omit **`input_doc_path`** in the JSON body to process all **`input_docs/*.docx`**.

When multiple files run in one batch, **`blocks.json`** is overwritten per file (**last sorted file wins**); per-document outputs use distinct names (**`{doc_id}_overview.md`**, etc.).

Set **`PROJECT_NAME`** in **`backend/.env`** when you do not rely on **`workspace/.current_project`**. Restart the API after changing env or **`.current_project`** (`get_settings()` is cached).

### Example project: **`workspace/project1/`**

Reviewer-style prompts live here:

- **System prompt:** **`workspace/project1/prompts/agent_system.md`** (loaded as OpenAI **`instructions`** for extract-overview).
- **Task prompt:** **`workspace/project1/instructions/full_document_extraction.txt`** (exhaustive extraction / capability test wording; must still satisfy the pipeline JSON schema).

Use **`PROJECT_NAME=project1`** or **`python scripts/execute_project.py --project project1`**. Put **`.docx`** files under **`workspace/project1/input_docs/`**.

(See **[Backend setup with uv](#backend-setup-with-uv-first-time)** above for **`uv sync`**, **`.env`**, and **`uv run uvicorn …`**.)

## Pipeline Endpoints

- `POST /parse` with `input_doc_path` and `doc_id`
- `POST /parse/extract-overview` (**requires `OPENAI_API_KEY`**): body may include **`input_doc_path`** + optional **`doc_id`**, or omit **`input_doc_path`** to process **every `input_docs/*.docx`** in the active project. Writes under **`intermediate/`** as above (batch ⇒ last file determines **`blocks.json`**).

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

```bash
uv run pytest -q
```
