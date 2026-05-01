from fastapi import APIRouter, Depends, HTTPException

from app.core.settings import Settings, get_settings
from app.models.change_table import ChangeStatusUpdate
from app.services.change_table_store import load_change_table_csv, save_change_table_csv


router = APIRouter(tags=["change-table"])


@router.get("/change-table")
def get_change_table(settings: Settings = Depends(get_settings)) -> dict[str, list[dict]]:
    path = settings.project_paths.change_tables_dir / "change_table.csv"
    rows = load_change_table_csv(path)
    return {"rows": [row.model_dump() for row in rows]}


@router.patch("/change-table/{change_id}")
def update_change_status(
    change_id: str, payload: ChangeStatusUpdate, settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    path = settings.project_paths.change_tables_dir / "change_table.csv"
    rows = load_change_table_csv(path)
    for row in rows:
        if row.change_id == change_id:
            row.status = payload.status
            save_change_table_csv(path, rows)
            return {"updated_change_id": change_id, "status": payload.status}
    raise HTTPException(status_code=404, detail="change_id not found")
