from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.settings import Settings, get_settings
from app.models.change_table import ChangeRow
from app.services.change_table_store import load_change_table_csv, save_change_table_csv
from app.services.patcher import apply_changes_to_docx


router = APIRouter(tags=["apply"])


class ApplyRequest(BaseModel):
    source_doc_path: str
    output_doc_name: str = "patched_output.docx"
    dry_run: bool = True


@router.post("/apply")
def apply_changes(
    request: ApplyRequest, settings: Settings = Depends(get_settings)
) -> dict[str, int | str]:
    table_path = settings.artifact_root / "change_tables" / "change_table.csv"
    all_rows = load_change_table_csv(table_path)
    approved_rows = [row for row in all_rows if row.status == "approved"]

    source_doc = Path(request.source_doc_path)
    output_doc = settings.artifact_root / "output_docs" / request.output_doc_name
    result = apply_changes_to_docx(
        source_doc=source_doc,
        output_doc=output_doc,
        approved_rows=approved_rows,
        dry_run=request.dry_run,
    )
    if not request.dry_run:
        updated_rows: list[ChangeRow] = []
        approved_ids = {row.change_id for row in approved_rows}
        for row in all_rows:
            if row.change_id in approved_ids:
                row.status = "applied"
            updated_rows.append(row)
        save_change_table_csv(table_path, updated_rows)

    return {**result, "output_doc": str(output_doc)}
