"""Load LLM-facing text from ``ARTIFACT_ROOT``: task instructions, agent system prompt, (document body built elsewhere)."""

from pathlib import Path

INSTRUCTIONS_SUBDIR = "instructions"
PROMPTS_SUBDIR = "prompts"

DEFAULT_TASK_INSTRUCTION_FILE = "full_document_extraction.txt"
DEFAULT_AGENT_SYSTEM_PROMPT_FILE = "agent_system.md"

_ALLOWED_TEXT_SUFFIXES = frozenset({".txt", ".md"})


def task_instructions_dir(artifact_root: Path) -> Path:
    return artifact_root / INSTRUCTIONS_SUBDIR


def agent_prompts_dir(artifact_root: Path) -> Path:
    return artifact_root / PROMPTS_SUBDIR


def _load_text_under_artifact(
    artifact_root: Path,
    subdir: str,
    filename: str,
    *,
    role_label: str,
) -> str:
    path = artifact_root / subdir / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"{role_label} file not found: {path}. "
            f"Create {filename!r} under {artifact_root / subdir!s}."
        )
    if path.suffix.lower() not in _ALLOWED_TEXT_SUFFIXES:
        raise ValueError(
            f"{role_label} must be .txt or .md, got {path.suffix!r} ({path})"
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{role_label} file is empty: {path}")
    return text


def load_task_instruction(artifact_root: Path, filename: str | None = None) -> str:
    """What to do with the document(s): ``ARTIFACT_ROOT/instructions/{file}``."""
    rel = filename or DEFAULT_TASK_INSTRUCTION_FILE
    return _load_text_under_artifact(
        artifact_root,
        INSTRUCTIONS_SUBDIR,
        rel,
        role_label="Task instruction",
    )


def load_agent_system_prompt(artifact_root: Path, filename: str | None = None) -> str:
    """Agent persona / system behaviour: ``ARTIFACT_ROOT/prompts/{file}``."""
    rel = filename or DEFAULT_AGENT_SYSTEM_PROMPT_FILE
    return _load_text_under_artifact(
        artifact_root,
        PROMPTS_SUBDIR,
        rel,
        role_label="Agent system prompt",
    )
