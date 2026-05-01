from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.settings import Settings, get_settings
from app.services.artifacts import write_json
from app.services.docx_parser import parse_docx_to_blocks


router = APIRouter(tags=["parse"])


class ParseRequest(BaseModel):
    input_doc_path: str
    doc_id: str = "DOC001"


@router.post("/parse")
def parse_document(
    request: ParseRequest, settings: Settings = Depends(get_settings)
) -> dict[str, str | int]:
    input_path = Path(request.input_doc_path)
    blocks = parse_docx_to_blocks(input_path, doc_id=request.doc_id)
    output_path = settings.project_paths.intermediate_dir / "blocks.json"
    write_json(output_path, [block.model_dump() for block in blocks])
    return {"blocks": len(blocks), "blocks_path": str(output_path)}
