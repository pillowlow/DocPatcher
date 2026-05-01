from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.settings import Settings, get_settings
from app.services.artifacts import write_json
from app.services.document_extraction import extract_overview_and_content_sheet
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


@router.post("/parse/extract-overview")
def parse_and_extract_overview(
    request: ParseRequest, settings: Settings = Depends(get_settings)
) -> dict[str, str | int]:
    """Parse DOCX blocks, call the model once to emit overview Markdown + CSV content sheet."""
    if not settings.openai_api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is required for /parse/extract-overview.",
        )
    input_path = Path(request.input_doc_path)
    if not input_path.is_file():
        raise HTTPException(status_code=404, detail=f"Input document not found: {input_path}")
    blocks = parse_docx_to_blocks(input_path, doc_id=request.doc_id)
    try:
        parsed_result = extract_overview_and_content_sheet(
            blocks=blocks,
            settings=settings,
            project_paths=settings.project_paths,
            doc_id=request.doc_id,
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    blocks_path = settings.project_paths.intermediate_dir / "blocks.json"
    write_json(blocks_path, [block.model_dump() for block in blocks])
    return {
        **parsed_result,
        "blocks": len(blocks),
        "blocks_path": str(blocks_path),
    }
