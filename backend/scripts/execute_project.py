#!/usr/bin/env python3
"""Run project pipeline stages for **one workspace project**.

**Project root** is ``WORKSPACE_ROOT / PROJECT_NAME`` (resolved in ``app/services/workspace.py``).

Set it **before** this script runs using any of:

1. Flags on this script: ``--project`` / ``--workspace-root`` (applied after loading ``backend/.env``, so flags override ``.env``).
2. ``PROJECT_NAME`` and optional ``WORKSPACE_ROOT`` in ``backend/.env``.
3. First line of ``workspace/.current_project`` from ``python scripts/set_current_project.py <key>``.

Stages:

- ``init``: one-time extraction context build (single file or all ``input_docs/*.docx``).
- ``plan``: ask model to produce/iterate ``reports/plan.md`` (may return questions).
- ``execute``: run model-guided edits and write ``*_patched.docx`` into ``output_docs/``.

Examples (run from the ``backend/`` directory)::

    cd backend
    python scripts/execute_project.py init --project project1
    python scripts/execute_project.py plan --project project1 --instruction "Revise consent language"
    python scripts/execute_project.py execute --project project1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def find_backend_install_root() -> Path:
    """Locate the backend package directory (folder with ``pyproject.toml`` + ``app/``).

    Works whether this file lives at ``<repo>/scripts/execute_project.py`` or
    ``<repo>/backend/scripts/execute_project.py`` — we walk parents instead of assuming depth.
    """
    here = Path(__file__).resolve()
    for d in here.parents:
        if (d / "pyproject.toml").is_file() and (d / "app").is_dir():
            return d
    raise RuntimeError(
        f"Could not find backend root (directory with pyproject.toml and app/) above {here}"
    )


def main() -> int:
    backend = find_backend_install_root()

    sys.path.insert(0, str(backend))
    os.chdir(backend)

    from dotenv import load_dotenv

    load_dotenv(backend / ".env")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "stage",
        choices=["init", "plan", "execute"],
        help="Pipeline stage to run",
    )
    parser.add_argument(
        "--workspace-root",
        "-w",
        metavar="DIR",
        help="WORKSPACE_ROOT for this run (directory that contains project folders; default is <repo>/workspace)",
    )
    parser.add_argument(
        "--project",
        "-p",
        metavar="KEY",
        help="PROJECT_NAME for this run (path segment under WORKSPACE_ROOT, e.g. project1/example_project)",
    )
    parser.add_argument(
        "input_doc",
        nargs="?",
        metavar="PATH",
        help="Single input .docx (omit to process all input_docs/*.docx)",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_path",
        metavar="PATH",
        help="Single input .docx (same as positional)",
    )
    parser.add_argument(
        "--doc-id",
        default=None,
        help="Only used by init with a single input file; default is derived from filename stem",
    )
    parser.add_argument(
        "--instruction",
        default=None,
        help="Required by plan: user instruction that drives plan.md",
    )
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        help="Optional Q/A answer line for plan iteration; repeatable flag",
    )
    parser.add_argument(
        "--doc",
        dest="selected_doc_ids",
        action="append",
        default=[],
        help="Optional doc_id selection for plan/execute; repeatable flag",
    )
    parser.add_argument(
        "--plan-path",
        default=None,
        help="Optional explicit plan markdown path for execute (default reports/plan.md)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-document progress lines on stderr (JSON still goes to stdout)",
    )
    args = parser.parse_args()

    if args.workspace_root:
        os.environ["WORKSPACE_ROOT"] = str(Path(args.workspace_root).expanduser().resolve())
    if args.project:
        os.environ["PROJECT_NAME"] = args.project.strip()

    doc_path = args.input_path or args.input_doc

    # Import after env overrides so Settings resolves the right project root.
    from app.core.settings import get_settings
    from app.models.project_pipeline import ExecuteProjectRequest, PlanProjectRequest
    from app.services.extract_progress import emit_batch_begin, emit_batch_done, make_cli_stderr_progress
    from app.services.project_init import run_project_init
    from app.services.project_plan import run_project_plan
    from app.services.project_execute import run_project_execute

    get_settings.cache_clear()
    settings = get_settings()

    on_progress = None if args.quiet else make_cli_stderr_progress()

    try:
        if args.stage == "init":
            if args.doc_id:
                print("--doc-id is no longer used in init stage; doc id is derived from filename", file=sys.stderr)
            emit_batch_begin(on_progress, 1)
            result = run_project_init(settings=settings, input_doc_path=doc_path).model_dump()
            emit_batch_done(on_progress, 1)
        elif args.stage == "plan":
            req = PlanProjectRequest(
                user_instruction=(args.instruction or "").strip(),
                selected_doc_ids=args.selected_doc_ids or None,
                qa_answers=args.answer,
            )
            if not req.user_instruction:
                print("--instruction is required for plan stage", file=sys.stderr)
                return 2
            result = run_project_plan(
                settings=settings,
                user_instruction=req.user_instruction,
                selected_doc_ids=req.selected_doc_ids,
                qa_answers=req.qa_answers,
            ).model_dump()
        else:
            req = ExecuteProjectRequest(
                selected_doc_ids=args.selected_doc_ids or None,
                plan_path=args.plan_path,
            )
            result = run_project_execute(
                settings=settings,
                selected_doc_ids=req.selected_doc_ids,
                plan_path=req.plan_path,
            ).model_dump()
    except (ValueError, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    print(
        f"# project root: {settings.project_paths.root}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
