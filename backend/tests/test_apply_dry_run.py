from pathlib import Path

from app.models.change_table import ChangeRow
from app.services.patcher import apply_changes_to_docx


def test_apply_dry_run_does_not_create_output(tmp_path: Path) -> None:
    source = tmp_path / "in.docx"
    output = tmp_path / "out.docx"
    source.write_bytes(b"placeholder")

    rows = [
        ChangeRow(
            change_id="C0001",
            doc_id="DOC001",
            block_id="DOC001-B0001",
            original_text="old",
            proposed_text="new",
            status="approved",
        )
    ]
    result = apply_changes_to_docx(source, output, rows, dry_run=True)
    assert result["mode"] == "dry-run"
    assert output.exists() is False
