from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sociomemory.dashboard.export import DashboardService

ServiceFactory = Callable[[], DashboardService]


class IngestRequest(BaseModel):
    text: str = ""
    source: str = "conversation"


class PersonRequest(BaseModel):
    name: str | None = None
    area: str | None = None
    school: str | None = None
    places: list[str] | str | None = None
    notes: str | None = None


class LocationRequest(BaseModel):
    lat: float
    lng: float
    accuracy_m: float | None = None


def create_app(service_factory: ServiceFactory = DashboardService.from_env) -> FastAPI:
    app = FastAPI(
        title="Sociomemory Dashboard API",
        docs_url="/docs" if _docs_enabled() else None,
        redoc_url="/redoc" if _docs_enabled() else None,
        openapi_url="/openapi.json" if _docs_enabled() else None,
    )
    app.state.dashboard_service_factory = service_factory
    _configure_cors(app)
    _configure_exception_handlers(app)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(_protected_router())
    return app


def _protected_router() -> APIRouter:
    router = APIRouter(prefix="/api", dependencies=[Depends(_require_dashboard_token)])

    @router.get("/children")
    async def list_children(request: Request, limit: int = 100) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.list_children(limit=limit)

    @router.get("/children/{child_id}/summary")
    async def summary(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.summary(child_id)

    @router.get("/children/{child_id}/graph")
    async def graph_export(
        request: Request,
        child_id: str,
        start_id: str | None = None,
        max_depth: int = 3,
        min_confidence: float = 0.0,
        limit: int = 200,
    ) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.graph_export(
                child_id=child_id,
                start_id=start_id,
                max_depth=max_depth,
                min_confidence=min_confidence,
                limit=limit,
            )

    @router.get("/children/{child_id}/nodes/{node_id}")
    async def node_detail(request: Request, child_id: str, node_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.node_detail(child_id, node_id)

    @router.get("/children/{child_id}/stale")
    async def stale_nodes(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.stale_nodes(child_id)

    @router.get("/children/{child_id}/profile")
    async def profile(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.profile(child_id)

    @router.get("/children/{child_id}/context")
    async def context(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.context(child_id)

    @router.get("/children/{child_id}/coaching")
    async def coaching(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.coaching(child_id)

    @router.get("/children/{child_id}/privacy/export")
    async def privacy_export(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.privacy_export(child_id)

    @router.delete("/children/{child_id}/privacy")
    async def privacy_erase(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.privacy_erase(child_id)

    @router.post("/children/{child_id}/ingest")
    async def ingest(request: Request, child_id: str, body: IngestRequest) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.ingest(
                child_id=child_id,
                text=body.text,
                source=body.source,
            )

    @router.post("/children/{child_id}/person")
    async def ingest_person(request: Request, child_id: str, body: PersonRequest) -> dict[str, Any]:
        places = body.places
        if isinstance(places, str):
            places = [p.strip() for p in places.split(",")]
        async with _service(request) as service:
            return await service.ingest_person(
                child_id=child_id,
                name=_opt_str(body.name),
                area=_opt_str(body.area),
                school=_opt_str(body.school),
                places=[p for p in (places or []) if p],
                notes=_opt_str(body.notes),
            )

    @router.post("/children/{child_id}/episodes/segment")
    async def segment_episodes(request: Request, child_id: str) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.segment_episodes(child_id)

    @router.post("/children/{child_id}/location/acquire")
    async def acquire_location(
        request: Request,
        child_id: str,
        body: LocationRequest,
    ) -> dict[str, Any]:
        async with _service(request) as service:
            return await service.acquire_location(
                child_id=child_id,
                lat=body.lat,
                lng=body.lng,
                accuracy_m=body.accuracy_m,
            )

    return router


@asynccontextmanager
async def _service(request: Request):
    factory: ServiceFactory = request.app.state.dashboard_service_factory
    service = factory()
    await service.connect()
    try:
        yield service
    finally:
        await service.close()


def _require_dashboard_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> None:
    expected = os.getenv("SOCIOMEMORY_DASHBOARD_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SOCIOMEMORY_DASHBOARD_TOKEN is not configured",
        )
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        _raise_invalid_token()
    if not secrets.compare_digest(token, expected):
        _raise_invalid_token()


def _raise_invalid_token() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or missing dashboard token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _configure_cors(app: FastAPI) -> None:
    origins = [
        origin.strip()
        for origin in os.getenv("SOCIOMEMORY_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


def _configure_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LookupError)
    async def not_found_handler(_request: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=status.HTTP_404_NOT_FOUND)

    @app.exception_handler(ValueError)
    async def bad_request_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=status.HTTP_400_BAD_REQUEST)


def _docs_enabled() -> bool:
    return os.getenv("SOCIOMEMORY_ENABLE_DOCS", "").lower() in {"1", "true", "yes"}


def _opt_str(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


app = create_app()
