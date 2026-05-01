from typing import Literal
from pydantic import BaseModel


class ProposalItem(BaseModel):
    block_id: str
    should_change: bool
    reason: str
    proposed_text: str
    risk_level: Literal["low", "medium", "high"]
