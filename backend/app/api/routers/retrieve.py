from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.settings import Settings, get_settings
from app.models.block import Block
from app.models.requirement import Requirement
from app.services.artifacts import read_json, write_json
from app.services.retriever import retrieve_candidates


router = APIRouter(tags=["retrieve"])


class RetrieveRequest(BaseModel):
    requirement_id: str = "REQ001"
    requirement_text: str
    top_k: int | None = None


@router.post("/retrieve")
def retrieve(
    request: RetrieveRequest, settings: Settings = Depends(get_settings)
) -> dict[str, str | int]:
    blocks_path = settings.project_paths.intermediate_dir / "blocks.json"
    blocks = [Block(**record) for record in read_json(blocks_path)]
    requirement = Requirement(
        requirement_id=request.requirement_id, text=request.requirement_text
    )
    candidate_buffer = retrieve_candidates(
        requirement=requirement,
        blocks=blocks,
        top_k=request.top_k or settings.default_top_k,
    )
    output_path = settings.project_paths.intermediate_dir / "candidates.json"
    write_json(output_path, candidate_buffer.model_dump())
    return {"candidates": len(candidate_buffer.candidates), "candidates_path": str(output_path)}
