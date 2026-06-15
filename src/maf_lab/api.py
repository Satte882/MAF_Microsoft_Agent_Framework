from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from maf_lab.config import Settings
from maf_lab.domain import ConceptCard, HumanDecision, InvoiceCaseCreate, RunDetail, RunRecord, SystemInfo
from maf_lab.repository import SQLiteRepository
from maf_lab.service import RunService


STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()
    repository = SQLiteRepository(settings.database_path)
    repository.initialize()
    service = RunService(settings, repository)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.ensure_directories()
        repository.initialize()
        yield

    app = FastAPI(
        title="MAF Learning Platform",
        version="0.1.0",
        description="Runnable lab for Microsoft Agent Framework workflows, checkpoints and human approval.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repository = repository
    app.state.service = service
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "application": "maf-learning-platform"}

    @app.get("/api/system", response_model=SystemInfo)
    async def system_info() -> SystemInfo:
        return service.system_info()

    @app.get("/api/concepts", response_model=list[ConceptCard])
    async def concepts() -> list[ConceptCard]:
        return service.concepts()

    @app.get("/api/runs", response_model=list[RunRecord])
    async def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[RunRecord]:
        return service.list_runs()[:limit]

    @app.post("/api/runs", response_model=RunDetail, status_code=201)
    async def create_run(case: InvoiceCaseCreate) -> RunDetail:
        return await service.create_run(case)

    @app.get("/api/runs/{run_id}", response_model=RunDetail)
    async def get_run(run_id: str) -> RunDetail:
        try:
            return service.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc

    @app.post("/api/runs/{run_id}/decision", response_model=RunDetail)
    async def decide(run_id: str, decision: HumanDecision) -> RunDetail:
        try:
            return await service.decide(run_id, decision)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return app


app = create_app()
