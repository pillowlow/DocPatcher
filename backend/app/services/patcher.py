from pathlib import Path

from docx import Document

from app.models.change_table import ChangeRow


def apply_changes_to_docx(
    source_doc: Path,
    output_doc: Path,
    approved_rows: list[ChangeRow],
    dry_run: bool,
) -> dict[str, int | str]:
    if dry_run:
        return {"mode": "dry-run", "approved_changes": len(approved_rows)}

    doc = Document(source_doc)
    replacements = {row.original_text: row.proposed_text for row in approved_rows}
    applied = 0
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text in replacements:
            paragraph.text = replacements[text]
            applied += 1

    output_doc.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_doc)
    return {"mode": "apply", "approved_changes": len(approved_rows), "applied": applied}
