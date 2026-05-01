from fastapi import FastAPI

from app.api.routers import (
    apply as apply_router,
    change_table as change_table_router,
    health,
    parse as parse_router,
    propose as propose_router,
    report as report_router,
    retrieve as retrieve_router,
)


def create_app() -> FastAPI:
    app = FastAPI(title="DocPatcher API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(parse_router.router)
    app.include_router(retrieve_router.router)
    app.include_router(propose_router.router)
    app.include_router(change_table_router.router)
    app.include_router(apply_router.router)
    app.include_router(report_router.router)
    return app


app = create_app()
