from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.settings import Settings, get_settings
from app.services.artifacts import write_json
from app.services.change_table_store import load_change_table_csv
from app.services.reporting import write_run_report


router = APIRouter(tags=["report"])


class ReportRequest(BaseModel):
    run_id: str = "run-001"


@router.post("/report")
def generate_report(
    payload: ReportRequest, settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    table_path = settings.project_paths.change_tables_dir / "change_table.csv"
    rows = load_change_table_csv(table_path)
    report_payload = {
        "run_id": payload.run_id,
        "total_rows": len(rows),
        "status_breakdown": {
            "pending": len([r for r in rows if r.status == "pending"]),
            "approved": len([r for r in rows if r.status == "approved"]),
            "rejected": len([r for r in rows if r.status == "rejected"]),
            "applied": len([r for r in rows if r.status == "applied"]),
        },
    }
    report_path = settings.project_paths.reports_dir / "run_report.json"
    write_run_report(report_path, report_payload)
    return {"report_path": str(report_path)}
