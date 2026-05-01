import json
from datetime import UTC, datetime
from pathlib import Path


def write_run_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        **payload,
    }
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
