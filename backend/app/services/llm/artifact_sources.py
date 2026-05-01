"""Load fixed LLM text assets from an active **project root** (``instructions/``, ``prompts/``)."""

from pathlib import Path

INSTRUCTIONS_SUBDIR = "instructions"
PROMPTS_SUBDIR = "prompts"

DEFAULT_TASK_INSTRUCTION_FILE = "full_document_extraction.txt"
DEFAULT_AGENT_SYSTEM_PROMPT_FILE = "agent_system.md"

_ALLOWED_TEXT_SUFFIXES = frozenset({".txt", ".md"})


def task_instructions_dir(project_root: Path) -> Path:
    return project_root / INSTRUCTIONS_SUBDIR


def agent_prompts_dir(project_root: Path) -> Path:
    return project_root / PROMPTS_SUBDIR


def _load_text_under_project(
    project_root: Path,
    subdir: str,
    filename: str,
    *,
    role_label: str,
) -> str:
    path = project_root / subdir / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"{role_label} file not found: {path}. "
            f"Create {filename!r} under {project_root / subdir!s}."
        )
    if path.suffix.lower() not in _ALLOWED_TEXT_SUFFIXES:
        raise ValueError(
            f"{role_label} must be .txt or .md, got {path.suffix!r} ({path})"
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{role_label} file is empty: {path}")
    return text


def load_task_instruction(project_root: Path, filename: str | None = None) -> str:
    """Task text from ``{project_root}/instructions/{file}``."""
    rel = filename or DEFAULT_TASK_INSTRUCTION_FILE
    return _load_text_under_project(
        project_root,
        INSTRUCTIONS_SUBDIR,
        rel,
        role_label="Task instruction",
    )


def load_agent_system_prompt(project_root: Path, filename: str | None = None) -> str:
    """Agent system prompt from ``{project_root}/prompts/{file}``."""
    rel = filename or DEFAULT_AGENT_SYSTEM_PROMPT_FILE
    return _load_text_under_project(
        project_root,
        PROMPTS_SUBDIR,
        rel,
        role_label="Agent system prompt",
    )
