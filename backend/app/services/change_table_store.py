from pathlib import Path

import pandas as pd

from app.models.change_table import ChangeRow

CHANGE_TABLE_COLUMNS = [
    "change_id",
    "doc_id",
    "block_id",
    "original_text",
    "proposed_text",
    "status",
]


def save_change_table_csv(path: Path, rows: list[ChangeRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row.model_dump() for row in rows], columns=CHANGE_TABLE_COLUMNS)
    df.to_csv(path, index=False)


def load_change_table_csv(path: Path) -> list[ChangeRow]:
    if not path.exists():
        return []
    df = pd.read_csv(path).fillna("")
    return [ChangeRow(**record) for record in df.to_dict(orient="records")]
