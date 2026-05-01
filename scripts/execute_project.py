#!/usr/bin/env python3
"""Run extract / summarize for **one workspace project** (same as ``POST /parse/extract-overview``).

**Project root** is ``WORKSPACE_ROOT / PROJECT_NAME`` (resolved in ``app/services/workspace.py``).

Set it **before** this script runs using any of:

1. Flags on this script: ``--project`` / ``--workspace-root`` (applied after loading ``backend/.env``, so flags override ``.env``).
2. ``PROJECT_NAME`` and optional ``WORKSPACE_ROOT`` in ``backend/.env``.
3. First line of ``workspace/.current_project`` from ``python scripts/set_current_project.py <key>``.

**Default:** omit the input path to process every ``*.docx`` in that project’s ``input_docs/``.

Examples::

    python scripts/execute_project.py --project project1/example_project
    python scripts/execute_project.py -p project1/example_project -w ../workspace
    python scripts/execute_project.py --project my/nested/project --input path/to/one.docx
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    backend = repo / "backend"
    if not backend.is_dir():
        print(f"Expected backend/ at {backend}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(backend))
    os.chdir(backend)

    from dotenv import load_dotenv

    load_dotenv(backend / ".env")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
        help="Only for a single file; default is derived from the filename stem",
    )
    args = parser.parse_args()

    if args.workspace_root:
        os.environ["WORKSPACE_ROOT"] = str(Path(args.workspace_root).expanduser().resolve())
    if args.project:
        os.environ["PROJECT_NAME"] = args.project.strip()

    doc_path = args.input_path or args.input_doc

    # Import after env overrides so Settings resolves the right project root.
    from app.core.settings import get_settings
    from app.services.project_extract import (
        run_extract_overview,
        run_extract_overview_all_input_docs,
        stable_doc_id_from_filename,
    )

    get_settings.cache_clear()
    settings = get_settings()

    try:
        if doc_path:
            inp = Path(doc_path)
            doc_id = args.doc_id or stable_doc_id_from_filename(inp, 1)
            result = run_extract_overview(
                input_doc_path=inp,
                doc_id=doc_id,
                settings=settings,
            )
        else:
            if args.doc_id:
                print("--doc-id applies only when a single input file is given", file=sys.stderr)
                return 2
            result = run_extract_overview_all_input_docs(settings=settings)
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
