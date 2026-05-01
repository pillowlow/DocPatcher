from pydantic import BaseModel


class CandidateItem(BaseModel):
    block_id: str
    score: float


class CandidateBuffer(BaseModel):
    requirement_id: str
    candidates: list[CandidateItem]
