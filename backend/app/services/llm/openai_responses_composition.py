"""Compose OpenAI Responses API ``instructions`` and ``input`` from artifact-backed parts + parsed document."""


def compose_openai_responses_user_input(
    *,
    task_instruction: str,
    document_section: str,
) -> str:
    """Full user turn: task (what to do) + input document (parsed body)."""
    return (
        "## Task instruction\n\n"
        f"{task_instruction.strip()}\n\n"
        "## Input document (parsed from DOCX)\n\n"
        f"{document_section.strip()}\n"
    )


def compose_input_document_section(
    *,
    doc_id: str,
    source_file_name: str,
    paragraph_block_listing: str,
) -> str:
    """Machine-readable listing of one parsed document (metadata + paragraph blocks)."""
    return (
        "DOCUMENT_METADATA:\n"
        f"- doc_id: {doc_id}\n"
        f"- source_file_name: {source_file_name}\n\n"
        "PARAGRAPH_BLOCKS (verbatim text per block; use block_id and paragraph_index as given):\n\n"
        f"{paragraph_block_listing.strip()}\n"
    )
