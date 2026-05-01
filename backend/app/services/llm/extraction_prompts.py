"""Hints/prompt templates for LLM-assisted steps. Operational text lives under ARTIFACT_ROOT/prompts/."""

from pathlib import Path

EXTRACTION_PROMPT_FILENAME = "full_document_extraction.txt"


def prompts_dir(artifact_root: Path) -> Path:
    return artifact_root / "prompts"


def load_extraction_hints(artifact_root: Path) -> str:
    """Load system instructions/hints from example_project-style prompts folder."""
    path = prompts_dir(artifact_root) / EXTRACTION_PROMPT_FILENAME
    if not path.is_file():
        raise FileNotFoundError(
            f"Extraction hints not found at {path}. "
            f"Create {EXTRACTION_PROMPT_FILENAME} under {prompts_dir(artifact_root)!s}."
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Extraction hints file is empty: {path}")
    return text


def build_extraction_input(doc_id: str, file_name: str, numbered_blocks: str) -> str:
    """User message carrying block listing for the Responses API."""
    return (
        f"DOCUMENT_METADATA:\n"
        f"- doc_id: {doc_id}\n"
        f"- file_name: {file_name}\n\n"
        f"The following lines are labelled blocks. BLOCK lines are verbatim source text:\n\n"
        f"{numbered_blocks}"
    )
