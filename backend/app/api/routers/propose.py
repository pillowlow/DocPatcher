from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.settings import Settings, get_settings
from app.models.block import Block
from app.models.candidate import CandidateBuffer
from app.models.requirement import Requirement
from app.services.artifacts import read_json
from app.services.change_table_store import save_change_table_csv
from app.services.proposer import build_provider, propose_changes


router = APIRouter(tags=["propose"])


class ProposeRequest(BaseModel):
    requirement_id: str = "REQ001"
    requirement_text: str


@router.post("/propose")
def propose(
    request: ProposeRequest, settings: Settings = Depends(get_settings)
) -> dict[str, str | int]:
    blocks_path = settings.artifact_root / "intermediate" / "blocks.json"
    candidates_path = settings.artifact_root / "intermediate" / "candidates.json"
    blocks = [Block(**record) for record in read_json(blocks_path)]
    blocks_by_id = {block.block_id: block for block in blocks}
    candidate_buffer = CandidateBuffer(**read_json(candidates_path))
    requirement = Requirement(
        requirement_id=request.requirement_id, text=request.requirement_text
    )

    provider = build_provider(settings)
    rows = propose_changes(requirement, blocks_by_id, candidate_buffer, provider)
    output_path = settings.artifact_root / "change_tables" / "change_table.csv"
    save_change_table_csv(output_path, rows)
    return {"change_rows": len(rows), "change_table_path": str(output_path)}
