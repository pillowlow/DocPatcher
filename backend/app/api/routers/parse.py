from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.settings import Settings, get_settings
from app.services.artifacts import write_json
from app.services.docx_parser import parse_docx_to_blocks
from app.services.project_extract import (
    run_extract_overview,
    run_extract_overview_all_input_docs,
    stable_doc_id_from_filename,
)


router = APIRouter(tags=["parse"])


class ParseRequest(BaseModel):
    input_doc_path: str
    doc_id: str = "DOC001"


class ExtractOverviewRequest(BaseModel):
    """Omit ``input_doc_path`` to run on every ``*.docx`` under the project ``input_docs/``."""

    input_doc_path: str | None = Field(
        default=None,
        description="Path to one .docx; if omitted, all ``input_docs/*.docx`` are processed.",
    )
    doc_id: str | None = Field(
        default=None,
        description="Only used with a single ``input_doc_path``. Defaults to sanitized file stem.",
    )

    @field_validator("input_doc_path", mode="before")
    @classmethod
    def empty_path_is_none(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        return str(v)

    @field_validator("doc_id", mode="before")
    @classmethod
    def empty_doc_id_is_none(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        return str(v)


@router.post("/parse")
def parse_document(
    request: ParseRequest, settings: Settings = Depends(get_settings)
) -> dict[str, str | int]:
    input_path = Path(request.input_doc_path)
    blocks = parse_docx_to_blocks(input_path, doc_id=request.doc_id)
    output_path = settings.project_paths.intermediate_dir / "blocks.json"
    write_json(output_path, [block.model_dump() for block in blocks])
    return {"blocks": len(blocks), "blocks_path": str(output_path)}


def _http_from_extract_error(e: Exception) -> HTTPException:
    if isinstance(e, ValueError):
        return HTTPException(status_code=400, detail=str(e))
    if isinstance(e, FileNotFoundError):
        detail = str(e)
        if detail.startswith("Input document not found"):
            return HTTPException(status_code=404, detail=detail)
        return HTTPException(status_code=400, detail=detail)
    raise e


@router.post("/parse/extract-overview")
def parse_and_extract_overview(
    request: ExtractOverviewRequest, settings: Settings = Depends(get_settings)
) -> dict[str, str | int] | dict[str, object]:
    """Parse DOCX, run the model: one file, or every ``input_docs/*.docx`` when path omitted."""
    try:
        if request.input_doc_path is not None:
            input_path = Path(request.input_doc_path)
            doc_id = request.doc_id or stable_doc_id_from_filename(input_path, 1)
            result = run_extract_overview(
                input_doc_path=input_path,
                doc_id=doc_id,
                settings=settings,
            )
            return result
        return run_extract_overview_all_input_docs(settings=settings)
    except (ValueError, FileNotFoundError) as e:
        raise _http_from_extract_error(e) from e
