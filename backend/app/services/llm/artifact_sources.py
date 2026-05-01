"""Load fixed LLM text assets from an active **project root** (``instructions/``, ``prompts/``)."""

from pathlib import Path

INSTRUCTIONS_SUBDIR = "instructions"
PROMPTS_SUBDIR = "prompts"

DEFAULT_TASK_INSTRUCTION_FILE = "full_document_extraction.txt"
DEFAULT_AGENT_SYSTEM_PROMPT_FILE = "agent_system.md"
DEFAULT_PROJECT_INIT_INSTRUCTION_FILE = "init.txt"
DEFAULT_PROJECT_PLAN_INSTRUCTION_FILE = "plan.txt"
DEFAULT_PROJECT_EXECUTE_INSTRUCTION_FILE = "execute.txt"

_ALLOWED_TEXT_SUFFIXES = frozenset({".txt", ".md"})
_DEFAULT_AGENT_SYSTEM_PROMPT = (
    "You are a senior document revision agent. Ask clarifying questions when instructions are unclear "
    "or underspecified. When context is sufficient, produce structured, actionable output and stay "
    "grounded in the provided project artifacts."
)
_DEFAULT_PROJECT_INIT_INSTRUCTION = (
    "Extract source documents once and produce faithful overview/context artifacts for the project. "
    "Do not perform planning or editing in this stage."
)
_DEFAULT_PROJECT_PLAN_INSTRUCTION = (
    "Create a numbered plan for document changes. Include project understanding, explicit edits, "
    "and questions only when clarification is required before safe execution."
)
_DEFAULT_PROJECT_EXECUTE_INSTRUCTION = (
    "Execute approved plan edits on target document blocks. Preserve unchanged content, rewrite only "
    "where needed, and return high-precision block-level revisions."
)


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


def _load_with_fallback(
    project_root: Path,
    subdir: str,
    filename: str,
    *,
    role_label: str,
    fallback_text: str,
) -> str:
    try:
        return _load_text_under_project(
            project_root,
            subdir,
            filename,
            role_label=role_label,
        )
    except FileNotFoundError:
        return fallback_text


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
    return _load_with_fallback(
        project_root,
        PROMPTS_SUBDIR,
        rel,
        role_label="Agent system prompt",
        fallback_text=_DEFAULT_AGENT_SYSTEM_PROMPT,
    )


def load_project_init_instruction(project_root: Path, filename: str | None = None) -> str:
    """Init-stage instruction text from ``{project_root}/instructions/{file}``."""
    rel = filename or DEFAULT_PROJECT_INIT_INSTRUCTION_FILE
    return _load_with_fallback(
        project_root,
        INSTRUCTIONS_SUBDIR,
        rel,
        role_label="Project init instruction",
        fallback_text=_DEFAULT_PROJECT_INIT_INSTRUCTION,
    )


def load_project_plan_instruction(project_root: Path, filename: str | None = None) -> str:
    """Plan-stage instruction text from ``{project_root}/instructions/{file}``."""
    rel = filename or DEFAULT_PROJECT_PLAN_INSTRUCTION_FILE
    return _load_with_fallback(
        project_root,
        INSTRUCTIONS_SUBDIR,
        rel,
        role_label="Project plan instruction",
        fallback_text=_DEFAULT_PROJECT_PLAN_INSTRUCTION,
    )


def load_project_execute_instruction(
    project_root: Path, filename: str | None = None
) -> str:
    """Execute-stage instruction text from ``{project_root}/instructions/{file}``."""
    rel = filename or DEFAULT_PROJECT_EXECUTE_INSTRUCTION_FILE
    return _load_with_fallback(
        project_root,
        INSTRUCTIONS_SUBDIR,
        rel,
        role_label="Project execute instruction",
        fallback_text=_DEFAULT_PROJECT_EXECUTE_INSTRUCTION,
    )
