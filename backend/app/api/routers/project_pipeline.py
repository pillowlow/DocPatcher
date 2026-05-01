from fastapi import APIRouter, Depends, HTTPException

from app.core.settings import Settings, get_settings
from app.models.project_pipeline import (
    ExecuteProjectRequest,
    ExecuteProjectResponse,
    InitProjectRequest,
    InitProjectResponse,
    PlanProjectRequest,
    PlanProjectResponse,
)
from app.services.project_patching import run_project_execute
from app.services.project_init import run_project_init
from app.services.project_plan import run_project_plan


router = APIRouter(tags=["project-pipeline"])


def _to_http_error(e: Exception) -> HTTPException:
    if isinstance(e, ValueError):
        return HTTPException(status_code=400, detail=str(e))
    if isinstance(e, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(e))
    raise e


@router.post("/project/init", response_model=InitProjectResponse)
def init_project(
    request: InitProjectRequest,
    settings: Settings = Depends(get_settings),
) -> InitProjectResponse:
    try:
        return run_project_init(settings=settings, input_doc_path=request.input_doc_path)
    except (ValueError, FileNotFoundError) as e:
        raise _to_http_error(e) from e


@router.post("/project/plan", response_model=PlanProjectResponse)
def plan_project(
    request: PlanProjectRequest,
    settings: Settings = Depends(get_settings),
) -> PlanProjectResponse:
    try:
        return run_project_plan(
            settings=settings,
            user_instruction=request.user_instruction,
            selected_doc_ids=request.selected_doc_ids,
            qa_answers=request.qa_answers,
        )
    except (ValueError, FileNotFoundError) as e:
        raise _to_http_error(e) from e


@router.post("/plan", response_model=PlanProjectResponse)
def plan_project_alias(
    request: PlanProjectRequest,
    settings: Settings = Depends(get_settings),
) -> PlanProjectResponse:
    """Compatibility alias for plan stage."""
    return plan_project(request=request, settings=settings)


@router.post("/project/execute", response_model=ExecuteProjectResponse)
def execute_project(
    request: ExecuteProjectRequest,
    settings: Settings = Depends(get_settings),
) -> ExecuteProjectResponse:
    try:
        return run_project_execute(
            settings=settings,
            selected_doc_ids=request.selected_doc_ids,
            plan_path=request.plan_path,
        )
    except (ValueError, FileNotFoundError) as e:
        raise _to_http_error(e) from e
