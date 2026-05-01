import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))
