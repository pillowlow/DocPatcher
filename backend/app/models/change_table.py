from typing import Literal

from pydantic import BaseModel


ChangeStatus = Literal["pending", "approved", "rejected", "applied"]


class ChangeRow(BaseModel):
    change_id: str
    doc_id: str
    block_id: str
    original_text: str
    proposed_text: str
    status: ChangeStatus = "pending"


class ChangeStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]
